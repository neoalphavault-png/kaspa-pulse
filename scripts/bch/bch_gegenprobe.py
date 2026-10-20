#!/usr/bin/env python3
"""bch_gegenprobe.py - Gegenprobe der eigenen Tempnet-Koepfe gegen chaingraph.

Quelle der Zahlen sind unsere eigenen Header (tempnet_koepfe.py). chaingraph
(tempnet.chaingraph.cash, Ben 20.10.2026) dient nur als Gegenprobe, im Bericht
als "source chaingraph" gekennzeichnet: fuer Stichproben-Hoehen fragen wir die
Block-Hashes ab und vergleichen. Scheitert die Abfrage, steht das mit Grund in
der Ausgabe; der Lauf geht weiter.

  python3 scripts/bch/bch_gegenprobe.py --koepfe data/bch/tempnet-koepfe.csv.gz --aus data/bch/gegenprobe.json
"""
import argparse
import csv
import gzip
import json
import os
import urllib.error
import urllib.request

ENDPUNKT = os.environ.get("BCH_CHAINGRAPH", "https://tempnet.chaingraph.cash/v1/graphql")
ERSTER = 327_989


def abfragen(hoehen):
    q = "query($h:[bigint!]!){block(where:{height:{_in:$h}}){hash height}}"
    daten = json.dumps({"query": q, "variables": {"h": [str(x) for x in hoehen]}}).encode()
    req = urllib.request.Request(ENDPUNKT, data=daten, headers={"content-type": "application/json",
                                                                 "user-agent": "kaspa-pulse-gegenprobe/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        antwort = json.load(r)
    if "errors" in antwort:
        raise ValueError(str(antwort["errors"])[:200])
    out = {}
    for b in antwort["data"]["block"]:
        out.setdefault(int(b["height"]), set()).add(b["hash"].lower().replace("\\x", ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--aus", required=True)
    ap.add_argument("--schritt", type=int, default=500)
    args = ap.parse_args()
    with gzip.open(args.koepfe, "rt") as f:
        unsere = {int(z["hoehe"]): z["hash"] for z in csv.DictReader(f)}
    spitze = max(unsere)
    proben = sorted({ERSTER, *range(ERSTER, spitze - 10, args.schritt), spitze - 10, spitze - 100})
    proben = [h for h in proben if h in unsere]
    ergebnis = {"quelle": "source chaingraph", "endpunkt": ENDPUNKT, "proben": len(proben)}
    try:
        cg = {}
        for i in range(0, len(proben), 100):
            cg.update(abfragen(proben[i:i + 100]))
        gleich = sum(1 for h in proben if unsere[h] in cg.get(h, set()))
        fehlt = [h for h in proben if h not in cg]
        anders = [h for h in proben if h in cg and unsere[h] not in cg[h]]
        ergebnis.update({"verglichen": len(proben) - len(fehlt), "gleich": gleich,
                         "bei_chaingraph_fehlend": fehlt[:20], "abweichend": anders[:20]})
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as e:
        ergebnis.update({"verglichen": 0, "gleich": 0, "fehler": f"{type(e).__name__}: {str(e)[:120]}"})
    with open(args.aus, "w") as f:
        json.dump(ergebnis, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: ergebnis.get(k) for k in ("proben", "verglichen", "gleich", "fehler")}))


if __name__ == "__main__":
    main()
