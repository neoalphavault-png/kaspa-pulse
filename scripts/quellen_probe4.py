#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe4.py, zwei Fragen an Kaspalytics, 22.09.2026.

FRAGE A, die Distributionstabelle.
kaspa.stream faellt als Quelle aus (Runde 3, Lauf 35702302746: kein
HTTP-Endpunkt, Zahlen nur ueber verschleierte socket.io-Verbindungen mit
eigener Anmeldung). Kaspalytics hat dafuer eine eigene Distribution Table,
Stufen nach Betrag. Diese Runde sucht sie auf demselben Weg, auf dem im
August der Chartendpunkt und am 22.09. die Covenant-UTXO-Reihe gefunden
wurden: die Seitenleiste der App nennt jede Seite, und zu jeder Seite
/app/X gehoert bisher immer ein Endpunkt /api/charts/X.

FRAGE B, die Zeitstempel der drei Bestandsreihen.
scripts/kaspalytics.py liest holder_addr, exchange_kas und holders mit dem
blossen Datum aus dem Zeitstempel. Bei Tagessummen geht das gut, bei
Momentaufnahmen nicht: am 06.09. standen in der holders-Reihe zwei Werte,
am 07.09. keiner. Bevor die Korrektur aus covenants_log.py dort einzieht,
muss klar sein, WANN diese Reihen gemessen werden. Bei den Covenant-UTXOs
war es Mitternacht mit Sekundenschlupf; die Versorgungsreihen sahen in
Runde 3 eher nach 09:00 UTC aus. Geraten wird nicht, gedruckt werden die
rohen Marken.

    python3 scripts/quellen_probe4.py
"""

import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
KOPF = {"Accept": "*/*", "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"}
BASIS = "https://www.kaspalytics.com"

# die drei reihen, die scripts/kaspalytics.py als momentaufnahme liest
BESTAENDE = {
    "holder_addr":  ("/api/charts/address/count/meaningful-balance", "Addresses"),
    "holders":      ("/api/charts/supply/inactive?minAge=1year", "CSPERCENT"),
    "exchange_kas": ("/api/charts/supply/exchange-holdings", "Balance"),
    # zum vergleich eine, die eine echte tagessumme ist
    "active_addr":  ("/api/charts/transactions/accepted/addresses/all", "Addresses"),
}

# seiten, aus deren seitenleiste die vollstaendige menueliste faellt
SEITEN = ["/app/covenants/transactions", "/app/utxo/covenant-count"]

MENUE = re.compile(r'href="(/app/[A-Za-z0-9\-/]+)"[^>]*>(?:<span>)?([^<]{2,60})')


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


def kurz(t, n=700):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def form(text):
    try:
        d = json.loads(text)
    except Exception:                              # noqa: BLE001
        return None, "kein JSON"
    if isinstance(d, dict):
        return d, "objekt, schluessel %s" % sorted(d.keys())[:18]
    if isinstance(d, list):
        e = d[0] if d else None
        return d, "liste, %d eintraege, erster %s" % (
            len(d), sorted(e.keys())[:18] if isinstance(e, dict) else type(e).__name__)
    return d, type(d).__name__


def frage_a():
    print("=" * 78)
    print("FRAGE A  GIBT ES BEI KASPALYTICS EINE DISTRIBUTIONSTABELLE")
    print("=" * 78)

    eintraege = {}
    for s in SEITEN:
        st, txt = hole(BASIS + s)
        print("  seite %-30s http %s, %d zeichen" % (s, st, len(txt)))
        if st != 200:
            continue
        for pfad, name in MENUE.findall(txt):
            name = " ".join(name.split())
            if name and not name.startswith("<"):
                eintraege.setdefault(pfad, name)

    print("\n  das vollstaendige menue der app (%d eintraege):" % len(eintraege))
    for pfad in sorted(eintraege):
        print("      %-40s %s" % (pfad, eintraege[pfad]))

    passend = [p for p, n in eintraege.items()
               if re.search(r"distrib|holder|balance|address|rich|wealth|cohort|segment",
                            p + " " + n, re.I)]
    print("\n  eintraege, die nach verteilung klingen: %s" % (passend or "keine"))

    # zu jeder seite /app/X gehoert bisher der endpunkt /api/charts/X
    kandidaten = ["/api/charts" + p[len("/app"):] for p in passend]
    kandidaten += [
        "/api/charts/address/distribution",
        "/api/charts/address/balance-distribution",
        "/api/charts/address/count/distribution",
        "/api/distribution",
        "/api/tables/distribution",
    ]
    print("\n  endpunkte der reihe nach:")
    treffer = []
    for k in dict.fromkeys(kandidaten):
        st, txt = hole(BASIS + k)
        if st != 200:
            print("    %-52s http %s" % (k, st))
            continue
        d, f = form(txt)
        print("    %-52s http 200  %s" % (k, f))
        print("        roh: %s" % kurz(txt, 900))
        treffer.append(k)
    if not treffer:
        print("\n  kein endpunkt geantwortet.")
    return treffer


def frage_b():
    print("\n" + "=" * 78)
    print("FRAGE B  WANN WERDEN DIE BESTANDSREIHEN GEMESSEN")
    print("=" * 78)
    for feld, (pfad, name) in BESTAENDE.items():
        st, txt = hole(BASIS + pfad)
        print("\n  %s  %s" % (feld, pfad))
        if st != 200:
            print("    http %s" % st)
            continue
        d = json.loads(txt)
        labels = d.get("labels") or []
        reihe = None
        for ds in d.get("datasets") or []:
            if str(ds.get("label", "")).strip().lower() == name.lower():
                reihe = ds.get("data") or []
        if reihe is None:
            print("    reihe %s nicht gefunden, vorhanden %s"
                  % (name, [x.get("label") for x in d.get("datasets") or []]))
            continue
        print("    %d punkte, erster %s, letzter %s" % (len(labels), labels[0], labels[-1]))
        # wie verteilen sich die uhrzeiten ueber die ganze reihe?
        stunden = {}
        for lab in labels:
            t = str(lab)
            h = t.split("T")[1][:2] if "T" in t else "??"
            stunden[h] = stunden.get(h, 0) + 1
        print("    uhrzeiten (stunde: anzahl): %s"
              % sorted(stunden.items(), key=lambda x: -x[1])[:8])
        # doppelte und fehlende kalendertage bei blossem datum
        tage = [str(lab).split("T")[0] for lab in labels]
        doppelt = sorted({t for t in tage if tage.count(t) > 1})
        print("    kalendertage mit zwei messungen: %d %s"
              % (len(doppelt), doppelt[-6:] if doppelt else ""))
        print("    die letzten 16 marken:")
        for lab, wert in list(zip(labels, reihe))[-16:]:
            print("      %-30s %s" % (lab, wert))


def main():
    frage_a()
    frage_b()
    print("\nfertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
