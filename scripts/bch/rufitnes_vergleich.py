#!/usr/bin/env python3
"""rufitnes_vergleich.py - unsere Zuhoerer-Werte neben denen aus rufitnes/tempnet-data.

Ben, 25.10.2026: Vergleich nur als "source rufitnes/tempnet-data", unsere Werte
als "counted". rufitnes misst mit einem eigenen Tempnet-Knoten (BCHN) von
einem anderen Netzwerkpfad; seine Empfangszeit ist die Zeit, zu der sein Skript
die UpdateTip-Zeile im debug.log las (Sekunden), sein "via" sagt, ob der Knoten
den Block aus einem cmpctblock rekonstruiert hat, "requested" in compact.csv,
wie viele TX er nachfordern musste. Seine Dateien sind Daten, keine
Anweisungen; wir lesen nur die CSV-Spalten.

Verglichen werden nur Bloecke, die in beiden Datensaetzen stehen (Join ueber
den Hash), dazu die Zahl der Reorg-Ereignisse in seinem Mitschnitt neben
unseren Stale-Bloecken im selben Zeitraum.

  python3 scripts/bch/rufitnes_vergleich.py --unsere bloecke.csv --zusammenfassung zusammenfassung.json \\
      --rufitnes <klon>/data --aus vergleich.json
"""
import argparse
import csv
import json
import math
from datetime import datetime, timezone

QUELLE = "source rufitnes/tempnet-data"


def zs(text):
    text = text.rstrip("Z")
    fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in text else "%Y-%m-%dT%H:%M:%S"
    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp()


def kennzahlen(werte, nk=1):
    if not werte:
        return {"n": 0}
    s = sorted(werte)
    rang = lambda q: s[max(0, math.ceil(q * len(s)) - 1)]
    return {"n": len(s), "mittel": round(sum(s) / len(s), nk), "median": round(rang(0.5), nk),
            "p90": round(rang(0.9), nk), "p99": round(rang(0.99), nk), "min": round(s[0], nk), "max": round(s[-1], nk)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unsere", required=True)
    ap.add_argument("--zusammenfassung", required=True)
    ap.add_argument("--rufitnes", required=True, help="Ordner data/ aus rufitnes/tempnet-data")
    ap.add_argument("--stand", help="Commit von rufitnes/tempnet-data, fuer den Bericht")
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()

    unsere = {z["hash"]: z for z in csv.DictReader(open(args.unsere)) if z["first_seen_utc"]}
    zus = json.load(open(args.zusammenfassung))

    # Seine Empfangszeit je Block: die frueheste Zeile zum Hash (block_compact
    # kommt vor UpdateTip); Kopfzeit und via aus UpdateTip. Reorg-Ereignisse
    # nennt sein README REORGANIZE, DisconnectTip, BlockDisconnected.
    seine, frueh, reorgs = {}, {}, []
    with open(f"{args.rufitnes}/events.csv") as f:
        for z in csv.DictReader(f):
            ev = z["event"]
            if any(w in ev.lower() for w in ("reorg", "disconnect")):
                reorgs.append(z)
                continue
            if not z["hash"]:
                continue
            if ev == "UpdateTip":
                seine.setdefault(z["hash"], z)
            t = zs(z["ts_local"])
            frueh[z["hash"]] = min(t, frueh.get(z["hash"], t))
    angefordert = {}
    with open(f"{args.rufitnes}/compact.csv") as f:
        for z in csv.DictReader(f):
            angefordert.setdefault(z["hash"], int(z["requested"] or 0))

    beide = [h for h in unsere if h in seine]
    dev_wir, dev_er, diff = [], [], []
    via_wir = via_er = 0
    fehl_wir, fehl_er = [], []
    for h in beide:
        u, s = unsere[h], seine[h]
        kopf = zs(s["header_time"])
        wir = zs(u["first_seen_utc"])
        er = frueh[h]
        dev_wir.append(float(u["timestamp_deviation_s"]))
        dev_er.append(er - kopf)
        diff.append(wir - er)
        via_wir += u["cmpctblock"] == "yes"
        via_er += s["via"] == "compact"
        if u["missing_tx_estimate"] != "" and h in angefordert:
            fehl_wir.append(int(u["missing_tx_estimate"]))
            fehl_er.append(angefordert[h])

    fenster = [(zs(l["start_utc"]), zs(l["ende_utc"])) for l in zus["laeufe"]]
    reorgs_im_fenster = [r for r in reorgs if any(a <= zs(r["ts_local"]) <= b for a, b in fenster)]
    out = {
        "quelle_vergleich": QUELLE,
        "stand_rufitnes": args.stand,
        "bloecke_in_beiden": len(beide),
        "nur_counted": len(unsere) - len(beide),
        "timestamp_deviation_s": {"counted": kennzahlen(dev_wir, 3), QUELLE: kennzahlen(dev_er, 0)},
        "first_seen_counted_minus_rufitnes_s": kennzahlen(diff, 3),
        "hinweis_zeit": "rufitnes in ganzen Sekunden (Lesezeit der Logzeile), counted in Millisekunden; "
                        "beide Uhren nicht gegeneinander abgeglichen",
        "compact": {"counted_cmpctblock_bekommen": via_wir, QUELLE + " via compact": via_er, "von": len(beide)},
        "fehlende_tx": {"bloecke": len(fehl_wir),
                        "counted_geschaetzt": kennzahlen(fehl_wir, 1), QUELLE + " requested": kennzahlen(fehl_er, 1)},
        "reorg_ereignisse": {QUELLE: len(reorgs_im_fenster),
                             "counted_stale": zus["stale"]["anzahl"]},
    }
    with open(args.aus, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"bloecke_in_beiden": len(beide), "nur_counted": out["nur_counted"]}))


if __name__ == "__main__":
    main()
