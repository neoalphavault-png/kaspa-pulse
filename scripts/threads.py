#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threads.py, Kaspa Pulse auf Threads (Ben, 14.10.2026).

DIESER STAND KANN NOCH NICHT VEROEFFENTLICHEN. Er liest /me und legt einen
Container an, und dort hoert er auf. Der zweite Schritt (threads_publish)
kommt erst, wenn die Probe bestaetigt hat, dass Konto, Rechte und
topic_tag stimmen - vorher waere jede Zeile davon geraten.

DAS TOKEN KOMMT AUS DER UMGEBUNG UND WIRD NIE GEDRUCKT. THREADS_TOKEN
steht als Secret in kaspa-pulse, nie in einer Datei, nie in einer Ausgabe.
urllib nennt die URL im Text einer HTTPError, und die Graph-API nimmt das
Token als Parameter - deshalb geht jede Ausgabe durch blind(), und das
Token steht in keiner URL, sondern im Authorization-Header.

    python3 scripts/threads.py me
    python3 scripts/threads.py container --text "..." [--bild URL] [--thema Crypto]
    python3 scripts/threads.py wache --text "..."
    python3 scripts/threads.py --selbsttest

Was dieses Skript NICHT tut: es postet nicht, es loescht nicht, es
antwortet nicht. Und es erfindet keinen Text: der Text kommt aus der
Warteschlange oder aus der Tagesgrafik, nie aus dem Skript.
"""
import argparse
import json
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


def container(text, bild="", thema=THEMA, tok=None, oeffner=None):
    """Container anlegen und DORT AUFHOEREN. Kein threads_publish."""
    befunde = wache(text)
    if befunde:
        for b in befunde:
            print("WACHE: %s" % b, file=sys.stderr)
        sys.exit("der text haelt die wachen nicht ein, kein container")
    nutzer = os.environ.get(ENV_USER, "").strip()
    if not nutzer:
        sys.exit("FEHLT: %s steht nicht in der Umgebung (erst 'me' laufen lassen)" % ENV_USER)
    felder = {"media_type": "IMAGE" if bild else "TEXT", "text": text}
    if bild:
        felder["image_url"] = bild
    if thema:
        felder["topic_tag"] = thema
    d = graph("%s/threads" % nutzer, felder, post=True, tok=tok, oeffner=oeffner)
    print("container = %s" % d.get("id", "?"))
    print("NICHT veroeffentlicht. threads_publish laeuft in diesem stand nicht.")
    return d


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

    print("\n%d faelle, %d falsch" % (len(gezaehlt), len(fehler)))
    for f in fehler:
        print("  " + f)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", nargs="?", choices=["me", "container", "wache"])
    ap.add_argument("--text", default="")
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
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
