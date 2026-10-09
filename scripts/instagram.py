#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""instagram.py, die Tagesgrafik auf Instagram (@kaspapulse) (Ben, 08.10.2026).

ZUGANG. Graph API ueber Facebook-Login (graph.facebook.com). Der Seiten-Token
kommt nur aus der Umgebung (INSTAGRAM_PAGE_TOKEN, GitHub Secret) und geht nur
im Kopf "Authorization: Bearer" hinaus, nie in einer URL. Er wird nie
ausgegeben, nie geschrieben und steht in keiner Fehlermeldung: jede Antwort
der API laeuft durch sauber(), bevor sie irgendwo erscheint. IG_USER_ID und
FB_PAGE_ID sind Variablen, keine Geheimnisse.

ABLAUF UM 09:30 BERLIN, NACH DISCORD (Job "instagram" in tagesgrafik.yml)
    faellig     liefert die Grafik von heute, wenn 07:30 sie mit "senden"
                ausgeliefert hat (Eintrag in data/tagesgrafik-log.json), wenn es
                zwischen 09:25 und 11:30 Berlin ist, wenn heute noch nichts in
                data/instagram-log.json steht und wenn IG_STOPP nicht auf heute
                oder "immer" steht
    artefakt    holt PNG und Caption aus dem Artefakt genau des Laufs, der die
                Grafik um 07:30 gebaut hat (gleiche Form, gleiche Messzeit). So
                ist es dieselbe Grafik, die Ben geprueft hat, nicht neu gerechnet
    jpeg        PNG nach JPEG, Instagram nimmt kein PNG. Ablage in ig/, der
                Workflow committet sie, kaspapulse.com liefert sie aus
    posten      wartet, bis die URL das JPEG liefert, legt den Container an,
                prueft seinen Status und veroeffentlicht nur mit --modus scharf.
                Trocken (Vorgabe) bleibt der Container unveroeffentlicht,
                Caption und Status stehen im Log

PFLEGE (instagram-pflege.yml)
    insights    je Post der letzten 7 Tage Reichweite, Likes, Kommentare, Saves,
                Shares nach data/instagram-insights.json. Nur Zahlen.
    kommentare  neue Kommentare unter unseren Posts, je einer mit Antwort-
                ENTWURF an DISCORD_WEBHOOK_OPS. Es wird nichts beantwortet. Im
                Repo stehen nur die IDs gesehener Kommentare, kein Text, kein Name.
    antworten   die Freigabe: Ben startet instagram-antwort.yml mit Kommentar-ID
                und Text. Der Text laeuft durch dieselbe Wortwache wie Discord und
                X, erst dann geht die Antwort raus.

    python3 scripts/instagram.py faellig
    python3 scripts/instagram.py artefakt --ziel out/ig
    python3 scripts/instagram.py jpeg --png out/ig/x.png --ziel ig
    python3 scripts/instagram.py posten --bild ig/x.jpg --caption out/ig/x-instagram.json --modus trocken
    python3 scripts/instagram.py insights
    python3 scripts/instagram.py kommentare
    python3 scripts/instagram.py antworten --kommentar-id 123 --text "..."
    python3 scripts/instagram.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

GRAPH = "https://graph.facebook.com/%s" % os.environ.get("IG_GRAPH_VERSION", "v24.0")
SEITE = "https://kaspapulse.com"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"
LOG_GRAFIK = REPO / "data" / "tagesgrafik-log.json"
LOG_IG = REPO / "data" / "instagram-log.json"
INSIGHTS = REPO / "data" / "instagram-insights.json"
KOMMENTARE = REPO / "data" / "instagram-kommentare.json"
ANTWORTEN = REPO / "data" / "instagram-antworten.json"
METRIKEN = ("reach", "likes", "comments", "saved", "shares")
FENSTER_BERLIN = ((9, 25), (11, 30))   # Ben, 08.10.2026: Discord kommt immer zuerst
INSIGHT_TAGE = 7
KOMMENTAR_TAGE = 14
JPEG_QUALITAET = 92


class Fehler(Exception):
    pass


class KeinArtefakt(Fehler):
    """Kein Artefakt vom Morgen im neuen Format. Kein Fehler, nur nicht faellig."""


# ---------------------------------------------------------------- token und bereinigung

def token():
    t = os.environ.get("INSTAGRAM_PAGE_TOKEN", "")
    if not t:
        raise Fehler("kein INSTAGRAM_PAGE_TOKEN in der umgebung")
    return t


def sauber(text):
    """Entfernt den Token und alles, was wie ein Token aussieht, aus einem Text,
    bevor er geloggt, geschrieben oder als Fehler gemeldet wird."""
    t = str(text)
    for name in ("INSTAGRAM_PAGE_TOKEN", "DISCORD_WEBHOOK_OPS", "GITHUB_TOKEN"):
        wert = os.environ.get(name, "")
        if len(wert) >= 8:
            t = t.replace(wert, "***")
    t = re.sub(r"(access_token|token|client_secret|appsecret_proof)=[^&\s\"']+", r"\1=***", t, flags=re.I)
    t = re.sub(r"(\"(?:access_token|token|client_secret)\"\s*:\s*\")[^\"]*\"", r"\1***\"", t, flags=re.I)
    t = re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1***", t)
    t = re.sub(r"\bEA[A-Za-z0-9]{20,}\b", "***", t)          # form der facebook-token
    t = re.sub(r"https://(discord(app)?\.com)/api/webhooks/\S+", r"https://\1/api/webhooks/***", t)
    return t


def ausgabe(*teile):
    print(sauber(" ".join(str(t) for t in teile)))


# ---------------------------------------------------------------- http

_oeffnen = urllib.request.urlopen          # im selbsttest ersetzt


def http(methode, url, daten=None, kopf=None, timeout=40):
    kopf = dict(kopf or {})
    kopf.setdefault("User-Agent", UA)
    body = None
    if daten is not None:
        body = urllib.parse.urlencode(daten).encode()
        kopf.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, headers=kopf, method=methode)
    try:
        with _oeffnen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        roh = b""
        try:
            roh = exc.read()
        except Exception:                              # noqa: BLE001
            pass
        return exc.code, roh, dict(exc.headers or {})


def graph(methode, pfad, params=None, versuche=3):
    """Ein Aufruf der Graph API. Der Token geht nur im Kopf. Fehlertexte
    laufen durch sauber()."""
    params = dict(params or {})
    url = "%s/%s" % (GRAPH, pfad.lstrip("/"))
    kopf = {"Authorization": "Bearer " + token()}
    if methode == "GET" and params:
        url += "?" + urllib.parse.urlencode(params)
        params = None
    for n in range(versuche):
        status, roh, _ = http(methode, url, params if methode != "GET" else None, kopf)
        if status in (429, 500, 502, 503) and n + 1 < versuche:
            time.sleep(5 * (n + 1))
            continue
        try:
            d = json.loads(roh.decode("utf-8") or "{}")
        except ValueError:
            d = {"roh": roh[:300].decode("utf-8", "replace")}
        if status >= 400 or "error" in d:
            fehler = d.get("error", d) if isinstance(d, dict) else d
            raise Fehler(sauber("graph %s %s, http %s, %s" % (
                methode, pfad.split("?")[0], status, json.dumps(fehler, ensure_ascii=False)[:500])))
        return d
    raise Fehler("graph %s %s, keine antwort" % (methode, pfad))


def ig_user():
    u = os.environ.get("IG_USER_ID", "")
    if not re.fullmatch(r"\d{5,30}", u):
        raise Fehler("IG_USER_ID fehlt oder ist keine zahl")
    return u


def ops(text):
    hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
    if not hook:
        ausgabe("kein DISCORD_WEBHOOK_OPS, nachricht nur im log")
        ausgabe(text)
        return
    status, _, _ = _ops_post(hook, text)
    ausgabe("an ops, http %s" % status)


def _ops_post(hook, text):
    body = json.dumps({"content": sauber(text)[:1990], "allowed_mentions": {"parse": []}}).encode()
    req = urllib.request.Request(hook, data=body, headers={"Content-Type": "application/json",
                                                           "User-Agent": UA}, method="POST")
    try:
        with _oeffnen(req, timeout=30) as r:
            return r.status, b"", {}
    except urllib.error.HTTPError as exc:
        return exc.code, b"", {}


def json_laden(pfad, leer):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return leer


def json_schreiben(pfad, d):
    text = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if sauber(text) != text:
        raise Fehler("in %s stand etwas, das wie ein token aussieht, nichts geschrieben" % Path(pfad).name)
    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    Path(pfad).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- faellig

def berlin(now):
    try:
        from zoneinfo import ZoneInfo
        return now.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:                                  # noqa: BLE001
        # rueckfall ohne zeitzonendaten: mesz von ende maerz bis ende oktober
        jahr = now.year
        beginn = max(dt.datetime(jahr, 3, d, 1, tzinfo=dt.timezone.utc) for d in range(25, 32)
                     if dt.date(jahr, 3, d).weekday() == 6)
        ende = max(dt.datetime(jahr, 10, d, 1, tzinfo=dt.timezone.utc) for d in range(25, 32)
                   if dt.date(jahr, 10, d).weekday() == 6)
        return now + dt.timedelta(hours=2 if beginn <= now < ende else 1)


def faellig(now, log_grafik, log_ig, stopp="", hand=False):
    """(eintrag der grafik, None) oder (None, grund). hand (nur trocken, von
    Hand gestartet) laesst Zeitfenster und Tagessperre weg."""
    b = berlin(now)
    heute = b.date().isoformat()
    (h0, m0), (h1, m1) = FENSTER_BERLIN
    if not hand and not (h0, m0) <= (b.hour, b.minute) < (h1, m1):
        return None, "%02d:%02d berlin liegt nicht zwischen %02d:%02d und %02d:%02d" % (
            b.hour, b.minute, h0, m0, h1, m1)
    if stopp.strip() in (heute, "immer"):
        return None, "IG_STOPP steht auf %s" % stopp.strip()
    if not hand and any(e.get("datum") == heute for e in log_ig.get("posts", [])):
        return None, "heute (%s) schon an instagram" % heute
    eintrag = next((e for e in reversed(log_grafik.get("laeufe", [])) if e.get("datum") == heute), None)
    if not eintrag or not eintrag.get("messzeit_utc"):
        return None, "heute (%s) keine ausgelieferte tagesgrafik im log, also nicht gesendet" % heute
    return eintrag, None


# ---------------------------------------------------------------- artefakt

def gh(pfad, roh=False):
    """GitHub-API mit GITHUB_TOKEN. Bei Weiterleitung (Artefakt-Zip) wird die
    Ziel-URL ohne Token geholt."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    gt = os.environ.get("GITHUB_TOKEN", "")
    if not repo or not gt:
        raise Fehler("GITHUB_REPOSITORY oder GITHUB_TOKEN fehlt")
    url = "https://api.github.com/repos/%s/%s" % (repo, pfad.lstrip("/"))

    class OhneWeiter(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(OhneWeiter)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + gt, "User-Agent": UA,
                                               "Accept": "application/vnd.github+json"})
    try:
        with opener.open(req, timeout=60) as r:
            daten = r.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
            with _oeffnen(urllib.request.Request(exc.headers["Location"], headers={"User-Agent": UA}),
                          timeout=120) as r:
                daten = r.read()
        else:
            raise Fehler(sauber("github %s, http %s" % (pfad.split("?")[0], exc.code)))
    return daten if roh else json.loads(daten.decode("utf-8"))


def artefakt(eintrag, ziel):
    """PNG und Caption aus dem Lauf, der die Grafik ausgeliefert hat."""
    mz = eintrag["messzeit_utc"]
    stamm = "tagesgrafik-%s-form%02d" % (mz[:10], int(eintrag["form"]))
    runs = gh("actions/workflows/tagesgrafik.yml/runs?per_page=30&created=%%3E%%3D%s" % mz[:10])
    for run in runs.get("workflow_runs", []):
        for a in gh("actions/runs/%d/artifacts" % run["id"]).get("artifacts", []):
            if a.get("name") != "tagesgrafik" or a.get("expired"):
                continue
            z = zipfile.ZipFile(io.BytesIO(gh("actions/artifacts/%d/zip" % a["id"], roh=True)))
            namen = {Path(n).name: n for n in z.namelist()}
            if stamm + "-instagram.json" not in namen or stamm + ".png" not in namen:
                continue
            ig = json.loads(z.read(namen[stamm + "-instagram.json"]).decode("utf-8"))
            if ig.get("messzeit_utc") != mz:
                continue
            Path(ziel).mkdir(parents=True, exist_ok=True)
            png = Path(ziel) / (stamm + ".png")
            png.write_bytes(z.read(namen[stamm + ".png"]))
            cap = Path(ziel) / (stamm + "-instagram.json")
            cap.write_bytes(z.read(namen[stamm + "-instagram.json"]))
            ausgabe("artefakt aus lauf %d, %s" % (run["id"], png.name))
            return png, cap
    raise KeinArtefakt("kein artefakt mit %s und messzeit %s gefunden" % (stamm, mz))


# ---------------------------------------------------------------- jpeg

def jpeg(png, ziel):
    from PIL import Image
    bild = Image.open(png)
    w, h = bild.size
    if not 0.8 <= w / h <= 1.91:
        raise Fehler("seitenverhaeltnis %dx%d passt nicht zu instagram (4:5 bis 1.91:1)" % (w, h))
    if bild.mode in ("RGBA", "LA", "P"):
        grund = Image.new("RGB", bild.size, (8, 11, 15))
        bild = bild.convert("RGBA")
        grund.paste(bild, mask=bild.split()[-1])
        bild = grund
    else:
        bild = bild.convert("RGB")
    Path(ziel).mkdir(parents=True, exist_ok=True)
    out = Path(ziel) / (Path(png).stem + ".jpg")
    bild.save(out, "JPEG", quality=JPEG_QUALITAET, optimize=True)
    if out.stat().st_size > 8 * 1024 * 1024:
        raise Fehler("jpeg ueber 8 MB")
    return out


def url_warten(url, laenge, frist=600, takt=15):
    """Wartet, bis kaspapulse.com das JPEG mit genau dieser Laenge liefert."""
    ende = time.time() + frist
    letzter = None
    while time.time() < ende:
        status, roh, kopf = http("GET", url + "?v=%d" % int(time.time()))
        typ = {k.lower(): v for k, v in kopf.items()}.get("content-type", "")
        if status == 200 and typ.startswith("image/jpeg") and len(roh) == laenge:
            return True
        letzter = "http %s, %s, %d bytes" % (status, typ or "-", len(roh))
        time.sleep(takt)
    raise Fehler("bild nach %d s nicht oeffentlich, zuletzt %s" % (frist, letzter))


# ---------------------------------------------------------------- posten

def posten(bild_url, caption, modus, warte_takt=10, warte_max=300):
    """Container anlegen, Status pruefen, nur mit modus scharf veroeffentlichen."""
    from tagesgrafik import ig_pruefung
    fehler = ig_pruefung(caption, None)
    if fehler:
        raise Fehler("caption nicht gruen, %s" % "; ".join(fehler))
    u = ig_user()
    c = graph("POST", "%s/media" % u, {"image_url": bild_url, "caption": caption})
    cid = str(c.get("id", ""))
    if not re.fullmatch(r"\d+", cid):
        raise Fehler("container ohne id")
    ausgabe("container %s angelegt" % cid)
    status, ende = "", time.time() + warte_max
    while time.time() < ende:
        d = graph("GET", cid, {"fields": "status_code,status"})
        status = d.get("status_code", "")
        ausgabe("container %s, status %s" % (cid, status))
        if status in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED"):
            break
        time.sleep(warte_takt)
    erg = {"container": cid, "status": status, "modus": modus}
    if status != "FINISHED":
        raise Fehler("container %s endet mit status %s, nicht veroeffentlicht" % (cid, status or "-"))
    if modus != "scharf":
        ausgabe("trocken, container %s bleibt unveroeffentlicht" % cid)
        return erg
    m = graph("POST", "%s/media_publish" % u, {"creation_id": cid})
    erg["media"] = str(m.get("id", ""))
    try:
        erg["permalink"] = graph("GET", erg["media"], {"fields": "permalink"}).get("permalink", "")
    except Fehler as exc:
        ausgabe("permalink nicht gelesen, %s" % exc)
    ausgabe("veroeffentlicht, media %s %s" % (erg["media"], erg.get("permalink", "")))
    return erg


# ---------------------------------------------------------------- insights

def zeit(t):
    return dt.datetime.strptime(t[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def eigene_medien(tage, now):
    d = graph("GET", "%s/media" % ig_user(), {"fields": "id,timestamp,media_type,permalink", "limit": 30})
    grenze = now - dt.timedelta(days=tage)
    return [m for m in d.get("data", []) if m.get("timestamp") and zeit(m["timestamp"]) >= grenze]


def metrik_wert(eintrag):
    if "total_value" in eintrag:
        return eintrag["total_value"].get("value")
    werte = eintrag.get("values") or []
    return werte[-1].get("value") if werte else None


def insights(now):
    stand = json_laden(INSIGHTS, {"medien": {}})
    log = {p.get("media"): p for p in json_laden(LOG_IG, {"posts": []}).get("posts", []) if p.get("media")}
    heute = now.date().isoformat()
    for m in eigene_medien(INSIGHT_TAGE, now):
        mid = str(m["id"])
        werte, fehlt = {}, []
        try:
            d = graph("GET", "%s/insights" % mid, {"metric": ",".join(METRIKEN)})
            for e in d.get("data", []):
                werte[e.get("name")] = metrik_wert(e)
        except Fehler:
            for metrik in METRIKEN:             # eine metrik kann fuer ein medium fehlen
                try:
                    d = graph("GET", "%s/insights" % mid, {"metric": metrik})
                    werte[metrik] = metrik_wert((d.get("data") or [{}])[0])
                except Fehler:
                    fehlt.append(metrik)
        e = stand["medien"].setdefault(mid, {})
        e.update({"gepostet_utc": m.get("timestamp"), "typ": m.get("media_type"),
                  "permalink": m.get("permalink")})
        if mid in log:
            e.update({"form": log[mid].get("form"), "caption_sha": log[mid].get("caption_sha"),
                      "frage": log[mid].get("frage")})
        e.setdefault("tage", {})[heute] = {k: werte.get(k) for k in METRIKEN}
        if fehlt:
            e["tage"][heute]["nicht_messbar"] = fehlt
        ausgabe("insights %s %s" % (mid, json.dumps(e["tage"][heute])))
    grenze = (now - dt.timedelta(days=60)).date().isoformat()
    stand["medien"] = {k: v for k, v in stand["medien"].items() if (v.get("gepostet_utc") or "")[:10] >= grenze}
    stand["stand_utc"] = now.isoformat(timespec="seconds")
    json_schreiben(INSIGHTS, stand)
    return stand


# ---------------------------------------------------------------- kommentare

# ---------------------------------------------------------------- kommentar-entwuerfe
# Ben, 09.10.2026. Je Kommentar eine Klasse, je Klasse mehrere Varianten,
# nie zweimal derselbe Text an einem Tag, der Account-Name wo es passt, ein
# Bezug auf den Kommentar. Spam und Promo werden nicht beantwortet, nur als
# ignoriert an Ops gemeldet. Automatisch geantwortet wird nicht (AUTOMATIK).
AUTOMATIK = False

SPAM = re.compile(
    r"send (me )?(this|the) post|dm (us |me )?(for|to)\b|\bdm me\b|\bpromo(te|tion)?\b|\bcollab|"
    r"\bfeature(d)? (on|by|you|your|this)|\bshout ?out|check (my|our) (page|profile|bio|account)|"
    r"\bfollow (me|us|back)\b|\bgiveaway|\bairdrop|link in (my|our) bio|whats ?app|\btelegram\b|"
    r"\bsignals?\b|\binvest(ing|ment)? (with|plan)|earn \$|\bpaid partnership|\bsponsor", re.I)
SPAM_NAME = re.compile(r"promo|feature|shoutout|collab|marketing|growth|_ads\b|ads_|crypto_?news|daily_?crypto", re.I)
WUNSCH = re.compile(
    r"(can|could|would|will) you (please )?(track|show|count|post|add|chart|do)\s+(?P<a>[^?.!]{3,60})|"
    r"please (track|show|count|post|add|chart)\s+(?P<b>[^?.!]{3,60})|"
    r"(would|i'?d) love to see\s+(?P<c>[^?.!]{3,60})|"
    r"(do|make) (one|a post) (on|about)\s+(?P<d>[^?.!]{3,60})|"
    r"what about\s+(?P<e>[^?.!]{3,60})", re.I)
FRAGE_ANFANG = re.compile(r"^\s*(how|what|why|when|where|who|which|is|are|does|do|can|will|wie|was|warum|wann)\b", re.I)
LOB = re.compile(r"great|love|nice|thanks|thank you|awesome|cool|amazing|good (work|job|stuff)|helpful|"
                 r"newsletter|subscribed|signed up|\bfire\b|🔥|👏|💯|🙌|❤|💚|👍", re.I)
KURS = re.compile(r"\b(price|moon|pump|target|ath|\$\d|buy|sell|bullish|bearish|when lambo)\b", re.I)
THEMEN = (("hashrate", "hashrate"), ("hash rate", "hashrate"), ("supply", "supply"), ("entity x", "entity x"),
          ("whale", "the largest address"), ("fee", "fees"), ("block", "blocks"), ("address", "addresses"),
          ("holder", "addresses"), ("exchange", "exchange balances"), ("covenant", "covenants"),
          ("halving", "the reward cut"), ("reward", "the reward cut"), ("mining", "mining"), ("miner", "mining"),
          ("tps", "throughput"), ("transaction", "transactions"), ("tvl", "tvl"), ("token", "tokens"))

VARIANTEN = {
    "lob": [
        "thanks {name}, glad it helps. we count kaspa from the chain every day. what should we count next?",
        "appreciate it {name}. {zahl_satz} more of these every day.",
        "thank you {name}. if a number is missing, tell us and we will see if the chain can answer it.",
        "glad you like it {name}. the weekly mail has the take behind the numbers, link in bio.",
        "thanks for reading {name}. every number here is counted or sourced, never guessed.",
    ],
    "frage": [
        "good question {name}. {zahl_satz} we only publish what we count ourselves or can name a source for.",
        "{name} fair question{thema_satz}. {zahl_satz} the method is on our site, link in bio.",
        "{name} short answer{thema_satz}, {zahl_satz} if that does not cover it, ask again and we will dig in.",
        "thanks for asking {name}. {zahl_satz} we stick to what the chain shows.",
    ],
    "wunsch": [
        "noted {name}, {wunsch} goes on our list. if the chain can answer it, we will count it.",
        "{name} good idea, {wunsch}. we will check whether we can count it ourselves before we post it.",
        "thanks {name}, {wunsch} is on the list. we only post it once we can count it cleanly.",
        "{name} we hear you on {wunsch}. give us a few days to see what the chain can tell us.",
    ],
    "kurs": [
        "{name} we only count what the chain shows and leave the chart talk to others. {zahl_satz}",
        "{name} no calls from us, just counts. {zahl_satz}",
        "{name} we stay out of where it goes next and stick to what the chain records. {zahl_satz}",
    ],
    "sonstiges": [
        "thanks for the comment {name}. {zahl_satz}",
        "{name} noted. {zahl_satz} what should we count next?",
        "appreciate you stopping by {name}. {zahl_satz}",
    ],
}


def einordnen(text, username=""):
    """(klasse, grund). Klassen lob, frage, wunsch, kurs, sonstiges, spam."""
    t = (text or "").strip()
    m = SPAM.search(t)
    if m:
        return "spam", "treffer %r" % m.group(0).lower()
    if username and SPAM_NAME.search(username):
        return "spam", "account-name %r" % SPAM_NAME.search(username).group(0).lower()
    if WUNSCH.search(t):
        return "wunsch", "wunsch"
    if KURS.search(t):
        return "kurs", "kurs oder kauf"
    if "?" in t or FRAGE_ANFANG.search(t):
        return "frage", "frage"
    if LOB.search(t):
        return "lob", "lob"
    return "sonstiges", "ohne klasse"


def wunsch_thema(text):
    m = WUNSCH.search(text or "")
    if not m:
        return ""
    w = next(g for g in (m.group(x) for x in "abcde") if g)
    w = re.sub(r"https?://\S+|@\w+|#\w+", "", w)
    w = re.sub(r"[^a-z0-9 %,']", " ", w.lower())
    w = " ".join(w.split()[:7]).strip(" ,")
    return w


def thema(text):
    k = (text or "").lower()
    return next((name for wort, name in THEMEN if wort in k), "")


def name_ok(username):
    """Der Name nur, wenn er die Regeln nicht verletzt (kein Domain-Muster usw.)."""
    from tagesgrafik import pruefe_eine
    if not username or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", username) or "kaspapulse" in username.lower():
        return ""
    return "" if pruefe_eine("@" + username, None, "name") else "@" + username


def entwurf(text, post, username="", verwendet=None):
    """(klasse, entwurf oder None). Der Entwurf haelt pruefe_eine ein und ist
    heute noch nicht verwendet worden. Spam bekommt keinen Entwurf."""
    from tagesgrafik import pruefe_eine
    klasse, _ = einordnen(text, username)
    if klasse == "spam":
        return klasse, None
    verwendet = verwendet if verwendet is not None else set()
    if post.get("zahl") and post.get("tag") and post.get("herkunft"):
        zahl_satz = "this one is %s as of %s, %s." % (post["zahl"], post["tag"], post["herkunft"])
    else:
        zahl_satz = "we count kaspa from the chain every day."
    th = thema(text)
    werte = {"zahl_satz": zahl_satz, "thema_satz": (" on %s" % th) if th else "",
             "wunsch": wunsch_thema(text) or (th or "that")}
    # erst die varianten, die heute in dieser klasse noch nicht dran waren,
    # dann die uebrigen; derselbe text nie zweimal am tag
    vorlagen = list(enumerate(VARIANTEN[klasse]))
    vorlagen.sort(key=lambda iv: ("%s:%d" % (klasse, iv[0])) in verwendet)
    for mit_name in (True, False):
        werte["name"] = name_ok(username) if mit_name else ""
        for i, vorlage in vorlagen:
            t = " ".join(vorlage.format(**werte).split())
            t = re.sub(r"\s+([,.?])", r"\1", t).strip()
            t = t[0].lower() + t[1:] if t else t
            h = hashlib.sha256(t.encode()).hexdigest()[:12]
            if h in verwendet or pruefe_eine(t, post.get("form"), "entwurf"):
                continue
            verwendet.update({h, "%s:%d" % (klasse, i)})
            return klasse, t
    return klasse, None


def kommentare(now):
    stand = json_laden(KOMMENTARE, {"gesehen": {}})
    # nur neue kommentare melden (Ben, 09.10.2026): was vor dem ersten lauf
    # mit dieser regel geschrieben wurde, wird still als gesehen markiert
    seit = stand.setdefault("seit_utc", now.isoformat(timespec="seconds"))
    heute = now.date().isoformat()
    verwendet_alle = stand.setdefault("entwuerfe_heute", {})
    for tag in [t for t in verwendet_alle if t != heute]:
        del verwendet_alle[tag]
    verwendet = set(verwendet_alle.get(heute, []))
    log = {p.get("media"): p for p in json_laden(LOG_IG, {"posts": []}).get("posts", []) if p.get("media")}
    ich = graph("GET", ig_user(), {"fields": "username"}).get("username", "")
    neu, ignoriert = 0, 0
    for m in eigene_medien(KOMMENTAR_TAGE, now):
        mid = str(m["id"])
        d = graph("GET", "%s/comments" % mid, {"fields": "id,text,timestamp,username", "limit": 50})
        for k in d.get("data", []):
            kid = str(k.get("id"))
            if kid in stand["gesehen"]:
                continue
            stand["gesehen"][kid] = {"media": mid, "zeit": k.get("timestamp")}
            if k.get("username") == ich:
                continue
            if not k.get("timestamp") or zeit(k["timestamp"]) < zeit(seit):
                continue
            text, wer = k.get("text") or "", k.get("username", "?")
            klasse, e = entwurf(text, log.get(mid, {}), wer, verwendet)
            stand["gesehen"][kid]["klasse"] = klasse
            if klasse == "spam":
                ops("instagram kommentar ignoriert, spam oder promo (%s), von @%s unter %s" % (
                    einordnen(text, wer)[1], wer, m.get("permalink", mid)))
                ignoriert += 1
                continue
            ops("INSTAGRAM KOMMENTAR (%s) unter %s\nvon @%s, %s\n> %s\n\nENTWURF\n```\n%s\n```\n"
                "freigeben, workflow instagram antwort, kommentar_id %s, text anpassen und starten. "
                "es geht nichts automatisch raus." % (
                    klasse, m.get("permalink", mid), wer, k.get("timestamp", ""),
                    text.replace("\n", " ")[:600], e or "kein entwurf, der die regeln einhaelt, bitte von hand", kid))
            neu += 1
    verwendet_alle[heute] = sorted(verwendet)
    stand["stand_utc"] = now.isoformat(timespec="seconds")
    json_schreiben(KOMMENTARE, stand)
    ausgabe("kommentare neu %d, ignoriert %d" % (neu, ignoriert))
    return neu


def antworten(kommentar_id, text, nur_pruefen=False, now=None):
    from tagesgrafik import pruefe_eine
    now = now or dt.datetime.now(dt.timezone.utc)
    if not re.fullmatch(r"\d{5,30}", kommentar_id or ""):
        raise Fehler("kommentar-id ist keine zahl")
    text = " ".join((text or "").split())
    regeln = pruefe_eine(text, None, "antwort")
    if not text or len(text) > 2200:
        regeln.append("text leer oder ueber 2200 zeichen")
    if regeln:
        raise Fehler("antwort nicht gruen, %s" % "; ".join(regeln))
    if nur_pruefen:
        ausgabe("antwort gruen, nur geprueft, nicht gesendet")
        return None
    r = graph("POST", "%s/replies" % kommentar_id, {"message": text})
    stand = json_laden(ANTWORTEN, {"antworten": []})
    stand["antworten"].append({"kommentar": kommentar_id, "antwort": str(r.get("id", "")),
                               "zeit_utc": now.isoformat(timespec="seconds"), "text": text})
    json_schreiben(ANTWORTEN, stand)
    ausgabe("antwort %s unter kommentar %s" % (r.get("id"), kommentar_id))
    return r.get("id")


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import contextlib
    import tempfile
    fehler = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            fehler.append(name)

    global _oeffnen, LOG_IG, INSIGHTS, KOMMENTARE, ANTWORTEN
    geheim = "EAAtestTOKEN" + "x" * 40
    os.environ["INSTAGRAM_PAGE_TOKEN"] = geheim
    os.environ["IG_USER_ID"] = "17841400000000000"
    os.environ.pop("DISCORD_WEBHOOK_OPS", None)
    aufrufe = []

    class Antwort(io.BytesIO):
        def __init__(self, status, d):
            super().__init__(json.dumps(d).encode())
            self.status, self.headers = status, {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    zustand = {"status": ["IN_PROGRESS", "FINISHED"]}

    def fake(req, timeout=0):
        url, body = req.full_url, (req.data or b"").decode()
        aufrufe.append((req.get_method(), url, body, dict(req.header_items())))
        if "/media_publish" in url:
            return Antwort(200, {"id": "900"})
        if url.endswith("/media") and req.get_method() == "POST":
            return Antwort(200, {"id": "800"})
        if "fields=status_code" in url:
            return Antwort(200, {"status_code": zustand["status"].pop(0) if zustand["status"] else "FINISHED"})
        if "fields=permalink" in url:
            return Antwort(200, {"permalink": "https://www.instagram.com/p/x/"})
        if "/insights" in url:
            if "metric=reach%2Clikes" in url:
                return Antwort(200, {"data": [{"name": n, "values": [{"value": i + 1}]}
                                              for i, n in enumerate(METRIKEN)]})
        if "/media?" in url:
            return Antwort(200, {"data": [{"id": "900", "timestamp": "2026-10-09T07:05:00+0000",
                                           "media_type": "IMAGE", "permalink": "https://www.instagram.com/p/x/"}]})
        if "fields=username" in url:
            return Antwort(200, {"username": "kaspapulse"})
        if "/comments" in url:
            return Antwort(200, {"data": [{"id": "555001", "text": "how do you count this?",
                                           "timestamp": "2026-10-09T08:00:00+0000", "username": "fan"},
                                          {"id": "555002", "text": "thanks", "username": "kaspapulse"},
                                          {"id": "555003", "text": "DM us for promo, we feature crypto pages",
                                           "timestamp": "2026-10-09T09:00:00+0000", "username": "promo_page"},
                                          {"id": "555004", "text": "can you track exchange balances next week?",
                                           "timestamp": "2026-10-09T09:10:00+0000", "username": "whale_watcher"},
                                          {"id": "555005", "text": "old one, how is this counted?",
                                           "timestamp": "2026-10-08T07:00:00+0000", "username": "olduser"}]})
        if "/replies" in url:
            return Antwort(200, {"id": "777"})
        if "/fehler" in url:
            raise urllib.error.HTTPError(url, 400, "bad", {}, io.BytesIO(json.dumps(
                {"error": {"message": "Invalid OAuth access token %s" % geheim,
                           "fbtrace_id": "x"}, "access_token": geheim}).encode()))
        return Antwort(404, {"error": {"message": "unbekannt"}})

    _oeffnen = fake
    with tempfile.TemporaryDirectory() as tmp:
        LOG_IG, INSIGHTS = Path(tmp, "ig-log.json"), Path(tmp, "ins.json")
        KOMMENTARE, ANTWORTEN = Path(tmp, "kom.json"), Path(tmp, "ant.json")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            # caption aus tagesgrafik, wie im artefakt
            import tagesgrafik as tg
            s = tg.seite_bauen(4, tg.FAKE[4], tg.FAKE_NOW, {"laeufe": []})
            cap = s["instagram"]
            erg_t = posten("https://kaspapulse.com/ig/x.jpg", cap, "trocken", warte_takt=0)
            n_trocken = len(aufrufe)
            zustand["status"] = ["FINISHED"]
            erg_s = posten("https://kaspapulse.com/ig/x.jpg", cap, "scharf", warte_takt=0)
            try:
                graph("GET", "fehler")
                fehlertext = ""
            except Fehler as exc:
                fehlertext = str(exc)
            json_schreiben(LOG_IG, {"posts": [{"datum": "2026-10-09", "media": "900", "form": 4,
                                               "zahl": "281,000", "tag": "29 sep 2026",
                                               "herkunft": "counted by kaspa pulse"}]})
            now = dt.datetime(2026, 10, 10, 6, 0, tzinfo=dt.timezone.utc)
            ins = insights(now)
            # erster lauf mit der neuen regel am 09.10. um 00:00, aeltere kommentare still
            json_schreiben(KOMMENTARE, {"gesehen": {}, "seit_utc": "2026-10-09T00:00:00+00:00"})
            neu = kommentare(now)
            neu2 = kommentare(now)
            ant = antworten("555001", "thanks, we count it from the chain every day. what should we count next?",
                            now=now)
            try:
                antworten("555001", "the wallet bought more", now=now)
                schlecht = False
            except Fehler:
                schlecht = True
        log = puffer.getvalue()
        ok("trocken legt container an, prueft status, veroeffentlicht nicht",
           erg_t == {"container": "800", "status": "FINISHED", "modus": "trocken"}
           and not any("/media_publish" in a[1] for a in aufrufe[:n_trocken]))
        ok("scharf veroeffentlicht und holt permalink", erg_s.get("media") == "900" and erg_s.get("permalink"))
        ok("token nie in der url, nur im kopf", all(geheim not in a[1] and geheim not in a[2] for a in aufrufe)
           and all(a[3].get("Authorization") == "Bearer " + geheim for a in aufrufe if GRAPH in a[1]))
        ok("token nicht in der ausgabe", geheim not in log)
        ok("fehlermeldung ohne token", fehlertext and geheim not in fehlertext and "***" in fehlertext)
        ok("caption geht als formularfeld, nicht in der url", any("caption=" in a[2] for a in aufrufe)
           and not any("caption=" in a[1] for a in aufrufe))
        ok("insights je post, fuenf zahlen, form aus dem log",
           ins["medien"]["900"]["tage"]["2026-10-10"] == {"reach": 1, "likes": 2, "comments": 3, "saved": 4,
                                                          "shares": 5} and ins["medien"]["900"]["form"] == 4)
        ok("insights-datei ohne token", geheim not in INSIGHTS.read_text())
        ok("kommentare, zwei neu, eigener und alter still, spam ignoriert, zweiter lauf nichts neu",
           neu == 2 and neu2 == 0 and "olduser" not in log and "ignoriert, spam oder promo" in log
           and "@promo_page" in log and "kommentar_id 555003" not in log)
        ok("wunsch mit name und bezug auf den kommentar", "@whale_watcher" in log and "exchange balances next week" in log)
        ok("keine automatische antwort aus kommentare", AUTOMATIK is False and sum(
            1 for a in aufrufe if "/replies" in a[1]) == 1)
        kom = KOMMENTARE.read_text()
        ok("kommentar-datei nur ids, kein text, kein name", "555001" in kom and "how do you count" not in kom
           and "fan" not in kom)
        ok("entwurf an ops mit zahl und ohne automatik", "ENTWURF" in log and "281,000 as of 29 sep 2026" in log
           and "nichts automatisch" in log)
        post = {"zahl": "5.49%", "tag": "9 oct 2026", "herkunft": "counted by kaspa pulse", "form": 2}
        beispiele = {
            "lob": ["great work, love this 🔥", "signed up for the newsletter", "nice"],
            "frage": ["how do you get this number?", "is this every address?", "where does the data come from"],
            "wunsch": ["can you track miners next?", "would love to see fees per day", "what about covenants"],
            "kurs": ["price target?", "when moon", "should I buy more"],
            "spam": ["send me this post", "DM for promo", "collab?", "we feature crypto accounts, check our bio"],
        }
        richtig = all(einordnen(t, "user1")[0] == k for k, ts in beispiele.items() for t in ts)
        ok("einordnen, lob frage wunsch kurs spam", richtig)
        ok("spam am account-namen", einordnen("nice", "crypto_promo_daily")[0] == "spam")
        heute, texte = set(), []
        for k, ts in beispiele.items():
            for t in ts:
                kl, e = entwurf(t, post, "user1", heute)
                if kl != "spam":
                    texte.append(e)
        ok("alle entwuerfe halten die regeln", all(e and not tg.pruefe_eine(e, 2, "e") for e in texte))
        ok("nie zweimal derselbe text am tag", len(texte) == len(set(texte)))
        v2 = set()
        zwei = [entwurf(t, post, u, v2)[1] for t, u in (("great work", "a1"), ("love it", "b2"))]
        ok("zweites lob am tag nimmt eine andere vorlage, nicht nur einen anderen namen",
           zwei[0].replace("@a1", "") != zwei[1].replace("@b2", ""))
        ok("spam bekommt keinen entwurf", entwurf("DM for promo", post, "x")[1] is None)
        ok("name nur wenn er die regeln haelt", name_ok("fan_1") == "@fan_1" and name_ok("kaspapulse") == ""
           and name_ok("shop.io") == "")
        ok("kurs-frage ohne kurswort beantwortet", not tg.pruefe_eine(entwurf("price target?", post, "a")[1], 2, "e"))
        mehr = set()
        ok("fuenf lob-kommentare, fuenf verschiedene texte", len({entwurf("thanks", post, "a", mehr)[1]
                                                                   for _ in range(5)}) == 5)
        ok("antwort geht raus und steht im log", ant == "777" and "777" in ANTWORTEN.read_text())
        ok("antwort mit kaufwort wird gestoppt", schlecht)
    # bereinigung
    os.environ["INSTAGRAM_PAGE_TOKEN"] = geheim
    ok("sauber, wert, parameter, json, bearer, webhook", all(geheim not in sauber(t) for t in (
        geheim, "x?access_token=%s&y=1" % geheim, '{"access_token": "%s"}' % geheim, "Bearer %s" % geheim))
       and "abc" not in sauber("https://discord.com/api/webhooks/1/abc"))
    ok("sauber laesst normalen text stehen", sauber("container 800, status FINISHED") == "container 800, status FINISHED")
    try:
        json_schreiben(Path(tempfile.gettempdir(), "ig-probe.json"), {"x": geheim})
        ok("schreiben mit token wird verweigert", False)
    except Fehler:
        ok("schreiben mit token wird verweigert", True)
    # faellig
    lg = {"laeufe": [{"datum": "2026-10-09", "form": 4, "messzeit_utc": "2026-10-09T05:31:00+00:00"}]}
    t = lambda h, m: dt.datetime(2026, 10, 9, h, m, tzinfo=dt.timezone.utc)   # noqa: E731
    ok("faellig um 09:35 berlin (07:35 utc, sommerzeit)", faellig(t(7, 35), lg, {"posts": []})[0] is not None)
    ok("nicht faellig um 09:05 berlin, vor discord", faellig(t(7, 5), lg, {"posts": []})[0] is None)
    ok("nicht faellig ab 11:30 berlin", faellig(t(9, 30), lg, {"posts": []})[0] is None)
    ok("nicht faellig ohne gesendete grafik", faellig(t(7, 35), {"laeufe": []}, {"posts": []})[0] is None)
    ok("nicht doppelt am tag", faellig(t(7, 35), lg, {"posts": [{"datum": "2026-10-09"}]})[0] is None)
    ok("IG_STOPP fuer heute und immer", faellig(t(7, 35), lg, {"posts": []}, "2026-10-09")[0] is None
       and faellig(t(7, 35), lg, {"posts": []}, "immer")[0] is None
       and faellig(t(7, 35), lg, {"posts": []}, "2026-10-08")[0] is not None)
    ok("von hand ohne fenster und tagessperre", faellig(t(12, 0), lg, {"posts": [{"datum": "2026-10-09"}]},
                                                         hand=True)[0] is not None)
    ok("von hand nie scharf", main(["posten", "--hand", "--modus", "scharf", "--bild", "x", "--caption", "x"]) == 1)
    import tempfile as _tf
    with _tf.TemporaryDirectory() as tmp:
        Path(tmp, "eintrag.json").write_text(json.dumps({"form": 2, "messzeit_utc": "2026-10-08T06:44:02+00:00"}))
        ausgang = Path(tmp, "out.txt")
        global artefakt
        echt = artefakt

        def kein(e, ziel):
            raise KeinArtefakt("kein artefakt mit tagesgrafik-2026-10-08-form02")
        artefakt = kein
        try:
            rc = main(["artefakt", "--hand", "--ziel", tmp, "--github-output", str(ausgang)])
        finally:
            artefakt = echt
        ok("fehlt das artefakt, gruen mit gefunden=0", rc == 0 and "gefunden=0" in ausgang.read_text())
    ok("winterzeit, 08:30 utc ist 09:30 berlin", faellig(dt.datetime(2026, 11, 2, 8, 30, tzinfo=dt.timezone.utc),
                                                          {"laeufe": [{"datum": "2026-11-02", "form": 1,
                                                                       "messzeit_utc": "x"}]}, {"posts": []})[0])
    # jpeg
    try:
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "g.png")
            Image.new("RGBA", (1080, 1350), (8, 11, 15, 255)).save(p)
            j = jpeg(p, tmp)
            b = Image.open(j)
            ok("jpeg 1080x1350, rgb", b.format == "JPEG" and b.size == (1080, 1350) and b.mode == "RGB")
            Image.new("RGB", (400, 1350)).save(p)
            try:
                jpeg(p, tmp)
                ok("falsches seitenverhaeltnis wird gestoppt", False)
            except Fehler:
                ok("falsches seitenverhaeltnis wird gestoppt", True)
    except ImportError:
        ok("pillow fehlt, jpeg nicht geprueft", False)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", nargs="?", choices=["faellig", "artefakt", "jpeg", "posten", "insights",
                                                  "kommentare", "antworten"])
    ap.add_argument("--ziel", default="out/ig")
    ap.add_argument("--png")
    ap.add_argument("--bild")
    ap.add_argument("--caption")
    ap.add_argument("--modus", default="trocken", choices=["trocken", "scharf"])
    ap.add_argument("--kommentar-id", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--nur-pruefen", action="store_true")
    ap.add_argument("--hand", action="store_true", help="faellig ohne zeitfenster und tagessperre, nur trocken")
    ap.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    now = dt.datetime.now(dt.timezone.utc)
    try:
        if a.befehl == "faellig":
            e, grund = faellig(now, json_laden(LOG_GRAFIK, {"laeufe": []}), json_laden(LOG_IG, {"posts": []}),
                               os.environ.get("IG_STOPP", ""), a.hand)
            ausgabe("faellig" if e else "nicht faellig, %s" % grund)
            if a.github_output:
                with open(a.github_output, "a", encoding="utf-8") as fh:
                    fh.write("faellig=%s\n" % ("1" if e else "0"))
            if e:
                Path(a.ziel).mkdir(parents=True, exist_ok=True)
                Path(a.ziel, "eintrag.json").write_text(json.dumps(e), encoding="utf-8")
        elif a.befehl == "artefakt":
            e = json.loads(Path(a.ziel, "eintrag.json").read_text(encoding="utf-8"))
            try:
                png, cap = artefakt(e, a.ziel)
            except KeinArtefakt as exc:
                # gruen bleiben, rot nur bei echten fehlern (Ben, 08.10.2026)
                ausgabe("nicht faellig, kein artefakt vom morgen (%s)" % exc)
                if a.github_output:
                    with open(a.github_output, "a", encoding="utf-8") as fh:
                        fh.write("gefunden=0\n")
                if not a.hand:
                    ops("instagram heute nicht faellig, kein artefakt vom morgen. %s" % exc)
                return 0
            if a.github_output:
                with open(a.github_output, "a", encoding="utf-8") as fh:
                    fh.write("gefunden=1\npng=%s\ncaption=%s\n" % (png, cap))
        elif a.befehl == "jpeg":
            out = jpeg(a.png, a.ziel)
            ausgabe("jpeg %s, %d bytes" % (out, out.stat().st_size))
            if a.github_output:
                with open(a.github_output, "a", encoding="utf-8") as fh:
                    fh.write("jpeg=%s\n" % out)
        elif a.befehl == "posten":
            if a.hand and a.modus == "scharf":
                raise Fehler("von hand nur trocken")
            ig = json.loads(Path(a.caption).read_text(encoding="utf-8"))
            bild = Path(a.bild)
            url = "%s/%s" % (SEITE, bild.as_posix())
            url_warten(url, bild.stat().st_size)
            ausgabe("caption\n%s" % ig["caption"])
            erg = posten(url, ig["caption"], a.modus)
            log = json_laden(LOG_IG, {"posts": []})
            log["posts"].append({"datum": ig["datum"], "form": ig["form"], "modus": a.modus,
                                 "container": erg["container"], "status": erg["status"],
                                 "media": erg.get("media", ""), "permalink": erg.get("permalink", ""),
                                 "bild": url, "zahl": ig.get("zahl"), "tag": ig.get("tag"),
                                 "herkunft": ig.get("herkunft"), "caption": ig["caption"],
                                 "caption_sha": hashlib.sha256(ig["caption"].encode()).hexdigest()[:12],
                                 "zeit_utc": now.isoformat(timespec="seconds")})
            json_schreiben(LOG_IG, log)
            ops("instagram %s, form %s, container %s, status %s%s" % (
                a.modus, ig["form"], erg["container"], erg["status"],
                (", " + erg.get("permalink", "")) if erg.get("media") else ", nicht veroeffentlicht"))
        elif a.befehl == "insights":
            insights(now)
        elif a.befehl == "kommentare":
            kommentare(now)
        elif a.befehl == "antworten":
            antworten(a.kommentar_id, a.text, a.nur_pruefen, now)
        else:
            ap.print_help()
    except Fehler as exc:
        ausgabe("ABBRUCH %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
