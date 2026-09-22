#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe8.py, die Verteilung bei Kaspalytics, der richtige Pfad.

Runde 8 hat mit aufgeloesten Buendelpfaden 64 Dateien gelesen und darin das
Routenverzeichnis der App gefunden. Darin stehen Seiten, die in der
Seitenleiste der Chartseiten nicht auftauchen und die genau die Frage
beantworten, um die es seit dem 22.09. geht:

    /app/distribution/kas-bucket                 stufen nach betrag
    /app/distribution/kas-bucket/[bucket]        eine stufe einzeln
    /app/distribution/kas-threshold/[threshold]  adressen ab einem betrag
    /app/address/count/non-zero-balance          adressen mit guthaben

und im Menue dazu die Schwellen "0.01+ KAS", "1+ KAS", "100+ KAS".

Das ist der Ersatz fuer das, was kaspa.stream nicht hergibt: kas-bucket
sind die Stufen, kas-threshold/1+ ist die Zahl der Halter ab einem KAS,
non-zero-balance die Zahl aller Halter. Diese Runde prueft, ob die
Chartregel "zu /app/X gehoert /api/charts/X" hier greift, und druckt die
Rohantworten.

Sie druckt ausserdem das vollstaendige Routenverzeichnis, damit nicht bei
der naechsten Frage wieder drei Runden lang gesucht wird.

    python3 scripts/quellen_probe8.py
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

JSDATEI = re.compile(r'((?:\.\./|/)[A-Za-z0-9_\-./]+\.(?:js|mjs))')
ROUTE = re.compile(r'"/\(sidebar\)(/app/[A-Za-z0-9_\-/\[\].+]*)"')


def hole(url):
    try:
        req = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as exc:                       # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(t, n=1100):
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


def spanne(d):
    if not isinstance(d, dict):
        return None
    lab, ds = d.get("labels") or [], d.get("datasets") or []
    if not lab or not ds:
        return None
    return "%d punkte, %s bis %s, reihen %s" % (
        len(lab), lab[0], lab[-1], [x.get("label") for x in ds])


def routenverzeichnis():
    st, html = hole(BASIS + SEITE)
    if st != 200:
        return []
    js = {urllib.parse.urljoin(BASIS + SEITE, x) for x in JSDATEI.findall(html)}
    texte = []
    for u in sorted(js):
        if not u.startswith(BASIS):
            continue
        s, t = hole(u)
        if s == 200:
            texte.append((u, t))
    # eine ebene tiefer, dort liegt das verzeichnis
    tiefer = set()
    for u, t in texte:
        for c in JSDATEI.findall(t):
            tiefer.add(urllib.parse.urljoin(u, c))
    for u in sorted(tiefer)[:60]:
        if not u.startswith(BASIS):
            continue
        s, t = hole(u)
        if s == 200 and "(sidebar)" in t:
            texte.append((u, t))
    routen = set()
    for _, t in texte:
        routen |= set(ROUTE.findall(t))
    return sorted(routen)


def probiere(pfade, ueberschrift):
    print("\n  %s" % ueberschrift)
    treffer = []
    for p in pfade:
        url = BASIS + p
        st, txt = hole(url)
        if st != 200:
            print("    %-58s http %s" % (p, st))
            continue
        d, f = form(txt)
        sp = spanne(d)
        print("    %-58s http 200  %s" % (p, f))
        if sp:
            print("        %s" % sp)
        print("        roh: %s" % kurz(txt, 1100))
        treffer.append(p)
    return treffer


def main():
    print("=" * 78)
    print("DAS ROUTENVERZEICHNIS DER APP")
    print("=" * 78)
    routen = routenverzeichnis()
    print("  %d seiten:" % len(routen))
    for r in routen:
        print("      %s" % r)

    verteilung = [r for r in routen
                  if re.search(r"distribution|threshold|bucket|balance|count", r, re.I)]
    print("\n  davon zur verteilung: %s" % verteilung)

    print("\n" + "=" * 78)
    print("DIE CHARTREGEL AUF DIESE SEITEN ANGEWENDET")
    print("=" * 78)
    kandidaten = []
    for r in verteilung:
        if "[" in r:
            continue
        kandidaten.append("/api/charts" + r[len("/app"):])
    # die schwellen aus dem menue, einmal roh und einmal kodiert
    for schwelle in ("0.01+", "1+", "100+", "1000+"):
        kandidaten.append("/api/charts/distribution/kas-threshold/" + schwelle)
        kandidaten.append("/api/charts/distribution/kas-threshold/"
                          + urllib.parse.quote(schwelle, safe=""))
    treffer = probiere(list(dict.fromkeys(kandidaten)), "endpunkte der reihe nach:")

    print("\n" + "=" * 78)
    print("DIE LETZTEN STAENDE DER ANTWORTENDEN REIHEN")
    print("=" * 78)
    print("  (zum vergleich: Bens handablesung vom 22.09. 08:59 nannte")
    print("   792.706 als summe aller stufen-counts auf kaspa.stream)\n")
    for p in treffer:
        if "%2B" in p:
            continue                    # dieselbe reihe, nur anders geschrieben
        st, txt = hole(BASIS + p)
        if st != 200:
            continue
        d, _ = form(txt)
        if not isinstance(d, dict):
            continue
        lab = d.get("labels") or []
        reihe = None
        for ds in d.get("datasets") or []:
            if str(ds.get("label", "")).strip().lower() != "price":
                reihe = ds
        if reihe is None:
            continue
        werte = reihe.get("data") or []
        print("  %s" % p)
        print("     reihe '%s'" % reihe.get("label"))
        for l, w in list(zip(lab, werte))[-3:]:
            print("     %-30s %s" % (l, w))

    print()
    if treffer:
        print("ERGEBNIS: abrufbar. %d endpunkte antworten:" % len(treffer))
        for t in treffer:
            print("   %s" % t)
    else:
        print("ERGEBNIS: keiner dieser endpunkte antwortet.")
    print("\nNICHT abrufbar, und darum ging es eigentlich:")
    print("   /api/charts/distribution/kas-bucket          404, die stufen")
    print("   /api/charts/supply/distribution-table/KAS    404, die tabelle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
