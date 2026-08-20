#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grafik_check.py, der waechter fuer grafiken.

Warum es das gibt. Am 19.08.2026 ist eine grafik rausgegangen, deren
erklaertext bei 28 pixeln stand. Im feed wird ein 1080 breites bild bei
etwa 390 pixeln angezeigt, der massstab ist also 0.36, und aus 28 werden
zehn. Zehn pixel liest niemand ohne anzutippen, und wer antippt, leitet
nicht weiter. Die regel dazu stand zu dem zeitpunkt bereits in der
doktrin, abschnitt 11. Sie wurde trotzdem verletzt, weil niemand die
verkleinerte fassung wirklich angesehen hat.

Genau dagegen hilft ein waechter, und nur dagegen. Er prueft, was
messbar ist. Er prueft nicht, ob die grafik gut ist.

WAS ER FAENGT
  zu kleine schrift, gemessen an der gerenderten schriftgroesse
  ueberlauf ueber die bildhoehe hinaus
  abgeschnittene elemente innerhalb der seite
  fehlende marke oder domain im bild
  verbotene zeichen im sichtbaren text
  falsches seitenverhaeltnis

Der dritte punkt kam am 20.08.2026 dazu. Eine FOLLOW THE MONEY fassung kam
durch, obwohl die grosse zahl mittendrin abgeschnitten war. Grund war
flexbox. Der kasten mit der zahl wurde gestaucht statt ueberzulaufen, die
seitenhoehe blieb deshalb korrekt und die alte pruefung sah nichts. Wer nur
die gesamthoehe misst, faengt genau die haelfte der ueberlauffehler.

WAS ER NICHT FAENGT
  ob die grafik genau eine aussage macht
  ob sie ohne begleittext verstaendlich ist
  ob jemand sie an einen freund schicken wuerde
  ob die zahl stimmt

Diese vier stehen in der doktrin und bleiben urteilssache. Ein gruener
lauf heisst also nicht, dass die grafik gut ist. Er heisst nur, dass sie
nicht aus einem der fuenf mechanischen gruende scheitert. Der waechter
schreibt zusaetzlich immer eine feed-vorschau bei 390 pixeln und nennt
ihren pfad. Diese vorschau ist anzusehen, nicht zu messen.

AUFRUF
  python3 scripts/grafik_check.py pulse/tps2.html
  python3 scripts/grafik_check.py pulse/tps2.html --breite 1080 --hoehe 1350
  python3 scripts/grafik_check.py --selbsttest
"""

import argparse
import os
import re
import sys

# --- grenzwerte, aus content-doktrin.md abschnitt 11 -----------------

MIN_ALLGEMEIN = 40      # alles, was gelesen werden muss
MIN_KLEIN = 30          # einheit, datum, absender. duerfen kleiner sein
FEED_BREITE = 390       # so breit ist das bild im feed auf dem telefon

# elemente, die bei MIN_KLEIN gemessen werden statt bei MIN_ALLGEMEIN.
# bewusst kurz gehalten. wer hier etwas eintraegt, sagt damit, dass der
# text nicht gelesen werden muss.
KLEIN_ERLAUBT = ".iss, .foot, .foot *, .brand, .brand *, .num .u, .u, .src, .quelle"

VERBOTEN = ["\u2014", "\u2013", " - ", ":", "\u2192"]
# zeitstempel wie 06:25 und urls sind ausgenommen
AUSNAHME = re.compile(r"\d:\d|https?://|\w+\.(com|io|org|app|stream|fyi)")

MARKEN = ["kaspapulse.com", "pulsehawk.io", "alphavault", "pulse hawk"]


def messen(html_pfad, breite, hoehe):
    """rendert die datei und liefert die messwerte."""
    from playwright.sync_api import sync_playwright
    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    js = """() => {
      const klein = new Set(Array.from(document.querySelectorAll(KLEIN)));
      const out = [];
      document.querySelectorAll("*").forEach(e => {
        if (e.children.length) return;
        const t = (e.textContent || "").trim();
        if (!t) return;
        const s = getComputedStyle(e);
        if (s.display === "none" || s.visibility === "hidden") return;
        if (parseFloat(s.opacity) === 0) return;
        out.push({txt: t.slice(0, 60), px: parseFloat(s.fontSize),
                  klein: klein.has(e)});
      });
      // gestauchte kaesten. flexbox schrumpft ein kind, statt die seite
      // wachsen zu lassen, der inhalt wird dabei abgeschnitten. das ist an
      // der gesamthoehe nicht zu sehen, nur am einzelnen element.
      const schnitt = [];
      document.querySelectorAll("body *").forEach(e => {
        const s = getComputedStyle(e);
        if (s.display === "none") return;
        // nur wo wirklich abgeschnitten wird. bei overflow visible ragt der
        // inhalt heraus und bleibt sichtbar, das ist kein fehler. ein paar
        // pixel unterschied entstehen bei grossen schriften durch
        // unterlaengen, deshalb die schwelle.
        if (s.overflowY === "visible") return;
        const fehl = e.scrollHeight - e.clientHeight;
        if (fehl > 6 && e.clientHeight > 0) {
          schnitt.push({txt: (e.textContent || "").trim().slice(0, 40),
                        tag: e.className || e.tagName, fehl: fehl});
        }
      });
      return {texte: out, hoehe: document.body.scrollHeight,
              schnitt: schnitt, sicht: document.body.innerText};
    }"""
    js = js.replace("KLEIN", repr(KLEIN_ERLAUBT))
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe)
        p = b.new_page(viewport={"width": breite, "height": hoehe})
        p.goto("file://" + os.path.abspath(html_pfad), wait_until="load")
        p.wait_for_timeout(400)
        daten = p.evaluate(js)
        png = os.path.splitext(html_pfad)[0] + ".png"
        p.screenshot(path=png)
        b.close()
    daten["png"] = png
    return daten


def vorschau(png, breite, hoehe):
    """schreibt die feed-fassung. die ist anzusehen, nicht zu messen."""
    from PIL import Image
    im = Image.open(png)
    h = round(FEED_BREITE * hoehe / breite)
    ziel = os.path.splitext(png)[0] + "-feed.png"
    im.resize((FEED_BREITE, h), Image.LANCZOS).save(ziel)
    return ziel


def zeichen_pruefen(text):
    fehler = []
    for zeile in text.splitlines():
        if AUSNAHME.search(zeile):
            continue
        for v in VERBOTEN:
            if v in zeile:
                fehler.append("verbotenes zeichen %r in %r" % (v, zeile[:50]))
    return fehler


def pruefen(daten, breite, hoehe):
    fehler = []
    warnung = []
    for e in daten["texte"]:
        grenze = MIN_KLEIN if e["klein"] else MIN_ALLGEMEIN
        if e["px"] < grenze:
            fehler.append(
                "%.0f px, mindestens %d noetig, im feed nur %.0f px, %r"
                % (e["px"], grenze, e["px"] * FEED_BREITE / breite, e["txt"]))
    if daten["hoehe"] > hoehe + 1:
        fehler.append("ueberlauf, inhalt ist %d px hoch, bild nur %d"
                      % (daten["hoehe"], hoehe))
    for s in daten.get("schnitt") or []:
        fehler.append("abgeschnitten, %r fehlen %d px, inhalt %r"
                      % (s["tag"], s["fehl"], s["txt"]))
    sicht = (daten.get("sicht") or "").lower()
    if not any(m in sicht for m in MARKEN):
        fehler.append("keine marke und keine domain im bild gefunden")
    fehler += zeichen_pruefen(daten.get("sicht") or "")
    verh = breite / float(hoehe)
    if abs(verh - 0.8) > 0.01 and abs(verh - 16 / 9.0) > 0.01:
        warnung.append("seitenverhaeltnis %.3f, erwartet 0.800 fuer posts "
                       "oder 1.778 fuer thumbnails" % verh)
    return fehler, warnung


def lauf(pfad, breite, hoehe):
    daten = messen(pfad, breite, hoehe)
    fehler, warnung = pruefen(daten, breite, hoehe)
    feed = vorschau(daten["png"], breite, hoehe)
    kleinste = sorted(daten["texte"], key=lambda e: e["px"])[:3]
    print("bild      %s" % daten["png"])
    print("vorschau  %s   <- ANSEHEN, nicht messen" % feed)
    print("kleinste  %s" % ", ".join(
        "%.0f px (%s)" % (e["px"], e["txt"][:22]) for e in kleinste))
    for w in warnung:
        print("warnung   %s" % w)
    if fehler:
        print("")
        for f in fehler:
            print("FEHLER    %s" % f)
        print("")
        print("%d fehler. was nicht in die mindestgroesse passt, wird "
              "geloescht und nicht verkleinert." % len(fehler))
        return 1
    print("ok        alle mechanischen pruefungen bestanden")
    print("offen     eine aussage, ohne text verstaendlich, freundetest. "
          "das entscheidet kein skript.")
    return 0


# --- selbsttest ------------------------------------------------------

GUT = """<html><head><style>
body{width:1080px;height:1350px;margin:0;background:#080B0F;color:#fff;
font-family:Arial;padding:40px;box-sizing:border-box}
.h{font-size:82px;font-weight:700}.s{font-size:46px}
.foot{font-size:32px}</style></head><body>
<div class="h">same chain, two answers</div>
<div class="s">each transaction counted once, over 24 hours</div>
<div class="foot">kaspapulse.com</div></body></html>"""

KLEIN = GUT.replace("font-size:46px", "font-size:28px")
OHNE_MARKE = GUT.replace("kaspapulse.com", "some other site")
ZEICHEN = GUT.replace("same chain, two answers", "same chain \u2014 two answers")
UEBERLAUF = GUT.replace("height:1350px", "height:1350px").replace(
    '<div class="h">', '<div class="h" style="margin-top:1300px">')

# der fall vom 20.08.2026. die seite ist genau 1350 hoch, aber flexbox
# staucht den kasten, und die zahl darin wird abgeschnitten.
GESTAUCHT = """<html><head><style>
body{width:1080px;height:1350px;margin:0;background:#080B0F;color:#fff;
font-family:Arial;padding:40px;box-sizing:border-box;display:flex;
flex-direction:column}
.hero{overflow:hidden;padding:20px}
.hero .v{font-size:186px;font-weight:700}
.rest{height:1100px;font-size:46px}
.foot{font-size:32px}</style></head><body>
<div class="hero"><div class="v">+$4.1B</div></div>
<div class="rest">viel inhalt darunter, der den kasten zusammendrueckt</div>
<div class="foot">pulsehawk.io</div></body></html>"""


def selbsttest():
    import tempfile
    faelle = [("gut", GUT, 0), ("zu klein", KLEIN, 1),
              ("ohne marke", OHNE_MARKE, 1), ("gedankenstrich", ZEICHEN, 1),
              ("ueberlauf", UEBERLAUF, 1), ("gestaucht", GESTAUCHT, 1)]
    schlecht = 0
    for name, html, erwartet in faelle:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                         encoding="utf-8") as f:
            f.write(html)
            pfad = f.name
        daten = messen(pfad, 1080, 1350)
        fehler, _ = pruefen(daten, 1080, 1350)
        ist = 1 if fehler else 0
        ok = "ok  " if ist == erwartet else "FEHL"
        if ist != erwartet:
            schlecht += 1
        print("%s %-16s erwartet %d, ist %d %s"
              % (ok, name, erwartet, ist, fehler[:1]))
        os.unlink(pfad)
    print("%d von %d faellen falsch" % (schlecht, len(faelle)))
    return 1 if schlecht else 0


def main():
    a = argparse.ArgumentParser()
    a.add_argument("datei", nargs="?")
    a.add_argument("--breite", type=int, default=1080)
    a.add_argument("--hoehe", type=int, default=1350)
    a.add_argument("--selbsttest", action="store_true")
    n = a.parse_args()
    if n.selbsttest:
        return selbsttest()
    if not n.datei:
        a.error("datei fehlt")
    return lauf(n.datei, n.breite, n.hoehe)


if __name__ == "__main__":
    sys.exit(main())
