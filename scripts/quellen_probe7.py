#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe7.py, die Distributionstabelle, letzte Runde.

Runde 7 hat null Buendel gefunden, aber das lag an meiner Suche und nicht
an der Seite: in Runde 2 stand im Quelltext ein Schnipsel
"mmutable/assets/DefaultTooltip.BvDJXtoG.css", da ist also sehr wohl etwas
eingebunden. Bevor hier "nicht abrufbar" steht, muss die Buendelsuche
wirklich gelaufen sein und nicht nur an einem Tippfehler vorbeigezielt
haben.

Diese Runde raet deshalb gar nichts mehr. Sie druckt, wie die Seite ihre
Dateien einbindet: jedes src=, jedes href=, jede Stelle mit "immutable".
Danach holt sie jede gefundene js-Datei und sucht darin nach der Adresse
der Tabelle.

    python3 scripts/quellen_probe7.py
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30
KOPF = {"Accept": "*/*", "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"}
BASIS = "https://www.kaspalytics.com"
SEITE = "/app/supply/distribution-table/KAS"

ATTR = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')
JSDATEI = re.compile(r'((?:\.\./|/)[A-Za-z0-9_\-./]+\.(?:js|mjs))')


def absolut(pfad, basis=BASIS + SEITE):
    """Die Seite bindet ihre Buendel relativ ein, mit ../../../_app/...
    Wer daraus mit Abschneiden eine Adresse baut, bekommt 400 und haelt das
    dann faelschlich fuer 'es gibt keine Buendel'. Genau das ist in Runde 8
    passiert, deshalb rechnet hier urljoin und nicht ich."""
    return urllib.parse.urljoin(basis, pfad)
API = re.compile(r'["\'`](/api/[A-Za-z0-9_\-/{}$.:?=]*)["\'`]')


def hole(url):
    try:
        req = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as exc:                       # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(t, n=800):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def umfeld(text, muster, spanne=260, hoechstens=10):
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
        return "kein JSON"
    if isinstance(d, dict):
        return "objekt, schluessel %s" % sorted(d.keys())[:20]
    if isinstance(d, list):
        e = d[0] if d else None
        return "liste, %d eintraege, erster %s" % (
            len(d), sorted(e.keys())[:20] if isinstance(e, dict) else type(e).__name__)
    return type(d).__name__


def main():
    st, html = hole(BASIS + SEITE)
    print("seite %s  http %s, %d zeichen" % (SEITE, st, len(html)))
    if st != 200:
        return 1

    attrs = sorted(set(ATTR.findall(html)))
    print("\nalle src= und href= der seite (%d):" % len(attrs))
    for a in attrs[:60]:
        print("   %s" % a)

    print("\njede stelle mit 'immutable':")
    for u in umfeld(html, r"immutable", 220, 6):
        print("   … %s" % kurz(u, 260))

    js = sorted({absolut(x) for x in JSDATEI.findall(html)})
    js = [u for u in js if u.startswith(BASIS)]
    print("\njs-dateien im quelltext (%d):" % len(js))
    for u in js[:20]:
        print("   %s" % u)

    quelltexte = {}
    for d in js[:40]:
        s, txt = hole(d)
        print("   %s  http %s, %d zeichen" % (d, s, len(txt)))
        if s == 200:
            quelltexte[d] = txt

    # zwei ebenen tiefer, die einstiegsbuendel nennen die eigentlichen
    for runde in (1, 2):
        tiefer = set()
        for d, txt in list(quelltexte.items()):
            for c in JSDATEI.findall(txt):
                tiefer.add(absolut(c, d))
        tiefer = {u for u in tiefer if u.startswith(BASIS)} - set(quelltexte)
        print("\nebene %d: %d weitere js-dateien genannt, davon werden 60 gelesen"
              % (runde, len(tiefer)))
        for d in sorted(tiefer)[:60]:
            s, txt = hole(d)
            if s == 200:
                quelltexte[d] = txt
    print("%d dateien gelesen, %d zeichen zusammen"
          % (len(quelltexte), sum(len(x) for x in quelltexte.values())))

    alle = set()
    for txt in quelltexte.values():
        alle |= set(API.findall(txt))
    print("\nalle /api-adressen in den dateien (%d):" % len(alle))
    for a in sorted(alle)[:80]:
        print("   %s" % a)

    for wort in ("distribution-table", "distribution", "cohort", "Shrimp"):
        treffer = [d for d, t in quelltexte.items() if re.search(wort, t, re.I)]
        print("\n'%s' in %d dateien: %s" % (wort, len(treffer), treffer[:3]))
        for d in treffer[:2]:
            for u in umfeld(quelltexte[d], re.escape(wort), 300, 3):
                print("     … %s" % kurz(u, 340))

    kandidaten = [a for a in sorted(alle) if "{" not in a and "$" not in a
                  and re.search(r"distrib|cohort|supply|address", a, re.I)]
    print("\n--- die passenden adressen abfragen ---")
    gefunden = []
    for k in kandidaten[:20]:
        s, txt = hole(BASIS + k)
        if s != 200:
            print("   %-54s http %s" % (k, s))
            continue
        print("   %-54s http 200  %s" % (k, form(txt)))
        print("       roh: %s" % kurz(txt, 800))
        gefunden.append(k)

    print()
    print("ERGEBNIS: abrufbar unter %s" % ", ".join(gefunden) if gefunden else
          "ERGEBNIS: auch mit gelesenen buendeln keine adresse fuer die tabelle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
