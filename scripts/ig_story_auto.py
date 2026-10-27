#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ig_story_auto.py, eine einfache Instagram-Story am Dienstag und Donnerstag (Ben, 27.10.2026).

WARUM
Poll- und Quiz-Sticker kann die Instagram-API nicht setzen, eine einfache
Bild-Story schon. Mo, Mi und Fr macht Ben die interaktiven Stories von Hand,
Di und Do geht automatisch eine Story ohne Sticker raus. So bleibt der Account
jeden Tag aktiv, ohne Bens Zeit.

INHALT
1. Die Tagesgrafik des Tages: das JPEG, das um 09:30 auf den Feed ging
   (ig/tagesgrafik-JJJJ-MM-TT-formNN.jpg), mit Zahl, Datum und Herkunft aus
   data/instagram-log.json.
2. Gibt es heute keine, die Zahl des Tages (graphics/number-of-day.png), wenn
   data/number-of-day.json vom selben Tag ist.
Beide Bilder sind in ihrer eigenen Kette schon durch die Wachen gegangen. Hier
wird zusaetzlich geprueft, dass Zahl, Datum und counted, source oder computed
dastehen und die Texte die Textregeln bestehen. Das Bild kommt auf 1080 x 1920,
die Grafik in der Mitte, oben und unten je 285 px in ihrer eigenen Randfarbe,
also ausserhalb der Flaechen, die Instagram mit Namen und Antwortfeld belegt.
Kein Sticker, keine Caption, kein Link.

MODI
probe     von Hand, jeder Tag: nur nach #moderator-only, nie zu Instagram
entwurf   Takt oder Zeitplan ohne IG_STORY_AUTO_LIVE=true: nur nach #moderator-only
scharf    Takt oder Zeitplan, IG_STORY_AUTO_LIVE=true, Di oder Do, zwischen 17:15
          und 19:30 Berlin, IG_STORY_AUTO_STOPP nicht auf heute oder "immer",
          heute noch keine Story in data/ig-story-auto-log.json (die Merkdatei)
aus       sonst, mit Grund im Log

GEHEIMNISSE nur aus der Umgebung (INSTAGRAM_PAGE_TOKEN, DISCORD_WEBHOOK_OPS),
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
import urllib.request
import uuid
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
RAND_OBEN = 285                            # 1920 - 1350 = 570, halb oben, halb unten
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
    return re.sub(r"\b(?:api\.)?([a-z0-9-]+)\.(?:com|org|io|net)\b", r"\1", t)


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
            return {"art": "tagesgrafik", "form": p.get("form"), "bild": str(datei),
                    "zahl": p.get("zahl_text") or p["zahl"], "datum": p["tag"], "herkunft": p["herkunft"]}
    if nod and nod_datum(nod.get("issue")) == tag and (repo / "graphics" / "number-of-day.png").exists():
        d = nod_datum(nod["issue"])
        return {"art": "zahl des tages", "form": None, "bild": str(repo / "graphics" / "number-of-day.png"),
                "zahl": "%s %s" % (nod.get("value", ""), nod.get("value_label", "")),
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
    for feld in ("zahl", "herkunft"):
        for v in content_wache.text_verstoesse(q[feld]):
            fehler.append("%s, %s" % (feld, v))
    if re.search(r"\b(buy|sell|kaufen|verkaufen|moon|pump|target)\b", q["zahl"] + " " + q["herkunft"], re.I):
        fehler.append("kaufsprache oder kursziel")
    return fehler


# ---------------------------------------------------------------- bild

def randfarbe(bild, zeile):
    px = [bild.getpixel((x, zeile)) for x in range(0, bild.width, 8)]
    px = sorted(px, key=lambda p: sum(p[:3]))
    return px[len(px) // 2][:3]


def story_bild(quelle_pfad, ziel):
    """1080 x 1920 JPEG, die 4:5-Grafik in der Mitte, oben und unten ihre Randfarbe."""
    from PIL import Image
    g = Image.open(quelle_pfad).convert("RGB")
    if g.size != (1080, 1350):
        g = g.resize((1080, round(1080 * g.height / g.width)))
    hoehe = g.height
    if hoehe > H - 2 * 250:
        raise Stopp("grafik %dx%d ragt in die flaechen von instagram" % g.size)
    oben = (H - hoehe) // 2
    leinwand = Image.new("RGB", (W, H), randfarbe(g, 2))
    unten_farbe = randfarbe(g, hoehe - 3)
    leinwand.paste(Image.new("RGB", (W, H - oben - hoehe), unten_farbe), (0, oben + hoehe))
    leinwand.paste(g, (0, oben))
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    leinwand.save(ziel, "JPEG", quality=92, optimize=True)
    return ziel


def bauen(tag, ziel, repo=REPO):
    q = quelle(tag, ig.json_laden(LOG_IG, {}), ig.json_laden(LOG_GRAFIK, {}), ig.json_laden(NOD_JSON, {}), repo)
    f = pruefen(q)
    if f:
        raise Stopp("story nicht gruen, %s" % "; ".join(f))
    jpeg = Path(repo) / "ig" / ("story-auto-%s.jpg" % tag.isoformat())
    story_bild(q["bild"], jpeg)
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
              "zahl %s, %s, %s" % (info["zahl"], info["datum"], info["herkunft"]),
              "kein sticker, keine caption, kein link"]
    if modus != "scharf":
        zeilen.append("geht di und do um %s berlin raus, aber nur mit IG_STORY_AUTO_LIVE=true. "
                      "veto mit IG_STORY_AUTO_STOPP auf %s oder immer" % (POSTZEIT, info["datum_tag"]))
    return ohne_host("\n".join(zeilen))


def ops_senden(text, bild):
    hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
    if not hook:
        ausgabe("kein DISCORD_WEBHOOK_OPS, nur im log")
        ausgabe(text)
        return 0
    grenze = "----st" + uuid.uuid4().hex
    teile = [("--%s\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json"
              "\r\n\r\n" % grenze).encode()
             + json.dumps({"content": ig.sauber(text)[:1990], "allowed_mentions": {"parse": []}}).encode() + b"\r\n"]
    if bild:
        teile.append(("--%s\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"%s\"\r\n"
                      "Content-Type: image/jpeg\r\n\r\n" % (grenze, Path(bild).name)).encode()
                     + Path(bild).read_bytes() + b"\r\n")
    body = b"".join(teile) + ("--%s--\r\n" % grenze).encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % grenze, "User-Agent": ig.UA})
    with ig._oeffnen(req, timeout=60) as r:
        ausgabe("an #moderator-only, http %s" % r.status)
        return r.status


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
    ok("ohne host", ohne_host("source api.kaspa.org and coingecko.com") == "source kaspa and coingecko")

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
               "sources": "api.kaspa.org and coingecko.com"}
        tag = dt.date(2026, 10, 27)
        q = quelle(tag, log_ig, log_g, nod, r)
        ok("tagesgrafik zuerst", q["art"] == "tagesgrafik" and q["form"] == 11)
        ok("tagesgrafik gruen", pruefen(q) == [], pruefen(q))
        q2 = quelle(tag, {"posts": []}, log_g, nod, r)
        ok("sonst zahl des tages", q2["art"] == "zahl des tages" and q2["datum"] == "27 oct 2026")
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
        jp = story_bild(r / "ig" / "tagesgrafik-2026-10-27-form11.jpg", r / "ig" / "story-auto-2026-10-27.jpg")
        b = Image.open(jp)
        ok("story 1080 x 1920", b.size == (1080, 1920))
        ok("rand in der randfarbe der grafik", sum(abs(a - c) for a, c in zip(b.getpixel((10, 10)), (242, 245, 244))) < 12)
        ok("grafik in der mitte, ausserhalb der 250-px-flaechen", RAND_OBEN >= 250 and H - RAND_OBEN - 1350 >= 250)

    t = ops_text("entwurf", {"datum_tag": "2026-10-27", "art": "zahl des tages", "form": None, "zahl": "$61.6K x",
                             "datum": "27 oct 2026", "herkunft": "source kaspa and coingecko"})
    ok("ops nennt tag, quelle, veto und live", "di 27.10.2026" in t and "IG_STORY_AUTO_STOPP" in t
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
