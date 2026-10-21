#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archiv.py, die Wochenseiten, die Archiv-Uebersicht und die Seite method (Ben, 21.10.2026, PR 2).

  /week/JJJJ-MM-TT/   eine Seite je Montagslesung in data/weekly.json, mit der
                      Zahl der Woche, den Schritten dieser Woche und Links zur
                      Vor- und Folgewoche. Rueckwirkend so weit die Daten
                      reichen, also ab dem 13.07.2026 (Ausgabe 1).
  /archive/           alle Wochen, neueste oben.
  /method/            je Kennzahl ein Satz, was sie misst, die Quelle und ob wir
                      selbst zaehlen (counted), uebernehmen (source ...) oder
                      rechnen (computed). Jede hervorgehobene Zahl der
                      Startseite verlinkt auf ihren Eintrag.

STRENG HEISST: KEIN WERT AUS DER ZUKUNFT. Eine vergangene Woche nimmt nur
Werte, die bis zu ihrem Montag gemessen waren (startseite.bis, streng). Was es
damals noch nicht gab, fehlt dort als Schritt. Die Blockrate messen wir seit
dem 21.10.2026, die Gebuehrenreihe seit dem 12.10.2026; aeltere Wochen haben
deshalb weniger Schritte. Nur die laufende Woche ist dieselbe Seite wie die
Startseite, mit deren Rueckfall auf den neuesten Wert.

Alle Seiten tragen den Rahmen der Startseite (Kopf, Menue, Fuss, Farben,
Schrift), genommen aus index.html. Die SEO-Bloecke (canonical, Open Graph,
Stand-Zeile) schreibt seo_seiten.py; dieses Skript laesst sie bei einer
schon vorhandenen Seite stehen, damit die beiden sich nicht abwechselnd
ueberschreiben.

Montags baut dashboard_weekly.py die neue Woche mit (ueber startseite.py),
der taegliche Lauf von number-of-day ebenso. Die alte Vorwoche bekommt dabei
ihren Link auf die neue Woche.

    python3 scripts/archiv.py              schreiben
    python3 scripts/archiv.py --pruefen    nur pruefen, Exit 1 wenn eine Seite abweicht
    python3 scripts/archiv.py --selbsttest
"""
import argparse
import datetime as dt
import html as htmlmod
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import startseite as ss  # noqa: E402

SEITE = ss.SEITE
WOCHE_ORDNER = "week"
ARCHIV = "archive/index.html"
METHODE = "method/index.html"

KOPF = re.compile(r"(?s)<!--AUTO:seo-kopf-->.*?<!--/AUTO:seo-kopf-->")
STAND = re.compile(r"(?s)<!--AUTO:seitenstand-->.*?<!--/AUTO:seitenstand-->")

# Je Kennzahl: id (wie der Schritt auf der Startseite), Name, was sie misst,
# Quelle, und wie die Zahl zustande kommt. Keine Werte, nur Regeln.
EINTRAEGE = [
    ("week", "number of the week",
     "how far kaspa's weekly close sits above or below the plain average of its last 50 weekly closes. "
     "a week closes on saturday at 24:00 utc.",
     "source kraken daily candles, the average computed by kaspa pulse",
     "source kraken, average computed"),
    ("chain", "blocks per second",
     "how many blocks the network adds each second, read as the rise of the virtual DAA score over 600 seconds.",
     "counted by kaspa pulse from the kaspa rest api",
     "counted"),
    ("fees", "fees in miner revenue",
     "the share of transaction fees in everything miners earned over 30 days, fees divided by fees plus new coins.",
     "fees source kaspalytics, new coins computed by kaspa pulse from the emission schedule",
     "source kaspalytics"),
    ("emission", "daily emission",
     "the new KAS created per day, the block reward times 10 blocks a second times 86,400 seconds. the reward "
     "steps down every month by the same factor and halves once a year.",
     "computed by kaspa pulse from the emission schedule",
     "computed"),
    ("holders", "addresses with at least 100 KAS",
     "how many addresses hold 100 KAS or more at the end of a day. an address is not a holder, "
     "one wallet can use many addresses.",
     "source kaspalytics address thresholds",
     "source kaspalytics"),
    ("layer2", "layer 2 DEX volume share",
     "the share of igra in the DEX volume of kaspa's 2 layer 2 networks, igra and kasplex, over the 24 hours "
     "before our monday reading.",
     "source defillama",
     "source defillama"),
    ("addresses", "addresses with any balance",
     "every address with a balance above zero, next to those holding more than 0.01 KAS. most of the first "
     "group hold dust.",
     "source kaspalytics address thresholds",
     "source kaspalytics"),
]
ALLGEMEIN = [
    ("reading", "the monday reading",
     "every number on the home page and on each week page is the reading of a monday. a value measured "
     "after that monday is not shown on its week page, so a week can show fewer numbers than the next."),
    ("chips", "the comparison chips",
     "fast numbers are compared with the week before and with 13 weeks before, the emission with the month "
     "before and with 3 months before. fixed numbers get no comparison. when a value is missing, its chip "
     "is left out."),
]


# ---------------------------------------------------------------- daten

def wochen(q, heute):
    """Die Montage der Lesungen in data/weekly.json, bis zum laufenden Stichtag."""
    st = ss.stichtag(heute)
    aus = set()
    for r in (q["weekly"] or {}).get("history", []):
        try:
            d = dt.date.fromisoformat(r["date"])
        except (KeyError, ValueError):
            continue
        if d.weekday() == 0 and d <= st:
            aus.add(d)
    return sorted(aus)


def ausgabe(d):
    import weekly_numbers
    return weekly_numbers.issue_number(d)


def pfad(d):
    return "%s/%s/index.html" % (WOCHE_ORDNER, d.isoformat())


def url(d):
    return "%s%s/%s/" % (SEITE, WOCHE_ORDNER, d.isoformat())


# ---------------------------------------------------------------- rahmen

def vorlage(index_text):
    """Der Rahmen der Startseite ohne das, was nur dorthin gehoert: das
    fo-verify-Tag, den Datenblock fuer dashboard_weekly und check_reads und
    die Markierung "this week" im Menue."""
    s = index_text
    s = re.sub(r"<!-- FlexOffers site verification, do not remove -->\n<meta name=\"fo-verify\"[^\n]*\n", "", s)
    s = re.sub(r"(?s)// WEEKLY-DATA-START.*?// WEEKLY-DATA-END\n(?://[^\n]*\n)*", "", s)
    s = s.replace(' aria-current="page"', "")
    return s


def rahmen(vorl, titel, beschr, inhalt, alt=None):
    s = re.sub(r"(?s)<title>.*?</title>", lambda m: "<title>%s</title>" % ss.esc(titel), vorl, count=1)
    s = re.sub(r'<meta name="description" content="[^"]*">',
               lambda m: '<meta name="description" content="%s">' % ss.esc(beschr), s, count=1)
    s = ss.ersetzen(s, "startseite", inhalt)
    if alt:
        # die bloecke von seo_seiten.py bleiben stehen, siehe kopf des skripts
        for muster in (KOPF, STAND):
            m = muster.search(alt)
            if m and muster.search(s):
                s = muster.sub(lambda _m: m.group(0), s, count=1)
    return s


def beschreibung(kandidaten):
    """Die erste Fassung mit 140 bis 155 Zeichen (Regel aus seo_pruefung.py)."""
    for k in kandidaten:
        if 140 <= len(k) <= 155:
            return k
    raise ss.Abbruch("keine beschreibung mit 140 bis 155 zeichen, %s" % [len(k) for k in kandidaten])


# ---------------------------------------------------------------- seiten

def woche_seite(D, d, vor, nach, nr):
    oben = "issue %d · the monday reading of %s" % (nr, ss.d_kurz(d))
    links = []
    if vor:
        links.append('<a href="/%s/%s/">previous week, %s</a>' % (WOCHE_ORDNER, vor.isoformat(), ss.d_kurz(vor)))
    links.append('<a href="/archive/">all weeks</a>')
    if nach:
        links.append('<a href="/%s/%s/">next week, %s</a>' % (WOCHE_ORDNER, nach.isoformat(), ss.d_kurz(nach)))
    unten = '  <nav class="weeknav" aria-label="weeks">%s</nav>' % "".join(links)
    inhalt = ss.inhalt_html(D, url(d), {"oben": oben, "unten": unten})
    schritte = ss.schritte(D)
    fehler = ss.pruefen(inhalt, schritte)
    if fehler:
        raise ss.Abbruch("wache, woche %s, %s" % (d, "; ".join(fehler)))
    tag = "%d %s %d" % (d.day, ss.MON[d.month - 1].capitalize(), d.year)
    titel = "Kaspa Pulse Issue %d, the Reading of %s" % (nr, tag)
    z = D["zdw"]
    k = len(schritte)
    if z:
        lage = "the weekly close sat %s %s the 50 week average" % (
            ss.pct(abs(z["abstand"])), "below" if z["abstand"] < 0 else "above")
        rest = "plus %d more numbers" % k
    else:
        lage, rest = "%d numbers" % k, "on the network"
    grund = "The Kaspa Pulse reading of monday %s, issue %d. %s%s, %s" % (
        ss.d_kurz(d), nr, lage[0].upper(), lage[1:], rest)
    beschr = beschreibung([grund + s for s in (
        ", each with date and source.", ", each with its date and source.",
        ", each with its date and its source.", ".", ", dated and sourced.")])
    return titel, beschr, inhalt, schritte


def archiv_seite(eintraege):
    """eintraege: [(montag, ausgabe, zdw, zahl der schritte)], neueste zuerst."""
    erste = eintraege[-1][0]
    zeilen = []
    for d, nr, z, k in eintraege:
        if z:
            satz = "weekly close %s %s the 50 week average · %d numbers" % (
                ss.pct(abs(z["abstand"])), "below" if z["abstand"] < 0 else "above", k)
        else:
            satz = "%d numbers" % k
        zeilen.append('    <li><a href="/%s/%s/"><b>%s</b><span>issue %d</span></a><p>%s</p></li>'
                      % (WOCHE_ORDNER, d.isoformat(), ss.d_kurz(d), nr, ss.esc(satz)))
    inhalt = "\n".join([
        '  <section class="hero" id="archive">',
        '    <p class="eyebrow">archive · %d monday readings</p>' % len(eintraege),
        '    <h1 class="lead">every monday reading since %s, newest first.</h1>' % ss.d_kurz(erste),
        '    <p class="note">each week keeps the numbers of its own monday. how we count is on '
        '<a href="/method/">method</a>.</p>',
        "  </section>",
        '  <ol class="weeks">',
        "\n".join(zeilen),
        "  </ol>",
        ss.anmeldung(1, "subscribe", "all the weekly numbers in one mail, every monday",
                     "the next reading lands in your inbox, dated and sourced.")])
    titel = "Kaspa Pulse Archive, Every Monday Reading"
    beschr = beschreibung([
        "Every Kaspa Pulse monday reading since %s, newest first. The number of the week and each step, "
        "every number with its date and source." % ss.d_kurz(erste),
        "Every Kaspa Pulse monday reading since %s, newest first. The number of the week and each step, "
        "with date and source." % ss.d_kurz(erste)])
    return titel, beschr, inhalt


def methode_seite(layer2=False):
    teile = ['  <section class="hero" id="method">',
             '    <p class="eyebrow">method</p>',
             '    <h1 class="lead">how kaspa pulse gets each number on the home page.</h1>',
             '    <ul class="cmp" aria-label="kinds"><li>counted means we count it ourselves</li>'
             '<li>source names who we read it from</li>'
             '<li>computed means we work it out from fixed protocol rules</li></ul>',
             "  </section>"]
    for sid, name, misst, quelle, art in EINTRAEGE:
        if sid == "layer2" and not layer2:
            continue
        teile.append("\n".join([
            '  <section class="mentry" id="%s">' % sid,
            '    <div class="steprow"><h2>%s</h2><span class="art">%s</span></div>' % (ss.esc(name), ss.esc(art)),
            '    <p class="body">%s</p>' % ss.esc(misst),
            '    <p class="note">%s</p>' % ss.esc(quelle),
            "  </section>"]))
    for sid, name, satz in ALLGEMEIN:
        teile.append("\n".join([
            '  <section class="mentry" id="%s">' % sid,
            "    <h2>%s</h2>" % ss.esc(name),
            '    <p class="body">%s</p>' % ss.esc(satz),
            "  </section>"]))
    teile.append('  <div class="deeper"><a href="/">this week</a><a href="/archive/">archive</a>'
                 '<a href="/kaspa-data-sources.html">data sources</a></div>')
    inhalt = "\n".join(teile)
    titel = "How Kaspa Pulse Counts Each Number"
    beschr = beschreibung([
        "What each Kaspa Pulse number measures, where it comes from, and whether we count it, "
        "read it from a named source or compute it from protocol rules."])
    return titel, beschr, inhalt


def texte_pruefen(inhalt):
    import karussell
    return karussell.text_pruefen(ss.sichtbare_texte(inhalt))


# ---------------------------------------------------------------- bauen

def alle(heute=None, index_text=None, q=None):
    """{pfad: text} fuer alle Seiten dieses Skripts."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    q = q or ss.lade_quellen()
    vorl = vorlage(index_text if index_text is not None else ss.INDEX.read_text(encoding="utf-8"))
    st = ss.stichtag(heute)
    ws = wochen(q, heute)
    if not ws:
        raise ss.Abbruch("keine montagslesung in data/weekly.json")
    aus, eintraege = {}, []
    for i, d in enumerate(ws):
        D = ss.daten(d, streng=(d != st), quellen=q)
        nr = ausgabe(d)
        titel, beschr, inhalt, schritte = woche_seite(D, d, ws[i - 1] if i else None,
                                                      ws[i + 1] if i + 1 < len(ws) else None, nr)
        aus[pfad(d)] = (titel, beschr, inhalt)
        eintraege.append((d, nr, D["zdw"], len(schritte)))
    titel, beschr, inhalt = archiv_seite(list(reversed(eintraege)))
    aus[ARCHIV] = (titel, beschr, inhalt)
    aus[METHODE] = methode_seite(ss.LAYER2)
    fehler = []
    for p, (titel, beschr, inhalt) in aus.items():
        if p in (ARCHIV, METHODE):
            fehler += ["%s, %s" % (p, f) for f in texte_pruefen(inhalt)]
        if len(titel) > 60:
            fehler.append("%s, titel %d zeichen" % (p, len(titel)))
    if fehler:
        raise ss.Abbruch("wache, %s" % "; ".join(fehler))
    fertig = {}
    for p, (titel, beschr, inhalt) in aus.items():
        alt = (REPO / p).read_text(encoding="utf-8") if (REPO / p).exists() else None
        fertig[p] = rahmen(vorl, titel, beschr, inhalt, alt)
    return fertig


def ohne_seo(s):
    return STAND.sub("", KOPF.sub("", s))


def schreiben(heute=None, nur_pruefen=False):
    try:
        seiten = alle(heute)
    except ss.Abbruch as exc:
        print("ABBRUCH archiv, %s, die seiten bleiben wie sie sind" % exc)
        return 1
    abw = []
    for p, text in seiten.items():
        ziel = REPO / p
        alt = ziel.read_text(encoding="utf-8") if ziel.exists() else None
        if alt is not None and ohne_seo(alt) == ohne_seo(text):
            continue
        abw.append(p)
        if not nur_pruefen:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(text, encoding="utf-8")
    vorhanden = sorted(str(x.relative_to(REPO)) for x in (REPO / WOCHE_ORDNER).glob("*/index.html"))
    fremd = [x for x in vorhanden if x not in seiten]
    for x in fremd:
        print("WARNUNG %s hat keine montagslesung mehr in data/weekly.json, bitte von hand pruefen" % x)
    if nur_pruefen:
        for p in abw:
            print("weicht ab, %s" % p)
        print("archiv passt zu den daten" if not abw else "python3 scripts/archiv.py laufen lassen")
        return 1 if abw else 0
    print("archiv, %d seiten neu geschrieben%s" % (len(abw), (": " + ", ".join(abw)) if abw else ""))
    return 0


def seiten_pfade():
    """Alle Seiten dieses Skripts, wie sie im Repo liegen. Fuer seo_seiten.py
    und seo_pruefung.py."""
    aus = sorted(str(x.relative_to(REPO)) for x in (REPO / WOCHE_ORDNER).glob("*/index.html"))
    for p in (ARCHIV, METHODE):
        if (REPO / p).exists():
            aus.append(p)
    return aus


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    ok("ausgabe 15 am 19.10.", ausgabe(dt.date(2026, 10, 19)) == 15)
    ok("ausgabe 1 am 13.07.", ausgabe(dt.date(2026, 7, 13)) == 1)
    q = {"weekly": {"history": [{"date": "2026-10-12"}, {"date": "2026-10-19"}, {"date": "2026-10-14"},
                                {"date": "2026-10-26"}]}}
    ok("nur montage bis zum stichtag", wochen(q, dt.date(2026, 10, 21)) == [dt.date(2026, 10, 12),
                                                                             dt.date(2026, 10, 19)])
    ok("pfad und url", pfad(dt.date(2026, 10, 19)) == "week/2026-10-19/index.html"
       and url(dt.date(2026, 10, 19)) == "https://kaspapulse.com/week/2026-10-19/")
    idx = ss.INDEX.read_text(encoding="utf-8")
    v = vorlage(idx)
    ok("vorlage ohne fo-verify", "fo-verify" not in v)
    ok("vorlage ohne datenblock", "WEEKLY-DATA" not in v and "const DATA" not in v)
    ok("vorlage ohne this week markierung", ' aria-current="page">' not in v)
    ok("vorlage behaelt menue und fuss", "<!--AUTO:menue-->" in v and "<!--AUTO:seitenstand-->" in v)
    alt = rahmen(v, "a", "b", "x").replace("page last updated", "page last updated 1 May 2026 stand")
    neu = rahmen(v, "a", "b", "y", alt)
    ok("stand-zeile einer vorhandenen seite bleibt", "1 May 2026 stand" in neu)
    try:
        beschreibung(["x" * 100])
        ok("zu kurze beschreibung bricht ab", False)
    except ss.Abbruch:
        ok("zu kurze beschreibung bricht ab", True)
    try:
        seiten = alle(dt.date(2026, 10, 21))
    except ss.Abbruch as exc:
        ok("alle seiten bauen mit den echten daten", False, exc)
        seiten = {}
    else:
        ok("alle seiten bauen mit den echten daten", True)
    if seiten:
        ws = sorted(p for p in seiten if p.startswith("week/"))
        ok("15 wochen ab 13.07.", len(ws) == 15 and ws[0] == "week/2026-07-13/index.html", len(ws))
        alte = seiten["week/2026-10-12/index.html"]
        ok("alte woche ohne blockrate (erst seit 21.10. gemessen)", 'id="chain"' not in alte)
        ok("laufende woche wie die startseite, mit blockrate", 'id="chain"' in seiten["week/2026-10-19/index.html"])
        ok("vor- und folgewoche verlinkt", '/week/2026-10-05/' in alte and '/week/2026-10-19/' in alte)
        ok("erste woche ohne vorwoche", "previous week" not in seiten["week/2026-07-13/index.html"])
        ok("letzte woche ohne folgewoche", "next week" not in seiten["week/2026-10-19/index.html"])
        ok("archiv neueste oben", seiten[ARCHIV].index("2026-10-19") < seiten[ARCHIV].index("2026-07-13"))
        ok("method hat jeden eintrag der startseite",
           all('id="%s"' % i in seiten[METHODE] for i in ("week", "chain", "fees", "emission", "holders",
                                                          "addresses")))
        ok("layer 2 fehlt in method, solange LAYER2 aus ist", ss.LAYER2 or 'id="layer2"' not in seiten[METHODE])
        titel = [re.search(r"<title>(.*?)</title>", t).group(1) for t in seiten.values()]
        ok("jede seite mit eigenem titel", len(set(titel)) == len(titel))
        ok("titel hoechstens 60 zeichen", all(len(htmlmod.unescape(t)) <= 60 for t in titel))
        besch = [htmlmod.unescape(re.search(r'<meta name="description" content="([^"]*)"', t).group(1))
                 for t in seiten.values()]
        ok("beschreibungen 140 bis 155 zeichen", all(140 <= len(b) <= 155 for b in besch),
           [len(b) for b in besch])
        ok("keine beschreibung doppelt", len(set(besch)) == len(besch))
        ok("kein doppelpunkt, kein gedankenstrich im titel und in der beschreibung",
           not any(re.search(":|—|–", x) for x in titel + besch))
        ok("anker subscribe auf jeder seite einmal",
           all(t.count('id="subscribe"') == 1 for p, t in seiten.items() if p != METHODE))
        ok("kein wert nach dem montag in einer alten woche",
           "21 oct" not in seiten["week/2026-10-12/index.html"].split("<!--AUTO:startseite-->")[1])
        js = ('var MENUE = [\n    { t: "about", k: [\n      ["method", "/method/"]\n    ]}\n  ];')
        ok("menue zeigt auf die echten seiten", '"/method/"' in ss.menue_html(js) or
           'href="/method/"' in ss.menue_html())
        ok("startseite verlinkt jede zahl auf method", all(
            'href="/method/#%s"' % i in idx for i in ("week", "fees", "emission", "holders", "addresses")))
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--heute")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    heute = dt.date.fromisoformat(a.heute) if a.heute else None
    return schreiben(heute, a.pruefen)


if __name__ == "__main__":
    sys.exit(main())
