#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""whales_seite.py, die Landingpage kaspapulse.com/whales (Ben, 26.10.2026).

WARUM
Die Anzeige ad1-whales-v2 versprach "the 8 kaspa numbers whales watch" und
landete auf der allgemeinen Startseite. 29 Besucher, keine belegte Anmeldung.
Diese Seite loest genau das Versprechen ein: oben der Satz der Anzeige, darunter
eine einzige Anmeldung, dann alle 8 Zahlen sichtbar. Der Grund fuer die
Anmeldung ist die naechste Ausgabe, nicht das Aufdecken.

WOHER DIE ZAHLEN KOMMEN
Die 8 Zahlen des Karussells vom 13.10.2026, also Edition 1 des Cheat Sheets mit
den Daten vom 11.10.2026 (scripts/cheat-sheet-probe.json). Frage, Zahl, Einheit
und Datumszeile baut cheat_sheet.karten(), damit sie zeichengleich zum
Karussell bleiben. Die Herkunft je Zahl (counted, source, computed) steht hier
in HERKUNFT, kuerzer als im Karussell und ohne Hostnamen.

WAS DIE SEITE NICHT HAT
Keine Navigation, kein zweites Formular, kein capture.js. Das Logo fuehrt zur
Startseite, unten stehen nur Impressum und Datenschutz (Pflicht). noindex: die
Seite ist fuer die Anzeige da, nicht fuer die Suche.

Formular, UTM-Felder und utm.js wie auf der Startseite (startseite.anmeldung,
Brevo-Liste #16). Plausible-Block und Signup-Ereignis aus plausible.py.

AB EDITION 2 (Ben, 29.10.2026)
54 Besucher aus der Anzeige, 0 Anmeldungen: die ganze Edition stand offen da.
Ab Edition 2 zeigt die Seite oben die Ueberschrift und genau 2 der 8 Zahlen
(OFFEN) mit Datum und Quelle. Die anderen 6 sind gesperrte Karten: nur die
Frage, statt der Zahl ein unscharfer Block ohne Ziffern, darunter "in the
cheat sheet, free by email". Im HTML der gesperrten Karten steht keine echte
Zahl, der Selbsttest prueft das. Darunter das eine Formular. Kein Countdown,
keine Echtzeitwoerter, keine Kurs- oder Gewinnversprechen.

Die Zahlen kommen frisch aus cheat_sheet.py: festschreiben() dort ruft
festschreiben() hier, das schreibt whales/index.html und data/whales-stand.json
(Probe und Edition). Ohne diese Datei baut die Seite Edition 1 aus
scripts/cheat-sheet-probe.json wie bisher.

    python3 scripts/whales_seite.py --probe [--edition 2]   frisch messen, Vorschau
                                                            390 px nach #ops-log, nichts schreiben

    python3 scripts/whales_seite.py              whales/index.html schreiben
    python3 scripts/whales_seite.py --pruefen    Exit 1, wenn die Datei abweicht
    python3 scripts/whales_seite.py --selbsttest
"""
import argparse
import datetime as dt
import html as htmlmod
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import cheat_sheet  # noqa: E402
import plausible  # noqa: E402
import startseite  # noqa: E402

ZIEL = REPO / "whales" / "index.html"
PROBE = REPO / "scripts" / "cheat-sheet-probe.json"
STAND = REPO / "data" / "whales-stand.json"
# die 2 offenen zahlen ab edition 2: die groesste wallet (die frage der anzeige)
# und der reward cut, eine regel des protokolls, die jeder pruefen kann
OFFEN = (1, 5)
GESPERRT_TEXT = "in the cheat sheet, free by email"
FORM_TITEL = "get all 8 numbers of the %s edition, plus the weekly numbers every monday"
FORM_TEXT = ("free, one mail every monday, unsubscribe anytime. after you confirm, "
             "the cheat sheet pdf comes with the welcome mail.")
URL = "https://kaspapulse.com/whales/"
ANZEIGE = "https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3"

TITEL = "The 8 Kaspa Numbers Whales Watch, Kaspa Pulse"
BESCHREIBUNG = ("8 Kaspa numbers whales watch, each with its date and source. The largest wallet, "
                "exchange balances, unmoved coins, holders, block reward, fees, hashrate and covenants.")


def herkunft(p):
    """Herkunft je Zahl. counted nur fuer eigene Zaehlung, sonst source oder computed."""
    ex = p["zahlen"]["entityx"]
    return {
        1: "counted by kaspa pulse from the public address, supply as of %s" % cheat_sheet.tag_lang(
            ex["umlauf_stichtag"]),
        2: "source kaspalytics",
        3: "source kaspalytics",
        4: "source kaspalytics",
        5: "computed from the emission schedule",
        6: "fees source kaspalytics, new coins computed from the emission schedule",
        7: "source kaspa rest api, 7 day mean computed by kaspa pulse",
        8: "source kaspalytics",
    }


def esc(s):
    return htmlmod.escape(s, quote=True)


ZAHLWORT = {w: i for i, w in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
                                         "nine", "ten", "eleven", "twelve"))}


def ziffern(t):
    """"about one in seven" aus dem Karussell steht hier als "about 1 in 7":
    auf der Website gilt die Zahlregel ohne Ausnahme."""
    return re.sub(r"\bone in (\w+)\b", lambda m: "1 in %d" % ZAHLWORT[m.group(1)]
                  if m.group(1) in ZAHLWORT else m.group(0), t)


def einheit(k):
    """Beim Reward Cut nur das Datum, ohne Uhrzeit, wie im Newsletter (Ben, 26.10.2026)."""
    if k["n"] == 5:
        return re.sub(r",\s*\d{1,2}:\d{2} utc$", "", k["unit"])
    return ziffern(k["unit"])


def karten(p):
    h = herkunft(p)
    return [dict(n=k["n"], q=k["q"], big=k["big"], unit=einheit(k), date=k["date"], src=h[k["n"]])
            for k in cheat_sheet.karten(p)]


def formular(titel="get the next edition every monday",
             text="the weekly kaspa numbers in one mail every monday, free, unsubscribe anytime."):
    """Das Formular der Startseite, mit h2 statt h3 und ohne die Zeile zum
    Cheat Sheet: hier gibt es ein einziges Versprechen."""
    f = startseite.anmeldung(1, "subscribe", titel, text)
    f = f.replace("<h3>", "<h2>").replace("</h3>", "</h2>")
    # web interface guidelines: autocomplete, keine rechtschreibpruefung, platzhalter mit muster
    # (wie in #146 fuer die startseite; ist #146 gemergt, aendert die zeile nichts mehr)
    f = re.sub(r'<input type="email" name="EMAIL" [^>]*>',
               '<input type="email" name="EMAIL" placeholder="you@example.com" aria-label="email" '
               'autocomplete="email" spellcheck="false" required>', f)
    return re.sub(r"\n    <small>.*?</small>", "", f)


STIL = """
@font-face{font-family:Archivo;font-weight:900;font-display:swap;src:url(/graphics/fonts/archivo-latin-900-normal.woff2) format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-weight:400;font-display:swap;src:url(/graphics/fonts/ibm-plex-mono-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-weight:400;font-display:swap;src:url(/graphics/fonts/ibm-plex-sans-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-weight:600;font-display:swap;src:url(/graphics/fonts/ibm-plex-sans-latin-600-normal.woff2) format("woff2")}
/* in beiden looks dunkel wie die anzeige: #080B0F, #F2F5F4, #49EACB (Ben, 26.10.2026) */
:root{--bg:#080B0F;--card:#0F1519;--ink:#F2F5F4;--muted:#A9B7B4;--brand:#49EACB;--chip:#1B252B;color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;touch-action:manipulation}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.55 "IBM Plex Sans",system-ui,sans-serif}
a{color:inherit}
a,button{-webkit-tap-highlight-color:rgba(73,234,203,.25)}
a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
.top{height:56px;display:flex;align-items:center}
.logo{font:900 18px/1 Archivo,sans-serif;letter-spacing:.04em;color:var(--ink);text-decoration:none}
.logo span{color:var(--brand)}
.kopf{display:grid;gap:0 56px;padding:20px 0 36px}
.kopf .lead{margin-bottom:22px}
@media (min-width:900px){.kopf{grid-template-columns:minmax(0,6fr) minmax(0,5fr);align-items:start;padding:48px 0 64px}.kopf h1{grid-column:1/-1;margin-bottom:24px}.kopf .lead{margin:0}}
h1{font:900 clamp(28px,7.4vw,56px)/1.04 Archivo,sans-serif;letter-spacing:-.015em;margin:0 0 14px;text-wrap:balance}
@media (min-width:900px){h1{font-size:clamp(56px,5.6vw,80px)}}
.lead{font-size:17px;color:var(--muted);margin:0;max-width:40ch}
.subscribe{background:var(--card);border-radius:14px;padding:20px}
.subscribe h2{font:900 21px/1.2 Archivo,sans-serif;margin:0 0 6px}
.subscribe p{margin:0 0 14px;color:var(--muted)}
.subscribe form{display:flex;gap:8px;flex-wrap:wrap}
.subscribe input[type=email]{flex:1 1 180px;min-width:0;padding:14px 16px;border-radius:8px;border:0;background:#F2F5F4;color:#080B0F;font:400 16px "IBM Plex Sans",system-ui,sans-serif}
.subscribe input::placeholder{color:#4F625D;opacity:1}
.subscribe button{padding:14px 22px;border:0;border-radius:8px;background:var(--brand);color:#04211C;font:600 16px "IBM Plex Sans",system-ui,sans-serif;cursor:pointer}
.subscribe button:hover{background:#7FF0DA}
.subscribe button:disabled{opacity:.6;cursor:wait}
.subscribe .msg{display:none;margin-top:12px;font-size:15px;font-weight:600}
.subscribe .msg.ok{display:block;color:var(--brand)} .subscribe .msg.err{display:block;color:var(--ink)}
.zahlen{list-style:none;margin:0;padding:0 0 40px;display:grid;gap:12px;grid-template-columns:1fr}
@media (min-width:600px){.zahlen{grid-template-columns:1fr 1fr}}
@media (min-width:1100px){.zahlen{grid-template-columns:repeat(4,1fr)}}
.zahlen li{background:var(--card);border-radius:14px;padding:20px;display:flex;flex-direction:column}
/* die frage ist die ueberschrift der karte, keine kleine kopfzeile (taste-skill) */
.q{font:600 19px/1.3 "IBM Plex Sans",system-ui,sans-serif;color:var(--ink);margin:0 0 12px}
.big{font:900 46px/1 Archivo,sans-serif;color:var(--brand);margin:0 0 6px;font-variant-numeric:tabular-nums}
.unit{margin:0 0 12px;font-weight:600}
.date,.src{font:400 14px/1.5 "IBM Plex Mono",monospace;color:var(--muted);margin:0}
.src{margin-top:auto;padding-top:6px}
/* ab edition 2: gesperrte karten, der block steht fuer die zahl und hat keine ziffer */
.zu li{background:var(--card);border-radius:14px;padding:16px 20px}
.zu .q{color:var(--ink);margin-bottom:10px}
.schleier{display:flex;gap:5px;align-items:flex-end;height:32px;margin:0 0 8px;filter:blur(5px)}
.schleier span{display:block;height:28px;border-radius:6px;background:var(--brand);opacity:.6}
.schleier span:nth-child(1){width:22px}.schleier span:nth-child(2){width:22px;height:24px}.schleier span:nth-child(3){width:9px;height:9px}.schleier span:nth-child(4){width:22px}
.zu .hinweis{margin:0;font-weight:600;color:var(--brand)}
.kopf.v2{padding-bottom:24px}
.kopf.v2 .lead{max-width:52ch}
.unten{padding:0 0 40px}
.unten .subscribe{max-width:620px}
footer{padding:8px 0 40px;font:400 13px/1.7 "IBM Plex Mono",monospace;color:var(--muted)}
footer a{color:var(--muted);display:inline-block;padding:6px 0}
footer a:hover{color:var(--ink)}
"""

SKRIPT = """<script>
(function () {
  // anmeldung im hintergrund, bestaetigung im kasten, wie auf der startseite
  document.querySelectorAll(".subform").forEach(function (form) {
    var box = form.parentNode, msg = box.querySelector(".msg"), btn = form.querySelector("button");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      btn.disabled = true; var alt = btn.textContent; btn.textContent = "\\u2026";
      msg.className = "msg";
      fetch(form.action, { method: "POST", body: new FormData(form) })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.success) {
            %s
            msg.textContent = "\\u2713 almost there. check your inbox and click the confirmation link.";
            msg.className = "msg ok"; form.reset();
          } else {
            msg.textContent = (j && j.message) || "something went wrong, please try again";
            msg.className = "msg err";
          }
        })
        .catch(function () { form.submit(); })
        .then(function () { btn.disabled = false; btn.textContent = alt; });
    });
  });
})();
</script>""" % plausible.SIGNUP.replace("FORM", "form")


def monat_name(p):
    """Der Monat der Edition. Gebaut wird am 1. um 09:00, ein Probelauf am
    letzten Tag davor zeigt schon den neuen Monat: also der Monat des Tages
    nach dem Stand."""
    d = dt.date.fromisoformat(p["stand"]) + dt.timedelta(days=1)
    return cheat_sheet.MONATE_LANG[d.month - 1]


def seite(p, edition=1):
    """Edition 1 alle 8 Zahlen offen, ab Edition 2 die Teaser-Seite."""
    return seite_voll(p) if edition < 2 else seite_teaser(p)


def karte_offen(k):
    return ('  <li>\n'
            '    <h2 class="q">%s</h2>\n'
            '    <p class="big">%s</p>\n'
            '    <p class="unit">%s</p>\n'
            '    <p class="date">%s</p>\n'
            '    <p class="src">%s</p>\n'
            '  </li>' % (esc(k["q"]), esc(k["big"]), esc(k["unit"]), esc(k["date"]), esc(k["src"])))


def karte_zu(k):
    """Nur die Frage. Zahl, Einheit, Datum und Quelle stehen nicht im HTML."""
    return ('  <li class="gesperrt">\n'
            '    <h2 class="q">%s</h2>\n'
            '    <div class="schleier" aria-hidden="true"><span></span><span></span><span></span>'
            '<span></span></div>\n'
            '    <p class="hinweis">%s</p>\n'
            '  </li>' % (esc(k["q"]), esc(GESPERRT_TEXT)))


def seite_teaser(p):
    stand = dt.date.fromisoformat(p["stand"])
    ks = karten(p)
    offen = "\n".join(karte_offen(k) for k in ks if k["n"] in OFFEN)
    zu = "\n".join(karte_zu(k) for k in ks if k["n"] not in OFFEN)
    monat = monat_name(p)
    form = formular(FORM_TITEL % monat, FORM_TEXT)
    return SEITE_KOPF % dict(titel=esc(TITEL), beschr=esc(BESCHREIBUNG), url=URL, stil=STIL,
                             plausible=plausible.BLOCK) + """<section class="kopf v2">
  <h1>%(versprechen)s</h1>
  <p class="lead">the %(monat)s edition, numbers as of %(stand)s. 2 of the 8 are open here, each with its date and where it comes from.</p>
</section>
<ul class="zahlen offen" aria-label="2 of the 8 numbers">
%(offen)s
</ul>
<ul class="zahlen zu" aria-label="6 more numbers in the cheat sheet">
%(zu)s
</ul>
<section class="unten">
%(form)s
</section>
""" % dict(versprechen=VERSPRECHEN, monat=monat, stand=startseite.d_kurz(stand), offen=offen, zu=zu,
           form=form) + SEITE_FUSS % dict(skript=SKRIPT)


SEITE_KOPF = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#080B0F">
<meta name="robots" content="noindex, follow">
<title>%(titel)s</title>
<meta name="description" content="%(beschr)s">
<link rel="canonical" href="%(url)s">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preload" href="/graphics/fonts/archivo-latin-900-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>%(stil)s</style>
%(plausible)s
</head>
<body>
<!-- gebaut von scripts/whales_seite.py, nicht von hand aendern -->
<div class="wrap">
<header class="top"><a class="logo" href="/" translate="no">KASPA <span>PULSE</span></a></header>
<main>
"""

SEITE_FUSS = """</main>
<footer><a href="/impressum.html">legal notice</a> · <a href="/datenschutz.html">privacy</a> · not financial advice</footer>
</div>
%(skript)s
<script src="/utm.js" defer></script>
</body>
</html>
"""


def seite_voll(p):
    stand = dt.date.fromisoformat(p["stand"])
    ks = karten(p)
    lis = "\n".join(
        '  <li>\n'
        '    <h2 class="q">%s</h2>\n'
        '    <p class="big">%s</p>\n'
        '    <p class="unit">%s</p>\n'
        '    <p class="date">%s</p>\n'
        '    <p class="src">%s</p>\n'
        '  </li>' % (esc(k["q"]), esc(k["big"]), esc(k["unit"]), esc(k["date"]), esc(k["src"]))
        for k in ks)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#080B0F">
<meta name="robots" content="noindex, follow">
<title>%(titel)s</title>
<meta name="description" content="%(beschr)s">
<link rel="canonical" href="%(url)s">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preload" href="/graphics/fonts/archivo-latin-900-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>%(stil)s</style>
%(plausible)s
</head>
<body>
<!-- gebaut von scripts/whales_seite.py, nicht von hand aendern -->
<div class="wrap">
<header class="top"><a class="logo" href="/" translate="no">KASPA <span>PULSE</span></a></header>
<main>
<section class="kopf">
  <h1>%(versprechen)s</h1>
  <p class="lead">the october edition, read on %(stand)s. every number with its date and where it comes from.</p>
%(form)s
</section>
<ul class="zahlen" aria-label="the 8 numbers">
%(lis)s
</ul>
</main>
<footer><a href="/impressum.html">legal notice</a> · <a href="/datenschutz.html">privacy</a> · not financial advice</footer>
</div>
%(skript)s
<script src="/utm.js" defer></script>
</body>
</html>
""" % dict(versprechen=VERSPRECHEN, titel=esc(TITEL), beschr=esc(BESCHREIBUNG), url=URL, stil=STIL, plausible=plausible.BLOCK,
           stand=startseite.d_kurz(stand), form=formular(), lis=lis, skript=SKRIPT)


def texte(s):
    s = re.sub(r"(?s)<(script|style|form)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<head>.*?</head>", " ", s)
    aus = []
    for m in re.finditer(r"(?s)<(h1|h2|p|footer)\b[^>]*>(.*?)</\1>", s):
        t = " ".join(htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
        if t:
            aus.append(t)
    return aus


# der satz der anzeige, von Ben vorgegeben (26.10.2026). "whales" steht auf der
# wortliste der tagesgrafik und bleibt dort, ausgenommen ist nur dieser satz.
VERSPRECHEN = "the 8 kaspa numbers whales watch"


def pruefen_inhalt(s, ks, edition=1):
    import karussell
    teaser = edition >= 2
    fehler = karussell.text_pruefen([t for t in texte(s) if t != VERSPRECHEN
                                     and not (teaser and t.startswith("get all 8 numbers of the "))])
    if teaser:
        fehler += gesperrt_pruefen(s, ks)
        ks = [k for k in ks if k["n"] in OFFEN]
        if s.count('<p class="big">') != len(OFFEN):
            fehler.append("nicht genau %d offene zahlen" % len(OFFEN))
        if re.search(r"(?i)\b(countdown|only today|hurry|last chance|ends? in|left)\b", " ".join(texte(s))):
            fehler.append("druck statt grund")
    for k in ks:
        if not startseite.DATUM_RE.search(k["date"] + " " + k["src"]):
            fehler.append("zahl %d ohne datum" % k["n"])
        if not re.search(r"\b(counted|source|computed)\b", k["src"]):
            fehler.append("zahl %d ohne herkunft" % k["n"])
    if s.count("<form") != 1:
        fehler.append("nicht genau ein formular")
    if re.search(r'<a [^>]*href="https?://', s.split("<body>")[1]):
        fehler.append("link nach aussen")
    return fehler


def gesperrt_pruefen(s, ks):
    """Im HTML der gesperrten Karten keine Ziffer und kein Wert der Karte."""
    fehler = []
    zu = re.findall(r'(?s)<li class="gesperrt">.*?</li>', s)
    if len(zu) != 8 - len(OFFEN):
        fehler.append("%d gesperrte karten statt %d" % (len(zu), 8 - len(OFFEN)))
    for li in zu:
        if re.search(r"\d", re.sub(r"<[^>]+>", " ", li)):
            fehler.append("ziffer in einer gesperrten karte, %r" % re.sub(r"\s+", " ", li)[:80])
    gesamt = " ".join(zu)
    for k in ks:
        if k["n"] in OFFEN:
            continue
        for feld in ("big", "unit", "date", "src"):
            if k[feld] and esc(k[feld]) in gesamt:
                fehler.append("zahl %d, %s steht in der gesperrten karte" % (k["n"], feld))
    return fehler


def stand_lesen():
    """(probe, edition): der festgeschriebene Stand aus cheat_sheet.py, sonst Edition 1."""
    if STAND.exists():
        d = json.loads(STAND.read_text(encoding="utf-8"))
        return d["probe"], int(d["edition"])
    return json.loads(PROBE.read_text(encoding="utf-8")), 1


def bauen(p=None, edition=None):
    if p is None:
        p, edition = stand_lesen()
    edition = edition or 1
    s = seite(p, edition)
    f = pruefen_inhalt(s, karten(p), edition)
    if f:
        raise SystemExit("ABBRUCH wache, %s" % "; ".join(f))
    return s


def festschreiben(p, edition):
    """Von cheat_sheet.festschreiben gerufen, nur im scharfen Lauf. Schreibt
    die Seite und den Stand, beides committet der Workflow mit dem PDF."""
    s = bauen(p, edition)
    STAND.write_text(json.dumps({"edition": edition, "probe": p}, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    ZIEL.parent.mkdir(exist_ok=True)
    ZIEL.write_text(s, encoding="utf-8")
    return ZIEL


def vorschau(s, ziel, breite=390):
    """Die Seite in voller Hoehe bei 390 px, mit den Schriften der Website.
    Die Seite verweist mit /graphics/... auf das Repo, deshalb liegt die
    Datei fuer die Aufnahme im Repo-Wurzelverzeichnis und wird danach
    entfernt."""
    from playwright.sync_api import sync_playwright
    tmp = REPO / ".whales-vorschau.html"
    tmp.write_text(s.replace('href="/', 'href="./').replace('src="/', 'src="./')
                   .replace("url(/", "url(./"), encoding="utf-8")
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            import tagesgrafik
            b = tagesgrafik.chromium_start(pw)
            seite_ = b.new_page(viewport={"width": breite, "height": 844}, device_scale_factor=2)
            seite_.route("**/*", lambda r: r.abort() if not r.request.url.startswith("file:") else r.continue_())
            seite_.goto(tmp.as_uri())
            seite_.wait_for_timeout(300)
            seite_.screenshot(path=str(ziel), full_page=True)
            b.close()
    finally:
        tmp.unlink(missing_ok=True)
    return ziel


def probe_senden(edition, ziel_ordner):
    """Frisch messen wie das Cheat Sheet, die Seite bauen, nichts schreiben.
    Die Vorschau in 390 px geht nach #ops-log, nie nach #moderator-only."""
    import ops_melden
    heute = dt.datetime.now(dt.timezone.utc).date()
    p = cheat_sheet.probe(heute)
    cheat_sheet.frische_pruefen(p, dt.date.fromisoformat(p["stand"]))
    s = bauen(p, edition)
    ordner = Path(ziel_ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "index.html").write_text(s, encoding="utf-8")
    png = vorschau(s, ordner / "whales-390.png")
    ks = {k["n"]: k for k in karten(p)}
    offen = "; ".join("%s %s (%s)" % (ks[n]["big"], ks[n]["unit"], ks[n]["date"]) for n in OFFEN)
    text = ("PROBE /whales edition %d, nicht veroeffentlicht. stand %s, %s edition.\n"
            "offen: %s\ngesperrt: %d karten, im html ohne zahl.\n"
            "live geht die seite mit dem scharfen cheat-sheet-lauf (CHEAT_SHEET_LIVE)."
            % (edition, p["stand"], monat_name(p), offen, 8 - len(OFFEN)))
    print(text)
    ops_melden.log(text, [(png, "image/png")], "whales probe")
    return png


def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    p = json.loads(PROBE.read_text(encoding="utf-8"))
    ks = karten(p)
    s = seite(p)
    ok("acht zahlen", len(ks) == 8 and s.count('<p class="big">') == 8)
    ok("zahlen wie im karussell", [k["big"] for k in ks][:2] == ["5.5%", "13.6%"] and ks[3]["big"] == "293,978"
       and ks[5]["big"] == "765x", [k["big"] for k in ks])
    ok("wachen gruen", pruefen_inhalt(s, ks) == [], pruefen_inhalt(s, ks))
    ok("h1 ist das versprechen der anzeige", "<h1>the 8 kaspa numbers whales watch</h1>" in s and s.count("<h1") == 1)
    ok("anmeldung vor den zahlen", s.index('id="subscribe"') < s.index('class="zahlen"'))
    ok("genau ein formular, liste der startseite", s.count("<form") == 1 and startseite.BREVO in s)
    ok("utm-felder mit id fuer utm.js", all('id="%s"' % i in s for i in
                                            ("utmSource", "utmMedium", "utmCampaign", "utmMediumRaw")))
    ok("utm.js eingebunden, capture.js nicht", '<script src="/utm.js" defer>' in s and "capture.js" not in s)
    ok("plausible im kopf, signup im handler", plausible.BLOCK in s.split("</head>")[0]
       and plausible.MARKE_SIGNUP in s and plausible.kopf_setzen(s) == s and plausible.signup_setzen(s) == s)
    ok("logo fuehrt zur startseite", '<a class="logo" href="/"' in s)
    ok("e-mail-feld nach den guidelines", 'autocomplete="email" spellcheck="false"' in s)
    ok("noindex", 'content="noindex, follow"' in s)
    ok("kein falke", "falke" not in s.lower() and "falcon" not in s.lower() and "hawk" not in s.lower())
    ok("reward cut ohne uhrzeit", ks[4]["big"] == "4 nov" and ks[4]["unit"] == "next block reward cut"
       and "13:45" not in s, ks[4]["unit"])
    ok("1 in 7 in ziffern", ks[1]["unit"] == "of all KAS, about 1 in 7", ks[1]["unit"])
    ok("whales nur im versprechen erlaubt",
       pruefen_inhalt(s.replace("source kaspalytics</p>", "whales source kaspalytics</p>", 1), ks) != [])
    ok("echtzeitwort faellt auf", pruefen_inhalt(s.replace("read on", "live on"), ks) != [])
    ok("zweites formular faellt auf", pruefen_inhalt(s + "<form></form>", ks) != [])
    ok("link nach aussen faellt auf",
       pruefen_inhalt(s.replace("</footer>", '<a href="https://example.com">x</a></footer>'), ks) != [])
    ok("anzeige-url mit paid", "utm_medium=paid" in ANZEIGE)

    # ab edition 2 (Ben, 29.10.2026)
    t = seite(p, 2)
    ok("edition 2, wachen gruen", pruefen_inhalt(t, ks, 2) == [], pruefen_inhalt(t, ks, 2))
    ok("edition 2, genau 2 zahlen offen", t.count('<p class="big">') == 2
       and all(esc(ks[n - 1]["big"]) in t for n in OFFEN))
    ok("edition 2, 6 gesperrte karten mit frage", t.count('<li class="gesperrt">') == 6
       and all(esc(k["q"]) in t for k in ks))
    ok("edition 2, keine echte zahl im html der gesperrten",
       all(esc(k[f]) not in t for k in ks if k["n"] not in OFFEN for f in ("big", "unit", "date")),
       [k["big"] for k in ks if k["n"] not in OFFEN and esc(k["big"]) in t])
    ok("edition 2, satz unter den karten", "in the cheat sheet, free by email" in t)
    ok("edition 2, formular nach den karten mit dem satz",
       t.count("<form") == 1 and t.index('class="zahlen zu"') < t.index('id="subscribe"')
       and "get all 8 numbers of the october edition, plus the weekly numbers every monday" in t)
    ok("edition 2, monat aus dem tag nach dem stand",
       monat_name({"stand": "2026-10-31"}) == "november" and monat_name({"stand": "2026-11-01"}) == "november")
    ok("edition 2, ziffer in gesperrter karte faellt auf",
       gesperrt_pruefen(t.replace(GESPERRT_TEXT, "13.6% " + GESPERRT_TEXT, 1), ks) != [])
    ok("edition 2, wert in gesperrter karte faellt auf", gesperrt_pruefen(
        t.replace("free by email</p>", "free by email</p><p>%s</p>" % esc(ks[1]["src"]), 1), ks) != [])
    ok("edition 2, countdown faellt auf",
       pruefen_inhalt(t.replace("free by email</p>", "free by email, only today</p>", 1), ks, 2) != [])
    ok("edition 2, echtzeitwort faellt auf",
       pruefen_inhalt(t.replace("numbers as of", "live numbers as of"), ks, 2) != [])
    ok("edition 2, ohne kurs und gewinn", not re.search(r"(?i)\b(price|profit|gain|moon|usd|\$)", " ".join(texte(t))))
    import tempfile
    alt_stand = globals()["STAND"]
    with tempfile.TemporaryDirectory() as td:
        globals()["STAND"] = Path(td) / "whales-stand.json"
        try:
            ok("ohne stand-datei edition 1", stand_lesen()[1] == 1 and bauen() == s)
            globals()["STAND"].write_text(json.dumps({"edition": 2, "probe": p}), encoding="utf-8")
            ok("mit stand-datei die teaser-seite", stand_lesen()[1] == 2 and bauen() == t)
        finally:
            globals()["STAND"] = alt_stand
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--probe", action="store_true", help="frisch messen, vorschau nach #ops-log, nichts schreiben")
    ap.add_argument("--edition", type=int, default=2)
    ap.add_argument("--vorschau", help="png der gebauten seite in 390 px")
    ap.add_argument("--aus", help="aus einer gespeicherten probe bauen, nur mit --vorschau")
    ap.add_argument("--out", default="graphics/whales-probe")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.probe:
        probe_senden(a.edition, a.out)
        return 0
    if a.vorschau:
        if a.aus:
            s = bauen(json.loads(Path(a.aus).read_text(encoding="utf-8")), a.edition)
        else:
            s = bauen()
        print(vorschau(s, a.vorschau))
        return 0
    s = bauen()
    alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
    if a.pruefen:
        print("whales/index.html passt" if s == alt else "whales/index.html weicht ab, whales_seite.py laufen lassen")
        return 0 if s == alt else 1
    if s != alt:
        ZIEL.parent.mkdir(exist_ok=True)
        ZIEL.write_text(s, encoding="utf-8")
        print("whales/index.html geschrieben")
    else:
        print("whales/index.html unveraendert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
