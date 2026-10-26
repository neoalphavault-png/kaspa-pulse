#!/usr/bin/env python3
"""lauscher_auswertung.py - wertet den Tempnet-Zuhoerer (tempnet_lauscher.py) aus.

Eingang: ein oder mehrere Lauf-Ordner (ereignisse/koepfe/compact.jsonl.gz und
meta.json je Lauf) und die Kette aus tempnet_koepfe.py, abgerufen NACH den
Laeufen. Ausgang: eine Zeile je Kettenblock (CSV) und eine Zusammenfassung.

Groessen (Ben, 25.10.2026; Namen wie im Tempnet-Thread):
- first_seen_utc: erste Ankuendigung des Blocks bei uns, ueber alle Peers und
  Nachrichtentypen; dazu je Typ (inv, headers, cmpctblock) die erste.
- timestamp_deviation_s = first_seen_utc minus Header-Zeitstempel. Name nach
  bitcoincashautist; kein reiner Ausbreitungswert, weil Miner den Zeitstempel
  frei innerhalb der Regeln setzen.
- propagation_spread_ms: letzte minus erste Ankuendigung ueber die Peers, je
  Peer die erste Ankuendigung, nur Bloecke mit mindestens zwei Peers.
- Stale: angekuendigter Block, der nicht in der Kette steht, obwohl die Kette
  mindestens 6 Bloecke ueber seine Hoehe hinausreicht.
- Compact-Block-Weg: ob ein cmpctblock kam (von selbst im High-Bandwidth-Modus
  oder auf unsere Anfrage), Kurz-IDs, vorbefuellte TX und die geschaetzt
  fehlenden TX (Kurz-IDs, die zu keiner bei uns angekuendigten Transaktion
  passen). Ohne eigenen Mempool ist das eine Schaetzung.

Peers heissen peer_N je Lauf; ueber Laeufe hinweg werden sie nicht
zusammengelegt (keine Adressen, also keine Zuordnung).

  python3 scripts/bch/lauscher_auswertung.py --laeufe <ordner>... --kette kette.csv.gz \\
      --aus zusammenfassung.json --csv bloecke.csv
"""
import argparse
import csv
import gzip
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

TYPEN = ("inv", "headers", "cmpctblock")


def jsonl(pfad):
    if not os.path.exists(pfad):
        return []
    with (gzip.open(pfad, "rt") if pfad.endswith(".gz") else open(pfad)) as f:
        return [json.loads(z) for z in f if z.strip()]


def datei(ordner, name):
    gz = os.path.join(ordner, name + ".jsonl.gz")
    return gz if os.path.exists(gz) else os.path.join(ordner, name + ".jsonl")


def iso_ms(t_ms):
    return datetime.fromtimestamp(t_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{t_ms % 1000:03d}Z"


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zs(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def kennzahlen(werte, nk=1):
    """Wie bei rufitnes: Perzentile nach dem naechsten Rang."""
    if not werte:
        return {"n": 0}
    s = sorted(werte)
    rang = lambda q: s[max(0, math.ceil(q * len(s)) - 1)]
    return {"n": len(s), "mittel": round(sum(s) / len(s), nk), "median": round(rang(0.5), nk),
            "p90": round(rang(0.9), nk), "p99": round(rang(0.99), nk), "min": round(s[0], nk), "max": round(s[-1], nk)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laeufe", nargs="+", required=True)
    ap.add_argument("--kette", required=True)
    ap.add_argument("--aus", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--bestaetigungen", type=int, default=6)
    args = ap.parse_args()

    # Laeufe zusammenlegen; Peer-Labels bekommen den Lauf vorangestellt
    ev, koepfe, cmpct, metas = [], {}, [], []
    for o in sorted(args.laeufe):
        lauf = os.path.basename(os.path.normpath(o))
        m = json.load(open(os.path.join(o, "meta.json")))
        m["lauf"] = lauf
        metas.append(m)
        ev += [dict(e, peer=f"{lauf}/{e['peer']}") for e in jsonl(datei(o, "ereignisse"))]
        cmpct += [dict(c, peer=f"{lauf}/{c['peer']}") for c in jsonl(datei(o, "compact"))]
        for k in jsonl(datei(o, "koepfe")):
            koepfe.setdefault(k["hash"], k)
    fenster = [(zs(m["start_utc"]), zs(m["ende_utc"])) for m in metas]

    kette_h, kette_t, nach_h = {}, {}, {}
    with gzip.open(args.kette, "rt") as f:
        for z in csv.DictReader(f):
            h = int(z["hoehe"])
            kette_h[z["hash"]], kette_t[z["hash"]], nach_h[h] = h, int(z["zeit"]), z["hash"]
    spitze = max(nach_h)

    # erste Ankuendigung je Block: gesamt, je Typ, je Peer
    erste = defaultdict(lambda: {"gesamt": None, "typ": None, **{t: None for t in TYPEN}, "peers": {}})
    for e in sorted(ev, key=lambda e: e["t_ms"]):
        d = erste[e["hash"]]
        if d["gesamt"] is None:
            d["gesamt"], d["typ"] = e["t_ms"], e["art"]
        if d[e["art"]] is None:
            d[e["art"]] = e["t_ms"]
        d["peers"].setdefault(e["peer"], e["t_ms"])
    cb = defaultdict(list)
    for c in cmpct:
        cb[c["hash"]].append(c)

    # eine Zeile je Kettenblock, dessen Kopfzeit in einem Lauf-Fenster liegt
    zeilen = []
    for h in sorted(nach_h):
        x = nach_h[h]
        t = kette_t[x]
        if not any(a <= t <= b for a, b in fenster) and x not in erste:
            continue
        d = erste.get(x)
        c = cb.get(x, [])
        c0 = min(c, key=lambda y: y["t_ms"]) if c else None
        peers_t = list(d["peers"].values()) if d else []
        vor = nach_h.get(h - 1)
        zeilen.append({
            "height": h, "hash": x, "header_time_utc": iso(t),
            "interval_s": t - kette_t[vor] if vor else "",
            "first_seen_utc": iso_ms(d["gesamt"]) if d else "",
            "first_seen_type": d["typ"] if d else "",
            **{f"first_{ty}_utc": (iso_ms(d[ty]) if d and d[ty] else "") for ty in TYPEN},
            "timestamp_deviation_s": round(d["gesamt"] / 1000 - t, 3) if d else "",
            "propagation_spread_ms": (max(peers_t) - min(peers_t)) if len(peers_t) >= 2 else "",
            "peers_announced": len(peers_t),
            "cmpctblock": "yes" if c else "no",
            "cmpctblock_unsolicited_peers": sum(1 for y in c if y["von_selbst"]),
            "short_ids": c0["kurz_ids"] if c0 else "",
            "prefilled": c0["vorbefuellt"] if c0 else "",
            "missing_tx_estimate": c0["fehlend_geschaetzt"] if c0 else "",
        })
    spalten = list(zeilen[0].keys()) if zeilen else ["height"]
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=spalten, lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)

    # Stale: angekuendigt, nicht in der Kette, Kette reicht 6 Bloecke darueber
    def hoehe_von(x, tiefe=0):
        k = koepfe.get(x)
        if not k or tiefe > 50:
            return None
        if k["prev"] in kette_h:
            return kette_h[k["prev"]] + 1
        hv = hoehe_von(k["prev"], tiefe + 1)
        return hv + 1 if hv is not None else None

    stale, offen, ohne_kopf = [], 0, 0
    for x, d in erste.items():
        if x in kette_h:
            continue
        hv = hoehe_von(x)
        if hv is None:
            ohne_kopf += 1
            continue
        if hv > spitze - args.bestaetigungen:
            offen += 1
            continue
        stale.append({"height": hv, "hash": x, "header_time_utc": iso(koepfe[x]["zeit"]),
                      "first_seen_utc": iso_ms(d["gesamt"]), "first_seen_type": d["typ"],
                      "peers_announced": len(d["peers"]),
                      "canonical_hash_at_height": nach_h.get(hv)})
    stale.sort(key=lambda s: s["height"])

    gesehen = [z for z in zeilen if z["first_seen_utc"]]
    mit_cb = [z for z in gesehen if z["cmpctblock"] == "yes"]
    out = {
        "art": "ein Zuhoerer, kein eigener Knoten, ein Netzwerkpfad",
        "laeufe": [{k: m.get(k) for k in ("lauf", "start_utc", "ende_utc", "peers_ohne_abzweig_abgelehnt")}
                   | {"peers": len(m["peers"])} for m in metas],
        "abgedeckt_h": round(sum(b - a for a, b in fenster) / 3600, 1),
        "peer_software": sorted({p["software"] for m in metas for p in m["peers"]}),
        "kette_spitze": spitze,
        "kettenbloecke": len(zeilen),
        "davon_angekuendigt_gesehen": len(gesehen),
        "first_seen_typ": {t: sum(1 for z in gesehen if z["first_seen_type"] == t) for t in TYPEN},
        "timestamp_deviation_s": kennzahlen([z["timestamp_deviation_s"] for z in gesehen], 3),
        "propagation_spread_ms": kennzahlen([z["propagation_spread_ms"] for z in gesehen
                                             if z["propagation_spread_ms"] != ""], 0),
        "peers_je_block": kennzahlen([z["peers_announced"] for z in gesehen], 1),
        "compact": {
            "bloecke_mit_cmpctblock": len(mit_cb),
            "davon_von_selbst": sum(1 for z in mit_cb if z["cmpctblock_unsolicited_peers"]),
            "kurz_ids": kennzahlen([z["short_ids"] for z in mit_cb], 1),
            "fehlend_geschaetzt": kennzahlen([z["missing_tx_estimate"] for z in mit_cb], 1),
            "bloecke_ohne_fehlende": sum(1 for z in mit_cb if z["missing_tx_estimate"] == 0),
            "hinweis": "geschaetzt gegen die bei uns per inv angekuendigten Transaktionen, kein eigener Mempool",
        },
        "stale": {"anzahl": len(stale), "bestaetigungen": args.bestaetigungen,
                  "anteil_prozent": round(100 * len(stale) / (len(gesehen) + len(stale)), 3) if gesehen else None,
                  "noch_offen_unter_6": offen, "ohne_kopf": ohne_kopf, "bloecke": stale},
    }
    with open(args.aus, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("kettenbloecke", "davon_angekuendigt_gesehen", "first_seen_typ")}
                     | {"stale": len(stale), "cmpct": len(mit_cb)}))


if __name__ == "__main__":
    main()
