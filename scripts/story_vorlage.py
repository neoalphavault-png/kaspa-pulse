#!/usr/bin/env python3
"""story_vorlage.py, Instagram-Story-Vorlagen Mo bis Fr (Ben, 24.10.2026).

VORLAGE, NICHT SCHARF. Dieses Skript baut jeden Werktag eine Story im
Format 1080x1920 und schickt sie mit einer genauen Anleitung nach
#moderator-only (DISCORD_WEBHOOK_OPS). Es postet nirgendwo. Ben postet die
Story von Hand um 17:30 und legt das Instagram-Element (Quiz, Slider,
Umfrage, Fragebox, Link) auf die gestrichelte Flaeche im Bild.

WOCHENPLAN
  mo  quiz      "guess the week", eine Wochenzahl aus dem letzten Weekly,
                vier Antworten, eine richtig
  di  slider    "kaspa in real life", eine Schaetzung mit Emoji-Slider, die
                Emission des Tages gegen etwas aus dem Alltag
  mi  poll      "your call", zwei Optionen, eine Messfrage, nie der Kurs
  do  zitat     der staerkste Satz aus dem Erklaerer dieser Woche, darunter
                die Fragebox "what should we count next?"
  fr  wahr      "nobody counts this", wahr oder falsch, eine eigene
                Zaehlung, dazu die Newsletter-Zeile und die Link-Flaeche
  di bis sa     frueh die kleine Aufloesung "yesterday's answer" mit der
                richtigen Antwort und der Zahl von gestern (aus
                data/story-log.json)

INHALT. Zuerst data/story-plan.json (je Woche, Schluessel ist der Montag,
darin je Tag ein Eintrag; Claude oder Ben ueberschreiben dort). Fehlt der
Eintrag, kommen Frage und Antworten aus festen Vorlagen und den Daten:
Weekly (data/weekly-history.json), Emission (dieselbe Datei), Zahl des Tages
(data/number-of-day.json, nur wenn kein Erklaerer da ist), Entity X
(data/entity-x-inflows.json, scripts/entity_x_daily.json).

LOOK. Grund #080B0F, Weiss #F2F5F4, Akzent #49EACB im dunklen Look, dazu
hell und teal im Takt dunkel, hell, teal, hell (look_takt, eigene Serie
"story"). Wortmarke KASPA PULSE, kein Falke. Eine grosse Zahl oder ein
grosses Zitat, klare Rangfolge, viel Platz.

WACHEN, vor dem Rendern und am gerenderten Bild
  Textregeln wie ueberall (content_wache, tagesgrafik.pruefe_eine): kein
  Echtzeit-Wort, "%" statt "percent", kein Gedankenstrich, kein Doppelpunkt,
  kein Pfeil, kein Kursziel, "counted" nur bei eigener Zaehlung, jede Zahl
  mit Datum. Keine Kursfrage, kein Koeder. Umfrage-Optionen hoechstens 24
  Zeichen, Quiz hoechstens vier Optionen. Ein Element ausserhalb der
  sicheren Flaeche (oben 14 %, unten 20 % frei, content_wache "story")
  stoppt. Die Zahl der Story darf nicht die Zahl des heutigen Feed-Posts
  sein.

    python3 scripts/story_vorlage.py --out /tmp/s [--datum 2026-10-26]
    python3 scripts/story_vorlage.py --datum 2026-10-26 --senden     nach ops, look und log merken
    python3 scripts/story_vorlage.py --woche 2026-10-26 --out /tmp/s  mo bis sa auf einmal, ohne senden
    python3 scripts/story_vorlage.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

PLAN = REPO / "data" / "story-plan.json"
LOG = REPO / "data" / "story-log.json"
HISTORY = REPO / "data" / "weekly-history.json"
NOD = REPO / "data" / "number-of-day.json"
KARUSSELL_STORY = REPO / "data" / "karussell-story.json"
EX_INFLOWS = REPO / "data" / "entity-x-inflows.json"
EX_DAILY = HERE / "entity_x_daily.json"
IG_LOG = REPO / "data" / "instagram-log.json"
GRAFIK_LOG = REPO / "data" / "tagesgrafik-log.json"

W, H = 1080, 1920
VORSCHAU = 390
# die sichere flaeche der content_wache, oben 14 % und unten 20 % frei
X0, Y0, X1, Y1 = 60, 270, 900, 1500
TAGE = ("mo", "di", "mi", "do", "fr", "sa")
WOCHENTAG_EN = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MONATE = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
ART_JE_TAG = {"mo": "quiz", "di": "slider", "mi": "poll", "do": "zitat", "fr": "wahr"}
POSTEN = "17:30"
LINK = "kaspapulse.com/story"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"
BEHALTEN = 40
MUSIK = ("ambient electronic", "lofi electronic", "chillwave instrumental", "deep focus electronic",
         "minimal electronic calm", "downtempo instrumental")
SELBST = "counted by kaspa pulse"
POLL_MAX = 24
QUIZ_MAX = 4

# Kurs und Koeder (Ben, 24.10.2026): keine Frage nach dem Kurs, nichts, das
# Klicks mit einem Versprechen kauft.
KURS = re.compile(r"\b(?:price|prices|usd|dollars?|market ?cap|mcap|ath|all.time high|pump|dump|moon|"
                  r"lambo|bull(?:ish)?|bear(?:ish)?|buy|sell|worth|profit|gains?|invest(?:ing|ment)?)\b|\$",
                  re.I)
KOEDER = re.compile(r"\b(?:giveaway|airdrop|free|win|winners?|prize|dm me|dm us|link in comments|"
                    r"tag a friend|tag someone|like if|share if|follow for|100x|1000x|guaranteed|"
                    r"get rich|secret|nobody tells you|you won.t believe|shocking)\b", re.I)


class Stopp(Exception):
    pass


# ------------------------------------------------------------ helfer

def tag(iso):
    j, m, d = str(iso)[:10].split("-")
    return "%d %s %s" % (int(d), MONATE[int(m) - 1], j)


def tag_kurz(iso):
    return " ".join(tag(iso).split()[:2])


def ganz(n):
    return "{:,}".format(int(round(n)))


def kompakt(n):
    """Kurz genug fuer die grosse Zahl in 840 px."""
    a = abs(n)
    if a >= 1e9:
        return "%.2fB" % (n / 1e9)
    if a >= 1e6:
        return "%.2fM" % (n / 1e6)
    if a >= 1e4:
        return "%.0fk" % (n / 1e3)
    return ganz(n)


def montag(d):
    d = dt.date.fromisoformat(str(d))
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def wochentag(d):
    i = dt.date.fromisoformat(str(d)).weekday()
    return TAGE[i] if i < 6 else ""


def saat(*teile):
    """Fester Zufall je Datum: derselbe Tag baut immer dieselbe Story."""
    return int(hashlib.sha256("|".join(str(t) for t in teile).encode()).hexdigest()[:12], 16)


def stichtag(woche):
    """Die Weekly Numbers einer Ausgabe (Montag) stehen auf dem Samstag davor."""
    return (dt.date.fromisoformat(woche) - dt.timedelta(days=2)).isoformat()


def json_lesen(pfad, vorgabe=None):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return vorgabe


def zahl_kern(t):
    """Die Ziffern einer Zahl fuer den Vergleich mit dem Feed: '574M',
    '574 million' und '574,000,000' sind dieselbe Zahl."""
    t = str(t or "").lower().replace(",", "")
    m = re.search(r"[+\-]?\d+(?:\.\d+)?", t)
    if not m:
        return None
    v = float(m.group(0))
    rest = t[m.end():].strip()
    for wort, f in (("billion", 1e9), ("b", 1e9), ("million", 1e6), ("m", 1e6), ("k", 1e3)):
        if rest.startswith(wort) and (len(rest) == len(wort) or not rest[len(wort)].isalpha()):
            v *= f
            break
    return round(abs(v), 6)


# ------------------------------------------------------------ daten

def weekly(history=None):
    h = json_lesen(history or HISTORY, [])
    if len(h) < 2:
        raise Stopp("weekly-history.json hat weniger als zwei ausgaben")
    return h[-1], h[-2]


def quiz_aus_weekly(datum, history=None):
    """Mo, "guess the week". Drei Fragen im Wochentakt, die Antworten sind
    die echte Zahl und drei andere im selben Format."""
    jetzt, vorher = weekly(history)
    s, s0 = stichtag(jetzt["week"]), stichtag(vorher["week"])
    fragen = []
    if jetzt.get("hashrate") and vorher.get("hashrate"):
        d = 100 * (jetzt["hashrate"] / vorher["hashrate"] - 1)
        schritt = max(1.5, round(abs(d) * 0.8, 1))
        fragen.append({
            "id": "hashrate", "titel": "GUESS THE WEEK",
            "text": "how much did the kaspa hashrate move in the week to %s?" % tag_kurz(s),
            "frage": "how much did kaspa hashrate move this week?",
            "richtig": "%+.1f%%" % d, "fmt": lambda v: "%+.1f%%" % v, "wert": d,
            "andere": [d + schritt * 2, d - schritt * 1.5, -d if abs(d) >= 1 else d + schritt * 4],
            "zahl": "%+.1f%%" % d, "loesung": "hashrate %.0f PH/s in the week to %s, %+.1f%% against %s"
                                   % (jetzt["hashrate"], tag_kurz(s), d, tag_kurz(s0)),
            "datum": "week to %s · source kaspa rest api" % tag(s)})
    if jetzt.get("holders") and vorher.get("holders"):
        n = jetzt["holders"] - vorher["holders"]
        schritt = max(2000, round(abs(n) * 0.9, -3))
        fragen.append({
            "id": "holders", "titel": "GUESS THE WEEK",
            "text": "how many addresses with a meaningful balance did kaspa add in the week to %s?"
                    % tag_kurz(s),
            "frage": "how many kaspa addresses joined this week?",
            "richtig": "%+d" % round(n), "fmt": lambda v: "%s%s" % ("+" if v >= 0 else "", ganz(v)),
            "wert": n, "andere": [n + schritt * 2, n - schritt * 1.5, n + schritt * 4],
            "zahl": "%s%s" % ("+" if n >= 0 else "", ganz(n)),
            "loesung": "%s addresses hold a meaningful balance, %s%s in a week"
                       % (ganz(jetzt["holders"]), "+" if n >= 0 else "", ganz(n)),
            "datum": "week to %s · source kaspalytics address counts" % tag(s)})
    if jetzt.get("dormant_pct"):
        p = jetzt["dormant_pct"]
        fragen.append({
            "id": "dormant", "titel": "GUESS THE WEEK",
            "text": "what share of all KAS has not moved in a year, as of the week to %s?" % tag_kurz(s),
            "frage": "what share of all KAS has not moved in a year?",
            "richtig": "%.0f%%" % p, "fmt": lambda v: "%.0f%%" % v, "wert": p,
            "andere": [p - 31, p - 17, p + 22 if p < 70 else p - 42],
            "zahl": "%.0f%%" % p, "loesung": "%.1f%% of all KAS has not moved in a year" % p,
            "datum": "week to %s · source kaspalytics" % tag(s)})
    if not fragen:
        raise Stopp("keine wochenzahl fuer das quiz in der ausgabe %s" % jetzt["week"])
    f = fragen[dt.date.fromisoformat(datum).isocalendar()[1] % len(fragen)]
    antworten = [f["richtig"]]
    for v in f["andere"] + [f["wert"] + 9.5, f["wert"] - 12.5, f["wert"] * 3 + 7]:
        t = f["fmt"](v)
        if t not in antworten:
            antworten.append(t)
        if len(antworten) == 4:
            break
    r = saat(datum, "quiz")
    reihe = sorted(antworten, key=lambda t: saat(r, t))
    return {"art": "quiz", "titel": f["titel"], "text": f["text"], "zahl": "", "einheit": "",
            "frage": f["frage"], "antworten": reihe, "richtig": reihe.index(f["richtig"]),
            "datum": f["datum"], "quelle_vorlage": "weekly %s" % jetzt["week"],
            "aufloesung": {"frage": f["frage"], "zahl": f["zahl"], "einheit": "",
                           "satz": f["loesung"], "datum": f["datum"]}}


ALLTAG = (
    (90, "one football match of 90 minutes", "⚽"),
    (8 * 60, "one night of 8 hours sleep", "\U0001f634"),
    (120, "one movie of 2 hours", "\U0001f37f"),
    (25, "one 25 minute lunch break", "\U0001f96a"),
    (4, "the 4 minutes your coffee brews", "☕"),
)


def slider_aus_emission(datum, history=None):
    """Di, "kaspa in real life". Die Tagesemission gegen eine Zeit aus dem
    Alltag. Die Zahl im Bild ist die Emission, die Antwort kommt morgen."""
    jetzt, _ = weekly(history)
    e = jetzt.get("emission")
    if not e:
        raise Stopp("keine emission in der ausgabe %s" % jetzt["week"])
    minuten, was, emoji = ALLTAG[dt.date.fromisoformat(datum).isocalendar()[1] % len(ALLTAG)]
    antwort = e * minuten / 1440
    d = "as of %s · source kaspa emission schedule" % tag(jetzt["week"])
    return {"art": "slider", "titel": "KASPA IN REAL LIFE", "zahl": kompakt(e), "einheit": "KAS a day",
            "text": "how many new KAS in %s?" % was,
            "frage": "how many KAS are mined during %s?" % was, "emoji": emoji,
            "antwort": "%s KAS" % kompakt(antwort), "datum": d,
            "quelle_vorlage": "emission %s" % jetzt["week"],
            "aufloesung": {"frage": "how many KAS are mined during %s?" % was,
                           "zahl": kompakt(antwort), "einheit": "KAS",
                           "satz": "%s KAS a day, so %s KAS in %s" % (ganz(e), ganz(antwort), was),
                           "datum": d}}


def poll_aus_weekly(datum, history=None):
    """Mi, "your call". Zwei Optionen, eine davon stimmt, gemessen an der
    letzten Ausgabe. Nie der Kurs."""
    jetzt, vorher = weekly(history)
    s, s0 = stichtag(jetzt["week"]), stichtag(vorher["week"])
    d = "week to %s · source %s" % (tag(s), "%s")
    fragen = []
    if jetzt.get("hashrate") and vorher.get("hashrate") and jetzt["hashrate"] != vorher["hashrate"]:
        up = jetzt["hashrate"] > vorher["hashrate"]
        p = 100 * (jetzt["hashrate"] / vorher["hashrate"] - 1)
        fragen.append({"text": "kaspa hashrate in the week to %s, up or down against the week before?"
                               % tag_kurz(s),
                       "frage": "kaspa hashrate this week, up or down?",
                       "optionen": ["up", "down"], "richtig": 0 if up else 1,
                       "sieger": "up" if up else "down",
                       "zahl": "%+.1f%%" % p, "satz": "%.0f PH/s against %.0f PH/s in the week to %s"
                                                      % (jetzt["hashrate"], vorher["hashrate"], tag_kurz(s0)),
                       "datum": d % "kaspa rest api"})
    if jetzt.get("dormant_pct") and vorher.get("dormant_pct") and jetzt["dormant_pct"] != vorher["dormant_pct"]:
        mehr = jetzt["dormant_pct"] > vorher["dormant_pct"]
        fragen.append({"text": "did more KAS fall asleep or wake up in the week to %s?" % tag_kurz(s),
                       "frage": "more KAS asleep or awake this week?",
                       "optionen": ["more fell asleep", "more woke up"], "richtig": 0 if mehr else 1,
                       "sieger": "more fell asleep" if mehr else "more woke up",
                       "zahl": "%.1f%%" % jetzt["dormant_pct"],
                       "satz": "of all KAS has not moved in a year, %.2f%% the week before"
                               % vorher["dormant_pct"], "datum": d % "kaspalytics"})
    if all(jetzt.get(k) and vorher.get(k) for k in ("hashrate", "holders")):
        ph = 100 * (jetzt["hashrate"] / vorher["hashrate"] - 1)
        pa = 100 * (jetzt["holders"] / vorher["holders"] - 1)
        if round(ph, 1) != round(pa, 1):
            fragen.append({"text": "which grew more in the week to %s, hashrate or addresses?" % tag_kurz(s),
                           "frage": "which grew more this week?",
                           "optionen": ["hashrate", "addresses"], "richtig": 0 if ph > pa else 1,
                           "sieger": "%s grew more" % ("hashrate" if ph > pa else "addresses"),
                           "zahl": "%+.1f%%" % (ph if ph > pa else pa),
                           "satz": "%+.1f%% against %+.1f%% for %s" % (
                               max(ph, pa), min(ph, pa), "addresses" if ph > pa else "hashrate"),
                           "datum": d % "kaspa rest api, kaspalytics"})
    if not fragen:
        raise Stopp("keine messfrage fuer die umfrage in der ausgabe %s" % jetzt["week"])
    f = fragen[dt.date.fromisoformat(datum).isocalendar()[1] % len(fragen)]
    return {"art": "poll", "titel": "YOUR CALL", "zahl": "", "einheit": "", "text": f["text"],
            "frage": f["frage"], "optionen": f["optionen"], "richtig": f["richtig"],
            "datum": f["datum"], "quelle_vorlage": "weekly %s" % jetzt["week"],
            "aufloesung": {"frage": f["frage"], "zahl": f["zahl"], "einheit": "",
                           "satz": "%s, %s" % (f["sieger"], f["satz"]), "datum": f["datum"]}}


def zitat_aus_daten(datum, story=None, nod=None):
    """Do. Der staerkste Satz aus dem Erklaerer (data/karussell-story.json),
    ersatzweise die Zahl des Tages, beides nur, wenn es frisch ist."""
    heute = dt.date.fromisoformat(datum)
    st = json_lesen(story or KARUSSELL_STORY)
    if st and st.get("stand"):
        try:
            frisch = (heute - dt.date.fromisoformat(st["stand"])).days <= 10
        except ValueError:
            frisch = False
        mit_zahl = [x for x in st.get("seiten", []) if x.get("zahl") and x.get("datum") and x.get("quelle")]
        if frisch and mit_zahl:
            x = mit_zahl[0]
            return {"art": "zitat", "titel": "THIS WEEK'S EXPLAINER", "zahl": x["zahl"], "einheit": "",
                    "text": x["satz"], "datum": "%s · %s" % (x["datum"], x["quelle"]),
                    "frage": "what should we count next?",
                    "quelle_vorlage": "erklaerer, data/karussell-story.json",
                    "aufloesung": {"frage": "yesterday's explainer", "zahl": x["zahl"], "einheit": "",
                                   "satz": x["satz"], "datum": "%s · %s" % (x["datum"], x["quelle"])}}
    n = json_lesen(nod or NOD)
    if not n or not n.get("value"):
        raise Stopp("kein erklaerer und keine zahl des tages fuer das zitat, bitte data/story-plan.json")
    try:
        ausgabe = dt.datetime.strptime(n["issue"].title(), "%b %d %Y").date()
    except (KeyError, ValueError):
        raise Stopp("zahl des tages ohne lesbares datum")
    if (heute - ausgabe).days > 3 or ausgabe > heute:
        raise Stopp("zahl des tages ist vom %s, zu alt fuer das zitat, bitte data/story-plan.json"
                    % ausgabe.isoformat())
    quelle = {"api.kaspa.org": "kaspa rest api"}.get(n.get("sources", ""), n.get("sources", ""))
    d = "%s \u00b7 %s" % (tag(ausgabe.isoformat()), ("source %s" % quelle) if quelle else SELBST)
    satz = n.get("value_label", "").strip()
    if not satz:
        raise Stopp("zahl des tages ohne satz, bitte data/story-plan.json")
    # die schlagzeile der zahl des tages vergleicht oft mit bitcoin, das
    # bleibt in der story draussen; es steht nur die zahl mit ihrem satz
    return {"art": "zitat", "titel": "NUMBER OF THE WEEK", "zahl": n["value"], "einheit": "",
            "text": satz, "ohne_zeichen": True, "datum": d,
            "frage": "what should we count next?",
            "quelle_vorlage": "zahl des tages %s, kein erklaerer gefunden" % ausgabe.isoformat(),
            "aufloesung": {"frage": "yesterday's number", "zahl": n["value"], "einheit": "",
                           "satz": satz, "datum": d}}


def wahr_aus_entity_x(datum, inflows=None, daily=None):
    """Fr, "nobody counts this". Eine Aussage aus unserer eigenen Zaehlung
    zu Entity X, im Wochentakt wahr oder falsch."""
    ex = json_lesen(inflows or EX_INFLOWS, {}) or {}
    tg = json_lesen(daily or EX_DAILY, {}) or {}
    aussagen = []
    if ex.get("inflow_count") and "coinbase_inflows" in ex and ex.get("generated_at"):
        am = dt.datetime.fromtimestamp(ex["generated_at"], dt.timezone.utc).date().isoformat()
        d = "as of %s · %s" % (tag(am), SELBST)
        n, c = ex["inflow_count"], ex["coinbase_inflows"]
        aussagen.append({"aussage": "entity x got KAS straight from mining", "wahr": c > 0,
                         "zahl": "%d of %s" % (c, ganz(n)),
                         "satz": "inflows came straight from mining", "datum": d})
        boerse = ex.get("kas_by_verdict", {}).get("boerse", 0)
        if ex.get("inflow_kas") and boerse:
            p = 100 * boerse / ex["inflow_kas"]
            aussagen.append({"aussage": "most KAS sent to entity x came from exchange wallets",
                             "wahr": p > 50, "zahl": "%.0f%%" % p,
                             "satz": "of all KAS sent to entity x came from exchange wallets", "datum": d})
        frisch = ex.get("kas_by_verdict", {}).get("frisches wallet", 0)
        if ex.get("inflow_kas") and frisch:
            p = 100 * frisch / ex["inflow_kas"]
            aussagen.append({"aussage": "most KAS sent to entity x came from fresh wallets",
                             "wahr": p > 50, "zahl": "%.0f%%" % p,
                             "satz": "of all KAS sent to entity x came from fresh wallets", "datum": d})
    if tg.get("balance_kas") and tg.get("checked_utc"):
        b = tg["balance_kas"]
        d = "as of %s · source kaspa rest api, address tracked by kaspa pulse" % tag(tg["checked_utc"])
        aussagen.append({"aussage": "one address holds more than 1 billion KAS", "wahr": b > 1e9,
                         "zahl": kompakt(b), "einheit": "KAS",
                         "satz": "sit at the entity x address", "datum": d})
    if not aussagen:
        raise Stopp("keine eigene zaehlung fuer wahr oder falsch, bitte data/story-plan.json")
    a = aussagen[dt.date.fromisoformat(datum).isocalendar()[1] % len(aussagen)]
    return {"art": "wahr", "titel": "NOBODY COUNTS THIS", "zahl": "", "einheit": "",
            "text": a["aussage"] + ".", "frage": "true or false?", "optionen": ["true", "false"],
            "richtig": 0 if a["wahr"] else 1, "datum": a["datum"],
            "newsletter": "weekly kaspa numbers in our newsletter, link below",
            "quelle_vorlage": "entity x, eigene zaehlung",
            "aufloesung": {"frage": a["aussage"], "zahl": "TRUE" if a["wahr"] else "FALSE", "einheit": "",
                           "satz": "%s %s" % (a["zahl"] + (" " + a["einheit"] if a.get("einheit") else ""),
                                              a["satz"]), "datum": a["datum"]}}


VORLAGEN = {"quiz": quiz_aus_weekly, "slider": slider_aus_emission, "poll": poll_aus_weekly,
            "zitat": zitat_aus_daten, "wahr": wahr_aus_entity_x}


# ------------------------------------------------------------ plan

def aus_plan(eintrag, art):
    """Ein Eintrag aus data/story-plan.json. Pflichtfelder je Art, die
    Aufloesung baut sich aus denselben Feldern."""
    e = dict(eintrag)
    pflicht = {"quiz": ("text", "frage", "antworten", "richtig", "loesung", "datum"),
               "slider": ("text", "frage", "emoji", "antwort", "datum"),
               "poll": ("text", "frage", "optionen", "richtig", "loesung", "datum"),
               "zitat": ("text", "datum"),
               "wahr": ("text", "wahr", "loesung", "datum")}[art]
    fehlt = [k for k in pflicht if k not in e or e[k] in ("", None, [])]
    if fehlt:
        raise Stopp("story-plan %s, es fehlt %s" % (art, ", ".join(fehlt)))
    titel = {"quiz": "GUESS THE WEEK", "slider": "KASPA IN REAL LIFE", "poll": "YOUR CALL",
             "zitat": "THIS WEEK'S EXPLAINER", "wahr": "NOBODY COUNTS THIS"}[art]
    s = {"art": art, "titel": e.get("titel", titel).upper(), "text": e["text"], "zahl": e.get("zahl", ""),
         "einheit": e.get("einheit", ""), "datum": e["datum"], "quelle_vorlage": "data/story-plan.json"}
    if art == "quiz":
        richtig = e["richtig"] if isinstance(e["richtig"], int) else e["antworten"].index(e["richtig"])
        s.update(frage=e["frage"], antworten=list(e["antworten"]), richtig=richtig)
        loes = {"zahl": e["antworten"][richtig], "satz": e["loesung"]}
    elif art == "slider":
        s.update(frage=e["frage"], emoji=e["emoji"], antwort=e["antwort"])
        loes = {"zahl": e.get("antwort_zahl", e["antwort"]), "satz": e.get("loesung", e["antwort"])}
    elif art == "poll":
        richtig = e["richtig"] if isinstance(e["richtig"], int) else e["optionen"].index(e["richtig"])
        s.update(frage=e["frage"], optionen=list(e["optionen"]), richtig=richtig)
        loes = {"zahl": e.get("loesung_zahl", e["optionen"][richtig]), "satz": e["loesung"]}
    elif art == "zitat":
        s.update(frage=e.get("frage", "what should we count next?"))
        loes = {"zahl": e.get("zahl", ""), "satz": e["text"]}
    else:
        s.update(frage="true or false?", optionen=["true", "false"], richtig=0 if e["wahr"] else 1,
                 newsletter=e.get("newsletter", "weekly kaspa numbers in our newsletter, link below"))
        loes = {"zahl": "TRUE" if e["wahr"] else "FALSE", "satz": e["loesung"]}
    s["aufloesung"] = {"frage": e.get("frage_kurz", e.get("frage", e["text"])), "zahl": loes["zahl"],
                       "einheit": e.get("loesung_einheit", ""), "satz": loes["satz"],
                       "datum": e.get("loesung_datum", e["datum"])}
    return s


def vorlage(datum, plan=None, quellen=None):
    """Die Story fuer einen Tag Mo bis Fr, aus dem Plan oder den Daten."""
    t = wochentag(datum)
    if t not in ART_JE_TAG:
        return None
    art = ART_JE_TAG[t]
    p = json_lesen(plan or PLAN, {}) or {}
    eintrag = (p.get("wochen", {}).get(montag(datum)) or {}).get(t)
    if eintrag:
        s = aus_plan(eintrag, art)
    else:
        s = VORLAGEN[art](datum, **(quellen or {}).get(art, {}))
    s.update(datum_tag=datum, tag=t)
    return s


def aufloesung(datum, log):
    """Di bis Sa. Die Antwort von gestern aus dem Story-Log."""
    t = wochentag(datum)
    if t not in ("di", "mi", "do", "fr", "sa"):
        return None
    gestern = (dt.date.fromisoformat(datum) - dt.timedelta(days=1)).isoformat()
    e = next((x for x in reversed(log.get("tage", [])) if x.get("datum") == gestern), None)
    if not e or not e.get("aufloesung"):
        return None
    a = e["aufloesung"]
    satz_vor = {"quiz": "the right answer", "slider": "the answer", "poll": "the right call",
                "zitat": "the number behind it", "wahr": "the answer"}.get(e.get("art"), "the answer")
    return {"art": "aufloesung", "titel": "YESTERDAY'S ANSWER", "text": a["frage"], "zahl": a["zahl"],
            "einheit": a.get("einheit", ""), "satz": a["satz"], "vor": satz_vor, "datum": a["datum"],
            "von_art": e.get("art"), "datum_tag": datum, "tag": t}


# ------------------------------------------------------------ wachen

def oeffentliche_texte(s):
    """Alles, was Instagram-Nutzer sehen: Bildtexte und Sticker-Texte."""
    t = [s.get(k) for k in ("titel", "text", "zahl", "einheit", "datum", "frage", "unter",
                            "newsletter", "satz", "antwort") if s.get(k)]
    t += list(s.get("antworten") or []) + list(s.get("optionen") or [])
    return [str(x) for x in t]


def text_pruefen(s):
    import content_wache
    import tagesgrafik as tg
    fehler = []
    texte = oeffentliche_texte(s)
    for t in texte:
        for f in tg.pruefe_eine(t, None, "story"):
            fehler.append("%s in %r" % (f, t[:50]))
        for f in content_wache.text_verstoesse(t):
            fehler.append("%s in %r" % (f, t[:50]))
        m = KURS.search(t)
        if m:
            fehler.append("kursfrage oder kurswort %r in %r" % (m.group(0), t[:50]))
        m = KOEDER.search(t)
        if m:
            fehler.append("koeder %r in %r" % (m.group(0), t[:50]))
    alles = " ".join(texte)
    if re.search(r"\bcounted\b", alles, re.I) and re.search(r"\bsource\b", s.get("datum", "")) \
            and SELBST not in s.get("datum", ""):
        fehler.append("counted bei einer fremden quelle")
    if re.search(r"\d", alles) and not content_wache.DATUM.search(s.get("datum", "")):
        fehler.append("zahl ohne datum in der datumszeile")
    return fehler


def element_pruefen(s):
    fehler = []
    art = s["art"]
    if art == "quiz":
        n = len(s.get("antworten") or [])
        if not 2 <= n <= QUIZ_MAX:
            fehler.append("quiz hat %d optionen, erlaubt 2 bis %d" % (n, QUIZ_MAX))
        if len(set(s["antworten"])) != n:
            fehler.append("quiz hat doppelte antworten")
        if not 0 <= s.get("richtig", -1) < n:
            fehler.append("quiz ohne richtige antwort")
        for a in s["antworten"]:
            if len(a) > POLL_MAX:
                fehler.append("quiz-antwort %r hat %d zeichen, hoechstens %d" % (a, len(a), POLL_MAX))
    if art in ("poll", "wahr"):
        o = s.get("optionen") or []
        if len(o) != 2:
            fehler.append("umfrage braucht genau 2 optionen, hat %d" % len(o))
        for a in o:
            if len(a) > POLL_MAX:
                fehler.append("umfrage-option %r hat %d zeichen, hoechstens %d" % (a, len(a), POLL_MAX))
    if art == "slider" and not s.get("emoji"):
        fehler.append("slider ohne emoji")
    return fehler


def zahlen_der_story(s):
    aus = [s.get("zahl")]
    if s.get("aufloesung"):
        aus.append(s["aufloesung"].get("zahl"))
    aus.append(s.get("antwort"))
    return [z for z in (zahl_kern(x) for x in aus if x) if z is not None]


def feed_pruefen(s, feed_zahl):
    """Die Zahl der Story ist nie die Zahl des heutigen Feed-Posts."""
    f = zahl_kern(feed_zahl)
    if f is None:
        return []
    if f in zahlen_der_story(s):
        return ["die story-zahl ist die zahl des heutigen feed-posts (%s)" % feed_zahl]
    return []


def pruefen(s, feed_zahl=None):
    fehler = text_pruefen(s) + element_pruefen(s) + feed_pruefen(s, feed_zahl)
    if fehler:
        raise Stopp("wache %s %s, %s" % (s.get("tag", ""), s["art"], "; ".join(fehler)))


def feed_zahl_heute(datum, ziel=None):
    """Die Zahl des heutigen Feed-Posts. Um 07:45 ist er noch nicht gepostet
    (09:30), die Zahl steht aber im Artefakt der Tagesgrafik von 07:30.
    (zahl, herkunft) oder (None, grund)."""
    log = json_lesen(IG_LOG, {"posts": []}) or {"posts": []}
    for p in reversed(log.get("posts", [])):
        if p.get("datum") == datum and p.get("zahl"):
            return p["zahl"], "instagram-log"
    g = json_lesen(GRAFIK_LOG, {"laeufe": []}) or {"laeufe": []}
    eintrag = next((e for e in reversed(g.get("laeufe", [])) if e.get("datum") == datum
                    and e.get("messzeit_utc")), None)
    if not eintrag:
        return None, "heute noch keine tagesgrafik im log"
    if not os.environ.get("GITHUB_TOKEN"):
        return None, "kein GITHUB_TOKEN fuer das artefakt der tagesgrafik"
    try:
        import instagram
        _, cap = instagram.artefakt(eintrag, ziel or tempfile.mkdtemp())
        ig = json.loads(Path(cap).read_text(encoding="utf-8"))
        return (ig.get("zahl"), "artefakt der tagesgrafik") if ig.get("zahl") else (None, "artefakt ohne zahl")
    except Exception as exc:  # noqa: BLE001, die vorlage kommt trotzdem, mit hinweis
        return None, "artefakt nicht lesbar, %s" % str(exc)[:120]


# ------------------------------------------------------------ html

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;background:%(grund)s;position:relative;overflow:hidden;color:%(text)s;
  font-family:'IBM Plex Sans',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.feld{position:absolute;left:60px;top:290px;width:840px;height:1210px;display:flex;flex-direction:column}
.feld>*{flex-shrink:0}
.kopf{display:flex;justify-content:space-between;align-items:baseline}
.tag{font-family:'IBM Plex Mono',monospace;font-size:40px;color:%(text2)s;white-space:nowrap}
.puls{display:block;width:230px;height:48px;margin:14px 0 0 -4px}
.titel{font-family:'Archivo',sans-serif;font-weight:800;font-size:84px;line-height:0.98;letter-spacing:-1px;
  margin-top:26px;color:%(akzent)s}
.zahl{font-family:'Archivo',sans-serif;font-weight:900;font-size:240px;line-height:0.86;letter-spacing:-6px;
  white-space:nowrap;margin-top:36px}
.zahl .einheit{display:block;font-size:64px;font-weight:800;letter-spacing:0;line-height:1;margin-top:22px}
.unter{font-size:46px;line-height:1.18;color:%(text2)s;margin-top:18px}
.text{font-weight:500;font-size:58px;line-height:1.16;margin-top:32px}
.zitat{font-family:'Archivo',sans-serif;font-weight:800;font-size:64px;line-height:1.08;margin-top:34px}
.vor{font-family:'IBM Plex Mono',monospace;font-size:40px;color:%(text2)s;margin-top:44px;text-transform:uppercase;
  letter-spacing:1px}
.satz{font-weight:500;font-size:46px;line-height:1.2;margin-top:24px;color:%(akzent)s}
.luft{flex:1 1 auto;min-height:40px}
.element{position:relative;border:5px dashed %(akzent)s;border-radius:34px;flex:0 0 auto;margin-bottom:28px}
.element .marke{position:absolute;left:28px;top:-30px;background:%(grund)s;padding:0 14px;
  font-family:'IBM Plex Mono',monospace;font-size:40px;font-weight:500;color:%(akzent)s;white-space:nowrap}
.element .hin{position:absolute;left:0;right:0;bottom:22px;text-align:center;font-family:'IBM Plex Mono',monospace;
  font-size:40px;color:%(text2)s}
.news{font-weight:600;font-size:42px;line-height:1.18;margin-bottom:42px}
.datum{font-family:'IBM Plex Mono',monospace;font-size:40px;line-height:1.25;color:%(text2)s;letter-spacing:-0.5px}
"""

# hoehe der freien flaeche je instagram-element, so gross wie der sticker
ELEMENT = {"quiz": (440, "quiz here"), "slider": (220, "slider here"), "poll": (250, "poll here"),
           "frage": (300, "question box here"), "link": (110, "link here")}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def elemente(s):
    return {"quiz": ["quiz"], "slider": ["slider"], "poll": ["poll"], "zitat": ["frage"],
            "wahr": ["poll", "link"], "aufloesung": []}[s["art"]]


def seite_html(s, look):
    import look_takt
    import tagesgrafik as tg
    import wortmarke
    lk = look_takt.look(look)
    css = (look_takt.schriften_css()
           + CSS % {"grund": lk["grund"], "text": lk["text"], "text2": lk["text2"], "akzent": lk["akzent"]}
           + wortmarke.css(groesse=44, sperrung=5, look=look))
    d = dt.date.fromisoformat(s["datum_tag"])
    kopf = ("<div class='kopf'>%s<span class='tag'>%s %d %s</span></div>"
            "<svg class='puls' viewBox='0 0 230 48'><path d='%s' fill='none' stroke='%s' stroke-width='4' "
            "stroke-linejoin='round' stroke-linecap='round'/></svg>"
            % (wortmarke.html(), WOCHENTAG_EN[d.weekday()], d.day, MONATE[d.month - 1].upper(),
               tg.PULS, lk["markierung"]))
    teile = [kopf, "<div class='titel' data-rolle='titel'>%s</div>" % esc(s["titel"])]
    if s.get("zahl"):
        teile.append("<div class='zahl' data-rolle='zahl'>%s%s</div>" % (
            esc(s["zahl"]), "<span class='einheit' data-rolle='einheit'>%s</span>" % esc(s["einheit"])
            if s.get("einheit") else ""))
    if s.get("unter"):
        teile.append("<div class='unter'>%s</div>" % esc(s["unter"]))
    if s["art"] == "zitat":
        teile.append("<div class='zitat'>%s</div>" % esc(s["text"]) if s.get("ohne_zeichen")
                     else "<div class='zitat'>\u201c%s\u201d</div>" % esc(s["text"]))
    elif s["art"] == "aufloesung":
        teile.append("<div class='text' style='font-size:46px'>%s</div>" % esc(s["text"]))
        teile.append("<div class='vor'>%s</div>" % esc(s["vor"]))
        if s.get("zahl"):
            z = teile.pop(2)
            teile.append(z.replace("margin-top:44px", ""))
        teile.append("<div class='satz'>%s</div>" % esc(s["satz"]))
    else:
        teile.append("<div class='text'%s>%s</div>" % (" style='font-size:52px'" if s["art"] == "wahr" else "",
                                                       esc(s["text"])))
    teile.append("<div class='luft'></div>")
    if s.get("newsletter"):
        teile.append("<div class='news'>%s</div>" % esc(s["newsletter"]))
    for e in elemente(s):
        hoehe, marke = ELEMENT[e]
        hin = {"slider": "", "link": LINK}.get(e, "")
        teile.append("<div class='element' data-element='%s' style='height:%dpx'><span class='marke'>%s</span>%s</div>"
                     % (e, hoehe, esc(marke), "<span class='hin'>%s</span>" % esc(hin) if hin else ""))
    teile.append("<div class='datum'>%s</div>" % esc(s["datum"]))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'><div class='feld'>%s</div></body></html>" % (css, look, "".join(teile)))


PASSEN_JS = """([x0, y0, x1, y1]) => {
  const z = document.querySelector('.zahl');
  if (z) { let g = 240; while (z.scrollWidth > 840 && g > 220) { g -= 4; z.style.fontSize = g + 'px'; } }
  const feld = document.querySelector('.feld');
  const aus = [];
  if (z && z.scrollWidth > 840) aus.push('zahl ist ' + z.scrollWidth + ' px breit, hoechstens 840');
  if (feld.scrollHeight > feld.clientHeight + 1) aus.push('inhalt ist ' + (feld.scrollHeight - feld.clientHeight) + ' px zu hoch, text kuerzen');
  for (const e of document.querySelectorAll('[data-element]')) {
    const r = e.getBoundingClientRect();
    if (r.left < x0 - 1 || r.right > x1 + 1 || r.top < y0 - 1 || r.bottom > y1 + 1)
      aus.push('element ' + e.dataset.element + ' liegt ausserhalb der sicheren flaeche, bei '
               + Math.round(r.left) + '..' + Math.round(r.right) + ' x ' + Math.round(r.top) + '..' + Math.round(r.bottom));
  }
  const mk = document.querySelector('.luft');
  if (mk && mk.getBoundingClientRect().height < 39) aus.push('kein luft zwischen text und element, text kuerzen');
  return aus;
}"""


def rendern(s, look, png, browser, motiv=None):
    """Rendert eine Story, prueft Elemente und Flaeche, dann die content_wache
    im Profil "story". Danach die kleine Vorschau in 390 px."""
    import content_wache
    png = Path(png)
    html = png.with_suffix(".html")
    import hintergrund
    seite = seite_html(s, look)
    if motiv:
        seite = hintergrund.setzen(seite, motiv, look, W, H)
    html.write_text(seite, encoding="utf-8")
    pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    try:
        pg.goto(html.resolve().as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        hintergrund.warten(pg)
        fehler = pg.evaluate(PASSEN_JS, [X0, Y0, X1, Y1])
        if fehler:
            raise Stopp("layout %s, %s" % (png.name, "; ".join(fehler)))
        pg.screenshot(path=str(png))
        verstoesse = content_wache.pruefe_seite(pg, "story", png)
        if verstoesse:
            raise Stopp("wache %s, %s" % (png.name, "; ".join(verstoesse)))
    finally:
        pg.close()
    html.unlink()
    return png


def vorschau(pngs, ziel, browser, breite=VORSCHAU):
    """Die Bilder nebeneinander in 390 px, so wie auf dem Handy."""
    import base64
    hoehe = round(breite * H / W)
    bilder = "".join("<img src='data:image/png;base64,%s' style='width:%dpx;height:%dpx;margin:0 12px 0 0'>"
                     % (base64.b64encode(Path(p).read_bytes()).decode(), breite, hoehe) for p in pngs)
    pg = browser.new_page(viewport={"width": (breite + 12) * len(pngs), "height": hoehe}, device_scale_factor=1)
    try:
        pg.set_content("<html><body style='margin:0;background:#000;display:flex'>%s</body></html>" % bilder)
        pg.wait_for_timeout(100)
        pg.screenshot(path=str(ziel))
    finally:
        pg.close()
    return Path(ziel)


# ------------------------------------------------------------ anleitung, senden

def tag_de(datum):
    d = dt.date.fromisoformat(datum)
    return "%s %02d.%02d." % (["MO", "DI", "MI", "DO", "FR", "SA", "SO"][d.weekday()], d.day, d.month)


def anleitung(s):
    """Der Block zum Kopieren. Deutsch fuer Ben, Englisch was auf Instagram steht."""
    z = []
    musik = MUSIK[saat(s["datum_tag"], "musik") % len(MUSIK)]
    if s["art"] == "aufloesung":
        z += ["%s AUFLOESUNG, frueh posten (vor 10:00)" % tag_de(s["datum_tag"]),
              "element    keins, nur das bild",
              "frage      %s" % s["text"],
              "antwort    %s%s" % (s["zahl"], (" " + s["einheit"]) if s.get("einheit") else ""),
              "satz       %s" % s["satz"]]
    else:
        name = {"quiz": "quiz", "slider": "emoji-slider", "poll": "umfrage", "zitat": "fragebox",
                "wahr": "umfrage (true/false) und link"}[s["art"]]
        z.append("%s %s, posten %s" % (tag_de(s["datum_tag"]), s["art"].upper(), POSTEN))
        z.append("element    %s" % name)
        z.append("frage      %s" % s["frage"])
        if s["art"] == "quiz":
            for i, a in enumerate(s["antworten"]):
                z.append("antwort %s  %s" % ("abcd"[i], a))
            z.append("richtig    %s, %s" % ("abcd"[s["richtig"]], s["antworten"][s["richtig"]]))
        elif s["art"] == "slider":
            z.append("emoji      %s" % s["emoji"])
            z.append("richtig    %s (aufloesung morgen frueh)" % s["antwort"])
        elif s["art"] in ("poll", "wahr"):
            for i, a in enumerate(s["optionen"]):
                z.append("option %d   %s" % (i + 1, a))
            z.append("richtig    %s (aufloesung morgen frueh)" % s["optionen"][s["richtig"]])
        else:
            z.append("richtig    keine, offene frage")
        platz = "sticker auf den gestrichelten rahmen, rahmen ganz bedecken"
        if s["art"] == "wahr":
            platz += ", link-sticker auf den unteren rahmen"
        z.append("platz      %s" % platz)
        z.append("inhalt     %s" % s.get("quelle_vorlage", ""))
    z.append("musik      ruhig, elektronisch, ohne gesang, suche \"%s\"" % musik)
    z.append("link       %s%s" % (LINK, "" if s["art"] == "wahr" else " (link-sticker optional)"))
    return "\n".join(z)


def nachricht(stories, feed_hinweis=""):
    teile = ["STORY-VORLAGE %s, nicht automatisch gepostet, Ben postet von hand." % tag_de(stories[0]["datum_tag"])]
    for s in stories:
        teile.append("```\n%s\n```" % anleitung(s).replace("`", "'"))
    teile.append("posten 17:30" if any(s["art"] != "aufloesung" for s in stories) else "heute keine neue vorlage")
    if feed_hinweis:
        teile.append(feed_hinweis)
    return "\n".join(teile)[:1990]


def ops_senden(hook, inhalt, bilder):
    grenze = "----st" + uuid.uuid4().hex
    teile = [("--%s\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json"
              "\r\n\r\n" % grenze).encode()
             + json.dumps({"content": inhalt, "allowed_mentions": {"parse": []}}).encode() + b"\r\n"]
    for i, p in enumerate(bilder[:10]):
        teile.append(("--%s\r\nContent-Disposition: form-data; name=\"files[%d]\"; filename=\"%s\"\r\n"
                      "Content-Type: image/png\r\n\r\n" % (grenze, i, Path(p).name)).encode()
                     + Path(p).read_bytes() + b"\r\n")
    body = b"".join(teile) + ("--%s--\r\n" % grenze).encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % grenze, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        print("story-vorlage an ops geschickt, http %s" % r.status)


def log_merken(log, s):
    eintrag = {"datum": s["datum_tag"], "tag": s["tag"], "art": s["art"], "frage": s.get("frage", ""),
               "richtig": s.get("richtig"), "aufloesung": s["aufloesung"],
               "quelle_vorlage": s.get("quelle_vorlage", "")}
    for k in ("antworten", "optionen", "antwort", "emoji"):
        if s.get(k):
            eintrag[k] = s[k]
    tage = [x for x in log.get("tage", []) if x.get("datum") != s["datum_tag"]] + [eintrag]
    log["tage"] = sorted(tage, key=lambda x: x["datum"])[-BEHALTEN:]
    return log


# ------------------------------------------------------------ bauen

def bauen(datum, out, log=None, plan=None, quellen=None, look=None, feed_zahl=None, browser=None):
    """Aufloesung (di bis sa) und Vorlage (mo bis fr) fuer einen Tag. Gibt
    (stories, pngs) zurueck."""
    import look_takt
    log = log if log is not None else (json_lesen(LOG, {"tage": []}) or {"tage": []})
    stories = [x for x in (aufloesung(datum, log), vorlage(datum, plan, quellen)) if x]
    for s in stories:
        pruefen(s, feed_zahl)
    import hintergrund
    sp = look_takt.lesen()
    if look is None:
        look = look_takt.faellig(sp, "story", "instagram", datum)[1]
    # das motiv der story ruckt mit dem datum, nie das des feed-posts vom tag
    motiv = hintergrund.motiv_story(datum, look_takt.raster_motiv(sp, "tagesgrafik", datum))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pngs = []

    def alle(b):
        for s in stories:
            name = "story-%s-%s-%s.png" % (datum, "aufloesung" if s["art"] == "aufloesung" else s["art"], look)
            pngs.append(rendern(s, look, out / name, b, motiv))
    if browser is None:
        import tagesgrafik as tg
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = tg.chromium_start(p)
            try:
                alle(b)
                if pngs:
                    vorschau(pngs, out / ("story-%s-vorschau-%d.png" % (datum, VORSCHAU)), b)
            finally:
                b.close()
    else:
        alle(browser)
    return stories, pngs, look


def tageslauf(datum, out, senden=False):
    import look_takt
    if not wochentag(datum):
        print("sonntag, keine story")
        return 0
    zahl, herkunft = feed_zahl_heute(datum, Path(out) / "feed")
    hinweis = ("feed-zahl heute %s (%s), die story nimmt eine andere" % (zahl, herkunft) if zahl
               else "feed-zahl heute unbekannt (%s), bitte gegen den feed-post von 09:30 pruefen" % herkunft)
    print(hinweis)
    log = json_lesen(LOG, {"tage": []}) or {"tage": []}
    stories, pngs, look = bauen(datum, out, log=log, feed_zahl=zahl)
    if not stories:
        print("nichts zu bauen fuer %s" % datum)
        return 0
    inhalt = nachricht(stories, hinweis)
    Path(out, "story-%s-anleitung.txt" % datum).write_text(inhalt + "\n", encoding="utf-8")
    print(inhalt)
    if senden:
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise Stopp("kein DISCORD_WEBHOOK_OPS, nichts geschickt")
        ops_senden(hook, inhalt, pngs)
        for s in stories:
            if s["art"] != "aufloesung":
                log_merken(log, s)
        Path(LOG).write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        sp = look_takt.lesen()
        look_takt.merken(sp, "story", "instagram", datum)
        look_takt.schreiben(sp)
    return 0


# ------------------------------------------------------------ selbsttest

PROBE_HISTORY = [
    {"week": "2026-10-12", "hashrate": 374.6, "emission": 1779988.8, "holders": 801210.0, "dormant_pct": 51.12,
     "mined_pct": 96.70},
    {"week": "2026-10-19", "hashrate": 383.01, "emission": 1779988.811045, "holders": 803742.0,
     "dormant_pct": 50.98, "mined_pct": 96.727944},
]


def selbsttest():
    import look_takt
    schlecht = 0

    def ok(name, bed, *mehr):
        nonlocal schlecht
        print("%s %s%s" % ("ok  " if bed else "FEHL", name, (" " + " ".join(str(m) for m in mehr))
                           if mehr and not bed else ""))
        if not bed:
            schlecht += 1

    tmp = Path(tempfile.mkdtemp(prefix="story-"))
    hist = tmp / "history.json"
    hist.write_text(json.dumps(PROBE_HISTORY), encoding="utf-8")
    nod = tmp / "nod.json"
    nod.write_text(json.dumps({"issue": "OCT 29 2026", "value": "6",
                               "value_label": "days until the next kaspa reward cut",
                               "headline": "bitcoin waits *535 days*.\nkaspa cuts 17 times before then.",
                               "sources": "api.kaspa.org"}), encoding="utf-8")
    leer = tmp / "leer.json"
    leer.write_text("{}", encoding="utf-8")
    quellen = {"quiz": {"history": hist}, "slider": {"history": hist}, "poll": {"history": hist},
               "zitat": {"story": leer, "nod": nod}, "wahr": {}}
    plan_leer = tmp / "plan.json"
    plan_leer.write_text(json.dumps({"wochen": {}}), encoding="utf-8")

    # reine helfer
    ok("zahl_kern liest kurz und lang gleich", zahl_kern("574M") == zahl_kern("574 million")
       == zahl_kern("574,000,000"))
    ok("zahl_kern trennt verschiedene zahlen", zahl_kern("574M") != zahl_kern("57.4M"))
    ok("wochentag mo bis sa, sonntag leer", [wochentag("2026-10-%02d" % d) for d in range(26, 32)]
       + [wochentag("2026-11-01")] == ["mo", "di", "mi", "do", "fr", "sa", ""])

    # eine ganze woche mo bis fr plus aufloesungen, aus den vorlagen
    woche = ["2026-10-%02d" % d for d in range(26, 31)] + ["2026-10-31"]
    log = {"tage": []}
    alle = []
    for d in woche:
        auf = aufloesung(d, log)
        v = vorlage(d, plan_leer, quellen)
        for s in (auf, v):
            if s:
                try:
                    pruefen(s)
                    gut = True
                except Stopp as exc:
                    gut = str(exc)
                ok("%s %s haelt alle wachen" % (d, s["art"]), gut is True, gut)
                alle.append(s)
        if v:
            log_merken(log, v)
    arten = [s["art"] for s in alle]
    ok("mo bis fr je eine vorlage in der richtigen art",
       [s["art"] for s in alle if s["art"] != "aufloesung"] == ["quiz", "slider", "poll", "zitat", "wahr"],
       arten)
    ok("di bis sa je eine aufloesung", arten.count("aufloesung") == 5, arten)
    q = alle[0]
    ok("quiz hat vier verschiedene antworten und eine richtige",
       len(set(q["antworten"])) == 4 and q["antworten"][q["richtig"]] == q["aufloesung"]["zahl"],
       q["antworten"])
    ok("aufloesung am dienstag nennt die richtige quiz-antwort",
       alle[1]["art"] == "aufloesung" and alle[1]["zahl"] == q["aufloesung"]["zahl"])
    ok("samstag nur aufloesung, keine vorlage", vorlage("2026-10-31", plan_leer, quellen) is None)
    ok("montag ohne aufloesung", aufloesung("2026-10-26", log) is None)
    ok("zitat faellt ohne erklaerer auf die zahl des tages zurueck",
       next(s for s in alle if s["art"] == "zitat")["quelle_vorlage"].startswith("zahl des tages"))
    ok("anleitung nennt element, frage, richtig, platz, musik und link",
       all(all(k in anleitung(s) for k in ("element", "frage", "musik", "link"))
           for s in alle) and "richtig" in anleitung(q) and "platz" in anleitung(q))
    ok("musik ruhig, elektronisch, ohne gesang", "ruhig, elektronisch, ohne gesang" in anleitung(q))
    n = nachricht([alle[1], alle[2]], "feed-zahl heute 574M")
    ok("nachricht mit zwei bloecken und posten 17:30", n.count("```") == 4 and "posten 17:30" in n
       and len(n) <= 1990, len(n))

    # wachen
    def stoppt(s, wort):
        try:
            pruefen(s)
            return False
        except Stopp as exc:
            return wort in str(exc)
    p = dict(alle[3]) if alle[3]["art"] == "poll" else next(s for s in alle if s["art"] == "poll")
    ok("umfrage-option ueber 24 zeichen stoppt",
       stoppt(dict(p, optionen=["hashrate grew more than addresses", "no"]), "hoechstens 24"))
    ok("quiz mit fuenf optionen stoppt",
       stoppt(dict(q, antworten=q["antworten"] + ["+50.0%"]), "erlaubt 2 bis 4"))
    ok("kursfrage stoppt", stoppt(dict(p, frage="will the kaspa price go up?"), "kurs"))
    ok("dollarzeichen stoppt", stoppt(dict(p, text="kaspa at $1 this week?"), "kurs"))
    ok("koeder stoppt", stoppt(dict(p, text="giveaway for the right answer in the week to 17 oct"), "koeder"))
    ok("echtzeitwort stoppt", stoppt(dict(p, text="hashrate right now, up or down?"), "echtzeit"))
    ok("percent stoppt", stoppt(dict(p, text="up 5 percent in the week to 17 oct?"), "percent"))
    ok("doppelpunkt stoppt", stoppt(dict(p, text="your call: up or down in the week to 17 oct?"), "doppelpunkt"))
    ok("gedankenstrich stoppt", stoppt(dict(p, text="up or down — week to 17 oct?"), "gedankenstrich"))
    ok("zahl ohne datum stoppt", stoppt(dict(p, datum="source kaspa rest api"), "datum"))
    ok("counted bei fremder quelle stoppt",
       stoppt(dict(p, text="counted 5 blocks in the week to 17 oct", datum="17 oct 2026 · source x"),
              "counted"))
    sl = next(s for s in alle if s["art"] == "slider")
    ok("slider ohne emoji stoppt", stoppt(dict(sl, emoji=""), "emoji"))
    ok("story-zahl gleich feed-zahl stoppt", stoppt(sl, "x") is False
       and feed_pruefen(sl, sl["zahl"]) != [] and feed_pruefen(sl, "574M") == [])
    ok("feed-zahl in anderer schreibweise stoppt auch",
       feed_pruefen(dict(sl, zahl="1.78M"), "1,780,000") != [])

    # plan schlaegt vorlage
    plan = tmp / "plan-voll.json"
    plan.write_text(json.dumps({"wochen": {"2026-10-26": {"mi": {
        "text": "which moved more in the week to 24 oct, blocks or addresses?",
        "frage": "which moved more this week?", "optionen": ["blocks", "addresses"], "richtig": 1,
        "loesung": "addresses, up 0.3% against blocks", "loesung_zahl": "+0.3%",
        "datum": "week to 24 oct 2026 · source kaspalytics"}}}}), encoding="utf-8")
    sp = vorlage("2026-10-28", plan, quellen)
    ok("eintrag im story-plan schlaegt die vorlage",
       sp["quelle_vorlage"] == "data/story-plan.json" and sp["optionen"] == ["blocks", "addresses"])
    ok("plan-eintrag ohne pflichtfeld stoppt", _stoppt_plan(tmp))
    echt = json_lesen(PLAN)
    ok("data/story-plan.json ist lesbar und hat wochen", isinstance(echt, dict) and "wochen" in echt)

    # rendern: alle sechs tage, drei looks fuer die vorlagen, wache und flaeche
    try:
        import tagesgrafik as tg
        from playwright.sync_api import sync_playwright
    except ImportError:
        ok("playwright fuer den bildtest", False)
        print("%d fehler" % schlecht)
        return 1
    out = tmp / "bilder"
    out.mkdir()
    with sync_playwright() as pw:
        b = tg.chromium_start(pw)
        try:
            for s in alle:
                for lk in ("dunkel", "hell", "teal"):
                    png = out / ("story-%s-%s-%s.png" % (s["datum_tag"], s["art"], lk))
                    try:
                        rendern(s, lk, png, b)
                        gut = True
                    except Stopp as exc:
                        gut = str(exc)
                    ok("%s %s %s gerendert und von der wache gemessen" % (s["datum_tag"], s["art"], lk),
                       gut is True and png.exists(), gut)
            # jede variante der festen vorlagen, fuenf wochen hintereinander
            # decken jeden rest im wochentakt ab (3 quiz, 5 alltag, 3 umfragen, 4 aussagen)
            for k in range(1, 6):
                for i in range(5):
                    d = (dt.date(2026, 10, 26) + dt.timedelta(days=7 * k + i)).isoformat()
                    if wochentag(d) == "do":
                        z = json.loads(nod.read_text(encoding="utf-8"))
                        z["issue"] = dt.date.fromisoformat(d).strftime("%b %d %Y").upper()
                        nod.write_text(json.dumps(z), encoding="utf-8")
                    v = vorlage(d, plan_leer, quellen)
                    for s in (v, aufloesung((dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat(),
                                            log_merken({"tage": []}, v))):
                        try:
                            pruefen(s)
                            rendern(s, "dunkel", out / ("variante-%s-%s.png" % (d, s["art"])), b)
                            gut = True
                        except Stopp as exc:
                            gut = str(exc)
                        ok("variante %s %s" % (d, s["art"]), gut is True, gut)
            # element ausserhalb der sicheren flaeche stoppt
            schief = dict(q, text=q["text"] + " " + "and more words that push the frame down. " * 6)
            try:
                rendern(schief, "dunkel", out / "schief.png", b)
                ok("zu langer text stoppt statt das element zu verschieben", False)
            except Stopp as exc:
                ok("zu langer text stoppt statt das element zu verschieben", "zu hoch" in str(exc)
                   or "ausserhalb" in str(exc) or "luft" in str(exc), exc)
            alt = ELEMENT["quiz"]
            ELEMENT["quiz"] = (1300, "quiz here")
            try:
                rendern(q, "dunkel", out / "riesig.png", b)
                ok("element ausserhalb der sicheren flaeche stoppt", False)
            except Stopp as exc:
                ok("element ausserhalb der sicheren flaeche stoppt", True)
            finally:
                ELEMENT["quiz"] = alt
            v = vorschau(sorted(out.glob("story-*-dunkel.png"))[:3], out / "vorschau.png", b)
            ok("vorschau in 390 px", v.exists())
        finally:
            b.close()
    ok("look-takt kennt die serie story", look_takt.faellig({"kanaele": {}}, "story", "instagram",
                                                            "2026-10-26")[1] in look_takt.LOOKS)
    print("bilder in %s" % out)
    print("%d fehler" % schlecht)
    return 1 if schlecht else 0


def _stoppt_plan(tmp):
    plan = tmp / "plan-kaputt.json"
    plan.write_text(json.dumps({"wochen": {"2026-10-26": {"mo": {"text": "nur ein text"}}}}), encoding="utf-8")
    try:
        vorlage("2026-10-26", plan)
        return False
    except Stopp as exc:
        return "es fehlt" in str(exc)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum", default="", help="JJJJ-MM-TT, leer = heute in berlin")
    ap.add_argument("--woche", default="", help="montag JJJJ-MM-TT, baut mo bis sa ohne senden")
    ap.add_argument("--out", default="graphics/story")
    ap.add_argument("--senden", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    try:
        if a.woche:
            log = {"tage": []}
            for i in range(6):
                d = (dt.date.fromisoformat(a.woche) + dt.timedelta(days=i)).isoformat()
                stories, pngs, _ = bauen(d, a.out, log=log)
                for s in stories:
                    if s["art"] != "aufloesung":
                        log_merken(log, s)
                print(nachricht(stories))
            return 0
        if a.datum:
            datum = a.datum
        else:
            from zoneinfo import ZoneInfo
            datum = dt.datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
        return tageslauf(datum, a.out, a.senden)
    except Stopp as exc:
        print("STOPP %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
