#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe.py, die Fragen an fremde Quellen, an einer Stelle.

Zwischen dem 22. und dem 23.09.2026 sind hier neun einzelne Sondendateien
entstanden, eine je Frage, quellen_probe2 bis quellen_probe8 und
holders_quelle. Jede war fuer sich richtig und zusammen waren sie ein
Haufen. Diese Datei fasst sie zusammen, ein Unterbefehl je Frage, und
behaelt dabei die Antworten im Kopf jeder Funktion. Wer die naechste Frage
stellt, soll nicht wieder bei null anfangen.

    python3 scripts/quellen_probe.py kaspalytics   welche endpunkte antworten
    python3 scripts/quellen_probe.py bestaende     wann gemessen wird
    python3 scripts/quellen_probe.py stream        kaspa.stream, warum nichts geht
    python3 scripts/quellen_probe.py tabelle       die distributionstabelle
    python3 scripts/quellen_probe.py routen        das routenverzeichnis der app
    python3 scripts/quellen_probe.py handwerte     handwerte gegen botwerte
    python3 scripts/quellen_probe.py richlist      rangliste und labels, api.kaspa.org
    python3 scripts/quellen_probe.py wochen        entity x, einzahlungen je woche
    python3 scripts/quellen_probe.py seite         entity-x.html live gegen stempel
    python3 scripts/quellen_probe.py montag        weekly numbers, montagstermin trocken
    python3 scripts/quellen_probe.py alle          alles nacheinander

WAS BISHER HERAUSKAM, in Kurzform

  Kaspalytics laedt seine Diagramme selbst per JSON, oeffentlich, ohne
  Anmeldung, und zu jeder Seite /app/X gehoert /api/charts/X. Ausnahmen:
  die Covenant-UTXO-Reihe liegt unter /utxo/covenant-count, nicht unter
  /covenants/, und die Distributionstabelle hat ueberhaupt keinen
  Endpunkt.

  kaspa.stream hat keinen HTTP-Endpunkt. Jeder /api/-Pfad liefert die
  Startseite der Anwendung zurueck. Das Buendel ist verschleiert, nach dem
  Zurueckrechnen der \\xNN-Escapes steht darin keine einzige Adresse im
  Klartext. Die Zahlen kommen ueber socket.io von vier Adressen, die in
  VITE_SOCKET_URL_1 bis _4 stecken, abgesichert mit Salt, Zeitfenstern und
  optional Turnstile. Das waere nur mit Nachbau ihrer Anmeldung zu holen
  und ist damit erledigt.

  Die Bestandsreihen (holder_addr, holders, exchange_kas und die
  Schwellenreihen) werden einmal taeglich gemessen, seit Anfang 2026 um
  Mitternacht mit Sekundenschlupf, davor gegen 09:00 UTC. Deshalb
  stichtag() in scripts/kaspalytics.py.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

TIMEOUT = 30
KOPF = {"Accept": "*/*", "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"}
KL = "https://www.kaspalytics.com"
STREAM = "https://kaspa.stream"
TABELLE = "/app/supply/distribution-table/KAS"

JSDATEI = re.compile(r'((?:\.\./|/)[A-Za-z0-9_\-./]+\.(?:js|mjs))')
ROUTE = re.compile(r'"/\(sidebar\)(/app/[A-Za-z0-9_\-/\[\].+]*)"')
API = re.compile(r'["\'`](/api/[A-Za-z0-9_\-/{}$.:?=]*)["\'`]')
ESC = re.compile(r"\\x([0-9a-fA-F]{2})")


# ------------------------------------------------------------------ werkzeug

def hole(url):
    """Gibt (status, text). Ein toter Endpunkt ist hier ein Ergebnis,
    kein Absturz."""
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


def spanne(d):
    if not isinstance(d, dict):
        return None
    lab, ds = d.get("labels") or [], d.get("datasets") or []
    if not lab or not ds:
        return None
    return "%d punkte, %s bis %s, reihen %s" % (
        len(lab), lab[0], lab[-1], [x.get("label") for x in ds])


def umfeld(text, muster, weite=260, hoechstens=6):
    aus = []
    for m in re.finditer(muster, text, re.I):
        a = max(0, m.start() - weite // 2)
        aus.append(text[a:m.end() + weite // 2])
        if len(aus) >= hoechstens:
            break
    return aus


def probiere(basis, pfade, ueberschrift, roh=700):
    print("\n  %s" % ueberschrift)
    treffer = []
    for p in pfade:
        st, txt = hole(basis + p)
        if st != 200:
            print("    %-56s http %s" % (p, st))
            continue
        d, f = form(txt)
        sp = spanne(d)
        print("    %-56s http 200  %s" % (p, f))
        if sp:
            print("        %s" % sp)
        if roh:
            print("        roh: %s" % kurz(txt, roh))
        treffer.append(p)
    return treffer


def buendel(seite, ebenen=2, je_ebene=60):
    """Alle js-Dateien einer Kaspalytics-Seite einsammeln.

    Die Seiten binden relativ ein, mit ../../../_app/immutable/... Wer
    daraus mit Abschneiden eine Adresse baut, bekommt http 400 und haelt
    das dann fuer 'es gibt keine Buendel'. Genau das ist am 22.09. eine
    Runde lang passiert, deshalb rechnet hier urljoin."""
    st, html = hole(KL + seite)
    if st != 200:
        return html, {}
    quelltexte = {}
    for u in sorted({urllib.parse.urljoin(KL + seite, x)
                     for x in JSDATEI.findall(html)}):
        if not u.startswith(KL):
            continue
        s, t = hole(u)
        if s == 200:
            quelltexte[u] = t
    for _ in range(ebenen):
        tiefer = set()
        for u, t in list(quelltexte.items()):
            for c in JSDATEI.findall(t):
                tiefer.add(urllib.parse.urljoin(u, c))
        tiefer = {u for u in tiefer if u.startswith(KL)} - set(quelltexte)
        for u in sorted(tiefer)[:je_ebene]:
            s, t = hole(u)
            if s == 200:
                quelltexte[u] = t
    return html, quelltexte


# ------------------------------------------------------------------ befehle

def befehl_kaspalytics():
    """Welche Chartendpunkte antworten. Am 22.09. gefunden, hier nur noch
    nachgehalten: wenn einer davon ausfaellt, faellt es hier auf."""
    print("=" * 78)
    print("KASPALYTICS, DIE ENDPUNKTE, DIE WIR BENUTZEN")
    print("=" * 78)
    probiere(KL, [
        "/api/charts/covenants/transactions",
        "/api/charts/covenants/outputs",
        "/api/charts/utxo/covenant-count",
        "/api/charts/transactions/accepted/addresses/all",
        "/api/charts/transactions/accepted/count",
        "/api/charts/address/count/meaningful-balance",
        "/api/charts/address/count/non-zero-balance",
        "/api/charts/address/count/non-meaningful-balance",
        "/api/charts/supply/inactive?minAge=1year",
        "/api/charts/supply/exchange-holdings",
        "/api/charts/supply/hodl-waves",
        "/api/charts/distribution/kas-threshold/0.01+",
        "/api/charts/distribution/kas-threshold/1+",
        "/api/charts/distribution/kas-threshold/100+",
    ], "in benutzung oder geprueft:", roh=260)

    probiere(KL, [
        "/api/charts/covenants/utxo-count",
        "/api/charts/distribution/kas-bucket",
        "/api/charts/supply/distribution-table/KAS",
        "/api/charts/distribution/kas-threshold/1000+",
    ], "bekannt tot, zur kontrolle:", roh=0)
    return 0


def befehl_bestaende():
    """Wann die Bestandsreihen gemessen werden. Das ist die Grundlage von
    stichtag() in kaspalytics.py: seit Anfang 2026 Mitternacht mit
    Sekundenschlupf, davor gegen 09:00 UTC, und deshalb greift die
    Korrektur nur in der ersten Stunde nach Mitternacht."""
    print("=" * 78)
    print("WANN DIE BESTANDSREIHEN GEMESSEN WERDEN")
    print("=" * 78)
    reihen = {
        "holder_addr":   ("/api/charts/address/count/meaningful-balance", "Addresses"),
        "holders":       ("/api/charts/supply/inactive?minAge=1year", "CSPERCENT"),
        "exchange_kas":  ("/api/charts/supply/exchange-holdings", "Balance"),
        "schwelle 1+":   ("/api/charts/distribution/kas-threshold/1+", "Addresses"),
        "alle halter":   ("/api/charts/address/count/non-zero-balance", "Addresses"),
        "active_addr":   ("/api/charts/transactions/accepted/addresses/all", "Addresses"),
    }
    for feld, (pfad, name) in reihen.items():
        st, txt = hole(KL + pfad)
        print("\n  %-14s %s" % (feld, pfad))
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
            print("    reihe %s fehlt, vorhanden %s"
                  % (name, [x.get("label") for x in d.get("datasets") or []]))
            continue
        stunden = {}
        for lab in labels:
            h = str(lab).split("T")[1][:2] if "T" in str(lab) else "??"
            stunden[h] = stunden.get(h, 0) + 1
        tage = [str(lab).split("T")[0] for lab in labels]
        doppelt = {t for t in tage if tage.count(t) > 1}
        print("    %d punkte, %s bis %s" % (len(labels), labels[0], labels[-1]))
        print("    uhrzeiten: %s" % sorted(stunden.items(), key=lambda x: -x[1])[:6])
        print("    kalendertage mit zwei messungen (ohne korrektur): %d" % len(doppelt))
        for lab, wert in list(zip(labels, reihe))[-4:]:
            print("      %-30s %s" % (lab, wert))
    return 0


def befehl_stream():
    """kaspa.stream. Die Frage ist beantwortet und negativ; dieser Befehl
    haelt die Begruendung nachpruefbar, statt sie nur zu behaupten."""
    print("=" * 78)
    print("KASPA.STREAM, WARUM DORT NICHTS ZU HOLEN IST")
    print("=" * 78)
    print("\n  jeder /api-pfad liefert die startseite zurueck:")
    for p in ("/api/distribution", "/api/addresses/top", "/api/holders",
              "/socket.io/?EIO=4&transport=polling"):
        st, txt = hole(STREAM + p)
        istml = txt.lstrip().lower().startswith("<!doctype")
        print("    %-40s http %s  %s" % (p, st, "SPA-startseite" if istml else kurz(txt, 80)))

    st, html = hole(STREAM + "/")
    dateien = sorted(set(re.findall(r'["\'(](/assets/[A-Za-z0-9_\-./]+\.js)', html)))
    print("\n  %d buendel: %s" % (len(dateien), dateien))
    for d in dateien[:2]:
        s, js = hole(STREAM + d)
        if s != 200:
            continue
        klar = ESC.sub(lambda m: chr(int(m.group(1), 16)), js)
        adressen = sorted(set(re.findall(r"https?://[A-Za-z0-9_.\-]+/[A-Za-z0-9_\-./]*", klar)))
        print("\n    %s, %d zeichen, nach dem zurueckrechnen %d"
              % (d, len(js), len(klar)))
        print("    adressen im klartext: %s" % (adressen[:8] or "keine"))
        for u in umfeld(klar, r"VITE_SOCKET_URL|VITE_WS_AUTH", 220, 3):
            print("      … %s" % kurz(u, 260))
    print("\n  ergebnis: kein HTTP-endpunkt, adressen nur verschleiert,")
    print("  zugang ueber socket.io mit eigener anmeldung. erledigt.")
    return 0


def befehl_tabelle():
    """Die Distributionstabelle bei Kaspalytics. Seite ja, Daten nein."""
    print("=" * 78)
    print("DIE DISTRIBUTIONSTABELLE")
    print("=" * 78)
    st, html = hole(KL + TABELLE)
    print("  seite %s  http %s, %d zeichen" % (TABELLE, st, len(html)))
    for wort in ("Shrimp", "Whale", "Plankton", "distribution-table"):
        print("    '%s' im quelltext: %d mal"
              % (wort, len(re.findall(re.escape(wort), html, re.I))))

    probiere(KL, [
        TABELLE + "/__data.json",
        "/api/charts/supply/distribution-table/KAS",
        "/api/charts/distribution/kas-bucket",
        "/api/tables/supply/distribution-table/KAS",
        "/api/supply/distribution-table/KAS",
    ], "die wege, die es geben koennte:", roh=300)

    _, texte = buendel(TABELLE)
    alle = set()
    for t in texte.values():
        alle |= set(API.findall(t))
    print("\n  %d buendel gelesen, %d zeichen, %d /api-adressen darin"
          % (len(texte), sum(len(x) for x in texte.values()), len(alle)))
    print("\n  ergebnis: die seite gibt es, die daten nicht. __data.json ist")
    print("  leer, kein endpunkt antwortet, und in den buendeln steht keine")
    print("  adresse. die tabelle wird erst im browser gefuellt.")
    return 0


def befehl_routen():
    """Das Routenverzeichnis der App. Steckt in den Buendeln und nennt
    Seiten, die in keiner Seitenleiste auftauchen, zum Beispiel die
    Schwellenreihen."""
    print("=" * 78)
    print("DAS ROUTENVERZEICHNIS DER APP")
    print("=" * 78)
    _, texte = buendel(TABELLE)
    routen = set()
    for t in texte.values():
        routen |= set(ROUTE.findall(t))
    routen = sorted(routen)
    print("  %d seiten aus %d buendeln:" % (len(routen), len(texte)))
    for r in routen:
        print("      %s" % r)
    passend = [r for r in routen
               if re.search(r"distribution|threshold|bucket|balance|count", r, re.I)]
    print("\n  davon zur verteilung: %s" % passend)
    return 0


# --------------------------------------------------------------- handwerte

# Was Ben von Hand eintraegt, und welches Botfeld dieselbe Frage beantwortet.
# Die Beschreibung ist woertlich der Hinweis aus data/week-input.json.
PAARE = {
    "active_addr": ("active_addr",
                    "kaspalytics, active addresses, kurve ALL UNIQUE, letzter voller tag"),
    "tps": ("tps",
            "kaspalytics, average tps, letzter voller tag  <-- ueberholt seit 16.09."),
    "dormant_pct": ("holders",
                    "kaspalytics, hodl waves, summe der zeilen ab 1y"),
    "exchange_kas": ("exchange_kas",
                     "kaspalytics, known exchange holdings, ganze zahl"),
}


def befehl_handwerte():
    """Jeden Handwert aus week-input.json gegen das stellen, was der Bot
    fuer dieselbe Woche liest. Das ist die Entscheidungsgrundlage dafuer,
    welches Feld automatisch werden kann und welches Handwert bleibt."""
    import kaspalytics as k

    print("=" * 78)
    print("HANDWERTE GEGEN BOTWERTE")
    print("=" * 78)
    pfad = os.path.join(REPO, "data", "week-input.json")
    eingabe = json.load(open(pfad, encoding="utf-8"))
    woche = dt.date.fromisoformat(eingabe["week"])
    manual = eingabe.get("manual") or {}
    print("  week-input.json, woche %s" % woche)
    print("  handwerte: %s\n" % sorted(manual))

    werte, tage, probleme = k.sammle(heute=woche)
    print("  %-13s %-16s %-16s %-11s %s"
          % ("feld", "hand", "bot", "abweichung", "gelesener tag"))
    for feld in sorted(manual):
        botfeld, _ = PAARE.get(feld, (None, None))
        hand = manual[feld]
        bot = werte.get(botfeld) if botfeld else None
        if bot is None:
            abw = "-"
        elif hand in (0, None):
            abw = "-"
        else:
            abw = "%+.2f%%" % ((float(bot) / float(hand) - 1) * 100)
        print("  %-13s %-16s %-16s %-11s %s"
              % (feld, hand, bot, abw, tage.get(botfeld, "-")))
    print()
    for feld in sorted(manual):
        botfeld, beschreibung = PAARE.get(feld, (None, ""))
        print("  %-13s <- %-13s  %s" % (feld, botfeld, beschreibung))
    if probleme:
        print("\n  probleme: %s" % probleme)

    # dormant_pct nennt in der eingabedatei die hodl-waves, der bot liest
    # supply/inactive. beides soll denselben anteil messen. hier steht, ob
    # es das tut.
    print("\n  die hodl-waves-seite, die der hinweis fuer dormant_pct nennt:")
    st, txt = hole(KL + "/api/charts/supply/hodl-waves")
    if st != 200:
        print("    /api/charts/supply/hodl-waves  http %s" % st)
    else:
        d, f = form(txt)
        print("    http 200  %s" % f)
        if isinstance(d, dict):
            reihen = [x.get("label") for x in d.get("datasets") or []]
            print("    reihen: %s" % reihen)
            lab = d.get("labels") or []
            print("    %d punkte, %s bis %s" % (len(lab), lab[0], lab[-1]))
            ab1j = 0.0
            for ds in d.get("datasets") or []:
                name = str(ds.get("label", ""))
                if re.match(r"\s*(1y|2y|3y|4y|5y|>|over)", name, re.I):
                    daten = ds.get("data") or []
                    if daten and daten[-1] is not None:
                        ab1j += float(daten[-1])
                        print("      %-12s letzter wert %s" % (name, daten[-1]))
            print("    summe der reihen ab 1y: %.2f" % ab1j)
            print("    supply/inactive?minAge=1year sagt: %s" % werte.get("holders"))
    return 0


# --------------------------------------------------------------- richlist

KASPA_API = "https://api.kaspa.org"
ENTITY_X = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"


def _form_tief(d, tiefe=0, name="antwort"):
    """Die Form einer JSON-Antwort beschreiben, zwei Ebenen tief. Genau das
    ist die Frage bei einem Endpunkt, der als EXPECT BREAKING CHANGES
    markiert ist: nicht was drinsteht, sondern wie es drinsteht."""
    pad = "    " + "  " * tiefe
    if isinstance(d, dict):
        print("%s%s: objekt, %d schluessel" % (pad, name, len(d)))
        if tiefe < 2:
            for k in list(d)[:12]:
                v = d[k]
                if isinstance(v, (dict, list)):
                    _form_tief(v, tiefe + 1, k)
                else:
                    print("%s  %s: %s = %s" % (pad, k, type(v).__name__, kurz(v, 90)))
    elif isinstance(d, list):
        print("%s%s: liste, %d eintraege" % (pad, name, len(d)))
        if d and tiefe < 2:
            _form_tief(d[0], tiefe + 1, "[0]")
    else:
        print("%s%s: %s = %s" % (pad, name, type(d).__name__, kurz(d, 90)))


def befehl_richlist():
    """Die Rangliste und das Label-Verzeichnis auf api.kaspa.org.

    Beide sind als EXPECT BREAKING CHANGES markiert und lassen sich per
    Umgebungsvariable abschalten (dann http 503). Bevor ein Logger gegen
    sie geschrieben wird, steht hier, welche Form die Antwort am Tag des
    Baus hatte: welche Schluessel, welche Typen, und vor allem in welcher
    Einheit die Betraege stehen. Die Einheit wird nicht angenommen, sie
    wird gegen den Kontostand von Entity X gestellt, den wir ueber den
    stabilen Endpunkt /addresses/{adresse}/balance kennen (in sompi)."""
    print("=" * 78)
    print("API.KASPA.ORG, RANGLISTE UND LABELS")
    print("=" * 78)
    daten = {}
    for pfad in ("/addresses/top", "/addresses/names",
                 "/addresses/%s/balance" % ENTITY_X, "/info/coinsupply"):
        st, txt = hole(KASPA_API + pfad)
        print("\n  %s  http %s, %d zeichen" % (pfad, st, len(txt)))
        if st != 200:
            print("    roh: %s" % kurz(txt, 400))
            continue
        d, f = form(txt)
        print("    %s" % f)
        _form_tief(d)
        print("    roh: %s" % kurz(txt, 900))
        daten[pfad] = d

    # die einheitspruefung selbst steht nur an einer stelle, im logger.
    # hier laeuft er trocken: holen, pruefen, drucken, nichts schreiben.
    print("\n  --- der logger, trocken ---")
    import richlist_log
    return richlist_log.main(["--trocken"])


def _serien(wochen, erste, letzte):
    """Zusammenhaengende Laeufe von Kalenderwochen mit mindestens einer
    Einzahlung, dazu die Wochen ohne. Wochen sind ISO-Wochen, Montag bis
    Sonntag, gezaehlt in UTC, so wie das Kostenskript die Tage zaehlt."""
    laeufe, luecken = [], []
    w = erste
    lauf = None
    while w <= letzte:
        if w in wochen:
            lauf = [lauf[0], w] if lauf else [w, w]
        else:
            luecken.append(w)
            if lauf:
                laeufe.append(tuple(lauf))
            lauf = None
        w += dt.timedelta(days=7)
    if lauf:
        laeufe.append(tuple(lauf))
    return laeufe, luecken


def befehl_wochen():
    """Stimmt "buys every week" auf entity-x.html? Gezaehlt werden dieselben
    Einzahlungen wie in data/entity-x-costbasis.json (netto ueber 1 KAS je
    Transaktion, gleiche Funktion net_flows), je Kalenderwoche. Nur lesen,
    nichts schreiben.

    Zweimal gezaehlt: einmal alle Einzahlungen, einmal nur die ab 100.000
    KAS. Die Grenze ist dieselbe, ab der die Seite einen Abfluss als echt
    und nicht als Staub zeigt. Eine Woche, in der nur 5 KAS ankamen, ist
    keine Woche, in der jemand gekauft hat."""
    import entity_x_costbasis as cb
    print("=" * 78)
    print("ENTITY X, EINZAHLUNGEN JE KALENDERWOCHE")
    print("=" * 78)
    txs = cb.fetch_transactions()
    zu, ab, _, _ = cb.net_flows(txs)
    datei = json.load(open(os.path.join(REPO, "data", "entity-x-costbasis.json"),
                           encoding="utf-8"))
    print("transaktionen %d, einzahlungen %d (datei sagt %s), erste %s, letzte %s"
          % (len(txs), len(zu), datei.get("deposits"),
             zu[0]["day"] if zu else "-", zu[-1]["day"] if zu else "-"))
    if not zu:
        return 1

    def montag(tag):
        d = dt.date.fromisoformat(tag)
        return d - dt.timedelta(days=d.weekday())

    def kw(m):
        j, n, _ = m.isocalendar()
        return "%d-W%02d (%s)" % (j, n, m.isoformat())

    for name, grenze in (("alle einzahlungen", 0), ("ab 100.000 KAS", 100000)):
        auswahl = [e for e in zu if e["kas"] >= grenze]
        wochen = {}
        for e in auswahl:
            wochen.setdefault(montag(e["day"]), []).append(e["kas"])
        erste, letzte = montag(zu[0]["day"]), montag(zu[-1]["day"])
        laeufe, luecken = _serien(set(wochen), erste, letzte)
        gesamt = (letzte - erste).days // 7 + 1
        print("\n--- %s: %d stueck in %d von %d kalenderwochen, %d ohne"
              % (name, len(auswahl), len(wochen), gesamt, len(luecken)))
        lang = sorted(laeufe, key=lambda l: ((l[1] - l[0]).days, l[1]), reverse=True)
        print("  laengste laeufe ohne luecke (wochen, von, bis):")
        for a, b in lang[:8]:
            print("    %3d  %s  bis  %s" % ((b - a).days // 7 + 1, kw(a),
                                            kw(b)))
        if laeufe:
            a, b = laeufe[-1]
            print("  letzter lauf: %d wochen, %s bis %s"
                  % ((b - a).days // 7 + 1, kw(a), kw(b)))
        je_jahr = {}
        for m in luecken:
            je_jahr.setdefault(m.isocalendar()[0], []).append(m)
        for j in sorted(je_jahr):
            print("  wochen ohne, %d: %d stueck  %s"
                  % (j, len(je_jahr[j]),
                     " ".join("W%02d" % m.isocalendar()[1] for m in je_jahr[j])))
        # die letzten zwanzig wochen einzeln, damit der lauf am ende sichtbar ist
        print("  die letzten 20 wochen:")
        w = letzte - dt.timedelta(days=7 * 19)
        while w <= letzte:
            b = wochen.get(w, [])
            print("    %s  %2d einzahlungen  %14s KAS"
                  % (kw(w), len(b), "{:,.0f}".format(sum(b))))
            w += dt.timedelta(days=7)

    _fenster(txs, zu, cb.ADDRESS)
    return 0


# Der Satz auf entity-x.html lautet "In the week ending July 27, 2026 it
# added ~17M KAS, withdrawn directly from Bitget and Gate.io. In the 90 days
# before that: ~84M KAS." Der 27.07.2026 ist ein Montag. Gedruckt wird
# deshalb jedes Sieben-Tage-Fenster, das zwischen dem 20.07. und dem 03.08.
# endet, mit den 90 Tagen davor, und jede Einzahlung vom 14.07. bis 03.08.
# mit ihren Absendern und deren Einstufung aus data/entity-x-inflows.json.
FENSTER_VON = dt.date(2026, 7, 14)
FENSTER_BIS = dt.date(2026, 8, 3)


def _fenster(txs, zu, adresse):
    print("\n" + "=" * 78)
    print("DER SATZ UEBER DIE WOCHE BIS ZUM 27.07.2026")
    print("=" * 78)
    tr = json.load(open(os.path.join(REPO, "data", "entity-x-inflows.json"),
                        encoding="utf-8"))
    stufe = {x["address"]: (x.get("exchange") or "-", x["verdict"])
             for x in tr.get("senders", [])}
    print("einstufung aus entity-x-inflows.json, erzeugt %s UTC"
          % dt.datetime.fromtimestamp(tr["generated_at"], dt.timezone.utc)
          .strftime("%Y-%m-%d %H:%M"))
    tag = {}
    for e in zu:
        d = dt.date.fromisoformat(e["day"])
        tag[d] = tag.get(d, 0.0) + e["kas"]

    def summe(von, bis):
        return sum(v for d, v in tag.items() if von <= d <= bis)

    print("\n  sieben tage bis        wochentag   summe KAS      90 tage davor")
    e = dt.date(2026, 7, 20)
    while e <= FENSTER_BIS:
        a = e - dt.timedelta(days=6)
        print("  %s bis %s  %-9s %14s %16s"
              % (a, e, e.strftime("%A"), "{:,.0f}".format(summe(a, e)),
                 "{:,.0f}".format(summe(a - dt.timedelta(days=90),
                                        a - dt.timedelta(days=1)))))
        e += dt.timedelta(days=1)

    nach_id = {t.get("transaction_id"): t for t in txs}
    print("\n  einzahlungen %s bis %s, mit absendern:" % (FENSTER_VON, FENSTER_BIS))
    for x in zu:
        d = dt.date.fromisoformat(x["day"])
        if not FENSTER_VON <= d <= FENSTER_BIS:
            continue
        t = nach_id.get(x["tx"]) or {}
        von = {}
        for i in t.get("inputs") or []:
            ad = i.get("previous_outpoint_address")
            if ad and ad != adresse:
                von[ad] = von.get(ad, 0.0) + float(i.get("previous_outpoint_amount") or 0) / 1e8
        teile = ["%s %s/%s" % (ad[-8:], *stufe.get(ad, ("-", "nicht im tracer")))
                 for ad in sorted(von, key=von.get, reverse=True)[:3]]
        print("    %s %s  %14s KAS  %s  %s"
              % (x["day"], dt.datetime.fromtimestamp(x["ts"] / 1000, dt.timezone.utc)
                 .strftime("%H:%M"), "{:,.2f}".format(x["kas"]), x["tx"][:10],
                 "; ".join(teile) or "keine eingaenge aufgeloest"))



def befehl_seite():
    """Steht auf kaspapulse.com/entity-x.html, was der Stempel im Repo
    geschrieben hat? Nur lesen. Holt die veroeffentlichte Seite und stellt
    jede gestempelte Stelle zweimal gegen entity-x.html im Checkout: den
    ausgelieferten Quelltext und das, was Chrome auf der Seite rechnet (mit
    der veroeffentlichten Datei, externe Adressen gesperrt, also ohne
    Live-Kurs). Die Arbeitsumgebung kommt an kaspapulse.com nicht heran,
    deshalb laeuft das hier."""
    import entity_x_page as ep
    print("=" * 78)
    print("ENTITY-X.HTML, VEROEFFENTLICHT GEGEN STEMPEL")
    print("=" * 78)
    chrome = ep.finde_browser()
    if not chrome:
        print("kein chrome gefunden")
        return 1
    with open(ep.SEITE, encoding="utf-8") as fh:
        gestempelt = fh.read()
    t = ep.sammle(gestempelt)
    print("stempel im checkout: oCnt %s, outLast %s, outLastKas %s, cbPnl %s"
          % tuple([x[1] for x in t.fund[i] if x[0] == "text"][0]
                  for i in ("oCnt", "outLast", "outLastKas", "cbPnl")))
    fehler, n = ep.live_pruefung("https://kaspapulse.com/entity-x.html",
                                 gestempelt, chrome)
    if fehler:
        print("ABWEICHUNG, %d beanstandungen" % len(fehler))
        for f in fehler:
            print("  " + f)
        return 1
    print("zeichengleich: %d gestempelte stellen, im ausgelieferten quelltext "
          "und im browser (%s)" % (n, chrome))
    return 0



def befehl_montag():
    """Der Montagstermin von weekly numbers, trocken, mit simuliertem Datum
    und simulierter Uhrzeit in Berlin. Nur lesen: DRY_RUN=1, keine Secrets,
    History bleibt, die Eingabedatei wird als Kopie im Temp-Verzeichnis
    veraendert, nicht im Repo. Alle Faelle mit heute = naechster Montag:
      A  Termin 18:40, week = Montag      voller Posttext
      B  Termin 16:20, week = Montag      zu frueh, kein Post, gruen
      C  Termin 17:40, week = Montag      Winter-Erstlauf, kein Post, gruen
      D  Termin 18:40, week wie jetzt     Abbruch, alte Woche
      E  Push   18:40, week wie jetzt     Abbruch, alte Woche
      F  Push   10:16, week = Montag      zu frueh, kein Post, gruen"""
    import subprocess
    import tempfile
    heute = dt.date.today()
    montag = heute + dt.timedelta(days=(7 - heute.weekday()) % 7 or 7)
    quelle = os.path.join(REPO, "data", "week-input.json")
    with open(quelle, encoding="utf-8") as fh:
        eingabe = json.load(fh)
    jetzt = eingabe.get("week")
    print("=" * 78)
    print("WEEKLY NUMBERS, MONTAGSTERMIN TROCKEN, heute simuliert %s" % montag)
    print("week in data/week-input.json: %s" % jetzt)
    print("=" * 78)
    schlecht = 0
    # name, anlass, uhr, week, exit, posttext erwartet
    faelle = (("A", "schedule", "18:40", str(montag), 0, True),
              ("B", "schedule", "16:20", str(montag), 0, False),
              ("C", "schedule", "17:40", str(montag), 0, False),
              ("D", "schedule", "18:40", jetzt, 1, False),
              ("E", "push", "18:40", jetzt, 1, False),
              ("F", "push", "10:16", str(montag), 0, False))
    for name, event, uhr, week, soll, text in faelle:
        d = tempfile.mkdtemp()
        pfad = os.path.join(d, "week-input.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(dict(eingabe, week=week), fh)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("DISCORD", "TELEGRAM"))}
        env.update({"DRY_RUN": "1", "FORCE": "", "SHOW_USD": "",
                    "GITHUB_EVENT_NAME": event, "WN_HEUTE": str(montag),
                    "WN_UHR": uhr, "WN_INPUT": pfad})
        r = subprocess.run([sys.executable, os.path.join(HERE, "weekly_numbers.py")],
                           env=env, capture_output=True, text=True, timeout=300, cwd=REPO)
        print("\n--- fall %s: %s um %s Berlin, week %s, erwartet exit %d, %s"
              % (name, event, uhr, week, soll, "posttext" if text else "kein posttext"))
        print(r.stdout[-5000:].rstrip())
        if r.stderr.strip():
            print("stderr: " + r.stderr[-800:])
        hat_text = "kaspa pulse, week" in r.stdout
        ok = r.returncode == soll and hat_text == text
        print("exit %s, posttext %s, %s" % (r.returncode, "ja" if hat_text else "nein",
                                           "wie erwartet" if ok else "NICHT WIE ERWARTET"))
        schlecht |= 0 if ok else 1
    return schlecht


BEFEHLE = {
    "kaspalytics": befehl_kaspalytics,
    "bestaende": befehl_bestaende,
    "stream": befehl_stream,
    "tabelle": befehl_tabelle,
    "routen": befehl_routen,
    "handwerte": befehl_handwerte,
    "richlist": befehl_richlist,
    "wochen": befehl_wochen,
    "seite": befehl_seite,
    "montag": befehl_montag,
}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", choices=sorted(BEFEHLE) + ["alle"])
    a = ap.parse_args(argv)
    if a.befehl == "alle":
        schlecht = 0
        for name in ("kaspalytics", "bestaende", "stream", "tabelle",
                     "routen", "handwerte"):
            print("\n\n" + "#" * 78)
            print("# %s" % name)
            print("#" * 78)
            schlecht |= BEFEHLE[name]()
        return schlecht
    return BEFEHLE[a.befehl]()


if __name__ == "__main__":
    sys.exit(main())
