#!/usr/bin/env python3
"""look_takt.py, die drei Looks und ihr Takt je Kanal (Ben, 15.10.2026).

DREI LOOKS. dunkel, hell, teal. Jeder Look ist ein Satz Farben (LOOKS), den
die Generatoren lesen, statt eigene Farben zu fuehren. Die Schriften stehen
eingebettet in schriften_css(), aus graphics/fonts, ohne Laden zur Laufzeit.

DER TAKT. Je Kanal und Serie dunkel, hell, teal, hell, dann von vorn. Teal
ist also jeder 4. Post. Ein 3er-Takt ergaebe im Instagram-Raster mit drei
Spalten eine ganze Teal-Spalte. Der Look kommt aus dem Takt, die Form aus dem
Wochentag wie bisher.

DER SPEICHER. data/look-takt.json haelt je "serie/kanal" die letzten
Eintraege (datum, schritt, look). Damit stimmt der Takt ueber Laeufe hinweg.
Ein zweiter Lauf am selben Tag bekommt denselben Look wie der erste, er
schiebt den Takt nicht weiter. Meme (Samstag) und Render (Sonntag) ersetzen
den faelligen Look: sie belegen den Schritt, der Takt laeuft danach weiter.

Serie und Kanal getrennt: die Zahl des Tages und die Tagesgrafik laufen beide
auf X und Discord. Mit einem gemeinsamen Takt waere die Zahl des Tages bei
zwei Posts am Tag immer hell. Die Zahl des Tages startet deshalb einen
Schritt versetzt (VERSATZ), dann tragen beide am selben Tag nie denselben Look,
solange beide taeglich laufen.

DAS INSTAGRAM-RASTER (Ben, 18.10.2026). Instagram hat einen gemeinsamen
Takt fuer alle Posts im Raster, Tagesgrafik und Karussell (RASTER, RANG).
Das Karussell nimmt den Schritt nach der Tagesgrafik desselben Tages.

TROCKENLAUF. ZIEL=moderator in der Umgebung heisst: bauen wie scharf, posten
nur nach #moderator-only. trockenlauf() ist die eine Stelle, die das liest.

    python3 scripts/look_takt.py --zeigen            den speicher lesen
    python3 scripts/look_takt.py --selbsttest
"""
import argparse
import base64
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEICHER = REPO / "data" / "look-takt.json"
SCHRIFTEN = REPO / "graphics" / "fonts"

TAKT = ("dunkel", "hell", "teal", "hell")
SONDER = ("meme", "render")          # ersetzen den faelligen look
KANAELE = ("instagram", "threads", "x", "discord")
VERSATZ = {"zahl": 1}                # startschritt je serie, sonst 0
BEHALTEN = 12                        # eintraege je serie/kanal im speicher

# Die Farben je Look (Ben, 15.10.2026). Der Filter "falke" ist mit der
# Marken-Umstellung weg (Ben, 21.10.2026), es gibt keinen Falken mehr; die
# Wortmarke steht in scripts/wortmarke.py und holt text und akzent von hier.
# grund, text, text2 und akzent sind
# vorgegeben. rest ist der dritte Ton fuer den "Rest" der Daten, akzent2 der
# dunkler abgesetzte Akzent (Form 11), markierung die Pulslinie und kleine
# Hervorhebungen. Im hellen Look ist #49EACB nur Markierung, die Balken
# tragen #0F9A80.
LOOKS = {
    "dunkel": {"grund": "#080B0F", "text": "#F2F5F4", "text2": "#A9B7B4",
               "akzent": "#49EACB", "akzent2": "#2FAE96", "rest": "#2B7A6C",
               "flaeche": "#1B252B", "markierung": "#49EACB"},
    "hell":   {"grund": "#EEF3F1", "text": "#0B1A17", "text2": "#4F625D",
               "akzent": "#0F9A80", "akzent2": "#0B6B59", "rest": "#B4CCC5",
               "flaeche": "#DCE6E2", "markierung": "#49EACB"},
    "teal":   {"grund": "#49EACB", "text": "#04211C", "text2": "#0F4A40",
               "akzent": "#04211C", "akzent2": "#0F4A40", "rest": "#9AF5E3",
               "flaeche": "#3BD3B6", "markierung": "#04211C"},
}

# Schnitte, die eingebettet werden. Anton und Permanent Marker kommen mit
# dem Meme-Geruest, mit ihrer OFL-Datei.
SCHNITTE = (("Archivo", 800, "archivo-latin-800-normal.woff2"),
            ("Archivo", 900, "archivo-latin-900-normal.woff2"),
            ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal.woff2"),
            ("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal.woff2"),
            ("IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal.woff2"),
            ("IBM Plex Sans", 500, "ibm-plex-sans-latin-500-normal.woff2"),
            ("IBM Plex Sans", 600, "ibm-plex-sans-latin-600-normal.woff2"))
TITEL = "'Archivo',sans-serif"
MONO = "'IBM Plex Mono',monospace"
SANS = "'IBM Plex Sans',sans-serif"


class Fehler(Exception):
    pass


def schriften_css():
    """@font-face fuer alle Schnitte, als data:-URL. Fehlt eine Datei, stoppt
    der Lauf: eine Ersatzschrift wuerde jede Messung verschieben."""
    teile = []
    for familie, gewicht, datei in SCHNITTE:
        p = SCHRIFTEN / datei
        if not p.exists():
            raise Fehler("schrift fehlt, %s" % p.relative_to(REPO))
        teile.append("@font-face{font-family:'%s';font-weight:%d;font-style:normal;"
                     "src:url(data:font/woff2;base64,%s) format('woff2')}"
                     % (familie, gewicht, base64.b64encode(p.read_bytes()).decode()))
    return "".join(teile)


def look(name):
    if name not in LOOKS:
        raise Fehler("unbekannter look %r" % name)
    return dict(LOOKS[name], name=name)


# ------------------------------------------------------------ speicher

def lesen(pfad=None):
    try:
        return json.loads(Path(pfad or SPEICHER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"kanaele": {}}


def schreiben(speicher, pfad=None):
    p = Path(pfad or SPEICHER)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(speicher, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                 encoding="utf-8")


def _schluessel(serie, kanal):
    if kanal not in KANAELE:
        raise Fehler("unbekannter kanal %r" % kanal)
    return "%s/%s" % (serie, kanal)


def faellig(speicher, serie, kanal, datum):
    """(schritt, look) fuer diesen Post. Steht der Tag schon im Speicher,
    gilt der Eintrag von dort (zweiter Lauf am selben Tag)."""
    datum = str(datum)
    reihe = speicher.get("kanaele", {}).get(_schluessel(serie, kanal), [])
    for e in reihe:
        if e["datum"] == datum:
            return e["schritt"], e["look"]
    frueher = [e for e in reihe if e["datum"] < datum]
    if not frueher:
        schritt = VERSATZ.get(serie, 0) % len(TAKT)
    else:
        schritt = (max(frueher, key=lambda e: e["datum"])["schritt"] + 1) % len(TAKT)
    return schritt, TAKT[schritt]


def merken(speicher, serie, kanal, datum, sonder=None):
    """Traegt den Post ein und gibt den Look zurueck. sonder ("meme" oder
    "render") belegt den faelligen Schritt, ohne dessen Look zu zeigen."""
    if sonder is not None and sonder not in SONDER:
        raise Fehler("unbekannter sonderlook %r" % sonder)
    schritt, lk = faellig(speicher, serie, kanal, datum)
    schl = _schluessel(serie, kanal)
    reihe = [e for e in speicher.setdefault("kanaele", {}).get(schl, []) if e["datum"] != str(datum)]
    reihe.append({"datum": str(datum), "schritt": schritt, "look": sonder or lk})
    speicher["kanaele"][schl] = sorted(reihe, key=lambda e: e["datum"])[-BEHALTEN:]
    return sonder or lk


# ---------------------------------------------------- das instagram-raster
#
# EIN TAKT FUER ALLE INSTAGRAM-POSTS (Ben, 18.10.2026). Tagesgrafik und
# Karussell landen im selben Raster mit drei Spalten. Getrennte Takte
# braechen dort das Muster dunkel, hell, teal, hell. Deshalb fuehrt
# "raster/instagram" alle Posts in der Reihenfolge, in der sie im Raster
# stehen: nach Datum, und am selben Tag nach RANG (die Tagesgrafik um 09:30
# vor dem Karussell um 11:00 oder 18:00). Jeder Eintrag traegt seine Serie.
#
# Das Karussell legt seinen Eintrag schon beim Entwurf am Vorabend an. Die
# Tagesgrafik des Folgetags sieht ihn nicht als Vorgaenger, weil sie im
# Rang davor steht, und rechnet vom Vortag weiter. Das Karussell nimmt den
# Schritt nach ihr.
RASTER = "raster/instagram"
RANG = {"tagesgrafik": 1, "meme": 2, "karussell": 3}


def _raster_ort(e):
    return (e["datum"], RANG.get(e.get("serie"), 9))


def raster_faellig(speicher, serie, datum):
    """(schritt, look) fuer einen Instagram-Post dieser Serie an diesem Tag."""
    if serie not in RANG:
        raise Fehler("unbekannte serie im raster %r" % serie)
    datum = str(datum)
    reihe = speicher.get("kanaele", {}).get(RASTER, [])
    for e in reihe:
        if e["datum"] == datum and e.get("serie") == serie:
            return e["schritt"], e["look"]
    # ein spaeterer rang folgt dem letzten post desselben tags davor. gibt es
    # an dem tag noch keinen, folgt er der tagesgrafik, auch wenn die noch
    # nicht gelaufen ist (der entwurf entsteht oft am vorabend). ein rang
    # ohne post (kein meme an einem karussell-samstag) zaehlt nicht mit.
    if RANG[serie] > 1:
        am_tag = [e for e in reihe if e["datum"] == datum and 1 < RANG.get(e.get("serie"), 9) < RANG[serie]]
        if am_tag:
            schritt = (max(am_tag, key=_raster_ort)["schritt"] + 1) % len(TAKT)
        else:
            schritt = (raster_faellig(speicher, "tagesgrafik", datum)[0] + 1) % len(TAKT)
        return schritt, TAKT[schritt]
    ort = (datum, RANG[serie])
    davor = [e for e in reihe if _raster_ort(e) < ort]
    if davor:
        schritt = (max(davor, key=_raster_ort)["schritt"] + 1) % len(TAKT)
    else:
        # der erste raster-eintrag knuepft an den alten takt der tagesgrafik an
        alt = [e for e in speicher.get("kanaele", {}).get("tagesgrafik/instagram", []) if e["datum"] < datum]
        schritt = ((max(alt, key=lambda e: e["datum"])["schritt"] + 1) % len(TAKT)) if alt else 0
    return schritt, TAKT[schritt]


def raster_merken(speicher, serie, datum, sonder=None):
    if sonder is not None and sonder not in SONDER:
        raise Fehler("unbekannter sonderlook %r" % sonder)
    schritt, lk = raster_faellig(speicher, serie, datum)
    reihe = [e for e in speicher.setdefault("kanaele", {}).get(RASTER, [])
             if not (e["datum"] == str(datum) and e.get("serie") == serie)]
    reihe.append({"datum": str(datum), "serie": serie, "schritt": schritt, "look": sonder or lk})
    speicher["kanaele"][RASTER] = sorted(reihe, key=_raster_ort)[-2 * BEHALTEN:]
    return sonder or lk


def looks_fuer(speicher, serie, datum, kanaele=KANAELE):
    """{kanal: look} fuer einen Lauf, ohne zu schreiben."""
    return {k: faellig(speicher, serie, k, datum)[1] for k in kanaele}


def trockenlauf():
    """ZIEL=moderator: bauen wie scharf, posten nur nach #moderator-only."""
    return os.environ.get("ZIEL", "").strip().lower() == "moderator"


# ------------------------------------------------------------ selbsttest

def _kontrast(a, b):
    def lum(h):
        r, g, bl = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        f = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, bl)]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    sp = {"kanaele": {}}
    tag0 = dt.date(2026, 10, 17)
    folge = []
    for i in range(9):
        folge.append(merken(sp, "tagesgrafik", "instagram", tag0 + dt.timedelta(days=i)))
    ok("takt dunkel hell teal hell, von vorn (%s)" % " ".join(folge),
       folge == ["dunkel", "hell", "teal", "hell"] * 2 + ["dunkel"])
    ok("teal genau jeder 4. post", [i for i, x in enumerate(folge) if x == "teal"] == [2, 6])
    ok("zweiter lauf am selben tag schiebt nicht weiter",
       merken(sp, "tagesgrafik", "instagram", tag0 + dt.timedelta(days=8)) == "dunkel"
       and len(sp["kanaele"]["tagesgrafik/instagram"]) == 9)
    ok("speicher behaelt hoechstens %d eintraege" % BEHALTEN,
       all(len(r) <= BEHALTEN for r in sp["kanaele"].values()))
    # kanaele laufen getrennt
    merken(sp, "tagesgrafik", "x", tag0)
    ok("x hat einen eigenen takt", faellig(sp, "tagesgrafik", "x", tag0 + dt.timedelta(days=1))[1] == "hell")
    # luecke im speicher: der takt laeuft vom letzten eintrag weiter, nicht vom kalender
    ok("nach einer luecke geht es beim naechsten schritt weiter",
       faellig(sp, "tagesgrafik", "x", tag0 + dt.timedelta(days=5))[1] == "hell")
    # zahl des tages versetzt: am selben tag nie derselbe look wie die tagesgrafik
    sp2 = {"kanaele": {}}
    gleich = 0
    for i in range(12):
        d = tag0 + dt.timedelta(days=i)
        gleich += merken(sp2, "tagesgrafik", "x", d) == merken(sp2, "zahl", "x", d)
    ok("tagesgrafik und zahl des tages auf x nie gleich am selben tag", gleich == 0)
    # sonderlook belegt den schritt
    sp3 = {"kanaele": {}}
    a = merken(sp3, "tagesgrafik", "instagram", tag0)
    b = merken(sp3, "tagesgrafik", "instagram", tag0 + dt.timedelta(days=1), sonder="meme")
    c = merken(sp3, "tagesgrafik", "instagram", tag0 + dt.timedelta(days=2))
    ok("meme ersetzt den faelligen look, danach teal (%s %s %s)" % (a, b, c),
       (a, b, c) == ("dunkel", "meme", "teal"))
    try:
        merken(sp3, "tagesgrafik", "tiktok", tag0)
        ok("unbekannter kanal stoppt", False)
    except Fehler:
        ok("unbekannter kanal stoppt", True)
    # roundtrip durch die datei
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "lt.json"
        schreiben(sp, p)
        ok("speicher liest sich zurueck", lesen(p) == json.loads(json.dumps(sp)))
        ok("fehlender speicher ist leer", lesen(Path(td) / "fehlt.json") == {"kanaele": {}})
    # farben: text gegen grund mindestens 4.5, akzent gegen grund mindestens 3
    for name, l in LOOKS.items():
        ok("%s text %.1f, text2 %.1f gegen grund" % (name, _kontrast(l["text"], l["grund"]),
                                                    _kontrast(l["text2"], l["grund"])),
           _kontrast(l["text"], l["grund"]) >= 7 and _kontrast(l["text2"], l["grund"]) >= 4.5)
        ok("%s akzent %.1f gegen grund" % (name, _kontrast(l["akzent"], l["grund"])),
           _kontrast(l["akzent"], l["grund"]) >= 3)
    # das gemeinsame instagram-raster (Ben, 18.10.2026)
    sp4 = {"kanaele": {"tagesgrafik/instagram": [{"datum": "2026-10-18", "schritt": 1, "look": "hell"}]}}
    ok("raster knuepft an den alten tagesgrafik-takt an",
       raster_merken(sp4, "tagesgrafik", "2026-10-19") == "teal")
    # freitag 23.10. tagesgrafik, entwurf fuer samstag am freitagabend
    for d in ("2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"):
        raster_merken(sp4, "tagesgrafik", d)
    fr = raster_faellig(sp4, "tagesgrafik", "2026-10-23")[0]
    k = raster_merken(sp4, "karussell", "2026-10-24")
    sa = raster_merken(sp4, "tagesgrafik", "2026-10-24")
    so = raster_merken(sp4, "tagesgrafik", "2026-10-25")
    folge = [e["look"] for e in sp4["kanaele"][RASTER]]
    ok("karussell nimmt den schritt nach der tagesgrafik desselben tags (%s)" % " ".join(folge),
       raster_faellig(sp4, "karussell", "2026-10-24")[0] == (fr + 2) % 4
       and raster_faellig(sp4, "tagesgrafik", "2026-10-24")[0] == (fr + 1) % 4
       and raster_faellig(sp4, "tagesgrafik", "2026-10-25")[0] == (fr + 3) % 4)
    ok("im raster laeuft das muster ohne bruch", folge == [TAKT[(1 + i + 1) % 4] for i in range(len(folge))])
    # das meme am sonntag (Ben, 19.10.2026): eigener rang nach der tagesgrafik,
    # und an einem karussell-samstag ohne meme ueberspringt nichts
    m = raster_merken(sp4, "meme", "2026-10-25")
    ok("meme am sonntag nimmt den schritt nach der tagesgrafik",
       raster_faellig(sp4, "meme", "2026-10-25")[0] == (raster_faellig(sp4, "tagesgrafik", "2026-10-25")[0] + 1) % 4)
    ok("tagesgrafik am montag folgt dem meme",
       raster_faellig(sp4, "tagesgrafik", "2026-10-26")[0] == (raster_faellig(sp4, "meme", "2026-10-25")[0] + 1) % 4)
    ok("ein zweiter entwurf am selben tag schiebt nicht weiter",
       raster_merken(sp4, "karussell", "2026-10-24") == k)
    ok("hell, #49EACB nur als markierung", LOOKS["hell"]["akzent"] == "#0F9A80"
       and "#49EACB" not in (LOOKS["hell"]["akzent"], LOOKS["hell"]["text"], LOOKS["hell"]["text2"]))
    css = schriften_css()
    ok("sieben schnitte eingebettet, nichts von aussen",
       css.count("@font-face") == 7 and "http" not in css)
    alt_ziel, alt_ops = os.environ.get("ZIEL"), os.environ.pop("DISCORD_WEBHOOK_OPS", None)
    os.environ["ZIEL"] = "moderator"
    t1 = trockenlauf()
    # die schalter in den skripten, die heute automatisch nach aussen posten
    sys.path.insert(0, str(REPO / "scripts"))
    import instagram
    import post_number_of_day
    import x_post
    jetzt = dt.datetime(2026, 10, 17, 7, 40, tzinfo=dt.timezone.utc)   # 09:40 berlin
    lg = {"laeufe": [{"datum": "2026-10-17", "form": 4, "messzeit_utc": "2026-10-17T05:30:00+00:00"}]}
    e, grund = instagram.faellig(jetzt, lg, {"posts": []})
    ok("instagram im trockenlauf nicht faellig (%s)" % grund, e is None and "trockenlauf" in grund)
    ok("instagram von hand bleibt moeglich (trocken)",
       instagram.faellig(jetzt, lg, {"posts": []}, hand=True)[0] is not None)
    ok("zahl des tages ohne ops-webhook bricht ab, faellt nicht auf oeffentlich",
       post_number_of_day.trockenlauf_senden("probe", []) == 1)
    with tempfile.TemporaryDirectory() as td:
        nod = Path(td) / "nod.json"
        nod.write_text(json.dumps({"date": "2026-10-17", "post": {"x": "probe"}}))
        ok("x postet die zahl des tages im trockenlauf nicht",
           x_post.run(argparse.Namespace(from_nod=str(nod), key=None, log=str(Path(td) / "log.json"))) == 0
           and not (Path(td) / "log.json").exists())
    os.environ["ZIEL"] = ""
    ok("ZIEL=moderator ist trockenlauf, leer nicht", t1 and not trockenlauf())
    ok("ohne trockenlauf ist instagram wieder faellig",
       instagram.faellig(jetzt, lg, {"posts": []})[0] is not None)
    if alt_ziel is not None:
        os.environ["ZIEL"] = alt_ziel
    if alt_ops is not None:
        os.environ["DISCORD_WEBHOOK_OPS"] = alt_ops
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    ap.add_argument("--zeigen", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.zeigen:
        print(json.dumps(lesen(), ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
