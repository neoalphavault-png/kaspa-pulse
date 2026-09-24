#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entity_x_page.py, schreibt die Zahlen aus der Kostenrechnung in die Seite.

WARUM
Bis zum 24.09.2026 kamen alle Zahlen auf entity-x.html, die aus
data/entity-x-costbasis.json stammen, erst im Browser auf die Seite. Im
Quelltext stand der Stand vom Tag, an dem jemand die Seite zuletzt von Hand
angefasst hatte: 20 Abfluesse statt 25, "Nothing has left since 18 Jun
2026", ein Einstandspreis von $0.0881. Wer die Seite ohne Javascript liest,
jede Antwortmaschine, die nur den rohen Quelltext holt, las also falsche
Zahlen, und zwar keine Luecke, sondern eine falsche Zeile.

Dieses Skript rechnet dasselbe wie das Skript auf der Seite, in Python, und
schreibt das Ergebnis als Text in dieselben Elemente, die das Seitenskript
spaeter ueberschreibt. Muster ist scripts/covenants_page.py, nur ohne
AUTO-Markierungen: die Elemente tragen ihre ids ohnehin, weil das
Seitenskript sie braucht, und genau diese ids sind der Vertrag.

Die Live-Werte (bal, factBal, factPct, usd) stempelt es nicht. Die kommen
von api.kaspa.org und nicht aus einer Datei im Repo.

DREI WACHEN, alle in --check
  1. Wiederholbar. Ein zweites Stempeln aendert nichts. Sonst ist die Seite
     nicht auf dem Stand der Datei.
  2. Kopf-Wache. Kein Wert, den der Stempel in diesem Lauf in den Rumpf
     schreibt, darf im <head> oder im ld+json stehen. Dorthin kommt der
     Stempel nicht, ein Wert dort friert also ein. Gesucht wird im Text
     des Kopfes ohne <style> und im ld+json, und nur ganze Werte: "25"
     trifft "25 transfers", aber nicht "250" oder "font-size:25px".
  3. Abgleich gegen den Browser. Ein echter Chromium laedt die Seite mit der
     Datei, alle externen Adressen gesperrt, damit kein Live-Kurs dazwischen
     kommt. Vorher werden alle gestempelten Stellen durch "§" ersetzt. Steht
     danach irgendwo noch "§", hat das Seitenskript nicht gerechnet, und der
     Abgleich faellt durch, statt still zu bestehen. Jeder gestempelte Wert
     muss zeichengleich zu dem sein, was der Browser rechnet. Dasselbe
     laeuft ein zweites Mal mit reliable=false, damit auch der Zweig
     geprueft ist, der die Kostenbox ausblendet.

    python3 scripts/entity_x_page.py             # stempeln
    python3 scripts/entity_x_page.py --check     # pruefen, nichts schreiben
    python3 scripts/entity_x_page.py --selftest  # ohne dateien, ohne browser

Den Browser sucht --check unter $CHROME, dann google-chrome, chromium,
chromium-browser und /opt/pw-browsers/chromium. Findet er keinen, faellt
die Pruefung durch. Ein Abgleich, der nicht gelaufen ist, ist kein Abgleich.
"""

import argparse
import copy
import decimal
import functools
import html as htmllib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATEI = os.path.join(REPO, "data", "entity-x-costbasis.json")
SEITE = os.path.join(REPO, "entity-x.html")

M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ab hier ist ein abfluss echt und kein staub, dieselbe grenze wie im
# seitenskript (o.kas < 100000)
STAUB = 100000

# die ids, die dieser stempel beschreibt. alle stehen genau einmal auf der
# seite, sonst bricht der lauf ab.
TEXT_IDS = ("cbAvg", "factCost", "cbSub", "cbInv", "cbVal", "cbPnl",
            "cbLastDep", "oLastDep",
            "oSum", "bSum", "oCnt", "bCnt", "oShare", "bShare", "oRest", "bRest",
            "oDustN", "oRealN", "oRealSum", "outLast", "outLastKas")
HTML_IDS = ("outBody",)
ALLE_IDS = TEXT_IDS + HTML_IDS

MARKE = "§"


# ------------------------------------------------------------ javascript nachbauen

def fixed(x, n):
    """Number.prototype.toFixed(n). Gerundet wird auf dem exakten Wert der
    Gleitkommazahl, bei Gleichstand nach oben, nicht zur geraden Zahl wie
    in Pythons "%.nf"."""
    q = decimal.Decimal(1).scaleb(-n)
    return format(decimal.Decimal(x).quantize(q, rounding=decimal.ROUND_HALF_UP), "f")


def js_round(x):
    """Math.round: die halbe Stelle nach oben, auch bei negativen Zahlen
    (Math.round(-2.5) ist -2)."""
    d = decimal.Decimal(x) + decimal.Decimal("0.5")
    return int(d.to_integral_value(rounding=decimal.ROUND_FLOOR))


def num(n):
    """Math.round(n).toLocaleString("en-US")."""
    return "{:,}".format(js_round(n))


def js_text(v):
    """Was textContent aus einer JSON-Zahl macht. Nur ganze Zahlen sind
    hier vorgesehen, alles andere bricht ab."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError("keine zahl: %r" % (v,))
    if float(v) != int(v):
        raise ValueError("keine ganze zahl: %r" % (v,))
    return str(int(v))


def dstr(s):
    if not s:
        return "—"
    a = s.split("-")
    return "%d %s %s" % (int(a[2]), M[int(a[1]) - 1], a[0])


def usd(n):
    v = abs(n)
    if v >= 1e9:
        k = fixed(v / 1e9, 2) + "B"
    elif v >= 1e6:
        k = fixed(v / 1e6, 1) + "M"
    else:
        k = fixed(v / 1e3, 0) + "K"
    return ("−" if n < 0 else "") + "$" + k


def zeile(o):
    """eine tabellenzeile, genau der string aus dem seitenskript."""
    small = o["kas"] < STAUB
    tx = o["tx"]
    sh = tx[:10] + "…" + tx[-6:] if tx else "—"
    return ('<tr' + (' class="dust"' if small else '') + '><td>' + dstr(o["day"])
            + '</td><td class="n">' + num(o["kas"]) + '</td>'
            + '<td class="tx"><a href="https://explorer.kaspa.org/txs/' + tx
            + '" target="_blank" rel="noopener" title="' + tx + '">' + sh
            + '</a></td></tr>')


# ------------------------------------------------------------ die rechnung

def pruefe_datei(cb):
    """Was die Datei mitbringen muss, damit der Stempel nichts Falsches
    schreibt. Fehlt etwas, bricht der Lauf ab: dann bleibt der alte Commit
    stehen, Seite und Datei zusammen, und jemand sieht nach."""
    fehler = []
    for f in ("reliable", "deposits", "first_deposit", "last_deposit",
              "kas_received", "outflow_kas", "outflow_count", "outflows",
              "last_outflow"):
        if cb.get(f) is None:
            fehler.append("%s fehlt in der datei" % f)
    if fehler:
        return fehler
    out = cb["outflows"]
    if not out:
        fehler.append("outflows ist leer")
        return fehler
    tage = [o["day"] for o in out]
    if tage != sorted(tage):
        fehler.append("outflows ist nicht nach datum sortiert, "
                      "outflows[-1] waere nicht der letzte abfluss")
    if cb["last_outflow"] != out[-1]["day"]:
        fehler.append("last_outflow %s ist nicht outflows[-1].day %s"
                      % (cb["last_outflow"], out[-1]["day"]))
    if cb["outflow_count"] != len(out):
        fehler.append("outflow_count %s, aber %d eintraege in outflows"
                      % (cb["outflow_count"], len(out)))
    summe = sum(o["kas"] for o in out)
    if abs(summe - cb["outflow_kas"]) > 0.01 * len(out):
        fehler.append("outflow_kas %s, summe der eintraege %.2f"
                      % (cb["outflow_kas"], summe))
    for o in out:
        if not re.fullmatch(r"[0-9a-f]{64}", o.get("tx") or ""):
            fehler.append("transaktion ohne gueltige nummer am %s" % o.get("day"))
    if cb["reliable"] and not all(cb.get(f) for f in (
            "avg_cost_usd", "usd_invested", "price_now", "balance_kas")):
        fehler.append("reliable, aber preis, bestand oder einsatz fehlt")
    return fehler


def werte(cb):
    """Alles, was das Seitenskript aus der Datei rechnet, bevor ein Live-Kurs
    da ist. Gibt (texte, tabelle, pnl_klasse, box_aus) zurueck."""
    t = {}
    ok = bool(cb.get("reliable") and cb.get("avg_cost_usd"))
    if ok:
        t["cbAvg"] = "$" + fixed(cb["avg_cost_usd"], 4)
        t["factCost"] = "$" + fixed(cb["avg_cost_usd"], 4)
        t["cbSub"] = ("across " + js_text(cb["deposits"]) + " deposits between "
                      + dstr(cb["first_deposit"]) + " and " + dstr(cb["last_deposit"]))
        t["cbInv"] = usd(cb["usd_invested"])
        # paint(null, null): kurs und bestand vom letzten botlauf
        val = cb["balance_kas"] * cb["price_now"]
        pnl = val - cb["usd_invested"]
        t["cbVal"] = usd(val)
        pct = pnl / cb["usd_invested"] * 100
        t["cbPnl"] = (usd(pnl) + " (" + ("−" if pct < 0 else "+")
                      + fixed(abs(pct), 0) + "%)")
        klasse = "k " + ("red" if pnl < 0 else "teal")
    else:
        for i in ("cbAvg", "factCost", "cbSub", "cbInv", "cbVal", "cbPnl"):
            t[i] = "—"
        klasse = None
    t["cbLastDep"] = dstr(cb["last_deposit"])
    t["oLastDep"] = dstr(cb["last_deposit"])

    share = cb["outflow_kas"] / cb["kas_received"] * 100
    t["oSum"] = t["bSum"] = num(cb["outflow_kas"])
    t["oCnt"] = t["bCnt"] = js_text(cb["outflow_count"])
    t["oShare"] = t["bShare"] = fixed(share, 2) + "%"
    t["oRest"] = t["bRest"] = fixed(100 - share, 2) + "%"

    out = cb["outflows"]
    dust = [o for o in out if o["kas"] < STAUB]
    real = [o for o in out if o["kas"] >= STAUB]
    t["oDustN"] = str(len(dust))
    t["oRealN"] = str(len(real))
    s = 0.0
    for o in real:           # reduce((a,o)=>a+o.kas, 0), in dieser reihenfolge
        s += o["kas"]
    t["oRealSum"] = num(s)
    t["outLast"] = dstr(out[-1]["day"])
    t["outLastKas"] = num(out[-1]["kas"])
    tabelle = [zeile(o) for o in out]
    return t, tabelle, klasse, not ok


def kopfwerte(cb, t, tabelle):
    """Die Werte, nach denen die Kopf-Wache sucht: jeder gestempelte Text,
    dazu die Bestandteile der zusammengesetzten Saetze und jede
    Tabellenzelle."""
    w = set(v for v in t.values() if v and v != "—")
    w.add(js_text(cb["deposits"]))
    w.add(dstr(cb["first_deposit"]))
    w.add(dstr(cb["last_deposit"]))
    if "cbPnl" in t and " (" in t["cbPnl"]:
        a, b = t["cbPnl"].split(" (", 1)
        w.add(a)
        w.add(b.rstrip(")"))
    for z in tabelle:
        for zelle in re.findall(r"<td[^>]*>([^<]+)</td>", z):
            w.add(htmllib.unescape(zelle))
    return sorted(w)


# ------------------------------------------------------------ in die seite

def _element(name):
    return re.compile(r'(<([a-zA-Z0-9]+)\b[^>]*\bid="%s"[^>]*>)(.*?)(</\2>)'
                      % re.escape(name), re.S)


def setz(html, name, inhalt, klasse=None):
    rx = _element(name)
    treffer = rx.findall(html)
    if len(treffer) != 1:
        raise ValueError("id %s steht %d mal auf der seite, erwartet einmal"
                         % (name, len(treffer)))

    def ersatz(m):
        auf = m.group(1)
        if klasse is not None:
            auf, n = re.subn(r'\bclass="[^"]*"', 'class="%s"' % klasse, auf, count=1)
            if n != 1:
                raise ValueError("id %s hat keine klasse" % name)
        return auf + inhalt + m.group(4)

    return rx.sub(ersatz, html, count=1)


def box(html, aus):
    """cbBox aus- oder einblenden, wie das seitenskript es tut."""
    rx = re.compile(r'<div class="cb" id="cbBox"( style="display:none")?>')
    if len(rx.findall(html)) != 1:
        raise ValueError("cbBox steht nicht genau einmal auf der seite")
    return rx.sub('<div class="cb" id="cbBox"%s>' % (' style="display:none"' if aus else ""),
                  html, count=1)


def stempel(html, cb):
    t, tabelle, klasse, aus = werte(cb)
    for name in TEXT_IDS:
        html = setz(html, name, htmllib.escape(t[name], quote=False),
                    klasse if (name == "cbPnl" and klasse) else None)
    html = setz(html, "outBody", "\n      " + "\n      ".join(tabelle) + "\n      ")
    html = box(html, aus)
    return html


# ------------------------------------------------------------ kopf-wache

def kopf(html):
    """der text, in den der stempel nicht kommt: alles vor </head> ohne
    <style>, dazu jedes ld+json."""
    i = html.find("</head>")
    oben = html[:i] if i >= 0 else ""
    oben = re.sub(r"<style\b.*?</style>", " ", oben, flags=re.S)
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return oben + "\n" + "\n".join(ld)


def kopf_funde(html, werte_liste):
    k = kopf(html)
    funde = []
    for v in werte_liste:
        rx = r"(?<![0-9A-Za-z.,$−-])" + re.escape(v) + r"(?![0-9A-Za-z.,%])"
        if re.search(rx, k):
            funde.append(v)
    return funde


# ------------------------------------------------------------ abgleich im browser

class Sammler(HTMLParser):
    """sammelt alles innerhalb der elemente mit den gesuchten ids, als
    folge von (start, tag, attribute), (text, ...), (ende, tag). leere
    zwischenraeume zaehlen nicht, alles andere schon."""

    LEER = {"br", "img", "input", "meta", "link", "hr", "wbr"}

    def __init__(self, ids):
        super().__init__(convert_charrefs=True)
        self.ids = set(ids)
        self.fund = {}
        self.klasse = {}
        self.stil = {}
        self.stack = []      # offene gesuchte elemente: [id, tag, tiefe]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id") == "cbBox":
            self.stil["cbBox"] = re.sub(r"[\s;]", "", a.get("style") or "")
        for s in self.stack:
            if tag == s[1]:
                s[2] += 1
            self.fund[s[0]].append(("start", tag, tuple(sorted(attrs))))
        if a.get("id") in self.ids and tag not in self.LEER:
            self.fund[a["id"]] = []
            self.klasse[a["id"]] = a.get("class")
            self.stack.append([a["id"], tag, 0])

    def handle_endtag(self, tag):
        for s in list(self.stack):
            if tag == s[1]:
                if s[2] == 0:
                    self.stack.remove(s)
                    continue
                s[2] -= 1
            self.fund[s[0]].append(("ende", tag))

    def handle_data(self, data):
        if not data.strip():
            return
        for s in self.stack:
            self.fund[s[0]].append(("text", data))


def sammle(html):
    p = Sammler(ALLE_IDS)
    p.feed(html)
    p.close()
    return p


def finde_browser():
    kandidaten = [os.environ.get("CHROME")] + [shutil.which(n) for n in (
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    kandidaten.append("/opt/pw-browsers/chromium")
    for k in kandidaten:
        if k and os.path.exists(k):
            return k
    return None


def markiert(html, cb):
    """die gestempelte seite mit "§" an jeder gestempelten stelle. rechnet
    das seitenskript nicht, bleibt "§" stehen. die klasse von cbPnl wird
    nur markiert, wenn der stempel sie auch setzt (reliable)."""
    klasse = werte(cb)[2]
    for name in TEXT_IDS:
        html = setz(html, name, MARKE,
                    "k " + MARKE if (name == "cbPnl" and klasse) else None)
    html = setz(html, "outBody", "<tr><td>%s</td></tr>" % MARKE)
    return box(html, False)


class _Stumm(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def im_browser(html, cb, chrome, warte_ms=10000):
    """laedt html mit cb als /data/entity-x-costbasis.json in chromium und
    gibt das dom zurueck, nachdem das seitenskript gelaufen ist."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "data"))
        with open(os.path.join(d, "entity-x.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        with open(os.path.join(d, "data", "entity-x-costbasis.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(cb, fh)
        handler = functools.partial(_Stumm, directory=d)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            url = "http://127.0.0.1:%d/entity-x.html" % srv.server_address[1]
            with tempfile.TemporaryDirectory() as profil:
                r = subprocess.run(
                    [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                     "--no-first-run", "--user-data-dir=" + profil,
                     # ohne proxy, sonst loest der proxy die namen auf und
                     # die sperre darunter greift nicht
                     "--no-proxy-server", "--disable-background-networking",
                     "--disable-component-update",
                     # alles ausser dem eigenen server ist gesperrt. sonst
                     # kaeme der live-kurs dazwischen und cbVal/cbPnl waeren
                     # nicht mehr aus der datei gerechnet.
                     "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                     "--virtual-time-budget=%d" % warte_ms,
                     "--dump-dom", url],
                    capture_output=True, text=True, timeout=120)
        finally:
            srv.shutdown()
            srv.server_close()
    if r.returncode != 0 or "<body" not in r.stdout:
        raise RuntimeError("chromium lief nicht sauber, code %s: %s"
                           % (r.returncode, r.stderr[-600:]))
    return r.stdout


def abgleich(gestempelt, cb, chrome):
    """stellt jede gestempelte stelle gegen das, was der browser aus
    derselben datei rechnet. gibt (beanstandungen, verglichene ids)."""
    dom = im_browser(markiert(gestempelt, cb), cb, chrome)
    q, b = sammle(gestempelt), sammle(dom)
    fehler = []
    if MARKE in "".join(str(x) for i in ALLE_IDS for x in b.fund.get(i, [])) \
            or b.klasse.get("cbPnl") == "k " + MARKE:
        fehler.append("im browser steht noch %s, das seitenskript hat nicht "
                      "(vollstaendig) gerechnet" % MARKE)
    for i in ALLE_IDS:
        if i not in q.fund:
            fehler.append("%s fehlt im quelltext" % i)
            continue
        if i not in b.fund:
            fehler.append("%s fehlt im browser" % i)
            continue
        if q.fund[i] != b.fund[i]:
            # die erste stelle, an der beide auseinanderlaufen
            n = next((k for k, (x, y) in enumerate(zip(q.fund[i], b.fund[i]))
                      if x != y), min(len(q.fund[i]), len(b.fund[i])))
            fehler.append("%s: ab stelle %d quelltext %r, browser %r"
                          % (i, n, q.fund[i][n:n + 2], b.fund[i][n:n + 2]))
    if q.klasse.get("cbPnl") != b.klasse.get("cbPnl"):
        fehler.append("cbPnl: klasse im quelltext %r, im browser %r"
                      % (q.klasse.get("cbPnl"), b.klasse.get("cbPnl")))
    if q.stil.get("cbBox") != b.stil.get("cbBox"):
        fehler.append("cbBox: stil im quelltext %r, im browser %r"
                      % (q.stil.get("cbBox"), b.stil.get("cbBox")))
    return fehler, b


# ------------------------------------------------------------ selftest

def _cb_stub():
    out = [{"day": "2024-03-07", "kas": 2.0, "tx": "a" * 64},
           {"day": "2025-05-12", "kas": 3151025.4, "tx": "b" * 64},
           {"day": "2026-09-24", "kas": 2000014.82, "tx": "c" * 64}]
    return {"reliable": True, "deposits": 315, "first_deposit": "2024-03-06",
            "last_deposit": "2026-09-23", "kas_received": 1579595170.22,
            "usd_invested": 136752646.19, "avg_cost_usd": 0.086574,
            "price_now": 0.03997, "balance_kas": 1524392806.78,
            "outflow_kas": 5151042.22, "outflow_count": 3, "outflows": out,
            "last_outflow": "2026-09-24"}


def _seite_stub():
    teile = ['<html><head><title>t</title><style>.a{font-size:25px}</style></head><body>']
    for i in TEXT_IDS:
        cls = ' class="k red"' if i == "cbPnl" else ""
        teile.append('<span%s id="%s">alt</span>' % (cls, i))
    teile.append('<div class="cb" id="cbBox"></div>')
    teile.append('<table><tbody id="outBody"><tr><td>alt</td></tr></tbody></table>')
    teile.append('<script type="application/ld+json">{"text": "nichts"}</script>')
    teile.append("</body></html>")
    return "".join(teile)


def run_selftest():
    fails = []

    def check(name, ist, soll):
        if ist != soll:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, ist, soll))

    # die javascript-rundungen
    check("toFixed rundet die exakte zahl", fixed(0.086574, 4), "0.0866")
    check("toFixed bei gleichstand nach oben", fixed(0.125, 2), "0.13")
    check("toFixed ganz", fixed(55.45, 0), "55")
    check("Math.round halb nach oben", num(2.5), "3")
    check("Math.round negativ halb", js_round(-2.5), -2)
    check("Math.round tausender", num(2000014.82), "2,000,015")
    check("Math.round knapp", num(2000014.49), "2,000,014")
    check("dstr ohne fuehrende null", dstr("2026-09-04"), "4 Sep 2026")
    check("dstr leer", dstr(None), "—")
    check("usd millionen negativ", usd(-75822665.71), "−$75.8M")
    check("usd milliarden", usd(1.5e9), "$1.50B")
    check("usd tausend", usd(1500), "$2K")
    check("ganze zahl als text", js_text(315), "315")
    check("315.0 wie in javascript", js_text(315.0), "315")

    cb = _cb_stub()
    check("stub ist in ordnung", pruefe_datei(cb), [])
    t, tabelle, klasse, aus = werte(cb)
    check("letzter abfluss datum", t["outLast"], "24 Sep 2026")
    check("letzter abfluss menge, gerundet wie die tabelle", t["outLastKas"], "2,000,015")
    check("staub gezaehlt", (t["oDustN"], t["oRealN"]), ("1", "2"))
    check("echte summe", t["oRealSum"], num(3151025.4 + 2000014.82))
    check("verlust mit prozent", t["cbPnl"], "−$75.8M (−55%)")
    check("verlust ist rot", klasse, "k red")
    check("box sichtbar", aus, False)
    check("tabellenzeile staub", tabelle[0].startswith('<tr class="dust"><td>7 Mar 2024</td>'), True)

    roh = _seite_stub()
    neu = stempel(roh, cb)
    check("stempeln ist wiederholbar", stempel(neu, cb), neu)
    check("die zahl steht im quelltext", '>2,000,015<' in neu, True)
    check("die alte tabelle ist weg", ">alt<" in neu, False)
    q = sammle(neu)
    check("alle ids gesammelt", sorted(q.fund), sorted(ALLE_IDS))
    check("tabelle hat drei zeilen", sum(1 for x in q.fund["outBody"] if x[:2] == ("start", "tr")), 3)
    check("klasse gelesen", q.klasse["cbPnl"], "k red")

    # die markierte seite hat an jeder gestempelten stelle das zeichen
    m = sammle(markiert(neu, cb))
    check("jede stelle markiert",
          all(any(x == ("text", MARKE) for x in m.fund[i]) for i in ALLE_IDS), True)

    # kopf-wache
    check("leerer kopf ohne fund", kopf_funde(neu, kopfwerte(cb, t, tabelle)), [])
    check("css zaehlt nicht", kopf_funde("<head><style>x{a:25px}</style></head>", ["25"]), [])
    k1 = neu.replace("<title>t</title>", "<title>2,000,015 KAS left</title>")
    check("wert im titel faellt auf", kopf_funde(k1, kopfwerte(cb, t, tabelle)), ["2,000,015"])
    k2 = neu.replace('"nichts"', '"it holds 3 of them"')
    check("wert im ld+json faellt auf", kopf_funde(k2, ["3"]), ["3"])
    check("teilzahl faellt nicht auf", kopf_funde("<head>2,000,0150</head>", ["2,000,015"]), [])
    check("prozent ist ein anderer wert", kopf_funde("<head>25% of</head>", ["25"]), [])

    # unzuverlaessige datei: box aus, kostenwerte weg, abfluesse bleiben
    cb2 = copy.deepcopy(cb)
    cb2["reliable"] = False
    t2, _, k2_, aus2 = werte(cb2)
    check("unzuverlaessig blendet aus", aus2, True)
    check("unzuverlaessig ohne preis", t2["cbAvg"], "—")
    check("abfluesse bleiben", t2["oCnt"], "3")
    n2 = stempel(neu, cb2)
    check("box im quelltext aus", '<div class="cb" id="cbBox" style="display:none">' in n2, True)
    check("und wieder an", '<div class="cb" id="cbBox">' in stempel(n2, cb), True)

    # kaputte dateien werden abgelehnt
    cb3 = copy.deepcopy(cb)
    cb3["outflows"] = list(reversed(cb3["outflows"]))
    check("unsortiert faellt auf", any("sortiert" in f for f in pruefe_datei(cb3)), True)
    cb4 = copy.deepcopy(cb)
    cb4["last_outflow"] = "2026-06-18"
    check("last_outflow passt nicht", any("last_outflow" in f for f in pruefe_datei(cb4)), True)
    cb5 = copy.deepcopy(cb)
    cb5["outflow_count"] = 20
    check("anzahl passt nicht", any("outflow_count" in f for f in pruefe_datei(cb5)), True)
    cb6 = copy.deepcopy(cb)
    cb6["outflows"][0]["tx"] = '"><script>'
    check("tx wird geprueft", any("transaktion" in f for f in pruefe_datei(cb6)), True)

    # doppelte id bricht ab
    try:
        setz(neu + '<b id="oSum">x</b>', "oSum", "1")
        check("doppelte id wirft", True, False)
    except ValueError:
        pass

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, %d faelle" % _faelle())
    return 0


def _faelle():
    import inspect
    return inspect.getsource(run_selftest).count("check(\"")


# ------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datei", default=DATEI)
    ap.add_argument("--seite", default=SEITE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return run_selftest()

    with open(a.datei, encoding="utf-8") as fh:
        cb = json.load(fh)
    with open(a.seite, encoding="utf-8") as fh:
        alt = fh.read()

    fehler = pruefe_datei(cb)
    if fehler:
        print("datei ABGELEHNT, nichts gestempelt")
        for f in fehler:
            print("  " + f)
        return 1

    t, tabelle, _, _ = werte(cb)
    neu = stempel(alt, cb)
    funde = kopf_funde(neu, kopfwerte(cb, t, tabelle))

    if not a.check:
        if funde:
            print("KOPF-WACHE: diese gestempelten werte stehen auch im kopf "
                  "oder im ld+json, dort friert der stempel sie ein: %s" % funde)
            return 1
        if neu == alt:
            print("seite war schon auf dem stand der datei")
        else:
            with open(a.seite, "w", encoding="utf-8") as fh:
                fh.write(neu)
            print("seite gestempelt, %d stellen, %d tabellenzeilen, letzter abfluss %s %s KAS"
                  % (len(TEXT_IDS), len(tabelle), t["outLast"], t["outLastKas"]))
        return 0

    schlecht = []
    if neu != alt:
        schlecht.append("die seite ist nicht auf dem stand der datei, "
                        "scripts/entity_x_page.py laufen lassen")
    if funde:
        schlecht.append("kopf-wache: im kopf oder ld+json stehen %s" % funde)
    chrome = finde_browser()
    if not chrome:
        schlecht.append("kein chromium gefunden, der abgleich ist nicht gelaufen")
    else:
        f1, dom = abgleich(alt, cb, chrome)
        schlecht += ["abgleich: " + x for x in f1]
        # derselbe abgleich mit reliable=false, gegen die dafuer gestempelte seite
        cb_aus = copy.deepcopy(cb)
        cb_aus["reliable"] = False
        f2, _ = abgleich(stempel(alt, cb_aus), cb_aus, chrome)
        schlecht += ["abgleich reliable=false: " + x for x in f2]
    if schlecht:
        print("pruefung FEHLGESCHLAGEN")
        for s in schlecht:
            print("  " + s)
        return 1
    print("pruefung ok")
    print("  datei        %s, reliable %s" % (os.path.relpath(a.datei, REPO), cb["reliable"]))
    print("  browser      %s" % chrome)
    print("  abgleich     %d stellen und %d tabellenzeilen zeichengleich zum browser, "
          "beide zweige (reliable true und false)" % (len(TEXT_IDS), len(tabelle)))
    print("  kopf-wache   %d werte gesucht, keiner im kopf oder ld+json"
          % len(kopfwerte(cb, t, tabelle)))
    print("  stand:")
    for i in TEXT_IDS:
        print("    %-11s %s" % (i, t[i]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
