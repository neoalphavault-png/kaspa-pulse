#!/usr/bin/env python3
"""kontaktbogen.py, alle Gerueste in allen Looks auf einem Bild (Ben, 15.10.2026).

Fuer jeden PR der Design-Runde. Ben schickt den Bogen zur Pruefung weiter.
Gerendert wird mit denselben Funktionen wie im scharfen Lauf, also mit
derselben Layoutpruefung: eine Kachel, die sie nicht besteht, steht rot mit
dem Grund im Bogen statt als Bild.

Bis die eigenen Formate kommen (Story, X 1600x900, Discord 1200x1200), sind
alle Kanaele 1080x1350 und unterscheiden sich nur im Look aus ihrem Takt.
Der Bogen zeigt deshalb je Geruest die drei Looks einmal.

    python3 scripts/kontaktbogen.py --out /tmp/bogen.png
    python3 scripts/kontaktbogen.py --out /tmp/bogen.png --zahl a.json --zahl b.json
    python3 scripts/kontaktbogen.py --selbsttest

Ohne --zahl nimmt der Bogen data/number-of-day.json.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

KACHEL_B, KACHEL_H, KOPF = 360, 450, 64
SPALTEN = 6


def bilder(ziel, zahl_payloads):
    import number_of_day
    import tagesgrafik
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = tagesgrafik.chromium_start(p)
        try:
            liste = tagesgrafik.kontaktbogen_bilder(Path(ziel) / "tg", b)
            liste += number_of_day.kontaktbogen_bilder(Path(ziel) / "zahl", b, zahl_payloads)
        finally:
            b.close()
    return liste


def zusammensetzen(liste, out):
    from PIL import Image, ImageDraw, ImageFont
    zeilen = (len(liste) + SPALTEN - 1) // SPALTEN
    bogen = Image.new("RGB", (KACHEL_B * SPALTEN, (KACHEL_H + KOPF) * zeilen), "#5A6266")
    zeichnen = ImageDraw.Draw(bogen)
    try:
        schrift = ImageFont.load_default(size=22)
    except TypeError:                                # pillow vor 10.1
        schrift = ImageFont.load_default()
    for i, (name, png) in enumerate(liste):
        x, y = (i % SPALTEN) * KACHEL_B, (i // SPALTEN) * (KACHEL_H + KOPF)
        if png is None:
            zeichnen.rectangle([x + 4, y + KOPF, x + KACHEL_B - 4, y + KOPF + KACHEL_H - 4], fill="#7A1414")
        else:
            bogen.paste(Image.open(png).convert("RGB").resize((KACHEL_B - 8, KACHEL_H - 8)),
                        (x + 4, y + KOPF))
        text = name if len(name) <= 60 else name[:58] + ".."
        zeichnen.text((x + 8, y + 6), text[:30], fill="#FFFFFF", font=schrift)
        zeichnen.text((x + 8, y + 32), text[30:], fill="#FFD5D5" if png is None else "#DDE6E3", font=schrift)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bogen.save(out)
    return out


def zahl_laden(pfade):
    if not pfade:
        pfade = [REPO / "data" / "number-of-day.json"]
    return [(Path(p).stem[:12], json.loads(Path(p).read_text(encoding="utf-8"))) for p in pfade]


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    try:
        from PIL import Image
    except ImportError:
        print("pillow fehlt, selbsttest uebersprungen")
        return 0
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.png"
        Image.new("RGB", (1080, 1350), "#080B0F").save(a)
        out = zusammensetzen([("probe dunkel", a), ("probe FEHLER zu hoch", None)], Path(td) / "b.png")
        im = Image.open(out)
        ok("bogen hat %d spalten und eine zeile" % SPALTEN,
           im.size == (KACHEL_B * SPALTEN, KACHEL_H + KOPF))
        ok("eine fehlerkachel ist rot", im.getpixel((KACHEL_B + 100, KOPF + 100)) == (0x7A, 0x14, 0x14))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="kontaktbogen.png")
    ap.add_argument("--zahl", action="append", default=[], help="payload der zahl des tages, mehrfach")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    with tempfile.TemporaryDirectory() as td:
        liste = bilder(td, zahl_laden(a.zahl))
        zusammensetzen(liste, a.out)
    rot = [n for n, p in liste if p is None]
    print("kontaktbogen %s, %d kacheln, %d rot" % (a.out, len(liste), len(rot)))
    for n in rot:
        print("ROT " + n)
    return 1 if rot else 0


if __name__ == "__main__":
    sys.exit(main())
