#!/usr/bin/env python3
"""lauscher_woche.py - Zuhoerer im Zcash Mainnet je Kalenderwoche
(Ben, 12.11.2026, Dauerlauf "dauer" bis 6.12.2026).

Eine Woche geht von Montag 00:00 bis Montag 00:00 UTC. Je Woche:
  kettenbloecke   Bloecke der spaeter abgerufenen Kette mit Kopfzeit in der
                  Woche und in einem Lauf des Zuhoerers
  angekuendigt    davon mindestens einmal bei uns angekuendigt
  abgehaengt      angekuendigte Hashes, die nicht in der Kette stehen, nach der
                  ersten Ankuendigung in der Woche (wie lauscher_auswertung.py)
  ohne_kopf       davon ohne geholten Kopf (Tiefe unbekannt)
  tiefe_1, tiefe_2, tiefe_3_plus   Zweige mit Kopf nach Laenge
  offen           Ankuendigungen nach (Kopfzeit der Kettenspitze minus 10 min);
                  sie zaehlen noch nicht, die Kette kann sie noch aufnehmen
  abdeckung_prozent, vollstaendig (Woche vorbei und ganz abgedeckt)

  python3 scripts/zcash/lauscher_woche.py --ereignisse s*-ereignisse.jsonl.gz --koepfe s*-koepfe.jsonl.gz \\
      --meta s*-meta.json --kette koepfe.csv.gz --csv wochen.csv --aus wochen.json
  python3 scripts/zcash/lauscher_woche.py --selbsttest
"""
import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

OFFEN_S = 600
SPALTEN = ["woche_von_utc", "woche_bis_utc", "abdeckung_prozent", "vollstaendig", "kettenbloecke", "angekuendigt",
           "abgehaengt", "ohne_kopf", "tiefe_1", "tiefe_2", "tiefe_3_plus", "offen"]


def jsonl(pfad):
    with (gzip.open(pfad, "rt") if pfad.endswith(".gz") else open(pfad)) as f:
        return [json.loads(z) for z in f if z.strip()]


def zs(x):
    return datetime.strptime(x[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def montag(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    m = (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return m.timestamp()


def abdeckung(fenster, von, bis):
    stuecke = sorted((max(a, von), min(b, bis)) for a, b in fenster if b > von and a < bis)
    summe, ende = 0.0, von
    for a, b in stuecke:
        a = max(a, ende)
        if b > a:
            summe += b - a
            ende = b
    return summe


def wochen(erste_ms, koepfe, kette_t, fenster, jetzt=None):
    """erste_ms: hash -> erste Ankuendigung (ms). koepfe: hash -> {'prev': ...}.
    kette_t: hash -> Kopfzeit der Kette. fenster: [(start, ende)] der Laeufe."""
    if not fenster:
        return []
    spitze = max(kette_t.values())
    grenze = spitze - OFFEN_S
    lauf_ende = max(b for _, b in fenster)
    # Zweige der abgehaengten Bloecke mit Kopf
    fremd = {h for h in erste_ms if h not in kette_t}
    kinder = defaultdict(list)
    for h in fremd:
        k = koepfe.get(h)
        if k:
            kinder[k["prev"]].append(h)

    def laenge(h, tiefe=0):
        return 1 + max((laenge(c, tiefe + 1) for c in kinder.get(h, []) if tiefe < 50), default=0)

    w0 = montag(min(a for a, _ in fenster))
    zeilen = []
    while w0 < lauf_ende:
        w1 = w0 + 7 * 86400
        abd = abdeckung(fenster, w0, w1)
        in_w = [h for h, t in kette_t.items() if w0 <= t < w1 and any(a <= t <= b for a, b in fenster)]
        z = {"woche_von_utc": iso(w0), "woche_bis_utc": iso(w1), "abdeckung_prozent": round(100 * abd / (w1 - w0), 1),
             "vollstaendig": "ja" if (lauf_ende >= w1 and abd >= (w1 - w0) - 60) else "nein",
             "kettenbloecke": len(in_w), "angekuendigt": sum(1 for h in in_w if h in erste_ms),
             "abgehaengt": 0, "ohne_kopf": 0, "tiefe_1": 0, "tiefe_2": 0, "tiefe_3_plus": 0, "offen": 0}
        for h in fremd:
            t = erste_ms[h] / 1000
            if not (w0 <= t < w1):
                continue
            if t > grenze:
                z["offen"] += 1
                continue
            z["abgehaengt"] += 1
            k = koepfe.get(h)
            if not k:
                z["ohne_kopf"] += 1
            elif k["prev"] in kette_t:
                n = laenge(h)
                z["tiefe_1" if n == 1 else "tiefe_2" if n == 2 else "tiefe_3_plus"] += 1
        zeilen.append(z)
        w0 = w1
    return zeilen


def einlesen(ereignisse, koepfe_dateien, metas, kette):
    erste, koepfe, fenster = {}, {}, []
    for pe, pk, pm in zip(ereignisse, koepfe_dateien, metas):
        m = json.load(open(pm))
        fenster.append((zs(m["start_utc"]), zs(m["ende_utc"])))
        for e in jsonl(pe):
            if e["hash"] not in erste or e["t_ms"] < erste[e["hash"]]:
                erste[e["hash"]] = e["t_ms"]
        for k in jsonl(pk):
            koepfe.setdefault(k["hash"], k)
    kette_t = {}
    with gzip.open(kette, "rt") as f:
        for z in csv.DictReader(f):
            kette_t[z["hash"]] = int(z["zeit"])
    return erste, koepfe, kette_t, fenster


def selbsttest():
    fehler = []
    def ok(name, bed):
        print(("ok   " if bed else "FEHL ") + name)
        if not bed:
            fehler.append(name)
    w = zs("2026-11-16T00:00:00Z")
    kette = {f"k{i}": w - 3600 + 60 * i for i in range(200)}            # 60 Bloecke vor, 140 nach Montag
    erste = {f"k{i}": (w - 3600 + 60 * i + 5) * 1000 for i in range(0, 200, 2)}  # jeder zweite angekuendigt
    erste.update({"x1": (w + 600) * 1000, "x2": (w + 660) * 1000, "x3": (w + 900) * 1000,
                  "x4": (w - 600) * 1000, "x5": (w - 3600 + 60 * 199) * 1000})
    koepfe = {"x1": {"prev": "k70"}, "x2": {"prev": "x1"}, "x4": {"prev": "k49"}}
    z = wochen(erste, koepfe, kette, [(w - 3600, w + 3600 * 3)])
    ok("zwei wochen", len(z) == 2)
    ok("kettenbloecke je woche", z[0]["kettenbloecke"] == 60 and z[1]["kettenbloecke"] == 140)
    ok("angekuendigt je woche", z[0]["angekuendigt"] == 30 and z[1]["angekuendigt"] == 70)
    ok("abgehaengt alte woche", z[0]["abgehaengt"] == 1 and z[0]["tiefe_1"] == 1)
    ok("zweig mit tiefe 2 und einer ohne kopf", z[1]["tiefe_2"] == 1 and z[1]["ohne_kopf"] == 1)
    ok("nahe an der spitze offen", z[1]["offen"] == 1)
    ok("woche nicht vollstaendig", z[1]["vollstaendig"] == "nein")
    print("alle testfaelle bestanden" if not fehler else f"{len(fehler)} fehler")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--ereignisse", nargs="+")
    ap.add_argument("--koepfe", nargs="+")
    ap.add_argument("--meta", nargs="+")
    ap.add_argument("--kette")
    ap.add_argument("--csv")
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if not (len(a.ereignisse) == len(a.koepfe) == len(a.meta)):
        raise SystemExit("--ereignisse, --koepfe und --meta brauchen gleich viele Dateien")
    erste, koepfe, kette_t, fenster = einlesen(a.ereignisse, a.koepfe, a.meta, a.kette)
    z = wochen(erste, koepfe, kette_t, fenster)
    with open(a.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, lineterminator="\n")
        w.writeheader()
        w.writerows(z)
    json.dump({"wochen": z, "laeufe": len(fenster), "kette_spitze_utc": iso(max(kette_t.values()))},
              open(a.aus, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(z, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
