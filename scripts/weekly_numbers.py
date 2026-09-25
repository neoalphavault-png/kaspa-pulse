#!/usr/bin/env python3
"""
kaspa pulse - weekly numbers bot
--------------------------------

Baut den Montags-Post fuer #weekly-numbers.

Was der Bot SELBST holt (8 Zeilen):
  hashrate, block reward + naechster Cut, emission, tvl gesamt,
  kasplex/igra split, dex volume, chain fees, prozent gemined

Was von Hand kommt (eine Sache):
  "the read" in data/week-input.json. Sonst nichts mehr.

DER WEG DAHIN, 21. BIS 23.09.2026
Bis zum 21.09. standen fuenf Zahlen von Hand in der Eingabedatei, jede aus
einem Diagramm abgelesen und als Screenshot geschickt. Am 22.09. fiel
holders weg: der uebernommene Wert 792098 stand exakt in der
Kaspalytics-Reihe address/count/meaningful-balance, am 06.09. Am 23.09.
fielen die restlichen vier, nachdem jede gegen den Handwert derselben
Woche gestellt worden war (Lauf 35752265732):

    active_addr    hand 7760          bot 7791          +0,40%
    dormant_pct    hand 50,54         bot 50,59         +0,10%
    exchange_kas   hand 3.790.000.000 bot 3.791.425.244 +0,04%
    tps            hand 2,76          bot 1,47          -46,74%

Die ersten drei sind dieselbe Zahl, einmal abgelesen und einmal gelesen.
Bei exchange_kas ist die Botzahl sogar genauer, der Handwert war der
gerundete Tooltip. Bei dormant_pct wurde zusaetzlich geprueft, ob die
hodl-waves-Seite aus dem Hinweis dasselbe misst wie supply/inactive: die
Summe der Reihen ab 1y ergab 50,57 gegen 50,59, also dieselbe Zahl im
Rahmen der Rundung.

tps ist der Ausreisser und kein Lesefehler. Die Korrektur vom 16.09.
(Wochenmittel, nur Standard) steckte seitdem im Bot, aber nicht im Post,
weil der Handwert weiter nach der alten Definition eingetragen wurde. Mit
der Umstellung wird die Korrektur zum ersten Mal sichtbar, und die Zahl
faellt einmalig um rund die Haelfte. Das steht in data/weekly-notes.md.

Jedes dieser Felder bleibt ueber override von Hand setzbar.

Und "the read" bleibt von Hand geschrieben. Das ist Absicht, das ist der
einzige Teil des Posts der uns von einem Datenfeed unterscheidet.

Aufrufe
  python3 scripts/weekly_numbers.py             normal, postet
  DRY_RUN=1 python3 scripts/weekly_numbers.py   rechnet und druckt, postet nicht
  FORCE=1 ...                                   ueberstimmt Sprungbremse und Dublette
  SHOW_USD=1 ...                                haengt Dollarwerte an zwei Zeilen
  python3 scripts/weekly_numbers.py --selftest  laeuft ohne Netz gegen feste Werte
"""

import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kaspalytics  # noqa: E402
import telegram_post  # noqa: E402
import utm  # noqa: E402

UA = "kaspa-pulse-weekly/1.0 (+https://kaspapulse.com)"
TIMEOUT = 20
RETRIES = 3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# WN_INPUT und WN_HEUTE gibt es nur fuer Trockenlaeufe (quellen_probe.py
# montag): eine andere Eingabedatei und ein simuliertes Datum. Im
# Workflow ist keins von beiden gesetzt.
INPUT_PATH = os.environ.get("WN_INPUT") or os.path.join(ROOT, "data", "week-input.json")
HISTORY_PATH = os.path.join(ROOT, "data", "weekly-history.json")

# --- Reward-Anker, identisch zu reward_cut_alert v3 -------------------------
ANCHOR_TS = 1783280744
ANCHOR_REWARD = 2.44997148
STEP = (365.25 / 12) * 86400
R = 0.5 ** (1 / 12)
BPS = 10
DAY = 86400

# --- Ausgabennummer --------------------------------------------------------
ISSUE_ANCHOR_WEEK = "2026-08-03"
ISSUE_ANCHOR_NUM = 4

# Welche Definition von tps in einer History-Zeile steckt. Seit dem
# 16.09.2026 ist tps das Wochenmittel nur der Standard-Transaktionen, davor
# war es ein einzelner Tag mit Coinbase (data/weekly-notes.md). Zeilen ohne
# dieses Feld sind nach der alten Definition gemessen. Einen Vergleich gibt
# es nur zwischen zwei Zeilen derselben Definition, sonst stuende im Post
# "down 48 percent", obwohl nur die Zaehlweise gewechselt hat.
TPS_DEF = "standard_7d"

# Unter diesem Prozentwert heisst eine Veraenderung "unchanged"
FLAT_PCT = 1.0

# Richtung: +1 heisst hoch ist gut, -1 heisst runter ist gut, 0 heisst neutral.
# Steht bewusst als Tabelle da. Das Vorzeichen allein sagt NICHT ob eine Zahl
# gut ist. Boersenbestand runter ist gruen, TVL runter ist rot.
DIRECTION = {
    "hashrate": +1,
    "tps": +1,
    "active_addr": +1,
    "holders": +1,
    "tvl_total": +1,
    "dex_vol": +1,
    "chain_fees": +1,
    "exchange_kas": -1,
    "dormant_pct": 0,
    "mined_pct": 0,
    "block_reward": 0,
    "emission": 0,
}

# Welche Zeilen im Post eine Wochenveraenderung tragen. Entspricht genau dem
# Post vom 03.08. Wer mehr will, setzt hier einen Schluessel auf True.
SHOW_DELTA = {
    "hashrate": True,
    "tps": True,
    "tvl_total": True,
    "dex_vol": True,
    "dormant_pct": True,
    "exchange_kas": True,
    "active_addr": False,
    "holders": False,
    "chain_fees": False,
    "mined_pct": False,
}

# Bot-Regel 10: um jeden Wert ein Fenster. Lieber kein Post als ein falscher.
PLAUSIBLE = {
    "hashrate": (10.0, 10000.0),        # PH/s
    "block_reward": (0.0001, 500.0),    # KAS
    "mined_pct": (90.0, 100.0),
    "tvl_kasplex": (0.0, 5e9),
    "tvl_igra": (0.0, 5e9),
    "tvl_total": (1.0, 1e10),
    "dex_vol": (0.0, 1e10),
    "chain_fees": (0.0, 1e8),
    "active_addr": (100, 5e7),
    "tps": (0.0, 3000.0),
    "holders": (10000, 5e8),
    "dormant_pct": (0.0, 100.0),
    "exchange_kas": (1e6, 3e10),
    "price": (0.0001, 100.0),
}

# Bot-Regel 12 mit Zaehnen: ein Sprung gegen die eigene Reihe stoppt den Post.
# Zweimal in einer Woche hat eine stille Definitionsaenderung eine falsche
# Zahl produziert. So etwas muss ab jetzt per FORCE bestaetigt werden.
MAX_JUMP = {
    "hashrate": 0.60,
    "block_reward": 0.10,
    "mined_pct": 0.01,
    "tvl_total": 0.80,
    "dex_vol": 4.00,
    "chain_fees": 5.00,
    "active_addr": 1.50,
    "tps": 1.50,
    "holders": 0.20,
    "dormant_pct": 0.10,
    "exchange_kas": 0.25,
}

MANUAL_KEYS = []          # seit 23.09.2026 leer, siehe KL_FELDER
AUTO_KEYS = [
    "hashrate", "block_reward", "emission", "mined_pct",
    "tvl_kasplex", "tvl_igra", "tvl_total", "dex_vol", "chain_fees",
    "holders", "active_addr", "dormant_pct", "exchange_kas", "tps",
]

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday"]

# Schreibregel. Gilt fuer alles was nach aussen geht, also auch fuer den Bot.
FORBIDDEN = ["—", "–", " - ", ":", "→"]


class Stop(Exception):
    """Abbruch mit Klartext. Kein halber Post."""


# ---------------------------------------------------------------- netzwerk --

def http_json(url, tries=RETRIES):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(2 * (i + 1))
    raise Stop("abruf fehlgeschlagen %s (%s)" % (url, last))


def fetch_hashrate():
    d = http_json("https://api.kaspa.org/info/hashrate?stringOnly=false")
    return float(d["hashrate"]) / 1000.0  # TH/s in PH/s


def fetch_supply():
    d = http_json("https://api.kaspa.org/info/coinsupply")
    circ = float(d["circulatingSupply"]) / 1e8
    mx = float(d["maxSupply"]) / 1e8
    if mx <= 0:
        raise Stop("coinsupply liefert maxSupply 0")
    return {"circ": circ, "mined_pct": 100.0 * circ / mx}


def _llama_chain_key(name):
    n = str(name or "").strip().lower()
    if n.startswith("kasplex"):
        return "kasplex"
    if n.startswith("igra"):
        return "igra"
    return None


def fetch_llama_tvl():
    rows = http_json("https://api.llama.fi/v2/chains")
    out = {}
    for row in rows:
        key = _llama_chain_key(row.get("name"))
        if key and key not in out:
            out[key] = float(row.get("tvl") or 0.0)
    return out


def _llama_overview(kind, chain):
    url = ("https://api.llama.fi/overview/%s/%s"
           "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
           % (kind, chain))
    try:
        d = http_json(url, tries=2)
    except Stop:
        return None
    v = d.get("total24h")
    return float(v) if v is not None else None


def fetch_price():
    """Kette wie in bots v3. Binance bewusst nicht drin, sperrt US-IPs."""
    chain = [
        ("https://api.kraken.com/0/public/Ticker?pair=KASUSD",
         lambda d: float(list(d["result"].values())[0]["c"][0])),
        ("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=KAS-USDT",
         lambda d: float(d["data"]["price"])),
        ("https://api.bybit.com/v5/market/tickers?category=spot&symbol=KASUSDT",
         lambda d: float(d["result"]["list"][0]["lastPrice"])),
        ("https://api.mexc.com/api/v3/ticker/price?symbol=KASUSDT",
         lambda d: float(d["price"])),
        ("https://api.coingecko.com/api/v3/simple/price"
         "?ids=kaspa&vs_currencies=usd",
         lambda d: float(d["kaspa"]["usd"])),
    ]
    for url, pick in chain:
        try:
            v = pick(http_json(url, tries=1))
            lo, hi = PLAUSIBLE["price"]
            if lo <= v <= hi:
                return v
        except Exception:  # noqa: BLE001
            continue
    return None  # graceful degradation, der Post kommt trotzdem


# ------------------------------------------------------------------ reward --

def utc(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc)


def reward_state(now_ts):
    n = math.floor((now_ts - ANCHOR_TS) / STEP)
    cur = ANCHOR_REWARD * (R ** n)
    nxt_ts = ANCHOR_TS + (n + 1) * STEP
    return cur, cur * R, nxt_ts


# --------------------------------------------------------------- formatter --

def fmt_int(n):
    return "{:,}".format(int(round(float(n))))


def fmt_money(v):
    v = float(v)
    if v >= 1e9:
        return "$%.2fB" % (v / 1e9)
    if v >= 1e6:
        return "$%.2fM" % (v / 1e6)
    if v >= 1e5:
        return "$%dK" % round(v / 1e3)
    if v >= 1e3:
        return "$%.1fK" % (v / 1e3)
    return "$%d" % round(v)


def fmt_kas(v):
    v = float(v)
    if v >= 1e9:
        return "%.2fB KAS" % (v / 1e9)
    if v >= 1e6:
        return "%.2fM KAS" % (v / 1e6)
    return "%s KAS" % fmt_int(v)


def fmt_num(v, nd=1):
    return ("%." + str(nd) + "f") % float(v)


def month_day(d):
    return "%s %d" % (MONTHS[d.month - 1], d.day)


def delta(key, now, prev):
    """gibt (kreis, text) zurueck, oder (None, None) ohne vergleichswoche"""
    if now is None or prev is None:
        return None, None
    try:
        prev = float(prev)
        now = float(now)
    except (TypeError, ValueError):
        return None, None
    if prev == 0:
        return None, None
    pct = (now - prev) / abs(prev) * 100.0
    if abs(pct) < FLAT_PCT:
        return "⚪", "unchanged"
    d = DIRECTION.get(key, 0)
    if d == 0:
        circle = "⚪"
    else:
        good = (pct > 0 and d > 0) or (pct < 0 and d < 0)
        circle = "\U0001f7e2" if good else "\U0001f534"
    return circle, "%s %s percent" % ("up" if pct > 0 else "down",
                                      fmt_num(abs(pct)))


def tail(key, now, prev, extra=""):
    """haengt ' KREIS text' an eine zeile, oder nichts"""
    if not SHOW_DELTA.get(key, False):
        return ""
    c, t = delta(key, now, prev)
    if c is None:
        return ""
    return " %s %s%s" % (c, t, extra)


def cut_phrase(nxt, nxt_ts, now_ts):
    d = utc(nxt_ts)
    days_out = (nxt_ts - now_ts) / DAY
    when = WEEKDAYS[d.weekday()] if days_out <= 8 else month_day(d)
    return "cut to %.3f on %s, %02d.%02d utc" % (nxt, when, d.hour, d.minute)


def vergleich_seit(prev, week_date):
    """Wie der Vergleich im Post heisst. Liegt die Vorwoche genau sieben
    Tage zurueck, bleibt es beim gewohnten Text ("this week" bei der
    Hashrate, sonst nur die Prozentzahl). Sonst steht an jedem Vergleich
    "since <datum der vorwoche>", denn nach einer ausgefallenen Woche ist
    der Abstand zwei oder drei Wochen, und "this week" waere falsch."""
    try:
        pw = dt.date.fromisoformat(str((prev or {}).get("week", "")))
    except ValueError:
        return None
    if (week_date - pw).days == 7:
        return None
    return " since " + month_day(pw)


def build_message(v, prev, issue, week_date, read, price=None, show_usd=False,
                  quelle="discord", tps_def=TPS_DEF):
    prev = prev or {}
    seit = vergleich_seit(prev, week_date)
    extra = seit or ""
    # tps nur gegen eine vorwoche derselben definition, siehe TPS_DEF
    tps_prev = prev.get("tps") if prev.get("tps_def") == tps_def else None
    out = []
    out.append("\U0001f4ca **kaspa pulse, week %d numbers**" % issue)
    out.append(month_day(week_date))
    out.append("")

    out.append("⛏️ **mining**")
    out.append("hashrate **%s PH/s**%s" % (
        fmt_num(v["hashrate"]),
        tail("hashrate", v["hashrate"], prev.get("hashrate"), seit or " this week")))
    out.append("block reward **%.2f KAS** \U0001f53b %s" % (
        v["block_reward"], v["cut_phrase"]))
    line = "emission **%s KAS** per day" % fmt_int(v["emission"])
    if show_usd and price:
        line += " worth %s" % fmt_money(v["emission"] * price)
    out.append(line)
    out.append("")

    out.append("\U0001f310 **network**")
    out.append("active addresses **%s** per day%s" % (
        fmt_int(v["active_addr"]),
        tail("active_addr", v["active_addr"], prev.get("active_addr"), extra)))
    out.append("tps **%s**%s" % (
        fmt_num(v["tps"], 2),
        tail("tps", v["tps"], tps_prev, extra)))
    out.append("addresses holding a balance **%s**%s" % (
        fmt_int(v["holders"]),
        tail("holders", v["holders"], prev.get("holders"), extra)))
    out.append("")

    out.append("\U0001f9f1 **layer 2**")
    out.append("total tvl **%s**%s" % (
        fmt_money(v["tvl_total"]),
        tail("tvl_total", v["tvl_total"], prev.get("tvl_total"), extra)))
    out.append("kasplex **%s** and igra **%s**" % (
        fmt_money(v["tvl_kasplex"]), fmt_money(v["tvl_igra"])))
    out.append("dex volume **%s**%s" % (
        fmt_money(v["dex_vol"]),
        tail("dex_vol", v["dex_vol"], prev.get("dex_vol"), extra)))
    out.append("chain fees **%s** for the day%s" % (
        fmt_money(v["chain_fees"]),
        tail("chain_fees", v["chain_fees"], prev.get("chain_fees"), extra)))
    out.append("")

    out.append("\U0001fa99 **supply**")
    out.append("**%s percent** of all KAS already mined"
               % fmt_num(v["mined_pct"], 2))
    line = "**%s percent** has not moved in over a year" % fmt_num(v["dormant_pct"])
    dc, dtxt = delta("dormant_pct", v["dormant_pct"], prev.get("dormant_pct"))
    if SHOW_DELTA.get("dormant_pct") and dc:
        line += " %s %s%s" % (dc, dtxt, extra)
    out.append(line)
    line = "exchange balances **%s**%s" % (
        fmt_kas(v["exchange_kas"]),
        tail("exchange_kas", v["exchange_kas"], prev.get("exchange_kas"), extra))
    if show_usd and price:
        line += " worth %s" % fmt_money(v["exchange_kas"] * price)
    out.append(line)
    out.append("")

    out.append("\U0001f4a1 **the read**")
    out.append(read.strip())
    out.append("")
    out.append("\U0001f517 full dashboard kaspapulse.com")
    # Der Anmeldelink traegt seine Quelle. Discord und Telegram bekommen
    # denselben Text, aber NICHT denselben Link: sonst steht in der
    # Auswertung ein Topf fuer zwei Kanaele (scripts/utm.py).
    out.append("\U0001f4e9 the same numbers by email every monday "
               + utm.link(quelle, campaign="weekly-numbers"))
    return "\n".join(out)


URL_IM_TEXT = re.compile(r"https?://\S+")


def assert_punctuation(text):
    """Schreibregel mechanisch statt aus dem Gedaechtnis.

    Links sind davon ausgenommen. Die Regel ("keine Gedankenstriche, keine
    Doppelpunkte, keine Pfeile") ist eine Regel fuer PROSA; ein Doppelpunkt
    in https:// ist keine Interpunktion, sondern Teil einer Adresse. Ohne
    diese Ausnahme koennte kein Post einen Link tragen, und der Anmeldelink
    mit seiner Quelle muss unter jeden Wochenpost."""
    text = URL_IM_TEXT.sub("", text)
    hits = [c for c in FORBIDDEN if c in text]
    if hits:
        raise Stop("schreibregel verletzt, gefunden %r. keine gedankenstriche, "
                   "keine doppelpunkte, keine pfeile im post" % hits)


# ------------------------------------------------------------------ pruefen --

def check_plausible(values):
    for key, val in values.items():
        if key not in PLAUSIBLE or val is None:
            continue
        lo, hi = PLAUSIBLE[key]
        if not (lo <= float(val) <= hi):
            raise Stop("wert ausserhalb des fensters, %s = %s erlaubt %s bis %s"
                       % (key, val, lo, hi))


def check_jumps(values, prev, force=False):
    warn = []
    for key, limit in MAX_JUMP.items():
        now = values.get(key)
        old = (prev or {}).get(key)
        if now is None or old in (None, 0):
            continue
        move = abs(float(now) - float(old)) / abs(float(old))
        if move > limit:
            warn.append("%s springt um %.0f prozent, von %s auf %s, grenze %.0f"
                        % (key, move * 100, old, now, limit * 100))
    if warn and not force:
        raise Stop("sprungbremse. " + " | ".join(warn) +
                   ". erst pruefen, dann mit FORCE=1 starten wenn die zahl stimmt")
    for w in warn:
        print("WARN sprung akzeptiert weil FORCE gesetzt, " + w)


# ------------------------------------------------------------------ dateien --

def load_json(path, default=None):
    if not os.path.exists(path):
        if default is None:
            raise Stop("datei fehlt %s" % path)
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_input(path=None):
    data = load_json(path or INPUT_PATH)
    week = str(data.get("week", "")).strip()
    try:
        wd = dt.date.fromisoformat(week)
    except ValueError:
        raise Stop("week fehlt oder ist kein datum im format JJJJ-MM-TT")
    manual = data.get("manual") or {}
    missing = [k for k in MANUAL_KEYS
               if manual.get(k) is None or manual.get(k) == ""]
    if missing:
        raise Stop("handzahlen fehlen, %s. der post geht nicht raus solange "
                   "eine zahl fehlt" % ", ".join(missing))
    read = str(data.get("read", "")).strip()
    if len(read) < 40:
        raise Stop("the read fehlt oder ist zu kurz. das ist der teil der uns "
                   "von einem datenfeed unterscheidet, den schreibt kein bot")
    return {
        "week": week,
        "date": wd,
        "manual": {k: float(manual[k]) for k in MANUAL_KEYS},
        "read": read,
        "override": data.get("override") or {},
        "issue": data.get("issue"),
    }


def issue_number(week_date, given=None):
    if given:
        return int(given)
    anchor = dt.date.fromisoformat(ISSUE_ANCHOR_WEEK)
    return ISSUE_ANCHOR_NUM + (week_date - anchor).days // 7


def previous_entry(history, week):
    past = [h for h in history if str(h.get("week", "")) < week]
    past.sort(key=lambda h: h["week"])
    return past[-1] if past else None


# ------------------------------------------------------------------ posten --

def post_discord(msg, dry=False, msg_tg=None):
    hook = (os.environ.get("DISCORD_WEBHOOK_WEEKLY")
            or os.environ.get("DISCORD_WEBHOOK"))
    if len(msg) > 1990:
        raise Stop("nachricht zu lang, %d zeichen. discord kann 2000" % len(msg))
    if dry:
        print("DRY_RUN, nichts gepostet")
        return
    if not hook:
        raise Stop("kein webhook. DISCORD_WEBHOOK_WEEKLY als repository secret "
                   "anlegen, der webhook muss im kanal weekly-numbers haengen")
    body = json.dumps({"content": msg,
                       "allowed_mentions": {"parse": []}}).encode("utf-8")
    req = urllib.request.Request(
        hook, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if r.status not in (200, 204):
            raise Stop("discord antwortet %s" % r.status)
    print("gepostet")

    # spiegel nach telegram. faellt er aus, bleibt discord unberuehrt,
    # siehe telegram_post.py. der dry-run kommt hier gar nicht erst an.
    # msg_tg traegt denselben Text mit utm_source=tg statt discord.
    telegram_post.send_text(msg_tg or msg)


# -------------------------------------------------------------------- lauf --

def _need(d, key):
    if key not in d:
        raise Stop("kette %s steht nicht in der defillama antwort" % key)
    return d[key]


def _sum_overview(kind):
    total = 0.0
    got = 0
    for chain in ("kasplex", "igra"):
        val = _llama_overview(kind, chain)
        if val is not None:
            total += val
            got += 1
    if got == 0:
        raise Stop("defillama %s liefert fuer keine der beiden ketten "
                   "einen wert" % kind)
    if got < 2:
        print("WARN defillama %s hat nur eine der beiden ketten geliefert" % kind)
    return total


# ---------------------------------------------------------- kaspalytics --
# Bis zum 21.09.2026 kamen fuenf Zahlen von Hand aus Diagrammen. Seit dem
# 22.09. holt der Bot holders selbst, seit dem 23.09. auch die restlichen
# vier. Damit bleibt in data/week-input.json nur noch "the read" von Hand,
# und der Montag braucht keine Screenshots mehr.
#
# ACHTUNG, ZWEI BEDEUTUNGEN FUER EIN WORT. In scripts/kaspalytics.py heisst
# das Feld "holders" der RUHENDE ANTEIL in Prozent, hier heisst "holders"
# die ADRESSZAHL und der ruhende Anteil heisst "dormant_pct". Die Zuordnung
# unten ist deshalb absichtlich ueber Kreuz und keine Schlamperei. Das
# Umbenennen steht nach dem Montagslauf am 28.09. an.
#
# unser name -> name in kaspalytics.py
KL_FELDER = {
    "holders":      "holder_addr",    # adressen mit nennenswertem guthaben
    "active_addr":  "active_addr",    # aktive adressen, kurve ALL UNIQUE
    "dormant_pct":  "holders",        # ruhender anteil ab 1 jahr, in prozent
    "exchange_kas": "exchange_kas",   # bekannte boersenbestaende
    "tps":          "tps",            # wochenmittel, nur Standard, siehe 16.09.
}

_KL = {}


def kaspalytics_reset():
    """Den Zwischenspeicher leeren. Braucht nur der Selbsttest."""
    _KL.clear()


def kaspalytics_werte():
    """sammle() genau einmal je Lauf.

    Frueher holte jedes Feld einzeln, das waeren jetzt fuenf Laeufe ueber
    dieselben Endpunkte. sammle() holt alles in einem Rutsch und faengt
    dabei je Feld ab: faellt eine Reihe aus, stehen die anderen trotzdem.
    """
    if not _KL:
        werte, tage, probleme = kaspalytics.sammle()
        _KL["werte"], _KL["tage"], _KL["probleme"] = werte, tage, probleme
        if probleme:
            print("kaspalytics meldet %d probleme: %s"
                  % (len(probleme), " | ".join(probleme)))
    return _KL["werte"]


def kl_feld(unser_name):
    """Ein Kaspalytics-Feld holen. Fehlt es, scheitert das laut.

    Ein stiller Rueckfall auf die Vorwoche waere hier das Schlimmste, was
    passieren koennte: die Zeile stuende im Post, saehe richtig aus und
    waere eine Woche alt. Stattdessen faengt collect_auto den Fehler,
    nennt das Feld beim Namen und der Post geht nicht raus. Von Hand
    setzbar bleibt jedes dieser Felder ueber override.
    """
    name = KL_FELDER[unser_name]
    wert = kaspalytics_werte().get(name)
    if wert is None:
        raise RuntimeError("kaspalytics liefert %s nicht" % name)
    return float(wert)


def fetch_holders():
    """Die Zahl der Adressen mit nennenswertem Guthaben.

    Bis zum 21.09.2026 stand sie als Handwert in week-input.json, ohne
    geklaerte Quelle, und wurde Woche fuer Woche uebernommen. Am 22.09.
    wurde im Runner nachgesehen: der uebernommene Wert 792098 steht exakt
    in der Reihe address/count/meaningful-balance, am 06.09.
    """
    return kl_feld("holders")


def collect_auto(now_ts, override):
    """holt was zu holen ist. jedes feld laesst sich per override setzen."""
    v = {}
    errors = []

    def take(key, fn):
        if override.get(key) is not None:
            v[key] = float(override[key])
            print("override %s = %s" % (key, v[key]))
            return
        try:
            v[key] = fn()
        except Exception as exc:  # noqa: BLE001
            errors.append("%s (%s)" % (key, exc))

    take("hashrate", fetch_hashrate)
    take("mined_pct", lambda: fetch_supply()["mined_pct"])
    take("holders", fetch_holders)
    take("active_addr", lambda: kl_feld("active_addr"))
    take("dormant_pct", lambda: kl_feld("dormant_pct"))
    take("exchange_kas", lambda: kl_feld("exchange_kas"))
    take("tps", lambda: kl_feld("tps"))

    tvl = {}
    if override.get("tvl_kasplex") is None or override.get("tvl_igra") is None:
        try:
            tvl = fetch_llama_tvl()
        except Exception as exc:  # noqa: BLE001
            errors.append("defillama chains (%s)" % exc)
    take("tvl_kasplex", lambda: _need(tvl, "kasplex"))
    take("tvl_igra", lambda: _need(tvl, "igra"))
    take("dex_vol", lambda: _sum_overview("dexs"))
    take("chain_fees", lambda: _sum_overview("fees"))

    cur, nxt, nxt_ts = reward_state(now_ts)
    if override.get("block_reward") is not None:
        cur = float(override["block_reward"])
        nxt = cur * R
    v["block_reward"] = cur
    v["emission"] = cur * BPS * DAY
    v["cut_phrase"] = cut_phrase(nxt, nxt_ts, now_ts)

    if "tvl_kasplex" in v and "tvl_igra" in v:
        v["tvl_total"] = v["tvl_kasplex"] + v["tvl_igra"]
    if override.get("tvl_total") is not None:
        v["tvl_total"] = float(override["tvl_total"])

    if errors:
        raise Stop("diese werte kamen nicht, " + " | ".join(errors) +
                   ". entweder quelle pruefen oder den wert in week-input.json "
                   "unter override von hand eintragen")
    return v


# Automatische Anstoesse. Weder ein Termin- noch ein Push-Lauf postet eine
# Woche, die nicht heute ist. Der Start von Hand (workflow_dispatch) bleibt
# frei, dafuer ist er da.
AUTO_EVENTS = ("push", "schedule")


def falsche_woche(event, week, heute):
    """Gibt die Abbruchmeldung zurueck, wenn ein automatischer Lauf eine
    Woche posten wuerde, die nicht heute ist, sonst None.

    Push: am 22. und 23.09.2026 haben zwei PR-Merges die Datei beruehrt und
    je einen echten Lauf gestartet; ohne Sprungbremse waere der Montagspost
    an einem Dienstag mit den Zahlen vom Dienstag rausgegangen.
    Termin: steht montags um 14:20 UTC noch die alte Woche in der Datei, hat
    die Montagsroutine nicht (rechtzeitig) geliefert. Dann kein Post mit
    alter Woche, sondern ein roter Lauf, den man sieht."""
    if event not in AUTO_EVENTS:
        return None
    if str(week).strip() == str(heute).strip():
        return None
    return ("%s-lauf, aber week in data/week-input.json ist %s und heute ist "
            "%s (Berlin). kein post. entweder hat die montagsroutine die neue "
            "woche nicht eingetragen, oder der lauf kam an einem anderen tag. "
            "wenn der post trotzdem raus soll, von hand per workflow_dispatch "
            "starten" % (event, week or "leer", heute))


def heute_berlin():
    fest = os.environ.get("WN_HEUTE", "").strip()
    if fest:
        dt.date.fromisoformat(fest)
        print("hinweis: datum simuliert, WN_HEUTE=%s" % fest)
        return fest
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()


def ops_zeile(log):
    """Die eine Zeile, die an den Ops-Kanal geht: die letzte ABBRUCH-Zeile,
    sonst die letzte Fehlerzeile, sonst die letzte Zeile ueberhaupt."""
    zeilen = [z.strip() for z in (log or "").splitlines() if z.strip()]
    for z in reversed(zeilen):
        if z.startswith("ABBRUCH"):
            return z
    for z in reversed(zeilen):
        if re.search(r"error|fehl|FAIL|Traceback|exception", z, re.I):
            return z
    return zeilen[-1] if zeilen else "kein log, der lauf ist vor dem ersten schritt gestorben"


def ops_melden(log_pfad, hook=None, lauf="", anlass=""):
    """Schickt die ops_zeile an DISCORD_WEBHOOK_OPS. Ohne Secret wird still
    uebersprungen, damit der Schritt nicht selbst rot wird, solange das
    Secret nicht angelegt ist. Ein Fehler beim Senden wird gedruckt, nicht
    geworfen: der Lauf ist ohnehin schon rot."""
    hook = hook if hook is not None else os.environ.get("DISCORD_WEBHOOK_OPS", "")
    try:
        with open(log_pfad, encoding="utf-8", errors="replace") as fh:
            log = fh.read()
    except OSError:
        log = ""
    zeile = ops_zeile(log)
    text = ("weekly numbers ist rot (%s)\n%s\n%s" % (anlass or "?", zeile, lauf)).strip()
    if len(text) > 1900:
        text = text[:1900]
    print(text)
    if not hook:
        print("kein DISCORD_WEBHOOK_OPS gesetzt, meldung uebersprungen")
        return 0
    body = json.dumps({"content": text,
                       "allowed_mentions": {"parse": []}}).encode("utf-8")
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            print("an ops gemeldet, http %s" % r.status)
    except Exception as exc:  # noqa: BLE001
        print("WARN ops-meldung ging nicht raus: %s" % exc)
    return 0


def history_eintrag(week, issue, v, price=None):
    entry = {"week": week, "issue": issue}
    for k in AUTO_KEYS + MANUAL_KEYS:
        if k in v:
            entry[k] = round(float(v[k]), 6)
    if "tps" in entry:
        entry["tps_def"] = TPS_DEF
    if price:
        entry["price"] = price
    return entry


def main():
    dry = os.environ.get("DRY_RUN", "").strip() not in ("", "0", "false")
    force = os.environ.get("FORCE", "").strip() not in ("", "0", "false")
    show_usd = os.environ.get("SHOW_USD", "").strip() not in ("", "0", "false")

    event = os.environ.get("GITHUB_EVENT_NAME", "")
    history = load_json(HISTORY_PATH, default=[])
    peek = str(load_json(INPUT_PATH).get("week", "")).strip()
    heute = heute_berlin()
    # der montagstermin prueft die woche VOR der dublettenpruefung. sonst
    # liefe er gruen durch, wenn die routine nicht geliefert hat und noch
    # die schon gepostete woche in der datei steht, und niemand merkt es.
    if event == "schedule":
        falsch = falsche_woche(event, peek, heute)
        if falsch:
            raise Stop(falsch)
    # dublettenpruefung. so laeuft ein merge, der die datei nach dem post
    # noch einmal beruehrt, gruen durch.
    if any(h.get("week") == peek for h in history) and not force:
        print("woche %s steht schon in der history. nichts gepostet. "
              "mit FORCE=1 starten wenn das absicht ist" % peek)
        return 0
    falsch = falsche_woche(event, peek, heute)
    if falsch:
        raise Stop(falsch)

    inp = read_input()
    now_ts = time.time()
    v = collect_auto(now_ts, inp["override"])
    v.update(inp["manual"])
    prev = previous_entry(history, inp["week"])

    check_plausible({k: v.get(k) for k in PLAUSIBLE if k in v})
    check_jumps(v, prev, force=force)

    price = fetch_price() if show_usd else None  # Regel 8, nur bei bedarf
    issue = issue_number(inp["date"], inp["issue"])
    msg = build_message(v, prev, issue, inp["date"], inp["read"],
                        price=price, show_usd=show_usd, quelle="discord")
    msg_tg = build_message(v, prev, issue, inp["date"], inp["read"],
                           price=price, show_usd=show_usd, quelle="tg")
    assert_punctuation(msg)
    assert_punctuation(msg_tg)
    print(msg)
    print("---- %d zeichen ----" % len(msg))

    post_discord(msg, dry=dry, msg_tg=msg_tg)

    if not dry:
        entry = history_eintrag(inp["week"], issue, v, price)
        history = [h for h in history if h.get("week") != inp["week"]]
        history.append(entry)
        history.sort(key=lambda h: h["week"])
        with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(history, fh, indent=2)
            fh.write("\n")
        print("history fortgeschrieben, %d wochen" % len(history))
    return 0


# ---------------------------------------------------------------- selftest --

GOLD_PREV = {
    "week": "2026-07-27",
    "hashrate": 262.3,
    "block_reward": 2.44997148,
    "mined_pct": 96.15,
    "tvl_total": 1962470.0,
    "dex_vol": 133009.0,
    "chain_fees": 305.0,
    "active_addr": 7950,
    "tps": 0.75,
    "holders": 735960,
    "dormant_pct": 50.47,
    "exchange_kas": 3941512619.0,
}

GOLD_NOW = {
    "hashrate": 342.5,
    "block_reward": 2.44997148,
    "emission": 2.44997148 * BPS * DAY,
    "mined_pct": 96.21,
    "tvl_kasplex": 342947.0,
    "tvl_igra": 1490000.0,
    "tvl_total": 1832947.0,
    "dex_vol": 109200.0,
    "chain_fees": 226.0,
    "active_addr": 13940,
    "tps": 0.91,
    "holders": 747603,
    "dormant_pct": 50.60,
    "exchange_kas": 3854799342.0,
}

GOLD_READ = ("more machines joined the network than at any point this quarter, "
             "and the reward per machine drops on wednesday. miners are paying "
             "more to earn less. that is a bet on later, not on today.")

GOLD_MSG = "\n".join([
    "\U0001f4ca **kaspa pulse, week 4 numbers**",
    "august 3",
    "",
    "⛏️ **mining**",
    "hashrate **342.5 PH/s** \U0001f7e2 up 30.6 percent this week",
    "block reward **2.45 KAS** \U0001f53b cut to 2.312 on wednesday, 06.15 utc",
    "emission **2,116,775 KAS** per day",
    "",
    "\U0001f310 **network**",
    "active addresses **13,940** per day",
    "tps **0.91** \U0001f7e2 up 21.3 percent",
    "addresses holding a balance **747,603**",
    "",
    "\U0001f9f1 **layer 2**",
    "total tvl **$1.83M** \U0001f534 down 6.6 percent",
    "kasplex **$343K** and igra **$1.49M**",
    "dex volume **$109K** \U0001f534 down 17.9 percent",
    "chain fees **$226** for the day",
    "",
    "\U0001fa99 **supply**",
    "**96.21 percent** of all KAS already mined",
    "**50.6 percent** has not moved in over a year ⚪ unchanged",
    "exchange balances **3.85B KAS** \U0001f7e2 down 2.2 percent",
    "",
    "\U0001f4a1 **the read**",
    GOLD_READ,
    "",
    "\U0001f517 full dashboard kaspapulse.com",
    "\U0001f4e9 the same numbers by email every monday "
    "https://kaspapulse.com/?utm_source=discord&utm_medium=chat"
    "&utm_campaign=weekly-numbers#subscribe",
])


def run_selftest():
    import calendar
    import tempfile

    fails = []

    def ok(name, cond, detail=""):
        print(("  ok   " if cond else "  FAIL ") + name +
              ("" if cond else "  " + str(detail)))
        if not cond:
            fails.append(name)

    def raises(name, fn):
        try:
            fn()
        except Stop as exc:
            print("  ok   %s (%s)" % (name, str(exc)[:60]))
            return
        print("  FAIL " + name + "  kein abbruch, obwohl erwartet")
        fails.append(name)

    print("selftest weekly_numbers")

    # 1 geldformat
    ok("fmt_money 1832947", fmt_money(1832947) == "$1.83M", fmt_money(1832947))
    ok("fmt_money 342947", fmt_money(342947) == "$343K", fmt_money(342947))
    ok("fmt_money 109200", fmt_money(109200) == "$109K", fmt_money(109200))
    ok("fmt_money 19600", fmt_money(19600) == "$19.6K", fmt_money(19600))
    ok("fmt_money 226", fmt_money(226) == "$226", fmt_money(226))

    # 2 kas format
    ok("fmt_kas 3.85B", fmt_kas(3854799342) == "3.85B KAS", fmt_kas(3854799342))
    ok("fmt_kas 11.65M", fmt_kas(11654139) == "11.65M KAS", fmt_kas(11654139))

    # 3 reward anker rollt auf den bekannten cut
    ts = calendar.timegm((2026, 8, 3, 12, 0, 0))
    cur, nxt, nxt_ts = reward_state(ts)
    ok("reward jetzt 2.44997148", abs(cur - 2.44997148) < 1e-8, cur)
    ok("reward danach 2.312", "%.3f" % nxt == "2.312", nxt)
    ok("cut am 5.8.2026 06.15 utc",
       utc(nxt_ts).strftime("%Y-%m-%d %H.%M") == "2026-08-05 06.15",
       utc(nxt_ts))
    ok("cut satz", cut_phrase(nxt, nxt_ts, ts) ==
       "cut to 2.312 on wednesday, 06.15 utc", cut_phrase(nxt, nxt_ts, ts))

    # 4 weit entfernter cut nennt datum statt wochentag
    far = calendar.timegm((2026, 7, 6, 12, 0, 0))
    c2, n2, t2 = reward_state(far)
    ok("ferner cut nennt datum", "august 5" in cut_phrase(n2, t2, far),
       cut_phrase(n2, t2, far))

    # 5 richtung der farbe
    ok("boersenbestand runter ist gruen",
       delta("exchange_kas", 90.0, 100.0)[0] == "\U0001f7e2")
    ok("tvl runter ist rot", delta("tvl_total", 90.0, 100.0)[0] == "\U0001f534")
    ok("hashrate hoch ist gruen", delta("hashrate", 110.0, 100.0)[0] == "\U0001f7e2")
    ok("hashrate runter ist rot", delta("hashrate", 90.0, 100.0)[0] == "\U0001f534")
    ok("kleine bewegung ist unchanged",
       delta("holders", 100.4, 100.0) == ("⚪", "unchanged"))
    ok("ohne vorwoche kein kreis", delta("hashrate", 100.0, None) == (None, None))

    # 6 die harte probe, der post vom 03.08. zeichen fuer zeichen
    v = dict(GOLD_NOW)
    v["cut_phrase"] = cut_phrase(nxt, nxt_ts, ts)
    # der goldpost vom 03.08. ist ganz nach der alten tps-definition
    # gemessen, jetzt und vorwoche, also vergleicht er tps
    msg = build_message(v, GOLD_PREV, 4, dt.date(2026, 8, 3), GOLD_READ,
                        tps_def=None)
    if msg != GOLD_MSG:
        for a, b in zip(msg.split("\n"), GOLD_MSG.split("\n")):
            if a != b:
                print("      ist  %r" % a)
                print("      soll %r" % b)
    ok("post vom 03.08. exakt reproduziert", msg == GOLD_MSG)
    ok("laenge unter dem discord limit", len(msg) < 1990, len(msg))

    # 7 schreibregel
    assert_punctuation(msg)
    print("  ok   schreibregel im goldpost eingehalten")
    raises("doppelpunkt wird abgefangen",
           lambda: assert_punctuation("the read: numbers"))
    raises("gedankenstrich wird abgefangen",
           lambda: assert_punctuation("hashrate — up"))
    raises("pfeil wird abgefangen",
           lambda: assert_punctuation("2.45 → 2.31"))

    # 8 plausibilitaetsfenster
    raises("absurde hashrate stoppt",
           lambda: check_plausible({"hashrate": 999999.0}))
    raises("dormant ueber 100 stoppt",
           lambda: check_plausible({"dormant_pct": 140.0}))
    check_plausible({k: GOLD_NOW[k] for k in GOLD_NOW if k in PLAUSIBLE})
    print("  ok   echte werte liegen im fenster")

    # 9 sprungbremse
    check_jumps(GOLD_NOW, GOLD_PREV)
    print("  ok   echte woche passiert die sprungbremse")
    raises("verdreifachte hashrate stoppt",
           lambda: check_jumps({"hashrate": 900.0}, GOLD_PREV))
    check_jumps({"hashrate": 900.0}, GOLD_PREV, force=True)
    print("  ok   FORCE laesst den sprung durch")

    # 10 ausgabennummer
    ok("issue 03.08. ist 4", issue_number(dt.date(2026, 8, 3)) == 4)
    ok("issue 10.08. ist 5", issue_number(dt.date(2026, 8, 10)) == 5)
    ok("issue 07.09. ist 9", issue_number(dt.date(2026, 9, 7)) == 9)
    ok("issue laesst sich ueberschreiben",
       issue_number(dt.date(2026, 8, 10), 12) == 12)

    # 11 vorwoche finden
    hist = [{"week": "2026-07-20"}, {"week": "2026-07-27"}, {"week": "2026-08-03"}]
    ok("vorwoche ist die letzte davor",
       previous_entry(hist, "2026-08-03")["week"] == "2026-07-27")
    ok("erste woche hat keine vorwoche",
       previous_entry(hist, "2026-07-13") is None)

    # 12 eingabedatei
    tmp = tempfile.mkdtemp()

    def write_input(obj):
        p = os.path.join(tmp, "week-input.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return p

    good = {
        "week": "2026-08-10",
        "manual": {"active_addr": 14000, "tps": 0.95, "holders": 748000,
                   "dormant_pct": 50.5, "exchange_kas": 3800000000},
        "read": GOLD_READ,
    }
    got = read_input(write_input(good))
    ok("eingabedatei wird gelesen", got["week"] == "2026-08-10")
    # die pruefung "fehlende handzahl stoppt" ist am 23.09.2026 entfallen,
    # weil es keine pflicht-handzahl mehr gibt. was den lauf jetzt noch
    # stoppt, steht weiter unten: ein fehlender read und ein datum im
    # falschen format.

    # seit dem 23.09.2026 ist KEIN feld mehr handwert. eine eingabedatei
    # ohne manual-block muss durchlaufen, und was dort stehengeblieben
    # ist, darf nicht mehr in den post wandern: sonst haette die
    # umstellung nichts geaendert und niemandem waere es aufgefallen.
    ohne = json.loads(json.dumps(good))
    del ohne["manual"]
    got2 = read_input(write_input(ohne))
    ok("eingabedatei ohne handwerte laeuft durch", got2["week"] == "2026-08-10")
    ok("handwerte sind leer", got2["manual"] == {})
    ok("MANUAL_KEYS ist leer", MANUAL_KEYS == [])
    for feld in ("holders", "active_addr", "dormant_pct", "exchange_kas", "tps"):
        ok("%s ist ein automatisches feld" % feld,
           feld in AUTO_KEYS and feld not in MANUAL_KEYS)
    mit = read_input(write_input(good))
    ok("stehengebliebene handwerte werden ignoriert", mit["manual"] == {})

    # Ein Stub, der an der LAUFENDEN Woche haengt. Der feste Stub in
    # kaspalytics.py liegt im August 2026; collect_auto rechnet aber gegen
    # das heutige Datum, und dann faellt tps aus, weil sein Siebentagefenster
    # leer bleibt. Ein Test, der aus dem falschen Grund rot wird, ist so
    # wenig wert wie einer, der aus dem falschen Grund gruen wird.
    def stub_diese_woche(pfad):
        anker = kaspalytics.wochenanker(dt.datetime.now(dt.timezone.utc).date())
        tage = [anker - dt.timedelta(days=n) for n in range(12, 0, -1)]
        fluss = [t.strftime("%Y-%m-%dT00:00:00.000Z") for t in tage]
        # bestaende mit echtem mitternachtsschlupf, abwechselnd
        bestand = [(t.strftime("%Y-%m-%dT23:59:59.400Z") if i % 2 == 0
                    else (t + dt.timedelta(days=1)).strftime("%Y-%m-%dT00:00:02.100Z"))
                   for i, t in enumerate(tage)]
        n = len(tage)
        if pfad.startswith("transactions/accepted/addresses"):
            return {"labels": fluss, "datasets": [
                {"label": "Addresses", "data": [7000 + i for i in range(n)]}]}
        if pfad.startswith("transactions/accepted/count"):
            return {"labels": fluss, "datasets": [
                {"label": "Standard", "data": [86400] * n},
                {"label": "Coinbase", "data": [120000] * n}]}
        if pfad.startswith("address/count"):
            return {"labels": bestand, "datasets": [
                {"label": "Addresses", "data": [790000 + i for i in range(n)]}]}
        if pfad.startswith("supply/inactive"):
            return {"labels": bestand, "datasets": [
                {"label": "CSPERCENT", "data": [50.5 + i / 100.0 for i in range(n)]}]}
        if pfad.startswith("supply/exchange-holdings"):
            return {"labels": bestand, "datasets": [
                {"label": "Balance", "data": [3.8e9 + i for i in range(n)]}]}
        if pfad.startswith("covenants/transactions"):
            return {"labels": fluss, "datasets": [
                {"label": "Transactions", "data": [500 + i for i in range(n)]}]}
        raise RuntimeError("unbekannter pfad im wochenstub, %s" % pfad)

    # der weg, auf dem die fuenf zahlen jetzt kommen. gestubbt wird der
    # echte stub aus kaspalytics.py, damit hier nicht eine zweite,
    # abweichende vorstellung von den reihen entsteht.
    echte_hole = kaspalytics.hole
    try:
        kaspalytics.hole = kaspalytics._stub
        kaspalytics_reset()
        heute = dt.date(2026, 8, 18)
        soll, _, _ = kaspalytics.sammle(heute=heute, holer=kaspalytics._stub)
        kaspalytics_reset()
        _KL["werte"], _KL["tage"], _KL["probleme"] = soll, {}, []
        ok("holders kommt aus der adressreihe", fetch_holders() == 789500.0)
        ok("active_addr kommt aus der eigenen reihe",
           kl_feld("active_addr") == float(soll["active_addr"]))
        ok("dormant_pct kommt aus dem ruhenden anteil",
           kl_feld("dormant_pct") == float(soll["holders"]))
        ok("exchange_kas kommt aus dem boersenbestand",
           kl_feld("exchange_kas") == float(soll["exchange_kas"]))
        ok("tps kommt aus dem wochenmittel", kl_feld("tps") == float(soll["tps"]))
        # die kreuzung der beiden holders-bedeutungen ist der gefaehrliche
        # teil. dormant_pct ist ein prozentwert, holders eine adresszahl;
        # wer sie vertauscht, faellt hier auf.
        ok("dormant_pct ist ein prozentwert", 0.0 < kl_feld("dormant_pct") < 100.0)
        ok("holders ist eine adresszahl", kl_feld("holders") > 1000.0)
        ok("die beiden sind nicht dieselbe zahl",
           kl_feld("holders") != kl_feld("dormant_pct"))
    finally:
        kaspalytics.hole = echte_hole
        kaspalytics_reset()

    # faellt eine einzelne reihe aus, stoppt der lauf und nennt das feld.
    # ein stiller rueckfall auf die vorwoche waere das schlimmste: die
    # zeile stuende im post, saehe richtig aus und waere eine woche alt.
    echte_hole = kaspalytics.hole
    try:
        def halb(pfad):
            if pfad.startswith("supply/exchange-holdings"):
                raise RuntimeError("503")
            return stub_diese_woche(pfad)
        kaspalytics.hole = halb
        kaspalytics_reset()
        rest = {"hashrate": 300.0, "mined_pct": 93.0, "tvl_kasplex": 1.0,
                "tvl_igra": 1.0, "dex_vol": 1.0, "chain_fees": 1.0}
        try:
            collect_auto(time.time(), rest)
            ok("faellt eine reihe aus, stoppt der lauf", False)
        except Stop as exc:
            ok("faellt eine reihe aus, stoppt der lauf", "exchange_kas" in str(exc))
            ok("und nur dieses eine feld wird genannt",
               all(x not in str(exc) for x in
                   ("holders", "active_addr", "dormant_pct", "tps")))
        # mit heiler quelle laeuft derselbe aufruf vollstaendig durch
        kaspalytics.hole = stub_diese_woche
        kaspalytics_reset()
        v_ganz = collect_auto(time.time(), rest)
        ok("mit heiler quelle sind alle fuenf felder da",
           all(x in v_ganz for x in ("holders", "active_addr", "dormant_pct",
                                     "exchange_kas", "tps")))
        ok("tps ist das wochenmittel, nicht der tageswert", v_ganz["tps"] == 1.0)
    finally:
        kaspalytics.hole = echte_hole
        kaspalytics_reset()

    # jedes der fuenf felder bleibt per override von hand setzbar
    echte_hole = kaspalytics.hole
    try:
        kaspalytics.hole = lambda pfad: (_ for _ in ()).throw(RuntimeError("503"))
        kaspalytics_reset()
        v_ov = collect_auto(time.time(), {
            "holders": 792098, "active_addr": 7760, "dormant_pct": 50.54,
            "exchange_kas": 3790000000, "tps": 2.76,
            "hashrate": 300.0, "mined_pct": 93.0,
            "tvl_kasplex": 1.0, "tvl_igra": 1.0,
            "dex_vol": 1.0, "chain_fees": 1.0})
        ok("override setzt holders", v_ov["holders"] == 792098.0)
        ok("override setzt active_addr", v_ov["active_addr"] == 7760.0)
        ok("override setzt dormant_pct", v_ov["dormant_pct"] == 50.54)
        ok("override setzt exchange_kas", v_ov["exchange_kas"] == 3790000000.0)
        ok("override setzt tps", v_ov["tps"] == 2.76)
        ok("und dann kommt der lauf ganz ohne kaspalytics aus",
           all(x in v_ov for x in ("holders", "active_addr", "dormant_pct",
                                   "exchange_kas", "tps")))
    finally:
        kaspalytics.hole = echte_hole
        kaspalytics_reset()

    bad2 = json.loads(json.dumps(good))
    bad2["read"] = "kurz"
    raises("fehlender read stoppt", lambda: read_input(write_input(bad2)))
    bad3 = json.loads(json.dumps(good))
    bad3["week"] = "10.08.2026"
    raises("falsches datumsformat stoppt", lambda: read_input(write_input(bad3)))

    # 13 dollarversion baut und bleibt im limit
    usd = build_message(v, GOLD_PREV, 4, dt.date(2026, 8, 3), GOLD_READ,
                        price=0.02639, show_usd=True)
    ok("usd version nennt den emissionswert", "worth $55.9K" in usd,
       [l for l in usd.split("\n") if "emission" in l])
    ok("usd version nennt den boersenwert", "worth $101.73M" in usd,
       [l for l in usd.split("\n") if "exchange" in l])
    assert_punctuation(usd)
    ok("usd version bleibt unter dem limit", len(usd) < 1990, len(usd))

    # 14 telegram-spiegel ist verdrahtet und faellt weich aus
    ok("telegram modul ist eingebunden", hasattr(telegram_post, "send_text"))
    ok("ohne secrets meldet telegram sauber False",
       telegram_post.send_text("selbsttest") is False)

    # 15 tps nur gegen dieselbe definition (reparatur 25.09.2026)
    alt = dict(GOLD_PREV, week="2026-07-27")
    neu = build_message(v, alt, 5, dt.date(2026, 8, 3), GOLD_READ)
    tps_zeile = [l for l in neu.split("\n") if l.startswith("tps ")][0]
    ok("tps ohne vergleich gegen alte definition", tps_zeile == "tps **0.91**",
       tps_zeile)
    gleich = dict(alt, tps_def=TPS_DEF)
    neu2 = build_message(v, gleich, 5, dt.date(2026, 8, 3), GOLD_READ)
    tps2 = [l for l in neu2.split("\n") if l.startswith("tps ")][0]
    ok("tps mit vergleich bei gleicher definition", "up 21.3 percent" in tps2, tps2)
    e = history_eintrag("2026-09-28", 12, {"tps": 1.47, "hashrate": 350.0})
    ok("history zeile traegt die definition", e.get("tps_def") == TPS_DEF, e)
    ok("ohne tps keine definition",
       "tps_def" not in history_eintrag("2026-09-28", 12, {"hashrate": 350.0}))

    # 16 abstand zur vorwoche (reparatur 25.09.2026)
    sep7 = dict(GOLD_PREV, week="2026-09-07", tps_def=TPS_DEF)
    lang = build_message(v, sep7, 12, dt.date(2026, 9, 28), GOLD_READ)
    ok("drei wochen abstand, kein this week", "this week" not in lang)
    ok("hashrate sagt since september 7",
       "up 30.6 percent since september 7" in lang,
       [l for l in lang.split("\n") if l.startswith("hashrate")])
    ok("alle vergleiche sagen since",
       all("since september 7" in l for l in lang.split("\n")
           if " percent" in l and ("up " in l or "down " in l)),
       [l for l in lang.split("\n") if " percent" in l])
    ok("unchanged sagt ebenfalls since",
       "unchanged since september 7" in lang)
    assert_punctuation(lang)
    ok("drei wochen bleibt unter dem limit", len(lang) < 1990, len(lang))
    ok("sieben tage bleibt this week",
       vergleich_seit({"week": "2026-09-21"}, dt.date(2026, 9, 28)) is None)
    ok("ohne vorwoche kein since", vergleich_seit(None, dt.date(2026, 9, 28)) is None)

    # 17 automatische laeufe posten nur am tag selbst (25.09.2026)
    ok("push am montag selbst geht durch",
       falsche_woche("push", "2026-09-28", "2026-09-28") is None)
    ok("termin am montag selbst geht durch",
       falsche_woche("schedule", "2026-09-28", "2026-09-28") is None)
    ok("push mit alter woche bricht ab",
       "kein post" in (falsche_woche("push", "2026-09-21", "2026-09-28") or ""))
    ok("termin mit alter woche bricht ab",
       "kein post" in (falsche_woche("schedule", "2026-09-21", "2026-09-28") or ""))
    ok("von hand gestartet bleibt frei",
       falsche_woche("workflow_dispatch", "2026-09-21", "2026-09-28") is None)
    ok("leere woche bricht ab",
       "leer" in (falsche_woche("schedule", "", "2026-09-28") or ""))
    ok("heute_berlin ist ein datum",
       bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", heute_berlin())), heute_berlin())
    alt_heute = os.environ.get("WN_HEUTE")
    os.environ["WN_HEUTE"] = "2026-09-28"
    ok("WN_HEUTE simuliert das datum", heute_berlin() == "2026-09-28")
    if alt_heute is None:
        del os.environ["WN_HEUTE"]
    else:
        os.environ["WN_HEUTE"] = alt_heute

    # 18 ops-meldung
    ok("ops nimmt die abbruchzeile",
       ops_zeile("a\nABBRUCH sprungbremse. tvl\nnode 20 is deprecated\n")
       == "ABBRUCH sprungbremse. tvl")
    ok("ops nimmt sonst die fehlerzeile",
       ops_zeile("x\nTraceback (most recent call last)\n  File y\nKeyError: 'week'\nende")
       == "KeyError: 'week'")
    ok("ops ohne log meldet das",
       ops_zeile("").startswith("kein log"))
    lp = os.path.join(tmp, "wn.log")
    with open(lp, "w", encoding="utf-8") as fh:
        fh.write("ABBRUCH sprungbremse. tvl_total springt\n")
    ok("ops ohne secret springt sauber ueber",
       ops_melden(lp, hook="", lauf="https://x/run/1", anlass="schedule") == 0)
    ok("ops ohne logdatei stuerzt nicht ab",
       ops_melden(os.path.join(tmp, "fehlt.log"), hook="") == 0)

    print("")
    if fails:
        print("%d von %d fehlgeschlagen: %s" % (len(fails), len(fails), fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    if "--ops-meldung" in sys.argv:
        i = sys.argv.index("--ops-meldung")
        pfad = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        sys.exit(ops_melden(pfad, lauf=os.environ.get("LAUF", ""),
                            anlass=os.environ.get("GITHUB_EVENT_NAME", "")))
    try:
        sys.exit(main())
    except Stop as e:
        print("ABBRUCH " + str(e))
        sys.exit(1)
