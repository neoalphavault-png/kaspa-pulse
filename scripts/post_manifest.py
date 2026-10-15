#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""post_manifest.py - eine Zeile je veroeffentlichtem Post.

WARUM ES DAS GIBT
Ohne Manifest ist jede Auswertung ein Ratespiel. Eine Reichweite von 4.100
sagt nichts, solange niemand weiss, welches Layout, welche Variante und
welcher Haken dahinter standen. Das Manifest ist die eine Stelle, an der
der Post beschrieben wird, bevor irgendeine Zahl dazukommt: geschrieben im
Moment des Postens, aus der Automatik heraus, ohne Nacharbeit.

Es ist absichtlich eine .jsonl: eine Zeile anhaengen ist atomar genug fuer
zwei Laeufe, die sich ueberschneiden, und eine kaputte Zeile kostet nicht
die ganze Datei. Gelesen wird zeilenweise, defekte Zeilen werden gezaehlt
und uebersprungen, nicht verschwiegen.

    data/insights/manifest.jsonl

FELDER (Ben, 15.10.2026)
    post_id       die id des Posts beim Kanal, als Text
    kanal         instagram | threads | x
    zeit_berlin   Postzeit in Berliner Zeit, mit Zeitzone
    format        bild | karussell | reel | story | text
    look          Name des Layouts, bei reinem Text "-"
    variante      A | B | -
    hook          Text in Sekunde 0, oder die erste Zeile
    laenge_s      Laenge in Sekunden, nur bei reel und story
    hashtags      Anzahl der Hashtags
    quelle        auto | hand
Dazu permalink (wenn bekannt) und eingetragen (UTC, wann die Zeile kam).

DIESELBE DATEI LIEGT IN BEIDEN REPOS
kaspa-pulse postet das Tagesbild und Threads, pulse-studio das Reel. Beide
brauchen dieselbe Zeile im selben Format, darum liegt dieses Skript in
kaspa-pulse/scripts/ und in pulse-studio/scripts/ - Wort fuer Wort gleich,
wie x_post.py. Geaendert wird es in kaspa-pulse und dann hierher kopiert.
Geschrieben wird immer in das eigene Repo; der Sammler in kaspa-pulse liest
beide Dateien (UHRWERK_MANIFEST, siehe kaspa-pulse/docs/uhrwerk.md).

GEHEIMNISSE
Im Manifest steht nie ein Token. Jede Zeile laeuft vor dem Schreiben durch
sauber(); findet sich darin trotzdem etwas, das wie ein Token aussieht,
bricht der Lauf ab, statt die Zeile zu schreiben.

    python3 scripts/post_manifest.py --eintragen --kanal instagram \
        --post-id 17900000000000000 --format bild --look kp-nod --variante A \
        --hook "338 PH" --hashtags 4 --quelle auto
    python3 scripts/post_manifest.py --eintragen --kanal instagram \
        --post-id 179... --format bild --look kp-nod --caption-datei data/ig-caption.json
    python3 scripts/post_manifest.py --lesen --kanal instagram --letzte 10
    python3 scripts/post_manifest.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
# GESCHRIEBEN WIRD IMMER NUR IN DIE ERSTE DATEI, GELESEN AUS ALLEN.
# Jedes Repo schreibt in sein eigenes data/insights/manifest.jsonl: der
# Tagespost in kaspa-pulse, das Reel in pulse-studio. Ein Lauf auf GitHub
# kann nicht in das andere Repo schreiben, und ein zweiter Schreibweg waere
# ein zweiter Weg, auf dem etwas schiefgeht. Der Sammler liest darum beide
# Dateien. UHRWERK_MANIFEST nennt sie, getrennt wie ein Suchpfad
# (":" unter Linux); in uhrwerk.yml steht dort die eigene Datei zuerst und
# die aus der zweiten Auscheckung dahinter.
def _manifeste():
    roh = os.environ.get("UHRWERK_MANIFEST", "").strip()
    if roh:
        return [Path(t) for t in roh.split(os.pathsep) if t.strip()]
    return [REPO / "data" / "insights" / "manifest.jsonl"]


MANIFESTE = _manifeste()
MANIFEST = MANIFESTE[0]
LOG_IG = REPO / "data" / "instagram-log.json"
LOG_THREADS = REPO / "data" / "threads-post-log.json"

KANAELE = ("instagram", "threads", "x")
FORMATE = ("bild", "karussell", "reel", "story", "text")
VARIANTEN = ("A", "B", "-")
QUELLEN = ("auto", "hand")
MIT_LAENGE = ("reel", "story")
FELDER = ("post_id", "kanal", "zeit_berlin", "format", "look", "variante",
          "hook", "laenge_s", "hashtags", "quelle")
HOOK_MAX = 200


class Fehler(Exception):
    pass


# ---------------------------------------------------------------- geheimnisse

def sauber(text):
    """Dieselbe Maske wie in instagram.py und threads.py: nichts, was wie ein
    Token aussieht, verlaesst dieses Skript."""
    t = str(text)
    for name in ("INSTAGRAM_PAGE_TOKEN", "THREADS_TOKEN", "DISCORD_WEBHOOK_OPS",
                 "GITHUB_TOKEN", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
                 "X_API_KEY", "X_API_SECRET", "BREVO_API_KEY"):
        wert = os.environ.get(name, "")
        if len(wert) >= 8:
            t = t.replace(wert, "***")
    t = re.sub(r"(access_token|token|client_secret|appsecret_proof)=[^&\s\"']+", r"\1=***", t, flags=re.I)
    t = re.sub(r"(\"(?:access_token|token|client_secret)\"\s*:\s*\")[^\"]*\"", r"\1***\"", t, flags=re.I)
    t = re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1***", t)
    t = re.sub(r"\bEA[A-Za-z0-9]{20,}\b", "***", t)
    t = re.sub(r"\bTH[A-Za-z0-9_\-]{20,}\b", "***", t)
    t = re.sub(r"https://(discord(app)?\.com)/api/webhooks/\S+", r"https://\1/api/webhooks/***", t)
    return t


def ausgabe(*teile):
    print(sauber(" ".join(str(t) for t in teile)))


# ---------------------------------------------------------------- zeit

def berlin_offset(when):
    """Berlin ohne zoneinfo-Datenbank: Sommerzeit vom letzten Sonntag im Maerz
    bis zum letzten Sonntag im Oktober, je 01:00 UTC."""
    def letzter_sonntag(jahr, monat):
        d = dt.date(jahr + (monat == 12), monat % 12 + 1, 1) - dt.timedelta(days=1)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    u = when.astimezone(dt.timezone.utc).replace(tzinfo=None)
    an = dt.datetime.combine(letzter_sonntag(u.year, 3), dt.time(1, 0))
    aus = dt.datetime.combine(letzter_sonntag(u.year, 10), dt.time(1, 0))
    return 2 if an <= u < aus else 1


def jetzt_berlin(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    tz = dt.timezone(dt.timedelta(hours=berlin_offset(now)))
    return now.astimezone(tz).isoformat(timespec="seconds")


# ---------------------------------------------------------------- lesen

def lesen(pfad=None):
    """Alle Zeilen als Liste. Defekte Zeilen werden uebersprungen und als
    zweiter Rueckgabewert gezaehlt, damit niemand still Daten verliert."""
    p = Path(pfad or MANIFEST)
    zeilen, kaputt = [], 0
    if not p.exists():
        return zeilen, kaputt
    for roh in p.read_text(encoding="utf-8").splitlines():
        if not roh.strip():
            continue
        try:
            d = json.loads(roh)
        except ValueError:
            kaputt += 1
            continue
        if isinstance(d, dict) and d.get("post_id"):
            zeilen.append(d)
        else:
            kaputt += 1
    return zeilen, kaputt


def alle(pfade=None):
    """Alle Zeilen aus allen Manifesten, der Post nur einmal. Die erste
    Datei gewinnt, wenn dieselbe id zweimal auftaucht."""
    zeilen, kaputt, gesehen = [], 0, set()
    for p in (pfade or MANIFESTE):
        z, k = lesen(p)
        kaputt += k
        for e in z:
            schl = (e.get("kanal"), str(e.get("post_id")))
            if schl in gesehen:
                continue
            gesehen.add(schl)
            zeilen.append(e)
    return zeilen, kaputt


def schon_da(post_id, kanal, pfad=None):
    zeilen, _ = lesen(pfad)
    return any(str(z.get("post_id")) == str(post_id) and z.get("kanal") == kanal for z in zeilen)


def letzte(kanal, n, pfad=None):
    zeilen, _ = lesen(pfad)
    aus = [z for z in zeilen if z.get("kanal") == kanal]
    return aus[-n:] if n else aus


# ---------------------------------------------------------------- caption

# ein hashtag steht am anfang oder nach einem leerzeichen. die raute in
# kaspapulse.com/#subscribe und in a&#x27;b ist keines.
HASHTAG = re.compile(r"(?<![^\s(\[])#([A-Za-z][A-Za-z0-9_]{1,59})")


def hashtags_zaehlen(text):
    return len(HASHTAG.findall(text or ""))


def erste_zeile(text):
    for z in (text or "").splitlines():
        if z.strip():
            return z.strip()[:HOOK_MAX]
    return ""


def aus_caption(pfad):
    """Haken und Hashtag-Zahl aus einer Caption-Datei. Nimmt die json-Form der
    Tagesgrafik ({"caption": "..."}) und genauso eine reine Textdatei."""
    roh = Path(pfad).read_text(encoding="utf-8")
    try:
        d = json.loads(roh)
        text = d.get("caption", "") if isinstance(d, dict) else ""
    except ValueError:
        text = roh
    if not text.strip():
        raise Fehler("in %s steht keine caption" % Path(pfad).name)
    return erste_zeile(text), hashtags_zaehlen(text)


# ---------------------------------------------------------------- schreiben

def pruefe(e):
    """Jede Zeile wird vor dem Schreiben geprueft. Eine Zeile, die hier
    durchrutscht, verdirbt spaeter jede Auswertung still."""
    for f in FELDER:
        if f not in e:
            raise Fehler("feld %s fehlt" % f)
    if not re.fullmatch(r"[A-Za-z0-9_.:\-]{1,64}", str(e["post_id"])):
        raise Fehler("post_id sieht nicht aus wie eine id, %r" % e["post_id"])
    if e["kanal"] not in KANAELE:
        raise Fehler("kanal %r, erlaubt %s" % (e["kanal"], ", ".join(KANAELE)))
    if e["format"] not in FORMATE:
        raise Fehler("format %r, erlaubt %s" % (e["format"], ", ".join(FORMATE)))
    if e["variante"] not in VARIANTEN:
        raise Fehler("variante %r, erlaubt %s" % (e["variante"], ", ".join(VARIANTEN)))
    if e["quelle"] not in QUELLEN:
        raise Fehler("quelle %r, erlaubt %s" % (e["quelle"], ", ".join(QUELLEN)))
    if not str(e["look"]).strip():
        raise Fehler("look leer, bei reinem text bitte -")
    if not str(e["hook"]).strip():
        raise Fehler("hook leer")
    if len(str(e["hook"])) > HOOK_MAX:
        raise Fehler("hook laenger als %d zeichen" % HOOK_MAX)
    if not isinstance(e["hashtags"], int) or e["hashtags"] < 0:
        raise Fehler("hashtags ist keine zahl ab null, %r" % e["hashtags"])
    laenge = e["laenge_s"]
    if e["format"] in MIT_LAENGE:
        if not isinstance(laenge, (int, float)) or laenge <= 0:
            raise Fehler("format %s braucht laenge_s" % e["format"])
    elif laenge is not None:
        raise Fehler("laenge_s nur bei %s" % " und ".join(MIT_LAENGE))
    try:
        dt.datetime.fromisoformat(str(e["zeit_berlin"]))
    except ValueError:
        raise Fehler("zeit_berlin nicht lesbar, %r" % e["zeit_berlin"])
    if dt.datetime.fromisoformat(str(e["zeit_berlin"])).utcoffset() is None:
        raise Fehler("zeit_berlin ohne zeitzone, %r" % e["zeit_berlin"])
    return e


def eintragen(kanal, post_id, format_, look, hook, hashtags, quelle="auto",
              variante="-", laenge_s=None, permalink="", zeit_berlin="",
              pfad=None, now=None):
    """Haengt eine Zeile an. Ein Post, der schon im Manifest steht, wird nicht
    doppelt geschrieben - der Sammler zaehlt sonst zweimal."""
    p = Path(pfad or MANIFEST)
    e = {"post_id": str(post_id), "kanal": kanal,
         "zeit_berlin": zeit_berlin or jetzt_berlin(now),
         "format": format_, "look": look or "-", "variante": variante or "-",
         "hook": erste_zeile(hook), "laenge_s": laenge_s,
         "hashtags": int(hashtags), "quelle": quelle}
    if permalink:
        e["permalink"] = permalink
    pruefe(e)
    if schon_da(e["post_id"], kanal, p):
        ausgabe("manifest: %s %s steht schon drin, nichts geschrieben" % (kanal, e["post_id"]))
        return None
    e["eingetragen"] = (now or dt.datetime.now(dt.timezone.utc)).astimezone(
        dt.timezone.utc).isoformat(timespec="seconds")
    zeile = json.dumps(e, ensure_ascii=False, sort_keys=True)
    if sauber(zeile) != zeile:
        raise Fehler("in der zeile stand etwas, das wie ein token aussieht, nichts geschrieben")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(zeile + "\n")
    ausgabe("manifest: %s %s, %s/%s, variante %s, %d hashtags" % (
        kanal, e["post_id"], e["format"], e["look"], e["variante"], e["hashtags"]))
    return e


def eintragen_still(**kw):
    """Fuer die Aufrufer in der Automatik: ein Manifest, das nicht geschrieben
    werden kann, darf keinen Post scheitern lassen. Der Post ist dann drau-
    ssen, die Zeile holt die Montagsroutine nach."""
    try:
        return eintragen(**kw)
    except (Fehler, OSError, ValueError, TypeError) as exc:
        ausgabe("manifest nicht geschrieben, %s" % exc)
        return None


# ---------------------------------------------------------------- nachtrag

def _ig_zeilen(log):
    """Aus data/instagram-log.json die veroeffentlichten Posts. Die Postzeit
    steht dort als UTC (zeit_utc), die form ist der look."""
    for p in log.get("posts", []):
        if not p.get("media") or p.get("modus") != "scharf":
            continue
        cap = p.get("caption", "") or p.get("zahl_text", "") or "-"
        when = p.get("zeit_utc", "")
        try:
            berlin = jetzt_berlin(dt.datetime.fromisoformat(when)) if when else ""
        except ValueError:
            berlin = ""
        yield dict(kanal="instagram", post_id=str(p["media"]), format_="bild",
                   look="tagesgrafik-form%02d" % int(p.get("form") or 0),
                   hook=cap, hashtags=hashtags_zaehlen(cap), quelle="auto",
                   variante=p.get("variante", "-") or "-",
                   permalink=p.get("permalink", ""), zeit_berlin=berlin)


def _threads_zeilen(log):
    for p in log.get("posts", []):
        pid = p.get("id") or p.get("post") or p.get("media")
        if not pid:
            continue
        text = p.get("text", "") or "-"
        when = p.get("zeit_utc", "") or p.get("zeit", "")
        try:
            berlin = jetzt_berlin(dt.datetime.fromisoformat(when)) if when else ""
        except ValueError:
            berlin = ""
        yield dict(kanal="threads", post_id=str(pid), format_="text", look="-",
                   hook=text, hashtags=hashtags_zaehlen(text), quelle="auto",
                   variante=p.get("variante", "-") or "-",
                   permalink=p.get("permalink", ""), zeit_berlin=berlin)


def nachtragen(pfad=None, ig=None, threads=None, now=None):
    """Einmaliger Nachtrag der schon veroeffentlichten Posts aus den alten
    Logs. Laeuft wiederholbar: was im Manifest steht, bleibt unberuehrt.
    Ohne Postzeit im Log wird nichts geraten - die Zeile faellt weg und
    steht im Bericht, Ben traegt sie montags von Hand nach."""
    neu, schon, ohne_zeit = 0, 0, []
    quellen = ((_ig_zeilen, json.loads(Path(ig or LOG_IG).read_text(encoding="utf-8"))
                if Path(ig or LOG_IG).exists() else {}),
               (_threads_zeilen, json.loads(Path(threads or LOG_THREADS).read_text(encoding="utf-8"))
                if Path(threads or LOG_THREADS).exists() else {}))
    for fn, log in quellen:
        for kw in fn(log):
            if not kw["zeit_berlin"]:
                ohne_zeit.append("%s %s" % (kw["kanal"], kw["post_id"]))
                continue
            if schon_da(kw["post_id"], kw["kanal"], pfad):
                schon += 1
                continue
            if eintragen(pfad=pfad, now=now, **kw):
                neu += 1
    ausgabe("nachtrag: %d neu, %d standen schon drin%s" % (
        neu, schon, ", %d ohne postzeit (%s)" % (len(ohne_zeit), ", ".join(ohne_zeit[:5]))
        if ohne_zeit else ""))
    return {"neu": neu, "schon": schon, "ohne_zeit": ohne_zeit}


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import tempfile
    n = [0]

    def ok(was, bedingung):
        n[0] += 1
        print("%s %s" % ("ok  " if bedingung else "FEHL", was))
        if not bedingung:
            raise SystemExit(1)

    def hebt(was, fn, teil=""):
        n[0] += 1
        try:
            fn()
        except Fehler as exc:
            treffer = teil in str(exc)
            print("%s %s%s" % ("ok  " if treffer else "FEHL", was,
                               "" if treffer else " (meldung: %s)" % exc))
            if not treffer:
                raise SystemExit(1)
            return
        print("FEHL %s (kein abbruch)" % was)
        raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp, "manifest.jsonl")
        gut = dict(kanal="instagram", post_id="17900000000000001", format_="bild",
                   look="kp-nod", hook="338 PH\nzweite zeile", hashtags=4,
                   quelle="auto", variante="A", pfad=p)
        e = eintragen(**gut)
        ok("eine zeile geschrieben", e is not None and p.exists())
        ok("hook ist die erste nicht leere zeile", e["hook"] == "338 PH")
        ok("eingetragen in UTC", e["eingetragen"].endswith("+00:00"))
        ok("zeit_berlin traegt zeitzone", dt.datetime.fromisoformat(e["zeit_berlin"]).utcoffset() is not None)
        ok("derselbe post kommt nicht zweimal", eintragen(**gut) is None)
        zeilen, kaputt = lesen(p)
        ok("gelesen wird genau eine zeile", len(zeilen) == 1 and kaputt == 0)

        eintragen(kanal="threads", post_id="18000000000000002", format_="text",
                  look="-", hook="one number a day", hashtags=0, quelle="hand", pfad=p)
        ok("zweiter kanal, reiner text", len(letzte("threads", 5, p)) == 1)
        ok("letzte() trennt die kanaele", len(letzte("instagram", 5, p)) == 1)

        eintragen(kanal="instagram", post_id="17900000000000003", format_="reel",
                  look="kp-nod", hook="this week's number", hashtags=3,
                  variante="B", laenge_s=31, pfad=p)
        ok("reel mit laenge geht durch", letzte("instagram", 1, p)[0]["laenge_s"] == 31)

        hebt("reel ohne laenge bricht ab",
             lambda: eintragen(kanal="instagram", post_id="x1", format_="reel",
                               look="kp-nod", hook="h", hashtags=0, pfad=p), "braucht laenge_s")
        hebt("bild mit laenge bricht ab",
             lambda: eintragen(kanal="instagram", post_id="x2", format_="bild",
                               look="kp-nod", hook="h", hashtags=0, laenge_s=9, pfad=p), "nur bei reel")
        hebt("fremder kanal bricht ab",
             lambda: eintragen(kanal="tiktok", post_id="x3", format_="bild",
                               look="a", hook="h", hashtags=0, pfad=p), "kanal")
        hebt("fremdes format bricht ab",
             lambda: eintragen(kanal="x", post_id="x4", format_="tweet",
                               look="a", hook="h", hashtags=0, pfad=p), "format")
        hebt("fremde variante bricht ab",
             lambda: eintragen(kanal="x", post_id="x5", format_="text", look="-",
                               hook="h", hashtags=0, variante="C", pfad=p), "variante")
        hebt("fremde quelle bricht ab",
             lambda: eintragen(kanal="x", post_id="x6", format_="text", look="-",
                               hook="h", hashtags=0, quelle="roboter", pfad=p), "quelle")
        hebt("leerer hook bricht ab",
             lambda: eintragen(kanal="x", post_id="x7", format_="text", look="-",
                               hook="   ", hashtags=0, pfad=p), "hook leer")
        hebt("leerer look bricht ab",
             lambda: eintragen(kanal="x", post_id="x8", format_="text", look=" ",
                               hook="h", hashtags=0, pfad=p), "look leer")
        hebt("post_id mit leerzeichen bricht ab",
             lambda: eintragen(kanal="x", post_id="17 900", format_="text", look="-",
                               hook="h", hashtags=0, pfad=p), "post_id")
        hebt("zeit ohne zeitzone bricht ab",
             lambda: eintragen(kanal="x", post_id="x9", format_="text", look="-",
                               hook="h", hashtags=0, zeit_berlin="2026-10-15T09:31:00", pfad=p),
             "ohne zeitzone")
        ok("nach den abbruechen stehen weiter drei zeilen", len(lesen(p)[0]) == 3)

        os.environ["THREADS_TOKEN"] = "TH" + "a" * 40
        try:
            hebt("ein token im hook bricht ab",
                 lambda: eintragen(kanal="threads", post_id="xa", format_="text", look="-",
                                   hook=os.environ["THREADS_TOKEN"], hashtags=0, pfad=p),
                 "token")
        finally:
            del os.environ["THREADS_TOKEN"]

        with open(p, "a", encoding="utf-8") as fh:
            fh.write("{kaputt\n\n")
        zeilen, kaputt = lesen(p)
        ok("kaputte zeile wird gezaehlt, nicht verschluckt", len(zeilen) == 3 and kaputt == 1)

        ok("eintragen_still meldet und laesst den post leben",
           eintragen_still(kanal="x", post_id="xb", format_="reel", look="-",
                           hook="h", hashtags=0, pfad=p) is None)

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp, "manifest.jsonl")
        iglog = Path(tmp, "ig.json")
        iglog.write_text(json.dumps({"posts": [
            {"datum": "2026-10-15", "form": 2, "modus": "scharf", "media": "991",
             "permalink": "https://www.instagram.com/p/A/", "caption": "5.51% at one address\n\n#kaspa",
             "zeit_utc": "2026-10-15T07:30:20+00:00"},
            {"datum": "2026-10-14", "form": 9, "modus": "trocken", "media": "",
             "caption": "nicht raus", "zeit_utc": "2026-10-14T07:30:00+00:00"},
            {"datum": "2026-10-13", "form": 3, "modus": "scharf", "media": "992",
             "caption": "ohne zeit", "zeit_utc": ""},
        ]}), encoding="utf-8")
        thlog = Path(tmp, "th.json")
        thlog.write_text(json.dumps({"posts": [
            {"tag": "2026-10-15", "id": "7001", "text": "one number a day?",
             "zeit_utc": "2026-10-15T17:05:00+00:00"}]}), encoding="utf-8")
        erg = nachtragen(pfad=p, ig=iglog, threads=thlog)
        ok("nachtrag nimmt nur veroeffentlichte posts", erg["neu"] == 2)
        ok("ein post ohne postzeit wird gemeldet, nicht geraten",
           erg["ohne_zeit"] == ["instagram 992"])
        ok("nachtrag setzt den look aus der form",
           letzte("instagram", 1, p)[0]["look"] == "tagesgrafik-form02")
        ok("postzeit wird nach berlin gerechnet",
           letzte("instagram", 1, p)[0]["zeit_berlin"].startswith("2026-10-15T09:30:20+02:00"))
        ok("threads-zeile kommt mit", letzte("threads", 1, p)[0]["post_id"] == "7001")
        zwei = nachtragen(pfad=p, ig=iglog, threads=thlog)
        ok("der nachtrag ist wiederholbar", zwei["neu"] == 0 and zwei["schon"] == 2)

    cap = Path(tmp2 := tempfile.mkdtemp(), "cap.json")
    cap.write_text(json.dumps({"caption": "338 PH today\n\nmore text #kaspa #kas #crypto"}),
                   encoding="utf-8")
    hook, tags = aus_caption(cap)
    ok("hook aus der caption-datei", hook == "338 PH today")
    ok("hashtags aus der caption-datei", tags == 3)
    txt = Path(tmp2, "cap.txt")
    txt.write_text("first line here\n#one #two", encoding="utf-8")
    ok("auch eine reine textdatei geht", aus_caption(txt) == ("first line here", 2))
    ok("adresse mit raute ist kein hashtag", hashtags_zaehlen("see kaspapulse.com/#subscribe") == 0)
    ok("ein wort mit raute mitten drin ist kein hashtag", hashtags_zaehlen("a&#x27;b") == 0)
    ok("sommerzeit im oktober ist noch +2",
       berlin_offset(dt.datetime(2026, 10, 15, 7, 0, tzinfo=dt.timezone.utc)) == 2)
    ok("winterzeit im november ist +1",
       berlin_offset(dt.datetime(2026, 11, 15, 7, 0, tzinfo=dt.timezone.utc)) == 1)

    print("%d pruefungen, alle gruen" % n[0])


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="manifest der veroeffentlichten posts")
    ap.add_argument("--eintragen", action="store_true")
    ap.add_argument("--lesen", action="store_true")
    ap.add_argument("--nachtragen", action="store_true",
                    help="posts aus instagram-log.json und threads-post-log.json nachtragen")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--kanal", choices=KANAELE)
    ap.add_argument("--post-id")
    ap.add_argument("--format", dest="format_", choices=FORMATE)
    ap.add_argument("--look", default="")
    ap.add_argument("--variante", choices=VARIANTEN, default="-")
    ap.add_argument("--hook", default="")
    ap.add_argument("--hashtags", type=int)
    ap.add_argument("--laenge-s", type=float)
    ap.add_argument("--quelle", choices=QUELLEN, default="auto")
    ap.add_argument("--permalink", default="")
    ap.add_argument("--zeit-berlin", default="")
    ap.add_argument("--caption-datei")
    ap.add_argument("--letzte", type=int, default=0)
    ap.add_argument("--datei")
    a = ap.parse_args(argv)
    try:
        if a.selbsttest:
            selbsttest()
        elif a.eintragen:
            if not (a.kanal and a.post_id and a.format_):
                raise Fehler("--kanal, --post-id und --format sind pflicht")
            hook, tags = a.hook, a.hashtags
            if a.caption_datei:
                hook_c, tags_c = aus_caption(a.caption_datei)
                hook = hook or hook_c
                tags = tags_c if tags is None else tags
            if tags is None:
                raise Fehler("--hashtags oder --caption-datei")
            eintragen(kanal=a.kanal, post_id=a.post_id, format_=a.format_,
                      look=a.look, hook=hook, hashtags=tags, quelle=a.quelle,
                      variante=a.variante, laenge_s=a.laenge_s,
                      permalink=a.permalink, zeit_berlin=a.zeit_berlin,
                      pfad=a.datei)
        elif a.nachtragen:
            nachtragen(pfad=a.datei)
        elif a.lesen:
            zeilen, kaputt = lesen(a.datei)
            if a.kanal:
                zeilen = [z for z in zeilen if z.get("kanal") == a.kanal]
            if a.letzte:
                zeilen = zeilen[-a.letzte:]
            for z in zeilen:
                ausgabe(json.dumps(z, ensure_ascii=False, sort_keys=True))
            ausgabe("%d zeilen%s" % (len(zeilen), ", %d kaputt" % kaputt if kaputt else ""))
        else:
            ap.print_help()
    except Fehler as exc:
        ausgabe("ABBRUCH %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
