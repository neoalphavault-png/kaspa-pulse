#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""holders_quelle.py, die offene Frage aus week-input.json, einmal gestellt.

In data/week-input.json steht seit dem 21.09.2026 dieser Hinweis:

    "holders": "quelle ungeklaert seit 21.09. der wert 792098 stammt aus
     der vorwoche; keine kaspalytics-seite im menue liefert diese zahl.
     bis die quelle steht, wird der wert uebernommen und im read genannt."

Ein uebernommener Wert ist eine Zahl, die niemand mehr gemessen hat. Solange
das so bleibt, steht in jedem Montagspost eine Zahl, fuer die es keinen
Zaehltag gibt. Diese Datei beantwortet die Frage nicht durch Nachdenken,
sondern durch Hinsehen: sie holt die Reihe, die scripts/kaspalytics.py
laengst als holder_addr liest, und stellt jeden Tag der letzten drei Wochen
gegen den uebernommenen Wert.

    /api/charts/address/count/meaningful-balance   reihe "Addresses"

Trifft ein Tag den Wert 792098 genau, ist die Quelle gefunden und die
Montagsroutine kann das Feld kuenftig selbst fuellen, ohne eine einzige
neue Abfrage: kaspalytics.py holt diese Reihe bereits.

    python3 scripts/holders_quelle.py
"""

import datetime as dt
import json
import sys
import urllib.request

URL = ("https://www.kaspalytics.com/api/charts/"
       "address/count/meaningful-balance")
GESUCHT = 792098          # der uebernommene wert aus week-input.json
TAGE = 21


def hole(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def tag_von(label):
    return dt.date.fromisoformat(str(label).replace("Z", "").split("T")[0])


def main():
    d = hole(URL)
    labels = d.get("labels") or []
    reihe = None
    for ds in d.get("datasets") or []:
        if str(ds.get("label", "")).strip().lower() == "addresses":
            reihe = ds.get("data") or []
    if reihe is None:
        print("reihe 'Addresses' nicht gefunden, vorhanden: %s"
              % [x.get("label") for x in d.get("datasets") or []])
        return 1

    paare = []
    for i, lab in enumerate(labels):
        if i >= len(reihe) or reihe[i] is None:
            continue
        paare.append((tag_von(lab), int(round(float(reihe[i])))))
    paare.sort()
    print("endpunkt %s" % URL)
    print("reihe    Addresses, %d tage, %s bis %s"
          % (len(paare), paare[0][0], paare[-1][0]))
    print("gesucht  %d, der uebernommene wert aus data/week-input.json\n" % GESUCHT)

    treffer = [t for t, w in paare if w == GESUCHT]
    for tag, wert in paare[-TAGE:]:
        marke = "  <== genau der uebernommene wert" if wert == GESUCHT else ""
        print("  %s  %8d%s" % (tag, wert, marke))

    print()
    if treffer:
        print("TREFFER. der wert %d steht in dieser reihe am %s."
              % (GESUCHT, ", ".join(str(t) for t in treffer)))
        print("damit ist die quelle geklaert: es ist dieselbe reihe, die")
        print("scripts/kaspalytics.py bereits als holder_addr liest.")
    else:
        nah = min(paare, key=lambda p: abs(p[1] - GESUCHT))
        print("KEIN exakter treffer in dieser reihe.")
        print("am naechsten liegt der %s mit %d, das sind %+d."
              % (nah[0], nah[1], nah[1] - GESUCHT))
        print("die reihe passt in groessenordnung und richtung, beweist die")
        print("herkunft des uebernommenen wertes aber nicht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
