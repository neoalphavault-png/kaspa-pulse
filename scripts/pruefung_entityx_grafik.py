#!/usr/bin/env python3
"""pruefung_entityx_grafik.py, Grafik zum Abgang von Entity X am 28.09.2026.

Hausnorm wie die Mining-Grafik vom 26.09. (1080x1350, #080B0F, #49EACB,
Falke oben und unten, keine Domain, kein Link). Jede Zahl stammt aus den
Runner-Laeufen auf diesem Branch:
  36525301805  alle Bewegungen seit 25.09.
  36525392196  die Transaktion 65f120cf... vollstaendig
  36525464638  Weitergabe der Zieladresse qrl6dvnd... am 29.09. 02:42 UTC
  36529480494  Umlauf 29.09. 03:00 UTC 27.727.376.907, Anteil 5,4805 %

Wortregel (Ben): sent, left, passed on. Nie sold oder bought, kein Motiv.
Kein Doppelpunkt, kein Gedankenstrich, kein Pfeil. "gate.io" ist das Label
der Explorer-API und darf als einziges Wort mit Punkt stehen.

    python3 scripts/pruefung_entityx_grafik.py --out bild.png --anteil 5.48 --vorschau 390
"""
import argparse
import base64
import os
import re
import sys
from pathlib import Path

W, H = 1080, 1350
RAUS = 6377600.99                  # 65f120cf..., nur der Anteil von entity x
ZIEL_GATE = 3291851.00             # an qrl6dvnd..., 29.09. 02:42 weiter an Gate.io
ZIEL_NEU = 3087061.98              # an qp779ewj..., unberuehrt
STAND = 1519597995.47              # entity x nach dem abgang, heartbeat und alarm
ERLAUBT = {"gate.io"}
WORTLISTE = ("sold", "sell", "selling", "sale", "bought", "buy", "buying",
             "purchase", "dump", "dumping", "panic", "exit", "cash out", "profit",
             "whale", "because", "to avoid", "preparing", "plans", "intends",
             "wants", "fear", "bearish", "bullish")


def mio(x):
    return "%.2fM" % (x / 1e6)


def pruefe_text(texte):
    verboten = {":": "Doppelpunkt", "\u2014": "Gedankenstrich", "\u2013": "Gedankenstrich",
                "\u2192": "Pfeil", "->": "Pfeil", " - ": "Bindestrich als Satzzeichen"}
    domain = re.compile(r"\b[\w-]+\.(?:com|org|io|net|stream|xyz|app|dev|de)\b", re.I)
    for t in texte:
        ohne_zeit = re.sub(r"\d\d:\d\d", "", t)      # uhrzeiten sind erlaubt
        for z, name in verboten.items():
            if z in ohne_zeit:
                raise SystemExit("FEHLER %s im Text %r" % (name, t))
        for m in domain.finditer(t):
            if m.group(0).lower() not in ERLAUBT:
                raise SystemExit("FEHLER Domain im Text %r" % t)
        if "http" in t.lower() or "www" in t.lower() or "kaspapulse" in t.lower():
            raise SystemExit("FEHLER Link im Text %r" % t)
        klein = " %s " % re.sub(r"[^a-z0-9. ]", " ", t.lower())
        for w in WORTLISTE:
            if " %s " % w in klein:
                raise SystemExit("FEHLER Wortliste %r im Text %r" % (w, t))

CSS = """
:root{--bg:#080B0F;--line:#1C242D;--teal:#49EACB;--txt:#FFFFFF;--dim:#A7B0B9;--dimmer:#8C97A2}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:var(--bg);color:var(--txt);
  font-family:'Helvetica Neue',Helvetica,Arial,'Liberation Sans',sans-serif;
  padding:34px 52px 26px;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}
.top{display:flex;align-items:center;gap:16px;border-bottom:2px solid var(--line);padding-bottom:12px;flex:none}
.falc{width:48px;height:auto;display:block}
.brand{font-size:40px;letter-spacing:6px;font-weight:700}
.brand span{color:var(--teal)}
h1{font-size:78px;line-height:1.04;letter-spacing:-1.5px;margin-top:18px;font-weight:700;flex:none}
.value{font-size:168px;font-weight:700;letter-spacing:-7px;line-height:0.88;margin-top:14px;color:var(--txt);flex:none}
.vlabel{font-size:56px;line-height:1.14;color:var(--dim);margin-top:6px;flex:none}
.chart{display:block;margin-top:12px;flex:none}
.chart .grid{stroke:#1C242D;stroke-width:2}
.chart .zero{stroke:#8C97A2;stroke-width:3}
.chart .area{fill:rgba(73,234,203,0.14)}
.chart .ser{fill:none;stroke:var(--teal);stroke-width:6;stroke-linejoin:round;stroke-linecap:round}
.chart .dot{fill:var(--teal)}
.chart .gap{fill:var(--bg);stroke:#FFFFFF;stroke-width:4}
.chart text{font-family:inherit;font-weight:700}
.chart .tag{font-size:42px;fill:#FFFFFF}
.chart .unit{font-size:34px;fill:#8C97A2}
.chart .axis{font-size:40px;fill:#A7B0B9}
.legend{display:flex;align-items:center;gap:16px;font-size:40px;color:var(--dim);flex:none}
.legend i{width:24px;height:24px;border:4px solid #FFFFFF;border-radius:50%;display:inline-block;flex:none}
.body{font-size:46px;line-height:1.2;margin-top:34px;flex:none}
.body em{font-style:normal;color:var(--teal);font-weight:700}
.blocks{display:flex;flex-direction:column;gap:26px;margin-top:34px;flex:none}
.blk .row{display:flex;align-items:baseline;gap:22px}
.blk .num{font-size:86px;font-weight:700;letter-spacing:-3px;line-height:1}
.blk .track{height:30px;background:#141B22;border-radius:6px;margin-top:14px;overflow:hidden}
.blk .fill{height:100%;background:var(--teal);border-radius:6px}
.blk.neu .fill{background:#E8ECEF}
.blk .txt{font-size:46px;line-height:1.18;color:var(--dim);margin-top:12px}
.foot{margin-top:auto;padding-top:12px;flex:none;border-top:2px solid var(--line);
  display:flex;flex-direction:column;align-items:flex-start;gap:12px}
.foot .src{font-size:32px;line-height:1.35;color:var(--dimmer)}
.foot .mark{display:flex;align-items:center;gap:12px;flex:none}
.foot .falc{width:40px}
.foot .brand{font-size:30px;letter-spacing:4px}
.foot .mark{gap:10px}
"""

def html(anteil, falke):
    texte = {
        "kopf": "ENTITY X MOVED",
        "wert": "%s KAS" % mio(RAUS),
        "label": "left the wallet in one transaction, 28 september, 12:26 utc",
        "a_num": mio(ZIEL_GATE),
        "a_txt": "passed on to a gate.io labelled address 14 hours later",
        "b_num": mio(ZIEL_NEU),
        "b_txt": "new address, untouched",
        "satz": "wallet now holds %.2fB kas, %.2f%% of everything in circulation"
                % (STAND / 1e9, anteil),
        "fuss": "counted on chain \u00b7 sources kaspa rest api, explorer labels "
                "\u00b7 as of 29 sep 2026, 03:00 utc",
    }
    pruefe_text(texte.values())
    for k in texte:
        for f in ("28 september", "12:26 utc", "14 hours", "29 sep 2026", "03:00 utc", "1.52B kas"):
            texte[k] = texte[k].replace(f, f.replace(" ", "\u00a0"))
    if abs(ZIEL_GATE + ZIEL_NEU - RAUS) > 2000:
        raise SystemExit("FEHLER die beiden Ziele ergeben nicht den Abgang")
    marke = '<img class="falc" src="%s" alt=""><div class="brand">KASPA <span>PULSE</span></div>' % falke
    satz = texte["satz"].replace("%.2f%%" % anteil, "<em>%.2f%%</em>" % anteil)
    blk = lambda cls, num, txt, frac: (
        "<div class='blk %s'><div class='num'>%s</div>"
        "<div class='track'><div class='fill' style='width:%.2f%%'></div></div>"
        "<div class='txt'>%s</div></div>" % (cls, num, 100 * frac, txt))
    return ("<!DOCTYPE html><html><head><meta charset='UTF-8'><style>%s</style></head><body>"
            "<div class='top'>%s</div>"
            "<h1>%s</h1><div class='value'>%s</div><div class='vlabel'>%s</div>"
            "<div class='blocks'>%s%s</div>"
            "<div class='body'>%s</div>"
            "<div class='foot'><div class='src'>%s</div><div class='mark'>%s</div></div>"
            "</body></html>") % (
        CSS, marke, texte["kopf"], texte["wert"], texte["label"],
        blk("gate", texte["a_num"], texte["a_txt"], ZIEL_GATE / RAUS),
        blk("neu", texte["b_num"], texte["b_txt"], ZIEL_NEU / RAUS),
        satz, texte["fuss"], marke)


def rendern(seite, out, vorschau=None):
    from playwright.sync_api import sync_playwright
    launch = {}
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        if os.path.exists(c):
            launch["executable_path"] = c
            break
    tmp = Path(out).with_suffix(".html")
    tmp.write_text(seite, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(400)
        ueber = pg.evaluate("Math.max(0, document.body.scrollHeight - %d)" % H)
        if ueber:
            b.close()
            raise SystemExit("FEHLER Inhalt ist %d px zu hoch. Text kuerzen, nicht Schrift verkleinern." % ueber)
        pg.screenshot(path=str(out))
        if vorschau:
            v = b.new_page(viewport={"width": vorschau, "height": round(vorschau * H / W)},
                           device_scale_factor=1)
            v.set_content("<html><body style='margin:0;background:#000'>"
                          "<img src='data:image/png;base64,%s' style='width:%dpx;display:block'>"
                          "</body></html>" % (base64.b64encode(Path(out).read_bytes()).decode(), vorschau))
            v.wait_for_timeout(200)
            v.screenshot(path=str(Path(out).with_name(Path(out).stem + "-vorschau-%d.png" % vorschau)))
        b.close()
    tmp.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--anteil", type=float, required=True,
                    help="anteil am umlauf in prozent, aus dem stand-lauf")
    ap.add_argument("--falke", default=str(Path.home() / "pulse-studio" / "kp" / "falcon.b64"))
    ap.add_argument("--vorschau", type=int, default=0)
    a = ap.parse_args(argv)
    falke = Path(a.falke).read_text().strip()
    rendern(html(a.anteil, falke), a.out, a.vorschau)
    print("geschrieben %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
