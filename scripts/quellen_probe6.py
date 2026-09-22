#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe6.py, die Distributionstabelle, letzter Anlauf.

Stand nach Runde 6 (Lauf 35707450692):

  /app/supply/distribution-table/KAS            gibt es, http 200
  /app/supply/distribution-table/KAS/__data.json  antwortet, ist aber leer:
      {"type":"data","nodes":[null,null,null]}
  elf geratene /api-pfade                        alle 404
  im seitenquelltext                             keine /api- und keine
                                                 .json-adresse, und die
                                                 stufennamen kommen null
                                                 mal vor

Die Tabelle wird also erst im Browser gefuellt, und die Adresse dafuer
steht im Skriptbuendel. In Runde 2 wurden bei Kaspalytics null Buendel
gelesen, weil der Pfad dort nicht /_next/ oder /assets/ heisst, sondern
/_app/immutable/. Diese Runde holt genau die und sucht darin nach
"distribution", "cohort" und nach allem, was wie ein Endpunkt aussieht.

Findet auch das nichts, ist die Tabelle von aussen nicht als Datei zu
haben, und dann wird sie nicht gebaut.

    python3 scripts/quellen_probe6.py
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

DATEI = re.compile(r'["\'(](/_app/immutable/[A-Za-z0-9_\-./]+\.(?:js|mjs))')
CHUNK = re.compile(r'["\']\.?\.?(/_app/immutable/[A-Za-z0-9_\-./]+\.(?:js|mjs))["\']')
API = re.compile(r'["\'`](/api/[A-Za-z0-9_\-/{}$.:?=]*)["\'`]')


def hole(url):
    try:
        req = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()[:300].decode("utf-8", "replace")
        except Exception:                          # noqa: BLE001
            return e.code, ""
    except Exception as exc:                       # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(t, n=900):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def umfeld(text, muster, spanne=300, hoechstens=8):
    aus = []
    for m in re.finditer(muster, text, re.I):
        a = max(0, m.start() - spanne // 2)
        aus.append(text[a:m.end() + spanne // 2])
        if len(aus) >= hoechstens:
            break
    return aus


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


def main():
    st, html = hole(BASIS + SEITE)
    print("seite %s  http %s, %d zeichen" % (SEITE, st, len(html)))
    if st != 200:
        return 1

    dateien = sorted(set(DATEI.findall(html)))
    print("\n%d buendel im seitenquelltext:" % len(dateien))
    for d in dateien[:40]:
        print("   %s" % d)

    quelltexte = {}
    for d in dateien[:40]:
        s, txt = hole(BASIS + d)
        if s == 200:
            quelltexte[d] = txt
    print("\n%d buendel gelesen, %d zeichen zusammen"
          % (len(quelltexte), sum(len(x) for x in quelltexte.values())))

    # eine ebene tiefer, die buendel nennen ihre eigenen nachbarn
    tiefer = set()
    for txt in list(quelltexte.values()):
        for c in CHUNK.findall(txt):
            tiefer.add(c)
    tiefer -= set(quelltexte)
    print("%d weitere buendel genannt, davon werden 40 gelesen" % len(tiefer))
    for d in sorted(tiefer)[:40]:
        s, txt = hole(BASIS + d)
        if s == 200:
            quelltexte[d] = txt

    print("\n--- was in den buendeln steht ---")
    alle_api = set()
    for d, txt in quelltexte.items():
        for a in API.findall(txt):
            alle_api.add(a)
    print("alle /api-adressen (%d):" % len(alle_api))
    for a in sorted(alle_api)[:80]:
        print("   %s" % a)

    for wort in ("distribution-table", "distribution", "cohort", "Shrimp", "Plankton"):
        treffer = [d for d, t in quelltexte.items() if re.search(wort, t, re.I)]
        print("\n'%s' in %d buendeln: %s" % (wort, len(treffer), treffer[:4]))
        for d in treffer[:2]:
            for u in umfeld(quelltexte[d], re.escape(wort), 320, 4):
                print("     … %s" % kurz(u, 380))

    kandidaten = [a for a in sorted(alle_api)
                  if "{" not in a and "$" not in a
                  and re.search(r"distrib|cohort|supply|address", a, re.I)]
    print("\n--- die passenden adressen abfragen ---")
    gefunden = []
    for k in kandidaten[:20]:
        s, txt = hole(BASIS + k)
        if s != 200:
            print("   %-54s http %s" % (k, s))
            continue
        d, f = form(txt)
        print("   %-54s http 200  %s" % (k, f))
        print("       roh: %s" % kurz(txt, 900))
        gefunden.append(k)

    print()
    if gefunden:
        print("ERGEBNIS: abrufbar unter %s" % ", ".join(gefunden))
    else:
        print("ERGEBNIS: die distributionstabelle ist von aussen nicht als")
        print("JSON oder CSV zu haben. keine adresse im buendel, keine im")
        print("seitenquelltext, __data.json leer, alle geratenen pfade 404.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
