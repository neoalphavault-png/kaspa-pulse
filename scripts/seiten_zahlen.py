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
  hashrate         kaspa-hashrate.html         live aus api.kaspa.org/info/hashrate und
                                               /info/hashrate/history (braucht Netz)

Faellt eine Quelle aus oder fehlt ein Wert, bleibt der alte Satz stehen.
Lieber ein Satz mit altem Datum als einer ohne Datum.

    python3 scripts/seiten_zahlen.py
    python3 scripts/seiten_zahlen.py --selbsttest
"""
import datetime as dt
import json
import re
import sys
import urllib.request
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


REST = "https://api.kaspa.org"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"


def hole(pfad):
    req = urllib.request.Request(REST + pfad, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def hashrate_daten(jetzt=None):
    """Aktueller Wert (TH/s) und Tagesmittel aus der Historie (kH/s -> PH/s)."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    akt = hole("/info/hashrate?stringOnly=false")
    roh = hole("/info/hashrate/history")
    je = {}
    for x in roh:
        t = dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc)
        je.setdefault(t.date(), []).append(x["hashrate_kh"] / 1e12)
    return {"jetzt": jetzt, "ph": float(akt["hashrate"]) / 1e3,
            "tage": {d: sum(v) / len(v) for d, v in je.items()}}


def hashrate_html(d, wochen=8):
    if not d or not d.get("tage"):
        return None
    jetzt, tage = d["jetzt"], d["tage"]
    heute = jetzt.date()
    fertig = {t: v for t, v in tage.items() if t < heute}
    if not fertig:
        return None
    hoch_tag = max(fertig, key=lambda t: fertig[t])
    montag = heute - dt.timedelta(days=heute.weekday())
    zeilen = []
    for k in range(wochen, 0, -1):
        a = montag - dt.timedelta(weeks=k)
        werte = [fertig[a + dt.timedelta(days=i)] for i in range(7) if a + dt.timedelta(days=i) in fertig]
        if len(werte) == 7:
            zeilen.append("<tr><td>week of %s</td><td>%.1f PH/s</td></tr>" % (datum(a.isoformat()), sum(werte) / 7))
    satz = ("Kaspa's hashrate was <b>%.1f PH/s</b> on %s at %s UTC, according to api.kaspa.org. The highest daily "
            "average on record is <b>%.1f PH/s</b>, on %s." % (d["ph"], datum(jetzt.isoformat()),
                                                               jetzt.strftime("%H:%M"), fertig[hoch_tag],
                                                               datum(hoch_tag.isoformat())))
    tabelle = ("<table><thead><tr><th>Week, Monday to Sunday</th><th>Average hashrate</th></tr></thead><tbody>%s"
               "</tbody></table><p class=\"note\">Weekly averages of the daily means in api.kaspa.org's hashrate "
               "history, read on %s.</p>" % ("".join(zeilen), datum(jetzt.isoformat())))
    return {"hashrate-satz": satz, "hashrate-wochen": tabelle}


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
    aufgaben = list(AUFGABEN)
    if "--ohne-netz" not in argv:
        try:
            hr = hashrate_html(hashrate_daten())
        except Exception as exc:                    # noqa: BLE001
            print("kaspa-hashrate.html, api.kaspa.org nicht erreichbar (%s), alte saetze bleiben" % type(exc).__name__)
            hr = None
        for name in ("hashrate-satz", "hashrate-wochen"):
            aufgaben.append(("kaspa-hashrate.html", name, (lambda n=name: hr[n] if hr else None)))
    for datei, name, quelle in aufgaben:
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
    tage = {dt.date(2026, 8, 3) + dt.timedelta(days=i): 300.0 + (i % 7) for i in range(63)}
    tage[dt.date(2026, 8, 20)] = 512.34
    h = hashrate_html({"jetzt": dt.datetime(2026, 10, 6, 11, 5, tzinfo=dt.timezone.utc), "ph": 345.67, "tage": tage})
    ok("hashrate-satz mit zeit und allzeithoch", h["hashrate-satz"].startswith(
        "Kaspa's hashrate was <b>345.7 PH/s</b> on 6 October 2026 at 11:05 UTC")
       and "<b>512.3 PH/s</b>, on 20 August 2026" in h["hashrate-satz"])
    ok("acht volle wochen, die laufende nicht", h["hashrate-wochen"].count("<tr><td>week of") == 8
       and "week of 28 September 2026" in h["hashrate-wochen"] and "5 October" not in h["hashrate-wochen"])
    ok("ersetzen zwischen marken", ersetze("a<!--AUTO:x-->alt<!--/AUTO:x-->b", "x", "neu")
       == "a<!--AUTO:x-->neu<!--/AUTO:x-->b")
    print("%d fehler" % len(f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
