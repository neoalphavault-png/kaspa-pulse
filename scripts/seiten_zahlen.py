#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seiten_zahlen.py, schreibt Zahlen zur Buildzeit ins statische HTML (Ben, 06.10.2026, SEO-Ausbau).

Suchmaschinen lesen das HTML, nicht das, was ein Skript im Browser spaeter
nachlaedt. Deshalb stehen die Antwortsaetze mit ihren Zahlen fest im
Quelltext, zwischen Marken <!--AUTO:name--> und <!--/AUTO:name-->, und dieses
Skript erneuert sie aus den Daten, die die Workflows ohnehin schreiben. Jede
Zahl traegt ihr Datum und ihre Quelle.

  supply-antwort   kaspa-supply.html           aus data/weekly.json (api.kaspa.org/info/coinsupply)
  covenant-zahl    kaspa-smart-contracts.html  aus data/covenants-log.json (Kaspalytics)

Faellt eine Quelle aus oder fehlt ein Wert, bleibt der alte Satz stehen.
Lieber ein Satz mit altem Datum als einer ohne Datum.

    python3 scripts/seiten_zahlen.py
    python3 scripts/seiten_zahlen.py --selbsttest
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MONATE = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def datum(iso):
    d = dt.date.fromisoformat(str(iso)[:10])
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def ganz(n):
    return "{:,}".format(int(round(n)))


def lies_json(pfad):
    try:
        return json.loads((REPO / pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def supply_satz(w):
    """There are 27,738,976,506 KAS in circulation as of 5 October 2026, ..."""
    if not w:
        return None
    circ = w.get("circ_supply")
    cf = w.get("context_fallback") or {}
    pct = cf.get("mined_pct")
    stand = w.get("circ_supply_as_of")
    if not (circ and pct and stand):
        return None
    return ("There are <b>%s KAS</b> in circulation as of %s, which is <b>%.2f%%</b> of the maximum supply of "
            "about <b>28.7 billion KAS</b>, according to api.kaspa.org." % (ganz(circ), datum(stand), pct))


def covenant_satz(log):
    if not log:
        return None
    tage = [e for e in log.get("tage") or [] if e.get("utxo_count") is not None]
    if not tage:
        return None
    e = tage[-1]
    return ("On layer 1, <b>%s covenant outputs</b> were unspent on chain at the end of %s, counted by "
            "Kaspalytics and logged in <a href=\"/kaspa-covenants.html\">our daily covenant count</a>."
            % (ganz(e["utxo_count"]), datum(e["datum"])))


AUFGABEN = [
    ("kaspa-supply.html", "supply-antwort", lambda: supply_satz(lies_json("data/weekly.json"))),
    ("kaspa-smart-contracts.html", "covenant-zahl", lambda: covenant_satz(lies_json("data/covenants-log.json"))),
]


def ersetze(s, name, inhalt):
    m = re.compile(r"(<!--AUTO:%s-->)(.*?)(<!--/AUTO:%s-->)" % (re.escape(name), re.escape(name)), re.S)
    if not m.search(s):
        raise SystemExit("marke %s fehlt" % name)
    return m.sub(lambda x: x.group(1) + inhalt + x.group(3), s, count=1)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--selbsttest"]:
        return selbsttest()
    for datei, name, quelle in AUFGABEN:
        p = REPO / datei
        s = p.read_text(encoding="utf-8")
        satz = quelle()
        if satz is None:
            print("%s, %s, keine daten, alter satz bleibt" % (datei, name))
            continue
        n = ersetze(s, name, satz)
        if n != s:
            p.write_text(n, encoding="utf-8")
            print("%s, %s, neu" % (datei, name))
        else:
            print("%s, %s, unveraendert" % (datei, name))
    return 0


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    w = {"circ_supply": 27738976506, "circ_supply_as_of": "2026-10-05T06:45:07Z",
         "context_fallback": {"mined_pct": 96.64}}
    ok("supply-satz", supply_satz(w) == "There are <b>27,738,976,506 KAS</b> in circulation as of 5 October 2026, "
       "which is <b>96.64%</b> of the maximum supply of about <b>28.7 billion KAS</b>, according to api.kaspa.org.")
    ok("supply ohne prozent bleibt leer", supply_satz({"circ_supply": 1, "circ_supply_as_of": "2026-10-05"}) is None)
    log = {"tage": [{"datum": "2026-10-03", "utxo_count": 13707}, {"datum": "2026-10-04", "utxo_count": 13760},
                    {"datum": "2026-10-05", "utxo_count": None}]}
    ok("covenant-satz nimmt den letzten tag mit bestand", "13,760 covenant outputs" in covenant_satz(log)
       and "4 October 2026" in covenant_satz(log))
    ok("ersetzen zwischen marken", ersetze("a<!--AUTO:x-->alt<!--/AUTO:x-->b", "x", "neu")
       == "a<!--AUTO:x-->neu<!--/AUTO:x-->b")
    print("%d fehler" % len(f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
