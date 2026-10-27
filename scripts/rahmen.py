#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rahmen.py, derselbe Rahmen fuer alle Unterseiten (Ben, 22.10.2026, PR 3).

Kopf, Menue, Fuss, Farben und Schrift wie auf der Startseite. Die Inhalte der
Seiten bleiben, wie sie sind: kein Satz, keine Zahl, keine id aendert sich,
in die ein Generator (seiten_zahlen, covenants_page, entity_x_page, seo_faq)
schreibt.

WAS DAS SKRIPT JE SEITE TUT, wiederholbar, ein zweiter Lauf aendert nichts:
  1. im Kopf /rahmen.css vor den eigenen Stilblock, am Ende /rahmen.js
  2. der alte Kopf (nav class="nav", auf impressum und datenschutz ein
     header mit Logo) weicht dem Balken der Startseite zwischen
     <!--AUTO:rahmen-kopf--> und <!--/AUTO:rahmen-kopf-->, das Menue aus
     MENUE in capture.js, der eigene Punkt markiert
  3. vor dem Fuss die Kanal-Knoepfe <!--AUTO:rahmen-kanaele-->, im Fuss die
     Wortmarke <!--AUTO:rahmen-marke-->. Was der Fuss sonst traegt (Stand,
     weiterlesen, how we fund this), bleibt stehen.
  4. die festen Farbwerte im eigenen Stilblock und in style-Attributen werden
     zu den Variablen aus rahmen.css, damit die Seite hell und dunkel kann.
     Ausgenommen sind die :root-Zeile der Seite (sonst zeigte eine Variable
     auf sich selbst), der Block von wortmarke.py und alles zwischen
     AUTO-Marken der Generatoren. Deren SVG-Farben faengt rahmen.css ueber
     Attribut-Selektoren ab.

Das Menue haelt seo_seiten.py taeglich auf dem Stand von MENUE (kopf_setzen).
Der Seitenstand zaehlt den Rahmen nicht mit (seo_seiten.inhalt_hash), und
die Umstellung selbst laesst das Datum jeder Seite stehen (stand_mitnehmen).

    python3 scripts/rahmen.py              anwenden
    python3 scripts/rahmen.py --pruefen    nur pruefen, Exit 1 wenn eine Seite abweicht
    python3 scripts/rahmen.py --selbsttest
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

AUSGENOMMEN = {"index.html", "utm-test.html"}

KOPF = ("<!--AUTO:rahmen-kopf-->", "<!--/AUTO:rahmen-kopf-->")
KANAELE = ("<!--AUTO:rahmen-kanaele-->", "<!--/AUTO:rahmen-kanaele-->")
MARKE = ("<!--AUTO:rahmen-marke-->", "<!--/AUTO:rahmen-marke-->")
CSS_LINK = '<link rel="stylesheet" href="/rahmen.css">'
FONT_PRELOAD = ('<link rel="preload" href="/graphics/fonts/archivo-latin-900-normal.woff2" as="font" '
                'type="font/woff2" crossorigin>')
# Die Fliesstextschrift auch vorab laden (SEO-Runde v2, Ben 27.10.2026):
# Lighthouse mobil mass auf kaspa-halving CLS 0.17, fast alles aus dem
# Tausch der Ersatzschrift gegen IBM Plex Sans im Einleitungsabsatz. Die H1
# der Unterseiten steht auf 700 und nimmt Archivo 800, also auch die vorab.
PLEX_PRELOAD = ('<link rel="preload" href="/graphics/fonts/archivo-latin-800-normal.woff2" as="font" '
                'type="font/woff2" crossorigin>\n'
                '<link rel="preload" href="/graphics/fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" '
                'type="font/woff2" crossorigin>')
JS = '<script src="/rahmen.js" defer></script>'

# feste werte der alten, nur dunklen seiten und ihre variable in rahmen.css
HEX = {
    "050608": "var(--bg)",
    # die baender (.band) laufen von #0B0E14 nach #090C10, ihre karten sind
    # #0F1218. als --card waeren band und karte gleich, also traegt das band
    # den leisen ton --grid, die karte bleibt --card.
    "090C10": "var(--grid)", "0B0E14": "var(--grid)",
    "0A0F14": "var(--card)", "0B0E12": "var(--card)", "0F1218": "var(--card)",
    "101317": "var(--grid)", "14171B": "var(--grid)",
    "15181C": "var(--line)", "181C23": "var(--line)", "1A1D21": "var(--line)", "2A2F36": "var(--line)",
    "3A424B": "var(--line)",
    "FFFFFF": "var(--txt)", "FFF": "var(--txt)", "F2F5F4": "var(--txt)",
    "9BA3AB": "var(--dim)", "7A828C": "var(--dimmer)", "5C6672": "var(--dimmer)",
    "49EACB": "var(--teal)", "1E9E88": "var(--teal)",
    "E36A6A": "var(--red)", "FF6B6B": "var(--red)", "FF5C5C": "var(--red)",
    "E8B04B": "var(--amber)", "E3B85F": "var(--amber)", "E3B96A": "var(--amber)",
    "9BA6F8": "var(--discord)",
}
RGBA = {
    (73, 234, 203): "var(--teal)", (227, 106, 106): "var(--red)", (255, 0, 0): "var(--red)",
    (255, 60, 60): "var(--red)", (255, 255, 255): "var(--txt)", (5, 6, 8): "var(--bg)",
}
HEX_RE = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")
RGBA_RE = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)")
# auf dem discord-knopf bleibt die schrift weiss, der grund ist immer lila
DISCORD_GRUND = re.compile(r"#5865F2", re.I)

KANAL_HTML = """<section class="kpkanal" aria-label="follow kaspa pulse">
  <p>follow kaspa pulse</p>
  <nav aria-label="channels">
    <a href="https://x.com/gokugalax" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.8 3h3.1l-6.8 7.7L22 21h-6.2l-4.9-6.4L5.3 21H2.2l7.3-8.3L1.8 3h6.4l4.4 5.8L17.8 3zm-1.1 16.2h1.7L7.4 4.7H5.6l11.1 14.5z"/></svg>X</a>
    <a href="https://www.youtube.com/channel/UCLheLoijZUZOE79vRtJtJ9Q" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 .5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8zM9.7 15V9l5.8 3-5.8 3z"/></svg>YouTube</a>
    <a href="https://discord.gg/e6snta6Rfg" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.3 4.4A19.6 19.6 0 0 0 15.4 3l-.6 1.3a18 18 0 0 0-5.6 0L8.6 3a19.6 19.6 0 0 0-4.9 1.4C.6 9 0 13.5.3 18a19.8 19.8 0 0 0 6 3l1.3-2a12.8 12.8 0 0 1-2-1l.5-.4a14 14 0 0 0 11.8 0l.5.4-2 1 1.3 2a19.7 19.7 0 0 0 6-3c.4-5.2-.7-9.6-3.4-13.6zM8.7 15.3c-1.2 0-2.1-1-2.1-2.3s.9-2.3 2.1-2.3 2.1 1 2.1 2.3-.9 2.3-2.1 2.3zm6.6 0c-1.2 0-2.1-1-2.1-2.3s.9-2.3 2.1-2.3 2.1 1 2.1 2.3-.9 2.3-2.1 2.3z"/></svg>Discord</a>
    <a href="https://www.instagram.com/kaspapulse" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7.3a4.7 4.7 0 1 0 0 9.4 4.7 4.7 0 0 0 0-9.4zm0 7.7a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm6-7.9a1.1 1.1 0 1 1-2.2 0 1.1 1.1 0 0 1 2.2 0zM17 2H7a5 5 0 0 0-5 5v10a5 5 0 0 0 5 5h10a5 5 0 0 0 5-5V7a5 5 0 0 0-5-5zm3.2 15a3.2 3.2 0 0 1-3.2 3.2H7A3.2 3.2 0 0 1 3.8 17V7A3.2 3.2 0 0 1 7 3.8h10A3.2 3.2 0 0 1 20.2 7v10z"/></svg>Instagram</a>
  </nav>
</section>"""


def seiten():
    return sorted(p.name for p in REPO.glob("*.html") if p.name not in AUSGENOMMEN)


def block(marken, inhalt):
    return "%s\n%s\n%s" % (marken[0], inhalt, marken[1])


def setzen(s, marken, inhalt):
    """Ersetzt den Inhalt zwischen den Marken, gibt None zurueck, wenn sie fehlen."""
    a, b = marken
    if a not in s or b not in s:
        return None
    i, j = s.index(a), s.index(b) + len(b)
    return s[:i] + block(marken, inhalt) + s[j:]


# ---------------------------------------------------------------- farben

def farbe_ersetzen(text, discord=False):
    def hx(m):
        k = m.group(1).upper()
        if discord and k in ("FFFFFF", "FFF"):
            return m.group(0)
        return HEX.get(k, m.group(0))

    def rg(m):
        rgb = tuple(int(x) for x in m.group(1, 2, 3))
        var = RGBA.get(rgb)
        if not var:
            return m.group(0)
        pct = round(float(m.group(4)) * 100, 2)
        return "color-mix(in srgb, %s %s%%, transparent)" % (var, ("%g" % pct))

    return RGBA_RE.sub(rg, HEX_RE.sub(hx, text))


def css_umstellen(css):
    """Jede Regel einzeln, damit der Discord-Knopf seine weisse Schrift behaelt.
    Die :root-Regel der Seite und der Block von wortmarke.py bleiben."""
    import wortmarke
    auf, zu = wortmarke.MARKE_AUF, wortmarke.MARKE_ZU
    teile = re.split("(%s.*?%s)" % (re.escape(auf), re.escape(zu)), css, flags=re.S)
    aus = []
    for t in teile:
        if t.startswith(auf):
            aus.append(t)
            continue

        def regel(m):
            kopf, rumpf = m.group(1), m.group(2)
            if re.match(r"\s*:root\s*$", kopf):
                return m.group(0)
            return "%s{%s}" % (kopf, farbe_ersetzen(rumpf, bool(DISCORD_GRUND.search(rumpf))))

        aus.append(re.sub(r"([^{}]*)\{([^{}]*)\}", regel, t))
    return "".join(aus)


AUTO_RE = re.compile(r"(?s)<!--AUTO:([a-z0-9_-]+)-->.*?<!--/AUTO:\1-->")


def farben_umstellen(s):
    # stilbloecke
    s = re.sub(r"(?s)(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + css_umstellen(m.group(2)) + m.group(3), s)
    # style-attribute, ausserhalb der bloecke der generatoren
    teile, pos = [], 0
    for m in AUTO_RE.finditer(s):
        teile.append((s[pos:m.start()], True))
        teile.append((m.group(0), False))
        pos = m.end()
    teile.append((s[pos:], True))

    def attr(m):
        wert = m.group(3)
        return m.group(1) + m.group(2) + farbe_ersetzen(wert, bool(DISCORD_GRUND.search(wert))) + m.group(2)

    return "".join(re.sub(r"""(style=)(["'])(.*?)\2""", attr, t) if frei else t for t, frei in teile)


# ---------------------------------------------------------------- kopf und fuss

def kopf_html(datei, s, js=None):
    import startseite
    import wortmarke
    ziel = "#subForm" if 'id="subForm"' in s else "/#subscribe"
    return "\n".join([
        '<div class="kpbar">',
        '<header class="top">',
        "  " + wortmarke.WEB_RECHT,
        startseite.menue_html(js, "/" + datei),
        '  <button class="burger" type="button" aria-expanded="false" aria-controls="menu">menu</button>',
        '  <a class="subbtn" href="%s">subscribe</a>' % ziel,
        "</header>",
        "</div>"])


def kopf_setzen(s, datei, js=None):
    """Nur das Menue im Kopf neu, fuer seo_seiten.py (MENUE hat sich geaendert)."""
    neu = setzen(s, KOPF, kopf_html(datei, s, js))
    return s if neu is None else neu


ALT_NAV = re.compile(r"(?s)<nav class=\"nav\">.*?</nav>\n?")
ALT_HEADER = re.compile(r"(?s)[ \t]*<header>\s*<a class=\"logo\".*?</header>\n?")


def anwenden(s, datei, js=None):
    import wortmarke
    # 1. stil und skript
    if CSS_LINK not in s:
        i = s.index("<style")
        s = s[:i] + FONT_PRELOAD + "\n" + CSS_LINK + "\n" + s[i:]
    if PLEX_PRELOAD not in s and FONT_PRELOAD in s:
        s = s.replace(FONT_PRELOAD, FONT_PRELOAD + "\n" + PLEX_PRELOAD, 1)
    if JS not in s:
        if '<script src="/capture.js"' in s:
            s = s.replace('<script src="/capture.js"', JS + '\n<script src="/capture.js"', 1)
        else:
            s = s.replace("</body>", JS + "\n</body>", 1)
    # 2. kopf
    s = ALT_NAV.sub("", s, count=1)
    if KOPF[0] not in s:
        s = ALT_HEADER.sub("", s, count=1)
        s = re.sub(r"(<body[^>]*>\n?)", lambda m: m.group(1) + block(KOPF, "") + "\n", s, count=1)
    s = setzen(s, KOPF, kopf_html(datei, s, js))
    # 3. fuss
    if KANAELE[0] not in s:
        s = re.sub(r"([ \t]*<footer)", lambda m: block(KANAELE, "") + "\n" + m.group(1), s, count=1)
    s = setzen(s, KANAELE, KANAL_HTML)
    if MARKE[0] not in s:
        stand = re.search(r'<div class="stand">.*?</div>\n', s)
        if stand and stand.start() > s.index("<footer"):
            s = s[:stand.end()] + "    " + block(MARKE, "") + "\n" + s[stand.end():]
        else:
            s = re.sub(r"(<footer[^>]*>\n?)", lambda m: m.group(1) + "    " + block(MARKE, "") + "\n", s, count=1)
    s = setzen(s, MARKE, wortmarke.WEB_FUSS)
    # 4. farben
    return farben_umstellen(s)


# ---------------------------------------------------------------- seitenstand

def stand_mitnehmen(alt_texte, neu_texte):
    """Die Umstellung ist kein neuer Inhalt. Stimmte der gespeicherte Hash einer
    Seite vorher, bekommt sie den neuen Hash mit ihrem alten Datum."""
    import seo_seiten
    st = seo_seiten.stand_laden()
    for datei, alt in alt_texte.items():
        e = st.get(datei)
        if e and e.get("hash") == seo_seiten.inhalt_hash(alt):
            e["hash"] = seo_seiten.inhalt_hash(neu_texte[datei])
    (REPO / seo_seiten.STAND).write_text(seo_seiten.stand_text(st), encoding="utf-8")


def lauf(schreiben=True):
    import wortmarke
    alt_texte, neu_texte, abw = {}, {}, []
    for datei in seiten():
        p = REPO / datei
        alt = p.read_text(encoding="utf-8")
        neu = anwenden(alt, datei)
        # die marke im fuss folgt jetzt dem look, das schreibt wortmarke.py
        neu, _ = wortmarke.seite_umschreiben(neu, datei)
        if neu != alt:
            abw.append(datei)
            alt_texte[datei], neu_texte[datei] = alt, neu
    if schreiben and abw:
        for datei in abw:
            (REPO / datei).write_text(neu_texte[datei], encoding="utf-8")
        stand_mitnehmen(alt_texte, neu_texte)
    return abw


# ---------------------------------------------------------------- selbsttest

PROBE = """<!DOCTYPE html>
<html><head>
<title>t</title>
<style>
  :root { --bg:#050608; --teal:#49EACB; }
  .a { color:#7A828C; border:1px solid rgba(73,234,203,0.35); }
  .dc { background:#5865F2; color:#FFFFFF; }
  /* wortmarke.py, nicht von hand aendern */
  .logo { color:#F2F5F4; }
  /* ende wortmarke.py */
</style>
</head>
<body>
<nav class="nav">
  <div class="nt"><div class="nlogo"><a href="/">KASPA <span>PULSE</span></a></div></div>
    <div class="nc">
    <a href="/">dashboard</a>
  </div>
</nav>
<div class="wrap">
  <p style="color:#9BA3AB">x</p>
  <!--AUTO:txchart--><rect fill="#49EACB" style="fill:#49EACB"/><!--/AUTO:txchart-->
  <form id="subForm"></form>
  <footer>
    <div class="stand"><!--AUTO:seitenstand-->page last updated 1 May 2026<!--/AUTO:seitenstand--></div>
    <div>further reading</div>
  </footer>
</div>
<script src="/capture.js" defer></script>
</body></html>
"""


def selbsttest():
    import seo_seiten
    import wortmarke
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    js = 'var MENUE = [\n    { t: "dashboard", h: "/" },\n    { t: "network", k: [\n      ["hashrate", "/a.html"]\n    ]}\n  ];'
    n = anwenden(PROBE, "a.html", js)
    ok("rahmen.css vor dem eigenen stil", n.index(CSS_LINK) < n.index("<style"))
    ok("rahmen.js vor capture.js", n.index(JS) < n.index('<script src="/capture.js"'))
    ok("alter kopf weg", '<nav class="nav">' not in n and "nlogo" not in n)
    ok("neuer kopf mit wortmarke", wortmarke.WEB_RECHT in n and n.index(KOPF[0]) < n.index('<div class="wrap">'))
    ok("eigener punkt markiert", 'href="/a.html" aria-current="page"' in n and 'class="gbtn on"' in n)
    ok("subscribe fuehrt zum formular der seite", 'class="subbtn" href="#subForm"' in n)
    ok("kanaele vor dem fuss", n.index(KANAELE[0]) < n.index("<footer"))
    ok("marke im fuss nach der stand-zeile", n.index("<!--/AUTO:seitenstand-->") < n.index(MARKE[0]) < n.index("further reading"))
    ok("inhalt des fusses bleibt", "further reading" in n)
    ok("farben werden variablen", ".a { color:var(--dimmer); border:1px solid color-mix(in srgb, var(--teal) 35%, transparent); }" in n)
    ok(":root der seite bleibt", ":root { --bg:#050608; --teal:#49EACB; }" in n)
    ok("discord-knopf behaelt weisse schrift", ".dc { background:#5865F2; color:#FFFFFF; }" in n)
    ok("wortmarke-block bleibt", ".logo { color:#F2F5F4; }" in n)
    ok("style-attribut umgestellt", '<p style="color:var(--dim)">' in n)
    ok("bloecke der generatoren bleiben", '<rect fill="#49EACB" style="fill:#49EACB"/>' in n)
    ok("zweiter lauf aendert nichts", anwenden(n, "a.html", js) == n)
    ok("der rahmen zaehlt nicht zum seitenstand", seo_seiten.inhalt_hash(n) == seo_seiten.inhalt_hash(PROBE))
    ok("kopf_setzen nimmt ein neues menue", "/b.html" in kopf_setzen(n, "a.html", js.replace("/a.html", "/b.html")))
    ok("rgba mit dezimalen", farbe_ersetzen("rgba(73,234,203,0.08)") == "color-mix(in srgb, var(--teal) 8%, transparent)")
    ok("unbekannte farbe bleibt", farbe_ersetzen("#123456 rgba(0,0,0,0.5)") == "#123456 rgba(0,0,0,0.5)")
    css = (REPO / "rahmen.css").read_text(encoding="utf-8")
    ok("jede variable aus HEX steht in rahmen.css",
       all(("--%s:" % v[6:-1]) in css for v in set(HEX.values()) | set(RGBA.values())))
    ok("rahmen.css hell und dunkel", "prefers-color-scheme: dark" in css and 'html:root[data-theme="dark"]' in css)
    if not f:
        abw = lauf(schreiben=False)
        ok("alle unterseiten tragen den rahmen", not abw, abw)
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    abw = lauf(schreiben=not a.pruefen)
    if a.pruefen:
        for d in abw:
            print("ohne rahmen oder veraltet, %s" % d)
        print("alle unterseiten im rahmen" if not abw else "python3 scripts/rahmen.py laufen lassen")
        return 1 if abw else 0
    print("rahmen gesetzt in %d seiten%s" % (len(abw), (": " + ", ".join(abw)) if abw else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
