#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kaspadollar_grafik.py, KaspaDollar-Spenden als Feed-Bild im Look v2 (Ben, 29.10.2026).

Stand 28.10.2026 12:42:28 UTC: 182,012.19 KAS counted (Kontrollzaehlung,
eigener Knoten) gegen 182,012 KAS source kaspadollar.com zur selben Minute,
0 KAS Abgaenge, 3.6 % von 5,000,000 laut Seite. Richtung A, Papier, Wortmarke
schwarz, kein Falke. Eine englische Fassung und eine deutsche fuer die
Telegram-Gruppe Kaspa German.

Keine Adresse, keine Transaktionskennung, kein Kurs, kein Link. Jede Seite
laeuft durch content_wache im Profil feed (Groessen, Textregeln, Kontrast
7:1, Rand 60 px). Die Datumsregel der Wache kennt nur englische Monate; fuer
die deutsche Fassung prueft dieses Skript das Datum selbst.

    python3 scripts/kaspadollar_grafik.py --ziel kaspadollar/ergebnis
    python3 scripts/kaspadollar_grafik.py --selbsttest
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

W, H = 1080, 1350
PAPIER, TINTE, LEISE, TEAL = "#F4F1EA", "#0B1A17", "#3A4744", "#49EACB"
SPUR = "#D9D4C8"

STAND = {"counted_kas": 182012.18740296, "seite_kas": 182012, "ziel_kas": 5000000, "seite_prozent": 3.6,
         "abgaenge_kas": 0}

TEXTE = {
    "en": {
        "kicker": "28 oct 2026", "rechts": "counted",
        "titel": "kaspadollar donations, checked on our own node",
        "zahl": "182,012", "einheit": "KAS",
        "zeile1": "counted 182,012.19 KAS, 28 oct 2026 12.42 utc",
        "zeile2": "site 182,012 KAS, same minute, source kaspadollar.com",
        "zeile3": "0 KAS left the address, counted",
        "balken": "3.6 % of the 5,000,000 KAS goal, source kaspadollar.com",
        "null": "0", "ende": "5,000,000",
    },
    "de": {
        "kicker": "28. okt 2026", "rechts": "gezählt",
        "titel": "kaspadollar spenden, geprüft auf unserem eigenen knoten",
        "zahl": "182.012", "einheit": "KAS",
        "zeile1": "gezählt 182.012,19 KAS, 28. okt 2026, 12.42 uhr utc",
        "zeile2": "seite 182.012 KAS, gleiche minute, quelle kaspadollar.com",
        "zeile3": "0 KAS haben die adresse verlassen, gezählt",
        "balken": "3,6 % vom ziel 5.000.000 KAS, quelle kaspadollar.com",
        "null": "0", "ende": "5.000.000",
    },
}
DATUM_DE = re.compile(r"\b\d{1,2}\. (?:jan|feb|mär|apr|mai|jun|jul|aug|sep|okt|nov|dez)\b", re.I)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
*{box-sizing:border-box}
body{margin:0;width:1080px;height:1350px;overflow:hidden;position:relative;font-family:'IBM Plex Sans',sans-serif;
background:%(papier)s}
.t{position:absolute}
.kicker{font:500 34px/1.2 'IBM Plex Mono',monospace;letter-spacing:.04em;color:%(leise)s}
.titel{font:900 64px/1.06 Archivo,sans-serif;letter-spacing:-.01em;text-wrap:balance;color:%(tinte)s}
.zahl{font:900 250px/.86 Archivo,sans-serif;letter-spacing:-.035em;white-space:nowrap;color:%(tinte)s}
.einheit{font:700 64px/1 Archivo,sans-serif;color:%(tinte)s}
.zeile{font:500 36px/1.3 'IBM Plex Sans',sans-serif;color:%(tinte)s}
.leise{font:400 34px/1.3 'IBM Plex Mono',monospace;color:%(leise)s}
.linie{position:absolute;height:1px;background:%(tinte)s}
.fuss{position:absolute;left:50%%;transform:translateX(-50%%);bottom:72px;white-space:nowrap}
""" % {"papier": PAPIER, "tinte": TINTE, "leise": LEISE}


def balken_breite(gesamt=936):
    """Fuellung ab der Nulllinie, Anteil laut Seite (3.6 %)."""
    return round(gesamt * STAND["seite_prozent"] / 100)


def seite(sprache):
    import look_takt
    import wortmarke
    t = TEXTE[sprache]
    b = balken_breite()
    teile = [
        "<div class='t kicker' style='left:72px;top:72px'>%s</div>" % esc(t["kicker"]),
        "<div class='t kicker' style='right:72px;top:72px'>%s</div>" % esc(t["rechts"]),
        "<div class='linie' style='left:72px;right:72px;top:134px'></div>",
        "<div class='linie' style='left:72px;width:160px;top:133px;height:4px;background:%s'></div>" % TEAL,
        "<div class='t titel' data-rolle='titel' style='left:72px;right:120px;top:184px'>%s</div>" % esc(t["titel"]),
        "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:400px'>%s</div>" % esc(t["zahl"]),
        "<div class='t einheit' data-rolle='einheit' style='left:72px;top:610px'>%s</div>" % esc(t["einheit"]),
        "<div class='linie' style='left:72px;right:72px;top:700px'></div>",
        # unterer teil im fluss, damit laengere deutsche zeilen umbrechen duerfen
        "<div class='t' id='unten' style='left:72px;right:72px;top:722px'>"
        "<div class='zeile'>%s</div><div class='zeile' style='margin-top:8px'>%s</div>"
        "<div class='zeile' style='margin-top:28px'>%s</div>"
        "<div style='height:1px;background:%s;margin-top:30px'></div>"
        "<div style='position:relative;height:68px;margin-top:40px'>"
        "<div style='position:absolute;left:0;top:12px;width:936px;height:44px;background:%s'></div>"
        "<div style='position:absolute;left:0;top:12px;width:%dpx;height:44px;background:%s'></div>"
        "<div style='position:absolute;left:0;top:0;width:3px;height:68px;background:%s'></div></div>"
        "<div style='display:flex;justify-content:space-between;margin-top:6px'>"
        "<span class='leise'>%s</span><span class='leise'>%s</span></div>"
        "<div class='zeile' style='margin-top:10px;color:%s'>%s</div></div>"
        % (esc(t["zeile1"]), esc(t["zeile2"]), esc(t["zeile3"]), TINTE, SPUR, b, TEAL, TINTE,
           esc(t["null"]), esc(t["ende"]), LEISE, esc(t["balken"])),
        "<div class='fuss' data-rolle='fuss'>%s</div>" % wortmarke.html(),
    ]
    css = look_takt.schriften_css() + CSS + wortmarke.css(groesse=36, sperrung=6, kaspa=TINTE, pulse=TINTE)
    return ("<!DOCTYPE html><html lang='%s'><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>"
            % (sprache, css, "".join(teile)))


FIT_JS = """() => {
  const aus = [];
  for (const z of document.querySelectorAll('[data-fit]')) {
    let g = parseFloat(getComputedStyle(z).fontSize), max = parseFloat(z.dataset.fit);
    while (z.scrollWidth > max && g > 200) { g -= 4; z.style.fontSize = g + 'px'; }
    if (z.scrollWidth > max) aus.push('zahl ' + z.textContent + ' zu breit');
  }
  const ts = [...document.querySelectorAll('.t')].map(e => [e.className + ' ' + e.textContent.slice(0, 20), e.getBoundingClientRect()]);
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i][1], b = ts[j][1];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
      aus.push('ueberlappen ' + ts[i][0] + ' / ' + ts[j][0]);
  }
  const u = document.getElementById('unten'), f = document.querySelector('[data-rolle=fuss]');
  if (u && f && u.getBoundingClientRect().bottom > f.getBoundingClientRect().top - 40)
    aus.push('unterer teil reicht bis an die wortmarke');
  return aus;
}"""


def rendern(ziel):
    from playwright.sync_api import sync_playwright
    import content_wache
    import tagesgrafik as tg
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    fertig = []
    with sync_playwright() as pw:
        br = tg.chromium_start(pw)
        try:
            for sprache in ("en", "de"):
                png = ziel / ("kaspadollar-spenden-2026-10-28-%s.png" % sprache)
                html = ziel / ("kaspadollar-%s.html" % sprache)
                html.write_text(seite(sprache), encoding="utf-8")
                pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
                try:
                    pg.goto(html.resolve().as_uri())
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(250)
                    f = pg.evaluate(FIT_JS)
                    if f:
                        raise SystemExit("%s, %s" % (sprache, "; ".join(f)))
                    pg.screenshot(path=str(png))
                    v = content_wache.pruefe_seite(pg, "instagram", png)
                    if sprache == "de":
                        # die wache kennt nur englische monate, das datum prueft DATUM_DE
                        v = [x for x in v if "zahl ohne datum" not in x]
                        if not DATUM_DE.search(TEXTE["de"]["zeile1"]):
                            v.append("de: kein datum mit monat")
                    if v:
                        raise SystemExit("%s, wache, %s" % (sprache, "; ".join(v)))
                finally:
                    pg.close()
                    html.unlink()
                fertig.append(png)
                print("ok", png.name)
        finally:
            br.close()
    return fertig


def selbsttest():
    import content_wache
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)
    ok("prozent der seite passt zur summe der seite",
       round(STAND["seite_kas"] / STAND["ziel_kas"] * 100, 1) == STAND["seite_prozent"])
    ok("counted und seite zur selben minute, unterschied unter 1 KAS",
       0 <= STAND["counted_kas"] - STAND["seite_kas"] < 1)
    ok("balken 3.6 % von 936 px", balken_breite() == 34)
    for s, t in TEXTE.items():
        for k, v in t.items():
            vs = content_wache.text_verstoesse(v)
            ok("textregeln %s %s" % (s, k), not vs)
        alles = " ".join(t.values())
        ok("%s ohne adresse, link oder kennung" % s, not re.search(r"kaspa:|https?://|www\.|[0-9a-f]{16,}", alles))
        ok("%s ohne kurs" % s, not re.search(r"(?i)\busd\b|\$|eur\b|€|price|preis|kurs", alles))
    ok("en datum", content_wache.DATUM.search(TEXTE["en"]["zeile1"]) is not None)
    ok("de datum", DATUM_DE.search(TEXTE["de"]["zeile1"]) is not None)
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ziel", default="kaspadollar/ergebnis")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    rendern(a.ziel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
