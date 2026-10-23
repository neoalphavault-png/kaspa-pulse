#!/usr/bin/env python3
"""mainnet_auswertung.py - Zcash Mainnet rund um NU7, gezaehlt gegen berechnet.

Ben, 23.10.2026:
  1. Baseline vor NU7 gegen eine ideale 75-s-Kette: Mittel, Median, p90, p99,
     laengste Luecke.
  2. Vorhersage, wann Hoehe 3.543.405 (NU7) erreicht wird, mit Band.
  3. Ab dem ersten NU7-Block: Abstaende gegen 25 s und wie schnell sich die
     Schwierigkeit nach dem Wechsel einpendelt.

Ideale Kette mit Zielzeit T: Abstaende exponentiell mit Mittel T. Daraus
berechnet: Median T ln 2, Quantil q bei -T ln(1-q), Anteil ueber x bei
exp(-x/T), erwartete laengste Luecke unter n Abstaenden T (ln n + 0,5772).

Vorhersage: N fehlende Bloecke. Das Tempo ist das mittlere Intervall der
letzten 14 vollen UTC-Tage. Band aus 20.000 Ziehungen (Seed 2027): je Ziehung
ein Tempo aus 14 zufaellig gezogenen Tagesmitteln (Bootstrap ueber Tage, deckt
Hashrate-Schwankungen ab), dann die Zeit fuer N Bloecke als Summe von N
exponentiellen Abstaenden mit diesem Tempo (Gamma). Ausgewiesen 5 % bis 95 %.
Zum Vergleich die Rechnung mit genau 75 s.

Zeitstempel sind die der Bloecke (vom Miner gesetzt, durch die Regeln auf
wenige Minuten begrenzt); einzelne Abstaende koennen deshalb negativ sein.

  python3 scripts/zcash/mainnet_auswertung.py --koepfe koepfe.csv.gz --meta koepfe-meta.json \\
      --json stand.json --md stand.md
"""
import argparse
import csv
import gzip
import json
import math
import random
import statistics
from datetime import datetime, timezone

NU7 = 3_543_405
ALT, NEU = 75.0, 25.0
EULER = 0.5772156649
ZAKURA_SCHAETZUNG = "2026-11-06T00:50:00Z"  # laut Zakura, Ben 23.10.2026


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(s, q):
    s = sorted(s)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def ziel_aus_nbits(bits):
    exp, mant = bits >> 24, bits & 0x007FFFFF
    return mant >> (8 * (3 - exp)) if exp <= 3 else mant << (8 * (exp - 3))


def kennzahlen(paare, T):
    """paare: (hoehe, zeit, abstand). Gezaehlt gegen eine ideale Kette mit Zielzeit T."""
    ab = [a for _, _, a in paare]
    n = len(ab)
    h_max, t_max, a_max = max(paare, key=lambda p: p[2])
    return {
        "abstaende": n,
        "gezaehlt": {
            "mittel_s": round(statistics.fmean(ab), 2), "median_s": round(statistics.median(ab), 1),
            "p90_s": round(quantil(ab, 0.9), 1), "p99_s": round(quantil(ab, 0.99), 1),
            "laengste_luecke_s": a_max, "laengste_luecke_vor_block": h_max,
            "laengste_luecke_utc": utc(t_max),
            "anteil_ueber_3T_prozent": round(100 * sum(a > 3 * T for a in ab) / n, 2),
            "anteil_ueber_T_ln1000_prozent": round(100 * sum(a > T * math.log(1000) for a in ab) / n, 3),
            "negativ": sum(a < 0 for a in ab),
        },
        "berechnet": {
            "zielzeit_s": T, "mittel_s": T, "median_s": round(T * math.log(2), 1),
            "p90_s": round(T * math.log(10), 1), "p99_s": round(T * math.log(100), 1),
            "laengste_luecke_s": round(T * (math.log(n) + EULER)),
            "anteil_ueber_3T_prozent": round(100 * math.exp(-3), 2),
            "anteil_ueber_T_ln1000_prozent": 0.1,
        },
    }


def je_woche(paare):
    w = {}
    for _, t, a in paare:
        j, k, _ = datetime.fromtimestamp(t, timezone.utc).isocalendar()
        w.setdefault(f"{j}-W{k:02d}", []).append(a)
    return [{"woche": k, "abstaende": len(v), "mittel_s": round(statistics.fmean(v), 2),
             "median_s": round(statistics.median(v), 1)} for k, v in sorted(w.items())]


def vorhersage(paare, spitze_h, spitze_t, ziel_h, tage=14, ziehungen=20_000):
    fehlend = ziel_h - spitze_h
    if fehlend <= 0:
        return None
    # volle UTC-Tage vor dem Tag der Spitze
    ende = datetime.fromtimestamp(spitze_t, timezone.utc).replace(hour=0, minute=0, second=0).timestamp()
    tag = {}
    for _, t, a in paare:
        if ende - tage * 86400 <= t < ende:
            tag.setdefault(int((t - ende) // 86400), []).append(a)
    mittel = [statistics.fmean(v) for v in tag.values() if len(v) >= 200]
    if len(mittel) < 7:
        return {"fehlend": fehlend, "fehler": f"nur {len(mittel)} volle tage im fenster"}
    tempo = sum(sum(v) for v in tag.values()) / sum(len(v) for v in tag.values())
    rnd = random.Random(2027)
    zeiten = sorted(rnd.gammavariate(fehlend, statistics.fmean(rnd.choices(mittel, k=len(mittel))))
                    for _ in range(ziehungen))
    q = lambda p: spitze_t + zeiten[int(p * (ziehungen - 1))]
    return {
        "zielhoehe": ziel_h, "fehlend": fehlend, "spitze_hoehe": spitze_h, "spitze_utc": utc(spitze_t),
        "tempo_fenster_tage": len(mittel), "tempo_mittel_s": round(tempo, 2),
        "tagesmittel_min_s": round(min(mittel), 1), "tagesmittel_max_s": round(max(mittel), 1),
        "gezaehltes_tempo_utc": utc(spitze_t + fehlend * tempo),
        "median_utc": utc(q(0.5)), "band_5_utc": utc(q(0.05)), "band_95_utc": utc(q(0.95)),
        "band_breite_h": round((q(0.95) - q(0.05)) / 3600, 1),
        "berechnet_75s_utc": utc(spitze_t + fehlend * ALT),
        "zakura_schaetzung_utc": ZAKURA_SCHAETZUNG.replace("T", " ").rstrip("Z"),
        "methode": f"tempo {tage} volle utc-tage, bootstrap ueber tagesmittel, gamma(n, tempo), {ziehungen} ziehungen, seed 2027",
    }


def einpendeln(zeilen, nu7, fenster=100, toleranz=0.2, halten=1000):
    """Ab welchem Block nach NU7 das gleitende Mittel ueber `fenster` Abstaende
    dauerhaft (mindestens `halten` Bloecke, oder bis zur Spitze) in 25 s +- 20 %
    liegt. Dazu die Schwierigkeit relativ zum Mittel der 1.000 Bloecke vor NU7."""
    nach = [z for z in zeilen if z[0] >= nu7]
    if len(nach) < fenster + 1:
        return {"bloecke_nach_nu7": max(0, len(nach) - 1), "hinweis": "zu wenige bloecke fuer das gleitende mittel"}
    vor = [z for z in zeilen if nu7 - 1000 <= z[0] < nu7]
    schw = lambda z: 1 / ziel_aus_nbits(z[2])
    basis = statistics.fmean(schw(z) for z in vor) if vor else None
    ab = [(nach[i][0], nach[i][1] - nach[i - 1][1]) for i in range(1, len(nach))]
    gleit = [(ab[i][0], statistics.fmean(a for _, a in ab[i - fenster + 1:i + 1])) for i in range(fenster - 1, len(ab))]
    innen = [abs(m / NEU - 1) <= toleranz for _, m in gleit]
    ab_hoehe = None
    for i in range(len(gleit)):
        rest = innen[i:i + halten]
        if all(rest) and (len(rest) == halten or i + len(rest) == len(gleit)):
            ab_hoehe = gleit[i][0]
            break
    zeit = {z[0]: z[1] for z in nach}
    out = {"bloecke_nach_nu7": len(nach) - 1, "fenster": fenster, "toleranz_prozent": int(toleranz * 100),
           "halten_bloecke": halten, "eingependelt_ab_block": ab_hoehe}
    if ab_hoehe:
        out["bloecke_bis_eingependelt"] = ab_hoehe - nu7
        out["stunden_bis_eingependelt"] = round((zeit[ab_hoehe] - zeit[nu7]) / 3600, 1)
        out["vorlaeufig"] = len(gleit) - gleit.index(next(g for g in gleit if g[0] == ab_hoehe)) < halten
    if basis:
        stufen = {}
        for k in (1, 10, 100, 1000, 5000):
            z = next((z for z in nach if z[0] == nu7 + k), None)
            if z:
                stufen[f"block_nu7_plus_{k}"] = round(schw(z) / basis, 3)
        out["schwierigkeit_relativ_zu_vor_nu7"] = stufen
        out["schwierigkeit_spitze_relativ"] = round(schw(nach[-1]) / basis, 3)
        out["berechnet_bei_gleicher_hashrate"] = round(NEU / ALT, 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--csv", help="ab NU7: Abstaende als CSV wie beim Testnet (height,timestamp,interval_s)")
    ap.add_argument("--nu7", type=int, default=NU7, help="nur fuer Tests mit Testnet-Daten")
    args = ap.parse_args()
    meta = json.load(open(args.meta))
    with gzip.open(args.koepfe, "rt") as f:
        zeilen = [(int(z["hoehe"]), int(z["zeit"]), int(z["nbits"], 16)) for z in csv.DictReader(f)]
    zeilen.sort()
    zt = {h: t for h, t, _ in zeilen}
    erste, spitze = zeilen[0][0], zeilen[-1][0]
    paare = [(h, zt[h], zt[h] - zt[h - 1]) for h, _, _ in zeilen if h - 1 in zt]
    vor = [p for p in paare if p[0] < args.nu7]
    nach = [p for p in paare if p[0] > args.nu7]  # der NU7-Block selbst schliesst noch an einen 75-s-Block an
    r = {
        "netz": "zcash mainnet", "quelle": "eigene header ueber p2p",
        "abruf_utc": meta.get("abruf_utc"), "peer_software": meta.get("peer_software"),
        "gegenproben": [{k: g[k] for k in ("agent", "verglichen", "gleich")} for g in meta.get("gegenproben", [])],
        "pruefungen": meta.get("pruefungen"), "checkpoints_geprueft": meta.get("checkpoints_geprueft"),
        "abzweige_verworfen": len(meta.get("abzweige_verworfen", [])),
        "nu7_hoehe": args.nu7,
        "bereich": {"von_hoehe": erste, "bis_hoehe": spitze, "von_utc": utc(zt[erste]), "bis_utc": utc(zt[spitze]),
                    "bloecke": spitze - erste + 1},
    }
    if vor:
        r["vor_nu7"] = kennzahlen(vor, ALT)
        r["vor_nu7"]["bereich"] = {"von_hoehe": vor[0][0], "bis_hoehe": vor[-1][0]}
        r["vor_nu7"]["je_woche"] = je_woche(vor)
        r["vorhersage"] = vorhersage(vor, spitze, zt[spitze], args.nu7)
    if nach:
        r["nach_nu7"] = kennzahlen(nach, NEU)
        r["nach_nu7"]["bereich"] = {"von_hoehe": nach[0][0], "bis_hoehe": nach[-1][0]}
        r["nach_nu7"]["erster_nu7_block_utc"] = utc(zt[args.nu7]) if args.nu7 in zt else None
    if spitze >= args.nu7:
        r["einpendeln"] = einpendeln(zeilen, args.nu7)
    if args.csv and args.nu7 in zt:
        with open(args.csv, "w") as f:
            f.write("height,timestamp,interval_s\n")
            for h in range(args.nu7, spitze + 1):
                f.write(f"{h},{zt[h]},{zt[h] - zt[h - 1] if h > args.nu7 else ''}\n")
    with open(args.json, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(args.md, "w") as f:
        f.write(md(r))
    print(json.dumps({"spitze": spitze, "vor_nu7": len(vor), "nach_nu7": len(nach),
                      "vorhersage_median": (r.get("vorhersage") or {}).get("median_utc")}))


def md(r):
    z = [f"Quelle: eigene Header ueber P2P, Abruf {r['abruf_utc']} UTC. Peer-Software: "
         f"{', '.join(r['peer_software'] or [])}. Gegenproben: "
         + ", ".join(f"{g['agent']} {g['gleich']}/{g['verglichen']}" for g in r["gegenproben"]) + ".",
         f"Bereich {r['bereich']['von_hoehe']:,} bis {r['bereich']['bis_hoehe']:,} "
         f"({r['bereich']['von_utc']} bis {r['bereich']['bis_utc']} UTC).", ""]
    for teil, titel in (("vor_nu7", "Vor NU7, gegen 75 s"), ("nach_nu7", "Ab NU7, gegen 25 s")):
        if teil not in r:
            continue
        k = r[teil]
        g, b = k["gezaehlt"], k["berechnet"]
        z += [f"### {titel} ({k['abstaende']:,} Abstaende, Bloecke {k['bereich']['von_hoehe']:,} bis {k['bereich']['bis_hoehe']:,})", "",
              "| Kennzahl | gezaehlt | berechnet |", "|---|---:|---:|",
              f"| Mittel | {g['mittel_s']} s | {b['mittel_s']:.0f} s |",
              f"| Median | {g['median_s']} s | {b['median_s']} s |",
              f"| p90 | {g['p90_s']} s | {b['p90_s']} s |",
              f"| p99 | {g['p99_s']} s | {b['p99_s']} s |",
              f"| Anteil ueber {3 * b['zielzeit_s']:.0f} s | {g['anteil_ueber_3T_prozent']} % | {b['anteil_ueber_3T_prozent']} % |",
              f"| Anteil ueber {b['zielzeit_s'] * math.log(1000):.0f} s | {g['anteil_ueber_T_ln1000_prozent']} % | 0.1 % |",
              f"| Laengste Luecke | {g['laengste_luecke_s']} s (vor Block {g['laengste_luecke_vor_block']:,}, {g['laengste_luecke_utc']} UTC) | {b['laengste_luecke_s']} s |",
              f"| Negative Abstaende | {g['negativ']} | 0 |", ""]
        if "je_woche" in k:
            z += ["| ISO-Woche | Abstaende | Mittel | Median |", "|---|---:|---:|---:|"]
            z += [f"| {w['woche']} | {w['abstaende']:,} | {w['mittel_s']} s | {w['median_s']} s |" for w in k["je_woche"]]
            z.append("")
    v = r.get("vorhersage")
    if v and "fehler" not in v:
        z += ["### Vorhersage fuer Hoehe {:,}".format(v["zielhoehe"]), "",
              f"Noch {v['fehlend']:,} Bloecke ab Spitze {v['spitze_hoehe']:,} ({v['spitze_utc']} UTC). "
              f"Tempo der letzten {v['tempo_fenster_tage']} vollen Tage {v['tempo_mittel_s']} s "
              f"(Tagesmittel {v['tagesmittel_min_s']} bis {v['tagesmittel_max_s']} s).", "",
              "| Rechnung | Zeitpunkt UTC |", "|---|---|",
              f"| Gezaehltes Tempo, Median | {v['median_utc']} |",
              f"| Band 5 % bis 95 % | {v['band_5_utc']} bis {v['band_95_utc']} ({v['band_breite_h']} h) |",
              f"| Berechnet mit genau 75 s | {v['berechnet_75s_utc']} |",
              f"| Zakura (laut Ben) | {v['zakura_schaetzung_utc']} |", ""]
    elif v:
        z += [f"Vorhersage nicht moeglich: {v['fehler']}.", ""]
    e = r.get("einpendeln")
    if e:
        z += ["### Einpendeln nach NU7", "", "```", json.dumps(e, indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(z)


if __name__ == "__main__":
    main()
