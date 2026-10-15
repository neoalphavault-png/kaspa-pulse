#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""insights_sammler.py - Zahlen zu den Posts, zweimal je Post.

WARUM ZWEI SCHNAPPSCHUESSE
Eine Reichweite ist kein Zustand, sie ist eine Kurve. Wer heute 4.100 liest
und naechste Woche 6.800, hat zwei Zahlen und keinen Vergleich. Deshalb
immer dieselben zwei Zeitpunkte: 24 Stunden und 7 Tage nach dem Post. Nur
so sind zwei Posts voneinander vergleichbar, und nur so ist ein Ausreisser
ein Ausreisser und nicht ein spaeter gelesener Post.

Der Timer laeuft alle 6 Stunden. Ein Fenster wird beim ersten Lauf genommen,
bei dem der Post alt genug ist, und danach nie wieder. Wer schon im Manifest
stand, bevor es den Sammler gab, bekommt beide Fenster in einem Lauf, mit
nachtrag true daneben - eine spaet gemessene 24-Stunden-Zahl ist keine
24-Stunden-Zahl, und das soll man in den Daten sehen.

    data/insights/instagram.jsonl    ein Schnappschuss je Zeile
    data/insights/threads.jsonl
    data/insights/x.jsonl
    data/insights/follower.jsonl     Followerzahl je Kanal, bei jedem Lauf
    data/insights/trichter.jsonl     Anmeldungen je Kanal, woechentlich

GEHEIMNISSE
Tokens kommen nur aus der Umgebung. Sie stehen in keiner Datei, in keiner
Ausgabe und in keiner Discord-Nachricht: jede Zeile laeuft durch sauber().
Ein fehlendes Token ist kein Abbruch des ganzen Laufs, sondern eine Zeile
im Bericht - die anderen Kanaele werden trotzdem gemessen.

STORIES
Eine Story ist nach 24 Stunden weg, mitsamt ihren Zahlen. Bei einem Takt
von 6 Stunden kann das knapp werden. Darum hat eine Story nur das Fenster
24h, und was dann nicht mehr da ist, steht als fehlend in der Zeile.

    python3 scripts/insights_sammler.py --sammeln                 # trocken
    python3 scripts/insights_sammler.py --sammeln --modus scharf  # mit meldung
    python3 scripts/insights_sammler.py --trichter --modus scharf  # montags
    python3 scripts/insights_sammler.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

from post_manifest import MANIFEST, MANIFESTE, alle, lesen, sauber, berlin_offset   # noqa: E402

REPO = HIER.parent
INSIGHTS = Path(os.environ.get("UHRWERK_INSIGHTS") or REPO / "data" / "insights")
FOLLOWER = "follower.jsonl"
TRICHTER = "trichter.jsonl"

FENSTER = (("24h", 24), ("7d", 168))
# Dieselbe Version wie in instagram.py, aus derselben Variable.
GRAPH = "https://graph.facebook.com/%s" % os.environ.get("IG_GRAPH_VERSION", "v24.0")
THREADS = "https://graph.threads.net/v1.0"
X_API = "https://api.x.com"
UA = "kaspa-pulse-uhrwerk/1.0"
FRIST = 45

# Instagram, Stand 10/2026: views hat impressions und plays ersetzt. Welche
# Metrik ein Medium kennt, haengt am Format - darum je Format eine Liste und
# darunter der Rueckfall einzeln, damit eine unbekannte Metrik nicht die
# anderen mitnimmt.
IG_METRIKEN = {
    "bild": ("reach", "views", "likes", "comments", "shares", "saved",
             "total_interactions", "follows", "profile_visits"),
    "karussell": ("reach", "views", "likes", "comments", "shares", "saved",
                  "total_interactions", "follows", "profile_visits"),
    "reel": ("reach", "views", "likes", "comments", "shares", "saved",
             "total_interactions", "follows", "profile_visits"),
    "story": ("reach", "views", "replies", "navigation", "total_interactions"),
}
TH_METRIKEN = ("views", "likes", "replies", "reposts", "quotes", "shares")
# Reichweite je Kanal: der Name, auf den der Ausreisser-Alarm schaut.
REICHWEITE = {"instagram": "reach", "threads": "views", "x": "impression_count"}
ALARM_FAKTOR = 3.0
ALARM_MIN_POSTS = 7
MEDIAN_POSTS = 30


class Sammelfehler(Exception):
    """Ein Kanal ist nicht gelaufen. Der Lauf geht weiter."""


def ausgabe(*teile):
    print(sauber(" ".join(str(t) for t in teile)))


def jetzt():
    return dt.datetime.now(dt.timezone.utc)


# ---------------------------------------------------------------- http

def hole(url, kopf=None, daten=None, methode="GET"):
    req = urllib.request.Request(url, data=daten, method=methode)
    req.add_header("User-Agent", UA)
    for k, v in (kopf or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=FRIST) as r:
            roh = r.read().decode("utf-8", "replace")
            return json.loads(roh) if roh.strip() else {}
    except urllib.error.HTTPError as e:
        leib = ""
        try:
            leib = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        raise Sammelfehler("http %s auf %s, %s" % (e.code, _weg(url), leib))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Sammelfehler("nicht erreichbar, %s auf %s" % (e, _weg(url)))


def _weg(url):
    """Nur Wirt und Pfad in die Meldung, nie die Parameter - dort steht das Token."""
    t = urllib.parse.urlsplit(url)
    return t.netloc + t.path


def umgebung(name):
    wert = os.environ.get(name, "").strip()
    if not wert:
        raise Sammelfehler("%s steht nicht in der umgebung" % name)
    return wert


# ---------------------------------------------------------------- instagram

def ig_konto(hole_fn=hole):
    """Wie in instagram.py: die User-id kommt aus der Variablen, nicht aus
    einem Suchlauf, und das Token geht in den Kopf, nie in die Adresse -
    eine Adresse landet in Protokollen, ein Kopf nicht."""
    tok = umgebung("INSTAGRAM_PAGE_TOKEN")
    uid = os.environ.get("IG_USER_ID", "").strip()
    if not re.fullmatch(r"\d{5,30}", uid):
        raise Sammelfehler("IG_USER_ID fehlt oder ist keine zahl")
    return uid, {"Authorization": "Bearer " + tok}


def ig_messen(post_id, format_, hole_fn=hole):
    """Erst alle Metriken in einem Aufruf, dann die fehlenden einzeln. Eine
    Metrik, die ein Medium nicht kennt, laesst Graph den ganzen Aufruf
    scheitern - das ist der Grund fuer den zweiten Weg."""
    _, kopf = ig_konto(hole_fn)
    will = IG_METRIKEN.get(format_, IG_METRIKEN["bild"])
    werte, fehlt = {}, []

    def ziehen(namen):
        d = hole_fn("%s/%s/insights?metric=%s" % (GRAPH, post_id, ",".join(namen)), kopf)
        for e in d.get("data", []):
            werte[e.get("name")] = _ig_wert(e)

    try:
        ziehen(will)
    except Sammelfehler:
        for name in will:
            try:
                ziehen((name,))
            except Sammelfehler as exc:
                fehlt.append("%s (%s)" % (name, str(exc)[:60]))
    for name in will:
        if name not in werte and not any(f.startswith(name) for f in fehlt):
            fehlt.append(name)
    return werte, fehlt


def _ig_wert(eintrag):
    if "total_value" in eintrag:
        return (eintrag["total_value"] or {}).get("value")
    w = eintrag.get("values") or []
    return w[-1].get("value") if w else None


def ig_follower(hole_fn=hole):
    uid, kopf = ig_konto(hole_fn)
    d = hole_fn("%s/%s?fields=followers_count" % (GRAPH, uid), kopf)
    return d.get("followers_count")


# ---------------------------------------------------------------- threads

def th_kopf():
    return {"Authorization": "Bearer %s" % umgebung("THREADS_TOKEN")}


def th_messen(post_id, format_="text", hole_fn=hole):
    kopf = th_kopf()
    werte, fehlt = {}, []

    def ziehen(namen):
        d = hole_fn("%s/%s/insights?metric=%s" % (THREADS, post_id, ",".join(namen)), kopf)
        for e in d.get("data", []):
            werte[e.get("name")] = _ig_wert(e)

    try:
        ziehen(TH_METRIKEN)
    except Sammelfehler:
        for name in TH_METRIKEN:
            try:
                ziehen((name,))
            except Sammelfehler as exc:
                fehlt.append("%s (%s)" % (name, str(exc)[:60]))
    for name in TH_METRIKEN:
        if name not in werte and not any(f.startswith(name) for f in fehlt):
            fehlt.append(name)
    return werte, fehlt


def th_follower(hole_fn=hole):
    d = hole_fn("%s/me/threads_insights?metric=followers_count" % THREADS, th_kopf())
    for e in d.get("data", []):
        if e.get("name") == "followers_count":
            return _ig_wert(e)
    return None


# ---------------------------------------------------------------- x

X_GRUPPEN = ("public_metrics", "non_public_metrics", "organic_metrics")


def x_messen(post_id, format_="text", hole_fn=None):
    """X gibt public_metrics mit jedem Zugang her. non_public_metrics und
    organic_metrics haengen an der Zugangsstufe und am Alter des Posts
    (nur eigene Posts, nur die letzten 30 Tage). Welche Gruppe unser
    Zugang liefert, sagt scripts/x_metriken_probe.py - der Sammler fragt
    sie einzeln und schreibt auf, was abgelehnt wurde, statt am ersten
    Nein zu scheitern."""
    import x_post
    creds = {n: umgebung(n) for n in ("X_API_KEY", "X_API_SECRET",
                                      "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    c = {"key": creds["X_API_KEY"], "secret": creds["X_API_SECRET"],
         "token": creds["X_ACCESS_TOKEN"], "token_secret": creds["X_ACCESS_SECRET"]}
    ruf = hole_fn or (lambda q: x_post.call("GET", X_API + "/2/tweets/" + str(post_id), c, query=q))
    werte, fehlt = {}, []
    for gruppe in X_GRUPPEN:
        try:
            d = ruf({"tweet.fields": gruppe})
            m = (d.get("data") or {}).get(gruppe) or {}
            for k, v in m.items():
                werte.setdefault(k if gruppe == "public_metrics" else "%s_%s" % (gruppe[:3], k), v)
            if not m:
                fehlt.append("%s (leer)" % gruppe)
        except (Sammelfehler, RuntimeError) as exc:
            fehlt.append("%s (%s)" % (gruppe, str(exc)[:80]))
    return werte, fehlt


def x_follower(hole_fn=None):
    import x_post
    c = {"key": umgebung("X_API_KEY"), "secret": umgebung("X_API_SECRET"),
         "token": umgebung("X_ACCESS_TOKEN"), "token_secret": umgebung("X_ACCESS_SECRET")}
    ruf = hole_fn or (lambda q: x_post.call("GET", X_API + "/2/users/me", c, query=q))
    d = ruf({"user.fields": "public_metrics"})
    return ((d.get("data") or {}).get("public_metrics") or {}).get("followers_count")


MESSER = {"instagram": (ig_messen, ig_follower),
          "threads": (th_messen, th_follower),
          "x": (x_messen, x_follower)}


# ---------------------------------------------------------------- dateien

def pfad(kanal):
    return INSIGHTS / ("%s.jsonl" % kanal)


def jsonl_lesen(p):
    p = Path(p)
    if not p.exists():
        return []
    aus = []
    for roh in p.read_text(encoding="utf-8").splitlines():
        if not roh.strip():
            continue
        try:
            d = json.loads(roh)
        except ValueError:
            continue
        if isinstance(d, dict):
            aus.append(d)
    return aus


def jsonl_schreiben(p, eintrag):
    zeile = json.dumps(eintrag, ensure_ascii=False, sort_keys=True)
    if sauber(zeile) != zeile:
        raise Sammelfehler("in der zeile stand etwas, das wie ein token aussieht")
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(zeile + "\n")
    return eintrag


# ---------------------------------------------------------------- faellig

def alter_h(zeit_berlin, now):
    t = dt.datetime.fromisoformat(str(zeit_berlin))
    return (now - t).total_seconds() / 3600.0


def faellig(eintraege, vorhanden, now):
    """(eintrag, fenster, nachtrag) fuer alles, was alt genug ist und noch
    nicht gemessen wurde. Stories haben nur das Fenster 24h."""
    da = {(str(s.get("post_id")), s.get("fenster")) for s in vorhanden}
    aus = []
    for e in eintraege:
        if not e.get("zeit_berlin"):
            continue
        alt = alter_h(e["zeit_berlin"], now)
        for name, stunden in FENSTER:
            if e.get("format") == "story" and name != "24h":
                continue
            if alt < stunden or (str(e["post_id"]), name) in da:
                continue
            # mehr als ein halbes Fenster zu spaet: die zahl ist keine
            # 24-stunden-zahl mehr, das steht dann in der zeile.
            aus.append((e, name, alt > stunden * 1.5))
    return aus


# ---------------------------------------------------------------- follower

def follower_messen(now, kanaele=("instagram", "threads", "x"), zaehler=None):
    """zaehler ist zum Pruefen da: {kanal: callable}. Ohne das die echten APIs."""
    zeilen, berichte = [], []
    for kanal in kanaele:
        try:
            fn = (zaehler or {}).get(kanal) or MESSER[kanal][1]
            wert = fn()
            if wert is None:
                raise Sammelfehler("keine followerzahl in der antwort")
            zeilen.append(jsonl_schreiben(INSIGHTS / FOLLOWER, {
                "kanal": kanal, "follower": wert,
                "gemessen_utc": now.isoformat(timespec="seconds")}))
        except Sammelfehler as exc:
            berichte.append("follower %s: %s" % (kanal, exc))
    return zeilen, berichte


def follower_zum(kanal, zeit_berlin, reihe):
    """Die letzte Followerzahl vor dem Post. Naeher kommt man nicht heran:
    die APIs geben die Followerzahl nur fuer jetzt, nie fuer damals."""
    t = dt.datetime.fromisoformat(str(zeit_berlin))
    vorher = [r for r in reihe if r.get("kanal") == kanal
              and dt.datetime.fromisoformat(r["gemessen_utc"]) <= t]
    return vorher[-1]["follower"] if vorher else None


# ---------------------------------------------------------------- sammeln

def sammeln(now=None, modus="trocken", messer=None, folgen=True, zaehler=None,
            manifeste=None):
    now = now or jetzt()
    eintraege, kaputt = alle(manifeste)
    bericht, neue = [], []
    if kaputt:
        bericht.append("manifest: %d kaputte zeile(n)" % kaputt)
    reihe = jsonl_lesen(INSIGHTS / FOLLOWER)
    nach_kanal = {}
    for e in eintraege:
        nach_kanal.setdefault(e.get("kanal"), []).append(e)
    for kanal, liste in sorted(nach_kanal.items()):
        if kanal not in MESSER:
            bericht.append("kanal %s kennt der sammler nicht" % kanal)
            continue
        vorhanden = jsonl_lesen(pfad(kanal))
        offen = faellig(liste, vorhanden, now)
        if not offen:
            continue
        mess = (messer or {}).get(kanal) or MESSER[kanal][0]
        for e, fenster, nachtrag in offen:
            try:
                werte, fehlt = mess(e["post_id"], e.get("format", "bild"))
            except Sammelfehler as exc:
                bericht.append("%s %s %s: %s" % (kanal, e["post_id"], fenster, exc))
                continue
            s = {"post_id": str(e["post_id"]), "kanal": kanal, "fenster": fenster,
                 "gemessen_utc": now.isoformat(timespec="seconds"),
                 "alter_h": round(alter_h(e["zeit_berlin"], now), 1),
                 "format": e.get("format"), "look": e.get("look"),
                 "variante": e.get("variante", "-"), "werte": werte}
            if nachtrag:
                s["nachtrag"] = True
            if fehlt:
                s["fehlt"] = fehlt
            fb = follower_zum(kanal, e["zeit_berlin"], reihe)
            if fb is not None:
                s["follower_bei_post"] = fb
            neue.append(jsonl_schreiben(pfad(kanal), s))
    if folgen:
        _, fb = follower_messen(now, zaehler=zaehler)
        bericht += fb
    alarme = ausreisser(neue)
    return {"neu": neue, "bericht": bericht, "alarme": alarme, "modus": modus}


# ---------------------------------------------------------------- ausreisser

def median(werte):
    werte = [w for w in werte if isinstance(w, (int, float))]
    return statistics.median(werte) if werte else None


def ausreisser(neue, frueher=None):
    """Reichweite ab dem Dreifachen des Kanal-Medians der letzten 30 Posts.
    Median, nicht Mittel: ein einzelner Ausreisser zieht ein Mittel mit und
    hebt damit die Schwelle genau dann, wenn sie greifen soll. Unter sieben
    Posts je Kanal gibt es keinen Alarm - ein Median aus drei Zahlen ist
    eine Meinung. frueher ist zum Pruefen da; ohne das kommt die Reihe aus
    data/insights/<kanal>.jsonl."""
    aus = []
    for s in neue:
        if s.get("fenster") != "24h":
            continue
        kanal = s["kanal"]
        name = REICHWEITE.get(kanal)
        wert = (s.get("werte") or {}).get(name)
        if not isinstance(wert, (int, float)):
            continue
        vorher = [x for x in (jsonl_lesen(pfad(kanal)) if frueher is None else frueher)
                  if x.get("fenster") == "24h" and x.get("kanal", kanal) == kanal
                  and str(x.get("post_id")) != s["post_id"]]
        werte = [(x.get("werte") or {}).get(name) for x in vorher[-MEDIAN_POSTS:]]
        werte = [w for w in werte if isinstance(w, (int, float))]
        if len(werte) < ALARM_MIN_POSTS:
            continue
        m = median(werte)
        if not m or wert < m * ALARM_FAKTOR:
            continue
        aus.append({"kanal": kanal, "post_id": s["post_id"], "wert": wert,
                    "median": m, "faktor": round(wert / m, 1),
                    "look": s.get("look"), "variante": s.get("variante")})
    return aus


def alarm_text(a, link=""):
    return ("ausreisser %s: %s %s, reichweite %s, median %s, faktor %sx%s. "
            "Kommentare jetzt beantworten." % (
                a["kanal"], a.get("look") or "-", a.get("variante") or "-",
                a["wert"], a["median"], a["faktor"], (" " + link) if link else ""))


def link_zu(post_id, kanal):
    for e in alle()[0]:
        if str(e.get("post_id")) == str(post_id) and e.get("kanal") == kanal:
            return e.get("permalink", "")
    return ""


# ---------------------------------------------------------------- trichter

def brevo_anmeldungen(tage=7, now=None, hole_fn=hole):
    """Anmeldungen je Kanal aus den Kontaktattributen in Brevo. Gezaehlt wird
    UTM_SOURCE; Kontakte ohne Attribut laufen als direct, weil sie es sind."""
    key = umgebung("BREVO_API_KEY")
    now = now or jetzt()
    seit = (now - dt.timedelta(days=tage)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    kopf = {"api-key": key, "accept": "application/json"}
    zaehler, offset, gesamt = {}, 0, 0
    while True:
        d = hole_fn("https://api.brevo.com/v3/contacts?limit=500&offset=%d&createdSince=%s"
                    % (offset, urllib.parse.quote(seit)), kopf)
        stapel = d.get("contacts", [])
        for k in stapel:
            a = k.get("attributes") or {}
            quelle = (a.get("UTM_SOURCE") or "direct").lower()
            zaehler[quelle] = zaehler.get(quelle, 0) + 1
            gesamt += 1
        if len(stapel) < 500:
            break
        offset += 500
        if offset > 20000:
            break
    return {"seit_tage": tage, "gesamt": gesamt, "je_kanal": zaehler,
            "gemessen_utc": now.isoformat(timespec="seconds")}


def trichter(now=None, hole_fn=hole):
    now = now or jetzt()
    bericht = []
    try:
        d = brevo_anmeldungen(7, now, hole_fn)
        jsonl_schreiben(INSIGHTS / TRICHTER, d)
        bericht.append("anmeldungen 7 tage: %d (%s)" % (
            d["gesamt"], ", ".join("%s %d" % kv for kv in sorted(d["je_kanal"].items())) or "keine"))
    except Sammelfehler as exc:
        bericht.append("anmeldungen: %s" % exc)
    # Klicks je Kurzlink: dafuer gibt es bis heute keine Quelle. Die Kurzlinks
    # sind statische Seiten auf GitHub Pages, dort gibt es kein Protokoll, und
    # eine Zaehlung im Browser hat die Weiterleitung mit meta refresh absicht-
    # lich nicht. Gemessen wird deshalb erst die Anmeldung, nicht der Klick.
    bericht.append("klicks je kurzlink: keine quelle, siehe docs/uhrwerk.md")
    return bericht


# ---------------------------------------------------------------- meldung

def melden(text, modus="trocken"):
    hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
    if modus != "scharf" or not hook:
        ausgabe("[%s] %s" % ("trocken" if modus != "scharf" else "kein webhook", text))
        return 0
    leib = json.dumps({"content": sauber(text)[:1990],
                       "allowed_mentions": {"parse": []}}).encode()
    try:
        hole(hook, {"Content-Type": "application/json"}, leib, "POST")
    except Sammelfehler as exc:
        ausgabe("meldung nicht abgesetzt, %s" % exc)
        return 1
    ausgabe("an #moderator-only abgesetzt")
    return 0


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import tempfile
    global INSIGHTS, MANIFEST
    import post_manifest
    n = [0]

    def ok(was, bedingung):
        n[0] += 1
        print("%s %s" % ("ok  " if bedingung else "FEHL", was))
        if not bedingung:
            raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmp:
        INSIGHTS = Path(tmp)
        MANIFEST = Path(tmp, "manifest.jsonl")
        ZWEITES = Path(tmp, "manifest-studio.jsonl")
        post_manifest.MANIFEST = MANIFEST
        post_manifest.MANIFESTE = [MANIFEST, ZWEITES]
        globals()["MANIFEST"] = MANIFEST
        now = dt.datetime(2026, 10, 20, 10, 0, tzinfo=dt.timezone.utc)

        def mani(pid, kanal="instagram", form="bild", tage=0, stunden=0, variante="A", look="l1"):
            zeit = (now - dt.timedelta(days=tage, hours=stunden))
            tz = dt.timezone(dt.timedelta(hours=berlin_offset(zeit)))
            post_manifest.eintragen(kanal=kanal, post_id=pid, format_=form, look=look,
                                    hook="h %s" % pid, hashtags=2, variante=variante,
                                    laenge_s=31 if form in ("reel", "story") else None,
                                    permalink="https://example.invalid/%s" % pid,
                                    zeit_berlin=zeit.astimezone(tz).isoformat(timespec="seconds"),
                                    pfad=MANIFEST, now=now)

        mani("p26", stunden=26)            # reif fuer 24h, nicht fuer 7d
        mani("p10", stunden=10)            # noch zu jung
        mani("p9d", tage=9)                # beide fenster, und zu spaet fuer 24h
        eintraege, _ = lesen(MANIFEST)
        offen = faellig(eintraege, [], now)
        ok("ein post von 26 stunden ist nur fuer 24h faellig",
           sorted((e["post_id"], f) for e, f, _ in offen) ==
           [("p26", "24h"), ("p9d", "24h"), ("p9d", "7d")])
        ok("der nachtrag-stempel sitzt am zu spaet gemessenen fenster",
           {(e["post_id"], f): nt for e, f, nt in offen}[("p9d", "24h")] is True)
        ok("ein frisch gemessenes fenster ist nicht nachtrag",
           {(e["post_id"], f): nt for e, f, nt in offen}[("p26", "24h")] is False)
        ok("ein schon gemessenes fenster kommt nicht wieder",
           [(e["post_id"], f) for e, f, _ in
            faellig(eintraege, [{"post_id": "p26", "fenster": "24h"}], now)] ==
           [("p9d", "24h"), ("p9d", "7d")])

        mani("s1", form="story", stunden=30)
        ok("eine story hat nur das fenster 24h",
           [f for e, f, _ in faellig(lesen(MANIFEST)[0], [], now) if e["post_id"] == "s1"] == ["24h"])

        rufe = []

        def falscher_messer(pid, form="bild"):
            rufe.append(pid)
            if pid == "p9d":
                raise Sammelfehler("http 400 auf graph.facebook.com/p9d, media not found")
            return {"reach": 4100, "views": 5200, "likes": 61}, []

        erg = sammeln(now=now, messer={"instagram": falscher_messer}, folgen=False)
        ok("ein kanalfehler nimmt die anderen posts nicht mit", len(erg["neu"]) == 2)
        ok("der fehler steht im bericht",
           any("p9d" in b and "media not found" in b for b in erg["bericht"]))
        ok("die zeile traegt fenster, format, look und variante",
           erg["neu"][0]["fenster"] == "24h" and erg["neu"][0]["look"] == "l1"
           and erg["neu"][0]["variante"] == "A" and erg["neu"][0]["format"] == "bild")
        ok("alter_h steht in der zeile", erg["neu"][0]["alter_h"] == 26.0)
        zweiter = sammeln(now=now, messer={"instagram": falscher_messer}, folgen=False)
        ok("derselbe lauf noch einmal misst nichts doppelt", zweiter["neu"] == [])

        # zweites manifest, wie es das reel in pulse-studio schreibt
        post_manifest.eintragen(kanal="instagram", post_id="r1", format_="reel",
                                look="kp-nod", hook="this week's number", hashtags=3,
                                variante="B", laenge_s=31,
                                zeit_berlin=(now - dt.timedelta(hours=30)).astimezone(
                                    dt.timezone(dt.timedelta(hours=2))).isoformat(timespec="seconds"),
                                pfad=ZWEITES, now=now)
        erg = sammeln(now=now, messer={"instagram": falscher_messer}, folgen=False)
        ok("ein post aus dem zweiten manifest wird mitgemessen",
           [s["post_id"] for s in erg["neu"]] == ["r1"])
        ok("die laenge kommt aus dem manifest des anderen repos",
           erg["neu"][0]["format"] == "reel" and erg["neu"][0]["look"] == "kp-nod")
        ok("derselbe post in beiden dateien wird einmal gezaehlt",
           len([e for e in post_manifest.alle([MANIFEST, MANIFEST])[0]
                if e["post_id"] == "p26"]) == 1)

        ok("follower werden je kanal geschrieben",
           len(follower_messen(now, ("instagram",), {"instagram": lambda: 1234})[0]) == 1)
        ok("eine fehlende followerzahl ist ein bericht, kein abbruch",
           follower_messen(now, ("threads",), {"threads": lambda: None})[1] != [])
        reihe = jsonl_lesen(INSIGHTS / FOLLOWER)
        ok("followerzahl vor dem post wird zugeordnet",
           follower_zum("instagram", (now + dt.timedelta(hours=1)).isoformat(), reihe) == 1234)
        ok("vor der ersten messung gibt es keine followerzahl",
           follower_zum("instagram", (now - dt.timedelta(days=5)).isoformat(), reihe) is None)

    # ausreisser gegen eine feste reihe, ohne datei
    reihe = [{"post_id": str(i), "kanal": "instagram", "fenster": "24h",
              "werte": {"reach": 1000}} for i in range(10)]
    hoch = {"post_id": "neu", "kanal": "instagram", "fenster": "24h", "look": "l1",
            "variante": "B", "werte": {"reach": 3100}}
    ok("dreifacher median loest aus",
       len(ausreisser([hoch], reihe)) == 1)
    ok("knapp unter dem dreifachen loest nicht aus",
       ausreisser([dict(hoch, werte={"reach": 2900})], reihe) == [])
    ok("unter sieben posts gibt es keinen alarm",
       ausreisser([hoch], reihe[:5]) == [])
    ok("das fenster 7d loest keinen alarm aus",
       ausreisser([dict(hoch, fenster="7d")], reihe) == [])
    ok("ohne reichweite in der antwort kein alarm",
       ausreisser([dict(hoch, werte={"likes": 9})], reihe) == [])
    schief = [{"post_id": str(i), "kanal": "instagram", "fenster": "24h",
               "werte": {"reach": w}} for i, w in enumerate([900] * 9 + [40000])]
    ok("ein alter ausreisser hebt die schwelle nicht (median statt mittel)",
       len(ausreisser([dict(hoch, werte={"reach": 2800})], schief)) == 1)
    ok("ein fremder kanal in der reihe zaehlt nicht mit",
       ausreisser([hoch], [dict(x, kanal="threads") for x in reihe]) == [])
    ok("der alarmtext nennt den faktor und die bitte",
       "3.1x" in alarm_text({"kanal": "instagram", "look": "l1", "variante": "B",
                             "wert": 3100, "median": 1000, "faktor": 3.1})
       and "Kommentare jetzt beantworten" in alarm_text(
           {"kanal": "instagram", "look": "l1", "variante": "B",
            "wert": 3100, "median": 1000, "faktor": 3.1}))
    ok("median nimmt die mitte", median([1, 2, 3, 100]) == 2.5)
    ok("median ohne zahlen ist nichts", median([None, "x"]) is None)

    # api-antworten, mit erfundenen antworten statt netz
    os.environ["INSTAGRAM_PAGE_TOKEN"] = "EA" + "b" * 30
    os.environ["IG_USER_ID"] = "17841400000000000"
    try:
        adressen = []

        def ig_antwort(url, kopf=None, daten=None, methode="GET"):
            adressen.append(url)
            if not (kopf or {}).get("Authorization", "").startswith("Bearer "):
                raise Sammelfehler("ohne token im kopf")
            if "metric=reach,views" in url:
                raise Sammelfehler("http 400, metric profile_visits is not supported")
            if "metric=" in url:
                name = url.split("metric=")[1].split("&")[0]
                if name == "profile_visits":
                    raise Sammelfehler("http 400, metric not supported for this media")
                return {"data": [{"name": name, "values": [{"value": 7}]}]}
            return {"followers_count": 2001}
        werte, fehlt = ig_messen("991", "bild", hole_fn=ig_antwort)
        ok("der rueckfall holt die metriken einzeln", werte.get("reach") == 7)
        ok("eine unbekannte metrik steht als fehlend in der zeile",
           any(f.startswith("profile_visits") for f in fehlt) and len(fehlt) == 1)
        ok("followerzahl aus der antwort", ig_follower(hole_fn=ig_antwort) == 2001)
        ok("das token steht in keiner adresse",
           adressen and not any("access_token" in u for u in adressen))
        ok("total_value wird auch gelesen",
           _ig_wert({"total_value": {"value": 12}}) == 12)
        ok("ein leerer wert bleibt nichts", _ig_wert({"values": []}) is None)
    finally:
        del os.environ["INSTAGRAM_PAGE_TOKEN"], os.environ["IG_USER_ID"]

    os.environ["THREADS_TOKEN"] = "TH" + "c" * 30
    try:
        def th_antwort(url, kopf=None, daten=None, methode="GET"):
            ok_kopf = (kopf or {}).get("Authorization", "")
            if not ok_kopf.startswith("Bearer "):
                raise Sammelfehler("ohne token")
            name = url.split("metric=")[1].split("&")[0]
            if name.startswith("views,"):
                raise Sammelfehler("http 400")
            return {"data": [{"name": name, "total_value": {"value": 42}}]}
        werte, fehlt = th_messen("7001", hole_fn=th_antwort)
        ok("threads einzeln gelesen", werte.get("views") == 42 and fehlt == [])
        ok("threads-token steht nur im header, nicht in der adresse",
           "TH" + "c" * 30 not in json.dumps(werte))
    finally:
        del os.environ["THREADS_TOKEN"]

    for name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        os.environ[name] = "x" * 20
    try:
        def x_antwort(q):
            g = q["tweet.fields"]
            if g == "public_metrics":
                return {"data": {"public_metrics": {"impression_count": 5000, "like_count": 9}}}
            raise RuntimeError("X antwortet HTTP 403 auf GET /2/tweets: "
                               "Your current access level does not include %s" % g)
        werte, fehlt = x_messen("1800", hole_fn=x_antwort)
        ok("public_metrics kommt an", werte.get("impression_count") == 5000)
        ok("die abgelehnten gruppen stehen in der zeile",
           len(fehlt) == 2 and all("403" in f for f in fehlt))
        ok("x-follower aus public_metrics",
           x_follower(hole_fn=lambda q: {"data": {"public_metrics": {"followers_count": 812}}}) == 812)
    finally:
        for name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
            del os.environ[name]

    os.environ["BREVO_API_KEY"] = "xkeysib-" + "d" * 20
    try:
        seiten = [{"contacts": [{"attributes": {"UTM_SOURCE": "instagram"}},
                                {"attributes": {"UTM_SOURCE": "Instagram"}},
                                {"attributes": {}}]}]
        d = brevo_anmeldungen(7, dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc),
                              hole_fn=lambda u, k=None: seiten[0])
        ok("anmeldungen werden je kanal gezaehlt", d["je_kanal"]["instagram"] == 2)
        ok("ohne herkunft zaehlt direct", d["je_kanal"]["direct"] == 1)
        ok("der schluessel steht im header, nicht in der adresse", d["gesamt"] == 3)
    finally:
        del os.environ["BREVO_API_KEY"]

    ok("ein fehlendes token ist ein sammelfehler, kein abbruch",
       isinstance(_fehlt_pruefen(), Sammelfehler))
    ok("parameter stehen nie in einer fehlermeldung",
       _weg("https://graph.facebook.com/v21.0/9/insights?access_token=EAxyz")
       == "graph.facebook.com/v21.0/9/insights")
    print("%d pruefungen, alle gruen" % n[0])


def _fehlt_pruefen():
    try:
        umgebung("GIBT_ES_NICHT_UHRWERK")
    except Sammelfehler as exc:
        return exc
    return None


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="schnappschuesse zu den posts, 24h und 7d")
    ap.add_argument("--sammeln", action="store_true")
    ap.add_argument("--trichter", action="store_true", help="anmeldungen je kanal, montags")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--modus", choices=("trocken", "scharf"), default="trocken")
    ap.add_argument("--ohne-follower", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        selbsttest()
        return 0
    if not (a.sammeln or a.trichter):
        ap.print_help()
        return 0
    zeilen = []
    if a.sammeln:
        erg = sammeln(modus=a.modus, folgen=not a.ohne_follower)
        for s in erg["neu"]:
            ausgabe("%s %s %s: %s" % (s["kanal"], s["post_id"], s["fenster"],
                                      json.dumps(s["werte"], sort_keys=True)))
        zeilen.append("uhrwerk: %d schnappschuss(e)%s" % (
            len(erg["neu"]), ", %d hinweis(e)" % len(erg["bericht"]) if erg["bericht"] else ""))
        zeilen += ["  " + b for b in erg["bericht"]]
        for al in erg["alarme"]:
            melden(alarm_text(al, link_zu(al["post_id"], al["kanal"])), a.modus)
    if a.trichter:
        zeilen += trichter()
    text = "\n".join(zeilen)
    ausgabe(text)
    melden(text, a.modus)
    return 0


if __name__ == "__main__":
    sys.exit(main())
