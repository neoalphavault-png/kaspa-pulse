#!/usr/bin/env python3
"""lauscher_auswertung.py - wertet den Zuhoerer (testnet_lauscher.py) aus.

Eingang: Ankuendigungen (jsonl), gesammelte Koepfe (jsonl), Meta des
Zuhoerers und die Kette aus testnet_koepfe.py (csv.gz), abgerufen NACH dem
Ende des Zuhoerens.

Festlegungen:
- Abgehaengt: ein angekuendigter Block-Hash, der nicht in der spaeter
  abgerufenen Kette steht. Hoehe ueber den Vorgaenger: liegt er in der
  Kette, ist der Block dessen Hoehe + 1; liegt er selbst unter den
  abgehaengten, eins mehr als dieser.
- Tiefe eines abgehaengten Zweigs: Anzahl Bloecke im Zweig (1 = ein
  einzelner Block an der Spitze ersetzt).
- Ankunft: erste Ankuendigung eines Blocks je Peer. Abstand Zakura - Zebra
  = erste Ankuendigung durch irgendeinen Zakura-Peer minus erste durch
  irgendeinen Zebra-Peer, nur fuer Bloecke, die beide angekuendigt haben.
- Alles aus Sicht EINES Zuhoerers. Die Ankunftszeit enthaelt den Weg vom
  Knoten zu uns.

  python3 scripts/zcash/lauscher_auswertung.py --ereignisse e.jsonl --koepfe k.jsonl \
      --meta m.json --kette data/zcash/testnet-koepfe.csv.gz --aus data/zcash/lauscher-2026-10-17.json
"""
import argparse
import csv
import gzip
import json
import math
from collections import defaultdict
from datetime import datetime, timezone


def quantil(s, q):
    if not s:
        return None
    s = sorted(s)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 1)


def jsonl(pfad):
    with (gzip.open(pfad, "rt") if pfad.endswith(".gz") else open(pfad)) as f:
        return [json.loads(z) for z in f if z.strip()]


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ereignisse", required=True)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--kette", required=True)
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()

    meta = json.load(open(args.meta))
    ev = jsonl(args.ereignisse)
    koepfe = {k["hash"]: k for k in jsonl(args.koepfe)}
    sw_von = {p["peer"]: p["peer"].split("-")[0] for p in meta["peers"]}

    kette_h, kette_t = {}, {}
    with gzip.open(args.kette, "rt") as f:
        for z in csv.DictReader(f):
            kette_h[z["hash"]] = int(z["hoehe"])
            kette_t[z["hash"]] = int(z["zeit"])

    t0 = datetime.strptime(meta["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    t1 = datetime.strptime(meta["ende_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()

    # erste Ankuendigung je (hash, peer)
    erste = defaultdict(dict)
    for e in ev:
        d = erste[e["hash"]]
        if e["peer"] not in d or e["t_ms"] < d[e["peer"]]:
            d[e["peer"]] = e["t_ms"]

    # Kettenbloecke im Fenster: Zeitstempel zwischen Start und Ende
    im_fenster = [h for h, t in kette_t.items() if t0 <= t <= t1]
    gesehen_in_kette = [h for h in im_fenster if h in erste]

    # Abgehaengte Bloecke
    fremd = [h for h in erste if h not in kette_h]
    abgehaengt = []
    for h in fremd:
        k = koepfe.get(h)
        eintrag = {"hash": h, "erste_ankuendigung_utc": utc(min(erste[h].values()) / 1000),
                   "angekuendigt_von": sorted({sw_von.get(p, "?") for p in erste[h]}),
                   "anzahl_peers": len(erste[h])}
        if k:
            eintrag.update({"vorgaenger": k["prev"], "zeitstempel_utc": utc(k["zeit"]), "nbits": k["nbits"]})
        abgehaengt.append(eintrag)
    nach_hash = {a["hash"]: a for a in abgehaengt}

    def hoehe(a, tiefe=0):
        if "hoehe" in a or tiefe > 50:
            return a.get("hoehe")
        v = a.get("vorgaenger")
        if v in kette_h:
            a["hoehe"] = kette_h[v] + 1
        elif v in nach_hash:
            hv = hoehe(nach_hash[v], tiefe + 1)
            a["hoehe"] = hv + 1 if hv is not None else None
        else:
            a["hoehe"] = None
        return a["hoehe"]

    for a in abgehaengt:
        hoehe(a)
    # Zweige: von einem Block, dessen Vorgaenger in der Kette liegt, so weit wie moeglich
    kinder = defaultdict(list)
    for a in abgehaengt:
        kinder[a.get("vorgaenger")].append(a["hash"])

    def laenge(h):
        return 1 + max((laenge(c) for c in kinder.get(h, [])), default=0)

    zweige = [{"abzweig_hoehe": kette_h[a["vorgaenger"]], "tiefe": laenge(a["hash"])}
              for a in abgehaengt if a.get("vorgaenger") in kette_h]
    ohne_kopf = sum(1 for a in abgehaengt if "vorgaenger" not in a)

    # Ankunft Zebra gegen Zakura, Streuung ueber alle Peers
    diff_ms, streu_ms, nach_zeitstempel_s = [], [], []
    zakura_zuerst = 0
    for h in gesehen_in_kette:
        d = erste[h]
        zb = [t for p, t in d.items() if sw_von.get(p) == "zebra"]
        zk = [t for p, t in d.items() if sw_von.get(p) == "zakura"]
        if zb and zk:
            diff_ms.append(min(zk) - min(zb))
            zakura_zuerst += min(zk) < min(zb)
        if len(d) >= 2:
            streu_ms.append(max(d.values()) - min(d.values()))
        nach_zeitstempel_s.append(min(d.values()) / 1000 - kette_t[h])

    peers_sw = defaultdict(int)
    ank_sw = defaultdict(int)
    for p in meta["peers"]:
        peers_sw[sw_von[p["peer"]]] += 1
        ank_sw[sw_von[p["peer"]]] += p["ankuendigungen"]

    out = {
        "art": "ein Zuhoerer, kein eigener Knoten",
        "fenster_utc": [meta["start_utc"], meta["ende_utc"]],
        # Tatsaechlich abgedeckt: erste bis letzte Ankuendigung. Faellt der
        # Zuhoerer still aus, ist das kuerzer als das Fenster (Pruefung im
        # Endlauf, Ben 15.10.2026: unter 2 h zaehlt D als nicht gemessen).
        "erste_ankuendigung_utc": utc(min(e["t_ms"] for e in ev) / 1000) if ev else None,
        "letzte_ankuendigung_utc": utc(max(e["t_ms"] for e in ev) / 1000) if ev else None,
        "abgedeckt_min": round((max(e["t_ms"] for e in ev) - min(e["t_ms"] for e in ev)) / 60000, 1) if ev else 0,
        "peers_je_software": dict(peers_sw),
        "ankuendigungen_je_software": dict(ank_sw),
        "peer_software": sorted({p["software"] for p in meta["peers"]}),
        "kettenbloecke_im_fenster": len(im_fenster),
        "davon_angekuendigt_gesehen": len(gesehen_in_kette),
        "abgehaengt_anzahl": len(abgehaengt),
        "abgehaengt_ohne_kopf": ohne_kopf,
        "zweige": len(zweige),
        "groesste_tiefe": max((z["tiefe"] for z in zweige), default=0),
        "tiefen": sorted((z["tiefe"] for z in zweige), reverse=True)[:20],
        "abgehaengt_beispiele": sorted(abgehaengt, key=lambda a: a["erste_ankuendigung_utc"])[:20],
        "zakura_minus_zebra_ms": {
            "bloecke": len(diff_ms), "median": quantil(diff_ms, 0.5), "p10": quantil(diff_ms, 0.1),
            "p90": quantil(diff_ms, 0.9), "zakura_zuerst": zakura_zuerst,
        },
        "streuung_alle_peers_ms": {"bloecke": len(streu_ms), "median": quantil(streu_ms, 0.5),
                                   "p90": quantil(streu_ms, 0.9), "max": max(streu_ms) if streu_ms else None},
        "erste_ankunft_minus_zeitstempel_s": {"median": quantil(nach_zeitstempel_s, 0.5),
                                              "p90": quantil(nach_zeitstempel_s, 0.9)},
        "zuhoerer_meta": {k: v for k, v in meta.items() if k != "peers"},
        "peers": [{k: p[k] for k in ("peer", "software", "verbunden_utc", "getrennt_utc", "ankuendigungen") if k in p}
                  for p in meta["peers"]],
    }
    with open(args.aus, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("kettenbloecke_im_fenster", "davon_angekuendigt_gesehen",
                                          "abgehaengt_anzahl", "groesste_tiefe")}))


if __name__ == "__main__":
    main()
