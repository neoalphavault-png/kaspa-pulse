#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wortmarke.py - DIE EINE STELLE fuer das Logo von Kaspa Pulse.

Marken-Umstellung (Ben, 21.10.2026): Kaspa Pulse und PulseHawk sind
getrennte Marken. Kaspa Pulse erscheint ohne Falken und ohne den Schriftzug
"PULSEHAWK". An die Stelle des Bildzeichens tritt die Wortmarke:

    KASPA  #F2F5F4   PULSE  #49EACB   Archivo 900

Wer die Marke aendert, aendert sie hier. Alles andere holt sie von hier:
die Tagesgrafik, das Karussell, die Meme-Seite, die Zahl des Tages, der
Cheat-Sheet-Generator, die OG-Bilder und das Favicon.

Die Website traegt ihr Logo im Quelltext jeder Seite, ein Python-Modul kann
sie nicht importieren. Deshalb gibt es hier zwei Befehle:

    python3 scripts/wortmarke.py pruefen      # steht die Marke ueberall gleich?
    python3 scripts/wortmarke.py anwenden     # schreibt sie in jede Seite
    python3 scripts/wortmarke.py bilder       # favicon und die og-karten neu
    python3 scripts/wortmarke.py --selbsttest

"pruefen" ist der Waechter und endet rot, sobald eine Seite abweicht oder
irgendwo wieder ein Falke oder "PULSEHAWK" auftaucht.

FARBEN JE LOOK. Die beiden Marken-Farben sind die des dunklen Looks
(look_takt.LOOKS["dunkel"]: text #F2F5F4, akzent #49EACB). Auf hellem und
tealem Grund waeren sie nicht zu lesen, deshalb nimmt die Marke dort die
Toene desselben Looks. Ein Selbsttest haelt fest, dass "dunkel" genau die
beiden Marken-Farben ergibt.
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------ marke --
WORT_1 = "KASPA"
WORT_2 = "PULSE"
TEXT = "%s %s" % (WORT_1, WORT_2)
FARBE_1 = "#F2F5F4"                  # KASPA
FARBE_2 = "#49EACB"                  # PULSE
SCHRIFT = "'Archivo', sans-serif"
GEWICHT = 900

# Der Falke ist raus. Diese Namen duerfen in keinem Erzeuger mehr vorkommen.
# "alphavault" steht NICHT dabei: der Github-Eigner heisst neoalphavault-png
# und taucht in Adressen auf, das ist keine Marke im Bild.
VERBOTEN_IN_AUSGABEN = ("pulsehawk", "pulse hawk", "falcon.b64", "falke_lesen")
# Dateien, die ueber die ANDERE Marke reden statt sie zu zeigen.
REDET_UEBER = ("wortmarke.py", "wortmarke_bilder.py", "x_post.py", "grafik_check.py")
# Keine Seite traegt PULSEHAWK mehr. Die Ausnahme fuer den alten Kopf der
# Startseite ist mit dem Startseiten-Umbau weg (Ben, 21.10.2026).
NOCH_OFFEN = {}


def farben(look=None):
    """(KASPA, PULSE) fuer einen Look. Ohne Look die Marken-Farben."""
    if not look:
        return FARBE_1, FARBE_2
    import look_takt
    lk = look_takt.LOOKS[look]
    # text traegt KASPA, akzent traegt PULSE. Im dunklen Look sind das genau
    # die Marken-Farben; im hellen ist akzent #0F9A80, weil #49EACB dort nur
    # Markierung ist und auf hellem Grund nicht zu lesen waere.
    return lk["text"], lk["akzent"]


def css(klasse="wm", groesse=34, sperrung=4, look=None, kaspa=None, pulse=None):
    """Der Stilblock fuer die Wortmarke. %%-sicher: diese Funktion gibt
    fertiges CSS zurueck, es laeuft durch kein weiteres %-Format.

    groesse und sperrung duerfen None sein, dann bestimmt sie der Aufrufer
    (der Cheat-Sheet-Kopf setzt sie in em). kaspa und pulse duerfen CSS-
    Variablen tragen, wo die Seite ihre Farben schon je Look fuehrt."""
    k, p = farben(look)
    k, p = kaspa or k, pulse or p
    teile = ["font-family:%s" % SCHRIFT, "font-weight:%d" % GEWICHT, "color:%s" % k,
             "white-space:nowrap"]
    if groesse is not None:
        teile.insert(2, "font-size:%dpx" % groesse)
    if sperrung is not None:
        teile.insert(3, "letter-spacing:%dpx" % sperrung)
    return (".%s{%s}.%s b{font-weight:inherit;color:%s}" % (
        klasse, ";".join(teile), klasse, p))


def html(klasse="wm", rolle=None):
    """Die Wortmarke als Schnipsel. KASPA steht im Element, PULSE im <b>."""
    r = " data-rolle='%s'" % rolle if rolle else ""
    return "<span class='%s'%s>%s <b>%s</b></span>" % (klasse, r, WORT_1, WORT_2)


def svg(breite=1200, groesse=34, sperrung=8, x=0, y=0, kaspa=None, pulse=None):
    """Die Wortmarke als SVG-Text, fuer Bilder ohne Stilblock (OG-Karten)."""
    k, p = kaspa or FARBE_1, pulse or FARBE_2
    return ("<text x='%d' y='%d' font-family=\"%s\" font-weight='%d' font-size='%d' "
            "letter-spacing='%d'><tspan fill='%s'>%s </tspan>"
            "<tspan fill='%s'>%s</tspan></text>" % (
                x, y, SCHRIFT.replace("'", ""), GEWICHT, groesse, sperrung,
                k, WORT_1, p, WORT_2))


# ------------------------------------------------------------- die website --
# Jede Seite traegt das Logo in genau einer Zeile. nlogo ist der Kopf der
# Unterseiten, logo der Kopf der Startseite, brand der Fuss.
WEB_KOPF = '<div class="nlogo"><a href="/">KASPA <span>PULSE</span></a></div>'
WEB_FUSS = '<div class="brand">KASPA <span>PULSE</span></div>'
WEB_RECHT = '<a class="logo" href="/">KASPA <span>PULSE</span></a>'
_ALT_KOPF = re.compile(r'<div class="nlogo"><a href="/">.*?</a></div>')
_ALT_FUSS = re.compile(r'<div class="brand">.*?</div>')
_ALT_RECHT = re.compile(r'<a class="logo" href="/">.*?</a>')
SEITEN = sorted(p.name for p in REPO.glob("*.html"))

# Die Farben der Marke stehen hier als Zahl, nicht als var(--ink): die
# Marke ist die Marke, nicht der Textton der Seite. Der Block haengt am Ende
# des Stilblocks jeder Seite und schlaegt die Regeln davor. Die Schriftart
# bleibt die der Seite; Archivo gehoert zum Startseiten-Umbau, der ueber das
# Laden der Schnitte entscheidet (Ben, 21.10.2026).
MARKE_AUF = "/* wortmarke.py, nicht von hand aendern */"
MARKE_ZU = "/* ende wortmarke.py */"
# Die beiden Gruppen, die die Marke tragen: KASPA und das <span>/<b> PULSE.
_S_KASPA = (".nav .nlogo a", ".logo", "footer .brand")
_S_PULSE = (".nav .nlogo span", ".logo span", "footer .brand span")
# Nur der Fuss, fuer die Seiten mit hellem Look.
_S_FUSS_K = ("footer .brand",)
_S_FUSS_P = ("footer .brand span",)
# HELLER LOOK (Ben, 21.10.2026). Die Startseite folgt seit dem Umbau dem
# System: hell als Grundfall, dunkel ueber zwei Abfragen. #F2F5F4 fest ist
# auf hellem Grund nicht zu lesen, deshalb hat der Umbau den Block mit
# "html footer .brand{color:var(--ink)}" uebersteuert - und damit stand die
# Markenfarbe an zwei Stellen. Jetzt schreibt dieser Block beide Looks selbst.
#
# WICHTIG, DER KOPF FOLGT DEM LOOK NICHT. Der Balken oben traegt seine
# eigenen Toene (--bar, --bar-ink, --brand) und bleibt in beiden Looks
# dunkel; sie stehen auf der Startseite nur einmal in :root. Die Marke im
# Kopf bleibt deshalb immer die dunkle. Nur der Fuss steht auf dem Grund
# der Seite und wechselt mit.
_DUNKEL_1 = "@media (prefers-color-scheme: dark){"
_DUNKEL_2_INNEN = ':root:not([data-theme="light"])'
_DUNKEL_2 = ':root[data-theme="dark"]'
# Eine Seite hat einen hellen Look, wenn sie selbst eine Dunkel-Abfrage
# fuehrt: dann ist hell ihr Grundfall. Die Unterseiten tun das nicht, sie
# sind immer dunkel. Das steht als Regel hier und nicht als Liste von
# Dateinamen, damit es von allein stimmt, wenn der Umbau weitergeht.
_DUNKELABFRAGE = "prefers-color-scheme: dark"


def _regel(auswahl, farbe, zusatz="", vor=""):
    """Eine CSS-Regel ueber eine Auswahlgruppe, jedem Teil vorangestellt."""
    teile = ", ".join(("%s %s" % (vor, a)) if vor else a for a in auswahl)
    return "%s { color:%s;%s }" % (teile, farbe, zusatz)


def web_css(hell=False):
    """Der Marken-Block fuer eine Seite.

    hell=False: die Seite ist immer dunkel (alle Unterseiten), eine Farbe.
    hell=True: die Seite folgt dem System (Startseite), also hell als
    Grundfall und dunkel in denselben zwei Abfragen wie die Seite selbst."""
    kd, pd = farben("dunkel")
    zeilen = [_regel(_S_KASPA, kd, " font-weight:%d;" % GEWICHT),
              _regel(_S_PULSE, pd),
              "footer .brand { opacity:1; }"]
    if hell:
        kh, ph = farben("hell")
        zeilen += [
            "/* nur der fuss steht auf dem grund der seite und folgt dem look,",
            "   der balken oben bleibt in beiden looks dunkel */",
            _regel(_S_FUSS_K, kh),
            _regel(_S_FUSS_P, ph),
            _DUNKEL_1,
            "  " + _regel(_S_FUSS_K, kd, vor=_DUNKEL_2_INNEN),
            "  " + _regel(_S_FUSS_P, pd, vor=_DUNKEL_2_INNEN),
            "}",
            _regel(_S_FUSS_K, kd, vor=_DUNKEL_2),
            _regel(_S_FUSS_P, pd, vor=_DUNKEL_2)]
    return "  %s\n%s\n  %s" % (MARKE_AUF,
                                "\n".join("  " + z for z in zeilen), MARKE_ZU)


_ALT_CSS = re.compile(re.escape(MARKE_AUF) + r".*?" + re.escape(MARKE_ZU), re.S)
# Faerbt eine Seite die Marke so, dass sie den Block SCHLAEGT, steht die
# Farbe an zwei Stellen. Genau das ist nach dem Startseiten-Umbau passiert:
# "html footer .brand{color:var(--ink)}" gewinnt gegen "footer .brand" aus
# dem Block, weil es spezifischer ist.
#
# Die gewoehnlichen Regeln der Seiten (".nav .nlogo a { color:var(--txt) }")
# stehen VOR dem Block und sind gleich spezifisch, der Block schlaegt sie.
# Sie sind kein Befund. Gesucht wird nur, was mit html, body oder :root
# davor spezifischer gemacht wurde.
_FREMDE_FARBE = re.compile(
    r"^[^\n{}]*\b(?:html|body|:root)\b[^\n{}]*"
    r"\.(?:brand|nlogo|logo)\b[^\n{}]*\{[^}]*\bcolor\s*:", re.M)


def seite_umschreiben(text, name):
    """(neuer text, zahl der ersetzungen) fuer eine Seite."""
    n = 0
    text, k = _ALT_KOPF.subn(WEB_KOPF, text)
    n += k
    for muster, neu in ((_ALT_FUSS, WEB_FUSS), (_ALT_RECHT, WEB_RECHT)):
        text, k = muster.subn(neu, text)
        n += k
    if n or MARKE_AUF in text:
        text = _css_setzen(text)
    return text, n


def hat_hellen_look(text):
    """True, wenn die Seite selbst eine Dunkel-Abfrage fuehrt. Dann ist hell
    ihr Grundfall und die Marke braucht beide Looks."""
    return _DUNKELABFRAGE in _ALT_CSS.sub(" ", text)


def fremde_markenfarbe(text):
    """Regeln ausserhalb des Blocks, die die Marke selbst faerben."""
    return [m.group(0).strip()
            for m in _FREMDE_FARBE.finditer(_ALT_CSS.sub(" ", text))]


def _css_setzen(text):
    """Haengt den Marken-Block ans Ende des Stilblocks, genau einmal."""
    WEB_CSS = web_css(hat_hellen_look(text))
    if MARKE_AUF in text:
        # der treffer beginnt bei MARKE_AUF, die einrueckung davor bleibt
        # stehen. ohne lstrip waechst sie mit jedem lauf um zwei leerzeichen.
        return _ALT_CSS.sub(lambda m: WEB_CSS.lstrip(), text, count=1)
    i = text.find("</style>")
    if i < 0:
        return text
    return text[:i] + WEB_CSS + "\n" + text[i:]


def anwenden(schreiben=True):
    """Schreibt die Wortmarke in jede Seite. Gibt die geaenderten Namen."""
    geaendert = []
    for name in SEITEN:
        p = REPO / name
        alt = p.read_text(encoding="utf-8")
        neu, n = seite_umschreiben(alt, name)
        if n and neu != alt:
            geaendert.append(name)
            if schreiben:
                p.write_text(neu, encoding="utf-8")
    return geaendert


def erzeuger_treffer():
    """Erzeuger, die noch Falke oder PulseHawk tragen."""
    quellen = sorted((REPO / "scripts").glob("*.py")) + [REPO / "capture.js"]
    treffer = []
    for q in quellen:
        if q.name in REDET_UEBER:
            continue
        t = q.read_text(encoding="utf-8").lower()
        treffer += ["%s: %s" % (q.name, w) for w in VERBOTEN_IN_AUSGABEN if w in t]
    return treffer


def seiten_treffer():
    """Seiten mit mehr PULSEHAWK, als noch offen stehen darf."""
    aus = []
    for name in SEITEN:
        n = (REPO / name).read_text(encoding="utf-8").lower().count("pulsehawk")
        if n > NOCH_OFFEN.get(name, 0):
            aus.append("%s: %dx" % (name, n))
    return aus


def farb_treffer():
    """Seiten, die die Marke ausserhalb des Blocks faerben."""
    aus = []
    for name in SEITEN:
        for r in fremde_markenfarbe((REPO / name).read_text(encoding="utf-8")):
            aus.append("%s faerbt die marke neben dem block: %s" % (name, r[:70]))
    return aus


def pruefen():
    """Befunde als Liste. Leer heisst: die Marke steht ueberall gleich."""
    befunde = erzeuger_treffer() + seiten_treffer() + farb_treffer()
    for name in SEITEN:
        text = (REPO / name).read_text(encoding="utf-8")
        for m in _ALT_KOPF.finditer(text):
            if m.group(0) != WEB_KOPF:
                befunde.append("%s, kopf weicht ab: %s" % (name, m.group(0)[:80]))
        for m in _ALT_FUSS.finditer(text):
            if m.group(0) != WEB_FUSS:
                befunde.append("%s, fuss weicht ab: %s" % (name, m.group(0)[:80]))
    return befunde


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", nargs="?", choices=("pruefen", "anwenden", "bilder"))
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.befehl == "anwenden":
        g = anwenden()
        print("wortmarke geschrieben in %d seiten%s" % (len(g), (": " + ", ".join(g)) if g else ""))
        return 0
    if a.befehl == "bilder":
        import wortmarke_bilder
        return wortmarke_bilder.alle()
    befunde = pruefen()
    for b in befunde:
        print("  " + b)
    print("%d abweichung(en)" % len(befunde))
    return 1 if befunde else 0


def selbsttest():
    fehler = []

    def ok(was, bedingung):
        print("  %s   %s" % ("ok " if bedingung else "FEHL", was))
        if not bedingung:
            fehler.append(was)

    print("wortmarke")
    ok("die marken-farben stehen fest", (FARBE_1, FARBE_2) == ("#F2F5F4", "#49EACB"))
    ok("archivo 900", GEWICHT == 900 and "Archivo" in SCHRIFT)
    ok("der dunkle look gibt genau die marken-farben", farben("dunkel") == (FARBE_1, FARBE_2))
    ok("der helle look nimmt einen lesbaren akzent, nicht die markierung",
       farben("hell") == ("#0B1A17", "#0F9A80"))
    ok("der teale look bleibt dunkel auf teal", farben("teal") == ("#04211C", "#04211C"))
    ok("im schnipsel steht KASPA und PULSE getrennt",
       html() == "<span class='wm'>KASPA <b>PULSE</b></span>")
    ok("das css faerbt KASPA und PULSE verschieden",
       FARBE_1 in css() and FARBE_2 in css() and "900" in css())
    ok("kein prozentzeichen im css, es laeuft durch kein format", "%" not in css())
    ok("groesse und sperrung lassen sich dem aufrufer ueberlassen",
       "font-size" not in css(groesse=None, sperrung=None)
       and "letter-spacing" not in css(groesse=None, sperrung=None))
    ok("css-variablen statt zahlen gehen auch",
       "var(--txt)" in css(kaspa="var(--txt)", pulse="var(--teal)")
       and "var(--teal)" in css(kaspa="var(--txt)", pulse="var(--teal)"))
    ok("das svg traegt beide woerter mit ihrer farbe",
       FARBE_1 in svg() and FARBE_2 in svg() and ">KASPA <" in svg())
    # die website
    auf, _ = seite_umschreiben(
        '<div class="nlogo"><a href="/">PULSE<span>HAWK</span> · KASPA PULSE</a></div>',
        "kaspa-hashrate.html")
    ok("der alte kopf wird zur wortmarke", auf == WEB_KOPF)
    auf, _ = seite_umschreiben('<div class="brand">PULSEHAWK</div>', "index.html")
    ok("der alte fuss wird zur wortmarke", auf == WEB_FUSS)
    auf, n = seite_umschreiben('<a class="logo" href="/">PULSE<span>HAWK</span></a>', "index.html")
    ok("der kopf der startseite wird zur wortmarke", n == 1 and auf == WEB_RECHT)
    idx = (REPO / "index.html").read_text(encoding="utf-8")
    ok("die startseite traegt die wortmarke in kopf und fuss",
       WEB_RECHT in idx and WEB_FUSS in idx and MARKE_AUF in idx)
    ok("zweimal anwenden aendert nichts mehr",
       seite_umschreiben(WEB_KOPF, "kaspa-tvl.html") == (WEB_KOPF, 1))
    mit_block = "<style>\n  a{}\n</style>\n" + WEB_FUSS
    einmal, _ = seite_umschreiben(mit_block, "x.html")
    ok("anwenden ist wiederholbar, auch mit farbblock",
       seite_umschreiben(einmal, "x.html")[0] == einmal and einmal.count(MARKE_AUF) == 1)
    ok("anwenden aendert keine seite, die schon stimmt", anwenden(schreiben=False) == [])
    # heller look (Ben, 21.10.2026)
    ok("eine seite mit dunkel-abfrage hat einen hellen grundfall",
       hat_hellen_look("@media (prefers-color-scheme: dark){:root{--bg:#000}}"))
    ok("eine seite ohne dunkel-abfrage bleibt dunkel",
       not hat_hellen_look(":root{--bg:#050608;--txt:#FFFFFF}"))
    ok("der block selbst zaehlt nicht als dunkel-abfrage der seite",
       not hat_hellen_look(web_css(True)))
    hellblock = web_css(True)
    ok("heller block: der kopf bleibt dunkel, er sitzt auf dem balken",
       hellblock.index("#F2F5F4") < hellblock.index("#0B1A17")
       and ".logo { color:#0B1A17" not in hellblock
       and ".nlogo a, " in hellblock.split("#0B1A17")[0])
    ok("heller block: nur der fuss bekommt die hellen toene",
       all(z.strip().startswith("footer .brand") for z in hellblock.splitlines()
           if "#0B1A17" in z or "#0F9A80" in z))
    ok("heller block traegt beide abfragen der seite, nur fuer den fuss",
       "prefers-color-scheme: dark" in hellblock
       and ':root[data-theme="dark"] footer .brand' in hellblock
       and ':root:not([data-theme="light"]) footer .brand' in hellblock
       and ':root[data-theme="dark"] .logo' not in hellblock)
    ok("dunkler block bleibt eine farbe je wort",
       web_css(False).count("#F2F5F4") == 1 and web_css(False).count("#0B1A17") == 0)
    ok("eine farbe neben dem block faellt auf",
       fremde_markenfarbe("html footer .brand{color:var(--ink)}"))
    ok("eine groesse neben dem block ist erlaubt",
       not fremde_markenfarbe("footer .brand{font:900 16px/1 Archivo}"))
    ok("die gewoehnliche regel der seite ist kein befund, der block schlaegt sie",
       not fremde_markenfarbe(".nav .nlogo a { color:var(--txt); }"))
    ok("keine seite faerbt die marke neben dem block: %s"
       % (farb_treffer() or "keine"), not farb_treffer())
    ok("nur die startseite traegt den hellen block",
       [n for n in SEITEN
        if "#0B1A17" in (REPO / n).read_text(encoding="utf-8")] == ["index.html"])
    ok("keine seite weicht ab", not pruefen())
    ok("kein erzeuger traegt noch falke oder pulsehawk: %s" % (erzeuger_treffer() or "keiner"),
       not erzeuger_treffer())
    ok("keine seite traegt pulsehawk: %s"
       % (seiten_treffer() or "keine"), not seiten_treffer())
    ok("graphics/falcon.b64 ist weg", not (REPO / "graphics" / "falcon.b64").exists())
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(_main())
