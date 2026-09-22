#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe5.py, die Distributionstabelle bei Kaspalytics, zweiter Anlauf.

Runde 5 (Lauf 35707239828) hat die Seite gefunden:

    /app/supply/distribution-table/KAS   "Distribution Table"

Die sonst verlaessliche Regel "zu /app/X gehoert /api/charts/X" greift hier
aber nicht, /api/charts/supply/distribution-table/KAS antwortet 404. Das ist
auch plausibel: die anderen Eintraege sind Diagramme, dieser ist eine
Tabelle, und eine Tabelle muss nicht unter /charts/ liegen.

Zwei Wege, beide ohne Raten ins Blaue:

  1. Die Seite selbst lesen und nachsehen, welche Adressen in ihrem
     Quelltext stehen. Kaspalytics ist eine SvelteKit-Anwendung; solche
     Seiten legen ihre Routendaten neben der Route unter __data.json ab,
     und genau das wird mitprobiert.
  2. Eine Handvoll Namensvarianten, die sich aus dem Seitenpfad ergeben,
     nicht aus der Fantasie.

    python3 scripts/quellen_probe5.py
"""

import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
KOPF = {"Accept": "*/*", "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"}
BASIS = "https://www.kaspalytics.com"
SEITE = "/app/supply/distribution-table/KAS"


def hole(url):
    try:
        req = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()[:400].decode("utf-8", "replace")
        except Exception:                          # noqa: BLE001
            return e.code, ""
    except Exception as exc:                       # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(t, n=1200):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def form(text):
    try:
        d = json.loads(text)
    except Exception:                              # noqa: BLE001
        return None, "kein JSON"
    if isinstance(d, dict):
        return d, "objekt, schluessel %s" % sorted(d.keys())[:20]
    if isinstance(d, list):
        e = d[0] if d else None
        return d, "liste, %d eintraege, erster %s" % (
            len(d), sorted(e.keys())[:20] if isinstance(e, dict) else type(e).__name__)
    return d, type(d).__name__


def umfeld(text, muster, spanne=280, hoechstens=10):
    aus = []
    for m in re.finditer(muster, text, re.I):
        a = max(0, m.start() - spanne // 2)
        aus.append(text[a:m.end() + spanne // 2])
        if len(aus) >= hoechstens:
            break
    return aus


def main():
    print("=" * 78)
    print("DIE SEITE SELBST")
    print("=" * 78)
    st, html = hole(BASIS + SEITE)
    print("  %s  http %s, %d zeichen" % (SEITE, st, len(html)))
    if st == 200:
        for u in umfeld(html, r'name="description"[^>]*', 340, 2):
            print("    %s" % kurz(u, 420))
        # die stufennamen taeten es verraten, falls die tabelle server-seitig
        # gerendert wird
        for wort in ("Shrimp", "Whale", "Plankton", "distribution-table", "cohort"):
            n = len(re.findall(re.escape(wort), html, re.I))
            print("    '%s' kommt %d mal vor" % (wort, n))
        pfade = sorted(set(re.findall(r'["\'(](/[a-z0-9][A-Za-z0-9_\-/.]*\.json[^"\')]*)', html)))
        print("    .json-adressen im quelltext: %s" % (pfade[:20] or "keine"))
        api = sorted(set(re.findall(r'["\'(](/api/[A-Za-z0-9_\-/.{}$]*)', html)))
        print("    /api-adressen im quelltext:  %s" % (api[:20] or "keine"))

    print("\n" + "=" * 78)
    print("KANDIDATEN")
    print("=" * 78)
    kandidaten = [
        # sveltekit legt routendaten neben die route
        SEITE + "/__data.json",
        SEITE.rsplit("/", 1)[0] + "/__data.json",
        # tabelle statt chart
        "/api/tables/supply/distribution-table/KAS",
        "/api/table/supply/distribution-table/KAS",
        "/api/supply/distribution-table/KAS",
        "/api/supply/distribution-table",
        "/api/distribution-table/KAS",
        "/api/distribution-table",
        # doch unter charts, aber anders geschrieben
        "/api/charts/supply/distribution-table",
        "/api/charts/supply/distribution-table/kas",
        "/api/charts/supply/distribution/KAS",
        # der ticker koennte ein parameter sein
        "/api/charts/supply/distribution-table?ticker=KAS",
    ]
    gefunden = []
    for k in dict.fromkeys(kandidaten):
        st, txt = hole(BASIS + k)
        if st != 200:
            print("  %-52s http %s" % (k, st))
            continue
        d, f = form(txt)
        print("  %-52s http 200  %s" % (k, f))
        print("      roh: %s" % kurz(txt, 1200))
        gefunden.append(k)

    print()
    if gefunden:
        print("ERGEBNIS: abrufbar unter %s" % ", ".join(gefunden))
    else:
        print("ERGEBNIS: kein endpunkt geantwortet. die tabelle ist von aussen")
        print("nicht als JSON oder CSV zu haben, jedenfalls nicht auf diesen wegen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
