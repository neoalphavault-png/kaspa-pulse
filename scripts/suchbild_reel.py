#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suchbild_reel.py, Suchbild "find the 1 white dot" (Ben, 26.10.2026).

WAS ES IST
Ein dichtes Standbild mit einer Aufgabe in Sekunde 0. Ein Raster aus genau so
vielen tuerkisen Punkten, wie wir Kaspa-Bloecke in einem Fenster gezaehlt
haben, darin 1 weisser Punkt fuer den 1 Block, den Bitcoin laut Protokoll in
600 Sekunden anpeilt. Bitcoin nur als Massstab, zwei Zahlen, kein Werturteil.

    Reel       1080x1920, Standbild 12 s mit ruhiger Musik ohne Gesang
    Karussell  2 Folien 1080x1350, Folie 2 mit markiertem weissem Punkt

DIE ZAHL IST DIE GEZAEHLTE ROHZAHL, NIE RATE MAL FENSTER
Ben, 26.10.2026: "Nicht aus 10.093 x 600.3 rechnen, sondern die gezaehlte
Rohzahl nehmen. Findest du sie nicht, melden und nicht raten." Deshalb gibt
es genau zwei Wege zur Zahl:

* --lauf JJJJ-MM-TT liest einen Lauf aus data/tagesgrafik-log.json, der
  messwerte.daa_zuwachs und fenster_sek traegt (seit 27.10.2026 legt die
  Tagesgrafik beides ab). Fehlt es, bricht das Skript ab.
* --rohzahl N --fenster S --datum JJJJ-MM-TT, wenn Ben die Zahl aus einem
  anderen eigenen Lauf nennt.

Gezaehlt wird der Zuwachs des virtuellen DAA-Scores zwischen zwei Abrufen,
so wie die Tagesgrafik ihre Blockrate misst.

Der Lauf vom 06.10.2026 (10.093 je Sekunde ueber 600.3 s) hat keine Rohzahl
im Repo, und der Workflow-Lauf mit dem Bericht ist bei GitHub geloescht.

MUSIK steht im Register von pulse-studio (docs/musik-lizenzen.md), Pixabay
Content License, fuer Shorts und Reels freigegeben. Standard ist MUSIK unten.

    python3 scripts/suchbild_reel.py bauen --lauf 2026-10-28 --ziel out/suchbild --musik PFAD
    python3 scripts/suchbild_reel.py bauen --rohzahl 6000 --fenster 600.2 --datum 2026-10-28 --ziel out/suchbild
    python3 scripts/suchbild_reel.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

LOG_GRAFIK = REPO / "data" / "tagesgrafik-log.json"
MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
TUERKIS, WEISS, GRUND = "#49EACB", "#F2F5F4", "#080B0F"
SEKUNDEN = 12
MUSIK = {
    "datei": "sonican-cinematic-80s-synthwave-mystery-484908.mp3",
    "titel": "Cinematic 80s Synthwave Mystery",
    "kuenstler": "Sonican",
    "quelle": "Pixabay",
    "lizenz": "Pixabay Content License",
    "register": "pulse-studio, docs/musik-lizenzen.md",
}
CTA = "the weekly kaspa numbers by email, link in bio"
WERTURTEIL = re.compile(r"\b(better|faster|slower|killer|beats?|wins?|loses?|superior|outdated|dead)\b", re.I)


class Stopp(ValueError):
    pass


def tag(d):
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def ganz(n):
    return "{:,}".format(int(n))


def fenster_text(s):
    return ("%.1f" % s).rstrip("0").rstrip(".")


def aus_log(datum, log=None):
    """Die gezaehlte Rohzahl eines Laufs. Ohne daa_zuwachs kein Bild."""
    if log is None:
        log = json.loads(LOG_GRAFIK.read_text(encoding="utf-8"))
    for e in log if isinstance(log, list) else []:
        if e.get("datum") == datum:
            m = e.get("messwerte") or {}
            if m.get("daa_zuwachs") and m.get("fenster_sek"):
                return {"rohzahl": int(m["daa_zuwachs"]), "fenster": float(m["fenster_sek"]),
                        "datum": dt.date.fromisoformat(datum)}
            raise Stopp("lauf %s hat keine gezaehlte rohzahl (daa_zuwachs, fenster_sek), "
                        "nicht raten, melden" % datum)
    raise Stopp("kein lauf %s in %s" % (datum, LOG_GRAFIK.name))


# ------------------------------------------------------------ raster

def raster(n, breite, hoehe):
    """Spalten und Zeilen fuer n Punkte in einer Flaeche, moeglichst quadratisch.
    Die letzte Zeile ist nur so weit gefuellt, wie Punkte da sind."""
    if n < 2:
        raise Stopp("zu wenige punkte")
    sp = max(2, round(math.sqrt(n * breite / hoehe)))
    ze = math.ceil(n / sp)
    while ze > 1 and (ze - 1) * sp >= n:
        ze -= 1
    return sp, ze


def versteck(n, sp, ze, saat):
    """Der Index des weissen Punkts. Nicht in der Mitte, nicht am Rand: ausserhalb
    des mittleren Drittels, mindestens 12 % Abstand zu jedem Rand, und nie in
    der angebrochenen letzten Zeile. Fest aus der Saat, damit Reel und
    Karussell denselben Punkt zeigen."""
    h = int(hashlib.sha256(saat.encode()).hexdigest(), 16)
    rand_s, rand_z = max(1, round(sp * 0.12)), max(1, round(ze * 0.12))
    kandidaten = []
    for z in range(rand_z, ze - rand_z):
        for s in range(rand_s, sp - rand_s):
            i = z * sp + s
            if i >= n or (z + 1) * sp > n:
                continue
            mitte = abs(s - (sp - 1) / 2) < sp / 6 and abs(z - (ze - 1) / 2) < ze / 6
            if not mitte:
                kandidaten.append(i)
    if not kandidaten:
        raise Stopp("kein versteck gefunden")
    return kandidaten[h % len(kandidaten)]


def punkte_svg(n, breite, hoehe, weiss, markiert=False):
    sp, ze = raster(n, breite, hoehe)
    schritt = min(breite / sp, hoehe / ze)
    r = schritt * 0.31
    ox = (breite - schritt * sp) / 2 + schritt / 2
    oy = (hoehe - schritt * ze) / 2 + schritt / 2
    kreise = []
    for i in range(n):
        x, y = ox + (i % sp) * schritt, oy + (i // sp) * schritt
        if i != weiss:
            kreise.append("<circle cx='%.1f' cy='%.1f' r='%.2f'/>" % (x, y, r))
    wx, wy = ox + (weiss % sp) * schritt, oy + (weiss // sp) * schritt
    markierung = ""
    if markiert:
        markierung = ("<circle cx='%.1f' cy='%.1f' r='%.1f' fill='none' stroke='%s' stroke-width='5'/>"
                      % (wx, wy, schritt * 3.2, WEISS))
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>"
           "<g fill='%s'>%s</g><circle cx='%.1f' cy='%.1f' r='%.2f' fill='%s'/>%s</svg>"
           % (breite, hoehe, breite, hoehe, TUERKIS, "".join(kreise), wx, wy, r, WEISS, markierung))
    return svg, {"spalten": sp, "zeilen": ze, "schritt": schritt, "radius": r, "x": wx, "y": wy}


# ------------------------------------------------------------ texte

def texte(d):
    z = ganz(d["rohzahl"])
    bps = d["rohzahl"] / d["fenster"]
    return {
        "titel": "find the 1 white dot",
        "zeile1": "%s kaspa blocks in %s s, counted, %s" % (z, fenster_text(d["fenster"]), tag(d["datum"])),
        "zeile2": "1 white dot, bitcoin protocol target, 1 block per 600 s",
        "f2_zeile1": "%.3f blocks a second, counted, %s" % (bps, tag(d["datum"])),
        "f2_zeile2": "1 block per 10 minutes, bitcoin protocol target",
        "cta": CTA,
    }


def pruefen(t):
    """Textregeln ueber alle sichtbaren Saetze. bitcoin steht hier nur als
    Massstab, deshalb nicht die Karussell-Wortliste, sondern content_wache."""
    import content_wache
    fehler = []
    for k, v in t.items():
        for x in content_wache.text_verstoesse(v):
            fehler.append("%s, %s" % (k, x))
        if WERTURTEIL.search(v):
            fehler.append("%s, werturteil" % k)
        if re.search(r"\b(ethereum|solana|cardano|eth|sol)\b", v, re.I):
            fehler.append("%s, andere chain als bitcoin" % k)
    for k in ("zeile1", "f2_zeile1"):
        if not (re.search(r"\b\d{1,2} (?:%s) \d{4}\b" % "|".join(MONATE), t[k]) and "counted" in t[k]):
            fehler.append("%s, zahl ohne datum oder counted" % k)
    return fehler


# ------------------------------------------------------------ seiten

CSS = """
body{margin:0;background:#080B0F;color:#F2F5F4;overflow:hidden;position:relative}
.t{position:absolute}
.kopf{position:absolute;display:flex;flex-direction:column;gap:14px}
.kopf .t{position:static}
.titel{font:900 96px/1.02 Archivo,sans-serif;letter-spacing:-.01em;color:#F2F5F4}
.zeile{font:500 40px/1.3 'IBM Plex Sans',sans-serif;color:#C9D2CF}
.zeile.weiss{color:#F2F5F4}
.cta{font:600 40px/1.3 'IBM Plex Sans',sans-serif;color:#49EACB}
.raster{position:absolute}
.fuss{position:absolute;left:50%;transform:translateX(-50%);white-space:nowrap}
"""

FORMATE = {
    # x0, breite der texte; raster oben, links, breite, hoehe; fuss unten
    # gleiche rastergroesse in beiden formaten, damit der weisse punkt im reel
    # und im karussell an derselben stelle sitzt
    "reel": {"w": 1080, "h": 1920, "x": 60, "tb": 840, "kopf": 280, "zeile": 40,
             "r": (740, 60, 840, 690), "fuss": 1448},
    "folie": {"w": 1080, "h": 1350, "x": 72, "tb": 936, "kopf": 72, "zeile": 36,
              "r": (410, 120, 840, 690), "fuss": 1218},
}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def seite(d, art, markiert=False):
    import look_takt
    import wortmarke
    f = FORMATE[art]
    t = texte(d)
    oben, links, rb, rh = f["r"]
    svg, info = punkte_svg(d["rohzahl"], rb, rh, d["weiss"], markiert)
    css = (look_takt.schriften_css() + CSS + "body{width:%dpx;height:%dpx}" % (f["w"], f["h"])
           + wortmarke.css(groesse=40, sperrung=5, look="dunkel") + ".zeile,.cta{font-size:%dpx}" % f["zeile"])
    sp = "left:%dpx;width:%dpx" % (f["x"], f["tb"])
    if not markiert:
        kopf = ["<div class='t titel' data-rolle='titel'>%s</div>" % esc(t["titel"]),
                "<div class='t zeile'>%s</div>" % esc(t["zeile1"]),
                "<div class='t zeile weiss'>%s</div>" % esc(t["zeile2"])]
    else:
        kopf = ["<div class='t zeile weiss' style='font-size:44px'>%s</div>" % esc(t["f2_zeile1"]),
                "<div class='t zeile' style='font-size:44px'>%s</div>" % esc(t["f2_zeile2"])]
    teile = ["<div class='kopf' style='top:%dpx;%s'>%s</div>" % (f["kopf"], sp, "".join(kopf))]
    teile.append("<div class='raster' style='top:%dpx;left:%dpx'>%s</div>" % (oben, links, svg))
    if markiert:
        teile.append("<div class='t cta' style='top:%dpx;%s'>%s</div>" % (oben + rh + 16, sp, esc(t["cta"])))
    teile.append("<div class='fuss' data-rolle='fuss' style='top:%dpx'>%s</div>" % (f["fuss"], wortmarke.html()))
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>"
            % (css, "".join(teile)))
    info.update({"x": info["x"] + links, "y": info["y"] + oben})
    return html, info


UEBERLAPP_JS = """() => {
  const aus = [];
  const ts = [...document.querySelectorAll('.t, .fuss')].map(e => [e.className, e.getBoundingClientRect()]);
  const r = document.querySelector('.raster').getBoundingClientRect();
  for (const [n, a] of ts) {
    if (a.left < r.right && r.left < a.right && a.top < r.bottom && r.top < a.bottom) aus.push(n + ' liegt auf dem raster (' + Math.round(a.bottom) + ' > ' + Math.round(r.top) + ')');
    if (a.right > innerWidth - 59 || a.left < 59) aus.push(n + ' reicht in den rand');
  }
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i][1], b = ts[j][1];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) aus.push('texte ueberlappen');
  }
  return aus;
}"""


def rendern(d, ziel):
    from playwright.sync_api import sync_playwright
    import content_wache
    import tagesgrafik as tg
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    stamm = d["datum"].isoformat()
    plan = [("reel", False, "story", ziel / ("suchbild-%s-reel.png" % stamm)),
            ("folie", False, "instagram", ziel / ("suchbild-%s-01.png" % stamm)),
            ("folie", True, "instagram", ziel / ("suchbild-%s-02.png" % stamm))]
    aus = {}
    with sync_playwright() as pw:
        b = tg.chromium_start(pw)
        try:
            for art, markiert, kanal, png in plan:
                html, info = seite(d, art, markiert)
                datei = png.with_suffix(".html")
                datei.write_text(html, encoding="utf-8")
                f = FORMATE[art]
                pg = b.new_page(viewport={"width": f["w"], "height": f["h"]}, device_scale_factor=1)
                try:
                    pg.goto(datei.resolve().as_uri())
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(200)
                    fehler = pg.evaluate(UEBERLAPP_JS)
                    if fehler:
                        raise Stopp("%s, %s" % (png.name, "; ".join(fehler)))
                    pg.screenshot(path=str(png))
                    v = content_wache.pruefe_seite(pg, kanal, png)
                    if v:
                        raise Stopp("%s, wache, %s" % (png.name, "; ".join(v)))
                finally:
                    pg.close()
                    datei.unlink()
                aus[png.name] = info
        finally:
            b.close()
    return aus


def video(png, musik, mp4, sekunden=SEKUNDEN):
    """Standbild mit Musik, Ein- und Ausblenden, Lautheit fuer Reels."""
    if not Path(musik).is_file():
        raise Stopp("musik fehlt, %s" % musik)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
           "-i", str(musik), "-t", str(sekunden),
           "-filter_complex",
           "[1:a]atrim=0:%d,afade=t=in:d=1,afade=t=out:st=%d:d=1.5,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
           % (sekunden, sekunden - 1.5),
           "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
           "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(mp4)]
    subprocess.run(cmd, check=True)
    return mp4


def zahl(a):
    if a.lauf:
        d = aus_log(a.lauf)
    elif a.rohzahl and a.fenster and a.datum:
        d = {"rohzahl": int(a.rohzahl), "fenster": float(a.fenster), "datum": dt.date.fromisoformat(a.datum)}
    else:
        raise Stopp("ohne --lauf oder --rohzahl/--fenster/--datum keine zahl, nicht raten")
    if not 1000 < d["rohzahl"] < 20000:
        raise Stopp("rohzahl %d unplausibel" % d["rohzahl"])
    sp, ze = raster(d["rohzahl"], *FORMATE["reel"]["r"][2:])
    d["weiss"] = versteck(d["rohzahl"], sp, ze, d["datum"].isoformat())
    return d


# ------------------------------------------------------------ selbsttest

def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    log = [{"datum": "2026-10-21", "messwerte": {"bps": 9.962, "blockrate_sek": 600}},
           {"datum": "2026-10-28", "messwerte": {"bps": 9.96, "daa_zuwachs": 5978, "fenster_sek": 600.12}}]
    try:
        aus_log("2026-10-21", log)
        ok("ohne rohzahl im log stopp", False)
    except Stopp as e:
        ok("ohne rohzahl im log stopp", "nicht raten" in str(e))
    d = aus_log("2026-10-28", log)
    ok("rohzahl und fenster aus dem log", d["rohzahl"] == 5978 and d["fenster"] == 600.12)
    for n in (5978, 6059, 6001):
        for art in FORMATE:
            sp, ze = raster(n, *FORMATE[art]["r"][2:])
            ok("raster %d in %s hat platz fuer alle, ohne leere zeile" % (n, art),
               sp * ze >= n and (ze - 1) * sp < n)
    sp, ze = raster(5978, 840, 690)
    w = versteck(5978, sp, ze, "2026-10-28")
    s, z = w % sp, w // sp
    ok("versteck nicht am rand", 0.11 * sp <= s < 0.89 * sp and 0.11 * ze <= z < 0.89 * ze)
    ok("versteck nicht in der mitte", not (abs(s - (sp - 1) / 2) < sp / 6 and abs(z - (ze - 1) / 2) < ze / 6))
    ok("versteck fest aus der saat", versteck(5978, sp, ze, "2026-10-28") == w)
    svg, info = punkte_svg(5978, 840, 690, w)
    ok("genau so viele punkte wie gezaehlt, einer davon weiss",
       svg.count("<circle") == 5978 and svg.count(WEISS) == 1)
    ok("punkt bei 390 px breite mindestens 2 px", info["radius"] * 2 * 390 / 1080 >= 2)
    t = texte({"rohzahl": 5978, "fenster": 600.12, "datum": dt.date(2026, 10, 28)})
    ok("zeile 1 wortgleich nach auftrag", t["zeile1"] == "5,978 kaspa blocks in 600.1 s, counted, 28 oct 2026")
    ok("folie 2 rate aus rohzahl und fenster", t["f2_zeile1"] == "9.961 blocks a second, counted, 28 oct 2026")
    ok("textregeln gruen", pruefen(t) == [])
    t2 = dict(t, zeile2="kaspa is faster than bitcoin")
    ok("werturteil faellt auf", any("werturteil" in x for x in pruefen(t2)))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("was", nargs="?", choices=["bauen"])
    ap.add_argument("--lauf")
    ap.add_argument("--rohzahl")
    ap.add_argument("--fenster")
    ap.add_argument("--datum")
    ap.add_argument("--ziel", default="out/suchbild")
    ap.add_argument("--musik")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.was != "bauen":
        ap.error("bauen oder --selbsttest")
    d = zahl(a)
    t = texte(d)
    fehler = pruefen(t)
    if fehler:
        raise Stopp("; ".join(fehler))
    infos = rendern(d, a.ziel)
    for name, i in infos.items():
        print("%s, %d x %d punkte, schritt %.1f px, weisser punkt bei %.0f/%.0f"
              % (name, i["spalten"], i["zeilen"], i["schritt"], i["x"], i["y"]))
    if a.musik:
        reel = Path(a.ziel) / ("suchbild-%s-reel.png" % d["datum"].isoformat())
        mp4 = Path(a.ziel) / ("suchbild-%s-reel.mp4" % d["datum"].isoformat())
        video(reel, a.musik, mp4)
        print(mp4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
