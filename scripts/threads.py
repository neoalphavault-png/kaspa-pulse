#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threads.py, Kaspa Pulse auf Threads (Ben, 14.10.2026).

VEROEFFENTLICHEN NUR MIT ZWEI SCHALTERN (Ben, 17.10.2026). "posten" legt den
Container an, wartet auf FINISHED und ruft threads_publish nur, wenn der
Lauf mit --modus scharf kommt UND die Variable THREADS_LIVE auf "scharf"
steht UND kein Trockenlauf ist (ZIEL=moderator). Sonst bleibt der
Container unveroeffentlicht, wie beim Instagram-Trockenlauf. Ein Lauf von
Hand (--hand) ist nie scharf.

DER TEXT kommt aus der Warteschlange data/threads-queue.json, wenn sie fuer
den Tag einen traegt, sonst aus der Tagesgrafik des Tages (der X-Text,
drei Zeilen, endet mit einer Frage, im Artefakt als -threads.json). Das
Bild ist das Threads-Bild der Tagesgrafik im eigenen Look, als JPEG auf
kaspapulse.com/ig/ gelegt wie das Instagram-Bild. Takt 17:10 Berlin von c2.

DAS TOKEN KOMMT AUS DER UMGEBUNG UND WIRD NIE GEDRUCKT. THREADS_TOKEN
steht als Secret in kaspa-pulse, nie in einer Datei, nie in einer Ausgabe.
urllib nennt die URL im Text einer HTTPError, und die Graph-API nimmt das
Token als Parameter - deshalb geht jede Ausgabe durch blind(), und das
Token steht in keiner URL, sondern im Authorization-Header.

    python3 scripts/threads.py me
    python3 scripts/threads.py faellig [--hand | --takt]
    python3 scripts/threads.py artefakt --ziel out/th
    python3 scripts/threads.py posten --bild URL --text-datei t.json --modus trocken|scharf
    python3 scripts/threads.py container --text "..." [--bild URL] [--thema Crypto]
    python3 scripts/threads.py wache --text "..."
    python3 scripts/threads.py --selbsttest

Was dieses Skript NICHT tut: es loescht nicht und es antwortet nicht. Und es erfindet keinen Text: der Text kommt aus der
Warteschlange oder aus der Tagesgrafik, nie aus dem Skript.
"""
import argparse
import datetime as dt
import json
import time
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

API = "https://graph.threads.net/v1.0"
ENV_TOKEN = "THREADS_TOKEN"
ENV_USER = "THREADS_USER_ID"
QUEUE = ROOT / "data" / "threads-queue.json"
LOG = ROOT / "data" / "threads-post-log.json"
# Threads nimmt 500 Zeichen. Wir bleiben darunter, damit nichts abgeschnitten
# wird, wenn Ben einen Satz nachtraegt.
TEXT_MAX = 480
POSTS_PRO_TAG = 2
THEMA = "Crypto"
ENV_LIVE = "THREADS_LIVE"
# 17:10 Berlin kommt der Takt von c2, nach Discord (09:00) und vor X (17:00
# geplant von Ben ist knapp davor). Bis 19:30 darf ein verspaeteter Lauf noch.
FENSTER_BERLIN = ((17, 0), (19, 30))
GRAFIK_LOG = ROOT / "data" / "tagesgrafik-log.json"


# ------------------------------------------------------------------ blenden

def blind(text, token=""):
    """Das Token taucht in keiner Ausgabe auf, auch nicht in Teilen."""
    text = str(text)
    if token:
        text = text.replace(token, "<token>")
        if len(token) >= 12:
            for n in (len(token), 24, 16, 12):
                for i in range(0, max(1, len(token) - n + 1)):
                    stueck = token[i:i + n]
                    if len(stueck) >= 12:
                        text = text.replace(stueck, "<token>")
    return text


def token():
    t = os.environ.get(ENV_TOKEN, "").strip()
    if not t:
        sys.exit("FEHLT: %s steht nicht in der Umgebung" % ENV_TOKEN)
    return t


# --------------------------------------------------------------------- api

def graph(weg, felder=None, post=False, tok=None, oeffner=None):
    """GET oder POST auf die Threads-API. Das Token geht in den Header."""
    tok = tok or token()
    url = "%s/%s" % (API, weg.lstrip("/"))
    daten = None
    if post:
        daten = urllib.parse.urlencode(felder or {}).encode("utf-8")
    elif felder:
        url = "%s?%s" % (url, urllib.parse.urlencode(felder))
    req = urllib.request.Request(url, data=daten, method="POST" if post else "GET")
    req.add_header("Authorization", "Bearer %s" % tok)
    req.add_header("User-Agent", "kaspa-pulse-threads/1.0")
    try:
        with (oeffner or urllib.request.urlopen)(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        leib = ""
        try:
            leib = e.read().decode("utf-8", "replace")[:600]
        except Exception:
            pass
        sys.exit(blind("threads-api http %s auf %s\n%s" % (e.code, weg, leib), tok))
    except (urllib.error.URLError, OSError) as e:
        sys.exit(blind("threads-api nicht erreichbar auf %s: %s" % (weg, e), tok))


# ------------------------------------------------------------------ wache

def wache(text, heute=None):
    """Befunde als Liste, leer heisst sauber.

    Geprueft wird mit der Hauswache aus tagesgrafik.pruefe_eine - dieselbe,
    die die Tagesgrafik und die Instagram-Entwuerfe durchlaufen: kein
    Doppelpunkt, kein Gedankenstrich, kein Pfeil, kein Link, keine fremde
    Chain, keine Kaufwoerter, '%' statt 'percent', keine Kursangabe. Dazu
    kommen die drei Regeln, die nur fuer Threads gelten."""
    from tagesgrafik import pruefe_eine, DATUM
    befunde = list(pruefe_eine(text, None, "threads-text"))
    if len(text) > TEXT_MAX:
        befunde.append("text ist %d zeichen lang, erlaubt sind %d" % (len(text), TEXT_MAX))
    if not text.strip().endswith("?"):
        befunde.append("der text endet nicht mit einer frage")
    # Jede Zahl mit ihrem Datum. Geprueft wird am Text, nicht am Versprechen:
    # steht eine Ziffer drin, muss auch ein Datum drin stehen.
    ohne_datum = DATUM.sub(" ", text.lower())
    ohne_datum = re.sub(r"\b(19|20)\d\d\b", " ", ohne_datum)
    if re.search(r"\d", ohne_datum) and not DATUM.search(text.lower()):
        befunde.append("eine zahl ohne datum im text")
    return befunde


# ---------------------------------------------------------- warteschlange

def warteschlange(tag, pfad=None):
    """Der Text fuer diesen Tag, oder None. Erfindet nichts.

    data/threads-queue.json ist {"JJJJ-MM-TT": "text", ...}. Fehlt der Tag,
    wird nicht gepostet - ein erfundener Post waere schlimmer als keiner."""
    p = Path(pfad or QUEUE)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    t = (d.get(tag) or "").strip()
    return t or None


def heute_schon(log, tag):
    """Wie viele Posts heute schon draussen sind."""
    return sum(1 for p in (log or {}).get("posts", []) if p.get("tag") == tag)


def darf_posten(log, tag, grenze=POSTS_PRO_TAG):
    return heute_schon(log, tag) < grenze


# ------------------------------------------------------------------ befehle

def me(tok=None, oeffner=None):
    d = graph("me", {"fields": "id,username"}, tok=tok, oeffner=oeffner)
    print("THREADS_USER_ID = %s" % d.get("id", "?"))
    print("username        = %s" % d.get("username", "?"))
    # Die ID ist kein Geheimnis und wird zur Variablen. Der erste Lauf hat sie
    # noch nicht, deshalb gibt die Probe sie an den naechsten Schritt weiter.
    ziel = os.environ.get("GITHUB_OUTPUT", "")
    if ziel:
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write("id=%s\nusername=%s\n" % (d.get("id", ""), d.get("username", "")))
    return d


def nutzer_id(tok=None, oeffner=None):
    """Die Threads-Nutzer-ID: aus der Umgebung, sonst selbst von /me geholt.

    WOFUER (Ben, 20.10.2026). THREADS_USER_ID gibt es als Variable nicht,
    und container() hat deshalb hart abgebrochen ("erst 'me' laufen
    lassen"). Damit war kein Trockenlauf moeglich, der etwas beweist: der
    Container-Schritt ist der EINZIGE, der Token und ID ueberhaupt
    benutzt, und er kam nie dazu.

    Die ID ist kein Geheimnis - sie ist die oeffentliche Konto-ID und
    gehoert als Repository-Variable eingetragen. Das Skript holt sie
    deshalb selbst und DRUCKT sie, damit sie aus dem Lauf-Log in die
    Variable wandern kann. DAS TOKEN NIE: es steht im Authorization-Header,
    in keiner URL und in keiner Ausgabe, und jede Fehlermeldung laeuft
    durch blind().

    Steht die Variable, wird /me nicht gefragt - ein Abruf weniger je Lauf."""
    wert = os.environ.get(ENV_USER, "").strip()
    if wert:
        if not re.fullmatch(r"\d+", wert):
            sys.exit("%s ist keine Zahl: %r" % (ENV_USER, wert))
        return wert
    print("%s steht nicht in der Umgebung, wird ueber /me geholt" % ENV_USER)
    wert = str(me(tok=tok, oeffner=oeffner).get("id", "") or "").strip()
    if not re.fullmatch(r"\d+", wert):
        sys.exit("/me liefert keine nutzer-id, %s bleibt leer" % ENV_USER)
    print("%s=%s als Repository-Variable eintragen, dann entfaellt dieser "
          "Abruf" % (ENV_USER, wert))
    return wert


def container(text, bild="", thema=THEMA, tok=None, oeffner=None):
    """Container anlegen und DORT AUFHOEREN. Kein threads_publish."""
    befunde = wache(text)
    if befunde:
        for b in befunde:
            print("WACHE: %s" % b, file=sys.stderr)
        sys.exit("der text haelt die wachen nicht ein, kein container")
    nutzer = nutzer_id(tok=tok, oeffner=oeffner)
    felder = {"media_type": "IMAGE" if bild else "TEXT", "text": text}
    if bild:
        felder["image_url"] = bild
    if thema:
        felder["topic_tag"] = thema
    d = graph("%s/threads" % nutzer, felder, post=True, tok=tok, oeffner=oeffner)
    print("container = %s" % d.get("id", "?"))
    print("NICHT veroeffentlicht. threads_publish laeuft in diesem stand nicht.")
    return d


# ------------------------------------------------------ der taegliche post

def json_laden(pfad, leer):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return leer


def faellig(now, log_grafik, log_th, hand=False):
    """(eintrag der tagesgrafik, None) oder (None, grund). --hand laesst
    Zeitfenster und Tagessperre weg und ist nie scharf."""
    import instagram
    import look_takt
    b = instagram.berlin(now)
    heute = b.date().isoformat()
    (h0, m0), (h1, m1) = FENSTER_BERLIN
    if not hand and not (h0, m0) <= (b.hour, b.minute) < (h1, m1):
        return None, "%02d:%02d berlin liegt nicht zwischen %02d:%02d und %02d:%02d" % (
            b.hour, b.minute, h0, m0, h1, m1)
    if not hand and look_takt.trockenlauf():
        return None, "trockenlauf, ZIEL=moderator, das threads-bild liegt in #moderator-only"
    if not hand and not darf_posten(log_th, heute, 1):
        return None, "heute (%s) schon auf threads" % heute
    eintrag = next((e for e in reversed(log_grafik.get("laeufe", [])) if e.get("datum") == heute), None)
    if not eintrag or not eintrag.get("messzeit_utc"):
        return None, "heute (%s) keine ausgelieferte tagesgrafik im log" % heute
    return eintrag, None


def artefakt(eintrag, ziel, gh=None):
    """Threads-Bild und -Text aus dem Lauf, der die Tagesgrafik ausgeliefert
    hat. Dieselbe Suche wie instagram.artefakt, nur andere Dateien."""
    import io
    import zipfile
    import instagram
    gh = gh or instagram.gh
    mz = eintrag["messzeit_utc"]
    stamm = "tagesgrafik-%s-form%02d" % (mz[:10], int(eintrag["form"]))
    runs = gh("actions/workflows/tagesgrafik.yml/runs?per_page=30&created=%%3E%%3D%s" % mz[:10])
    for run in runs.get("workflow_runs", []):
        for a in gh("actions/runs/%d/artifacts" % run["id"]).get("artifacts", []):
            if a.get("name") != "tagesgrafik" or a.get("expired"):
                continue
            z = zipfile.ZipFile(io.BytesIO(gh("actions/artifacts/%d/zip" % a["id"], roh=True)))
            namen = {Path(n).name: n for n in z.namelist()}
            png_n, txt_n = stamm + "-threads.png", stamm + "-threads.json"
            if png_n not in namen or txt_n not in namen:
                continue
            t = json.loads(z.read(namen[txt_n]).decode("utf-8"))
            if t.get("messzeit_utc") != mz:
                continue
            Path(ziel).mkdir(parents=True, exist_ok=True)
            png, txt = Path(ziel) / png_n, Path(ziel) / txt_n
            png.write_bytes(z.read(namen[png_n]))
            txt.write_bytes(z.read(namen[txt_n]))
            print("artefakt aus lauf %d, %s" % (run["id"], png.name))
            return png, txt
    raise LookupError("kein artefakt mit %s-threads und messzeit %s" % (stamm, mz))


def scharf(modus, hand=False):
    """Veroeffentlicht wird nur mit beiden Schaltern und ohne Trockenlauf."""
    import look_takt
    return (modus == "scharf" and not hand
            and os.environ.get(ENV_LIVE, "").strip().lower() == "scharf"
            and not look_takt.trockenlauf())


def posten(text, bild, modus, tag, log_pfad=None, hand=False, tok=None, oeffner=None,
           warte_takt=10, warte_max=300):
    """Container anlegen, auf FINISHED warten, nur scharf veroeffentlichen.
    Scharf steht der Post danach im Log, trocken nicht."""
    befunde = wache(text)
    if befunde:
        sys.exit("der text haelt die wachen nicht ein, kein container: %s" % "; ".join(befunde))
    tok = tok or token()
    nutzer = nutzer_id(tok=tok, oeffner=oeffner)
    felder = {"media_type": "IMAGE" if bild else "TEXT", "text": text, "topic_tag": THEMA}
    if bild:
        felder["image_url"] = bild
    cid = str(graph("%s/threads" % nutzer, felder, post=True, tok=tok, oeffner=oeffner).get("id", ""))
    if not re.fullmatch(r"\d+", cid):
        sys.exit("container ohne id")
    print("container %s angelegt" % cid)
    status, ende = "", time.time() + warte_max
    while time.time() < ende:
        status = graph(cid, {"fields": "status,error_message"}, tok=tok, oeffner=oeffner).get("status", "")
        print("container %s, status %s" % (cid, status))
        if status in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED"):
            break
        time.sleep(warte_takt)
    if status != "FINISHED":
        sys.exit("container %s endet mit status %s, nicht veroeffentlicht" % (cid, status or "-"))
    if not scharf(modus, hand):
        print("trocken, container %s bleibt unveroeffentlicht (modus %s, %s=%s, ziel %s)" % (
            cid, modus, ENV_LIVE, os.environ.get(ENV_LIVE, "") or "-", os.environ.get("ZIEL", "") or "-"))
        return {"container": cid, "status": status, "modus": "trocken"}
    m = graph("%s/threads_publish" % nutzer, {"creation_id": cid}, post=True, tok=tok, oeffner=oeffner)
    erg = {"tag": tag, "container": cid, "media": str(m.get("id", "")), "modus": "scharf",
           "bild": bild, "text": text}
    log = json_laden(log_pfad or LOG, {"posts": []})
    log.setdefault("posts", []).append(erg)
    Path(log_pfad or LOG).write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print("veroeffentlicht, media %s" % erg["media"])
    return erg


# -------------------------------------------------------------- selbsttest

def selbsttest():
    fehler = []
    gezaehlt = []

    def pruefe(was, ist, soll):
        gezaehlt.append(was)
        if ist != soll:
            fehler.append("%s: %r statt %r" % (was, ist, soll))
        print("%-52s %s" % (was, "ok" if ist == soll else "FALSCH"))

    tok = "THAAJxyzGEHEIMabcdefghijklmnopqrstuvwxyz0123456789"
    pruefe("token geblendet", "<token>" in blind("fehler mit %s" % tok, tok), True)
    pruefe("token nicht mehr lesbar", "GEHEIMabcdefghijkl" in blind(tok, tok), False)
    pruefe("ohne token bleibt text text", blind("alles gut", ""), "alles gut")

    gut = "the kaspa network hashrate on 14 oct is 338 PH, counted from the chain. what would make you check it?"
    pruefe("ein sauberer text hat keine befunde", wache(gut), [])
    pruefe("doppelpunkt faellt auf",
           any("doppelpunkt" in b for b in wache("today: what do you count?")), True)
    pruefe("gedankenstrich faellt auf",
           any("gedankenstrich" in b for b in wache("counted — not guessed, right?")), True)
    pruefe("pfeil faellt auf", any("pfeil" in b for b in wache("read it → here, ok?")), True)
    pruefe("percent statt prozentzeichen faellt auf",
           any("percent" in b for b in wache("up 5 percent on 14 oct, and you?")), True)
    pruefe("echtzeit-wort faellt auf",
           any("echtzeit" in b for b in wache("we watch it live on 14 oct, ok?")), True)
    pruefe("kaufwort faellt auf",
           any("wortliste" in b for b in wache("nobody should buy on 14 oct, right?")), True)
    pruefe("fremde chain faellt auf",
           any("chain" in b for b in wache("faster than bitcoin on 14 oct, really?")), True)
    pruefe("kursangabe faellt auf",
           any("kurs" in b for b in wache("the price on 14 oct, what now?")), True)
    pruefe("link faellt auf",
           any("link" in b for b in wache("more on kaspapulse.com on 14 oct, ok?")), True)
    pruefe("fehlende frage faellt auf",
           any("frage" in b for b in wache("the hashrate on 14 oct is 338 PH.")), True)
    pruefe("zahl ohne datum faellt auf",
           any("ohne datum" in b for b in wache("the hashrate is 338 PH, what now?")), True)
    pruefe("zu langer text faellt auf",
           any("zeichen lang" in b for b in wache("a " * 300 + "on 14 oct, ok?")), True)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp, "q.json")
        p.write_text(json.dumps({"2026-10-15": "  der text von morgen  ", "2026-10-16": "  "}),
                     encoding="utf-8")
        pruefe("warteschlange liefert den tag", warteschlange("2026-10-15", p), "der text von morgen")
        pruefe("leerer eintrag zaehlt als keiner", warteschlange("2026-10-16", p), None)
        pruefe("fehlender tag zaehlt als keiner", warteschlange("2026-10-17", p), None)
        pruefe("ohne datei kein text", warteschlange("2026-10-15", Path(tmp, "weg.json")), None)

    log = {"posts": [{"tag": "2026-10-15"}, {"tag": "2026-10-15"}, {"tag": "2026-10-14"}]}
    pruefe("zwei posts heute sind genug", darf_posten(log, "2026-10-15"), False)
    pruefe("einer ist noch frei", darf_posten(log, "2026-10-14"), True)
    pruefe("an einem leeren tag ist frei", darf_posten(log, "2026-10-16"), True)
    pruefe("zaehlen stimmt", heute_schon(log, "2026-10-15"), 2)

    gesehen = {}

    class Antwort:
        def __init__(self, d):
            self.d = d

        def read(self):
            return json.dumps(self.d).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def oeffner(req, timeout=0):
        gesehen["url"] = req.full_url
        gesehen["kopf"] = dict(req.header_items())
        gesehen["leib"] = (req.data or b"").decode()
        return Antwort({"id": "17890", "username": "kaspapulse"})

    os.environ[ENV_USER] = "99"
    me(tok=tok, oeffner=oeffner)
    pruefe("me geht auf /me", gesehen["url"].endswith("/me?fields=id%2Cusername"), True)
    pruefe("das token steht im header, nicht in der url",
           ("Bearer " + tok) in gesehen["kopf"].values() and tok not in gesehen["url"], True)
    container(gut, thema="Crypto", tok=tok, oeffner=oeffner)
    pruefe("container geht auf /<id>/threads", gesehen["url"].endswith("/99/threads"), True)
    pruefe("text als TEXT ohne bild", "media_type=TEXT" in gesehen["leib"], True)
    pruefe("das thema steht drin", "topic_tag=Crypto" in gesehen["leib"], True)
    container(gut, bild="https://kaspapulse.com/ig/x.jpg", tok=tok, oeffner=oeffner)
    pruefe("mit bild als IMAGE", "media_type=IMAGE" in gesehen["leib"], True)
    pruefe("die bildadresse steht drin", "image_url=https" in gesehen["leib"], True)
    del os.environ[ENV_USER]

    # --- DIE NUTZER-ID HOLT SICH DAS SKRIPT SELBST (Ben, 20.10.2026) ---
    # Jeder Fall hier stand dem Trockenlauf im Weg oder deckt ihn ab.
    import io as _io
    import contextlib as _ctx

    def _mit_ausgabe(fn):
        """(ergebnis_oder_SystemExit, gedruckte ausgabe)."""
        puffer = _io.StringIO()
        try:
            with _ctx.redirect_stdout(puffer):
                return fn(), puffer.getvalue()
        except SystemExit as exc:
            return exc, puffer.getvalue()

    os.environ[ENV_USER] = "4711"
    gesehen.clear()
    wert, _aus = _mit_ausgabe(lambda: nutzer_id(tok=tok, oeffner=oeffner))
    pruefe("steht die variable, gilt sie", wert, "4711")
    pruefe("und /me wird nicht gefragt", gesehen.get("url"), None)

    os.environ[ENV_USER] = "siebzehn"
    wert, _aus = _mit_ausgabe(lambda: nutzer_id(tok=tok, oeffner=oeffner))
    pruefe("eine nicht-zahl in der variable stoppt",
           isinstance(wert, SystemExit) and ENV_USER in str(wert), True)

    del os.environ[ENV_USER]
    gesehen.clear()
    wert, aus = _mit_ausgabe(lambda: nutzer_id(tok=tok, oeffner=oeffner))
    pruefe("fehlt sie, kommt sie von /me", wert, "17890")
    pruefe("und zwar wirklich von /me",
           (gesehen.get("url") or "").endswith("/me?fields=id%2Cusername"), True)
    pruefe("die id steht im log", "17890" in aus, True)
    pruefe("mit dem hinweis, sie einzutragen",
           "als Repository-Variable eintragen" in aus, True)
    # DAS TOKEN STEHT IN KEINER AUSGABE. Die ID ist kein Geheimnis, das
    # Token ist eines - und dieser Weg druckt zum ersten Mal etwas, das
    # aus einer Token-Antwort kommt.
    pruefe("das token steht nicht im log", tok in aus, False)
    pruefe("auch kein stueck davon", tok[2:22] in aus, False)

    # Liefert /me keine id, wird nicht geraten.
    def _ohne_id(req, timeout=0):
        return Antwort({"username": "kaspapulse"})
    wert, _aus = _mit_ausgabe(lambda: nutzer_id(tok=tok, oeffner=_ohne_id))
    pruefe("ohne id von /me stoppt der lauf",
           isinstance(wert, SystemExit) and "keine nutzer-id" in str(wert), True)

    # Und der Container laeuft jetzt ohne die Variable durch - das ist der
    # Schritt, der am 19.10. uebersprungen wurde.
    gesehen.clear()
    _r, _aus = _mit_ausgabe(
        lambda: container(gut, thema="Crypto", tok=tok, oeffner=oeffner))
    pruefe("der container nimmt die geholte id",
           (gesehen.get("url") or "").endswith("/17890/threads"), True)

    # der taegliche post (Ben, 17.10.2026)
    def zeit(h, m):
        return dt.datetime(2026, 10, 20, h, m, tzinfo=dt.timezone.utc)     # mesz, +2
    lg = {"laeufe": [{"datum": "2026-10-20", "form": 4, "messzeit_utc": "2026-10-20T05:30:00+00:00"}]}
    alt = {k: os.environ.pop(k, None) for k in ("ZIEL", ENV_LIVE)}
    pruefe("faellig um 17:10 berlin", faellig(zeit(15, 10), lg, {"posts": []})[0] is not None, True)
    pruefe("nicht faellig um 16:30 berlin", faellig(zeit(14, 30), lg, {"posts": []})[0] is None, True)
    pruefe("nicht doppelt am tag",
           faellig(zeit(15, 10), lg, {"posts": [{"tag": "2026-10-20"}]})[0] is None, True)
    pruefe("ohne tagesgrafik nicht faellig", faellig(zeit(15, 10), {"laeufe": []}, {"posts": []})[0] is None, True)
    os.environ["ZIEL"] = "moderator"
    pruefe("im trockenlauf nicht faellig", faellig(zeit(15, 10), lg, {"posts": []})[0] is None, True)
    pruefe("im trockenlauf nie scharf", scharf("scharf"), False)
    os.environ["ZIEL"] = ""
    pruefe("ohne THREADS_LIVE nicht scharf", scharf("scharf"), False)
    os.environ[ENV_LIVE] = "scharf"
    pruefe("beide schalter scharf", scharf("scharf"), True)
    pruefe("von hand nie scharf", scharf("scharf", hand=True), False)
    pruefe("modus trocken bleibt trocken", scharf("trocken"), False)

    wege = []

    def api(req, timeout=0):
        wege.append((req.get_method(), req.full_url.split("v1.0/")[1].split("?")[0],
                     (req.data or b"").decode()))
        weg = wege[-1][1]
        if weg == "me":
            return Antwort({"id": "99", "username": "kaspapulse"})
        if weg == "99/threads":
            return Antwort({"id": "555"})
        if weg == "555":
            return Antwort({"status": "FINISHED"})
        return Antwort({"id": "777"})
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp, "log.json")
        e = posten(gut, "https://kaspapulse.com/ig/x-threads.jpg", "scharf", "2026-10-20", lp,
                   tok=tok, oeffner=api, warte_takt=0)
        pruefe("scharf ruft threads_publish mit der container-id",
               ("POST", "99/threads_publish", "creation_id=555") in wege, True)
        pruefe("scharf steht im log", json.loads(lp.read_text())["posts"][0]["media"], "777")
        pruefe("bild und thema im container", any("image_url=https" in w[2] and "topic_tag=Crypto" in w[2]
                                                  for w in wege), True)
        wege.clear()
        os.environ[ENV_LIVE] = ""
        e = posten(gut, "", "scharf", "2026-10-21", lp, tok=tok, oeffner=api, warte_takt=0)
        pruefe("ohne THREADS_LIVE kein threads_publish",
               any(w[1].endswith("threads_publish") for w in wege) or e["modus"] != "trocken", False)
        pruefe("trocken nicht im log", len(json.loads(lp.read_text())["posts"]), 1)
    for k, v in alt.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    print("\n%d faelle, %d falsch" % (len(gezaehlt), len(fehler)))
    for f in fehler:
        print("  " + f)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", nargs="?",
                    choices=["me", "container", "wache", "faellig", "artefakt", "posten"])
    ap.add_argument("--text", default="")
    ap.add_argument("--text-datei", default="", help="-threads.json aus dem artefakt")
    ap.add_argument("--ziel", default="out/th")
    ap.add_argument("--modus", default="trocken", choices=["trocken", "scharf"])
    ap.add_argument("--hand", action="store_true", help="ohne fenster und tagessperre, nie scharf")
    ap.add_argument("--takt", action="store_true", help="vom takt auf c2, fenster und sperre gelten")
    ap.add_argument("--bild", default="")
    ap.add_argument("--thema", default=THEMA)
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.befehl == "me":
        me()
    elif a.befehl == "wache":
        befunde = wache(a.text)
        for b in befunde:
            print("WACHE: %s" % b)
        print("sauber" if not befunde else "%d befunde" % len(befunde))
        return 1 if befunde else 0
    elif a.befehl == "container":
        container(a.text, a.bild, a.thema)
    elif a.befehl in ("faellig", "artefakt"):
        now = dt.datetime.now(dt.timezone.utc)
        e, grund = faellig(now, json_laden(GRAFIK_LOG, {"laeufe": []}), json_laden(LOG, {"posts": []}),
                           a.hand)
        aus = os.environ.get("GITHUB_OUTPUT", "")
        if e is None:
            print("nicht faellig, %s" % grund)
            zeilen = "faellig=0\n"
        elif a.befehl == "faellig":
            print("faellig, tagesgrafik form %s" % e["form"])
            zeilen = "faellig=1\n"
        else:
            try:
                png, txt = artefakt(e, a.ziel)
                zeilen = "faellig=1\ngefunden=1\npng=%s\ntext=%s\n" % (png, txt)
            except LookupError as exc:
                print("kein artefakt, %s" % exc)
                zeilen = "faellig=1\ngefunden=0\n"
        if aus:
            with open(aus, "a", encoding="utf-8") as fh:
                fh.write(zeilen)
    elif a.befehl == "posten":
        import instagram
        tag = instagram.berlin(dt.datetime.now(dt.timezone.utc)).date().isoformat()
        text = warteschlange(tag) or (json_laden(a.text_datei, {}).get("text", "") if a.text_datei else a.text)
        if not text:
            sys.exit("kein text, weder warteschlange noch tagesgrafik")
        posten(text, a.bild, a.modus, tag, hand=a.hand)
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
