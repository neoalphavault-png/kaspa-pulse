#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""look_v2.py, Musterblatt Look v2 (Ben, 28.10.2026).

WARUM
Ben 28.10.2026: die selbst gezeichneten Motive (Kaffee, Sanduhr, Kuerbis)
wirken "sehr basic, wie fuer Kinder". Regel ab jetzt: keine selbst
gezeichneten Piktogramme oder Gegenstaende aus SVG-Formen mehr. Dieses
Skript baut dieselben zwei Inhalte in drei Richtungen, Ben waehlt.

    A  Editorial    die Typografie traegt alles, feine Linien, Papier oder Teal
    B  Foto-Objekt  ein Foto als Vollbild, Text nur auf ruhiger Flaeche
    C  Daten-Kunst  das Motiv besteht aus echten Daten, ein Punkt je Einheit
    D  Neutral und Gruen (Fassung 2, Bens Idee): neutraler Grund, eine Zahl
       oder eine Zeile in #49EACB, kleine Wortmarke. Der Grund ist warmer
       dunkler Stein: Teal als Schrift erreicht auf warmem Weiss nur 1.3:1,
       auf Stein ueber 7:1.

    Inhalt 1  Halloween Sa 31.10.2026, die Emissionsstufe am 4 nov 2026
    Inhalt 2  Kaspa in real life, Bloecke waehrend eines Espressos

WOHER DIE ZAHLEN KOMMEN
* Inhalt 1 aus dem Emissionsplan (startseite.emission), computed.
* Inhalt 2 aus unserer Zaehlung vom 27.10.2026, 5,953 Bloecke in 600.243 s
  (docs/suchbild/README.md), fuer 300 s gerechnet, also computed aus counted.

Fotos: graphics/fotos/, Register in docs/look-v2/README.md.
Jede Seite laeuft durch content_wache im Profil feed (Groessen, Textregeln,
Kontrast 7:1). Bei den Fotos entfaellt nur die Pruefung des 60-px-Rands,
weil das Foto bis an den Rand geht.

    python3 scripts/look_v2.py --ziel docs/look-v2
    python3 scripts/look_v2.py --selbsttest
"""
import argparse
import base64
import datetime as dt
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

W, H = 1080, 1350
PAPIER, TINTE, TEAL, NACHT, TEAL_DUNKEL = "#F4F1EA", "#0B1A17", "#49EACB", "#080B0F", "#062B24"
STEIN = {"D1": "#1F1D1A", "D2": "#3A3733"}
STAND = dt.date(2026, 10, 28)
ZAEHLUNG = {"bloecke": 5953, "sek": 600.243, "datum": dt.date(2026, 10, 27)}
MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def tag(d):
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def ganz(n):
    return "{:,}".format(int(round(n)))


def daten():
    import startseite
    e = startseite.emission(STAND)
    alt, neu = e["vormonat"]["wert"], e["neu"]
    espresso = ZAEHLUNG["bloecke"] / ZAEHLUNG["sek"] * 300
    return {
        "halloween": {
            "kicker": "halloween, 31 oct 2026",
            "titel": "the scariest kaspa number this month",
            "zahl": ganz(alt - neu), "diff": alt - neu,
            "label": "KAS less new supply every day from %s" % tag(e["datum"]),
            "vorher": ("before %s" % tag(e["datum"]), "%s KAS a day" % ganz(alt)),
            "nachher": ("from %s" % tag(e["datum"]), "%s KAS a day" % ganz(neu)),
            "quelle": "computed, emission schedule, %s" % tag(STAND),
        },
        "espresso": {
            "kicker": "kaspa in real life",
            "titel": "one espresso, about 5 minutes",
            "zahl": ganz(espresso), "roh": espresso,
            "label": "new kaspa blocks while you drink it",
            "vorher": ("counted %s" % tag(ZAEHLUNG["datum"]),
                       "%s blocks in %.1f s" % (ganz(ZAEHLUNG["bloecke"]), ZAEHLUNG["sek"])),
            "nachher": ("computed", "300 s, one espresso"),
            "quelle": "computed from our count of %s" % tag(ZAEHLUNG["datum"]),
        },
    }


# ------------------------------------------------------------ punkte aus daten

def in_kuerbis(x, y):
    """Kuerbis als Huelle aus vier Ellipsen, normiert auf -1..1, y nach unten."""
    for cx, rx in ((-0.42, 0.52), (-0.14, 0.50), (0.14, 0.50), (0.42, 0.52)):
        if ((x - cx) / rx) ** 2 + ((y - 0.12) / 0.78) ** 2 <= 1:
            # schmale Rillen zwischen den Rippen, damit die Form lesbar wird
            return not (y > -0.55 and any(abs(x - b) < 0.035 for b in (-0.28, 0.0, 0.28)))
    return -0.07 <= x <= 0.07 and -0.92 <= y <= -0.55


def in_tasse(x, y):
    """Tasse von der Seite: Koerper, Henkel als Ring, Untertasse."""
    koerper = -0.62 <= x <= 0.38 and -0.55 <= y <= 0.45 and not (y > 0.25 and abs(x + 0.12) > 0.5 - (y - 0.25))
    henkel = 0.11 <= (x - 0.48) ** 2 + (y + 0.05) ** 2 <= 0.07 + 0.11 and x > 0.38
    teller = ((x + 0.12) / 0.92) ** 2 + ((y - 0.58) / 0.1) ** 2 <= 1
    return koerper or henkel or teller


def punkte(form, anzahl, breite, hoehe):
    """Genau anzahl Punkte in der Form, auf einem gleichmaessigen Raster.
    Das Raster wird so fein gewaehlt, dass die Form mindestens anzahl Zellen
    hat, ueberzaehlige fallen gleichmaessig verteilt weg."""
    lo, hi = 1.0, 80.0
    for _ in range(40):
        s = (lo + hi) / 2
        n = len(_raster(form, s, breite, hoehe))
        if n >= anzahl:
            lo = s
        else:
            hi = s
    alle = _raster(form, lo, breite, hoehe)
    if len(alle) < anzahl:
        raise ValueError("form zu klein fuer %d punkte" % anzahl)
    # ueberzaehlige fallen fest zufaellig weg (Saat = anzahl), gleichmaessig
    # ausgeduennt nach Zeilen gaebe senkrechte Streifen
    import random
    weg = set(random.Random(anzahl).sample(range(len(alle)), len(alle) - anzahl))
    return [q for i, q in enumerate(alle) if i not in weg], lo


def _raster(form, s, breite, hoehe):
    aus = []
    ny, nx = int(hoehe / s), int(breite / s)
    for j in range(ny):
        for i in range(nx):
            x, y = (i + 0.5) * s, (j + 0.5) * s
            if form(2 * x / breite - 1, 2 * y / hoehe - 1):
                aus.append((x, y))
    return aus


def punkte_svg(form, anzahl, breite, hoehe, farbe):
    ps, s = punkte(form, anzahl, breite, hoehe)
    r = s * 0.32
    kreise = "".join("<circle cx='%.1f' cy='%.1f' r='%.2f'/>" % (x, y, r) for x, y in ps)
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>"
            "<g fill='%s'>%s</g></svg>" % (breite, hoehe, breite, hoehe, farbe, kreise)), len(ps)


# ------------------------------------------------------------ seiten

def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
*{box-sizing:border-box}
body{margin:0;width:1080px;height:1350px;overflow:hidden;position:relative;font-family:'IBM Plex Sans',sans-serif}
.t{position:absolute}
.kicker{font:500 34px/1.2 'IBM Plex Mono',monospace;letter-spacing:.04em}
.titel{font:900 72px/1.04 Archivo,sans-serif;letter-spacing:-.01em;text-wrap:balance}
.zahl{font:900 300px/.86 Archivo,sans-serif;letter-spacing:-.035em;white-space:nowrap}
.label{font:500 40px/1.25 'IBM Plex Sans',sans-serif;text-wrap:balance}
.paar{display:grid;grid-template-columns:1fr 1fr;column-gap:48px}
.paar .k{font:400 34px/1.3 'IBM Plex Mono',monospace}
.paar .v{font:600 38px/1.25 'IBM Plex Sans',sans-serif;margin-top:6px}
.quelle{font:400 34px/1.3 'IBM Plex Mono',monospace}
.linie{position:absolute;height:1px}
.fuss{position:absolute;left:50%;transform:translateX(-50%);bottom:72px;white-space:nowrap}
.foto{position:absolute;inset:0;background-size:cover;background-position:center}
"""


def _paar(inh, farbe_k):
    return ("<div class='paar'><div><div class='k' style='color:%s'>%s</div><div class='v'>%s</div></div>"
            "<div><div class='k' style='color:%s'>%s</div><div class='v'>%s</div></div></div>"
            % (farbe_k, esc(inh["vorher"][0]), esc(inh["vorher"][1]), farbe_k, esc(inh["nachher"][0]),
               esc(inh["nachher"][1])))


def seite(code, inh):
    import look_takt
    import wortmarke
    richtung = code[0]
    teile = []
    if richtung == "A":
        grund, tinte, leise, strich = (PAPIER, TINTE, "#3A4744", TINTE) if code == "A1" else \
            (TEAL, TEAL_DUNKEL, TEAL_DUNKEL, TEAL_DUNKEL)
        wm = wortmarke.css(groesse=36, sperrung=6, kaspa=tinte, pulse=tinte if code == "A2" else TINTE)
        teile += [
            "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (leise, esc(inh["kicker"])),
            "<div class='t kicker' style='right:72px;top:72px;color:%s'>%s</div>"
            % (leise, "emission schedule" if code == "A1" else "block count"),
            "<div class='linie' style='left:72px;right:72px;top:134px;background:%s'></div>" % strich,
            "<div class='t titel' data-rolle='titel' style='left:72px;right:200px;top:190px;color:%s'>%s</div>"
            % (tinte, esc(inh["titel"])),
            "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:450px;color:%s'>%s</div>"
            % (tinte, esc(inh["zahl"])),
            "<div class='t label' style='left:72px;right:200px;top:740px;color:%s'>%s</div>"
            % (tinte, esc(inh["label"])),
            "<div class='linie' style='left:72px;right:72px;top:900px;background:%s'></div>" % strich,
            "<div class='t' style='left:72px;right:72px;top:930px;color:%s'>%s</div>" % (tinte, _paar(inh, leise)),
            "<div class='linie' style='left:72px;right:72px;top:1074px;background:%s'></div>" % strich,
            "<div class='t quelle' style='left:72px;right:72px;top:1096px;color:%s'>%s</div>"
            % (leise, esc(inh["quelle"])),
        ]
        if code == "A1":
            # ein feiner Akzent in Teal, keine Schrift
            teile.append("<div class='linie' style='left:72px;width:160px;top:133px;height:4px;"
                         "background:%s'></div>" % TEAL)
    elif richtung == "B":
        foto = REPO / "graphics" / "fotos" / ("kuerbis-grok.jpg" if code == "B1" else "espresso-grok-2.jpg")
        url = "data:image/jpeg;base64," + base64.b64encode(foto.read_bytes()).decode()
        grund, tinte, leise = PAPIER, TINTE, TINTE
        wm = wortmarke.css(groesse=36, sperrung=6, kaspa=TINTE, pulse=TINTE)
        pos = "center 62%" if code == "B1" else "center 40%"
        teile.append("<div class='foto' style=\"background-image:url('%s');background-position:%s\"></div>"
                     % (url, pos))
        # Schleier aus Papierfarbe hinter den Textflaechen, oben und unten. Das
        # Motiv in der Mitte bleibt frei, die Schrift erreicht 7:1.
        oben = 640 if code == "B2" else 540
        teile.append("<div class='hg-schleier' style='position:absolute;left:0;right:0;top:0;height:%dpx;"
                     "background:linear-gradient(180deg,rgba(244,241,234,.86) 0%%,rgba(244,241,234,.78) 70%%,"
                     "rgba(244,241,234,0) 100%%)'></div>" % oben)
        teile.append("<div class='hg-schleier' style='position:absolute;left:0;right:0;bottom:0;height:300px;"
                     "background:linear-gradient(0deg,rgba(244,241,234,.9) 0%,rgba(244,241,234,.82) 62%,"
                     "rgba(244,241,234,0) 100%)'></div>")
        if code == "B1":
            teile += [
                "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (leise, esc(inh["kicker"])),
                "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:132px;"
                "font-size:220px;color:%s'>%s</div>" % (tinte, esc(inh["zahl"])),
                "<div class='t label' style='left:72px;right:240px;top:340px;color:%s'>%s</div>"
                % (tinte, esc(inh["label"])),
                "<div class='t quelle' style='left:72px;right:72px;top:1130px;color:%s'>%s</div>"
                % (leise, esc(inh["quelle"])),
            ]
        else:
            teile += [
                "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (leise, esc(inh["kicker"])),
                "<div class='t titel' data-rolle='titel' style='left:72px;right:72px;top:126px;font-size:64px;"
                "color:%s'>%s</div>" % (tinte, esc(inh["titel"])),
                "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:262px;"
                "font-size:220px;color:%s'>%s</div>" % (tinte, esc(inh["zahl"])),
                "<div class='t label' style='left:72px;right:72px;top:470px;color:%s'>%s</div>"
                % (tinte, esc(inh["label"])),
                "<div class='t quelle' style='left:72px;right:72px;top:1150px;color:%s'>%s</div>"
                % (leise, esc(inh["quelle"])),
            ]
    elif richtung == "D":
        grund = STEIN[code]
        leise = "#D6D0C6"
        wm = wortmarke.css(groesse=34, sperrung=5, kaspa="#D6D0C6", pulse=TEAL)
        if code == "D1":
            teile += [
                "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:520px;"
                "font-size:300px;color:%s'>%s</div>" % (TEAL, esc(inh["zahl"])),
                "<div class='t quelle' style='left:72px;right:72px;top:820px;color:%s'>%s</div>"
                % (leise, esc("KAS less new supply a day from 4 nov 2026, computed, emission schedule")),
            ]
        else:
            teile += [
                "<div class='t titel' data-rolle='titel' style='left:72px;right:72px;top:560px;font-size:76px;"
                "color:%s'>%s</div>" % (TEAL, esc("%s kaspa blocks in one espresso" % inh["zahl"])),
                "<div class='t quelle' style='left:72px;right:72px;top:820px;color:%s'>%s</div>"
                % (leise, esc("300 s, computed from our count of 27 oct 2026")),
            ]
    else:
        dunkel = code == "C1"
        grund, tinte, leise = (NACHT, "#F2F5F4", "#C9D2CF") if dunkel else (PAPIER, TINTE, "#3A4744")
        wm = wortmarke.css(groesse=36, sperrung=6, look="dunkel" if dunkel else "hell")
        if dunkel:
            anzahl, form, einheit = int(round(inh["diff"] / 100)), in_kuerbis, \
                "%s dots, each 100 KAS of the daily cut" % ganz(round(inh["diff"] / 100))
            fb, fh, top = 700, 470, 565
        else:
            anzahl, form, einheit = int(round(inh["roh"])), in_tasse, "%s dots, one for each block" % \
                ganz(round(inh["roh"]))
            fb, fh, top = 760, 470, 565
        svg, n = punkte_svg(form, anzahl, fb, fh, TEAL if dunkel else "#17B596")
        teile += [
            "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (leise, esc(inh["kicker"])),
            "<div class='t titel' data-rolle='titel' style='left:72px;right:72px;top:126px;font-size:64px;"
            "color:%s'>%s</div>" % (tinte, esc(inh["titel"])),
            "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:290px;font-size:200px;"
            "color:%s'>%s</div>" % (tinte, esc(inh["zahl"])),
            "<div class='t label' style='left:72px;right:72px;top:482px;font-size:36px;color:%s'>%s</div>"
            % (leise, esc(inh["label"])),
            "<div style='position:absolute;left:%dpx;top:%dpx'>%s</div>" % ((W - fb) // 2, top, svg),
            "<div class='t quelle' style='left:72px;right:72px;top:1052px;color:%s'>%s</div>"
            % (leise, esc(einheit)),
            "<div class='t quelle' style='left:72px;right:72px;top:1104px;color:%s'>%s</div>"
            % (leise, esc(inh["quelle"])),
        ]
    teile.append("<div class='fuss' data-rolle='fuss'>%s</div>" % wortmarke.html())
    css = look_takt.schriften_css() + CSS + "body{background:%s}" % grund + wm
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>"
            % (css, "".join(teile)))


FIT_JS = """() => {
  const aus = [];
  for (const z of document.querySelectorAll('[data-fit]')) {
    let g = parseFloat(getComputedStyle(z).fontSize), max = parseFloat(z.dataset.fit);
    while (z.scrollWidth > max && g > 200) { g -= 4; z.style.fontSize = g + 'px'; }
    if (z.scrollWidth > max) aus.push('zahl ' + z.textContent + ' zu breit');
  }
  const ts = [...document.querySelectorAll('.t')].map(e => [e.className, e.getBoundingClientRect()]);
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i][1], b = ts[j][1];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
      aus.push('ueberlappen ' + ts[i][0] + ' / ' + ts[j][0]);
  }
  const f = document.querySelector('.fuss').getBoundingClientRect();
  for (const [n, a] of ts) if (a.bottom > f.top - 16) aus.push(n + ' reicht an die fusszeile');
  return aus;
}"""

PLAN = [("A1", "halloween"), ("A2", "espresso"), ("B1", "halloween"), ("B2", "espresso"),
        ("C1", "halloween"), ("C2", "espresso"), ("D1", "halloween"), ("D2", "espresso")]


def rendern(ziel):
    from playwright.sync_api import sync_playwright
    import content_wache
    import tagesgrafik as tg
    d = daten()
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    fertig = []
    with sync_playwright() as pw:
        b = tg.chromium_start(pw)
        try:
            for code, was in PLAN:
                png = ziel / ("%s-%s.png" % (code, was))
                html = ziel / ("%s.html" % code)
                html.write_text(seite(code, d[was]), encoding="utf-8")
                pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
                try:
                    pg.goto(html.resolve().as_uri())
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(250)
                    f = pg.evaluate(FIT_JS)
                    if f:
                        raise SystemExit("%s, %s" % (code, "; ".join(f)))
                    pg.screenshot(path=str(png))
                    v = content_wache.pruefe_seite(pg, "instagram", None if code[0] == "B" else png)
                    if v:
                        raise SystemExit("%s, wache, %s" % (code, "; ".join(v)))
                finally:
                    pg.close()
                    html.unlink()
                fertig.append(png)
                print("ok", png.name)
        finally:
            b.close()
    return fertig


def musterblatt(pngs, ziel):
    from PIL import Image, ImageDraw, ImageFont
    s = 0.4
    w, h = int(W * s), int(H * s)
    rand, kopf = 24, 56
    blatt = Image.new("RGB", (4 * w + 5 * rand, 2 * (h + kopf) + 3 * rand), (24, 28, 30))
    try:
        schrift = ImageFont.truetype(str(REPO / "graphics" / "fonts" / "ibm-plex-mono-latin-500-normal.woff2"), 28)
    except Exception:                                     # noqa: BLE001
        schrift = ImageFont.load_default()
    zeichnen = ImageDraw.Draw(blatt)
    for i, p in enumerate(pngs):
        spalte, reihe = "ABCD".index(p.name[0]), int(p.name[1]) - 1
        x = rand + spalte * (w + rand)
        y = rand + reihe * (h + kopf + rand)
        zeichnen.text((x, y + 8), p.name[:2], fill=(242, 245, 244), font=schrift)
        blatt.paste(Image.open(p).resize((w, h), Image.LANCZOS), (x, y + kopf))
    blatt.save(ziel)
    return ziel


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    d = daten()
    ok("halloween aus dem emissionsplan", d["halloween"]["zahl"] == "99,903"
       and "1,779,989" in d["halloween"]["vorher"][1] and "1,680,086" in d["halloween"]["nachher"][1])
    ok("espresso aus der zaehlung vom 27.10.", d["espresso"]["zahl"] == "2,975")
    for form, n in ((in_kuerbis, 999), (in_tasse, 2975)):
        ps, _ = punkte(form, n, 800, 600)
        ok("genau %d punkte in der form" % n, len(ps) == n and len(set(ps)) == n)
    import content_wache
    for k, inh in d.items():
        for feld in ("kicker", "titel", "label", "quelle"):
            v = content_wache.text_verstoesse(inh[feld])
            ok("textregeln %s %s" % (k, feld), not v)
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ziel", default="docs/look-v2")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    pngs = rendern(a.ziel)
    print(musterblatt(pngs, Path(a.ziel) / "musterblatt.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
