#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""uhrwerk_proben.py - zwei Fragen an die APIs, bevor wir darauf bauen.

1. WAS LIEFERT X FUER UNSERE EIGENEN POSTS
X kennt drei Gruppen von Zahlen je Post:
    public_metrics        likes, replies, reposts, quotes, bookmarks,
                          impression_count - mit jedem Zugang
    non_public_metrics    impression_count, user_profile_clicks,
                          url_link_clicks - nur eigene Posts, nur die
                          letzten 30 Tage, und nur ab einer Zugangsstufe
    organic_metrics       dasselbe plus likes und reposts, gleiche Grenzen
Welche davon unser Zugang wirklich hergibt, sagt kein Handbuch verlaesslich,
sondern nur ein Aufruf. Die Probe fragt alle drei einzeln ab und schreibt
auf, was ankommt und was mit welcher Begruendung abgelehnt wird. Liefert der
Zugang nur public_metrics, kommt der Rest aus dem CSV-Export der X-Analyse
(scripts/x_analytics_csv.py), den Ben montags hochlaedt.

2. KENNT GRAPH TRIAL REELS
Ein Trial Reel geht nur an Menschen, die uns nicht folgen - fuer einen
Variantentest das saubere Besteck, weil die eigene Gefolgschaft das Ergebnis
nicht verwischt. Beim Veroeffentlichen waere das ein Feld am Container.
Die Probe liest nur: gibt es das Feld an unseren eigenen Medien, und nimmt
Graph es an einem Container an. Es wird nie etwas veroeffentlicht. Ein
Container entsteht nur mit --container und verfaellt von allein.

ACHTUNG BEIM LESEN DES ERGEBNISSES
Graph ignoriert unbekannte Felder beim Anlegen oft still. "Container
angelegt" ist deshalb kein Beweis. Beweis ist, dass is_trial beim Lesen
zurueckkommt - genau das steht in der Ausgabe getrennt.

Tokens kommen nur aus der Umgebung und stehen in keiner Ausgabe.

    python3 scripts/uhrwerk_proben.py --x-metriken
    python3 scripts/uhrwerk_proben.py --ig-trial-reels
    python3 scripts/uhrwerk_proben.py --ig-trial-reels --container --video-url https://...
    python3 scripts/uhrwerk_proben.py --selbsttest
"""
import argparse
import json
import sys
import urllib.parse
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

from insights_sammler import (GRAPH, X_API, X_GRUPPEN, Sammelfehler, ausgabe,  # noqa: E402
                              hole, ig_konto, umgebung)

ZUGANG = {403: "zugangsstufe reicht nicht", 400: "anfrage abgelehnt",
          401: "token nicht gueltig", 429: "zu viele anfragen"}


# ---------------------------------------------------------------- x

def x_letzte_posts(anzahl=5, ruf=None):
    import x_post
    c = _creds()
    d = (ruf or (lambda w, q: x_post.call("GET", X_API + w, c, query=q)))(
        "/2/users/me", {"user.fields": "id,username,public_metrics"})
    uid = (d.get("data") or {}).get("id")
    if not uid:
        raise Sammelfehler("keine eigene user-id in der antwort")
    t = (ruf or (lambda w, q: x_post.call("GET", X_API + w, c, query=q)))(
        "/2/users/%s/tweets" % uid, {"max_results": max(5, anzahl), "tweet.fields": "created_at"})
    return d.get("data", {}), (t.get("data") or [])[:anzahl]


def _creds():
    return {"key": umgebung("X_API_KEY"), "secret": umgebung("X_API_SECRET"),
            "token": umgebung("X_ACCESS_TOKEN"), "token_secret": umgebung("X_ACCESS_SECRET")}


def x_probe(ruf=None):
    """Fragt je Gruppe einzeln und meldet, was ankommt. Gefragt wird am
    jeuengsten eigenen Post, weil non_public nur 30 Tage zurueckreicht."""
    import x_post
    c = _creds()
    rufe = ruf or (lambda w, q: x_post.call("GET", X_API + w, c, query=q))
    konto, posts = x_letzte_posts(3, rufe)
    erg = {"konto": {k: v for k, v in konto.items() if k != "id"},
           "posts_gefunden": len(posts), "gruppen": {}}
    if not posts:
        erg["hinweis"] = ("keine eigenen posts gelesen - ohne einen post in den "
                          "letzten 30 tagen sagt die probe nichts ueber non_public")
        return erg
    pid = posts[0]["id"]
    erg["geprueft_an"] = pid
    for gruppe in X_GRUPPEN:
        try:
            d = rufe("/2/tweets/%s" % pid, {"tweet.fields": gruppe})
            m = (d.get("data") or {}).get(gruppe)
            erg["gruppen"][gruppe] = {"da": bool(m), "felder": sorted(m or {}) or None,
                                      "werte": m if m else None}
        except (RuntimeError, Sammelfehler) as exc:
            text = str(exc)
            code = next((k for k in ZUGANG if " %d " % k in text or "HTTP %d" % k in text), 0)
            erg["gruppen"][gruppe] = {"da": False, "grund": text[:200],
                                      "lesart": ZUGANG.get(code, "unklar")}
    liefert = [g for g, v in erg["gruppen"].items() if v.get("da")]
    erg["ergebnis"] = ("x liefert: %s" % ", ".join(liefert)) if liefert else "x liefert keine gruppe"
    erg["csv_noetig"] = not any(g in liefert for g in ("non_public_metrics", "organic_metrics"))
    return erg


# ---------------------------------------------------------------- trial reels

def ig_trial_probe(video_url="", cover_url="", container=False, hole_fn=hole):
    """Erst lesen, dann - nur auf Wunsch - einen Container anlegen. Ein
    Container wird nie veroeffentlicht."""
    uid, kopf = ig_konto(hole_fn)
    erg = {"feld_an_medien": None, "container": None}
    try:
        d = hole_fn("%s/%s/media?fields=id,media_product_type,is_trial&limit=5"
                    % (GRAPH, uid), kopf)
        erg["feld_an_medien"] = {"da": True,
                                 "medien": [{k: v for k, v in m.items() if k != "id"}
                                            for m in d.get("data", [])]}
    except Sammelfehler as exc:
        text = str(exc)
        erg["feld_an_medien"] = {"da": False, "grund": text[:240],
                                 "lesart": ("das feld kennt diese api-version nicht"
                                            if "nonexisting field" in text or "is_trial" in text
                                            else "anderer fehler, nicht die antwort auf die frage")}
    if container:
        if not video_url:
            raise Sammelfehler("--container braucht --video-url")
        felder = {"media_type": "REELS", "video_url": video_url, "is_trial": "true",
                  "caption": "uhrwerk probe, wird nicht veroeffentlicht"}
        if cover_url:
            felder["cover_url"] = cover_url
        try:
            c = hole_fn("%s/%s/media" % (GRAPH, uid),
                        dict(kopf, **{"Content-Type": "application/x-www-form-urlencoded"}),
                        urllib.parse.urlencode(felder).encode(), "POST")
            cid = str(c.get("id", ""))
            erg["container"] = {"angelegt": bool(cid), "id": cid}
            # Der Beweis: kommt is_trial beim Lesen zurueck?
            try:
                z = hole_fn("%s/%s?fields=status_code,is_trial" % (GRAPH, cid), kopf)
                erg["container"]["gelesen"] = z
                erg["container"]["beweis"] = "is_trial" in z
            except Sammelfehler as exc:
                erg["container"]["gelesen"] = {"fehler": str(exc)[:240]}
                erg["container"]["beweis"] = False
        except Sammelfehler as exc:
            erg["container"] = {"angelegt": False, "grund": str(exc)[:240]}
    erg["ergebnis"] = _trial_urteil(erg)
    return erg


def _trial_urteil(erg):
    an_medien = (erg.get("feld_an_medien") or {}).get("da")
    con = erg.get("container") or {}
    if con.get("beweis"):
        return "trial reels gehen: graph gibt is_trial am container zurueck"
    if an_medien:
        return ("das feld is_trial gibt es an unseren medien. ob das anlegen es "
                "annimmt, zeigt erst ein lauf mit --container")
    if con.get("angelegt") and not con.get("beweis"):
        return ("container angelegt, aber is_trial kommt nicht zurueck - das ist "
                "kein beweis, graph verschluckt unbekannte felder still")
    return "kein hinweis auf trial reels in dieser api-version"


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import os
    n = [0]

    def ok(was, bedingung):
        n[0] += 1
        print("%s %s" % ("ok  " if bedingung else "FEHL", was))
        if not bedingung:
            raise SystemExit(1)

    for name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        os.environ[name] = "x" * 20
    try:
        def ruf_voll(weg, q):
            if weg == "/2/users/me":
                return {"data": {"id": "99", "username": "gokugalax",
                                 "public_metrics": {"followers_count": 812}}}
            if weg.endswith("/tweets"):
                return {"data": [{"id": "1800", "created_at": "2026-10-14T19:05:00Z"}]}
            g = q["tweet.fields"]
            return {"data": {g: {"impression_count": 5000}}}
        e = x_probe(ruf_voll)
        ok("alle drei gruppen als geliefert erkannt", len(e["gruppen"]) == 3
           and all(v["da"] for v in e["gruppen"].values()))
        ok("csv ist dann nicht noetig", e["csv_noetig"] is False)
        ok("die eigene user-id steht nicht im ergebnis", "id" not in e["konto"])

        def ruf_knapp(weg, q):
            if weg == "/2/users/me":
                return {"data": {"id": "99", "username": "gokugalax"}}
            if weg.endswith("/tweets"):
                return {"data": [{"id": "1800"}]}
            g = q["tweet.fields"]
            if g == "public_metrics":
                return {"data": {g: {"impression_count": 5000, "like_count": 9}}}
            raise RuntimeError("X antwortet HTTP 403 auf GET /2/tweets/1800: "
                               "Your current access level does not include %s" % g)
        e = x_probe(ruf_knapp)
        ok("nur public_metrics erkannt", e["ergebnis"] == "x liefert: public_metrics")
        ok("die abgelehnten gruppen tragen die lesart",
           e["gruppen"]["non_public_metrics"]["lesart"] == "zugangsstufe reicht nicht")
        ok("dann braucht es den csv-export", e["csv_noetig"] is True)

        def ruf_leer(weg, q):
            if weg == "/2/users/me":
                return {"data": {"id": "99"}}
            return {"data": []}
        e = x_probe(ruf_leer)
        ok("ohne eigene posts sagt die probe das offen", "hinweis" in e)
    finally:
        for name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
            del os.environ[name]

    os.environ["INSTAGRAM_PAGE_TOKEN"] = "EA" + "b" * 30
    os.environ["IG_USER_ID"] = "17841400000000000"
    try:
        def kennt_feld(url, kopf=None, daten=None, methode="GET"):
            return {"data": [{"id": "1", "media_product_type": "REELS", "is_trial": False}]}
        e = ig_trial_probe(hole_fn=kennt_feld)
        ok("feld an den medien gefunden", e["feld_an_medien"]["da"] is True)
        ok("urteil verlangt trotzdem den container-lauf", "--container" in e["ergebnis"])

        def kennt_feld_nicht(url, kopf=None, daten=None, methode="GET"):
            raise Sammelfehler('http 400 auf graph.facebook.com/media, '
                               '(#100) Tried accessing nonexisting field (is_trial)')
        e = ig_trial_probe(hole_fn=kennt_feld_nicht)
        ok("unbekanntes feld wird als solches gelesen",
           e["feld_an_medien"]["lesart"].startswith("das feld kennt diese api-version nicht"))
        ok("urteil ohne hinweis ist ein klares nein",
           e["ergebnis"] == "kein hinweis auf trial reels in dieser api-version")

        rufe = []

        def mit_container(url, kopf=None, daten=None, methode="GET"):
            rufe.append((methode, url.split("?")[0]))
            if methode == "POST":
                ok_feld = b"is_trial=true" in (daten or b"")
                return {"id": "77"} if ok_feld else {}
            if "/media?" in url:
                return {"data": []}
            return {"status_code": "IN_PROGRESS", "is_trial": True}
        e = ig_trial_probe(video_url="https://example.invalid/a.mp4", container=True,
                           hole_fn=mit_container)
        ok("container angelegt und is_trial zurueckgelesen", e["container"]["beweis"] is True)
        ok("das urteil ist dann ein ja", e["ergebnis"].startswith("trial reels gehen"))
        ok("es wurde nie veroeffentlicht",
           not any("media_publish" in u for _, u in rufe))

        def container_ohne_beweis(url, kopf=None, daten=None, methode="GET"):
            if methode == "POST":
                return {"id": "78"}
            if "/media?" in url:
                raise Sammelfehler("(#100) nonexisting field (is_trial)")
            return {"status_code": "IN_PROGRESS"}
        e = ig_trial_probe(video_url="https://example.invalid/a.mp4", container=True,
                           hole_fn=container_ohne_beweis)
        ok("ein container ohne rueckgelesenes feld ist kein beweis",
           e["container"]["beweis"] is False and "kein beweis" in e["ergebnis"])
        try:
            ig_trial_probe(container=True, hole_fn=kennt_feld)
            ok("container ohne video bricht ab", False)
        except Sammelfehler as exc:
            ok("container ohne video bricht ab", "video-url" in str(exc))
        ok("das token steht in keiner ausgabe",
           os.environ["INSTAGRAM_PAGE_TOKEN"] not in json.dumps(e))
    finally:
        del os.environ["INSTAGRAM_PAGE_TOKEN"], os.environ["IG_USER_ID"]
    print("%d pruefungen, alle gruen" % n[0])


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="proben fuer x-metriken und trial reels")
    ap.add_argument("--x-metriken", action="store_true")
    ap.add_argument("--ig-trial-reels", action="store_true")
    ap.add_argument("--container", action="store_true",
                    help="legt einen reel-container an, veroeffentlicht nichts")
    ap.add_argument("--video-url", default="")
    ap.add_argument("--cover-url", default="")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.selbsttest:
            selbsttest()
        elif a.x_metriken:
            ausgabe(json.dumps(x_probe(), ensure_ascii=False, indent=1, sort_keys=True))
        elif a.ig_trial_reels:
            ausgabe(json.dumps(ig_trial_probe(a.video_url, a.cover_url, a.container),
                               ensure_ascii=False, indent=1, sort_keys=True))
        else:
            ap.print_help()
    except Sammelfehler as exc:
        ausgabe("ABBRUCH %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
