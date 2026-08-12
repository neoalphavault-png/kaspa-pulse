#!/usr/bin/env python3
"""
kaspa pulse - number of the day, datenteil

schreibt data/number-of-day.json aus den zahlen, die die bots ohnehin rechnen.
das rendern macht danach scripts/number_of_day.py, unveraendert.

grundsatz, uebernommen aus dem renderer:
    die vergleichszahl ist der held, nicht die zahl.
jeder kandidat hier muss deshalb einen anker mitliefern. eine zahl ohne anker
wird gar nicht erst gebaut.

auswahl:
    jeder kandidat berechnet sich selbst und gibt eine punktzahl zurueck.
    der hoechste gewinnt. ein reward cut am selben tag schlaegt alles.
    was gestern oder heute schon dran war, ist hart gesperrt (nachtrag
    07.08.: die weiche abwertung reichte nicht, die zahl vom 96er-typ kam
    zweimal hintereinander). einzelne kandidaten haben eine laengere
    sperrfrist, siehe MIN_GAP, weil sie sich zu langsam bewegen fuer eine
    taegliche meldung (nachtrag 10.08.: mined_left nur noch woechentlich).
    was in den letzten COOLDOWN_DAYS tagen davor
    dran war, wird abgewertet, damit nicht dreimal die woche dieselbe
    grafik erscheint.

    nachtrag 12.08.: der notnagel hat die sperre ausgehebelt. lief an einem
    tag kein anderer kandidat, kam der gesperrte trotzdem durch, und die
    96er zahl stand sieben tage hintereinander im kanal. ab jetzt gilt die
    umgekehrte reihenfolge. ein kandidat mit eigener MIN_GAP ist absolut
    gesperrt und kommt nie als notnagel in frage. notnagel darf nur sein,
    wer unter der standardsperre steht, also eine zahl die sich taeglich
    bewegt. ist auch das leer, faellt der post an diesem tag aus. ein
    wiederholter post ist schlimmer als kein post.

lokal:
    python3 scripts/number_of_day_data.py --dry-run
    python3 scripts/number_of_day_data.py --selftest
in github actions:
    python3 scripts/number_of_day_data.py --out data/number-of-day.json
"""

import argparse
import datetime as dt
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# der renderer haelt die interpunktionsregel. wir pruefen mit derselben
# funktion, damit die grafik nie an etwas scheitert, das hier entsteht.
from number_of_day import walk_and_check  # noqa: E402

# ---------------------------------------------------------------- konstanten

# reward anker, identisch zu weekly_numbers und reward_cut_alert v3.
# wird unten gegen weekly_numbers geprueft, falls importierbar.
ANCHOR_TS = 1783280744
ANCHOR_REWARD = 2.44997148
STEP = (365.25 / 12) * 86400
R = 0.5 ** (1 / 12)
BPS = 10
DAY = 86400

# geschaetzt, block 1.050.000. steht so auch in der note, damit die schaetzung
# im bild sichtbar ist und nicht als messwert durchgeht.
BTC_HALVING_EST = dt.date(2028, 4, 16)

# bitcoin, feste protokollwerte bis zum naechsten halving.
BTC_BLOCKS_PER_DAY = 144
BTC_REWARD = 3.125

# groesste bekannte adresse, dieselbe die der alert bot beobachtet.
WHALE_ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
BALANCE_API = "https://api.kaspa.org/addresses/%s/balance"
SOMPI = 100000000

HISTORY_PATH = os.path.join(ROOT, "data", "weekly-history.json")
LOG_PATH = os.path.join(ROOT, "data", "number-of-day-log.json")
OUT_PATH = os.path.join(ROOT, "data", "number-of-day.json")

COOLDOWN_DAYS = 8
HARD_BLOCK_DAYS = 1   # standard-sperrfrist in tagen fuer alle kandidaten

# einzelne kandidaten duerfen seltener dran sein als andere. der anteil der
# geschuerften menge bewegt sich um 0.01 prozentpunkte pro tag, als taegliche
# meldung ist er deshalb wertlos und wirkt wie eine wiederholung. eine woche
# abstand macht daraus wieder eine nachricht. schluessel ist der kandidatenname,
# wert die zahl der tage, die er nach einem einsatz gesperrt bleibt.
MIN_GAP = {
    "mined_left": 7,
    "whale_weight": 7,
    "emission_vs_btc": 2,
    "blocks_per_day": 21,
}
COOLDOWN_FACTOR = 0.15
MIN_ANCHOR_AGE_DAYS = 21
LOG_KEEP = 60

# wie weit die auswahl ueberhaupt zurueckschaut. muss laenger sein als die
# laengste sperrfrist, sonst laeuft ein kandidat mit MIN_GAP 21 nach acht
# tagen wieder los, weil ihn davor niemand mehr im log findet. genau das ist
# in der simulation aufgefallen. abgewertet wird trotzdem nur innerhalb von
# COOLDOWN_DAYS, damit eine taegliche kennzahl nicht wochenlang gedrueckt wird.
LOOKBACK_DAYS = max([COOLDOWN_DAYS] + list(MIN_GAP.values())) + 1

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

UA = "kaspa-pulse-notd/1.0 (+https://kaspapulse.com)"
TIMEOUT = 20
RETRIES = 3


class Stop(Exception):
    """Abbruch mit Klartext. Lieber keine Grafik als eine falsche."""


class Skip(Exception):
    """Heute ist nichts frei. Kein Fehler, nur kein Post."""


# ---------------------------------------------------------------- netzwerk

def http_json(url, tries=RETRIES):
    import time
    import urllib.request

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


def fetch_optional(what, fn):
    """Holt eine Kuer. Faellt sie aus, faellt nur ein kandidat weg."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        print("%s nicht erreichbar (%s), der kandidat faellt heute weg"
              % (what, exc))
        return None


def fetch_prices():
    d = http_json("https://api.coingecko.com/api/v3/simple/price"
                  "?ids=kaspa,bitcoin&vs_currencies=usd", tries=2)
    kas = float(d["kaspa"]["usd"])
    btc = float(d["bitcoin"]["usd"])
    if not (0.0001 <= kas <= 100.0) or not (1000.0 <= btc <= 10000000.0):
        raise Stop("preis ausserhalb des fensters, kas %s btc %s" % (kas, btc))
    return kas, btc


def fetch_whale():
    d = http_json(BALANCE_API % WHALE_ADDRESS, tries=2)
    bal = int(d["balance"]) / SOMPI
    if bal <= 0:
        raise Stop("adressbestand ist null")
    return bal


def fetch_live():
    """Alles, was ein Kandidat brauchen kann, in einem Rutsch."""
    sup = http_json("https://api.kaspa.org/info/coinsupply")
    circ = float(sup["circulatingSupply"]) / 1e8
    mx = float(sup["maxSupply"]) / 1e8
    if mx <= 0:
        raise Stop("coinsupply liefert maxSupply 0")

    hr = http_json("https://api.kaspa.org/info/hashrate?stringOnly=false")
    hashrate = float(hr["hashrate"]) / 1000.0  # TH/s in PH/s

    tvl = {}
    try:
        for row in http_json("https://api.llama.fi/v2/chains", tries=2):
            name = str(row.get("name") or "").strip().lower()
            if name.startswith("kasplex"):
                tvl.setdefault("kasplex", float(row.get("tvl") or 0.0))
            elif name.startswith("igra"):
                tvl.setdefault("igra", float(row.get("tvl") or 0.0))
    except Stop:
        tvl = {}

    prices = fetch_optional("coingecko", fetch_prices)
    whale = fetch_optional("adressbestand", fetch_whale)

    return {
        "circ": circ,
        "max": mx,
        "mined_pct": 100.0 * circ / mx,
        "hashrate": hashrate,
        "tvl_kasplex": tvl.get("kasplex"),
        "tvl_igra": tvl.get("igra"),
        "tvl_total": (tvl.get("kasplex", 0.0) + tvl.get("igra", 0.0)) or None,
        "price_kas": prices[0] if prices else None,
        "price_btc": prices[1] if prices else None,
        "whale_kas": whale,
    }


# ---------------------------------------------------------------- rechnen

def reward_state(now_ts):
    """Aktueller Reward, naechster Reward, Zeitpunkt des naechsten Schnitts."""
    n = math.floor((now_ts - ANCHOR_TS) / STEP)
    cur = ANCHOR_REWARD * (R ** n)
    nxt_ts = ANCHOR_TS + (n + 1) * STEP
    return cur, cur * R, nxt_ts


def emission_per_day(reward):
    return reward * BPS * DAY


def months_to_share(circ, mx, reward, share):
    """
    Wie viele Monate bis `share` (z. B. 0.99) der Maximalmenge gemint ist.

    Die Emission ist eine geometrische Reihe. Pro Monat faellt sie um denselben
    Faktor R, also ist die kumulierte Menge nach n Monaten M*(1-R^n)/(1-R).
    Gibt None zurueck, wenn das Ziel nie erreicht wird.
    """
    target = share * mx
    need = target - circ
    if need <= 0:
        return 0.0
    month_days = STEP / DAY
    m = emission_per_day(reward) * month_days
    total_future = m / (1.0 - R)
    if need >= total_future:
        return None
    ratio = 1.0 - need * (1.0 - R) / m
    return math.log(ratio) / math.log(R)


def fmt_int(n):
    return "{:,}".format(int(round(float(n))))


def fmt_millions(v):
    return "%.2f million" % (float(v) / 1e6)


def fmt_kas(v):
    v = float(v)
    if v >= 1e9:
        return "%.2fB KAS" % (v / 1e9)
    if v >= 1e6:
        return "%.1fM KAS" % (v / 1e6)
    return "%s KAS" % fmt_int(v)


def fmt_money(v):
    v = float(v)
    if v >= 1e9:
        return "$%.2fB" % (v / 1e9)
    if v >= 1e6:
        return "$%.2fM" % (v / 1e6)
    if v >= 1e5:
        return "$%.0fK" % (v / 1e3)
    if v >= 1e3:
        return "$%.1fK" % (v / 1e3)
    return "$%.0f" % v


def issue_line(day):
    return "KASPA PULSE · %s %d %d" % (MONTHS[day.month - 1], day.day, day.year)


def bar_pair(a, b):
    """Zwei Balkenbreiten, der groessere immer 100."""
    a, b = abs(float(a)), abs(float(b))
    hi = max(a, b, 1e-9)
    return 100.0 * a / hi, 100.0 * b / hi


# ---------------------------------------------------------------- historie

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def anchor_entry(history, today, key):
    """
    Aeltester Eintrag, der mindestens MIN_ANCHOR_AGE_DAYS zurueckliegt und den
    gesuchten Wert hat. Ohne Anker kein Kandidat, das ist der ganze Punkt.
    """
    best = None
    for row in history or []:
        try:
            d = dt.date.fromisoformat(str(row.get("week")))
        except ValueError:
            continue
        age = (today - d).days
        if age < MIN_ANCHOR_AGE_DAYS:
            continue
        if row.get(key) in (None, 0):
            continue
        if best is None or age < best[0]:
            best = (age, d, row)
    return best  # (age_days, date, row) oder None


def age_phrase(days):
    if days >= 330:
        return "a year ago"
    if days >= 60:
        return "%d months ago" % int(round(days / 30.44))
    return "%d weeks ago" % int(round(days / 7.0))


# ---------------------------------------------------------------- posttext

# hausstil auf X: klein geschrieben, unter sechzig woertern, keine hashtags,
# hoechstens ein $KAS, kein kursziel, kein link im ersten post. der link steht
# in der selbstantwort, deshalb sind es hier immer zwei felder.
MAX_POST_WORDS = 60
HALVING_URL = "kaspapulse.com/kaspa-halving.html"
SITE_URL = "kaspapulse.com"


def post_block(text, reply):
    """Baut den X Text und prueft die eigene Laengenregel sofort."""
    text = " ".join(str(text).split())
    words = len(text.split())
    if words > MAX_POST_WORDS:
        raise ValueError("posttext hat %d woerter, erlaubt sind %d"
                         % (words, MAX_POST_WORDS))
    return {"x": text, "reply": " ".join(str(reply).split())}


# ---------------------------------------------------------------- kandidaten

def cand_cut_today(ctx):
    """Der Schnitt landet heute. Schlaegt alles andere."""
    nxt_ts = ctx["next_cut_ts"]
    cut_day = dt.datetime.fromtimestamp(nxt_ts, dt.timezone.utc).date()
    prev_ts = nxt_ts - STEP
    prev_day = dt.datetime.fromtimestamp(prev_ts, dt.timezone.utc).date()
    today = ctx["today"]

    if today == prev_day:
        landed, when = True, "this morning"
    elif today == cut_day:
        landed, when = False, "this morning"
    else:
        return None

    if landed:
        before = ctx["reward"] / R
        after = ctx["reward"]
    else:
        before = ctx["reward"]
        after = ctx["next_reward"]

    e_before = emission_per_day(before)
    e_after = emission_per_day(after)
    gone = e_before - e_after
    pct = 100.0 * (1.0 - R)

    verb = "fell" if landed else "falls"
    tail = ("from now on the network mints %s fewer KAS every day. "
            "emission dropped from %s to %s."
            % (fmt_int(gone), fmt_millions(e_before), fmt_millions(e_after)))
    if not landed:
        tail = ("today the network stops minting %s KAS per day. "
                "emission goes from %s to %s."
                % (fmt_int(gone), fmt_millions(e_before), fmt_millions(e_after)))

    return {
        "score": 1000.0,
        "payload": {
            "issue": issue_line(today),
            "eyebrow": "NUMBER OF THE DAY",
            "value": "%.2f%%" % pct,
            "value_label": "how much the kaspa block reward %s %s" % (verb, when),
            "headline": "bitcoin cuts once every *four years*.\nkaspa cuts every month.",
            "panes": [
                {
                    "kind": "compare",
                    "title": "SIZE OF ONE CUT",
                    "sub": "how much new supply disappears in a single reduction",
                    "rows": [
                        {"label": "kaspa", "sub": "every month",
                         "value": "%.2f%%" % pct, "pct": 2.0 * pct, "tone": "teal"},
                        {"label": "bitcoin", "sub": "every four years",
                         "value": "50%", "pct": 100, "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHAT THAT MEANS",
                    "lines": [
                        "twelve of those small steps land on the *same 50 percent* "
                        "bitcoin does in one. a staircase instead of a cliff.",
                        tail,
                    ],
                },
            ],
            "note": ("the amount is fixed arithmetic and cannot move. the moment "
                     "lands on a block score, not on a clock, so the minute drifts."),
            "sources": "api.kaspa.org",
            "site": "kaspapulse.com",
            "post": post_block(
                "the kaspa block reward %s %.2f percent %s. bitcoin does 50 "
                "percent once every four years. kaspa does one small step every "
                "month, and twelve of them land on the same 50 percent. the "
                "network now mints %s fewer KAS per day."
                % (verb, pct, when, fmt_int(gone)),
                "the live emission numbers are on " + HALVING_URL),
        },
    }


def cand_cut_countdown(ctx):
    """Naechster Schnitt in Sichtweite, verglichen mit dem naechsten Halving."""
    days = (ctx["next_cut_ts"] - ctx["now_ts"]) / DAY
    if days > 12 or days < 0:
        return None
    btc_days = (BTC_HALVING_EST - ctx["today"]).days
    if btc_days <= 0:
        return None

    e_now = emission_per_day(ctx["reward"])
    e_next = emission_per_day(ctx["next_reward"])
    a, b = bar_pair(days, btc_days)
    d = int(round(days))
    word = "day" if d == 1 else "days"

    return {
        "score": 60.0 + (12.0 - days) * 3.0,
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": "%d" % d,
            "value_label": "%s until the next kaspa reward cut" % word,
            "headline": "bitcoin waits *%d days*.\nkaspa cuts %d times before then."
                        % (btc_days, int(btc_days / (STEP / DAY))),
            "panes": [
                {
                    "kind": "compare",
                    "title": "TIME TO THE NEXT REDUCTION",
                    "sub": "counted from today, in days",
                    "rows": [
                        {"label": "kaspa", "sub": "monthly",
                         "value": "%d" % d, "pct": a, "tone": "teal"},
                        {"label": "bitcoin", "sub": "estimated",
                         "value": fmt_int(btc_days), "pct": b, "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHAT CHANGES",
                    "lines": [
                        "daily emission goes from %s to *%s KAS*."
                        % (fmt_millions(e_now), fmt_millions(e_next)),
                        "the block reward drops from %.4f to %.4f KAS. "
                        "same arithmetic every month, no vote, no announcement."
                        % (ctx["reward"], ctx["next_reward"]),
                    ],
                },
            ],
            "note": ("the kaspa date is arithmetic, the bitcoin date is an estimate "
                     "because it depends on how fast blocks are found."),
            "sources": "api.kaspa.org",
            "site": "kaspapulse.com",
            "post": post_block(
                "the next kaspa reward cut lands in %d %s. bitcoin waits about "
                "%s days for its next one, and kaspa cuts %d more times before "
                "that date. daily emission drops from %s to %s KAS."
                % (d, word, fmt_int(btc_days), int(btc_days / (STEP / DAY)),
                   fmt_millions(e_now), fmt_millions(e_next)),
                "the countdown runs live on " + HALVING_URL),
        },
    }


def cand_mined_left(ctx):
    """Wie viel schon gemint ist und wie lange der Rest braucht."""
    circ, mx = ctx["circ"], ctx["max"]
    pct = ctx["mined_pct"]
    n99 = months_to_share(circ, mx, ctx["reward"], 0.99)
    if n99 is None:
        return None
    when99 = ctx["today"] + dt.timedelta(days=n99 * STEP / DAY)
    left = mx - circ
    a, b = bar_pair(pct, 100.0 - pct)

    return {
        "score": 40.0,
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": "%.2f%%" % pct,
            "value_label": "of every KAS that will ever exist is already mined",
            "headline": "the supply story is *almost over*.\nthe rest takes longer than the start.",
            "panes": [
                {
                    "kind": "compare",
                    "title": "SUPPLY ALREADY ISSUED",
                    "sub": "share of the maximum, measured today",
                    "rows": [
                        {"label": "mined", "sub": "in circulation",
                         "value": "%.2f%%" % pct, "pct": a, "tone": "teal"},
                        {"label": "left", "sub": "still to come",
                         "value": "%.2f%%" % (100.0 - pct), "pct": max(2.0, b),
                         "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHAT IS LEFT",
                    "lines": [
                        "%s KAS are still unmined. that is *%.2f percent* of the maximum."
                        % (fmt_int(left), 100.0 - pct),
                        "at the current schedule 99 percent is reached in %s. "
                        "what comes after keeps halving every twelve months."
                        % when99.strftime("%B %Y").lower(),
                    ],
                },
            ],
            "note": ("emission halves every twelve months, so the remaining amount "
                     "is a shrinking series and never quite reaches the maximum."),
            "sources": "api.kaspa.org",
            "site": "kaspapulse.com",
            "post": post_block(
                "%.2f percent of every KAS that will ever exist is already mined. "
                "%s KAS are still to come, and 99 percent is reached in %s at the "
                "current schedule. what comes after keeps halving every twelve "
                "months."
                % (pct, fmt_int(left), when99.strftime("%B %Y").lower()),
                "the full emission schedule is on " + HALVING_URL),
        },
    }


def _move_candidate(ctx, key, title, unit_fmt, label, headline_word,
                    base_score, sources):
    """Gemeinsame Form fuer alle Kandidaten, die gegen die Historie messen."""
    hist = anchor_entry(ctx["history"], ctx["today"], key)
    now = ctx.get(key)
    if hist is None or now in (None, 0):
        return None
    age, _, row = hist
    then = float(row[key])
    if then <= 0:
        return None

    change = 100.0 * (now - then) / then
    if abs(change) < 5.0:
        return None
    a, b = bar_pair(now, then)
    direction = "up" if change > 0 else "down"

    return {
        "score": base_score + min(40.0, abs(change)),
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": unit_fmt(now),
            "value_label": label,
            "headline": "%s is *%s %.0f percent*\nagainst %s."
                        % (headline_word, direction, abs(change), age_phrase(age)),
            "panes": [
                {
                    "kind": "compare",
                    "title": title,
                    "sub": "same measurement, two dates",
                    "rows": [
                        {"label": "today", "sub": "",
                         "value": unit_fmt(now), "pct": a,
                         "tone": "teal" if change > 0 else "red"},
                        {"label": age_phrase(age), "sub": "",
                         "value": unit_fmt(then), "pct": b, "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHAT THE NUMBER IS",
                    "lines": [
                        "the difference between the two readings is *%s*."
                        % unit_fmt(abs(now - then)),
                        "both values come from the same source, read the same way, "
                        "%d days apart." % age,
                        "we report the movement, *never the motive*.",
                    ],
                },
            ],
            "note": ("the anchor is the weekly reading we archived, not a chart "
                     "high. that is why the comparison holds."),
            "sources": sources,
            "site": "kaspapulse.com",
            "post": post_block(
                "%s on kaspa is %s %.0f percent against %s. %s today, %s then, "
                "both read from the same source %d days apart. we report the "
                "movement, never the motive."
                % (headline_word, direction, abs(change), age_phrase(age),
                   unit_fmt(now), unit_fmt(then), age),
                "the weekly readings behind that are on " + SITE_URL),
        },
    }


def cand_hashrate_move(ctx):
    return _move_candidate(
        ctx, "hashrate", "NETWORK HASHRATE",
        lambda v: "%.0f PH" % float(v),
        "petahash per second securing the network right now",
        "hashrate", 30.0, "api.kaspa.org")


def cand_tvl_move(ctx):
    return _move_candidate(
        ctx, "tvl_total", "TOTAL VALUE LOCKED",
        fmt_money,
        "locked across kasplex and igra",
        "layer 2 tvl", 28.0, "defillama.com")


def cand_emission_vs_btc(ctx):
    """Wie viel neues geld beide netze pro tag drucken, in dollar."""
    pk, pb = ctx.get("price_kas"), ctx.get("price_btc")
    if not pk or not pb:
        return None

    kas_day = emission_per_day(ctx["reward"])
    btc_day = BTC_REWARD * BTC_BLOCKS_PER_DAY
    usd_kas = kas_day * pk
    usd_btc = btc_day * pb
    if usd_kas <= 0 or usd_btc <= 0:
        return None
    times = usd_btc / usd_kas
    a, b = bar_pair(usd_kas, usd_btc)

    return {
        "score": 42.0,
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": fmt_money(usd_kas),
            "value_label": "of brand new kaspa supply is created every day",
            "headline": "bitcoin prints *%.0f times* more\nnew supply every single day." % times,
            "panes": [
                {
                    "kind": "compare",
                    "title": "NEW SUPPLY PER DAY",
                    "sub": "issuance valued at today's spot price",
                    "rows": [
                        {"label": "kaspa", "sub": fmt_millions(kas_day) + " KAS",
                         "value": fmt_money(usd_kas), "pct": a, "tone": "teal"},
                        {"label": "bitcoin", "sub": "%.0f BTC" % btc_day,
                         "value": fmt_money(usd_btc), "pct": b, "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHY THAT GAP CLOSES",
                    "lines": [
                        "kaspa cuts its reward *twelve times a year*. bitcoin "
                        "cuts once every four years.",
                        "the dollar figure moves with the price, the coin "
                        "figure does not. only one of the two is a decision.",
                    ],
                },
            ],
            "note": ("bitcoin issuance is fixed at 3.125 coins per block and "
                     "about 144 blocks a day until the next halving."),
            "sources": "api.kaspa.org and coingecko.com",
            "site": "kaspapulse.com",
            "post": post_block(
                "kaspa creates about %s of new supply per day. bitcoin creates "
                "%s, roughly %.0f times more. kaspa cuts its reward twelve "
                "times a year and bitcoin once every four years, so that gap "
                "narrows every month without anyone voting on it."
                % (fmt_money(usd_kas), fmt_money(usd_btc), times),
                "the full emission schedule is on " + HALVING_URL),
        },
    }


def cand_whale_weight(ctx):
    """Die groesste bekannte adresse, gemessen in tagen netzwerkleistung."""
    whale = ctx.get("whale_kas")
    circ = ctx.get("circ")
    if not whale or not circ:
        return None

    share = 100.0 * whale / circ
    per_day = emission_per_day(ctx["reward"])
    days = whale / per_day
    rest = circ - whale
    a, b = bar_pair(whale, rest)

    return {
        "score": 44.0,
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": "%.2f%%" % share,
            "value_label": "of every kaspa in circulation sits in one address",
            "headline": "one address holds *%d days*\nof the entire network output." % round(days),
            "panes": [
                {
                    "kind": "compare",
                    "title": "THE LARGEST KNOWN ADDRESS",
                    "sub": "balance against everything else in circulation",
                    "rows": [
                        {"label": "one address", "sub": "",
                         "value": fmt_kas(whale), "pct": max(2.0, a),
                         "tone": "teal"},
                        {"label": "everyone else", "sub": "",
                         "value": fmt_kas(rest), "pct": b, "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "HOW LONG THAT TAKES TO MINE",
                    "lines": [
                        "at today's emission the whole network needs *%d days* "
                        "to produce that many coins." % round(days),
                        "the address has never been named and we will not "
                        "guess. we report *what it does*, never who it is.",
                    ],
                },
            ],
            "note": ("an address is not a person. one owner can hold many "
                     "addresses and an exchange can hold coins for thousands."),
            "sources": "api.kaspa.org",
            "site": "kaspapulse.com",
            "post": post_block(
                "one address holds %.2f percent of every kaspa in circulation, "
                "about %s. at the current emission rate the entire network "
                "needs %d days to mine that much. it has never been named. we "
                "report what it does, never who it is."
                % (share, fmt_kas(whale), round(days)),
                "every move that wallet makes is on kaspapulse.com/entity-x.html"),
        },
    }


def cand_blocks_per_day(ctx):
    """Der evergreen. Selten, weil er sich nie aendert."""
    kas_blocks = BPS * DAY
    times = kas_blocks / float(BTC_BLOCKS_PER_DAY)
    a, b = bar_pair(kas_blocks, BTC_BLOCKS_PER_DAY)

    return {
        "score": 20.0,
        "payload": {
            "issue": issue_line(ctx["today"]),
            "eyebrow": "NUMBER OF THE DAY",
            "value": fmt_int(kas_blocks),
            "value_label": "blocks the kaspa network produces every single day",
            "headline": "bitcoin finds *144 blocks*.\nkaspa finds %s." % fmt_int(kas_blocks),
            "panes": [
                {
                    "kind": "compare",
                    "title": "BLOCKS IN TWENTY FOUR HOURS",
                    "sub": "protocol target, not an average of a good day",
                    "rows": [
                        {"label": "kaspa", "sub": "ten per second",
                         "value": fmt_int(kas_blocks), "pct": a, "tone": "teal"},
                        {"label": "bitcoin", "sub": "one per ten minutes",
                         "value": "%d" % BTC_BLOCKS_PER_DAY, "pct": max(2.0, b),
                         "tone": "grey"},
                    ],
                },
                {
                    "kind": "anchor",
                    "title": "WHY IT DOES NOT COLLAPSE",
                    "lines": [
                        "that is *%s times* more blocks in the same day."
                        % fmt_int(times),
                        "blocks found at the same moment are not thrown away. "
                        "they are *ordered and kept*, which is the part most "
                        "comparisons leave out.",
                    ],
                },
            ],
            "note": ("the block rate is a protocol constant. the number of "
                     "coins per block is what shrinks, not the number of blocks."),
            "sources": "api.kaspa.org",
            "site": "kaspapulse.com",
            "post": post_block(
                "kaspa produces %s blocks a day. bitcoin produces about 144. "
                "ten every second against one every ten minutes. blocks found "
                "at the same moment are not discarded, they are ordered and "
                "kept, and that is the part most comparisons leave out."
                % fmt_int(kas_blocks),
                "how that ordering works is explained on " + SITE_URL),
        },
    }


CANDIDATES = [
    ("cut_today", cand_cut_today),
    ("cut_countdown", cand_cut_countdown),
    ("whale_weight", cand_whale_weight),
    ("emission_vs_btc", cand_emission_vs_btc),
    ("mined_left", cand_mined_left),
    ("hashrate_move", cand_hashrate_move),
    ("tvl_move", cand_tvl_move),
    ("blocks_per_day", cand_blocks_per_day),
]


# ---------------------------------------------------------------- auswahl

def recent_picks(log, today, window=None):
    window = LOOKBACK_DAYS if window is None else window
    out = {}
    for row in log or []:
        try:
            d = dt.date.fromisoformat(str(row.get("date")))
        except ValueError:
            continue
        age = (today - d).days
        if 0 <= age < window:
            name = row.get("candidate")
            if name and (name not in out or age < out[name]):
                out[name] = age
    return out


def choose(ctx, log, force=None):
    cooled = recent_picks(log, ctx["today"])
    scored = []   # waehlbar
    spare = []    # nur standardsperre, darf im notfall einspringen
    locked = []   # eigene MIN_GAP, kommt heute unter keinen umstaenden dran
    for name, fn in CANDIDATES:
        try:
            res = fn(ctx)
        except Exception as exc:  # noqa: BLE001
            print("kandidat %s uebersprungen (%s)" % (name, exc))
            continue
        if not res:
            continue
        score = float(res["score"])
        note = ""
        age = cooled.get(name)
        gap = MIN_GAP.get(name, HARD_BLOCK_DAYS)
        if age is not None and name != "cut_today":
            if age <= gap:
                row = (score, name, res["payload"],
                       " (gesperrt bis tag %d, vor %d tagen dran)"
                       % (gap + 1, age))
                # der unterschied, der die 96er zahl sieben tage lang
                # durchgelassen hat. wer eine eigene sperrfrist hat, bewegt
                # sich zu langsam fuer eine wiederholung und bleibt heute
                # draussen, auch wenn sonst gar nichts da ist. wer nur unter
                # der standardsperre steht, aendert sich taeglich und darf
                # zur not einspringen.
                (locked if gap > HARD_BLOCK_DAYS else spare).append(row)
                continue
            if age < COOLDOWN_DAYS:
                score *= COOLDOWN_FACTOR
                note = " (abgewertet, vor %d tagen dran)" % age
        scored.append((score, name, res["payload"], note))

    for bucket in (scored, spare, locked):
        bucket.sort(key=lambda x: (-x[0], x[1]))
    shown = scored + spare + locked

    if force:
        for s, name, payload, note in shown:
            if name == force:
                return name, payload, shown
        raise Stop("kandidat %s hat heute keine zahlen" % force)

    pool = scored or spare
    if not pool:
        if locked:
            raise Skip("alle kandidaten mit zahlen stehen noch in ihrer "
                       "sperrfrist (%s). heute faellt der post aus, das ist "
                       "besser als dieselbe zahl zweimal"
                       % ", ".join(n for _, n, _, _ in locked))
        raise Stop("kein kandidat hat zahlen geliefert")
    return pool[0][1], pool[0][2], shown


# ---------------------------------------------------------------- hauptlauf

def build_context(now_ts=None, live=None, history=None):
    now_ts = now_ts if now_ts is not None else dt.datetime.now(dt.timezone.utc).timestamp()
    today = dt.datetime.fromtimestamp(now_ts, dt.timezone.utc).date()
    reward, nxt, nxt_ts = reward_state(now_ts)
    live = live if live is not None else fetch_live()
    ctx = {
        "now_ts": now_ts,
        "today": today,
        "reward": reward,
        "next_reward": nxt,
        "next_cut_ts": nxt_ts,
        "history": history if history is not None else load_json(HISTORY_PATH, []),
    }
    ctx.update(live)
    return ctx


LOG_READINGS = ["hashrate", "tvl_total", "mined_pct", "price_kas", "whale_kas"]


def append_log(log, name, ctx=None):
    """
    Schreibt die auswahl fort und legt die tagesmesswerte daneben.

    die messwerte braucht heute noch niemand. sie bauen die taegliche reihe
    auf, gegen die die vergleichskandidaten spaeter messen koennen, ohne auf
    die woechentliche historie angewiesen zu sein. genau die luecke hat den
    kandidatenpool im august auf einen einzigen eintrag schrumpfen lassen.
    """
    entry = {"date": str(dt.datetime.now(dt.timezone.utc).date()),
             "candidate": name}
    for key in LOG_READINGS:
        val = (ctx or {}).get(key)
        if val is not None:
            entry[key] = round(float(val), 6)
    log = (log or []) + [entry]
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log[-LOG_KEEP:], f, ensure_ascii=False, indent=2)
        f.write("\n")
    return log


def write_out(path, payload, name, log, ctx=None):
    walk_and_check(payload)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    append_log(log, name, ctx)


def set_output(key, value):
    """Sagt dem workflow bescheid, ob heute etwas zu rendern ist."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("%s=%s\n" % (key, value))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--force", default=None, help="kandidat erzwingen")
    ap.add_argument("--dry-run", action="store_true",
                    help="nur zeigen, welcher kandidat gewinnt")
    args = ap.parse_args()

    log = load_json(LOG_PATH, [])

    # der nachzuegler um 09.42 utc laeuft, wenn github den ersten start
    # verschluckt hat. hat sich der erste lauf heute bewusst zurueckgehalten,
    # soll der zweite nicht dieselbe pruefung nochmal fahren. den erfolgsfall
    # faengt die png-sperre im workflow ab.
    today = str(dt.datetime.now(dt.timezone.utc).date())
    if any(r.get("date") == today and r.get("candidate") == "none"
           for r in log or []):
        print("heute wurde schon entschieden, kein post. nichts zu tun")
        set_output("picked", "0")
        return 0

    ctx = build_context()
    try:
        name, payload, scored = choose(ctx, log, force=args.force)
    except Skip as exc:
        print("kein post heute. " + str(exc))
        set_output("picked", "0")
        if not args.dry_run:
            # der leerlauf wird trotzdem vermerkt, sonst sieht man spaeter
            # nicht, dass der bot lief und sich bewusst zurueckgehalten hat.
            append_log(log, "none", ctx)
        return 0

    print("kandidaten heute")
    for s, n, _, note in scored:
        mark = "-> " if n == name else "   "
        print("%s%-16s %6.1f%s" % (mark, n, s, note))

    if args.dry_run:
        walk_and_check(payload)
        print("")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    write_out(args.out, payload, name, log, ctx)
    set_output("picked", "1")
    print("")
    print("geschrieben %s (%s)" % (args.out, name))
    return 0


# ---------------------------------------------------------------- selbsttest

FAKE_LIVE = {
    "circ": 27616143000.0,
    "max": 28704026601.0,
    "mined_pct": 96.21,
    "hashrate": 342.5,
    "tvl_kasplex": 342947.0,
    "tvl_igra": 1490000.0,
    "tvl_total": 1832947.0,
    "price_kas": 0.0264,
    "price_btc": 118000.0,
    "whale_kas": 1437000000.0,
}

# nur das, was api.kaspa.org auch bei ausfall aller kuerquellen liefert.
# damit laesst sich der schlimmste fall pruefen, ein pool aus lauter
# langsamen kandidaten.
FAKE_LIVE_BARE = {
    "circ": 27616143000.0,
    "max": 28704026601.0,
    "mined_pct": 96.21,
    "hashrate": 342.5,
    "tvl_kasplex": None,
    "tvl_igra": None,
    "tvl_total": None,
    "price_kas": None,
    "price_btc": None,
    "whale_kas": None,
}

FAKE_HISTORY = [
    {"week": "2026-06-01", "hashrate": 250.0, "tvl_total": 900000.0},
    {"week": "2026-08-03", "hashrate": 342.5, "tvl_total": 1832947.0},
]


def run_selftest():
    fails = []

    def ok(what, cond, extra=""):
        if cond:
            print("  ok   %s" % what)
        else:
            fails.append(what)
            print("  FEHL %s %s" % (what, extra))

    print("reward arithmetik")
    r, nxt, nxt_ts = reward_state(ANCHOR_TS + 10)
    ok("anker liefert den ankerreward", abs(r - ANCHOR_REWARD) < 1e-9, r)
    ok("schnittgroesse ist 5.61 prozent",
       abs(100.0 * (1 - R) - 5.6126) < 0.001, 100.0 * (1 - R))
    ok("emission passt zur historie",
       abs(emission_per_day(ANCHOR_REWARD) - 2116775.35) < 1.0,
       emission_per_day(ANCHOR_REWARD))
    gone = emission_per_day(ANCHOR_REWARD) - emission_per_day(ANCHOR_REWARD * R)
    ok("wegfallende tagesmenge ist 118.805", abs(gone - 118805) < 2.0, gone)

    print("kandidat am schnitttag")
    ctx = build_context(now_ts=ANCHOR_TS + STEP - 3600,
                        live=FAKE_LIVE, history=FAKE_HISTORY)
    res = cand_cut_today(ctx)
    ok("schnitttag feuert", res is not None)
    if res:
        walk_and_check(res["payload"])
        ok("wert ist die schnittgroesse", res["payload"]["value"] == "5.61%",
           res["payload"]["value"])
        ok("schnitttag schlaegt alles", res["score"] >= 1000)

    print("kandidat countdown")
    ctx = build_context(now_ts=ANCHOR_TS + STEP - 5 * DAY,
                        live=FAKE_LIVE, history=FAKE_HISTORY)
    res = cand_cut_countdown(ctx)
    ok("countdown feuert fuenf tage vorher", res is not None)
    if res:
        walk_and_check(res["payload"])
        ok("countdown zeigt fuenf", res["payload"]["value"] == "5",
           res["payload"]["value"])
    far = build_context(now_ts=ANCHOR_TS + 3 * DAY,
                        live=FAKE_LIVE, history=FAKE_HISTORY)
    ok("countdown schweigt weit vorher", cand_cut_countdown(far) is None)

    print("kandidat restmenge")
    res = cand_mined_left(far)
    ok("restmenge feuert", res is not None)
    if res:
        walk_and_check(res["payload"])
        ok("restmenge nennt den messwert", res["payload"]["value"] == "96.21%",
           res["payload"]["value"])

    print("kandidaten gegen die historie")
    res = cand_hashrate_move(far)
    ok("hashrate vergleicht gegen den alten anker", res is not None)
    if res:
        walk_and_check(res["payload"])
        rows = res["payload"]["panes"][0]["rows"]
        ok("heutiger wert steht zuerst", rows[0]["label"] == "today")
        ok("anker ist nicht der eintrag von heute",
           "342" not in rows[1]["value"], rows[1]["value"])
    flat = build_context(now_ts=ANCHOR_TS + 3 * DAY, live=FAKE_LIVE,
                         history=[{"week": "2026-06-01", "hashrate": 340.0}])
    ok("kleine bewegung feuert nicht", cand_hashrate_move(flat) is None)
    young = build_context(now_ts=ANCHOR_TS + 3 * DAY, live=FAKE_LIVE,
                          history=[{"week": "2026-08-03", "hashrate": 100.0}])
    ok("zu junger anker feuert nicht", cand_hashrate_move(young) is None)

    print("auswahl und cooldown")
    name, payload, scored = choose(far, [])
    # im fixture verdoppelt sich der tvl, die hashrate steigt um 37 prozent.
    # die groessere bewegung muss gewinnen, nicht die gewohnheit.
    ok("ohne schnitt gewinnt die groesste bewegung", name == "tvl_move", name)
    ok("die ruhige kennzahl verliert",
       [n for _, n, _, _ in scored].index("mined_left") > 1,
       [n for _, n, _, _ in scored])
    log = [{"date": str(far["today"]), "candidate": "tvl_move"}]
    name2, _, _ = choose(far, log)
    ok("was gestern lief, gewinnt heute nicht", name2 != "tvl_move", name2)
    log2 = log + [{"date": str(far["today"]), "candidate": name2}]
    name2b, _, _ = choose(far, log2)
    ok("auch der zweitplatzierte wiederholt sich nicht",
       name2b not in ("tvl_move", name2), name2b)
    gap_log = [{"date": str(far["today"] - dt.timedelta(days=3)),
                "candidate": "mined_left"}]
    name_gap, _, _ = choose(far, gap_log)
    ok("langsame kennzahl bleibt auch nach 3 tagen gesperrt",
       name_gap != "mined_left", name_gap)
    gap_log8 = [{"date": str(far["today"] - dt.timedelta(days=8)),
                 "candidate": "mined_left"}]
    others_out = [{"date": str(far["today"]), "candidate": n}
                  for n, _ in CANDIDATES if n != "mined_left"]
    name_free, _, _ = choose(far, gap_log8 + others_out)
    ok("nach 8 tagen ist die langsame kennzahl wieder waehlbar",
       name_free == "mined_left", name_free)
    ok("das rueckblickfenster ist laenger als die laengste sperre",
       LOOKBACK_DAYS > max(MIN_GAP.values()), LOOKBACK_DAYS)
    all_blocked = [{"date": str(far["today"]), "candidate": n}
                   for n, _ in CANDIDATES]
    name2c, _, _ = choose(far, all_blocked)
    ok("sind alle gesperrt, springt eine taegliche kennzahl ein",
       bool(name2c), name2c)
    ok("der notnagel ist nie eine langsame kennzahl",
       name2c not in MIN_GAP, name2c)

    print("die regel, an der die 96er zahl gescheitert ist")
    # nur langsame kandidaten haben zahlen, und alle stehen in ihrer sperre.
    # frueher lief dann der gesperrte trotzdem. jetzt faellt der post aus.
    bare = build_context(now_ts=ANCHOR_TS + 3 * DAY,
                         live=FAKE_LIVE_BARE, history=[])
    bare_names = [n for n, fn in CANDIDATES if fn(bare)]
    ok("im magerfall bleiben nur langsame kandidaten uebrig",
       bare_names and all(n in MIN_GAP for n in bare_names), bare_names)
    bare_log = [{"date": str(bare["today"]), "candidate": n}
                for n in bare_names]
    skipped = False
    try:
        choose(bare, bare_log)
    except Skip as exc:
        skipped = True
        print("  ok   der post faellt aus statt sich zu wiederholen (%s)"
              % str(exc)[:52])
    except Stop as exc:
        print("  FEHL falscher abbruchtyp %s" % exc)
    ok("gesperrte langsame kennzahl kommt nicht mehr durch", skipped)
    # und einen tag nach ablauf der sperre ist sie wieder da
    freed = [{"date": str(bare["today"] - dt.timedelta(days=8)),
              "candidate": n} for n in bare_names]
    name_freed, _, _ = choose(bare, freed)
    ok("nach ablauf der sperrfrist laeuft sie wieder",
       name_freed == "mined_left", name_freed)

    print("neue kandidaten")
    for n in ("whale_weight", "emission_vs_btc", "blocks_per_day"):
        fn = dict(CANDIDATES)[n]
        r = fn(far)
        ok("%s liefert zahlen" % n, r is not None)
        if r:
            walk_and_check(r["payload"])
    ok("ohne preise schweigt der bitcoin vergleich",
       cand_emission_vs_btc(bare) is None)
    ok("ohne adressbestand schweigt die walzahl",
       cand_whale_weight(bare) is None)
    w = cand_whale_weight(far)
    if w:
        ok("die walzahl nennt den anteil",
           w["payload"]["value"].endswith("%"), w["payload"]["value"])
    e = cand_emission_vs_btc(far)
    if e:
        ok("der bitcoin vergleich nennt einen tageswert",
           e["payload"]["value"].startswith("$"), e["payload"]["value"])
    cut_ctx = build_context(now_ts=ANCHOR_TS + STEP - 3600,
                            live=FAKE_LIVE, history=FAKE_HISTORY)
    name3, _, _ = choose(cut_ctx, [{"date": str(cut_ctx["today"]),
                                    "candidate": "cut_today"}])
    ok("der schnitttag ignoriert den cooldown", name3 == "cut_today", name3)

    print("interpunktion")
    for n, fn in CANDIDATES:
        for c in (far, cut_ctx):
            r = fn(c)
            if r:
                try:
                    walk_and_check(r["payload"])
                except ValueError as exc:
                    fails.append("interpunktion %s" % n)
                    print("  FEHL interpunktion %s %s" % (n, exc))
    ok("alle kandidaten halten die zeichenregel",
       not [f for f in fails if f.startswith("interpunktion")])

    print("posttexte")
    seen_posts = 0
    bad = []
    cd_ctx = build_context(now_ts=ANCHOR_TS + STEP - 5 * DAY,
                           live=FAKE_LIVE, history=FAKE_HISTORY)
    for n, fn in CANDIDATES:
        for c in (far, cut_ctx, cd_ctx):
            r = fn(c)
            if not r:
                continue
            p = r["payload"].get("post")
            if not p or not p.get("x") or not p.get("reply"):
                bad.append("%s ohne posttext" % n)
                continue
            seen_posts += 1
            x = p["x"]
            if len(x.split()) > MAX_POST_WORDS:
                bad.append("%s zu lang" % n)
            if "#" in x:
                bad.append("%s hat ein hashtag" % n)
            if x.count("$KAS") > 1:
                bad.append("%s nennt $KAS mehrfach" % n)
            if "kaspapulse.com" in x:
                bad.append("%s hat den link im ersten post" % n)
            if x[:1].isupper():
                bad.append("%s faengt gross an" % n)
            if "kaspapulse.com" not in p["reply"]:
                bad.append("%s hat keinen link in der antwort" % n)
    ok("jeder kandidat liefert einen posttext", seen_posts >= len(CANDIDATES))
    ok("posttexte halten den hausstil", not bad, bad)

    print("")
    if fails:
        print("%d fehlgeschlagen %s" % (len(fails), fails))
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
