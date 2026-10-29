#!/usr/bin/env python3
"""build_wechsel.py - BCH Tempnet vor und nach dem Build-Wechsel von 9500 (Ben, 30.10.2026).

Laut Forum (cculianu, 29.10.2026) hatte der Build von 9500 P2P-Netzwerkfehler;
9500 hat am 29.10. auf den Stand von wip2 gezogen. Dieses Skript

1. listet je Lauf des Zuhoerers die Software-Kennungen der Peers (User-Agent und
   Protokollversion aus dem version-Handschlag, wie sie in meta.json stehen;
   keine Adressen),
2. sucht den Zeitpunkt, ab dem kein Peer mehr den alten Build meldet. Zwei Wege:
   a) eine neue Kennung ersetzt die alte (--alt), dann zaehlt die letzte
      Verbindung mit der alten Kennung;
   b) die Kennung bleibt gleich: ein neuer Build heisst Neustart des Knotens,
      dann reissen alle unsere Verbindungen mit dieser Kennung binnen weniger
      Minuten ab. Gemeldet wird jeder solche gemeinsame Abbruch.
   Mit --wechsel kann der Zeitpunkt auch von Hand gesetzt werden.
3. wertet vor und nach dem Zeitpunkt getrennt aus: erste Ankuendigung je Block
   (timestamp_deviation, propagation_spread, Peers je Block, welche Kennung
   zuerst ankuendigte), angekuendigte Bloecke, die nie in die Kette kamen
   (stale nach 6 Bestaetigungen), Median und p90 der Blockabstaende.

Eingang: der Ordner data/bch/lauscher (Laeufe mit meta.json und
ereignisse.jsonl.gz, dazu bloecke.csv und zusammenfassung.json der letzten
Auswertung ueber alle Laeufe mit frischer Kette).

  python3 scripts/bch/build_wechsel.py --lauscher data/bch/lauscher --alt 9500-tempnet --ab 2026-10-29T00:00:00Z \\
      --json data/bch/build-wechsel.json --md data/bch/build-wechsel.md [--wechsel 2026-10-29T22:00:00Z]

Lauf 30.10.2026 auf den Daten bis 29.10. 21:12 UTC: ein gemeinsamer Abbruch aller
9500-Verbindungen am 26.10. 08:30:51 UTC (frueherer Neustart), seit dem 29.10.
keiner; die Kennung blieb gleich.
"""
import argparse
import csv
import glob
import gzip
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

ABBRUCH_FENSTER_S = 180


def ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(s, q):
    s = sorted(s)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def laeufe_lesen(ordner):
    out = []
    for d in sorted(glob.glob(os.path.join(ordner, "2*"))):
        m = json.load(open(os.path.join(d, "meta.json")))
        out.append((os.path.basename(d), d, m))
    return out


def kennungen(laeufe, alt):
    zeilen, alt_letzte, abbrueche = [], None, []
    for name, _, m in laeufe:
        ende = ts(m["ende_utc"])
        c = Counter((p["software"], p["version"]) for p in m["peers"])
        zeilen.append({"lauf": name, "start_utc": m["start_utc"], "ende_utc": m["ende_utc"],
                       "kennungen": [{"software": s, "protokoll": v, "verbindungen": n} for (s, v), n in sorted(c.items())]})
        for p in m["peers"]:
            if alt in p["software"]:
                bis = ts(p["getrennt_utc"]) if p.get("getrennt_utc") else ende
                alt_letzte = max(alt_letzte or 0, bis)
        # gemeinsamer Abbruch: alle Verbindungen mit der Kennung, die vor dem
        # Laufende getrennt wurden, liegen binnen ABBRUCH_FENSTER_S
        je = defaultdict(list)
        for p in m["peers"]:
            if p.get("getrennt_utc") and ts(p["getrennt_utc"]) < ende - 60:
                je[p["software"]].append(ts(p["getrennt_utc"]))
        for sw, zeiten in je.items():
            alle = [p for p in m["peers"] if p["software"] == sw
                    and ts(p["verbunden_utc"]) <= min(zeiten)]
            if len(zeiten) >= 2 and max(zeiten) - min(zeiten) <= ABBRUCH_FENSTER_S and len(zeiten) >= len(alle):
                abbrueche.append({"lauf": name, "software": sw, "verbindungen": len(zeiten),
                                  "von_utc": utc(min(zeiten)), "bis_utc": utc(max(zeiten))})
    return zeilen, alt_letzte, abbrueche


def erste_ankuendiger(laeufe):
    """hash -> (t_ms, software des ersten Ankuendigers)"""
    erst = {}
    for _, d, m in laeufe:
        sw = {p["peer"]: p["software"] for p in m["peers"]}
        with gzip.open(os.path.join(d, "ereignisse.jsonl.gz"), "rt") as f:
            for z in f:
                e = json.loads(z)
                if e["hash"] not in erst or e["t_ms"] < erst[e["hash"]][0]:
                    erst[e["hash"]] = (e["t_ms"], sw.get(e["peer"], "?"))
    return erst


def seite(bloecke, stale, erst, von, bis, alt):
    b = [z for z in bloecke if von <= ts(z["first_seen_utc"]) < bis]
    s = [z for z in stale if von <= ts(z["first_seen_utc"]) < bis]
    if not b:
        return None
    ab = [int(z["interval_s"]) for z in b if z["interval_s"] not in ("", None)]
    dev = [float(z["timestamp_deviation_s"]) for z in b if z["timestamp_deviation_s"]]
    spr = [int(z["propagation_spread_ms"]) for z in b if z["propagation_spread_ms"]]
    peers = [int(z["peers_announced"]) for z in b if z["peers_announced"]]
    zuerst = Counter(erst[z["hash"]][1] for z in b if z["hash"] in erst)
    st_zuerst = Counter(erst[z["hash"]][1] for z in s if z["hash"] in erst)
    r = lambda x, n=1: None if x is None else round(x, n)
    return {
        "fenster_utc": [utc(von), utc(bis)],
        "kettenbloecke": len(b), "hoehen": [int(b[0]["height"]), int(b[-1]["height"])],
        "abstaende": {"n": len(ab), "median_s": r(quantil(ab, 0.5)), "p90_s": r(quantil(ab, 0.9))},
        "timestamp_deviation_s": {"median": r(quantil(dev, 0.5), 2), "p90": r(quantil(dev, 0.9), 2),
                                  "p99": r(quantil(dev, 0.99), 2)},
        "propagation_spread_ms": {"median": r(quantil(spr, 0.5), 0), "p90": r(quantil(spr, 0.9), 0)},
        "peers_je_block_median": r(quantil(peers, 0.5), 0),
        "zuerst_angekuendigt_von": dict(zuerst.most_common()),
        "anteil_zuerst_alt_prozent": r(100 * sum(n for k, n in zuerst.items() if alt in k) / max(1, sum(zuerst.values()))),
        "stale": {"anzahl": len(s), "anteil_prozent": r(100 * len(s) / (len(b) + len(s)), 2),
                  "zuerst_von": dict(st_zuerst.most_common()),
                  "bloecke": [{"hoehe": z["height"], "hash": z["hash"], "first_seen_utc": z["first_seen_utc"],
                               "peers": z["peers_announced"]} for z in s]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lauscher", required=True)
    ap.add_argument("--alt", default="9500-tempnet", help="Teil der Kennung des alten Builds")
    ap.add_argument("--wechsel", help="Zeitpunkt UTC von Hand, sonst aus den Daten")
    ap.add_argument("--ab", help="Wechsel fruehestens ab diesem Zeitpunkt UTC suchen (Forum: 29.10.2026)")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()

    laeufe = laeufe_lesen(args.lauscher)
    zeilen, alt_letzte, abbrueche = kennungen(laeufe, args.alt)
    ab = ts(args.ab) if args.ab else 0
    alt_abbrueche = [a for a in abbrueche if args.alt in a["software"]
                     and ts(a["von_utc"].replace(" ", "T") + "Z") >= ab]
    neue = sorted({k["software"] for z in zeilen for k in z["kennungen"]})
    ende_daten = ts(laeufe[-1][2]["ende_utc"])

    if args.wechsel:
        wechsel, grund = ts(args.wechsel), "von Hand gesetzt"
    elif alt_letzte and ab <= alt_letzte < ende_daten - 600:
        wechsel, grund = alt_letzte, f"letzte Verbindung mit '{args.alt}'"
    elif alt_abbrueche:
        wechsel = ts(alt_abbrueche[-1]["bis_utc"].replace(" ", "T") + "Z")
        grund = f"gemeinsamer Abbruch aller Verbindungen mit '{args.alt}' (Neustart)"
    else:
        wechsel, grund = None, f"kein Wechsel erkennbar: '{args.alt}' bis zum Ende der Daten verbunden, kein gemeinsamer Abbruch"

    with open(os.path.join(args.lauscher, "bloecke.csv")) as f:
        bloecke = list(csv.DictReader(f))
    zus = json.load(open(os.path.join(args.lauscher, "zusammenfassung.json")))
    stale = zus["stale"]["bloecke"]
    for z in stale:
        z.setdefault("first_seen_utc", z.get("first_seen_utc"))
    erst = erste_ankuendiger(laeufe)

    start = ts(laeufe[0][2]["start_utc"])
    r = {"alt": args.alt, "kennungen_gesamt": neue, "laeufe": zeilen, "gemeinsame_abbrueche": abbrueche,
         "alt_zuletzt_verbunden_utc": utc(alt_letzte) if alt_letzte else None,
         "daten_bis_utc": utc(ende_daten), "wechsel_utc": utc(wechsel) if wechsel else None, "wechsel_grund": grund,
         "vorher": seite(bloecke, stale, erst, start, wechsel or ende_daten, args.alt),
         "nachher": seite(bloecke, stale, erst, wechsel, ende_daten, args.alt) if wechsel else None}
    with open(args.json, "w") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)

    md = [f"# BCH Tempnet, Build-Wechsel '{args.alt}'", "",
          f"Daten bis {r['daten_bis_utc']} UTC. Wechsel: {r['wechsel_utc'] or 'nicht erkennbar'} ({grund}).", "",
          "| Kennung | Protokoll | erster Lauf | letzter Lauf |", "|---|---|---|---|"]
    erst_l, letzt_l = {}, {}
    for z in zeilen:
        for k in z["kennungen"]:
            key = (k["software"], k["protokoll"])
            erst_l.setdefault(key, z["start_utc"])
            letzt_l[key] = z["ende_utc"]
    for (sw, v) in sorted(erst_l):
        md.append(f"| `{sw}` | {v} | {erst_l[(sw, v)]} | {letzt_l[(sw, v)]} |")
    if abbrueche:
        md += ["", "Gemeinsame Abbrueche (alle Verbindungen einer Kennung binnen 3 min):"]
        md += [f"- {a['software']}: {a['verbindungen']} Verbindungen, {a['von_utc']} bis {a['bis_utc']} UTC" for a in abbrueche]
    for name in ("vorher", "nachher"):
        s = r[name]
        if not s:
            continue
        md += ["", f"## {name}, {s['fenster_utc'][0]} bis {s['fenster_utc'][1]} UTC", "",
               f"- Kettenbloecke {s['kettenbloecke']}, Hoehen {s['hoehen'][0]} bis {s['hoehen'][1]}",
               f"- Abstaende Median {s['abstaende']['median_s']} s, p90 {s['abstaende']['p90_s']} s",
               f"- timestamp_deviation Median {s['timestamp_deviation_s']['median']} s, p90 {s['timestamp_deviation_s']['p90']} s",
               f"- propagation_spread Median {s['propagation_spread_ms']['median']} ms, p90 {s['propagation_spread_ms']['p90']} ms",
               f"- zuerst angekuendigt von '{args.alt}': {s['anteil_zuerst_alt_prozent']} %",
               f"- stale {s['stale']['anzahl']} ({s['stale']['anteil_prozent']} %), zuerst von {s['stale']['zuerst_von']}"]
    with open(args.md, "w") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps({"wechsel_utc": r["wechsel_utc"], "grund": grund,
                      "vorher_bloecke": r["vorher"]["kettenbloecke"] if r["vorher"] else 0,
                      "nachher_bloecke": r["nachher"]["kettenbloecke"] if r["nachher"] else 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
