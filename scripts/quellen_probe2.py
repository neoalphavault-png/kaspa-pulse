#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe2.py, die zweite Runde der Machbarkeitsfrage.

Runde eins (scripts/quellen_probe.py, Lauf 35701693423) hat zwei Dinge
geklaert und zwei offen gelassen.

  geklaert   /api/charts/covenants/transactions  88 tage, reihen Transactions
             /api/charts/covenants/outputs       88 tage, reihen Created, Spent
  offen      die UTXO-Anzahl, alle geratenen Pfade antworten 404
  offen      kaspa.stream, jeder /api/-Pfad liefert die SPA-Startseite
             zurueck, die Daten kommen also von woanders her

Raten hilft hier nicht weiter. Diese Runde liest deshalb die Skriptbuendel
beider Seiten und sucht darin nach den Woertern, die nur an der gesuchten
Stelle stehen koennen: "covenant" bei Kaspalytics, die Stufennamen
"plankton" und "aquaman" bei kaspa.stream. Um jeden Treffer werden ein paar
hundert Zeichen gedruckt, damit die Adresse daneben sichtbar wird.

Auch hier wird nichts gescraped: aus den Dateien wird eine Adresse gelesen,
nie eine Zahl.

    python3 scripts/quellen_probe2.py
"""

import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
KOPF = {
    "Accept": "*/*",
    "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
}

KASPALYTICS = "https://www.kaspalytics.com"
STREAM = "https://kaspa.stream"

# alles, was nach einer mitgelieferten datei aussieht
DATEI = re.compile(r'["\'(]((?:/_next/static/|/assets/|/static/|/js/)[A-Za-z0-9_\-./]+\.(?:js|mjs|css))')
CHUNK = re.compile(r'["\']([A-Za-z0-9_\-./]+\.(?:js|mjs))["\']')
URL_ABS = re.compile(r'https?://[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_\-./{}$:]*)?')
API_PFAD = re.compile(r'["\'`](/(?:api|v1|v2)/[A-Za-z0-9_\-/{}$.:]*)["\'`]')


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


def kurz(t, n=600):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def umfeld(text, wort, spanne=260, hoechstens=6):
    """Druckt den Text um jeden Treffer herum. Das ist die eigentliche
    Arbeit: der Endpunkt steht fast immer als Zeichenkette direkt neben
    dem Wort, nach dem gesucht wird."""
    aus = []
    for m in re.finditer(re.escape(wort), text, re.I):
        a = max(0, m.start() - spanne // 2)
        aus.append(text[a:m.end() + spanne // 2])
        if len(aus) >= hoechstens:
            break
    return aus


def dateien_von(basis, seiten):
    """Alle mitgelieferten js-Dateien einer Seite einsammeln, eine Ebene
    tief den darin genannten Chunks folgen."""
    quelltexte = {}
    adressen = set()
    for s in seiten:
        st, txt = hole(basis + s)
        print("    seite %-28s http %s, %s zeichen" % (s, st, len(txt)))
        if st != 200:
            continue
        quelltexte[basis + s] = txt
        for p in DATEI.findall(txt):
            adressen.add(basis + p)
    erste = sorted(adressen)
    print("    %d mitgelieferte dateien in den seiten" % len(erste))
    for a in erste[:25]:
        st, txt = hole(a)
        if st != 200:
            print("      %s http %s" % (a, st))
            continue
        quelltexte[a] = txt
        print("      %s  %d zeichen" % (a, len(txt)))
    # eine ebene tiefer: chunknamen, die in den dateien selbst stehen
    tiefer = set()
    for a, txt in list(quelltexte.items()):
        if not a.endswith((".js", ".mjs")):
            continue
        wurzel = a.rsplit("/", 1)[0]
        for c in CHUNK.findall(txt)[:400]:
            if c.startswith("/"):
                tiefer.add(basis + c)
            elif "/" not in c and len(c) < 60:
                tiefer.add(wurzel + "/" + c)
    tiefer -= set(quelltexte)
    print("    %d weitere chunks genannt, davon werden 25 gelesen" % len(tiefer))
    for a in sorted(tiefer)[:25]:
        st, txt = hole(a)
        if st == 200:
            quelltexte[a] = txt
    return quelltexte


def suche(quelltexte, woerter, ueberschrift):
    print("\n  %s" % ueberschrift)
    gefunden = False
    for a, txt in quelltexte.items():
        for w in woerter:
            if re.search(re.escape(w), txt, re.I):
                gefunden = True
                print("    treffer '%s' in %s" % (w, a))
                for u in umfeld(txt, w):
                    print("      … %s" % kurz(u, 420))
    if not gefunden:
        print("    kein treffer fuer %s" % woerter)
    return gefunden


def alle_adressen(quelltexte, muster=None):
    aus = set()
    for txt in quelltexte.values():
        for u in URL_ABS.findall(txt):
            if muster and not re.search(muster, u, re.I):
                continue
            aus.add(u)
        for p in API_PFAD.findall(txt):
            aus.add(p)
    return sorted(aus)


def form(text):
    try:
        d = json.loads(text)
    except Exception:                              # noqa: BLE001
        return None, "kein JSON"
    if isinstance(d, dict):
        return d, "objekt, schluessel %s" % sorted(d.keys())[:16]
    if isinstance(d, list):
        e = d[0] if d else None
        return d, "liste, %d eintraege, erster %s" % (
            len(d), sorted(e.keys())[:16] if isinstance(e, dict) else type(e).__name__)
    return d, type(d).__name__


def probiere(kandidaten, ueberschrift):
    print("\n  %s" % ueberschrift)
    for u in kandidaten:
        st, txt = hole(u)
        if st != 200:
            print("    %-64s http %s" % (u, st))
            continue
        d, f = form(txt)
        print("    %-64s http 200  %s" % (u, f))
        print("        roh: %s" % kurz(txt, 620))


def main():
    print("=" * 78)
    print("RUNDE 2 A  KASPALYTICS, WO STECKT DIE UTXO-ANZAHL")
    print("=" * 78)
    kl = dateien_von(KASPALYTICS, ["/app/covenants/transactions",
                                   "/app/covenants/outputs",
                                   "/app/covenants"])
    suche(kl, ["covenants/"], "zeichenketten mit 'covenants/':")
    suche(kl, ["utxo"], "zeichenketten mit 'utxo':")
    print("\n  alle genannten api-adressen (erste 50):")
    for a in alle_adressen(kl, r"/api/|kaspalytics")[:50]:
        print("      %s" % a)

    probiere([KASPALYTICS + p for p in [
        "/api/charts/covenants/utxo-set",
        "/api/charts/covenants/unspent",
        "/api/charts/covenants/unspent-outputs",
        "/api/charts/covenants/utxoCount",
        "/api/charts/covenants/utxo_count",
        "/api/charts/covenants/outputs/unspent",
        "/api/charts/covenants",
        "/api/charts/covenants/summary",
        "/api/charts/covenants/stats",
    ]], "weitere kandidaten:")

    print("\n" + "=" * 78)
    print("RUNDE 2 B  KASPA.STREAM, WO KOMMEN DIE ZAHLEN HER")
    print("=" * 78)
    st_q = dateien_von(STREAM, ["/", "/distribution"])
    suche(st_q, ["plankton"], "zeichenketten mit 'plankton':")
    suche(st_q, ["aquaman"], "zeichenketten mit 'aquaman':")
    suche(st_q, ["distribution"], "zeichenketten mit 'distribution':")
    print("\n  alle genannten adressen ausserhalb der seite (erste 60):")
    for a in alle_adressen(st_q, r"api|kaspa|/v\d/")[:60]:
        print("      %s" % a)
    print("\nfertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
