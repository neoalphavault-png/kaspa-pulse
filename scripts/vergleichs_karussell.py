#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vergleichs_karussell.py, "Kaspa in Zahlen, zum Anfassen" (Ben, 27.10.2026).

WARUM
Ein wiederholbares Instagram-Karussell im Stil der grossen Vergleichs-Posts:
eine gezaehlte Zahl, uebersetzt in Dinge aus dem Alltag (eine Folie lesen, ein
Kaffee, eine Nacht), mit sehr grosser Zahl und einem freigestellten Objekt.
Dazu ein Einzelbild zu Halloween (31.10.2026).

WOHER DIE ZAHLEN KOMMEN
* die gezaehlte Blockrate aus data/tagesgrafik-log.json, ein Lauf mit
  messwerte.bps und blockrate_sek (Vorgabe 2026-10-21: 9.962 je Sekunde ueber
  600 s). Alles andere ist daraus gerechnet und steht als computed da.
* die Protokollrate 10 je Sekunde seit dem Crescendo-Upgrade am 5 may 2025
* Bitcoin nur als Massstab: ein Block je 600 s, das Ziel des Protokolls
* Halloween: die Emission je Tag vor und nach der Senkung am 4 nov 2026 aus
  startseite.emission (Emissionsplan), also computed

DIE OBJEKTE sind gezeichnet (SVG, Graustufen, freigestellt auf dem Grund).
Die offenen Bildarchive waren aus der Arbeitsumgebung nicht erreichbar, und
gezeichnet gibt es keine Lizenzfrage. Register: docs/hintergruende.md.

WACHEN: karussell.text_pruefen fuer jeden sichtbaren Satz, Bitcoin nur mit
zwei Zahlen ohne Werturteil, jede Zahl mit Datum und counted, source oder
computed, content_wache im Profil feed (Flaeche, Mindestgroessen, Fuss mittig).
Marke: #080B0F, #F2F5F4, #49EACB, Wortmarke KASPA PULSE, kein Falke.

    python3 scripts/vergleichs_karussell.py bauen --lauf 2026-10-21 --ziel out/vergleich
    python3 scripts/vergleichs_karussell.py halloween --ziel out/vergleich
    python3 scripts/vergleichs_karussell.py --selbsttest
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

W, H = 1080, 1350
LOG_GRAFIK = REPO / "data" / "tagesgrafik-log.json"
PROTOKOLL = 10
CRESCENDO = "5 may 2025"
BTC_SEK = 600
MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
DATUM = re.compile(r"\b\d{1,2} (?:%s)\b" % "|".join(MONATE))
HERKUNFT = re.compile(r"\b(counted|computed|source|protocol)\b")
WERTURTEIL = re.compile(r"\b(better|faster than|slower|killer|beats?|wins?|loses?|superior|outdated|dead)\b", re.I)
CTA = "the weekly kaspa numbers by email, link in bio"


class Stopp(Exception):
    pass


def tag(d):
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def ganz(n):
    return "{:,}".format(int(round(n)))


# ------------------------------------------------------------ zahlen

def lauf(datum, log=None):
    """Die gezaehlte Blockrate eines Laufs: (bps, sekunden, datum)."""
    log = log if log is not None else json.loads(LOG_GRAFIK.read_text(encoding="utf-8"))
    for e in log.get("laeufe", []):
        m = e.get("messwerte") or {}
        if e.get("datum") == datum and m.get("bps") and m.get("blockrate_sek"):
            return float(m["bps"]), int(m["blockrate_sek"]), dt.date.fromisoformat(datum)
    raise Stopp("kein lauf mit gezaehlter blockrate am %s" % datum)


def folien(bps, sek, d):
    """Die acht Folien als dicts. Jede Zahl traegt ihr Datum und ihre Herkunft."""
    gez = "%.3f" % bps
    am = tag(d)
    rech = "computed from our count of %s per second on %s" % (gez, am)
    lesen, kaffee, schlaf, zehn = bps * 10, bps * 300, bps * 8 * 3600, bps * BTC_SEK
    schlaf_rund = int(round(schlaf, -3))
    return [
        dict(n=1, art="titel", titel="how fast is kaspa, really?",
             unter="we counted %s blocks per second on %s. swipe." % (gez, am), objekt="stoppuhr",
             quelle="counted by kaspa pulse over %d seconds on %s" % (sek, am)),
        dict(n=2, art="zahl", titel="a block every 0.1 seconds", zahl=str(PROTOKOLL),
             label="blocks per second, the protocol rate since the crescendo upgrade on %s" % CRESCENDO,
             quelle="we counted %s per second on %s over %d seconds" % (gez, am, sek), objekt="bloecke"),
        dict(n=3, art="zahl", titel="while you read this slide, about 10 seconds", zahl=ganz(lesen),
             label="new blocks", quelle=rech, objekt="sanduhr", roh=lesen),
        dict(n=4, art="zahl", titel="while you drink one coffee, about 5 minutes", zahl=ganz(kaffee),
             label="new blocks", quelle=rech, objekt="tasse", roh=kaffee),
        dict(n=5, art="zahl", titel="while you sleep, 8 hours", zahl=ganz(schlaf_rund),
             label="new blocks, rounded from %s" % ganz(schlaf), quelle=rech, objekt="bett", roh=schlaf),
        dict(n=6, art="massstab", titel="in 10 minutes bitcoin adds 1 block by design. kaspa adds about %s."
             % ganz(zehn), links=("1", "block, bitcoin, by design 1 per %d seconds" % BTC_SEK),
             rechts=(ganz(zehn), "blocks, kaspa, %s" % rech),
             quelle="bitcoin by its protocol design, kaspa %s" % rech, objekt=None),
        dict(n=7, art="methode", titel="how we count", zahl=gez,
             label="blocks per second, counted by kaspa pulse on %s over %d seconds" % (am, sek),
             text="we read the rise of the virtual daa score from the kaspa rest api. the protocol rate is %d "
                  "per second since the crescendo upgrade on %s. every other number in this post is computed "
                  "from our count." % (PROTOKOLL, CRESCENDO),
             quelle="counted by kaspa pulse from the kaspa rest api on %s" % am, objekt=None),
        dict(n=8, art="cta", titel="the weekly kaspa numbers by email", zahl="link in bio",
             label="every monday, each number with its date and source", quelle="kaspa pulse, %s" % am,
             objekt="brief"),
    ]


def halloween_daten(heute=dt.date(2026, 10, 27)):
    import startseite
    e = startseite.emission(heute)
    alt, neu = e["vormonat"]["wert"], e["neu"]
    return dict(n=1, art="halloween", titel="the scariest kaspa number this month", zahl=ganz(alt - neu),
                label="KAS less new supply every day from %s" % tag(e["datum"]),
                text="daily emission steps down from %s to %s KAS on %s." % (ganz(alt), ganz(neu), tag(e["datum"])),
                quelle="computed, emission schedule, %s" % tag(heute), cta=CTA, objekt="kuerbis",
                diff=alt - neu, datum=e["datum"])


def texte(f):
    aus = [f.get("titel", ""), f.get("unter", ""), f.get("label", ""), f.get("text", ""), f.get("quelle", ""),
           f.get("cta", "")]
    for seite in ("links", "rechts"):
        if f.get(seite):
            aus.append(f[seite][1])
    return [t for t in aus if t]


def pruefen(fs):
    import karussell
    fehler = []
    for f in fs:
        for v in karussell.text_pruefen(texte(f)):
            # bitcoin nur als massstab und nur auf der massstab-folie (Ben, 27.10.2026)
            if f["art"] == "massstab" and "andere chain 'bitcoin'" in v:
                continue
            fehler.append("folie %d, %s" % (f["n"], v))
        alles = " ".join(texte(f))
        if WERTURTEIL.search(alles):
            fehler.append("folie %d, werturteil" % f["n"])
        if re.search(r"\b(ethereum|solana|cardano|sui|aptos|eth|sol)\b", alles, re.I):
            fehler.append("folie %d, andere chain als bitcoin" % f["n"])
        if f.get("zahl") and f["art"] != "cta" and not (DATUM.search(alles) and HERKUNFT.search(alles)):
            fehler.append("folie %d, zahl ohne datum oder herkunft" % f["n"])
    return fehler


# ------------------------------------------------------------ objekte, gezeichnet

GRAU = """<defs>
<linearGradient id='g1' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#E9ECEB'/><stop offset='1' stop-color='#8E9896'/></linearGradient>
<linearGradient id='g2' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#C9CFCD'/><stop offset='1' stop-color='#5E6866'/></linearGradient>
<linearGradient id='g3' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#4A5250'/><stop offset='.5' stop-color='#B9C0BE'/><stop offset='1' stop-color='#3C4442'/></linearGradient>
<radialGradient id='sch' cx='.5' cy='.5' r='.5'><stop offset='0' stop-color='#000' stop-opacity='.55'/><stop offset='1' stop-color='#000' stop-opacity='0'/></radialGradient>
</defs>"""

OBJEKTE = {
    "sanduhr": GRAU + """
<ellipse cx='230' cy='446' rx='170' ry='18' fill='url(#sch)'/>
<rect x='70' y='22' width='320' height='34' rx='8' fill='url(#g3)'/>
<rect x='70' y='404' width='320' height='34' rx='8' fill='url(#g3)'/>
<rect x='86' y='56' width='16' height='348' fill='url(#g2)'/><rect x='358' y='56' width='16' height='348' fill='url(#g2)'/>
<path d='M130 60 C130 160 214 190 222 230 C214 270 130 300 130 400 L330 400 C330 300 246 270 238 230 C246 190 330 160 330 60 Z'
 fill='#DDE3E1' fill-opacity='.22' stroke='#E9ECEB' stroke-width='5'/>
<path d='M160 92 C168 150 214 178 226 214 L234 214 C246 178 292 150 300 92 Z' fill='url(#g1)' fill-opacity='.85'/>
<path d='M229 220 L231 360' stroke='#C9CFCD' stroke-width='4'/>
<path d='M150 398 C170 340 210 326 230 322 C250 326 290 340 310 398 Z' fill='url(#g1)'/>
<path d='M150 80 C150 140 190 170 205 190' stroke='#fff' stroke-opacity='.5' stroke-width='6' fill='none'/>""",
    "tasse": GRAU + """
<ellipse cx='230' cy='430' rx='200' ry='22' fill='url(#sch)'/>
<ellipse cx='230' cy='398' rx='196' ry='34' fill='url(#g2)'/>
<ellipse cx='230' cy='390' rx='150' ry='20' fill='#3C4442'/>
<path d='M96 170 L364 170 C364 300 320 380 230 386 C140 380 96 300 96 170 Z' fill='url(#g1)'/>
<ellipse cx='230' cy='170' rx='134' ry='26' fill='#E9ECEB'/>
<ellipse cx='230' cy='174' rx='118' ry='19' fill='#3A2F2A'/>
<path d='M360 200 C440 196 446 300 352 310' stroke='url(#g2)' stroke-width='24' fill='none' stroke-linecap='round'/>
<path d='M120 196 C126 280 156 340 200 364' stroke='#fff' stroke-opacity='.45' stroke-width='10' fill='none' stroke-linecap='round'/>
<path d='M190 140 C170 110 214 90 196 56 M236 140 C216 104 262 86 244 46 M280 140 C262 112 302 94 286 62'
 stroke='#C9CFCD' stroke-opacity='.7' stroke-width='8' fill='none' stroke-linecap='round'/>""",
    "bett": GRAU + """
<ellipse cx='230' cy='420' rx='220' ry='20' fill='url(#sch)'/>
<rect x='24' y='120' width='26' height='290' rx='8' fill='url(#g3)'/>
<rect x='410' y='230' width='24' height='180' rx='8' fill='url(#g3)'/>
<rect x='40' y='300' width='384' height='60' rx='12' fill='url(#g2)'/>
<rect x='46' y='250' width='378' height='62' rx='20' fill='#E9ECEB'/>
<rect x='62' y='196' width='130' height='70' rx='30' fill='url(#g1)'/>
<path d='M150 262 C200 228 300 226 424 240 L424 330 C300 336 200 330 150 316 Z' fill='url(#g1)'/>
<path d='M180 270 C250 252 330 252 410 262' stroke='#fff' stroke-opacity='.5' stroke-width='6' fill='none'/>
<path d='M300 160 l18 0 l-18 22 l18 0 M340 120 l12 0 l-12 15 l12 0 M368 92 l9 0 l-9 11 l9 0' stroke='#C9CFCD'
 stroke-width='5' fill='none' stroke-linejoin='round'/>""",
    "stoppuhr": GRAU + """
<ellipse cx='230' cy='440' rx='170' ry='18' fill='url(#sch)'/>
<rect x='204' y='18' width='52' height='34' rx='8' fill='url(#g3)'/>
<rect x='220' y='48' width='20' height='26' fill='url(#g2)'/>
<path d='M330 92 l30 -30 l22 22 l-30 30 Z' fill='url(#g3)'/>
<circle cx='230' cy='250' r='182' fill='url(#g2)'/>
<circle cx='230' cy='250' r='158' fill='#E9ECEB'/>
<g stroke='#3C4442' stroke-width='6' stroke-linecap='round'>
<path d='M230 104 v24 M230 372 v24 M84 250 h24 M352 250 h24 M127 147 l16 16 M317 337 l16 16 M127 353 l16 -16 M317 163 l16 -16'/></g>
<path d='M230 250 L300 150' stroke='#49EACB' stroke-width='9' stroke-linecap='round'/>
<path d='M230 250 L230 170' stroke='#3C4442' stroke-width='7' stroke-linecap='round'/>
<circle cx='230' cy='250' r='14' fill='#3C4442'/>
<path d='M120 170 C140 130 180 110 220 104' stroke='#fff' stroke-opacity='.6' stroke-width='8' fill='none' stroke-linecap='round'/>""",
    "bloecke": "".join("<rect x='%d' y='196' width='40' height='68' rx='6' fill='#49EACB' fill-opacity='%.2f'/>"
                       % (6 + i * 45, 1 - i * 0.06) for i in range(10)),
    "brief": GRAU + """
<ellipse cx='230' cy='410' rx='200' ry='18' fill='url(#sch)'/>
<rect x='40' y='120' width='380' height='260' rx='16' fill='url(#g1)'/>
<path d='M44 132 L230 270 L416 132' stroke='#5E6866' stroke-width='10' fill='none' stroke-linejoin='round'/>
<path d='M44 370 L180 236 M416 370 L280 236' stroke='#8E9896' stroke-width='6' fill='none'/>
<circle cx='380' cy='132' r='34' fill='#49EACB'/>
<path d='M366 132 l10 10 l18 -20' stroke='#080B0F' stroke-width='7' fill='none' stroke-linecap='round' stroke-linejoin='round'/>""",
    "kuerbis": GRAU + """
<ellipse cx='230' cy='440' rx='210' ry='20' fill='url(#sch)'/>
<path d='M214 96 C210 60 236 34 264 30 L270 46 C248 52 236 70 240 100 Z' fill='url(#g3)'/>
<ellipse cx='130' cy='280' rx='96' ry='150' fill='url(#g2)'/>
<ellipse cx='330' cy='280' rx='96' ry='150' fill='url(#g2)'/>
<ellipse cx='230' cy='280' rx='110' ry='164' fill='url(#g1)'/>
<path d='M168 244 l36 -40 l20 48 Z M292 244 l-36 -40 l-20 48 Z' fill='#49EACB'/>
<path d='M150 320 l26 22 l26 -22 l28 24 l28 -24 l26 22 l26 -22 C300 380 160 380 150 320 Z' fill='#49EACB'/>
<path d='M190 140 C170 190 168 260 186 330' stroke='#fff' stroke-opacity='.35' stroke-width='8' fill='none' stroke-linecap='round'/>""",
    "netz": """
<g stroke='#C9CFCD' stroke-opacity='.55' stroke-width='3' fill='none'>
<path d='M460 0 L180 0 M460 0 L200 120 M460 0 L260 240 M460 0 L360 300 M460 0 L460 320'/>
<path d='M400 0 C392 24 420 30 432 28 C440 40 446 46 460 56'/>
<path d='M330 0 C322 46 372 62 392 58 C404 82 420 98 460 112'/>
<path d='M260 0 C250 70 320 98 352 92 C370 128 394 152 460 174'/>
<path d='M200 0 C190 96 280 134 314 126 C340 176 370 206 460 236'/>
<path d='M362 300 L360 410'/></g>
<g fill='#C9CFCD'><ellipse cx='360' cy='420' rx='16' ry='20'/><circle cx='360' cy='396' r='10'/></g>
<g stroke='#C9CFCD' stroke-width='3'><path d='M346 412 l-18 -10 M346 424 l-20 4 M374 412 l18 -10 M374 424 l20 4'/></g>""",
}


def objekt_svg(name, groesse):
    if not name:
        return ""
    return ("<svg class='objekt' width='%d' height='%d' viewBox='0 0 460 460' aria-hidden='true'>%s</svg>"
            % (groesse, groesse, OBJEKTE[name]))


# ------------------------------------------------------------ seiten

CSS = """
body{margin:0;width:1080px;height:1350px;background:#080B0F;color:#F2F5F4;overflow:hidden;position:relative}
.t{position:absolute;left:72px;right:72px}
.titel{top:80px;font:900 68px/1.06 Archivo,sans-serif;letter-spacing:-.01em;text-wrap:balance}
.gross{font:900 300px/0.9 Archivo,sans-serif;color:#49EACB;letter-spacing:-.03em;white-space:nowrap}
.label{font:600 40px/1.25 'IBM Plex Sans',sans-serif;color:#F2F5F4;text-wrap:balance}
.text{font:400 38px/1.4 'IBM Plex Sans',sans-serif;color:#C9D2CF}
.quelle{bottom:150px;font:400 34px/1.35 'IBM Plex Mono',monospace;color:#A9B7B4}
.fuss{position:absolute;left:50%;bottom:68px;transform:translateX(-50%);white-space:nowrap}
.nr{position:absolute;right:72px;bottom:68px;font:500 34px/1 'IBM Plex Mono',monospace;color:#A9B7B4}
.objekt{position:absolute;z-index:0}
.t,.fuss,.nr{z-index:1}
.cta{font:900 120px/1 Archivo,sans-serif;color:#49EACB}
"""

FIT_JS = """() => {
  const aus = [];
  for (const z of document.querySelectorAll('[data-fit]')) {
    let g = parseFloat(getComputedStyle(z).fontSize), max = parseFloat(z.dataset.fit);
    while (z.scrollWidth > max && g > 200) { g -= 4; z.style.fontSize = g + 'px'; }
    if (z.scrollWidth > max) aus.push('zahl ' + z.textContent + ' ist ' + z.scrollWidth + ' px breit');
  }
  const ts = [...document.querySelectorAll('.t')].map(e => e.getBoundingClientRect());
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i], b = ts[j];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) aus.push('texte ueberlappen');
  }
  for (const o of document.querySelectorAll('.objekt')) {
    const r = o.getBoundingClientRect();
    for (const t of document.querySelectorAll('.t')) {
      const a = t.getBoundingClientRect();
      if (a.left < r.right - 40 && r.left + 40 < a.right && a.top < r.bottom - 40 && r.top + 40 < a.bottom)
        aus.push('objekt liegt auf text ' + t.className);
    }
  }
  return aus;
}"""


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def seite(f, gesamt=8):
    import look_takt
    import wortmarke
    css = look_takt.schriften_css() + CSS + wortmarke.css(groesse=40, sperrung=5, look="dunkel")
    t = []
    a = f["art"]
    if a == "titel":
        t.append("<div class='t titel' data-rolle='titel' style='font-size:118px;top:110px'>%s</div>" % esc(f["titel"]))
        t.append("<div class='t label' style='top:560px;right:520px'>%s</div>" % esc(f["unter"]))
        t.append(objekt_svg("stoppuhr", 470).replace("class='objekt'", "class='objekt' style='right:56px;top:500px'"))
    elif a in ("zahl", "methode"):
        t.append("<div class='t titel' data-rolle='titel'>%s</div>" % esc(f["titel"]))
        t.append("<div class='t gross' data-rolle='zahl' data-fit='936' style='top:330px'>%s</div>" % esc(f["zahl"]))
        if f.get("objekt") == "bloecke":
            t.append("<div class='t label' style='top:640px'>%s</div>" % esc(f["label"]))
            t.append(objekt_svg("bloecke", 460).replace("class='objekt'", "class='objekt' style='left:72px;top:760px'")
                     .replace("width='460' height='460' viewBox='0 0 460 460'",
                              "width='936' height='200' viewBox='0 170 460 110' preserveAspectRatio='xMinYMid meet'"))
        elif f.get("objekt"):
            t.append("<div class='t label' style='top:640px;right:540px'>%s</div>" % esc(f["label"]))
            t.append(objekt_svg(f["objekt"], 460).replace("class='objekt'", "class='objekt' style='right:60px;top:640px'"))
        else:
            t.append("<div class='t label' style='top:640px'>%s</div>" % esc(f["label"]))
        if f.get("text"):
            t.append("<div class='t text' style='top:800px'>%s</div>" % esc(f["text"]))
    elif a == "massstab":
        t.append("<div class='t titel' data-rolle='titel'>%s</div>" % esc(f["titel"]))
        # zwei zahlen nebeneinander, gleich gross, ohne werturteil. die spalten sind
        # so breit wie ihre zahl, "5,977" braucht bei 200 px rund 570 px
        for links, breite, farbe, (z, lab) in ((72, 300, "#F2F5F4", f["links"]), (420, 588, "#49EACB", f["rechts"])):
            t.append("<div class='t gross' data-rolle='zahl' data-fit='%d' style='top:440px;left:%dpx;right:auto;"
                     "font-size:220px;color:%s'>%s</div>" % (breite, links, farbe, esc(z)))
            t.append("<div class='t label' style='top:680px;left:%dpx;right:auto;width:%dpx'>%s</div>"
                     % (links, breite - 24, esc(lab)))
    elif a == "cta":
        t.append("<div class='t titel' data-rolle='titel' style='font-size:96px;top:180px'>%s</div>" % esc(f["titel"]))
        t.append("<div class='t cta' data-rolle='titel' style='top:560px'>%s</div>" % esc(f["zahl"]))
        t.append("<div class='t label' style='top:740px;right:500px'>%s</div>" % esc(f["label"]))
        t.append(objekt_svg("brief", 380).replace("class='objekt'", "class='objekt' style='right:80px;top:700px'"))
    elif a == "halloween":
        t.append(objekt_svg("netz", 400).replace("class='objekt'", "class='objekt' style='right:60px;top:60px'"))
        t.append("<div class='t titel' data-rolle='titel' style='right:500px;font-size:72px;top:96px'>%s</div>"
                 % esc(f["titel"]))
        t.append("<div class='t gross' data-rolle='zahl' data-fit='936' style='top:440px'>%s</div>" % esc(f["zahl"]))
        t.append("<div class='t label' style='top:720px;right:470px'>%s</div>" % esc(f["label"]))
        t.append("<div class='t text' style='top:900px;right:470px'>%s</div>" % esc(f["text"]))
        t.append(objekt_svg("kuerbis", 340).replace("class='objekt'", "class='objekt' style='right:70px;top:690px'"))
        t.append("<div class='t label' style='bottom:225px;color:#49EACB'>%s</div>" % esc(f["cta"]))
    t.append("<div class='t quelle'>%s</div>" % esc(f["quelle"]))
    t.append("<div class='fuss' data-rolle='fuss'>%s</div>" % wortmarke.html())
    if a != "halloween":
        t.append("<div class='nr'>%d/%d</div>" % (f["n"], gesamt))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>"
            % (css, "".join(t)))


def rendern(fs, ziel, praefix):
    from playwright.sync_api import sync_playwright
    import content_wache
    import tagesgrafik as tg
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    pngs = []
    with sync_playwright() as pw:
        b = tg.chromium_start(pw)
        try:
            for f in fs:
                png = ziel / ("%s-%02d.png" % (praefix, f["n"]))
                html = png.with_suffix(".html")
                html.write_text(seite(f, len(fs)), encoding="utf-8")
                pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
                try:
                    pg.goto(html.resolve().as_uri())
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(150)
                    fehler = pg.evaluate(FIT_JS)
                    if fehler:
                        raise Stopp("folie %d, %s" % (f["n"], "; ".join(fehler)))
                    pg.screenshot(path=str(png))
                    v = content_wache.pruefe_seite(pg, "instagram", png)
                    if v:
                        raise Stopp("folie %d, wache, %s" % (f["n"], "; ".join(v)))
                finally:
                    pg.close()
                    html.unlink()
                pngs.append(png)
        finally:
            b.close()
    return pngs


def caption(bps, d):
    return ("how fast is kaspa, really? we counted %.3f blocks per second on %s over 600 seconds.\n\n"
            "which everyday moment should we count next?\n\n"
            "counted by kaspa pulse, every other number computed from that count. protocol rate 10 per second "
            "since the crescendo upgrade on 5 may 2025.\n\n"
            "Weekly Kaspa numbers in our newsletter, link in bio.\n\n"
            "#kaspa #kas #blockdag #proofofwork #crypto\n\n"
            "what would you compare it with?" % (bps, tag(d)))


def caption_halloween(h):
    return ("the scariest kaspa number this month, %s KAS less new supply every day from %s.\n\n"
            "did you know the cut was this close?\n\n"
            "%s computed from the emission schedule.\n\n"
            "Weekly Kaspa numbers in our newsletter, link in bio.\n\n"
            "#kaspa #kas #halloween #proofofwork #blockdag\n\n"
            "what is your scariest kaspa number?" % (h["zahl"], tag(h["datum"]), h["text"]))


# ------------------------------------------------------------ selbsttest

def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    log = {"laeufe": [{"datum": "2026-10-21", "messwerte": {"bps": 9.962104188874264, "blockrate_sek": 600}}]}
    bps, sek, d = lauf("2026-10-21", log)
    fs = folien(bps, sek, d)
    z = {x["n"]: x for x in fs}
    ok("acht folien", len(fs) == 8)
    ok("gezaehlt 9.962 am 21 oct", "9.962" in z[1]["unter"] and "21 oct 2026" in z[1]["unter"])
    ok("die 10 heisst protokollrate, nicht counted", z[2]["zahl"] == "10" and "protocol rate" in z[2]["label"]
       and "counted" not in z[2]["label"])
    ok("10 s, 100", z[3]["zahl"] == "100")
    ok("5 min, 2,989", z[4]["zahl"] == "2,989")
    ok("8 h, 287,000 gerundet, genau daneben", z[5]["zahl"] == "287,000" and "rounded from 286,909" in z[5]["label"])
    ok("bitcoin massstab 1 gegen 5,977", z[6]["links"][0] == "1" and z[6]["rechts"][0] == "5,977")
    ok("methode nennt 600 s und crescendo", "600 seconds" in z[7]["label"] and "5 may 2025" in z[7]["text"])
    ok("wachen gruen", pruefen(fs) == [], pruefen(fs))
    ok("werturteil faellt auf", pruefen([dict(z[6], titel="kaspa is better than bitcoin")]) != [])
    ok("andere chain faellt auf", pruefen([dict(z[6], titel="faster than solana")]) != [])
    ok("bitcoin ausserhalb des massstabs faellt auf", pruefen([dict(z[3], titel="bitcoin adds 1 block")]) != [])
    ok("zahl ohne datum faellt auf", pruefen([dict(z[3], quelle="computed", label="new blocks")]) != [])
    ok("echtzeitwort faellt auf", pruefen([dict(z[3], titel="right now, 100 blocks")]) != [])
    h = halloween_daten()
    ok("halloween 99,903 am 4 nov", h["zahl"] == "99,903" and h["datum"] == dt.date(2026, 11, 4)
       and "1,779,989 to 1,680,086" in h["text"])
    ok("halloween wachen gruen", pruefen([h]) == [], pruefen([h]))
    import karussell
    ok("caption gruen", karussell.caption_pruefen(caption(bps, d)) == [], karussell.caption_pruefen(caption(bps, d)))
    ok("caption halloween gruen", karussell.caption_pruefen(caption_halloween(h)) == [],
       karussell.caption_pruefen(caption_halloween(h)))
    s = seite(z[4])
    ok("seite mit objekt, wortmarke, kein falke", "class='objekt'" in s and "data-rolle='fuss'" in s
       and "falke" not in s.lower() and "hawk" not in s.lower())
    try:
        lauf("2026-10-20", log)
        ok("lauf ohne blockrate stopp", False)
    except Stopp:
        ok("lauf ohne blockrate stopp", True)
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("schritt", nargs="?", choices=("bauen", "halloween"))
    ap.add_argument("--lauf", default="2026-10-21")
    ap.add_argument("--ziel", default="out/vergleich")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.schritt:
        # Ben, 28.10.2026: das Halloween-Bild und "how fast is kaspa, really?"
        # werden nirgends mehr verwendet, beide tragen gezeichnete Gegenstaende.
        # Halloween baut jetzt look_motor im Look B (docs/grafik-regeln.md).
        print("STOPP eingestellt seit 28.10.2026, siehe docs/grafik-regeln.md, nichts gebaut")
        return 1
    try:
        if a.schritt == "bauen":
            bps, sek, d = lauf(a.lauf)
            fs = folien(bps, sek, d)
            fehler = pruefen(fs) + karussell_caption_fehler(caption(bps, d))
            if fehler:
                raise Stopp("; ".join(fehler))
            for p in rendern(fs, a.ziel, "vergleich-%s" % d.isoformat()):
                print("gebaut", p)
            (Path(a.ziel) / ("vergleich-%s-caption.txt" % d.isoformat())).write_text(caption(bps, d) + "\n",
                                                                                     encoding="utf-8")
            return 0
        if a.schritt == "halloween":
            h = halloween_daten()
            fehler = pruefen([h]) + karussell_caption_fehler(caption_halloween(h))
            if fehler:
                raise Stopp("; ".join(fehler))
            for p in rendern([h], a.ziel, "halloween-2026-10-31"):
                print("gebaut", p)
            (Path(a.ziel) / "halloween-2026-10-31-caption.txt").write_text(caption_halloween(h) + "\n",
                                                                           encoding="utf-8")
            return 0
    except Stopp as exc:
        print("STOPP %s" % exc)
        return 1
    ap.print_help()
    return 2


def karussell_caption_fehler(c):
    import karussell
    return karussell.caption_pruefen(c)


if __name__ == "__main__":
    sys.exit(main())
