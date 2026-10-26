#!/usr/bin/env python3
"""chipnet_auswertung.py - BCH chipnet, Blockabstaende gezaehlt gegen berechnet.

Ben, 26.10.2026: Kennzahlen seit 01.10.2026 aus unseren eigenen Koepfen
(chipnet_koepfe.py): Abstaende (Mittel, Median, p90, p99, Anteil ueber 5 min,
laengste Luecke), Anteil der Bloecke mit Mindestschwierigkeit, MTP-Abstand.
Dazu die Wartezeit ab einem zufaelligen Zeitpunkt bis zum naechsten Block, die
fuer XO zaehlt (wie lange eine Einloesung im unguenstigen Fall wartet).

Berechnet (computed) fuer eine ideale Kette mit Zielabstand T (chipnet heute
600 s, BCHN chainparams nPowTargetSpacing = 10 * 60): Abstaende exponentiell,
Median T ln 2, Quantil q bei -T ln(1-q), Anteil ueber x bei exp(-x/T),
erwartete laengste Luecke unter n Abstaenden T (ln n + 0,5772). Die Wartezeit
ab einem zufaelligen Zeitpunkt ist bei exponentiellen Abstaenden genauso
verteilt wie ein Abstand. MTP-Abstand per Simulation (feste Saat 2027).
Die chipnet-Regel fuer Mindestschwierigkeit (fPowAllowMinDifficultyBlocks,
nach 2 x T ohne Block) ist im berechneten Modell nicht enthalten.

Mindestschwierigkeit: nBits = 0x1d00ffff (powLimit von chipnet).

  python3 scripts/bch/chipnet_auswertung.py --koepfe k.csv.gz --meta m.json --ab 2026-10-01 \\
      --json chipnet.json --md chipnet.md
"""
import argparse
import bisect
import csv
import gzip
import json
import math
import random
import statistics
from datetime import datetime, timezone

POW_LIMIT_BITS = 0x1D00FFFF
EULER = 0.5772156649


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(s, q):
    s = sorted(s)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def kennzahlen(werte):
    return {"n": len(werte), "mittel": round(statistics.fmean(werte), 1), "median": round(statistics.median(werte), 1),
            "p90": round(quantil(werte, 0.9), 1), "p99": round(quantil(werte, 0.99), 1),
            "min": min(werte), "max": max(werte)}


def mtp_simulation(T, n=200_000, saat=2027):
    rnd = random.Random(saat)
    t, zeiten, verzug = 0.0, [], []
    for _ in range(n):
        t += rnd.expovariate(1 / T)
        if len(zeiten) >= 11:
            verzug.append(t - statistics.median(zeiten[-11:]))
        zeiten.append(t)
    return {"median": round(statistics.median(verzug), 1), "p90": round(quantil(verzug, 0.9), 1),
            "p99": round(quantil(verzug, 0.99), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--ab", default="2026-10-01", help="UTC-Tag, ab dem gezaehlt wird")
    ap.add_argument("--ziel", type=float, default=600.0)
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()
    T = args.ziel
    meta = json.load(open(args.meta))
    with gzip.open(args.koepfe, "rt") as f:
        z = sorted((int(r["hoehe"]), int(r["zeit"]), int(r["nbits"], 16)) for r in csv.DictReader(f))
    ab = datetime.strptime(args.ab, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    zt = {h: t for h, t, _ in z}
    bl = [(h, t, b) for h, t, b in z if t >= ab and h - 1 in zt]
    ab_ = [t - zt[h - 1] for h, t, _ in bl]
    n = len(ab_)
    h_max, t_max, _ = max(bl, key=lambda x: x[1] - zt[x[0] - 1])
    mindest = [(h, t) for h, t, b in bl if b == POW_LIMIT_BITS]
    # MTP-Abstand: Zeitstempel minus Median der 11 Bloecke davor
    hs = [h for h, _, _ in z]
    verzug = []
    for h, t, _ in bl:
        vor = [zt[x] for x in range(h - 11, h) if x in zt]
        if len(vor) == 11:
            verzug.append(t - statistics.median(vor))
    spitze_h, spitze_t = z[-1][0], z[-1][1]
    mtp_spitze = statistics.median([zt[x] for x in range(spitze_h - 10, spitze_h + 1)])
    abruf = datetime.strptime(meta["abruf_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    # Wartezeit ab zufaelligem Zeitpunkt bis zum naechsten Block (Raster 10 s ueber das Fenster)
    zeiten = [t for _, t, _ in bl]
    warte = []
    t = zeiten[0]
    while t < zeiten[-1]:
        i = bisect.bisect_right(zeiten, t)
        warte.append(zeiten[i] - t)
        t += 10
    # je Woche (ISO)
    wochen = {}
    for (h, t, b), a in zip(bl, ab_):
        j, k, _ = datetime.fromtimestamp(t, timezone.utc).isocalendar()
        w = wochen.setdefault(f"{j}-W{k:02d}", {"a": [], "m": 0})
        w["a"].append(a)
        w["m"] += b == POW_LIMIT_BITS
    r = {
        "netz": "bch chipnet", "quelle": "eigene header ueber p2p (chipnet_koepfe.py)",
        "abruf_utc": meta["abruf_utc"], "peer_software": meta.get("peer_software"),
        "gegenproben": [{k: g[k] for k in ("agent", "verglichen", "gleich")} for g in meta.get("gegenproben", [])],
        "pruefungen": meta.get("pruefungen"), "checkpoints_geprueft": meta.get("checkpoints_geprueft"),
        "proben_tempnet_oder_ohne_antwort": meta.get("proben_tempnet_oder_ohne_antwort"),
        "bereich": {"ab_utc": utc(bl[0][1]), "bis_utc": utc(bl[-1][1]), "von_hoehe": bl[0][0], "bis_hoehe": bl[-1][0],
                    "abstaende": n},
        "zielabstand_s": T,
        "counted": {
            "abstaende_s": kennzahlen(ab_),
            "anteil_ueber_5min_prozent": round(100 * sum(a > 300 for a in ab_) / n, 2),
            "anteil_ueber_2T_prozent": round(100 * sum(a > 2 * T for a in ab_) / n, 2),
            "laengste_luecke_s": t_max - zt[h_max - 1], "laengste_luecke_vor_block": h_max,
            "laengste_luecke_utc": utc(t_max),
            "negativ": sum(a < 0 for a in ab_),
            "mindestschwierigkeit": {"bloecke": len(mindest), "anteil_prozent": round(100 * len(mindest) / n, 2)},
            "mtp_abstand_s": {"median": round(statistics.median(verzug), 1), "p90": round(quantil(verzug, 0.9), 1),
                              "p99": round(quantil(verzug, 0.99), 1)},
            "abruf_minus_mtp_spitze_s": round(abruf - mtp_spitze), "abruf_minus_spitze_s": round(abruf - spitze_t),
            "wartezeit_ab_zufallszeitpunkt_s": {"median": round(statistics.median(warte), 1),
                                                "p90": round(quantil(warte, 0.9), 1), "p99": round(quantil(warte, 0.99), 1),
                                                "raster_s": 10},
        },
        "computed": {
            "mittel_s": T, "median_s": round(T * math.log(2), 1), "p90_s": round(T * math.log(10), 1),
            "p99_s": round(T * math.log(100), 1),
            "anteil_ueber_5min_prozent": round(100 * math.exp(-300 / T), 2),
            "anteil_ueber_2T_prozent": round(100 * math.exp(-2), 2),
            "laengste_luecke_s": round(T * (math.log(n) + EULER)),
            "mtp_abstand_s": mtp_simulation(T),
            "wartezeit_ab_zufallszeitpunkt_s": {"median": round(T * math.log(2), 1), "p90": round(T * math.log(10), 1),
                                                "p99": round(T * math.log(100), 1)},
            "hinweis": "ideale kette, exponentielle abstaende, ohne die mindestschwierigkeits-regel",
        },
        "je_woche": [{"woche": k, "abstaende": len(v["a"]), "mittel_s": round(statistics.fmean(v["a"]), 1),
                      "median_s": round(statistics.median(v["a"]), 1), "mindest": v["m"]} for k, v in sorted(wochen.items())],
    }
    with open(args.json, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
        f.write("\n")
    c, b = r["counted"], r["computed"]
    A = c["abstaende_s"]
    zeilen = [
        f"Bereich {r['bereich']['von_hoehe']:,} bis {r['bereich']['bis_hoehe']:,} ({r['bereich']['ab_utc']} bis "
        f"{r['bereich']['bis_utc']} UTC), {n:,} Abstände, Zielabstand {T:.0f} s.", "",
        "| Kennzahl | counted | computed |", "|---|---:|---:|",
        f"| Mittel | {A['mittel']} s | {b['mittel_s']:.0f} s |",
        f"| Median | {A['median']} s | {b['median_s']} s |",
        f"| p90 | {A['p90']} s | {b['p90_s']} s |",
        f"| p99 | {A['p99']} s | {b['p99_s']} s |",
        f"| Anteil über 5 min | {c['anteil_ueber_5min_prozent']} % | {b['anteil_ueber_5min_prozent']} % |",
        f"| Anteil über 20 min (2 × Ziel) | {c['anteil_ueber_2T_prozent']} % | {b['anteil_ueber_2T_prozent']} % |",
        f"| Längste Lücke | {c['laengste_luecke_s']} s (vor Block {c['laengste_luecke_vor_block']:,}, {c['laengste_luecke_utc']} UTC) | {b['laengste_luecke_s']} s |",
        f"| Blöcke mit Mindestschwierigkeit | {c['mindestschwierigkeit']['bloecke']:,} ({c['mindestschwierigkeit']['anteil_prozent']} %) | im Modell 0 |",
        f"| MTP-Abstand Median / p90 / p99 | {c['mtp_abstand_s']['median']} / {c['mtp_abstand_s']['p90']} / {c['mtp_abstand_s']['p99']} s | "
        f"{b['mtp_abstand_s']['median']} / {b['mtp_abstand_s']['p90']} / {b['mtp_abstand_s']['p99']} s |",
        f"| Wartezeit ab Zufallszeitpunkt Median / p90 / p99 | {c['wartezeit_ab_zufallszeitpunkt_s']['median']} / "
        f"{c['wartezeit_ab_zufallszeitpunkt_s']['p90']} / {c['wartezeit_ab_zufallszeitpunkt_s']['p99']} s | "
        f"{b['wartezeit_ab_zufallszeitpunkt_s']['median']} / {b['wartezeit_ab_zufallszeitpunkt_s']['p90']} / "
        f"{b['wartezeit_ab_zufallszeitpunkt_s']['p99']} s |",
        f"| Negative Abstände | {c['negativ']} | 0 |", "",
        "| ISO-Woche | Abstände | Mittel | Median | Mindestschwierigkeit |", "|---|---:|---:|---:|---:|",
    ] + [f"| {w['woche']} | {w['abstaende']:,} | {w['mittel_s']} s | {w['median_s']} s | {w['mindest']} |" for w in r["je_woche"]]
    with open(args.md, "w") as f:
        f.write("\n".join(zeilen) + "\n")
    print(json.dumps({"abstaende": n, "median": A["median"], "p99": A["p99"],
                      "mindest_prozent": c["mindestschwierigkeit"]["anteil_prozent"]}))


if __name__ == "__main__":
    main()
