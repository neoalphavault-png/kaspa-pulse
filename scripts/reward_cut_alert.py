#!/usr/bin/env python3
# Kaspa Pulse - Reward Cut Alert v3
# Ablageort im Repo: scripts/reward_cut_alert.py
#
# Kaspa halbiert nicht alle vier Jahre, sondern jeden Monat ein Stueck.
# Der Zeitpunkt ist deterministisch, wir muessen ihn also nicht suchen,
# wir rechnen ihn aus einem Anker vor. Die API /info/blockreward ist
# veraltet und wird bewusst NICHT benutzt.
#
# Neu gegenueber v2:
#   1. EMBEDS statt Textwand, violett fuer Protokoll-Ereignisse. Damit ist
#      im Kanal auf einen Blick klar, dass es nicht um eine Wallet geht.
#   2. DOLLARWERTE. Gleiche Preis-Fallback-Kette wie die Entity-X-Bots.
#   3. VORWARNUNG 24 STUNDEN VORHER. Der Kanal sagt Bescheid, bevor es
#      passiert, nicht erst danach. Das ist der halbe Wert der Sache.
#   4. PUNKTLANDUNG. Faellt der Cut in die naechsten 15 Minuten, wartet der
#      Job bis zur Sekunde und postet dann. Kein Warten auf den naechsten Lauf.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import sys
import time
import urllib.request

# ---------------------------------------------------------------------------
# Anker. Ein bekannter, verifizierter Cut. Alles andere wird vorgerollt.
# 05.07.2026 19:45:44 UTC, Reward danach 2.44997148 KAS pro Block.
# ---------------------------------------------------------------------------
ANCHOR_TS = 1783280744
ANCHOR_REWARD = 2.44997148
STEP = (365.25 / 12) * 86400          # ein Monat im Kaspa-Sinn
RATIO = 0.5 ** (1 / 12)               # zwoelf Schritte ergeben eine Halbierung
BPS = 10                              # Bloecke pro Sekunde seit Crescendo

API_SUPPLY = "https://api.kaspa.org/info/coinsupply"
STATE_FILE = "scripts/reward_cut_state.json"
SOMPI = 100_000_000
MAX_SUPPLY_FALLBACK = 28_704_026_601.0

PURPLE = 0x8B5CF6   # der Cut selbst
BLUE = 0x5B8DEF     # die Vorwarnung
PRE_WARN_SECONDS = 24 * 3600
SLEEP_MAX = 900     # bis zu 15 Minuten auf die Punktlandung warten

PRICE_MIN = 0.0001
PRICE_MAX = 100.0
UA = {"User-Agent": "kaspapulse-rewardcut/3.0"}


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# Preis. Kraken zuerst, echtes USD-Paar und freundlich zu Rechenzentrums-IPs.
# CoinGecko hinten, weil die Gratisstufe Cloud-IPs gerne abweist.
# Binance fehlt bewusst, die sperren US-IPs und Runner stehen meist in den USA.
# ---------------------------------------------------------------------------
def _p_kraken():
    d = get_json("https://api.kraken.com/0/public/Ticker?pair=KASUSD", timeout=12)
    for entry in (d.get("result") or {}).values():
        return float(entry["c"][0])
    raise ValueError("kraken ohne result")


def _p_kucoin():
    d = get_json(
        "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=KAS-USDT",
        timeout=12,
    )
    return float(d["data"]["price"])


def _p_bybit():
    d = get_json(
        "https://api.bybit.com/v5/market/tickers?category=spot&symbol=KASUSDT",
        timeout=12,
    )
    return float(d["result"]["list"][0]["lastPrice"])


def _p_mexc():
    d = get_json("https://api.mexc.com/api/v3/ticker/price?symbol=KASUSDT", timeout=12)
    return float(d["price"])


def _p_coingecko():
    d = get_json(
        "https://api.coingecko.com/api/v3/simple/price?ids=kaspa&vs_currencies=usd",
        timeout=12,
    )
    return float(d["kaspa"]["usd"])


PRICE_SOURCES = [
    ("kraken", _p_kraken),
    ("kucoin", _p_kucoin),
    ("bybit", _p_bybit),
    ("mexc", _p_mexc),
    ("coingecko", _p_coingecko),
]


def fetch_price_usd():
    for name, fn in PRICE_SOURCES:
        try:
            p = fn()
            if PRICE_MIN < p < PRICE_MAX:
                print(f"preis {p} von {name}")
                return p
            print(f"WARN {name} lieferte unplausible {p}", file=sys.stderr)
        except Exception as e:
            print(f"WARN preisquelle {name} fehlgeschlagen: {e}", file=sys.stderr)
    print("WARN keine preisquelle erreichbar, nachricht geht ohne dollarwert raus",
          file=sys.stderr)
    return None


def fetch_supply():
    """Gibt (circulating, max) zurueck. Faellt still auf None zurueck."""
    try:
        d = get_json(API_SUPPLY)
        circ = int(d["circulatingSupply"]) / SOMPI
        mx = float(d.get("maxSupply", 0)) / SOMPI or MAX_SUPPLY_FALLBACK
        return circ, mx
    except Exception as e:
        print(f"WARN supply nicht abrufbar: {e}", file=sys.stderr)
        return None, None


# ---------------------------------------------------------------------------
# Zeitplan
# ---------------------------------------------------------------------------
def schedule(now=None):
    """Liefert (naechster_cut_ts, reward_davor, reward_danach)."""
    now = now if now is not None else time.time()
    n = 0
    while ANCHOR_TS + STEP * (n + 1) <= now:
        n += 1
    # n = Anzahl vollendeter Schritte seit dem Anker
    current = ANCHOR_REWARD * RATIO ** n
    next_ts = ANCHOR_TS + STEP * (n + 1)
    nxt = ANCHOR_REWARD * RATIO ** (n + 1)
    return next_ts, current, nxt


def load_state():
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_embed(title, description, color, price=None):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    foot = "kaspa pulse · emission schedule · kaspapulse.com/kaspa-halving.html"
    if price:
        foot = (f"kaspa pulse · emission schedule · KAS at {fmt_price(price)} · "
                "kaspapulse.com/kaspa-halving.html")
    payload = {"embeds": [{
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": foot},
    }]}
    if os.environ.get("DRY_RUN"):
        print("DRY_RUN payload:\n" + json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if not url:
        print("ERROR: DISCORD_WEBHOOK secret fehlt", file=sys.stderr)
        sys.exit(1)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **UA},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def fmt(n):
    return f"{n:,.0f}"


def fmt_price(p):
    return f"${p:,.4f}" if p < 1 else f"${p:,.2f}"


def fmt_usd(v):
    a = abs(v)
    if a >= 1_000_000_000:
        return f"${v/1_000_000_000:,.2f}B"
    if a >= 1_000_000:
        return f"${v/1_000_000:,.1f}M"
    if a >= 10_000:
        return f"${v/1_000:,.0f}K"
    if a >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.0f}"


def daily(reward):
    return reward * BPS * 86400


def utc_str(ts):
    return time.strftime("%d %B %Y at %H:%M UTC", time.gmtime(ts))


def context_lines(reward_after, price):
    """Taegliche Emission und Jahresausgabe. Faellt weg, was nicht da ist."""
    lines = []
    d_now = daily(reward_after / RATIO)
    d_new = daily(reward_after)
    drop = d_now - d_new
    usd = f", about {fmt_usd(drop * price)} at today's price" if price else ""
    lines.append(
        f"daily issuance falls from **{fmt(d_now)} KAS** to **{fmt(d_new)} KAS**. "
        f"that is {fmt(drop)} fewer coins every single day{usd}."
    )
    circ, mx = fetch_supply()
    if circ and mx and mx > circ:
        yearly = (mx - circ) / 2
        yusd = f" and worth **{fmt_usd(yearly * price)}** at today's price" if price else ""
        lines.append(
            f"over the next twelve months the network will issue about "
            f"**{fmt(yearly)} KAS**, roughly **{yearly / circ * 100:.2f} percent** "
            f"of what exists today{yusd}."
        )
    return "\n".join(lines)


def announce_cut(before, after, ts, price):
    pct = (1 - after / before) * 100
    send_embed(
        "🟣 kaspa just cut its block reward",
        f"the reward dropped from **{before:.8f} KAS** to **{after:.8f} KAS** per block, "
        f"a cut of **{pct:.2f} percent**.\n"
        f"{context_lines(after, price)}\n\n"
        "kaspa does this every month instead of once every four years. "
        "no cliff, no shock, just a smaller number every thirty days. "
        f"the next cut lands on {utc_str(schedule(ts + 60)[0])}.",
        PURPLE, price=price,
    )


def announce_prewarn(before, after, ts, price):
    pct = (1 - after / before) * 100
    send_embed(
        "🔵 heads up. the next reward cut is one day away",
        f"on {utc_str(ts)} the block reward drops from **{before:.8f} KAS** "
        f"to **{after:.8f} KAS**, a cut of **{pct:.2f} percent**.\n"
        f"{context_lines(after, price)}\n\n"
        "this is not a prediction, it is arithmetic. "
        "the schedule was fixed when the chain launched and it has never moved.",
        BLUE, price=price,
    )


def main():
    now = time.time()
    next_ts, before, after = schedule(now)
    state = load_state()
    wrote = False

    # 1. Punktlandung. Der Cut kommt gleich, wir warten ihn ab.
    wait = next_ts - now
    if 0 < wait <= SLEEP_MAX:
        print(f"cut in {wait:.0f} sekunden, warte auf die punktlandung")
        time.sleep(wait + 2)
        now = time.time()
        next_ts, before, after = schedule(now)

    # 2. Ist ein Cut faellig, der noch nicht gemeldet wurde?
    #    schedule() liefert nach dem Cut bereits den naechsten Termin, also
    #    rechnen wir den gerade vergangenen zurueck.
    last_ts = next_ts - STEP
    if now >= last_ts and state.get("announced_cut_ts") != int(last_ts):
        if state.get("announced_cut_ts") is None and now - last_ts > 6 * 3600:
            # Erstlauf und der Cut liegt lange zurueck. Nicht nachtraeglich
            # posten, nur merken. Alte Nachrichten sind keine Nachrichten.
            print("erstlauf, alter cut wird nur gemerkt")
        else:
            price = fetch_price_usd()
            announce_cut(before / RATIO, before, last_ts, price)
            print(f"CUT gemeldet, {before:.8f} KAS")
        state["announced_cut_ts"] = int(last_ts)
        wrote = True

    # 3. Vorwarnung, genau einmal je Termin.
    left = next_ts - now
    if 0 < left <= PRE_WARN_SECONDS and state.get("prewarned_cut_ts") != int(next_ts):
        price = fetch_price_usd()
        announce_prewarn(before, after, next_ts, price)
        state["prewarned_cut_ts"] = int(next_ts)
        wrote = True
        print(f"VORWARNUNG gemeldet, cut in {left/3600:.1f} stunden")

    if wrote:
        save_state(state)
    else:
        print(f"nichts zu tun. naechster cut {utc_str(next_ts)}, "
              f"in {left/3600:.1f} stunden, reward {before:.8f} KAS")

    print(f"STATE_CHANGED={'1' if wrote else '0'}")


if __name__ == "__main__":
    main()
