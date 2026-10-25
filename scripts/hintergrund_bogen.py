#!/usr/bin/env python3
"""hintergrund_bogen.py, Kontaktbogen der Bildhintergruende (Ben, 25.10.2026).

Baut mit den echten Generatoren und durch alle Wachen (Groessen, Rand, Text,
Kontrast 7:1):

  raster   das Instagram-Profil als 9er-Raster, so wie Instagram es zeigt:
           drei Spalten, das Neueste oben links, jedes Bild als 3:4-Ausschnitt
           der 4:5-Grafik. Die Folge ab Mi 28.10.2026 mit Look und Motiv aus
           dem Look-Takt (eine Kopie von data/look-takt.json, nichts wird
           gemerkt). Die Inhalte sind Beispiele aus den Selbsttests.
  story    die Story-Vorlagen Mi bis Sa mit ihren Motiven.
  matrix   jedes Motiv in jedem Look, auf einer Tagesgrafik, einer Zahl des
           Tages, einer Karussellseite und einer Story.

    python3 scripts/hintergrund_bogen.py --out docs/hintergruende
"""
import argparse
import base64
import copy
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))


def _png_html(png, breite, ausschnitt=False):
    d = base64.b64encode(Path(png).read_bytes()).decode()
    if not ausschnitt:
        return "<img src='data:image/png;base64,%s' style='width:%dpx;display:block'>" % (d, breite)
    # 3:4 aus 4:5, mittig, wie das profilraster seit 2025
    hoehe = round(breite * 4 / 3)
    return ("<div style='width:%dpx;height:%dpx;overflow:hidden;position:relative'><img src='data:image/png;"
            "base64,%s' style='width:%dpx;position:absolute;top:%dpx'></div>"
            % (breite, hoehe, d, breite, -round((breite * 1350 / 1080 - hoehe) / 2)))


def bogen(b, zellen, ziel, spalten, breite, ausschnitt=False, abstand=3, titel=""):
    teile = []
    for png, text in zellen:
        teile.append("<div style='width:%dpx'>%s<div style='font:13px sans-serif;color:#bbb;padding:4px 2px 8px'>"
                     "%s</div></div>" % (breite, _png_html(png, breite, ausschnitt), text))
    w = spalten * (breite + abstand) + abstand
    pg = b.new_page(viewport={"width": w, "height": 100})
    try:
        pg.set_content("<body style='margin:0;background:#121212;width:%dpx'>%s<div style='display:grid;"
                       "grid-template-columns:repeat(%d,%dpx);gap:%dpx;padding:%dpx'>%s</div></body>"
                       % (w, "<div style='font:15px sans-serif;color:#eee;padding:10px 8px 4px'>%s</div>" % titel
                          if titel else "", spalten, breite, abstand, abstand, "".join(teile)))
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(ziel), full_page=True)
    finally:
        pg.close()
    return Path(ziel)


def tg_bild(b, form, look, motiv, png):
    import hintergrund as hg
    import tagesgrafik as tg
    werte = tg.FAKE[form]
    if form == 7:
        werte = json.loads(json.dumps(werte))
        werte["eintrag"]["name"] = "#data-requests"
    s = tg.seite_bauen(form, werte, tg.FAKE_NOW, {"laeufe": []})
    tg.rendern(hg.setzen(tg.html(s, look), motiv, look), png, 0, b, "instagram")
    tg.look_setzen("dunkel")
    return png


def karussell_bilder(b, look, motiv, ziel, art):
    import hintergrund as hg
    import karussell
    import meme_wahr
    import tagesgrafik as tg
    if art == "woche":
        h = json.loads((REPO / "data" / "weekly-history.json").read_text(encoding="utf-8"))
        ss = karussell.seiten_woche(h[-1], h[-2])
        bau = karussell.seite_html
    elif art == "story":
        ss = karussell.seiten_story(karussell.PROBE_STORY)
        bau = karussell.seite_html
    else:
        ss = meme_wahr.seiten("2026-10-31", meme_wahr.zahl_seite2("crescendo", "2026-10-31"))
        bau = meme_wahr.seite_html
    aus = []
    for s in ss:
        png = Path(ziel) / ("%s-%d-%s-%s.png" % (art, s["seite"], look, motiv))
        tg.rendern(hg.setzen(bau(s, look), motiv, look), png, 0, b, "instagram")
        aus.append(png)
    return aus


def nod_bild(b, look, motiv, png):
    import hintergrund as hg
    import number_of_day as nod
    d = json.loads((REPO / "data" / "number-of-day.json").read_text(encoding="utf-8"))
    nod.shoot(hg.setzen(nod.render_html(d, look), motiv, look), png, b, "x")
    Path(png).with_suffix(".html").unlink(missing_ok=True)
    return png


def story_bilder(b, ziel, motive_fuer):
    """Die Vorlagen Mi bis Fr und die Aufloesung Sa, mit den Daten aus dem Repo."""
    import story_vorlage as sv
    tmp = Path(tempfile.mkdtemp())
    nod = json.loads((REPO / "data" / "number-of-day.json").read_text(encoding="utf-8"))
    nod["issue"] = "OCT 29 2026"
    (tmp / "n.json").write_text(json.dumps(nod), encoding="utf-8")
    (tmp / "l.json").write_text("{}", encoding="utf-8")
    (tmp / "p.json").write_text('{"wochen":{}}', encoding="utf-8")
    q = {"zitat": {"story": tmp / "l.json", "nod": tmp / "n.json"}}
    looks = {"mi": "teal", "do": "hell", "fr": "dunkel", "sa": "hell"}
    log, aus = {"tage": []}, []
    for d in ("2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31"):
        for s in (sv.aufloesung(d, log), sv.vorlage(d, tmp / "p.json", q)):
            if not s:
                continue
            sv.pruefen(s)
            motiv = motive_fuer(d)
            png = Path(ziel) / ("story-%s-%s-%s.png" % (d, s["art"], motiv))
            sv.rendern(s, looks[s["tag"]], png, b, motiv)
            aus.append((png, "%s %s, %s, %s" % (s["tag"], s["art"], looks[s["tag"]], motiv)))
            if s["art"] != "aufloesung":
                sv.log_merken(log, s)
    return aus


def raster_folge(sp):
    """Die Instagram-Posts ab Mi 28.10. in Rasterfolge, mit Look und Motiv."""
    import look_takt
    plan = [("2026-10-28", "tagesgrafik", "tagesgrafik f1"), ("2026-10-28", "karussell", "karussell story"),
            ("2026-10-29", "tagesgrafik", "tagesgrafik f5"), ("2026-10-30", "tagesgrafik", "tagesgrafik f3"),
            ("2026-10-31", "tagesgrafik", "tagesgrafik f6"), ("2026-10-31", "karussell", "karussell woche"),
            ("2026-10-31", "meme", "meme, but true"), ("2026-11-01", "tagesgrafik", "tagesgrafik f9"),
            ("2026-11-02", "tagesgrafik", "tagesgrafik f2")]
    folge = []
    for datum, serie, was in plan:
        look = look_takt.raster_faellig(sp, serie, datum)[1]
        motiv = look_takt.raster_motiv(sp, serie, datum)
        look_takt.raster_merken(sp, serie, datum)
        folge.append({"datum": datum, "serie": serie, "was": was, "look": look, "motiv": motiv})
    return folge


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/hintergruende")
    a = ap.parse_args(argv)
    import hintergrund as hg
    import look_takt
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="hg-bogen-"))
    sp = copy.deepcopy(look_takt.lesen())
    folge = raster_folge(sp)
    wt = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            zellen = []
            for i, x in enumerate(folge):
                png = tmp / ("raster-%d.png" % i)
                if x["serie"] == "tagesgrafik":
                    tg_bild(b, int(x["was"].rsplit(" f", 1)[1]), x["look"], x["motiv"], png)
                else:
                    art = "meme" if x["serie"] == "meme" else x["was"].split()[1]
                    png = karussell_bilder(b, x["look"], x["motiv"], tmp, art)[0]
                tag = dt.date.fromisoformat(x["datum"])
                zellen.append((png, "%s %s, %s<br>%s, %s" % (wt[tag.weekday()], tag.strftime("%d.%m."), x["was"],
                                                            x["look"], x["motiv"])))
            r = bogen(b, list(reversed(zellen)), out / "raster-ab-2026-10-28.png", 3, 300, ausschnitt=True,
                      titel="Instagram-Raster ab Mi 28.10.2026, neuestes oben links, 3:4-Ausschnitt wie im Profil")
            print("raster", r)
            feed_motiv = {x["datum"]: x["motiv"] for x in folge if x["serie"] == "tagesgrafik"}
            st = story_bilder(b, tmp, lambda d: hg.motiv_story(d, feed_motiv.get(d)))
            print("story", bogen(b, st, out / "story-ab-2026-10-28.png", 5, 220,
                                 titel="Story-Vorlagen Mi 28. bis Sa 31.10., je mit Motiv"))
            mz = []
            for i, m in enumerate(hg.MOTIVE):
                for lk in ("dunkel", "hell", "teal"):
                    mz.append((tg_bild(b, (2, 4, 1, 6, 3, 9, 5, 10)[i], lk, m, tmp / ("m-tg-%s-%s.png" % (m, lk))),
                               "tagesgrafik, %s, %s" % (lk, m)))
                    mz.append((nod_bild(b, lk, m, tmp / ("m-nod-%s-%s.png" % (m, lk))),
                               "zahl des tages, %s, %s" % (lk, m)))
                    mz.append((karussell_bilder(b, lk, m, tmp, ("woche", "story", "meme")[i % 3])[1],
                               "karussell, %s, %s" % (lk, m)))
            print("matrix", bogen(b, mz, out / "matrix-alle-motive.png", 6, 200,
                                  titel="Jedes Motiv in jedem Look, alle durch die Wachen (Kontrast 7:1)"))
        finally:
            b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
