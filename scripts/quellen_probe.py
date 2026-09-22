#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe.py, die Machbarkeitsfrage, einmal im Runner gestellt.

Der Container, in dem gearbeitet wird, kommt weder an kaspalytics.com noch
an kaspa.stream heran (der Proxy antwortet mit 403 auf den CONNECT). Jede
Aussage ueber "gibt es dort einen Endpunkt" muss deshalb aus dem Runner
kommen, nicht aus der Erinnerung. Diese Datei stellt genau zwei Fragen und
druckt die Rohantwort gekuerzt ins Log:

  1. Kaspalytics: gibt es unter /api/charts/covenants/... je eine Reihe fuer
     Transaktionen, Outputs und UTXO-Anzahl, taeglich, und ab wann?
  2. kaspa.stream: gibt es einen Endpunkt fuer die Verteilungstabelle
     (Aquaman bis Plankton) und fuer die Top-Adressen mit Label?

Gesucht wird nicht geraten: die Seiten laden ihre eigenen Zahlen per JSON,
die Adressen dieser Aufrufe stehen in ihren eigenen Skriptbuendeln. Die
Sonde liest die Seite, zieht die Skript-Adressen heraus, sucht darin nach
API-Pfaden und probiert am Ende die gefundenen und die naheliegenden
Kandidaten der Reihe nach. Gescraped wird nichts: aus HTML wird nur die
Adresse des Datenendpunkts gelesen, nie eine Zahl.

    python3 scripts/quellen_probe.py
"""

import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
KOPF = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
}

KASPALYTICS = "https://www.kaspalytics.com"
STREAM = "https://kaspa.stream"

# Kandidaten Kaspalytics. covenants/transactions ist seit August 2026 in
# scripts/kaspalytics.py im Einsatz und damit der bekannte Anker.
KL_KANDIDATEN = [
    "/api/charts/covenants/transactions",
    "/api/charts/covenants/outputs",
    "/api/charts/covenants/utxo-count",
    "/api/charts/covenants/utxos",
    "/api/charts/covenants/utxo",
    "/api/charts/covenants/count",
    "/api/charts/covenants/outputs/count",
    "/api/charts/covenants/utxo/count",
]

KL_SEITEN = [
    "/app/covenants/transactions",
    "/app/covenants/outputs",
    "/app/covenants/utxo-count",
]

# Kandidaten kaspa.stream. Die Verteilungstabelle steht auf /distribution,
# die Adressliste auf /addresses beziehungsweise /top-addresses.
ST_KANDIDATEN = [
    "/api/distribution",
    "/api/addresses/distribution",
    "/api/holders/distribution",
    "/api/stats/distribution",
    "/api/addresses/top",
    "/api/top-addresses",
    "/api/addresses",
    "/api/holders",
    "/api/rich-list",
    "/api/richlist",
]

ST_SEITEN = ["/", "/distribution", "/addresses", "/top-addresses", "/rich-list"]

PFAD = re.compile(r"""["'`](/api/[A-Za-z0-9_\-/{}$.:]+)["'`]""")
ABSOLUT = re.compile(r"""["'`](https?://[A-Za-z0-9_.\-]+/(?:api|v\d)/[A-Za-z0-9_\-/{}$.:]*)["'`]""")
SKRIPT = re.compile(r'<script[^>]+src="([^"]+)"')


def hole(url, roh=False):
    """Eine Antwort holen. Gibt (status, text) zurueck, scheitert nie laut:
    ein toter Endpunkt ist hier ein Ergebnis, kein Absturz."""
    try:
        req = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            b = r.read()
            if roh:
                return r.status, b
            return r.status, b.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read()[:400].decode("utf-8", "replace") if not roh else b"")
    except Exception as exc:                      # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(text, n=700):
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def form_report(text):
    """Beschreibt die Form einer JSON-Antwort, ohne sie ganz auszudrucken."""
    try:
        d = json.loads(text)
    except Exception:                             # noqa: BLE001
        return None, "kein JSON"
    if isinstance(d, dict):
        return d, "objekt, schluessel: %s" % sorted(d.keys())[:14]
    if isinstance(d, list):
        erst = d[0] if d else None
        form = sorted(erst.keys())[:14] if isinstance(erst, dict) else type(erst).__name__
        return d, "liste, %d eintraege, erster eintrag: %s" % (len(d), form)
    return d, type(d).__name__


def chart_spanne(d):
    """Bei einer Kaspalytics-Chartantwort: erster und letzter Tag, Reihen."""
    if not isinstance(d, dict):
        return None
    lab = d.get("labels") or []
    ds = d.get("datasets") or []
    if not lab or not ds:
        return None
    namen = [x.get("label") for x in ds]
    laengen = [len(x.get("data") or []) for x in ds]
    return {"von": lab[0], "bis": lab[-1], "tage": len(lab),
            "reihen": namen, "punkte": laengen}


def pfade_aus_bundles(basis, seiten, grenze=14):
    """Die Seite laden, ihre Skripte laden, darin nach /api/-Pfaden suchen.
    Das ist die Methode, mit der im August der Kaspalytics-Endpunkt gefunden
    wurde: die Seite verraet ihre eigene Datenquelle."""
    gefunden = set()
    skripte = []
    for s in seiten:
        st, txt = hole(basis + s)
        print("    seite %-18s http %s, %s zeichen" % (s, st, len(txt) if isinstance(txt, str) else "?"))
        if st != 200 or not isinstance(txt, str):
            continue
        for p in PFAD.findall(txt):
            gefunden.add(p)
        for p in ABSOLUT.findall(txt):
            gefunden.add(p)
        for src in SKRIPT.findall(txt):
            if src.startswith("http"):
                skripte.append(src)
            elif src.startswith("/"):
                skripte.append(basis + src)
    for js in skripte[:grenze]:
        st, txt = hole(js)
        if st != 200 or not isinstance(txt, str):
            continue
        for p in PFAD.findall(txt):
            gefunden.add(p)
        for p in ABSOLUT.findall(txt):
            gefunden.add(p)
    print("    %d skriptbuendel gelesen (von %d)" % (min(len(skripte), grenze), len(skripte)))
    return sorted(gefunden)


def probiere(basis, kandidaten, ueberschrift):
    print("\n  %s" % ueberschrift)
    treffer = []
    for p in kandidaten:
        url = basis + p
        st, txt = hole(url)
        if st != 200:
            print("    %-46s http %s" % (p, st))
            continue
        d, form = form_report(txt)
        sp = chart_spanne(d)
        print("    %-46s http 200  %s" % (p, form))
        if sp:
            print("        %d tage, %s bis %s, reihen %s"
                  % (sp["tage"], sp["von"], sp["bis"], sp["reihen"]))
        print("        roh: %s" % kurz(txt, 500))
        treffer.append((p, d, sp))
    return treffer


def main():
    print("=" * 78)
    print("MACHBARKEIT 1  KASPALYTICS, COVENANTS")
    print("=" * 78)
    print("  was die seiten selbst aufrufen:")
    pf = pfade_aus_bundles(KASPALYTICS, KL_SEITEN)
    cov = [p for p in pf if "covenant" in p.lower()]
    print("    /api-pfade mit 'covenant' im namen: %s" % (cov or "keine gefunden"))
    print("    alle gefundenen /api-pfade (erste 40):")
    for p in pf[:40]:
        print("      %s" % p)

    kand = list(dict.fromkeys(cov + KL_KANDIDATEN))
    probiere(KASPALYTICS, kand, "endpunkte der reihe nach:")

    print("\n" + "=" * 78)
    print("MACHBARKEIT 2  KASPA.STREAM, VERTEILUNG UND TOP-ADRESSEN")
    print("=" * 78)
    print("  was die seiten selbst aufrufen:")
    pf2 = pfade_aus_bundles(STREAM, ST_SEITEN)
    interessant = [p for p in pf2 if re.search(r"distrib|holder|address|rich|top|balance", p, re.I)]
    print("    passende /api-pfade: %s" % (interessant or "keine gefunden"))
    print("    alle gefundenen pfade (erste 60):")
    for p in pf2[:60]:
        print("      %s" % p)

    kand2 = [p for p in dict.fromkeys(interessant + ST_KANDIDATEN) if "{" not in p and "$" not in p]
    probiere(STREAM, kand2, "endpunkte der reihe nach:")
    print("\nfertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
