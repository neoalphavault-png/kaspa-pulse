#!/usr/bin/env python3
"""pruefung_mining_grafik.py, Grafik fuer die deutsche Telegram-Gruppe.

Frage aus der Gruppe (NordicMineral, 26.09.2026): gleichen steigende
Gebuehren den sinkenden Block Reward aus? Jede Zahl im Bild kommt aus
data/pruefung/mining-ertrag-monate-2023-10-bis-2026-09.csv, und die ist
Zeichen fuer Zeichen die Ausgabe des Runner-Laufs 36234604567.

Kurve und grosse Zahl sind derselbe Wert: gebuehren_am_ertrag_pct, also
Gebuehren durch (Reward plus Gebuehren). Das ist, was die Beschriftung
"Anteil der Gebuehren am Miner-Ertrag" sagt.

    python3 scripts/pruefung_mining_grafik.py --out /pfad/bild.png
    python3 scripts/pruefung_mining_grafik.py --out /pfad/bild.png --vorschau 390

Kein Doppelpunkt, kein Gedankenstrich, kein Pfeil im Text (Hausregel,
dieselbe Pruefung wie number_of_day.py), keine Domain, kein Link.
"""
import argparse
import base64
import csv
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CSV = REPO / "data" / "pruefung" / "mining-ertrag-monate-2023-10-bis-2026-09.csv"
W, H = 1080, 1350
LUECKE = {"2025-02", "2026-01", "2026-03"}      # monate mit fehlenden gebuehrentagen
MONAT = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.",
         "Sep.", "Okt.", "Nov.", "Dez."]


def zahl(x, stellen):
    return ("%.*f" % (stellen, x)).replace(".", ",")


def monatsname(m):
    j, n = m.split("-")
    return "%s %s" % (MONAT[int(n) - 1], j)


def lies():
    with open(CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pruefe_text(texte):
    verboten = {":": "Doppelpunkt", "—": "Gedankenstrich", "–": "Gedankenstrich",
                "→": "Pfeil", " - ": "Bindestrich als Satzzeichen"}
    domain = re.compile(r"\b[\w-]+\.(?:com|org|io|net|stream|xyz|app|dev|de)\b", re.I)
    for t in texte:
        for z, name in verboten.items():
            if z in t:
                raise SystemExit("FEHLER %s im Text %r" % (name, t))
        if domain.search(t) or "http" in t.lower() or "www" in t.lower():
            raise SystemExit("FEHLER Domain oder Link im Text %r" % t)


def kurve(reihen):
    """SVG der Kurve. Nulllinie sichtbar, Spitze beschriftet, drei Monate
    mit fehlenden Gebuehrentagen als offene Kreise."""
    cw, ch = 976, 362
    l, r, o, u = 104, 24, 36, 58          # innenraender: links achse, unten monate
    pw, ph = cw - l - r, ch - o - u
    werte = [float(z["gebuehren_am_ertrag_pct"]) for z in reihen]
    ymax = 20.0
    n = len(werte)

    def x(i):
        return l + pw * i / (n - 1)

    def y(v):
        return o + ph * (1 - v / ymax)

    s = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d">' % (cw, ch, cw, ch)]
    # hilfslinien 10 und 20 %, nulllinie deutlich
    for v in (10, 20):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/>' % (l, cw - r, y(v), y(v)))
    for v in (0, 10, 20):
        s.append('<text x="%d" y="%.1f" class="unit" text-anchor="end">%d %%</text>'
                 % (l - 16, y(v) + 12, v))
    # jahresanfaenge als stille striche
    for i, z in enumerate(reihen):
        if z["monat"].endswith("-01"):
            s.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%.1f" class="grid"/>' % (x(i), x(i), o, y(0)))
    # flaeche und linie
    pts = " ".join("%.1f,%.1f" % (x(i), y(v)) for i, v in enumerate(werte))
    s.append('<polygon points="%.1f,%.1f %s %.1f,%.1f" class="area"/>'
             % (x(0), y(0), pts, x(n - 1), y(0)))
    s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="zero"/>' % (l, cw - r, y(0), y(0)))
    s.append('<polyline points="%s" class="ser"/>' % pts)
    # spitze
    k = max(range(n), key=lambda i: werte[i])
    s.append('<circle cx="%.1f" cy="%.1f" r="9" class="dot"/>' % (x(k), y(werte[k])))
    s.append('<text x="%.1f" y="%.1f" class="tag" text-anchor="start">%s · %s %%</text>'
             % (x(k) + 22, y(werte[k]) + 14, monatsname(reihen[k]["monat"]), zahl(werte[k], 1)))
    # monate mit luecke
    for i, z in enumerate(reihen):
        if z["monat"] in LUECKE:
            s.append('<circle cx="%.1f" cy="%.1f" r="11" class="gap"/>' % (x(i), y(werte[i])))
    # endpunkt
    s.append('<circle cx="%.1f" cy="%.1f" r="9" class="dot"/>' % (x(n - 1), y(werte[-1])))
    # monatsachse, nur anfang, ein jahr, ende
    unten = ch - 18
    s.append('<text x="%.1f" y="%d" class="axis" text-anchor="start">%s</text>'
             % (x(0) - 4, unten, monatsname(reihen[0]["monat"])))
    j25 = [i for i, z in enumerate(reihen) if z["monat"] == "2025-01"][0]
    s.append('<text x="%.1f" y="%d" class="axis" text-anchor="middle">2025</text>' % (x(j25), unten))
    s.append('<text x="%.1f" y="%d" class="axis" text-anchor="end">%s</text>'
             % (x(n - 1) + 4, unten, monatsname(reihen[-1]["monat"])))
    s.append("</svg>")
    return "\n".join(s)


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
.value{font-size:190px;font-weight:700;letter-spacing:-7px;line-height:0.88;margin-top:14px;color:var(--txt);flex:none}
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
.body{font-size:46px;line-height:1.2;margin-top:14px;flex:none}
.body em{font-style:normal;color:var(--teal);font-weight:700}
.foot{margin-top:auto;padding-top:12px;flex:none;border-top:2px solid var(--line);
  display:flex;justify-content:space-between;align-items:center;gap:24px}
.foot .src{font-size:32px;line-height:1.35;color:var(--dimmer)}
.foot .mark{display:flex;align-items:center;gap:12px;flex:none}
.foot .falc{width:56px}
"""


def html(reihen, falke):
    letzt = reihen[-1]
    feb = [z for z in reihen if z["monat"] == "2025-02"][0]
    anteil = float(letzt["gebuehren_am_ertrag_pct"])
    plus = 100 * (float(letzt["ertrag_kas_je_th_tag"]) / float(feb["ertrag_kas_je_th_tag"]) - 1)
    texte = {
        "kopf": "Gleichen Gebühren den sinkenden Block Reward aus?",
        "wert": "%s %%" % zahl(anteil, 2),
        "label": "Anteil der Gebühren am Miner-Ertrag, September 2026",
        "legende": "Monat mit fehlenden Gebührentagen",
        "satz": "Der Ertrag je TH/s hält sich, weil die Hashrate fällt, "
                "seit Februar 2025 +%d %% in KAS." % round(plus),
        "fuss": "Durchschnitt des ganzen Netzes · Quellen Kaspa REST API, "
                "Kaspalytics · Stand 25.09.2026",
    }
    pruefe_text(texte.values())
    satz = texte["satz"].replace("+%d %%" % round(plus), "<em>+%d %%</em>" % round(plus))
    marke = '<img class="falc" src="%s" alt=""><div class="brand">KASPA <span>PULSE</span></div>' % falke
    return ("<!DOCTYPE html><html><head><meta charset='UTF-8'><style>%s</style></head><body>"
            "<div class='top'>%s</div>"
            "<h1>%s</h1><div class='value'>%s</div><div class='vlabel'>%s</div>%s"
            "<div class='legend'><i></i>%s</div>"
            "<div class='body'>%s</div>"
            "<div class='foot'><div class='src'>%s</div><div class='mark'><img class='falc' src='%s' alt=''></div></div>"
            "</body></html>") % (CSS, marke, texte["kopf"], texte["wert"], texte["label"],
                                 kurve(reihen), texte["legende"], satz, texte["fuss"], falke)


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
    ap.add_argument("--falke", default=str(Path.home() / "pulse-studio" / "kp" / "falcon.b64"),
                    help="Falke als data-URI (pulse-studio/kp/falcon.b64)")
    ap.add_argument("--vorschau", type=int, default=0)
    a = ap.parse_args(argv)
    falke = Path(a.falke).read_text().strip()
    reihen = lies()
    if len(reihen) != 36 or reihen[0]["monat"] != "2023-10" or reihen[-1]["monat"] != "2026-09":
        raise SystemExit("FEHLER unerwartete Reihe %s bis %s, %d Monate"
                         % (reihen[0]["monat"], reihen[-1]["monat"], len(reihen)))
    rendern(html(reihen, falke), a.out, a.vorschau)
    print("geschrieben %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
