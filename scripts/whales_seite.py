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


def formular():
    """Das Formular der Startseite, mit h2 statt h3 und ohne die Zeile zum
    Cheat Sheet: hier gibt es ein einziges Versprechen."""
    f = startseite.anmeldung(1, "subscribe", "get the next edition every monday",
                             "the weekly kaspa numbers in one mail every monday, free, unsubscribe anytime.")
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


def seite(p):
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


def pruefen_inhalt(s, ks):
    import karussell
    fehler = karussell.text_pruefen([t for t in texte(s) if t != VERSPRECHEN])
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


def bauen():
    p = json.loads(PROBE.read_text(encoding="utf-8"))
    s = seite(p)
    f = pruefen_inhalt(s, karten(p))
    if f:
        raise SystemExit("ABBRUCH wache, %s" % "; ".join(f))
    return s


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
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
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
