#!/usr/bin/env python3
"""intervalle_csv.py - CSV aller Blockabstaende seit NU7 fuer pulsehawk.io/zcash-nu7.

Ben, 18.10.2026: Hoehe, Zeitstempel, Abstand, ohne IPs. Die Datei enthaelt
nur Werte aus den Blockkoepfen (testnet-koepfe.csv.gz), nichts ueber Peers.

Bereich wie im Bericht: ab 4.465.026 bis zur letzten Hoehe der fertigen
Auswertung (bereich.bis_hoehe in der JSON). Abstand = Zeitstempel minus
Zeitstempel des Vorgaengers, wie in nu7_auswertung.py; fuer 4.465.026 bleibt
er leer, weil der erste gezaehlte Abstand der von 4.465.027 ist.

  python3 scripts/zcash/intervalle_csv.py --koepfe data/zcash/testnet-koepfe.csv.gz \
      --json data/zcash/nu7-testnet-2026-10-18.json --aus data/zcash/nu7-testnet-intervalle-2026-10-18.csv
"""
import argparse
import csv
import gzip
import json

NU7 = 4_465_026


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()

    bis = json.load(open(args.json))["bereich"]["bis_hoehe"]
    with gzip.open(args.koepfe, "rt") as f:
        zeit = {int(z["hoehe"]): int(z["zeit"]) for z in csv.DictReader(f)}
    with open(args.aus, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["height", "timestamp", "interval_s"])
        for h in range(NU7, bis + 1):
            w.writerow([h, zeit[h], "" if h == NU7 else zeit[h] - zeit[h - 1]])
    print(f"{bis - NU7 + 1} zeilen, {NU7} bis {bis}")


if __name__ == "__main__":
    main()
