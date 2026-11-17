#!/usr/bin/env python3
"""tempnet_stuecke.py - das BCH Tempnet in Stuecken von 120 Bloecken
(Ben, 11.11.2026, Frage von bitcoincashautist im Forum 2173, Beitrag 44).

Je Stueck aus unseren eigenen Koepfen (nBits, Kopfzeiten) und dem Zuhoerer:
  chunk_n, erste und letzte Hoehe, Beginn (Kopfzeit des ersten Blocks, UTC),
  mittlere Difficulty, mittlere und mediane Blockzeit (Kopfzeit minus Kopfzeit
  des Vorgaengers, je Block des Stuecks), Stale-Bloecke im Stueck (nach Hoehe),
  Stale-Ereignisse (eine Hoehe mit einem oder mehr Kandidaten zaehlt einmal),
  Abdeckung des Zuhoerers in Prozent der Zeit vom Beginn bis zur Kopfzeit des
  letzten Blocks. Ohne volle Abdeckung (unter 99,9 %) ist das Stueck markiert
  und die Stale-Werte bleiben leer, nicht null.

Mit --ohne-diff1-csv eine zweite CSV mit denselben Stuecken ohne Bloecke mit
Difficulty 1, Spalten wie die erste plus block_count (siehe stuecke()). Stale
darin nach der Zweigregel von bitcoincashautist (zweig_filter()); dafuer
liest das Skript die koepfe.jsonl.gz der Laeufe.

Dazu, wenn --c2-bloecke kommt: Ausbreitung als Differenz der ersten
Ankuendigung bei c2 minus GitHub fuer Bloecke, die beide gesehen haben.

  python3 scripts/bch/tempnet_stuecke.py --koepfe tempnet-koepfe.csv.gz --zusammenfassung zusammenfassung.json \\
      --laeufe <ordner>... [--c2-bloecke bloecke-c2.csv --gh-bloecke bloecke.csv] --csv stuecke.csv --aus stuecke.json
  python3 scripts/bch/tempnet_stuecke.py --selbsttest
"""
import argparse
import csv
import gzip
import json
import os
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

STUECK = 120
VOLL = 99.9
ZIEL_1 = 0xffff * (1 << (8 * (0x1d - 3)))
SPALTEN = ["chunk_n", "first_height", "last_height", "start_utc", "mean_difficulty", "mean_block_time_s",
           "median_block_time_s", "stale_blocks", "stale_events", "listener_coverage_pct", "full_coverage"]


def difficulty(nbits):
    n = int(nbits, 16)
    e, m = n >> 24, n & 0xffffff
    return ZIEL_1 / (m * (1 << (8 * (e - 3))))


def ts(iso):
    return datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def abdeckung(fenster, von, bis):
    if bis <= von:
        return 100.0 if any(a <= von <= b for a, b in fenster) else 0.0
    stuecke = sorted((max(a, von), min(b, bis)) for a, b in fenster if b > von and a < bis)
    summe, ende = 0.0, von
    for a, b in stuecke:
        a = max(a, ende)
        if b > a:
            summe += b - a
            ende = b
    return 100.0 * summe / (bis - von)


def diff1(d):
    return abs(d - 1.0) < 1e-9


def stuecke(koepfe, stale_hoehen, fenster, ohne_diff1=False):
    """koepfe: Liste (hoehe, zeit, difficulty) nach Hoehe, lueckenlos.

    ohne_diff1 (bitcoincashautist, Forum 2173 Beitrag 47, Ben 12.11.2026):
    die Stuecke bleiben dieselben 120 Hoehen mit demselben chunk_n, aber
    Bloecke mit Difficulty 1 (nBits 1d00ffff) zaehlen nicht. block_count ist
    die Zahl der uebrigen Bloecke. Mittlere Difficulty und Blockzeiten gelten
    nur fuer sie (Blockzeit weiter Kopfzeit minus Kopfzeit des Vorgaengers,
    auch wenn der Vorgaenger Difficulty 1 hat).

    Stale (bitcoincashautist, Beitrag 52, Ben 17.11.2026): "I leave out
    entire forked branch if the main block or its sibling has difficulty 1."
    Mit ohne_diff1 kommen die Stale-Hoehen schon nach zweig_filter() gefiltert
    an und zaehlen auf allen Hoehen des Stuecks, auch wo der Kettenblock
    Difficulty 1 hat, denn die Regel gilt fuer den ganzen Zweig."""
    nach_h = {h: (t, d) for h, t, d in koepfe}
    stale = Counter(stale_hoehen)
    zeilen = []
    for n, i in enumerate(range(0, len(koepfe), STUECK), 1):
        teil = koepfe[i:i + STUECK]
        if len(teil) < STUECK:
            break  # das letzte, unvollstaendige Stueck faellt weg
        h1, h2 = teil[0][0], teil[-1][0]
        bleibt = [k for k in teil if not (ohne_diff1 and diff1(k[2]))]
        hoehen = [h for h, _, _ in bleibt]
        iv = [t - nach_h[h - 1][0] for h, t, _ in bleibt if h - 1 in nach_h]
        abd = abdeckung(fenster, teil[0][1], teil[-1][1])
        voll = abd >= VOLL
        alle_h = [h for h, _, _ in teil]
        s_bl = sum(stale[h] for h in alle_h)
        s_er = sum(1 for h in alle_h if stale[h])
        zeile = {"chunk_n": n, "first_height": h1, "last_height": h2, "start_utc": iso(teil[0][1]),
                       "mean_difficulty": round(sum(d for _, _, d in bleibt) / len(bleibt), 3) if bleibt else "",
                       "mean_block_time_s": round(sum(iv) / len(iv), 2) if iv else "",
                       "median_block_time_s": statistics.median(iv) if iv else "",
                       "stale_blocks": s_bl if voll else "", "stale_events": s_er if voll else "",
                       "listener_coverage_pct": round(abd, 1), "full_coverage": "yes" if voll else "no"}
        if ohne_diff1:
            zeile["block_count"] = len(bleibt)
        zeilen.append(zeile)
    return zeilen


def zweig_filter(stale, kopf, kanon):
    """Zweigregel von bitcoincashautist (Forum 2173, Beitrag 52).

    stale: Liste (hoehe, hash) der Stale-Bloecke. kopf: hash -> (prev, nbits)
    aus den aufgezeichneten Koepfen. kanon: hoehe -> difficulty der Kette.
    Stale-Bloecke, die ueber prev aneinander haengen, bilden einen Zweig. Der
    Zweig beginnt an seiner kleinsten Hoehe (Abzweig). Er faellt ganz weg,
    wenn dort der Kettenblock oder ein Stale-Block des Zweigs Difficulty 1
    hat. Fehlt der Kopf eines Stale-Blocks am Abzweig, ist seine Difficulty
    unbekannt; der Zweig bleibt und wird als ohne_kopf gezaehlt.
    Gibt (bleibende Stale-Hoehen, Kennzahlen)."""
    nach_hash = {x: h for h, x in stale}
    eltern = {}
    for h, x in stale:
        p = (kopf.get(x) or (None, None))[0]
        eltern[x] = p if p in nach_hash else None

    def w(x):
        while eltern.get(x):
            x = eltern[x]
        return x
    zweige = {}
    for h, x in stale:
        zweige.setdefault(w(x), []).append((h, x))
    bleibt, weg, ohne_kopf, weg_bloecke, breiter = [], 0, 0, 0, 0
    for r, glieder in zweige.items():
        ab = min(h for h, _ in glieder)
        am_abzweig = [x for h, x in glieder if h == ab]
        unbekannt = any(x not in kopf for x in am_abzweig)
        d1 = diff1(kanon.get(ab, 0)) or any(x in kopf and diff1(difficulty(kopf[x][1])) for x in am_abzweig)
        # zur kontrolle: die weitere lesart, difficulty 1 irgendwo im zweig
        if not d1 and any(diff1(kanon.get(h, 0)) or (x in kopf and diff1(difficulty(kopf[x][1]))) for h, x in glieder):
            breiter += 1
        if d1:
            weg += 1
            weg_bloecke += len(glieder)
            continue
        ohne_kopf += unbekannt
        bleibt += [h for h, _ in glieder]
    return bleibt, {"zweige": len(zweige), "zweige_weg": weg, "stale_bloecke_weg": weg_bloecke,
                    "zweige_ohne_kopf_am_abzweig": ohne_kopf, "stale_bloecke_bleiben": len(bleibt),
                    "zweige_anders_bei_weiterer_lesart": breiter}


def koepfe_der_laeufe(laeufe):
    kopf = {}
    for o in laeufe:
        p = os.path.join(o, "koepfe.jsonl.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rt") as f:
            for z in f:
                k = json.loads(z)
                if k.get("hash") and k.get("nbits"):
                    kopf[k["hash"]] = (k.get("prev"), k["nbits"])
    return kopf


def ausbreitung(c2_pfad, gh_pfad):
    def lesen(p):
        return {r["hash"]: ts(r["first_seen_utc"]) + (float("0." + r["first_seen_utc"][20:23]) if "." in r["first_seen_utc"] else 0)
                for r in csv.DictReader(open(p)) if r.get("first_seen_utc")}
    c, g = lesen(c2_pfad), lesen(gh_pfad)
    d = sorted(c[h] - g[h] for h in c if h in g)
    if not d:
        return {"n": 0}
    q = lambda p: d[int((len(d) - 1) * p)]  # noqa: E731
    return {"n": len(d), "c2_bloecke": len(c), "median_s": round(statistics.median(d), 3), "p10_s": round(q(0.1), 3),
            "p90_s": round(q(0.9), 3), "min_s": round(d[0], 3), "max_s": round(d[-1], 3),
            "c2_zuerst": sum(1 for x in d if x < 0), "github_zuerst": sum(1 for x in d if x > 0)}


def selbsttest():
    fehler = []
    def ok(name, bed):
        print(("ok   " if bed else "FEHL ") + name)
        if not bed:
            fehler.append(name)
    k = [(1000 + i, 1000 * 60 + 60 * i, 1.0) for i in range(250)]
    z = stuecke(k, [1005, 1005, 1007, 1200], [(0, 70000)])
    ok("zwei volle stuecke, rest faellt weg", len(z) == 2)
    ok("stale bloecke 3 im ersten", z[0]["stale_blocks"] == 3)
    ok("stale ereignisse 2 im ersten", z[0]["stale_events"] == 2)
    ok("blockzeit 60", z[0]["median_block_time_s"] == 60 and z[1]["mean_block_time_s"] == 60)
    z2 = stuecke(k, [1005], [(0, 60000 + 60 * 50)])
    ok("teilweise abdeckung markiert und leer", z2[0]["full_coverage"] == "no" and z2[0]["stale_blocks"] == "")
    ok("ohne abdeckung null prozent", z2[1]["listener_coverage_pct"] == 0.0)
    # ohne Difficulty 1: im ersten Stueck jeder dritte Block mit Difficulty 1, Stale auf 1005 (bleibt) und 1006 (faellt)
    k3 = [(1000 + i, 60000 + 60 * i, 1.0 if i % 3 == 0 and i < 120 else 2.0) for i in range(250)]
    z3 = stuecke(k3, [1005, 1006, 1006, 1007], [(0, 70000)], ohne_diff1=True)
    ok("block_count ohne difficulty 1", z3[0]["block_count"] == 80 and z3[1]["block_count"] == 120)
    ok("difficulty nur der uebrigen", z3[0]["mean_difficulty"] == 2.0)
    ok("vorgefilterte stale zaehlen auf allen hoehen", z3[0]["stale_blocks"] == 4 and z3[0]["stale_events"] == 3)
    # zweigregel: kanon 1000 bis 1009, difficulty 1 auf 1003
    kanon = {h: (1.0 if h == 1003 else 2.0) for h in range(1000, 1010)}
    n2, n1 = "1c00ffff", "1d00ffff"
    kopf = {"a5": ("k4", n2), "a6": ("a5", n2), "b3": ("k2", n2), "c7": ("k6", n1), "d8": ("k7", n2),
            "e5": ("k4", n2), "f6": ("a5", n1)}
    st = [(1005, "a5"), (1006, "a6"), (1003, "b3"), (1007, "c7"), (1008, "d8"), (1009, "x9"), (1005, "e5"), (1006, "f6")]
    bl, info = zweig_filter(st, kopf, kanon)
    ok("zweig mit abzweig ohne difficulty 1 bleibt ganz, auch mit difficulty 1 weiter oben",
       sorted(h for h in bl if h in (1005, 1006)) == [1005, 1005, 1006, 1006])
    ok("kettenblock am abzweig mit difficulty 1, zweig faellt", 1003 not in bl)
    ok("stale am abzweig mit difficulty 1, zweig faellt", 1007 not in bl)
    ok("zweig ohne kopf bleibt und wird gezaehlt", 1009 in bl and info["zweige_ohne_kopf_am_abzweig"] == 1)
    ok("weitere lesart zaehlt den zweig mit difficulty 1 oben", info["zweige_anders_bei_weiterer_lesart"] == 1)
    ok("kennzahlen", info["zweige"] == 6 and info["zweige_weg"] == 2 and info["stale_bloecke_weg"] == 2)
    ok("gleiches chunk_n und gleiche hoehen", z3[0]["first_height"] == 1000 and z3[0]["last_height"] == 1119)
    z4 = stuecke(k3, [1005, 1006, 1006, 1007], [(0, 70000)])
    ok("ohne schalter unveraendert", "block_count" not in z4[0] and z4[0]["stale_blocks"] == 4)
    print("alle testfaelle bestanden" if not fehler else f"{len(fehler)} fehler")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--koepfe")
    ap.add_argument("--zusammenfassung")
    ap.add_argument("--laeufe", nargs="*", default=[])
    ap.add_argument("--c2-bloecke")
    ap.add_argument("--gh-bloecke")
    ap.add_argument("--csv")
    ap.add_argument("--ohne-diff1-csv", help="zweite CSV ohne Bloecke mit Difficulty 1, Spalten wie --csv plus block_count")
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    koepfe = []
    with gzip.open(a.koepfe, "rt") as f:
        for z in csv.DictReader(f):
            koepfe.append((int(z["hoehe"]), int(z["zeit"]), difficulty(z["nbits"])))
    koepfe.sort()
    zus = json.load(open(a.zusammenfassung))
    stale_h = [s["height"] for s in zus["stale"]["bloecke"] if s.get("height") not in (None, "")]
    fenster = []
    for o in a.laeufe:
        p = os.path.join(o, "meta.json")
        if os.path.exists(p):
            m = json.load(open(p))
            if m.get("start_utc") and m.get("ende_utc"):
                fenster.append((ts(m["start_utc"]), ts(m["ende_utc"])))
    zeilen = stuecke(koepfe, stale_h, fenster)
    with open(a.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)
    zweig_info = None
    if a.ohne_diff1_csv:
        kanon = {h: d for h, _, d in koepfe}
        stale_hx = [(s["height"], s["hash"]) for s in zus["stale"]["bloecke"] if s.get("height") not in (None, "")]
        stale_z, zweig_info = zweig_filter(stale_hx, koepfe_der_laeufe(a.laeufe), kanon)
        z1 = stuecke(koepfe, stale_z, fenster, ohne_diff1=True)
        with open(a.ohne_diff1_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN + ["block_count"], lineterminator="\n")
            w.writeheader()
            w.writerows(z1)
    voll = [z for z in zeilen if z["full_coverage"] == "yes"]
    out = {"koepfe": [koepfe[0][0], koepfe[-1][0]], "stuecke": len(zeilen), "voll_abgedeckt": len(voll),
           "stale_in_vollen_stuecken": sum(z["stale_blocks"] for z in voll),
           "stale_ereignisse_in_vollen_stuecken": sum(z["stale_events"] for z in voll),
           "letztes_stueck_endet": zeilen[-1]["last_height"] if zeilen else None}
    if zweig_info:
        voll1 = [z for z in z1 if z["full_coverage"] == "yes"]
        zweig_info.update({"stale_in_vollen_stuecken": sum(z["stale_blocks"] for z in voll1),
                           "stale_ereignisse_in_vollen_stuecken": sum(z["stale_events"] for z in voll1)})
        out["ohne_diff1_zweigregel"] = zweig_info
    if a.c2_bloecke and a.gh_bloecke:
        out["ausbreitung_c2_minus_github"] = ausbreitung(a.c2_bloecke, a.gh_bloecke)
    json.dump(out, open(a.aus, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
