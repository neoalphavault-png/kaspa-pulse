#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""x_analytics_csv.py - die Wochenzahlen von X aus dem CSV-Export lesen.

WARUM
Die X-API gibt impression_count und die Klicks nur ab einer Zugangsstufe
her (scripts/uhrwerk_proben.py --x-metriken sagt, welche wir haben). Was
sie nicht hergibt, steht im CSV-Export der X-Analyse. Ben laedt die Datei
montags hoch, dieses Skript liest sie ein, und danach stehen die Zahlen in
derselben Datei wie alles andere: data/insights/x.jsonl.

DIE SPALTEN AENDERN SICH
X hat die Kopfzeile seit 2023 mehrfach umbenannt ("Tweet id" wurde "Post
id", "Retweets" wurden "Reposts"). Darum wird nicht auf eine feste
Kopfzeile gebaut: jede Spalte wird klein geschrieben, von Zeichen befreit
und gegen eine Liste von Schreibweisen gelegt. Eine Spalte, die niemand
kennt, kommt unter "weitere" mit, statt still zu verschwinden.

Eine Zeile je Post und Export. Der Stand (das Datum des Exports) gehoert
zum Schluessel: ein neuer Export am naechsten Montag schreibt neue Zeilen,
derselbe Export zweimal eingelesen schreibt keine.

    python3 scripts/x_analytics_csv.py --datei ~/Downloads/account_overview.csv
    python3 scripts/x_analytics_csv.py --datei ... --stand 2026-10-19
    python3 scripts/x_analytics_csv.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

from insights_sammler import INSIGHTS, Sammelfehler, ausgabe, jsonl_lesen, jsonl_schreiben, pfad  # noqa: E402
from post_manifest import MANIFEST, lesen  # noqa: E402

# Links der Name, den wir benutzen (wie in der API), rechts die Schreibweisen,
# die X in seinen Exporten hatte.
SPALTEN = {
    "impression_count": ("impressions", "impression", "views", "viewcount"),
    "like_count": ("likes", "like"),
    "reply_count": ("replies", "reply"),
    "retweet_count": ("reposts", "retweets", "repost", "retweet"),
    "quote_count": ("quotetweets", "quotes", "quoteposts"),
    "bookmark_count": ("bookmarks", "bookmark"),
    "url_link_clicks": ("urlclicks", "linkclicks", "permalinkclicks"),
    "user_profile_clicks": ("profilevisits", "userprofileclicks", "profileclicks"),
    "engagements": ("engagements", "engagement"),
    "follows": ("newfollows", "follows", "newfollowers"),
    "unfollows": ("unfollows",),
    "shares": ("share", "shares"),
    "detail_expands": ("detailexpands",),
    "media_views": ("mediaviews",),
}
ID_SPALTEN = ("postid", "tweetid", "id")
TEXT_SPALTEN = ("posttext", "tweettext", "text")
ZEIT_SPALTEN = ("date", "time", "createdat", "posttime")
FENSTER = "csv"


def schluessel(name):
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def zahl(wert):
    """X schreibt Zahlen je nach Ausgabesprache mit Punkt, Komma oder
    Leerzeichen. Eine Zahl, die sich nicht lesen laesst, wird nichts -
    geraten wird nie."""
    t = str(wert or "").strip().replace(" ", "").replace(" ", "")
    if not t or t in ("-", "–"):
        return None
    t = t.replace("%", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+", t):
        t = t.replace(",", "")
    t = t.replace(",", ".")
    try:
        f = float(t)
    except ValueError:
        return None
    return int(f) if f == int(f) else f


def kopf_lesen(kopf):
    """Gibt zurueck: Position der id-Spalte, {position: name} fuer die
    bekannten Zahlen, und die unbekannten Spalten."""
    id_pos, werte, weitere, zeit_pos, text_pos = None, {}, {}, None, None
    rueck = {s: name for name, schreibweisen in SPALTEN.items() for s in schreibweisen}
    for i, roh in enumerate(kopf):
        s = schluessel(roh)
        if id_pos is None and s in ID_SPALTEN:
            id_pos = i
        elif zeit_pos is None and s in ZEIT_SPALTEN:
            zeit_pos = i
        elif text_pos is None and s in TEXT_SPALTEN:
            text_pos = i
        elif s in rueck:
            werte[i] = rueck[s]
        elif s:
            weitere[i] = s
    if id_pos is None:
        raise Sammelfehler("keine spalte mit der post-id gefunden, kopfzeile: %s"
                           % ", ".join(str(k) for k in kopf[:12]))
    return id_pos, werte, weitere, zeit_pos, text_pos


def zeilen_aus_csv(text):
    try:
        trenner = csv.Sniffer().sniff(text[:4000], delimiters=",;\t").delimiter
    except csv.Error:
        trenner = ","
    roh = list(csv.reader(io.StringIO(text), delimiter=trenner))
    roh = [z for z in roh if any(str(f).strip() for f in z)]
    if not roh:
        raise Sammelfehler("die datei ist leer")
    id_pos, werte, weitere, zeit_pos, text_pos = kopf_lesen(roh[0])
    aus = []
    for z in roh[1:]:
        if len(z) <= id_pos:
            continue
        pid = str(z[id_pos]).strip().strip('"')
        if not re.fullmatch(r"\d{5,25}", pid):
            continue
        e = {"post_id": pid,
             "werte": {n: zahl(z[i]) for i, n in werte.items()
                       if i < len(z) and zahl(z[i]) is not None}}
        rest = {n: zahl(z[i]) for i, n in weitere.items()
                if i < len(z) and zahl(z[i]) is not None}
        if rest:
            e["weitere"] = rest
        if zeit_pos is not None and zeit_pos < len(z):
            e["zeit_csv"] = str(z[zeit_pos]).strip()
        aus.append(e)
    if not aus:
        raise Sammelfehler("keine zeile mit einer post-id gefunden")
    return aus, sorted(set(weitere.values()))


def einlesen(datei, stand="", schreiben=True, ziel=None, manifest=None):
    text = Path(datei).read_text(encoding="utf-8-sig", errors="replace")
    zeilen, unbekannt = zeilen_aus_csv(text)
    stand = stand or dt.date.today().isoformat()
    ziel = Path(ziel) if ziel else pfad("x")
    da = {(str(s.get("post_id")), s.get("stand")) for s in jsonl_lesen(ziel)
          if s.get("fenster") == FENSTER}
    bekannt = {str(e.get("post_id")) for e in lesen(manifest or MANIFEST)[0]
               if e.get("kanal") == "x"}
    neu, schon, fremd = 0, 0, []
    for e in zeilen:
        if (e["post_id"], stand) in da:
            schon += 1
            continue
        s = dict(e, kanal="x", fenster=FENSTER, stand=stand, quelle="csv",
                 im_manifest=e["post_id"] in bekannt)
        if not s["im_manifest"]:
            fremd.append(e["post_id"])
        if schreiben:
            jsonl_schreiben(ziel, s)
        neu += 1
    bericht = ["x-csv %s: %d neu, %d standen schon drin" % (stand, neu, schon)]
    if fremd:
        bericht.append("  %d post(s) nicht im manifest: %s%s" % (
            len(fremd), ", ".join(fremd[:5]), " ..." if len(fremd) > 5 else ""))
    if unbekannt:
        bericht.append("  unbekannte spalten mitgenommen: %s" % ", ".join(unbekannt))
    return {"neu": neu, "schon": schon, "fremd": fremd, "unbekannt": unbekannt,
            "bericht": bericht}


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import tempfile
    n = [0]

    def ok(was, bedingung):
        n[0] += 1
        print("%s %s" % ("ok  " if bedingung else "FEHL", was))
        if not bedingung:
            raise SystemExit(1)

    alt = ('"Tweet id","Tweet permalink","Tweet text","time","impressions",'
           '"engagements","retweets","replies","likes","user profile clicks","url clicks"\n'
           '"1800000000000000001","https://x.com/a/1","hello","2026-10-14 19:05",'
           '"5.000","120","4","3","61","12","9"\n'
           '"nicht-die-ueberschrift","","","","","","","","","",""\n')
    neu_kopf = ("Date,Post id,Post text,Impressions,Likes,Reposts,Replies,Bookmarks,"
                "Profile visits,New follows,Unbekanntes Feld\n"
                "2026-10-15,1800000000000000002,hi,12 345,80,5,2,7,33,4,99\n")
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp, "x.jsonl")
        mani = Path(tmp, "manifest.jsonl")
        mani.write_text(json.dumps({"post_id": "1800000000000000001", "kanal": "x",
                                    "zeit_berlin": "2026-10-14T19:05:00+02:00",
                                    "format": "text", "look": "-", "variante": "-",
                                    "hook": "hello", "hashtags": 0, "laenge_s": None,
                                    "quelle": "auto"}) + "\n", encoding="utf-8")
        a = Path(tmp, "alt.csv")
        a.write_text(alt, encoding="utf-8")
        e = einlesen(a, stand="2026-10-19", ziel=ziel, manifest=mani)
        ok("eine zeile aus dem alten export", e["neu"] == 1)
        ok("eine zeile ohne post-id wird uebersprungen", e["fremd"] == [])
        gelesen = jsonl_lesen(ziel)[0]
        ok("punkt als tausendertrennung gelesen",
           gelesen["werte"]["impression_count"] == 5000)
        ok("retweets landen unter retweet_count", gelesen["werte"]["retweet_count"] == 4)
        ok("url clicks landen unter url_link_clicks", gelesen["werte"]["url_link_clicks"] == 9)
        ok("profile clicks landen unter user_profile_clicks",
           gelesen["werte"]["user_profile_clicks"] == 12)
        ok("der post steht im manifest", gelesen["im_manifest"] is True)
        ok("der stand gehoert zur zeile", gelesen["stand"] == "2026-10-19")
        zwei = einlesen(a, stand="2026-10-19", ziel=ziel, manifest=mani)
        ok("derselbe export zweimal schreibt nichts", zwei["neu"] == 0 and zwei["schon"] == 1)
        drei = einlesen(a, stand="2026-10-26", ziel=ziel, manifest=mani)
        ok("ein neuer stand schreibt eine neue zeile", drei["neu"] == 1)

        b = Path(tmp, "neu.csv")
        b.write_text(neu_kopf, encoding="utf-8")
        e = einlesen(b, stand="2026-10-19", ziel=ziel, manifest=mani)
        z = [x for x in jsonl_lesen(ziel) if x["post_id"].endswith("2")][0]
        ok("die neue kopfzeile wird genauso gelesen", z["werte"]["impression_count"] == 12345)
        ok("reposts landen unter retweet_count", z["werte"]["retweet_count"] == 5)
        ok("bookmarks kommen mit", z["werte"]["bookmark_count"] == 7)
        ok("ein post ohne manifest-zeile wird gemeldet", e["fremd"] == [z["post_id"]])
        ok("eine unbekannte spalte verschwindet nicht",
           z.get("weitere", {}).get("unbekanntesfeld") == 99)
        ok("die unbekannte spalte steht im bericht", e["unbekannt"] == ["unbekanntesfeld"])

        c = Path(tmp, "ohne.csv")
        c.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        try:
            einlesen(c, ziel=ziel, manifest=mani)
            ok("eine datei ohne id-spalte bricht ab", False)
        except Sammelfehler as exc:
            ok("eine datei ohne id-spalte bricht ab", "post-id" in str(exc))

        d = Path(tmp, "semikolon.csv")
        d.write_text("Post id;Impressions;Likes\n1800000000000000003;1.000;5\n", encoding="utf-8")
        e = einlesen(d, stand="2026-10-19", ziel=ziel, manifest=mani)
        ok("auch semikolon als trenner", e["neu"] == 1)

    ok("komma als tausendertrennung", zahl("12,345") == 12345)
    ok("komma als dezimaltrennung", zahl("3,5") == 3.5)
    ok("ein strich ist keine zahl", zahl("-") is None)
    ok("leer ist keine zahl", zahl("") is None)
    ok("prozent wird gelesen", zahl("4,2%") == 4.2)
    ok("text ist keine zahl", zahl("keine") is None)
    print("%d pruefungen, alle gruen" % n[0])


def main(argv=None):
    ap = argparse.ArgumentParser(description="x-analyse aus dem csv-export")
    ap.add_argument("--datei")
    ap.add_argument("--stand", default="", help="datum des exports, standard heute")
    ap.add_argument("--probe", action="store_true", help="nur lesen, nichts schreiben")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.selbsttest:
            selbsttest()
        elif a.datei:
            e = einlesen(a.datei, a.stand, schreiben=not a.probe)
            for z in e["bericht"]:
                ausgabe(z)
        else:
            ap.print_help()
    except (Sammelfehler, OSError) as exc:
        ausgabe("ABBRUCH %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
