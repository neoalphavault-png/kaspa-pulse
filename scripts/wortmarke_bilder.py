#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wortmarke_bilder.py - Favicon und die OG-Karten aus der Wortmarke.

Bis zum 21.10.2026 waren favicon.png, og-card.png und og-builders.png
Handarbeit: das Favicon zeigte den Falken, die beiden Karten trugen
"PULSEHAWK · KASPA PULSE". Mit der Marken-Umstellung erzeugt dieses Skript
sie, damit auch sie an scripts/wortmarke.py haengen und eine Aenderung der
Marke eine Stelle bleibt.

    python3 scripts/wortmarke.py bilder        # alle drei neu
    python3 scripts/wortmarke_bilder.py --selbsttest

DAS FAVICON. Eine Wortmarke ist bei 16 px nicht zu lesen. Deshalb steht dort
das Monogramm der Wortmarke: K in #F2F5F4, P in #49EACB, Archivo 900, auf
dem Grund der Seite. Kein neues Bildzeichen, nur die beiden Anfangs-
buchstaben in den Farben der Marke. Wenn Ben etwas anderes will, steht es
hier an einer Stelle.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wortmarke                                              # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GRUND = "#080B0F"                     # derselbe Grund wie die Seiten
DIM = "#9BA3AB"
FAVICON = 256                         # wird vom Browser heruntergerechnet
OG = (1200, 630)

KARTEN = {
    "og-card.png": ("Kaspa, <em>counted.</em>",
                    "On-chain numbers for Kaspa, each with its date and source.",
                    "kaspapulse.com"),
    "og-builders.png": ("Find out what breaks on Kaspa <em>before your users do.</em>",
                        "Kaspa project review and testnet load testing",
                        "kaspapulse.com/for-builders"),
}


def _schriften():
    import look_takt
    return look_takt.schriften_css()


def favicon_html():
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s"
            "*{margin:0;padding:0}html,body{width:%dpx;height:%dpx;background:%s}"
            "div{width:100%%;height:100%%;display:flex;align-items:center;"
            "justify-content:center;font-family:%s;font-weight:%d;font-size:150px;"
            "letter-spacing:-6px;line-height:1}"
            "b{font-weight:inherit}"
            "</style></head><body><div><span style='color:%s'>K</span>"
            "<b style='color:%s'>P</b></div></body></html>" % (
                _schriften(), FAVICON, FAVICON, GRUND, wortmarke.SCHRIFT,
                wortmarke.GEWICHT, wortmarke.FARBE_1, wortmarke.FARBE_2))


def karte_html(titel, unter, fuss):
    titel = titel.replace("<em>", "<em style='font-style:normal;color:%s'>"
                          % wortmarke.FARBE_2)
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s"
            "*{margin:0;padding:0;box-sizing:border-box}"
            "body{width:%dpx;height:%dpx;background:%s;color:%s;padding:90px;"
            "font-family:'IBM Plex Sans',sans-serif;display:flex;"
            "flex-direction:column;-webkit-font-smoothing:antialiased}"
            "%s"
            ".wm{font-size:26px;letter-spacing:8px}"
            "h1{font-family:%s;font-weight:%d;font-size:76px;line-height:1.04;"
            "letter-spacing:-2px;margin-top:38px}"
            ".sub{font-size:30px;color:%s;margin-top:22px}"
            ".fuss{margin-top:auto;border-top:1px solid #1A1D21;padding-top:22px;"
            "font-size:22px;color:%s;letter-spacing:1px}"
            "</style></head><body>%s<h1>%s</h1><div class='sub'>%s</div>"
            "<div class='fuss'>%s</div></body></html>" % (
                _schriften(), OG[0], OG[1], GRUND, wortmarke.FARBE_1,
                wortmarke.css("wm", groesse=None, sperrung=None),
                wortmarke.SCHRIFT, wortmarke.GEWICHT, DIM, DIM,
                wortmarke.html(), titel, unter, fuss))


def _schiessen(html, ziel, breite, hoehe):
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            seite = b.new_page(viewport={"width": breite, "height": hoehe},
                               device_scale_factor=1)
            seite.set_content(html, wait_until="load")
            seite.wait_for_timeout(250)
            seite.screenshot(path=str(ziel))
            seite.close()
        finally:
            b.close()
    return ziel


def alle(ziel=None):
    ziel = Path(ziel) if ziel else REPO
    _schiessen(favicon_html(), ziel / "favicon.png", FAVICON, FAVICON)
    print("favicon.png, %dx%d" % (FAVICON, FAVICON))
    for name, (titel, unter, fuss) in KARTEN.items():
        _schiessen(karte_html(titel, unter, fuss), ziel / name, *OG)
        print("%s, %dx%d" % (name, *OG))
    return 0


def selbsttest():
    fehler = []

    def ok(was, bedingung):
        print("  %s   %s" % ("ok " if bedingung else "FEHL", was))
        if not bedingung:
            fehler.append(was)

    print("wortmarke, bilder")
    f = favicon_html()
    ok("das favicon traegt beide marken-farben",
       wortmarke.FARBE_1 in f and wortmarke.FARBE_2 in f)
    ok("das favicon traegt archivo 900",
       "Archivo" in f and str(wortmarke.GEWICHT) in f)
    k = karte_html(*KARTEN["og-card.png"])
    ok("die og-karte traegt die wortmarke", wortmarke.html() in k)
    ok("die og-karte traegt kein pulsehawk mehr", "pulsehawk" not in k.lower())
    ok("die og-karte traegt keinen falken", "falcon" not in k.lower() and "<img" not in k)
    ok("beide karten sind 1200x630", OG == (1200, 630))
    try:
        import playwright                                     # noqa: F401
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            alle(td)
            da = sorted(p.name for p in Path(td).glob("*.png"))
            ok("drei bilder gerendert, %s" % da,
               da == ["favicon.png", "og-builders.png", "og-card.png"])
            gross = (Path(td) / "og-card.png").stat().st_size
            ok("die og-karte ist ein echtes bild, %d bytes" % gross, gross > 5000)
    except ImportError:
        print("     playwright fehlt, render-probe uebersprungen")
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(selbsttest() if "--selbsttest" in sys.argv else alle())
