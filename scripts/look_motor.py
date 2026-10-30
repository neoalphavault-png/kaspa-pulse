#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""look_motor.py, Look v2 und die Abwechslung (Ben, 28.10.2026).

Ben hat nach dem Musterblatt vom 28.10.2026 gewaehlt: A Editorial, B
Foto-Objekt, D Neutral und Gruen. C faellt raus, keine gezeichneten oder aus
Punkten gebauten Gegenstaende mehr (Ausnahme bleibt das Suchbild "Find the
1", ein eigenes Format). Die Regeln stehen in docs/grafik-regeln.md.

DIE LOOKS
    A-papier  Typografie auf warmem Papier, feine Linien, Teal nur als Strich
    A-teal    dieselbe Typografie auf Teal, Schrift dunkelgruen
    B-foto    ein Foto als Vollbild aus graphics/fotos/, Text auf ruhiger Flaeche
    D-dunkel  warmer dunkler Stein, die grosse Zahl in #49EACB
    D-hell    warmes Weiss oder heller Stein. Teal als Schrift erreicht dort
              nur 1.3:1, also ist die Zahl schwarz und #49EACB steht als
              Strich darunter (Bens Regel: Zahl in Teal nur mit genug
              Kontrast, sonst schwarz und eine Zeile in Teal)

DIE WORTMARKE wechselt nach dem Grund: schwarz, weiss oder normal (KASPA
weiss, PULSE #49EACB). Gemessen wird im fertigen Bild unter der Marke, mit
ausgeblendeter Marke, das untere 5-%-Quantil, mindestens 4.5:1. Passen
mehrere, nie zweimal hintereinander dieselbe (look_takt.logo_waehlen).

DIE ABWECHSLUNG haelt look_takt je Kanal in data/look-takt.json: nie
zweimal derselbe Look hintereinander auf Feed, Story, Karussell oder
Tagesgrafik.

DAS KARUSSELL "the week in numbers" (ab Sa 31.10.2026)
    Titel     am 31.10.2026 Halloween in B, sonst die erste Wochenzahl
    innen     die Wochenzahlen, A und D im Wechsel
    Schluss   die Newsletter-Folie mit dem Kurzlink kaspapulse.com/nl
              (utm_source instagram, utm_medium post, utm_campaign karussell)

Jede Seite laeuft durch content_wache im Profil feed (Groessen, Textregeln,
Kontrast 7:1). Beim Foto entfaellt nur die Pruefung des 60-px-Rands.

    python3 scripts/look_motor.py --probe --fuer 2026-10-31 --out out/look   # nur bauen
    python3 scripts/look_motor.py --selbsttest
"""
import argparse
import base64
import colorsys
import datetime as dt
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

W, H = 1080, 1350
PAPIER, TINTE, TEAL, TEAL_DUNKEL = "#F4F1EA", "#0B1A17", "#49EACB", "#062B24"
STEIN_DUNKEL, STEIN_HELL, STEIN_TEXT = "#1F1D1A", "#ECE7DE", "#D6D0C6"
LEISE_HELL = "#3A4744"
ORANGE = "#E2711D"                     # Kuerbis-Orange, nur als Strich und Licht
MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
LOOKS = ("A-papier", "A-teal", "B-foto", "D-dunkel", "D-hell")
LOGO = {"schwarz": (TINTE, TINTE), "weiss": ("#F2F5F4", "#F2F5F4"), "normal": ("#F2F5F4", TEAL)}
LOGO_MIN = 4.5
ORANGE_MAX = 0.05                      # hoechstens rund 5 % der flaeche
WEICH_RADIUS = 28                      # gauss-radius in px fuer fotos in look B (Ben, 30.10.2026)
KURZLINK_NL = "kaspapulse.com/nl"
HALLOWEEN = "2026-10-31"
FOTO_KUERBIS = REPO / "graphics" / "fotos" / "kuerbis-grok.jpg"


class Stopp(Exception):
    pass


def tag(d):
    d = dt.date.fromisoformat(str(d)[:10])
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def tag_kurz(d):
    return " ".join(tag(d).split()[:2])


def ganz(n):
    return "{:,}".format(int(round(n)))


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------ kontrast

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    f = []
    for c in rgb:
        c = c / 255.0
        f.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def kontrast(a, b):
    la, lb = sorted((_lum(a if isinstance(a, tuple) else _rgb(a)),
                     _lum(b if isinstance(b, tuple) else _rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def logo_kontraste(pixel, quantil=0.05):
    """{variante: kontrast} gegen die Pixel unter der Marke. Je Variante zaehlt
    die schwaechere ihrer beiden Farben, davon das untere 5-%-Quantil."""
    aus = {}
    for name, farben in LOGO.items():
        werte = sorted(min(kontrast(f, p) for f in farben) for p in pixel)
        aus[name] = werte[min(len(werte) - 1, int(len(werte) * quantil))] if werte else 0.0
    return aus


# ------------------------------------------------------------ zahlen

def halloween(stand):
    """Die Emissionsstufe am 4.11.2026 aus dem Emissionsplan, beim Bau frisch
    gerechnet. 99,903 = 1,779,989 minus 1,680,086, computed."""
    import startseite
    e = startseite.emission(dt.date.fromisoformat(str(stand)))
    alt, neu = e["vormonat"]["wert"], e["neu"]
    return {"kicker": "halloween, %s" % tag(HALLOWEEN), "zahl": ganz(alt - neu),
            "label": "KAS less new supply every day from %s" % tag(e["datum"]),
            "paar": (("before %s" % tag_kurz(e["datum"]), "%s KAS a day" % ganz(alt)),
                     ("from %s" % tag_kurz(e["datum"]), "%s KAS a day" % ganz(neu))),
            "quelle": "computed, emission schedule, %s" % tag(stand),
            "roh": {"alt": alt, "neu": neu, "datum": str(e["datum"])}}


def zahl_inhalt(s):
    """Eine Wochenzahl aus karussell.seiten_woche als Inhalt einer Seite."""
    vorher, jetzt = s["werte"]
    return {"kicker": "the week in numbers", "kicker_r": s["kopf"].lower(),
            "titel": s.get("haken") or "", "zahl": s["zahl"], "label": s["satz"],
            "paar": (("week to %s" % tag_kurz(s["woche_vorher"]), s["fmt"](vorher)),
                     ("week to %s" % tag_kurz(s["woche"]), s["fmt"](jetzt))),
            "quelle": "%s, week to %s" % (s["quelle"], tag(s["woche"]))}


def newsletter_inhalt():
    return {"kicker": "free newsletter", "titel": "the kaspa numbers that moved, every monday",
            "label": "dated and sourced, one short email a week.", "link": KURZLINK_NL}


# ------------------------------------------------------------ foto

def foto_orange(pfad, ziel=None):
    """Farbkorrektur am vorhandenen Foto (Ben, 28.10.2026): das kuehle
    Streiflicht an der Kuerbiskante wird warmes Orange. Nichts wird
    gezeichnet, nur der Farbton der Pixel im Teal- und Cyan-Bereich gedreht.
    Danach stark weichgezeichnet (WEICH_RADIUS).
    Gibt (jpeg-bytes, anteil umgefaerbter pixel) zurueck."""
    from PIL import Image
    im = Image.open(pfad).convert("RGB")
    px = im.load()
    n = 0
    oh = colorsys.rgb_to_hsv(*[c / 255.0 for c in _rgb(ORANGE)])[0]
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if 0.40 <= h <= 0.58 and s >= 0.22 and v >= 0.12:
                r2, g2, b2 = colorsys.hsv_to_rgb(oh, min(1.0, s * 1.15), v)
                px[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255))
                n += 1
    # stark weichgezeichnet (Ben, 30.10.2026, Regel Hintergrund vom 29.10.):
    # das foto ist flaeche, keine kante darf wie eine linie oder ein datenpunkt wirken
    from PIL import ImageFilter
    im = im.filter(ImageFilter.GaussianBlur(WEICH_RADIUS))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    if ziel:
        Path(ziel).write_bytes(buf.getvalue())
    return buf.getvalue(), n / float(im.width * im.height)


def orange_anteil(png):
    """Anteil der Flaeche im fertigen Bild, die Kuerbis-Orange traegt."""
    from PIL import Image
    im = Image.open(png).convert("RGB").resize((270, 338))
    oh = colorsys.rgb_to_hsv(*[c / 255.0 for c in _rgb(ORANGE)])[0]
    n = 0
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if abs(h - oh) < 0.05 and s >= 0.35 and v >= 0.25:
            n += 1
    return n / float(270 * 338)


# ------------------------------------------------------------ html

CSS = """
*{box-sizing:border-box}
body{margin:0;width:1080px;height:1350px;overflow:hidden;position:relative;font-family:'IBM Plex Sans',sans-serif}
.t{position:absolute}
.kicker{font:500 34px/1.2 'IBM Plex Mono',monospace;letter-spacing:.04em}
.titel{font:900 68px/1.04 Archivo,sans-serif;letter-spacing:-.01em;text-wrap:balance}
.zahl{font:900 260px/.86 Archivo,sans-serif;letter-spacing:-.035em;white-space:nowrap}
.label{font:500 40px/1.25 'IBM Plex Sans',sans-serif;text-wrap:balance}
.paar{display:grid;grid-template-columns:1fr 1fr;column-gap:48px}
.paar .k{font:400 34px/1.3 'IBM Plex Mono',monospace}
.paar .v{font:600 40px/1.25 'IBM Plex Sans',sans-serif;margin-top:6px}
.quelle{font:400 34px/1.3 'IBM Plex Mono',monospace}
.link{font:900 76px/1.05 Archivo,sans-serif;letter-spacing:-.01em;white-space:nowrap}
.linie{position:absolute;height:1px}
.fuss{position:absolute;left:50%;transform:translateX(-50%);bottom:72px;white-space:nowrap}
.foto{position:absolute;inset:0;background-size:cover;background-position:center}
"""


def _paar(paar, farbe_k):
    (k1, v1), (k2, v2) = paar
    return ("<div class='paar'><div><div class='k' style='color:%s'>%s</div><div class='v'>%s</div></div>"
            "<div><div class='k' style='color:%s'>%s</div><div class='v'>%s</div></div></div>"
            % (farbe_k, esc(k1), esc(v1), farbe_k, esc(k2), esc(v2)))


def seite_html(look, inh, foto_bytes=None):
    """Eine Seite 1080x1350 im Look. Die Wortmarke steht unten mittig, ihre
    Farbe setzt logo_setzen nach der Messung."""
    import look_takt
    import wortmarke
    teile = []
    if look in ("A-papier", "A-teal"):
        grund, tinte, leise, strich = ((PAPIER, TINTE, LEISE_HELL, TINTE) if look == "A-papier"
                                       else (TEAL, TEAL_DUNKEL, TEAL_DUNKEL, TEAL_DUNKEL))
        teile += ["<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (leise, esc(inh["kicker"]))]
        if inh.get("kicker_r"):
            teile.append("<div class='t kicker' style='right:72px;top:72px;color:%s'>%s</div>"
                         % (leise, esc(inh["kicker_r"])))
        teile.append("<div class='linie' style='left:72px;right:72px;top:134px;background:%s'></div>" % strich)
        if look == "A-papier":
            teile.append("<div class='linie' style='left:72px;width:160px;top:133px;height:4px;background:%s'></div>"
                         % TEAL)
        if inh.get("link"):
            teile += [
                "<div class='t titel' data-rolle='titel' style='left:72px;right:72px;top:200px;color:%s'>%s</div>"
                % (tinte, esc(inh["titel"])),
                "<div class='t label' style='left:72px;right:72px;top:470px;color:%s'>%s</div>"
                % (tinte, esc(inh["label"])),
                "<div class='linie' style='left:72px;right:72px;top:700px;background:%s'></div>" % strich,
                "<div class='t link' data-rolle='titel' data-fit='936' style='left:72px;top:740px;color:%s'>%s</div>"
                % (tinte, esc(inh["link"])),
                "<div class='linie' style='left:72px;width:220px;top:842px;height:6px;background:%s'></div>"
                % (TEAL if look == "A-papier" else TEAL_DUNKEL),
            ]
        else:
            top_zahl = 200
            if inh.get("titel"):
                teile.append("<div class='t titel' data-rolle='titel' style='left:72px;right:120px;top:180px;"
                             "color:%s'>%s</div>" % (tinte, esc(inh["titel"])))
                top_zahl = 400
            teile += [
                "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:%dpx;color:%s'>%s</div>"
                % (top_zahl, tinte, esc(inh["zahl"])),
                "<div class='t label' style='left:72px;right:120px;top:%dpx;color:%s'>%s</div>"
                % (top_zahl + 250, tinte, esc(inh["label"])),
                "<div class='linie' style='left:72px;right:72px;top:900px;background:%s'></div>" % strich,
                "<div class='t' style='left:72px;right:72px;top:930px;color:%s'>%s</div>"
                % (tinte, _paar(inh["paar"], leise)),
                "<div class='linie' style='left:72px;right:72px;top:1074px;background:%s'></div>" % strich,
                "<div class='t quelle' style='left:72px;right:72px;top:1096px;color:%s'>%s</div>"
                % (leise, esc(inh["quelle"])),
            ]
    elif look == "B-foto":
        grund, tinte = PAPIER, TINTE
        url = "data:image/jpeg;base64," + base64.b64encode(foto_bytes).decode()
        teile.append("<div class='foto' style=\"background-image:url('%s');background-position:center 62%%\"></div>"
                     % url)
        # Schleier aus Papierfarbe hinter den Textflaechen, das Motiv bleibt frei
        teile.append("<div class='hg-schleier' style='position:absolute;left:0;right:0;top:0;height:560px;"
                     "background:linear-gradient(180deg,rgba(244,241,234,.86) 0%,rgba(244,241,234,.78) 70%,"
                     "rgba(244,241,234,0) 100%)'></div>")
        teile.append("<div class='hg-schleier' style='position:absolute;left:0;right:0;bottom:0;height:300px;"
                     "background:linear-gradient(0deg,rgba(244,241,234,.9) 0%,rgba(244,241,234,.82) 62%,"
                     "rgba(244,241,234,0) 100%)'></div>")
        teile += [
            "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (tinte, esc(inh["kicker"])),
            # die kurze linie in kuerbis-orange unter der kopfzeile, ein strich, keine schrift
            "<div class='linie' style='left:72px;width:120px;top:128px;height:6px;background:%s'></div>" % ORANGE,
            "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:160px;font-size:220px;"
            "color:%s'>%s</div>" % (tinte, esc(inh["zahl"])),
            "<div class='t label' style='left:72px;right:240px;top:368px;color:%s'>%s</div>"
            % (tinte, esc(inh["label"])),
            "<div class='t quelle' style='left:72px;right:72px;top:1130px;color:%s'>%s</div>"
            % (tinte, esc(inh["quelle"])),
        ]
    elif look in ("D-dunkel", "D-hell"):
        dunkel = look == "D-dunkel"
        grund = STEIN_DUNKEL if dunkel else STEIN_HELL
        zahl_farbe = TEAL if dunkel else TINTE
        text = STEIN_TEXT if dunkel else LEISE_HELL
        if inh.get("link"):
            teile += [
                "<div class='t kicker' style='left:72px;top:440px;color:%s'>%s</div>" % (text, esc(inh["kicker"])),
                "<div class='t titel' data-rolle='titel' style='left:72px;right:72px;top:500px;color:%s'>%s</div>"
                % (TEAL if dunkel else TINTE, esc(inh["titel"])),
                "<div class='t link' data-rolle='titel' data-fit='936' style='left:72px;top:760px;color:%s'>%s</div>"
                % ("#F2F5F4" if dunkel else TINTE, esc(inh["link"])),
                "<div class='linie' style='left:72px;width:220px;top:862px;height:6px;background:%s'></div>" % TEAL,
                "<div class='t quelle' style='left:72px;right:72px;top:900px;color:%s'>%s</div>"
                % (text, esc(inh["label"])),
            ]
        else:
            teile += [
                "<div class='t kicker' style='left:72px;top:72px;color:%s'>%s</div>" % (text, esc(inh["kicker"])),
                "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:440px;color:%s'>%s</div>"
                % (zahl_farbe, esc(inh["zahl"])),
                "<div class='t label' style='left:72px;right:120px;top:710px;color:%s'>%s</div>"
                % ("#F2F5F4" if dunkel else TINTE, esc(inh["label"])),
                "<div class='t quelle' style='left:72px;right:72px;top:1000px;color:%s'>%s</div>"
                % (text, esc(inh["quelle"])),
            ]
            if inh.get("paar_d"):
                # das paar vorher und nachher auch im D-look (schalter-karussell, Ben 30.10.2026)
                teile.append("<div class='t' style='left:72px;right:72px;top:850px;color:%s'>%s</div>"
                             % ("#F2F5F4" if dunkel else TINTE, _paar(inh["paar"], text)))
            if not dunkel:
                # Teal als Strich unter der schwarzen Zahl, nie als Schrift auf hellem Grund
                teile.append("<div class='linie' style='left:72px;width:240px;top:682px;height:8px;"
                             "background:%s'></div>" % TEAL)
    else:
        raise Stopp("unbekannter look %r" % look)
    teile.append("<div class='fuss' data-rolle='fuss'>%s</div>" % wortmarke.html())
    css = (look_takt.schriften_css() + CSS + "body{background:%s}" % grund
           + wortmarke.css(groesse=36, sperrung=6, kaspa=TINTE, pulse=TINTE))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'>%s</body></html>" % (css, look, "".join(teile)))


FIT_JS = """() => {
  const aus = [];
  for (const z of document.querySelectorAll('[data-fit]')) {
    let g = parseFloat(getComputedStyle(z).fontSize), max = parseFloat(z.dataset.fit);
    const min = z.classList.contains('link') ? 64 : 200;
    while (z.scrollWidth > max && g > min) { g -= 4; z.style.fontSize = g + 'px'; }
    if (z.scrollWidth > max) aus.push('zahl ' + z.textContent + ' zu breit');
  }
  const ts = [...document.querySelectorAll('.t')].map(e => [e.className + ' ' + e.textContent.slice(0, 20),
                                                            e.getBoundingClientRect()]);
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i][1], b = ts[j][1];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
      aus.push('ueberlappen ' + ts[i][0] + ' / ' + ts[j][0]);
  }
  const f = document.querySelector('.fuss').getBoundingClientRect();
  for (const [n, a] of ts) if (a.bottom > f.top - 16) aus.push(n + ' reicht an die fusszeile');
  return aus;
}"""


def logo_messen(pg):
    """Die Pixel unter der Wortmarke, mit ausgeblendeter Marke."""
    from PIL import Image
    pg.add_style_tag(content=".wm{visibility:hidden !important}")
    r = pg.evaluate("() => { const b = document.querySelector('.wm').getBoundingClientRect();"
                    " return [b.left, b.top, b.right, b.bottom]; }")
    bild = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    box = tuple(int(round(v)) for v in r)
    return list(bild.crop(box).resize((120, 12)).getdata())


def logo_setzen(pg, variante):
    k, p = LOGO[variante]
    pg.add_style_tag(content=".wm{visibility:visible !important;color:%s !important}"
                             ".wm b{color:%s !important}" % (k, p))


def seite_rendern(b, look, inh, png, speicher, kanal, foto_bytes=None, ohne_rand=False):
    """Rendert eine Seite, waehlt die Wortmarke nach Messung, prueft mit
    content_wache. Gibt die gewaehlte Logo-Variante und die Kontraste zurueck."""
    import content_wache
    import look_takt
    html = Path(png).with_suffix(".html")
    html.write_text(seite_html(look, inh, foto_bytes), encoding="utf-8")
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    try:
        pg.goto(html.resolve().as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        f = pg.evaluate(FIT_JS)
        if f:
            raise Stopp("%s, %s" % (look, "; ".join(f)))
        werte = logo_kontraste(logo_messen(pg))
        gueltig = [v for v, k in werte.items() if k >= LOGO_MIN]
        variante = look_takt.logo_waehlen(speicher, kanal, gueltig)
        logo_setzen(pg, variante)
        pg.wait_for_timeout(50)
        pg.screenshot(path=str(png))
        v = content_wache.pruefe_seite(pg, "instagram", None if ohne_rand else png)
        if v:
            raise Stopp("%s, wache, %s" % (look, "; ".join(v)))
    finally:
        pg.close()
        html.unlink()
    return variante, werte


# ------------------------------------------------------------ karussell

# Dieselbe Zahl hoechstens einmal pro Tag auf Instagram (Ben, 28.10.2026).
# Welche Wochenzahl eine Form der Tagesgrafik traegt.
FORM_ZAHLEN = {1: ("holders", "hashrate"), 8: ("hashrate",), 9: ("holders",), 11: ("dormant",)}


def tagesgrafik_zahlen(fuer, log=None):
    """Die Wochenzahlen, die die Tagesgrafik am selben Tag schon zeigt."""
    if log is None:
        try:
            log = json.loads((REPO / "data" / "tagesgrafik-log.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()
    aus = set()
    for e in log.get("laeufe", []):
        if e.get("datum") == str(fuer):
            aus.update(FORM_ZAHLEN.get(e.get("form"), ()))
    return aus


def plan_woche(fuer, ss, stand, speicher, merken=True, schon=None):
    """Die Seiten des Wochen-Karussells: [(look, inhalt, art)]. Der Look der
    Titelseite laeuft durch die Rotation des Kanals karussell."""
    import look_takt
    zahlen = [x for x in ss if x["art"] in ("haken", "zahl")]
    schon = tagesgrafik_zahlen(fuer) if schon is None else set(schon)
    zahlen = [x for x in zahlen if x.get("id") not in schon] or zahlen[:0]
    if not zahlen:
        raise Stopp("alle wochenzahlen stehen heute schon in der tagesgrafik (%s)" % ", ".join(sorted(schon)))
    plan = []
    if str(fuer) == HALLOWEEN:
        titel = look_takt.richtung_faellig(speicher, "karussell", fuer, "woche", wunsch="B")
        if titel != "B":
            raise Stopp("halloween braucht look B, die rotation gibt %s (zuletzt B auf karussell)" % titel)
        plan.append(("B-foto", halloween(stand), "titel"))
        innen = ("A-papier", "D-dunkel", "A-teal")
    else:
        titel = look_takt.richtung_faellig(speicher, "karussell", fuer, "woche", erlaubt=("A", "D"))
        innen = ("A-papier", "D-dunkel", "A-teal") if titel == "A" else ("D-dunkel", "A-papier", "D-hell")
    for i, z in enumerate(zahlen):
        plan.append((innen[i % len(innen)], zahl_inhalt(z), "zahl"))
    plan.append(("D-hell" if plan[-1][0].startswith("A") else "A-papier", newsletter_inhalt(), "newsletter"))
    if merken:
        look_takt.richtung_merken(speicher, "karussell", fuer, "woche",
                                  erlaubt=None if str(fuer) == HALLOWEEN else ("A", "D"),
                                  wunsch="B" if str(fuer) == HALLOWEEN else None)
    return plan


def karussell_woche(fuer, ss, out, speicher=None, stand=None, merken=False):
    """Baut alle Seiten als PNG 1080x1350. Gibt (pngs, info) zurueck."""
    import look_takt
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    stand = stand or dt.datetime.now(dt.timezone.utc).date().isoformat()
    sp = speicher if speicher is not None else look_takt.lesen()
    if not merken:
        sp = json.loads(json.dumps(sp))         # eine probe merkt nichts
    plan = plan_woche(fuer, ss, stand, sp, merken=True)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pngs, info = [], []
    foto = None
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for i, (look, inh, art) in enumerate(plan, 1):
                png = out / ("karussell-woche-%s-%d-%s.png" % (fuer, i, look))
                if look == "B-foto" and foto is None:
                    foto, anteil_foto = foto_orange(FOTO_KUERBIS)
                variante, werte = seite_rendern(b, look, inh, png, sp, "karussell", foto if look == "B-foto" else None,
                                                ohne_rand=look == "B-foto")
                e = {"seite": i, "look": look, "art": art, "logo": variante,
                     "logo_kontrast": {k: round(v, 2) for k, v in werte.items()}}
                if look == "B-foto":
                    e["orange_anteil"] = round(orange_anteil(png), 4)
                    if e["orange_anteil"] > ORANGE_MAX:
                        raise Stopp("orange auf %.1f %% der flaeche, erlaubt rund 5 %%" % (100 * e["orange_anteil"]))
                pngs.append(png)
                info.append(e)
        finally:
            b.close()
    if merken and speicher is not None:
        speicher.clear()
        speicher.update(sp)
    return pngs, {"seiten": info, "halloween": plan[0][1].get("roh") if plan[0][2] == "titel" else None}


def texte(plan):
    """Alle sichtbaren Texte eines Plans, fuer die Textwache."""
    aus = []
    for _, inh, _ in plan:
        for k in ("kicker", "kicker_r", "titel", "zahl", "label", "quelle", "link"):
            if inh.get(k):
                aus.append(inh[k])
        for kk, vv in inh.get("paar") or ():
            aus += [kk, vv]
    return aus


# ------------------------------------------------------------ schalter

# Das Schalter-Karussell "off / on" zum Reward Cut vom 4.11.2026 (Ben,
# 29.10.2026, Fenster nach Variante a am 30.10.2026). Post Fr 6.11. 11:00,
# am 4.11. laeuft der Collab mit Kasforge. Hashrate als Tagesmittel (UTC) aus
# der kaspa rest api, die zwei Tage vor dem Cut gegen den ersten vollen Tag
# danach. Der Tag des Cuts zaehlt nicht, er ist halb vorher, halb nachher.
SCHALTER_TAG = "2026-11-06"
SCHALTER_CUT = "2026-11-04"
SCHALTER_VOR = ("2026-11-02", "2026-11-03")
SCHALTER_NACH = ("2026-11-05",)


def schalter_zahlen(heute=None, tage=None, teiltag=False):
    """Hashrate vorher und nachher in PH/s, die Belohnung vor und nach dem
    Cut aus dem Emissionsplan. Ein Tag, der in UTC noch laeuft, zaehlt nur
    in einer Probe (teiltag), die Seiten sagen das nicht, die Meldung schon."""
    import statistics
    import tagesgrafik as tg
    heute = str(heute or dt.datetime.now(dt.timezone.utc).date())
    tage = tg.m_hashrate_tage() if tage is None else tage
    offen = [d for d in SCHALTER_VOR + SCHALTER_NACH if d >= heute]
    if offen and not teiltag:
        raise Stopp("hashrate, %s ist in utc noch nicht vorbei" % ", ".join(offen))
    fehlt = [d for d in SCHALTER_VOR + SCHALTER_NACH if d not in tage]
    if fehlt:
        raise Stopp("hashrate, kein tagesmittel fuer %s" % ", ".join(fehlt))
    nod = tg.reward_plan()
    mittag = dt.datetime.combine(dt.date.fromisoformat(SCHALTER_VOR[-1]), dt.time(12),
                                 dt.timezone.utc).timestamp()
    alt, neu, cut_ts = nod.reward_state(mittag)
    cut = dt.datetime.fromtimestamp(cut_ts, dt.timezone.utc)
    if cut.date().isoformat() != SCHALTER_CUT:
        raise Stopp("der cut faellt auf %s, nicht auf %s" % (cut.date(), SCHALTER_CUT))
    vor = statistics.mean(tage[d] for d in SCHALTER_VOR) / 1000.0
    nach = statistics.mean(tage[d] for d in SCHALTER_NACH) / 1000.0
    return {"vor": vor, "nach": nach, "aenderung": (nach / vor - 1) * 100,
            "alt": "%.2f" % alt, "neu": "%.2f" % neu, "cut": cut.isoformat(), "teiltag": offen}


def _hr(x):
    return "%s PH/s" % ganz(round(x))


def schalter_seiten(z):
    """Die Seiten als Texte fuer die Wachen (karussell.seiten_texte) und als
    Inhalt fuer seite_html. art haken und zahl wie im Wochen-Karussell."""
    cut = tag(SCHALTER_CUT)
    vor_txt = "2 and 3 nov"
    nach_txt = tag_kurz(SCHALTER_NACH[0])
    a = z["aenderung"]
    richtung = ("%.1f%% higher" % a) if a > 0.05 else (("%.1f%% lower" % -a) if a < -0.05 else "about the same")
    vergleich = "%s than on %s" % (richtung, vor_txt) if richtung != "about the same" else \
        "about the same as on %s" % vor_txt
    titel = {"kicker": "off / on", "kicker_r": "reward cut, %s" % cut,
             "zahl": z["neu"], "label": "KAS per block from %s, before it was %s" % (cut, z["alt"]),
             "paar": (("until %s" % tag_kurz(SCHALTER_CUT), "%s KAS a block" % z["alt"]),
                      ("from %s" % tag_kurz(SCHALTER_CUT), "%s KAS a block" % z["neu"])),
             "quelle": "computed, emission schedule, cut on %s, %s utc"
                       % (cut, dt.datetime.fromisoformat(z["cut"]).strftime("%H:%M")),
             "paar_d": True}
    hash_ = {"kicker": "off / on", "kicker_r": "network hashrate",
             "zahl": ganz(round(z["nach"])),
             "label": "PH/s on %s, the first full day after the cut, %s" % (tag(SCHALTER_NACH[0]), vergleich),
             "paar": ((vor_txt, _hr(z["vor"])), (nach_txt, _hr(z["nach"]))),
             "quelle": "source kaspa rest api, daily means computed by kaspa pulse, %s" % tag(SCHALTER_NACH[-1]),
             "paar_d": True}
    return [
        {"art": "haken", "id": "reward", "kopf": "BLOCK REWARD", "zahl": titel["zahl"], "satz": titel["label"],
         "quelle": titel["quelle"], "inhalt": titel},
        {"art": "zahl", "id": "hashrate", "kopf": "HASHRATE", "zahl": hash_["zahl"], "satz": hash_["label"],
         "quelle": hash_["quelle"], "inhalt": hash_},
    ]


def schalter_caption(z, ss):
    import karussell
    return karussell.caption(
        "%s KAS per block from %s, down from %s" % (z["neu"], tag(SCHALTER_CUT), z["alt"]),
        "network hashrate %s on %s against %s on 2 and 3 nov 2026, source kaspa rest api, "
        "the reward computed from the emission schedule" % (_hr(z["nach"]), tag_kurz(SCHALTER_NACH[0]),
                                                            _hr(z["vor"])),
        "which number do you watch after a reward cut?")


def plan_schalter(fuer, ss, speicher, merken=True):
    """Titel Belohnung, dann Hashrate, dann Newsletter. Der Titel-Look laeuft
    durch die Rotation des Kanals karussell, A oder D, nie zweimal derselbe."""
    import look_takt
    titel = look_takt.richtung_faellig(speicher, "karussell", fuer, "schalter", erlaubt=("A", "D"))
    looks = ("A-papier", "D-dunkel") if titel == "A" else ("D-dunkel", "A-papier")
    plan = [(looks[0], ss[0]["inhalt"], "titel"), (looks[1], ss[1]["inhalt"], "zahl")]
    plan.append(("D-hell" if plan[-1][0].startswith("A") else "A-papier", newsletter_inhalt(), "newsletter"))
    if merken:
        look_takt.richtung_merken(speicher, "karussell", fuer, "schalter", erlaubt=("A", "D"))
    return plan


def karussell_schalter(fuer, ss, out, speicher=None, merken=False):
    """Baut die drei Seiten als PNG 1080x1350. Gibt (pngs, info) zurueck."""
    import look_takt
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    sp = speicher if speicher is not None else look_takt.lesen()
    if not merken:
        sp = json.loads(json.dumps(sp))
    plan = plan_schalter(fuer, ss, sp, merken=True)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pngs, info = [], []
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for i, (look, inh, art) in enumerate(plan, 1):
                png = out / ("karussell-schalter-%s-%d-%s.png" % (fuer, i, look))
                variante, werte = seite_rendern(b, look, inh, png, sp, "karussell")
                pngs.append(png)
                info.append({"seite": i, "look": look, "art": art, "logo": variante,
                             "logo_kontrast": {k: round(v, 2) for k, v in werte.items()}})
        finally:
            b.close()
    if merken and speicher is not None:
        speicher.clear()
        speicher.update(sp)
    return pngs, {"seiten": info}


# ------------------------------------------------------------ selbsttest

def selbsttest():
    import content_wache
    import look_takt
    f = []

    def ok(name, bed, *mehr):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, (" " + repr(mehr)) if mehr and not bed else ""))
        if not bed:
            f.append(name)

    h = halloween("2026-10-31")
    ok("halloween 99,903 = 1,779,989 minus 1,680,086, computed",
       h["zahl"] == "99,903" and h["roh"]["alt"] == 1779989 and h["roh"]["neu"] == 1680086
       and h["quelle"].startswith("computed, emission schedule"))
    ok("halloween kopfzeile", h["kicker"] == "halloween, 31 oct 2026")
    ok("gewaehlt sind A, B und D, C faellt raus", look_takt.GEWAEHLT == ("A", "B", "D"))
    # logo-regel
    hell = [_rgb(PAPIER)] * 50
    dunkel = [_rgb(STEIN_DUNKEL)] * 50
    teal = [_rgb(TEAL)] * 50
    kh, kd, kt = logo_kontraste(hell), logo_kontraste(dunkel), logo_kontraste(teal)
    ok("heller grund, nur schwarz", [v for v, k in kh.items() if k >= LOGO_MIN] == ["schwarz"], kh)
    ok("teal-grund, nur schwarz", [v for v, k in kt.items() if k >= LOGO_MIN] == ["schwarz"], kt)
    ok("dunkler grund, weiss und normal", sorted(v for v, k in kd.items() if k >= LOGO_MIN) == ["normal", "weiss"],
       kd)
    sp = {}
    a1 = look_takt.logo_waehlen(sp, "karussell", ["weiss", "normal"])
    a2 = look_takt.logo_waehlen(sp, "karussell", ["weiss", "normal"])
    ok("passen mehrere, nie zweimal dieselbe hintereinander", a1 != a2, a1, a2)
    ok("passt nur eine, bleibt es die", look_takt.logo_waehlen(sp, "karussell", ["schwarz"]) == "schwarz"
       and look_takt.logo_waehlen(sp, "karussell", ["schwarz"]) == "schwarz")
    # rotation je kanal
    sp = {}
    folge = [look_takt.richtung_merken(sp, "karussell", "2026-11-%02d" % (d + 1), "woche") for d in range(6)]
    ok("karussell nie zweimal derselbe look hintereinander", all(a != b for a, b in zip(folge, folge[1:])), folge)
    ok("rotation nur zwischen A, B und D", set(folge) == {"A", "B", "D"}, folge)
    look_takt.richtung_merken(sp, "tagesgrafik", "2026-11-07", "tagesgrafik")
    ok("kanaele getrennt gefuehrt", "richtung/tagesgrafik" in sp["kanaele"] and "richtung/karussell" in sp["kanaele"])
    sp2 = {"kanaele": {"richtung/karussell": [{"datum": "2026-10-24", "serie": "woche", "richtung": "A"}]}}
    ok("wunsch B fuer halloween, wenn zuletzt nicht B",
       look_takt.richtung_faellig(sp2, "karussell", HALLOWEEN, "woche", wunsch="B") == "B")
    sp2["kanaele"]["richtung/karussell"][-1]["richtung"] = "B"
    ok("wunsch weicht, wenn zuletzt derselbe look",
       look_takt.richtung_faellig(sp2, "karussell", HALLOWEEN, "woche", wunsch="B") != "B")
    # plan und texte
    ss = [{"art": "haken", "id": "holders", "kopf": "ADDRESSES", "zahl": "295,726", "haken": "more addresses hold at least 100 KAS than a week ago",
           "satz": "addresses with at least 100 KAS, +1,122 in a week", "quelle": "source kaspalytics address counts",
           "werte": (803742, 808128), "fmt": ganz, "woche": "2026-10-24", "woche_vorher": "2026-10-17"},
          {"art": "zahl", "id": "dormant", "kopf": "SLEEPING COINS", "zahl": "51.2%",
           "satz": "of all KAS has not moved in a year", "quelle": "source kaspalytics",
           "werte": (51.1, 51.2), "fmt": lambda v: "%.2f%%" % v, "woche": "2026-10-24", "woche_vorher": "2026-10-17"},
          {"art": "abbinder"}]
    sp = {}
    plan = plan_woche(HALLOWEEN, ss, "2026-10-31", sp, merken=False, schon=())
    ok("halloween-titel in B, innen A und D im wechsel, schluss newsletter",
       [x[0] for x in plan] == ["B-foto", "A-papier", "D-dunkel", "A-papier"] and plan[-1][2] == "newsletter",
       [x[0] for x in plan])
    ok("tagesgrafik form 11 am selben tag, schlafende coins fallen raus",
       tagesgrafik_zahlen(HALLOWEEN, {"laeufe": [{"datum": HALLOWEEN, "form": 11}]}) == {"dormant"}
       and [x[1].get("zahl") for x in plan_woche(HALLOWEEN, ss, HALLOWEEN, {}, merken=False, schon={"dormant"})]
       == ["99,903", "295,726", None])
    ok("anderer tag zaehlt nicht", tagesgrafik_zahlen(HALLOWEEN, {"laeufe": [{"datum": "2026-10-30", "form": 9}]})
       == set())
    ok("keine zwei gleichen looks hintereinander im karussell",
       all(a[0] != b[0] for a, b in zip(plan, plan[1:])))
    v = [x for t in texte(plan) for x in content_wache.text_verstoesse(t)]
    ok("alle texte bestehen die textregeln", not v, v)
    ok("newsletter mit kurzlink, kein engagement-koeder",
       plan[-1][1]["link"] == "kaspapulse.com/nl"
       and not any(w in " ".join(texte([plan[-1]])).lower() for w in ("comment", "like", "share", "follow", "tag a")))
    alt = ("halloween-2026-10-31-01", "how fast is kaspa")
    ok("die alten bilder kommen in keinem plan vor", not any(a in json.dumps(texte(plan)) for a in alt))
    # kontrast der festen farben
    ok("schrift auf papier, teal, stein dunkel und hell ab 7:1",
       kontrast(TINTE, PAPIER) >= 7 and kontrast(TEAL_DUNKEL, TEAL) >= 7 and kontrast(TEAL, STEIN_DUNKEL) >= 7
       and kontrast(STEIN_TEXT, STEIN_DUNKEL) >= 7 and kontrast(LEISE_HELL, STEIN_HELL) >= 7
       and kontrast(TINTE, STEIN_HELL) >= 7)
    ok("teal als schrift auf hellem stein waere unter 7:1, deshalb nur strich", kontrast(TEAL, STEIN_HELL) < 7)
    # foto in look B stark weichgezeichnet (Ben, 30.10.2026)
    from PIL import Image, ImageFilter
    roh = Image.open(FOTO_KUERBIS).convert("L")
    weich = Image.open(io.BytesIO(foto_orange(FOTO_KUERBIS)[0])).convert("L")

    def kanten(im):
        # staerkste kanten, das 99,9-%-quantil des kantenbilds in voller aufloesung
        e = im.filter(ImageFilter.FIND_EDGES)
        h = e.crop((40, 40, e.width - 40, e.height - 40)).histogram()      # ohne den bildrand
        rest = 0.001 * im.width * im.height
        for wert in range(255, -1, -1):
            rest -= h[wert]
            if rest <= 0:
                return wert
        return 0
    ok("kuerbis-foto weichgezeichnet, staerkste kanten unter einem fuenftel", kanten(weich) < kanten(roh) / 5,
       round(kanten(roh), 2), round(kanten(weich), 2))
    # schalter-karussell zum reward cut (Ben, 29.10. und 30.10.2026)
    tage = {"2026-11-02": 380000.0, "2026-11-03": 384000.0, "2026-11-04": 383000.0, "2026-11-05": 390000.0}
    z = schalter_zahlen("2026-11-06", tage)
    ok("schalter, 2 und 3 nov gegen 5 nov, mittel in PH/s", round(z["vor"]) == 382 and round(z["nach"]) == 390
       and round(z["aenderung"], 1) == 2.1, z)
    ok("schalter, belohnung 2.06 auf 1.94 computed, cut am 4.11.", z["alt"] == "2.06" and z["neu"] == "1.94"
       and z["cut"].startswith("2026-11-04"), z)
    try:
        schalter_zahlen("2026-11-05", tage)
        ok("schalter, laufender utc-tag stoppt", False)
    except Stopp:
        ok("schalter, laufender utc-tag stoppt", True)
    ok("schalter, probe darf den laufenden tag nehmen",
       schalter_zahlen("2026-11-05", tage, teiltag=True)["teiltag"] == ["2026-11-05"])
    try:
        schalter_zahlen("2026-11-06", {k: v for k, v in tage.items() if k != "2026-11-02"})
        ok("schalter, fehlender tag stoppt", False)
    except Stopp:
        ok("schalter, fehlender tag stoppt", True)
    import karussell
    sss = schalter_seiten(z)
    cap = schalter_caption(z, sss)
    tx = karussell.seiten_texte(sss) + texte([(None, x["inhalt"], None) for x in sss])
    ok("schalter, texte bestehen die wachen", karussell.text_pruefen(tx) == [], karussell.text_pruefen(tx))
    ok("schalter, caption besteht die wachen", karussell.caption_pruefen(cap) == [], karussell.caption_pruefen(cap))
    ok("schalter, kein kausalsatz", not any(w in " ".join(tx + [cap]).lower()
                                             for w in ("because", "caused", "due to", "miners left")))
    ok("schalter, seite 2 nennt 2 and 3 nov und 5 nov", "2 and 3 nov" in " ".join(tx) and "5 nov" in " ".join(tx))
    for lt, erwartet in (("A", ["A-papier", "D-dunkel", "A-papier"]), ("D", ["D-dunkel", "A-papier", "D-hell"])):
        spp = {"kanaele": {"richtung/karussell": [{"datum": "2026-10-31", "serie": "woche",
                                                    "richtung": "D" if lt == "A" else "A"}]}}
        pl = plan_schalter(SCHALTER_TAG, sss, spp, merken=False)
        ok("schalter, titel %s, nie zwei gleiche looks hintereinander" % lt,
           [x[0] for x in pl] == erwartet and all(a[0] != b[0] for a, b in zip(pl, pl[1:])), [x[0] for x in pl])
    ok("schalter, nur am 6.11.", SCHALTER_TAG == "2026-11-06" and karussell.POSTZEIT["schalter"] == (4, "11:00"))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuer", default=HALLOWEEN)
    ap.add_argument("--out", default="out/look")
    ap.add_argument("--probe", action="store_true", help="bauen ohne den takt zu merken")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    import karussell
    ss, _ = karussell.vorbereiten("woche", a.fuer)
    pngs, info = karussell_woche(a.fuer, ss, a.out, merken=not a.probe)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    for p in pngs:
        print(p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stopp as exc:
        print("STOPP %s" % exc)
        sys.exit(1)
