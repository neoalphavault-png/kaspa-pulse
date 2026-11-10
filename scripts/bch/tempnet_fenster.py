#!/usr/bin/env python3
"""tempnet_fenster.py - Fenster der Hash-Ein- und Ausstiege im BCH Tempnet aus
unseren eigenen Koepfen und Aufteilung unserer gezaehlten Stale-Bloecke
(Ben, 10.11.2026, Abschlussbericht, Zusage im Forum #40).

Difficulty je Kopf aus nBits (die Koepfe sind beim Abruf auf Verkettung und
Arbeit geprueft): difficulty = Ziel bei 0x1d00ffff / Ziel aus nBits.

Fenster: Arbeitsrate ueber 10 Bloecke = Summe der Difficulty der letzten 10
Bloecke / Zeit zwischen dem Kopf vor ihnen und dem letzten (Kopfzeiten). Ein
Block gehoert zu einem Hash-Fenster, wenn diese Rate mindestens SCHWELLE
(5 Difficulty je Sekunde) erreicht, das Zehnfache der hoechsten Stundenrate
ausserhalb solcher Fenster (rund 0,5), oder wenn die 10 Bloecke in hoechstens
60 s kamen, das Zehnfache der Zielrate. Die zweite Bedingung faengt die Rampe
am Anfang eines Einstiegs, wenn die Bloecke schon schnell kommen, die
Difficulty aber noch niedrig ist. Laeufe mit weniger als
30 min Abstand werden zusammengelegt. Einstieg = Kopfzeit des ersten Blocks,
Ausstieg = Kopfzeit des letzten Blocks des Laufs. Die Raender sind der erste
und letzte Block, dessen eigener Abstand allein die Schwelle erreicht.

Gegenprobe (--vergleich): CSV height,difficulty von bitcoincashautist
(Forum #41), nur als Daten gelesen. Gezaehlt wird, fuer wie viele gemeinsame
Hoehen die Difficulty abweicht (relativ mehr als 1e-9).

Stale: aus zusammenfassung.json des Zuhoerers (stale nach 6 Bestaetigungen).
Zuordnung zu einem Hash-Fenster ueber die Hoehe (zwischen erstem und letztem
Block des Fensters), zu den Stunden von rufitnes ueber die erste Ankuendigung
bei uns. Anteil = stale / (angekuendigte Kettenbloecke + stale) im selben
Bereich, Kettenbloecke aus bloecke.csv. Wo der Zuhoerer nicht lief, wird
nichts gezaehlt; die Abdeckung je Fenster steht dabei.

  python3 scripts/bch/tempnet_fenster.py --koepfe tempnet-koepfe.csv.gz --bloecke bloecke.csv \\
      --zusammenfassung zusammenfassung.json --laeufe <ordner>... [--vergleich tempnet_d.csv] --aus fenster.json
  python3 scripts/bch/tempnet_fenster.py --selbsttest
"""
import argparse
import csv
import gzip
import json
import os
import sys
from datetime import datetime, timezone

SCHWELLE = 5.0      # Difficulty je Sekunde
N_RATE = 10         # Bloecke fuer die Arbeitsrate
LUECKE_S = 1800     # Laeufe mit kleinerem Abstand zusammenlegen
RAMPE_S = 60        # 10 Bloecke in hoechstens 60 s, das Zehnfache der Zielrate (60 s je Block)
ZIEL_1 = 0xffff * (1 << (8 * (0x1d - 3)))

# rufitnes, Forum #37 (8.11.2026): Stunden mit hoher Blockrate, UTC, [von, bis)
RUFITNES = [("2026-10-29T21:00:00Z", "2026-10-29T23:00:00Z"), ("2026-11-02T22:00:00Z", "2026-11-03T00:00:00Z"),
            ("2026-11-03T08:00:00Z", "2026-11-03T09:00:00Z"), ("2026-11-03T17:00:00Z", "2026-11-03T18:00:00Z"),
            ("2026-11-05T17:00:00Z", "2026-11-05T18:00:00Z")]


def difficulty(nbits):
    n = int(nbits, 16)
    e, m = n >> 24, n & 0xffffff
    return ZIEL_1 / (m * (1 << (8 * (e - 3))) if e >= 3 else m >> (8 * (3 - e)))


def ts(iso):
    return datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fenster_finden(koepfe):
    """koepfe: Liste (hoehe, zeit, difficulty) nach Hoehe. Gibt Laeufe [(i_von, i_bis)]."""
    drin = []
    for i in range(N_RATE, len(koepfe)):
        dt = koepfe[i][1] - koepfe[i - N_RATE][1]
        arbeit = sum(k[2] for k in koepfe[i - N_RATE + 1:i + 1])
        if arbeit / max(dt, 1) >= SCHWELLE or dt <= RAMPE_S:
            drin.append(i)
    laeufe = []
    for i in drin:
        if laeufe and koepfe[i][1] - koepfe[laeufe[-1][1]][1] <= LUECKE_S:
            laeufe[-1][1] = i
        else:
            laeufe.append([i, i])
    # Die Rate ueber 10 Bloecke reicht ueber die Raender hinaus. Deshalb Rand
    # auf den ersten und letzten Block, dessen eigener Abstand allein die
    # Schwelle erreicht (Difficulty / Abstand zum Vorgaenger, mindestens 1 s).
    def schnell(j):
        if j == 0:
            return False
        dt = max(koepfe[j][1] - koepfe[j - 1][1], 1)
        return koepfe[j][2] / dt >= SCHWELLE or dt <= RAMPE_S / N_RATE
    raender = []
    for a, b in laeufe:
        kand = [j for j in range(max(a - N_RATE + 1, 1), b + 1) if schnell(j)]
        if kand:
            raender.append((kand[0], kand[-1]))
    return raender


def abdeckung(laeufe_meta, von, bis):
    """Sekunden in [von, bis), die ein Zuhoerer-Lauf abdeckt."""
    stuecke = sorted((max(a, von), min(b, bis)) for a, b in laeufe_meta if b > von and a < bis)
    summe, ende = 0, von
    for a, b in stuecke:
        a = max(a, ende)
        if b > a:
            summe += b - a
            ende = b
    return summe


def anteil(ketten, stale):
    return {"kettenbloecke": ketten, "stale": stale,
            "anteil_prozent": round(100 * stale / (ketten + stale), 3) if ketten + stale else None}


def auswerten(koepfe_pfad, bloecke_pfad, zus_pfad, laeufe_ordner, vergleich_pfad=None):
    koepfe = []
    with gzip.open(koepfe_pfad, "rt") as f:
        for z in csv.DictReader(f):
            koepfe.append((int(z["hoehe"]), int(z["zeit"]), difficulty(z["nbits"])))
    koepfe.sort()
    out = {"koepfe": {"von": koepfe[0][0], "bis": koepfe[-1][0], "anzahl": len(koepfe)},
           "regel": f"arbeitsrate ueber {N_RATE} bloecke mindestens {SCHWELLE} difficulty je sekunde oder {N_RATE} bloecke in hoechstens {RAMPE_S} s, "
                    f"laeufe mit weniger als {LUECKE_S // 60} min abstand zusammengelegt"}
    if vergleich_pfad:
        fremd = {}
        with open(vergleich_pfad, newline="") as f:
            for z in csv.DictReader(f):
                fremd[int(z["height"])] = float(z["difficulty"])
        gemeinsam = [(h, d) for h, _, d in koepfe if h in fremd]
        ab = [h for h, d in gemeinsam if abs(d - fremd[h]) > 1e-9 * max(1.0, d)]
        out["gegenprobe_bitcoincashautist"] = {
            "quelle": "source bitcoincashautist, Forum #41, Gist tempnet_d.csv",
            "hoehen_dort": [min(fremd), max(fremd)], "gemeinsame_hoehen": len(gemeinsam),
            "abweichungen": len(ab), "erste_abweichungen": ab[:10],
            "nur_dort": len([h for h in fremd if h < koepfe[0][0] or h > koepfe[-1][0]])}
    bloecke = list(csv.DictReader(open(bloecke_pfad)))
    zus = json.load(open(zus_pfad))
    stale = zus["stale"]["bloecke"]
    meta = []
    for o in laeufe_ordner:
        p = os.path.join(o, "meta.json")
        if os.path.exists(p):
            m = json.load(open(p))
            if m.get("start_utc") and m.get("ende_utc"):
                meta.append((ts(m["start_utc"]), ts(m["ende_utc"])))
    gesehen_h = [int(b["height"]) for b in bloecke if b.get("first_seen_utc")]
    stale_h = [int(s["height"]) for s in stale if s.get("height") not in (None, "")]
    fen = []
    for a, b in fenster_finden(koepfe):
        h1, h2 = koepfe[a][0], koepfe[b][0]
        t1, t2 = koepfe[a][1], koepfe[b][1]
        dmax = max(k[2] for k in koepfe[a:b + 1])
        k = sum(1 for h in gesehen_h if h1 <= h <= h2)
        s = sum(1 for h in stale_h if h1 <= h <= h2)
        abd = abdeckung(meta, t1, t2 + 1)
        fen.append({"einstieg_utc": iso(t1), "ausstieg_utc": iso(t2), "hoehen": [h1, h2], "bloecke": h2 - h1 + 1,
                    "difficulty_max": round(dmax, 1), "zuhoerer_abdeckung_prozent": round(100 * abd / max(t2 + 1 - t1, 1), 1),
                    **anteil(k, s)})
    out["hash_fenster"] = fen
    drin_k = sum(f["kettenbloecke"] for f in fen)
    drin_s = sum(f["stale"] for f in fen)
    alle_k, alle_s = len(gesehen_h), len(stale_h)
    out["drin_und_draussen"] = {"in_hash_fenstern": anteil(drin_k, drin_s),
                                "ausserhalb": anteil(alle_k - drin_k, alle_s - drin_s),
                                "stale_ohne_hoehe": len(stale) - len(stale_h)}
    ruf = []
    gesehen_t = [ts(b["first_seen_utc"]) for b in bloecke if b.get("first_seen_utc")]
    stale_t = [ts(s["first_seen_utc"]) for s in stale if s.get("first_seen_utc")]
    for v, b in RUFITNES:
        a, e = ts(v), ts(b)
        ruf.append({"von_utc": v, "bis_utc": b, "zuhoerer_abdeckung_prozent": round(100 * abdeckung(meta, a, e) / (e - a), 1),
                    **anteil(sum(1 for t in gesehen_t if a <= t < e), sum(1 for t in stale_t if a <= t < e))})
    rk, rs = sum(r["kettenbloecke"] for r in ruf), sum(r["stale"] for r in ruf)
    out["rufitnes_stunden"] = {"quelle": "source rufitnes, Forum #37", "fenster": ruf,
                               "zusammen": anteil(rk, rs), "rest": anteil(len(gesehen_t) - rk, len(stale_t) - rs)}
    return out


def selbsttest():
    fehler = []
    def ok(name, bed):
        print(("ok   " if bed else "FEHL ") + name)
        if not bed:
            fehler.append(name)
    ok("difficulty 1d00ffff ist 1", abs(difficulty("1d00ffff") - 1.0) < 1e-12)
    ok("difficulty 1d009691", abs(difficulty("1d009691") - 0xffff / 0x9691) < 1e-12)
    ok("difficulty 1b0404cb", abs(difficulty("1b0404cb") - 16307.420938523983) < 1e-6)
    # 200 ruhige Bloecke alle 60 s mit Difficulty 2, dann 100 Bloecke alle 6 s mit 1000, dann ruhig
    k, t, h = [], 0, 1000
    for _ in range(200):
        t += 60; k.append((h, t, 2.0)); h += 1
    for _ in range(100):
        t += 6; k.append((h, t, 1000.0)); h += 1
    for _ in range(200):
        t += 600; k.append((h, t, 1.0)); h += 1
    f = fenster_finden(k)
    ok("ein fenster", len(f) == 1)
    ok("einstieg beim ersten schnellen block", f and k[f[0][0]][0] == 1200)
    ok("ausstieg am ende der schnellen bloecke oder kurz danach", f and 1299 <= k[f[0][1]][0] <= 1301)
    k2, t, h = [], 0, 1000
    for _ in range(200):
        t += 60; k2.append((h, t, 2.0)); h += 1
    for _ in range(50):
        t += 3; k2.append((h, t, 1.0)); h += 1
    for _ in range(200):
        t += 60; k2.append((h, t, 2.0)); h += 1
    f2 = fenster_finden(k2)
    ok("rampe mit niedriger difficulty wird erkannt", len(f2) == 1 and k2[f2[0][0]][0] == 1200)
    ok("abdeckung halb", abdeckung([(0, 50)], 0, 100) == 50)
    ok("abdeckung ueberlappend", abdeckung([(0, 60), (40, 100)], 0, 100) == 100)
    print("alle testfaelle bestanden" if not fehler else f"{len(fehler)} fehler")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--koepfe")
    ap.add_argument("--bloecke")
    ap.add_argument("--zusammenfassung")
    ap.add_argument("--laeufe", nargs="*", default=[])
    ap.add_argument("--vergleich")
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    out = auswerten(a.koepfe, a.bloecke, a.zusammenfassung, a.laeufe, a.vergleich)
    json.dump(out, open(a.aus, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
