#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ig_story_auto.py, eine einfache Instagram-Story am Dienstag und Donnerstag (Ben, 27.10.2026).

WARUM
Poll- und Quiz-Sticker kann die Instagram-API nicht setzen, eine einfache
Bild-Story schon. Mo, Mi und Fr macht Ben die interaktiven Stories von Hand,
Di und Do geht automatisch eine Story ohne Sticker raus. So bleibt der Account
jeden Tag aktiv, ohne Bens Zeit.

INHALT, ALS KOEDER (Ben, 27.10.2026, Nachtrag)
Keine flache Grafik, sondern ein Haken: oben in Sekunde null eine Frage, in
der Mitte die grosse Kernzahl als Antwort, darunter ihr Satz, Datum und
counted, source oder computed, unten "full breakdown on our profile". Ein
klickbarer Sticker geht ueber die API nicht, also soll die Story neugierig
machen und aufs Profil fuehren.
1. Quelle ist die Tagesgrafik des Tages (Zahl, Satz, Datum und Herkunft aus
   data/instagram-log.json, nur wenn sie um 07:30 ausgeliefert wurde). Die
   Frage kommt aus HAKEN, eine je Form, die Zahl beantwortet sie.
2. Gibt es heute keine, die Zahl des Tages (data/number-of-day.json vom selben
   Tag), mit "did you expect this number?" als Haken und "link in bio" unten.
Alles laeuft durch die Textregeln, die Kurs- und Koederwache der Story-Vorlage
und die content_wache im Profil "story" (sichere Flaeche, Mindestgroessen,
Kontrast). Marke dunkel: #080B0F, #F2F5F4, #49EACB, Wortmarke ohne Falken.
Kein Sticker, keine Caption.

MODI
probe     von Hand, jeder Tag: nur nach #moderator-only, nie zu Instagram
entwurf   Takt oder Zeitplan ohne IG_STORY_AUTO_LIVE=true: nur nach #moderator-only
scharf    Takt oder Zeitplan, IG_STORY_AUTO_LIVE=true, Di oder Do, zwischen 17:15
          und 19:30 Berlin, IG_STORY_AUTO_STOPP nicht auf heute oder "immer",
          heute noch keine Story in data/ig-story-auto-log.json (die Merkdatei)
aus       sonst, mit Grund im Log

GEHEIMNISSE nur aus der Umgebung (INSTAGRAM_PAGE_TOKEN, DISCORD_WEBHOOK_LOG),
jede Ausgabe laeuft durch instagram.sauber(). Keine Hostnamen im Log.

    python3 scripts/ig_story_auto.py planen --start probe|takt|geplant [--datum JJJJ-MM-TT]
    python3 scripts/ig_story_auto.py bauen --datum JJJJ-MM-TT --ziel out/story
    python3 scripts/ig_story_auto.py ops --modus probe|entwurf --info out/story/info.json
    python3 scripts/ig_story_auto.py posten --info out/story/info.json --jpeg ig/story-auto-JJJJ-MM-TT.jpg
    python3 scripts/ig_story_auto.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import instagram as ig  # noqa: E402

LOG_IG = REPO / "data" / "instagram-log.json"
LOG_GRAFIK = REPO / "data" / "tagesgrafik-log.json"
NOD_JSON = REPO / "data" / "number-of-day.json"
NOD_PNG = REPO / "graphics" / "number-of-day.png"
MERK = REPO / "data" / "ig-story-auto-log.json"
TAGE = (1, 3)                              # dienstag, donnerstag
POSTZEIT = "17:30"
FENSTER = ((17, 15), (19, 30))            # berlin, nur fuer scharf
W, H = 1080, 1920
LOOK = "dunkel"                            # die marke: #080B0F, #F2F5F4, #49EACB
CTA_PROFIL = "full breakdown on our profile"
CTA_BIO = "more numbers like this, link in bio"
HAKEN_NOD = "did you expect this number?"
# eine frage je form der tagesgrafik, die grosse zahl ist die antwort
HAKEN = {
    1: "how did kaspa move this week?",
    2: "how much KAS sits in the single largest wallet?",
    3: "when do kaspa miners get paid less again?",
    4: "how many blocks does kaspa add while you sleep?",
    5: "what actually pays kaspa miners?",
    6: "how far has the kaspa chain come since nov 2021?",
    7: "you asked us to count this. guess first?",
    8: "how much computing power guards kaspa?",
    9: "how many wallets hold a real stake?",
    10: "how much of all KAS is already mined?",
    11: "how much KAS has not moved in a year?",
}
MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
WOCHENTAG = ("mo", "di", "mi", "do", "fr", "sa", "so")
DATUM = re.compile(r"\b\d{1,2} (?:%s)\b" % "|".join(MONATE))
HERKUNFT = re.compile(r"\b(counted|source|computed)\b")


class Stopp(Exception):
    pass


def ausgabe(*t):
    ig.ausgabe(*t)


def ausgang(**kw):
    """Werte fuer die naechsten Schritte im Workflow."""
    pfad = os.environ.get("GITHUB_OUTPUT")
    for k, v in kw.items():
        ausgabe("%s=%s" % (k, v))
        if pfad:
            with open(pfad, "a", encoding="utf-8") as fh:
                fh.write("%s=%s\n" % (k, v))


def ohne_host(t):
    """api.kaspa.org und coingecko.com stehen in der Quelle der Zahl des Tages.
    Im Log und im Ops-Kanal stehen nur die Namen."""
    for host, name in (("api.kaspa.org", "kaspa rest api"), ("coingecko.com", "coingecko"),
                       ("kaspalytics.com", "kaspalytics"), ("api.llama.fi", "defillama")):
        t = t.replace(host, name)
    return re.sub(r"\b(?:api\.)?([a-z0-9-]+)\.(?:com|org|io|net|fi)\b", r"\1", t)


def heute_berlin(now):
    return ig.berlin(now).date()


# ---------------------------------------------------------------- planen

def planen(start, now, live="", stopp="", merk=None, datum=None):
    """(modus, grund, datum). modus ist probe, entwurf, scharf oder aus."""
    b = ig.berlin(now)
    tag = datum or b.date()
    if start == "probe":
        return "probe", "von hand, nur nach #moderator-only", tag
    if tag.weekday() not in TAGE:
        return "aus", "%s ist kein dienstag oder donnerstag" % tag.isoformat(), tag
    if stopp.strip() in (tag.isoformat(), "immer"):
        return "aus", "IG_STORY_AUTO_STOPP steht auf %s" % stopp.strip(), tag
    import look_takt
    scharf = live.strip().lower() == "true" and not look_takt.trockenlauf()
    if not scharf:
        return "entwurf", "IG_STORY_AUTO_LIVE ist nicht true, nur nach #moderator-only", tag
    (h0, m0), (h1, m1) = FENSTER
    if not (h0, m0) <= (b.hour, b.minute) < (h1, m1):
        return "aus", "%02d:%02d berlin liegt nicht zwischen %02d:%02d und %02d:%02d, verspaetet wird nie gepostet" % (
            b.hour, b.minute, h0, m0, h1, m1), tag
    if any(e.get("datum") == tag.isoformat() and e.get("media") for e in (merk or {}).get("stories", [])):
        return "aus", "heute (%s) ist schon eine story draussen" % tag.isoformat(), tag
    return "scharf", "live, %s, im fenster" % WOCHENTAG[tag.weekday()], tag


# ---------------------------------------------------------------- quelle

def nod_datum(issue):
    """'OCT 27 2026' -> date"""
    m = re.fullmatch(r"([A-Za-z]{3}) (\d{1,2}) (\d{4})", (issue or "").strip())
    if not m or m.group(1).lower() not in MONATE:
        return None
    return dt.date(int(m.group(3)), MONATE.index(m.group(1).lower()) + 1, int(m.group(2)))


def quelle(tag, log_ig, log_grafik, nod, repo=REPO):
    """Was heute in die Story kommt: dict mit art, bild, zahl, datum, herkunft."""
    t = tag.isoformat()
    ausgeliefert = any(e.get("datum") == t and e.get("messzeit_utc") for e in log_grafik.get("laeufe", []))
    for p in reversed(log_ig.get("posts", [])):
        if p.get("datum") != t or not p.get("bild") or not ausgeliefert:
            continue
        datei = repo / "ig" / Path(p["bild"]).name
        if datei.exists() and p.get("zahl") and p.get("tag") and p.get("herkunft"):
            form = int(p.get("form") or 0)
            if form not in HAKEN:
                break
            return {"art": "tagesgrafik", "form": form, "haken": HAKEN[form], "kern": p["zahl"],
                    "zahl": p.get("zahl_text") or p["zahl"], "datum": p["tag"], "herkunft": p["herkunft"],
                    "cta": CTA_PROFIL}
    if nod and nod_datum(nod.get("issue")) == tag:
        d = nod_datum(nod["issue"])
        satz = " ".join(nod.get("headline", "").replace("*", "").split())
        hervor = re.search(r"\*([^*]+)\*", nod.get("headline", ""))
        return {"art": "zahl des tages", "form": None, "haken": HAKEN_NOD,
                "kern": hervor.group(1) if hervor else nod.get("value", ""),
                "zahl": satz or "%s %s" % (nod.get("value", ""), nod.get("value_label", "")), "cta": CTA_BIO,
                "datum": "%d %s %d" % (d.day, MONATE[d.month - 1], d.year),
                "herkunft": "source " + ohne_host(nod.get("sources", ""))}
    raise Stopp("heute (%s) weder tagesgrafik noch zahl des tages, keine story" % t)


def pruefen(q):
    """Eine Zahl mit Datum und counted, source oder computed, Textregeln."""
    import content_wache
    fehler = []
    if not re.search(r"\d", q["zahl"]):
        fehler.append("keine zahl")
    if not DATUM.search(q["datum"]):
        fehler.append("kein datum")
    if not HERKUNFT.search(q["herkunft"]):
        fehler.append("weder counted noch source noch computed")
    if not re.search(r"\d", q.get("kern", "")):
        fehler.append("keine grosse zahl")
    if not q.get("haken", "").endswith("?"):
        fehler.append("haken ist keine frage")
    import story_vorlage as sv
    for feld in ("haken", "kern", "zahl", "herkunft", "cta"):
        for v in content_wache.text_verstoesse(q.get(feld, "")):
            fehler.append("%s, %s" % (feld, v))
        if sv.KURS.search(q.get(feld, "")):
            fehler.append("%s, kurs oder kaufsprache" % feld)
        if sv.KOEDER.search(q.get(feld, "")):
            fehler.append("%s, billiger koeder" % feld)
    if re.search(r"\b(target|kaufen|verkaufen)\b", " ".join(q.get(k, "") for k in ("haken", "zahl", "cta")), re.I):
        fehler.append("kaufsprache oder kursziel")
    return fehler


# ---------------------------------------------------------------- bild

def kern_teilen(kern):
    """"51.20%" -> ("51.20", "%"), "14 days" -> ("14", "days"), "574M" -> ("574", "M").
    Die Einheit steht klein neben der Zahl, so passt die Zahl in 220 px."""
    m = re.match(r"^\s*([+\-\u2212]?[\d.,]*\d)\s*(.*)$", kern)
    return (m.group(1), m.group(2).strip()) if m else (kern, "")


def kurz(kern):
    """Zahlen ab 5 Stellen passen nicht in 220 px: 287,000 -> 287K, 294,512 -> 294.5K.
    Die genaue Zahl steht dann im Satz darunter."""
    zahl, einheit = kern_teilen(kern)
    roh = zahl.replace(",", "")
    if not re.fullmatch(r"\d{5,}", roh):
        return kern
    n = int(roh)
    for teiler, z in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= teiler:
            w = ("%.1f" % (n / teiler)).rstrip("0").rstrip(".")
            return (w + z + ((" " + einheit) if einheit else "")).strip()
    return kern


def satz_ohne_kern(q):
    """Der Satz unter der Zahl, ohne die Zahl am Anfang zu wiederholen."""
    z, k = q["zahl"], q["kern"]
    return z[len(k):].strip(" ,") if z.startswith(k) and len(z) > len(k) else z


def datumszeile(q):
    h = q["herkunft"].rstrip(" .")
    return h if DATUM.search(h) else "%s \u00b7 %s" % (q["datum"], h)


CSS = """
body{margin:0;width:1080px;height:1920px;background:%(grund)s;color:%(text)s;overflow:hidden}
.feld{position:absolute;left:60px;top:276px;width:840px;height:1220px;display:flex;flex-direction:column}
.haken{font:900 80px/1.06 Archivo,sans-serif;letter-spacing:-.01em;text-wrap:balance}
.zahl{font:900 220px/1 Archivo,sans-serif;color:%(akzent)s;letter-spacing:-.02em;white-space:nowrap}
.einheit{font:900 110px/1 Archivo,sans-serif;color:%(akzent)s;margin-left:10px;letter-spacing:-.01em}
.satz{font:600 48px/1.22 "IBM Plex Sans",sans-serif;margin-top:26px;text-wrap:balance}
.datum{font:400 40px/1.35 "IBM Plex Mono",monospace;color:%(text2)s;margin-top:30px}
.luft{flex:1;min-height:60px}
.luft.unten{flex:1.3}
.cta{font:600 44px/1.2 "IBM Plex Sans",sans-serif;color:%(akzent)s;border-top:3px solid %(akzent)s;padding-top:26px}
.marke{margin-top:30px}
"""


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def seite_html(q):
    import look_takt
    import wortmarke
    lk = look_takt.look(LOOK)
    css = (look_takt.schriften_css()
           + CSS % {"grund": lk["grund"], "text": lk["text"], "text2": lk["text2"], "akzent": lk["akzent"]}
           + wortmarke.css(groesse=44, sperrung=5, look=LOOK))
    gross = kurz(q["kern"])
    zahl, einheit = kern_teilen(gross)
    satz = satz_ohne_kern(q) if gross == q["kern"] else q["zahl"]
    teile = ["<div class='haken' data-rolle='titel'>%s</div>" % esc(q["haken"]),
             "<div class='luft'></div>",
             "<div class='zahl' data-rolle='zahl'>%s%s</div>" % (
                 esc(zahl), "<span class='einheit' data-rolle='einheit'>%s</span>" % esc(einheit) if einheit else ""),
             "<div class='satz'>%s</div>" % esc(satz),
             "<div class='datum'>%s</div>" % esc(datumszeile(q)),
             "<div class='luft unten'></div>",
             "<div class='cta'>%s</div>" % esc(q["cta"]),
             "<div class='marke' data-rolle='fuss'>%s</div>" % wortmarke.html()]
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'><div class='feld'>%s</div></body></html>" % (css, LOOK, "".join(teile)))


PASSEN_JS = """() => {
  const z = document.querySelector('.zahl'), feld = document.querySelector('.feld'), aus = [];
  if (z.scrollWidth > 840) aus.push('zahl ist ' + z.scrollWidth + ' px breit, hoechstens 840');
  if (feld.scrollHeight > feld.clientHeight + 1) aus.push('inhalt ' + (feld.scrollHeight - feld.clientHeight) + ' px zu hoch');
  if (document.querySelector('.luft.unten').getBoundingClientRect().height < 40) aus.push('keine luft vor der zeile unten');
  return aus;
}"""


def rendern(q, png, browser=None):
    """PNG mit Playwright, Layout und content_wache im Profil story, dann JPEG daneben."""
    if browser is None:
        from playwright.sync_api import sync_playwright
        import tagesgrafik as tg
        with sync_playwright() as pw:
            b = tg.chromium_start(pw)
            try:
                return rendern(q, png, b)
            finally:
                b.close()
    import content_wache
    png = Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    html = png.with_suffix(".html")
    html.write_text(seite_html(q), encoding="utf-8")
    pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    try:
        pg.goto(html.resolve().as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        fehler = pg.evaluate(PASSEN_JS)
        if fehler:
            raise Stopp("layout, %s" % "; ".join(fehler))
        pg.screenshot(path=str(png))
        verstoesse = content_wache.pruefe_seite(pg, "story", png)
        if verstoesse:
            raise Stopp("wache, %s" % "; ".join(verstoesse))
    finally:
        pg.close()
        html.unlink()
    return png


def als_jpeg(png, jpeg):
    from PIL import Image
    Path(jpeg).parent.mkdir(parents=True, exist_ok=True)
    Image.open(png).convert("RGB").save(jpeg, "JPEG", quality=92, optimize=True)
    return Path(jpeg)


def bauen(tag, ziel, repo=REPO):
    q = quelle(tag, ig.json_laden(LOG_IG, {}), ig.json_laden(LOG_GRAFIK, {}), ig.json_laden(NOD_JSON, {}), repo)
    f = pruefen(q)
    if f:
        raise Stopp("story nicht gruen, %s" % "; ".join(f))
    jpeg = Path(repo) / "ig" / ("story-auto-%s.jpg" % tag.isoformat())
    png = rendern(q, Path(ziel) / ("story-auto-%s.png" % tag.isoformat()))
    als_jpeg(png, jpeg)
    info = dict(q, datum_tag=tag.isoformat(), jpeg=str(jpeg.relative_to(repo)))
    Path(ziel).mkdir(parents=True, exist_ok=True)
    ig.json_schreiben(Path(ziel) / "info.json", info)
    ausgabe("story gebaut, %s, %s" % (info["art"], info["jpeg"]))
    return info


# ---------------------------------------------------------------- ops

def ops_text(modus, info):
    tag = dt.date.fromisoformat(info["datum_tag"])
    kopf = {"probe": "PROBE ig-story, nicht oeffentlich",
            "entwurf": "ENTWURF ig-story, nicht oeffentlich",
            "scharf": "IG-STORY ist draussen"}[modus]
    zeilen = ["%s, %s %s" % (kopf, WOCHENTAG[tag.weekday()], tag.strftime("%d.%m.%Y")),
              "quelle %s%s" % (info["art"], (", form %s" % info["form"]) if info.get("form") else ""),
              "haken %s" % info["haken"],
              "zahl %s, %s, %s" % (info["zahl"], info["datum"], info["herkunft"]),
              "unten %s, kein sticker, keine caption" % info["cta"]]
    if modus != "scharf":
        zeilen.append("geht di und do um %s berlin raus, aber nur mit IG_STORY_AUTO_LIVE=true. "
                      "veto mit IG_STORY_AUTO_STOPP auf %s oder immer" % (POSTZEIT, info["datum_tag"]))
    return ohne_host("\n".join(zeilen))


def ops_senden(text, bild):
    """Probe, Entwurf und Bestaetigung zur Info nach #ops-log (Art "log" in
    scripts/ops_melden.py). Die Story geht automatisch raus, Ben muss nichts tun."""
    import ops_melden
    return ops_melden.log(ig.sauber(text), [(bild, "image/jpeg")] if bild else None, "ig-story")


# ---------------------------------------------------------------- posten

def posten(info, jpeg, warte_takt=10, warte_max=300, warten=True):
    """Story-Container, Status, veroeffentlichen. Nur aus dem scharfen Lauf."""
    url = "%s/ig/%s" % (ig.SEITE, Path(jpeg).name)
    if warten:
        ig.url_warten(url, Path(jpeg).stat().st_size)
    u = ig.ig_user()
    c = ig.graph("POST", "%s/media" % u, {"image_url": url, "media_type": "STORIES"})
    cid = str(c.get("id", ""))
    if not re.fullmatch(r"\d+", cid):
        raise Stopp("container ohne id")
    status, ende = "", time.time() + warte_max
    while time.time() < ende:
        status = ig.graph("GET", cid, {"fields": "status_code"}).get("status_code", "")
        ausgabe("container %s, status %s" % (cid, status))
        if status in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED"):
            break
        time.sleep(warte_takt)
    if status != "FINISHED":
        raise Stopp("container %s endet mit status %s, keine story" % (cid, status or "-"))
    m = ig.graph("POST", "%s/media_publish" % u, {"creation_id": cid})
    media = str(m.get("id", ""))
    merk = ig.json_laden(MERK, {"stories": []})
    merk.setdefault("stories", []).append({
        "datum": info["datum_tag"], "art": info["art"], "form": info.get("form"), "container": cid,
        "media": media, "zeit_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    ig.json_schreiben(MERK, merk)
    ausgabe("story veroeffentlicht, media %s" % media)
    return media


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import tempfile
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    utc = dt.timezone.utc
    di = dt.datetime(2026, 10, 27, 16, 30, tzinfo=utc)          # 17:30 berlin, dienstag
    mi = dt.datetime(2026, 10, 28, 16, 30, tzinfo=utc)
    spaet = dt.datetime(2026, 10, 27, 22, 40, tzinfo=utc)       # cron sechs stunden zu spaet
    ok("probe an jedem tag", planen("probe", mi)[0] == "probe")
    ok("mittwoch aus", planen("takt", mi, "true")[0] == "aus")
    ok("ohne live nur entwurf", planen("takt", di, "")[0] == "entwurf")
    ok("live im fenster scharf", planen("takt", di, "true")[0] == "scharf")
    ok("verspaetet nie scharf", planen("geplant", spaet, "true")[0] == "aus")
    ok("veto heute", planen("takt", di, "true", "2026-10-27")[0] == "aus")
    ok("veto immer", planen("takt", di, "true", "immer")[0] == "aus")
    ok("veto anderer tag stoert nicht", planen("takt", di, "true", "2026-10-29")[0] == "scharf")
    ok("merkdatei, nur eine story je tag",
       planen("takt", di, "true", merk={"stories": [{"datum": "2026-10-27", "media": "1"}]})[0] == "aus")
    ok("versuch ohne media sperrt nicht",
       planen("takt", di, "true", merk={"stories": [{"datum": "2026-10-27", "media": ""}]})[0] == "scharf")
    ok("winterzeit 16:30 utc ist 17:30 berlin", ig.berlin(di).strftime("%H:%M") == "17:30")
    ok("nod-datum", nod_datum("OCT 27 2026") == dt.date(2026, 10, 27) and nod_datum("x") is None)
    ok("ohne host, mit namen", ohne_host("source api.kaspa.org and coingecko.com") == "source kaspa rest api and coingecko"
       and ohne_host("source example.com") == "source example")

    with tempfile.TemporaryDirectory() as d:
        from PIL import Image
        r = Path(d)
        (r / "ig").mkdir()
        (r / "graphics").mkdir()
        Image.new("RGB", (1080, 1350), (242, 245, 244)).save(r / "ig" / "tagesgrafik-2026-10-27-form11.jpg")
        Image.new("RGB", (1080, 1350), (8, 11, 15)).save(r / "graphics" / "number-of-day.png")
        log_ig = {"posts": [{"datum": "2026-10-27", "form": 11, "bild": "https://x/ig/tagesgrafik-2026-10-27-form11.jpg",
                             "zahl": "943x", "zahl_text": "943x more KAS for miners from new coins than from fees",
                             "tag": "12 oct 2026", "herkunft": "source kaspalytics fees, kaspa emission schedule"}]}
        log_g = {"laeufe": [{"datum": "2026-10-27", "messzeit_utc": "2026-10-27T06:30:44+00:00"}]}
        nod = {"issue": "OCT 27 2026", "value": "$61.6K", "value_label": "of new kaspa supply each day",
               "headline": "bitcoin prints *583x*\nmore supply each day.", "sources": "api.kaspa.org and coingecko.com"}
        tag = dt.date(2026, 10, 27)
        q = quelle(tag, log_ig, log_g, nod, r)
        ok("tagesgrafik zuerst, mit haken der form", q["art"] == "tagesgrafik" and q["form"] == 11
           and q["haken"] == HAKEN[11] and q["cta"] == CTA_PROFIL)
        ok("tagesgrafik gruen", pruefen(q) == [], pruefen(q))
        q2 = quelle(tag, {"posts": []}, log_g, nod, r)
        ok("sonst zahl des tages, kern aus der ueberschrift, nicht der dollarwert",
           q2["art"] == "zahl des tages" and q2["datum"] == "27 oct 2026" and q2["kern"] == "583x"
           and q2["zahl"] == "bitcoin prints 583x more supply each day." and q2["cta"] == CTA_BIO, q2)
        ok("zahl des tages gruen, ohne host", pruefen(q2) == [] and "." not in q2["herkunft"], (pruefen(q2), q2))
        ok("grafik ohne auslieferung zaehlt nicht", quelle(tag, log_ig, {"laeufe": []}, nod, r)["art"] == "zahl des tages")
        try:
            quelle(dt.date(2026, 10, 29), log_ig, log_g, nod, r)
            ok("ohne beides stopp", False)
        except Stopp:
            ok("ohne beides stopp", True)
        ok("echtzeitwort faellt auf", pruefen(dict(q, zahl="943x more KAS right now")) != [])
        ok("ohne herkunft faellt auf", pruefen(dict(q, herkunft="kaspalytics")) != [])
        ok("ohne datum faellt auf", pruefen(dict(q, datum="gestern")) != [])
        ok("kaufsprache faellt auf", pruefen(dict(q, zahl="943x, buy now")) != [])
        ok("dollar faellt auf", pruefen(dict(q, kern="$61.6K")) != [])
        ok("billiger koeder faellt auf", pruefen(dict(q, haken="the secret number nobody tells you?")) != [])
        ok("haken ohne frage faellt auf", pruefen(dict(q, haken="kaspa numbers")) != [])
        ok("jede form hat eine gruene frage", all(pruefen(dict(q, haken=h)) == [] for h in HAKEN.values()),
           [h for h in HAKEN.values() if pruefen(dict(q, haken=h))])
        ok("kern teilen", kern_teilen("51.20%") == ("51.20", "%") and kern_teilen("14 days") == ("14", "days")
           and kern_teilen("+0.7%") == ("+0.7", "%") and kern_teilen("574M") == ("574", "M"))
        ok("grosse zahlen kurz", kurz("287,000") == "287K" and kurz("294,512") == "294.5K"
           and kurz("51.20%") == "51.20%" and kurz("14 days") == "14 days" and kurz("1,234") == "1,234")
        h4 = seite_html(dict(q, kern="287,000", zahl="287,000 blocks while you slept"))
        ok("gekuerzt, genaue zahl im satz", ">287<" in h4 and "287,000 blocks while you slept" in h4)
        ok("satz ohne doppelte zahl", satz_ohne_kern(q) == "more KAS for miners from new coins than from fees")
        ok("datumszeile mit datum vorn, wenn die herkunft keins hat",
           datumszeile(q) == "12 oct 2026 \u00b7 source kaspalytics fees, kaspa emission schedule")
        h = seite_html(q)
        ok("seite hat haken, zahl, cta und wortmarke, keinen falken",
           HAKEN[11] in h and ">943<" in h and CTA_PROFIL in h and "data-rolle='fuss'" in h
           and "falke" not in h.lower() and "hawk" not in h.lower())
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            png = rendern(q, r / "out" / "story.png")
            b = Image.open(als_jpeg(png, r / "ig" / "story-auto-2026-10-27.jpg"))
            ok("gerendert 1080 x 1920, wache im profil story gruen", b.size == (1080, 1920))
            ok("grund dunkel wie die marke", sum(b.getpixel((5, 5))) < 60, b.getpixel((5, 5)))
        except ImportError:
            print("--   playwright fehlt, rendern hier nicht geprueft (im workflow installiert)")

    t = ops_text("entwurf", {"datum_tag": "2026-10-27", "art": "zahl des tages", "form": None,
                             "zahl": "bitcoin prints 583x more supply each day.", "haken": HAKEN_NOD, "cta": CTA_BIO,
                             "datum": "27 oct 2026", "herkunft": "source kaspa rest api and coingecko"})
    ok("ops nennt tag, haken, quelle, veto und live", "di 27.10.2026" in t and "IG_STORY_AUTO_STOPP" in t
       and HAKEN_NOD in t
       and "IG_STORY_AUTO_LIVE=true" in t and "17:30" in t)
    ok("ops ohne hostnamen", not re.search(r"\b[a-z0-9-]+\.(com|org|io|net)\b", t))

    # posten: graph ersetzt, token nur im kopf, media_type STORIES, merkdatei
    aufrufe = []
    geheim = "EA" + "B" * 30
    os.environ["INSTAGRAM_PAGE_TOKEN"] = geheim
    os.environ["IG_USER_ID"] = "17841400000000000"

    def falsch(methode, pfad, params=None, versuche=3):
        aufrufe.append((methode, pfad, dict(params or {})))
        if pfad.endswith("/media"):
            return {"id": "111"}
        if pfad.endswith("/media_publish"):
            return {"id": "222"}
        return {"status_code": "FINISHED"}
    alt_graph, alt_merk = ig.graph, globals()["MERK"]
    with tempfile.TemporaryDirectory() as d:
        globals()["MERK"] = Path(d) / "merk.json"
        ig.graph = falsch
        try:
            jp = Path(d) / "story-auto-2026-10-27.jpg"
            jp.write_bytes(b"x" * 10)
            media = posten({"datum_tag": "2026-10-27", "art": "tagesgrafik", "form": 11}, jp, warte_takt=0, warten=False)
            merk = json.loads(globals()["MERK"].read_text())
        finally:
            ig.graph, globals()["MERK"] = alt_graph, alt_merk
    ok("story-container mit media_type STORIES", aufrufe[0][2].get("media_type") == "STORIES"
       and aufrufe[0][2]["image_url"].endswith("/ig/story-auto-2026-10-27.jpg"))
    ok("kein sticker, keine caption", "caption" not in aufrufe[0][2] and not any("sticker" in str(a) for a in aufrufe))
    ok("veroeffentlicht und gemerkt", media == "222" and merk["stories"][0]["media"] == "222"
       and merk["stories"][0]["datum"] == "2026-10-27")
    ok("token nie in der ausgabe", geheim not in ig.sauber("fehler " + geheim))
    os.environ.pop("INSTAGRAM_PAGE_TOKEN", None)
    os.environ.pop("IG_USER_ID", None)
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("schritt", nargs="?", choices=("planen", "bauen", "ops", "posten"))
    ap.add_argument("--start", choices=("probe", "takt", "geplant"), default="geplant")
    ap.add_argument("--datum")
    ap.add_argument("--ziel", default="out/story")
    ap.add_argument("--modus", choices=("probe", "entwurf", "scharf"))
    ap.add_argument("--info", default="out/story/info.json")
    ap.add_argument("--jpeg")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    try:
        if a.schritt == "planen":
            datum = dt.date.fromisoformat(a.datum) if a.datum else None
            modus, grund, tag = planen(a.start, dt.datetime.now(dt.timezone.utc),
                                       os.environ.get("IG_STORY_AUTO_LIVE", ""),
                                       os.environ.get("IG_STORY_AUTO_STOPP", ""),
                                       ig.json_laden(MERK, {"stories": []}), datum)
            ausgabe("plan, %s, %s" % (modus, grund))
            ausgang(modus=modus, datum=tag.isoformat())
            return 0
        if a.schritt == "bauen":
            info = bauen(dt.date.fromisoformat(a.datum), a.ziel)
            ausgang(jpeg=info["jpeg"], gebaut="1")
            return 0
        if a.schritt == "ops":
            info = json.loads(Path(a.info).read_text(encoding="utf-8"))
            ops_senden(ops_text(a.modus, info), REPO / info["jpeg"])
            return 0
        if a.schritt == "posten":
            info = json.loads(Path(a.info).read_text(encoding="utf-8"))
            posten(info, REPO / (a.jpeg or info["jpeg"]))
            ops_senden(ops_text("scharf", info), REPO / info["jpeg"])
            return 0
    except (Stopp, ig.Fehler) as exc:
        print("STOPP %s" % ig.sauber(exc))
        return 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
