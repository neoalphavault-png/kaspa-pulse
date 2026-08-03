#!/usr/bin/env python3
"""
kaspa pulse - weekly numbers bot
--------------------------------
Baut den Montags-Post fuer #weekly-numbers.

Was der Bot SELBST holt (8 Zeilen):
  hashrate, block reward + naechster Cut, emission, tvl gesamt,
  kasplex/igra split, dex volume, chain fees, prozent gemined

Was der Bot NICHT holen kann (5 Zahlen, kommen aus data/week-input.json):
  active addresses, tps, holder-adressen  (Kaspalytics, keine API)
  dormant >1J                              (Kaspalytics, plus Handkorrektur)
  exchange balances                        (kaspa.stream, keine API)

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
import sys
import time
import urllib.error
import urllib.request

UA = "kaspa-pulse-weekly/1.0 (+https://kaspapulse.com)"
TIMEOUT = 20
RETRIES = 3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "data", "week-input.json")
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

MANUAL_KEYS = ["active_addr", "tps", "holders", "dormant_pct", "exchange_kas"]
AUTO_KEYS = [
    "hashrate", "block_reward", "emission", "mined_pct",
    "tvl_kasplex", "tvl_igra", "tvl_total", "dex_vol", "chain_fees",
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


def build_message(v, prev, issue, week_date, read, price=None, show_usd=False):
    prev = prev or {}
    out = []
    out.append("\U0001f4ca **kaspa pulse, week %d numbers**" % issue)
    out.append(month_day(week_date))
    out.append("")

    out.append("⛏️ **mining**")
    out.append("hashrate **%s PH/s**%s" % (
        fmt_num(v["hashrate"]),
        tail("hashrate", v["hashrate"], prev.get("hashrate"), " this week")))
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
        tail("active_addr", v["active_addr"], prev.get("active_addr"))))
    out.append("tps **%s**%s" % (
        fmt_num(v["tps"], 2),
        tail("tps", v["tps"], prev.get("tps"))))
    out.append("addresses holding a balance **%s**%s" % (
        fmt_int(v["holders"]),
        tail("holders", v["holders"], prev.get("holders"))))
    out.append("")

    out.append("\U0001f9f1 **layer 2**")
    out.append("total tvl **%s**%s" % (
        fmt_money(v["tvl_total"]),
        tail("tvl_total", v["tvl_total"], prev.get("tvl_total"))))
    out.append("kasplex **%s** and igra **%s**" % (
        fmt_money(v["tvl_kasplex"]), fmt_money(v["tvl_igra"])))
    out.append("dex volume **%s**%s" % (
        fmt_money(v["dex_vol"]),
        tail("dex_vol", v["dex_vol"], prev.get("dex_vol"))))
    out.append("chain fees **%s** for the day%s" % (
        fmt_money(v["chain_fees"]),
        tail("chain_fees", v["chain_fees"], prev.get("chain_fees"))))
    out.append("")

    out.append("\U0001fa99 **supply**")
    out.append("**%s percent** of all KAS already mined"
               % fmt_num(v["mined_pct"], 2))
    line = "**%s percent** has not moved in over a year" % fmt_num(v["dormant_pct"])
    dc, dtxt = delta("dormant_pct", v["dormant_pct"], prev.get("dormant_pct"))
    if SHOW_DELTA.get("dormant_pct") and dc:
        line += " %s %s" % (dc, dtxt)
    out.append(line)
    line = "exchange balances **%s**%s" % (
        fmt_kas(v["exchange_kas"]),
        tail("exchange_kas", v["exchange_kas"], prev.get("exchange_kas")))
    if show_usd and price:
        line += " worth %s" % fmt_money(v["exchange_kas"] * price)
    out.append(line)
    out.append("")

    out.append("\U0001f4a1 **the read**")
    out.append(read.strip())
    out.append("")
    out.append("\U0001f517 full dashboard kaspapulse.com")
    return "\n".join(out)


def assert_punctuation(text):
    """Schreibregel mechanisch statt aus dem Gedaechtnis."""
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

def post_discord(msg, dry=False):
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


def main():
    dry = os.environ.get("DRY_RUN", "").strip() not in ("", "0", "false")
    force = os.environ.get("FORCE", "").strip() not in ("", "0", "false")
    show_usd = os.environ.get("SHOW_USD", "").strip() not in ("", "0", "false")

    # dublettenpruefung vor der strengen pruefung. so laeuft die vorlage,
    # die noch auf der letzten woche steht, ohne roten lauf durch.
    history = load_json(HISTORY_PATH, default=[])
    peek = str(load_json(INPUT_PATH).get("week", "")).strip()
    if any(h.get("week") == peek for h in history) and not force:
        print("woche %s steht schon in der history. nichts gepostet. "
              "mit FORCE=1 starten wenn das absicht ist" % peek)
        return 0

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
                        price=price, show_usd=show_usd)
    assert_punctuation(msg)

    print(msg)
    print("---- %d zeichen ----" % len(msg))
    post_discord(msg, dry=dry)

    if not dry:
        entry = {"week": inp["week"], "issue": issue}
        for k in AUTO_KEYS + MANUAL_KEYS:
            if k in v:
                entry[k] = round(float(v[k]), 6)
        if price:
            entry["price"] = price
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
    msg = build_message(v, GOLD_PREV, 4, dt.date(2026, 8, 3), GOLD_READ)
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
    ok("eingabedatei wird gelesen", got["week"] == "2026-08-10"
       and got["manual"]["tps"] == 0.95)

    bad = json.loads(json.dumps(good))
    del bad["manual"]["holders"]
    raises("fehlende handzahl stoppt", lambda: read_input(write_input(bad)))

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

    print("")
    if fails:
        print("%d von %d fehlgeschlagen: %s" % (len(fails), len(fails), fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    try:
        sys.exit(main())
    except Stop as e:
        print("ABBRUCH " + str(e))
        sys.exit(1)
