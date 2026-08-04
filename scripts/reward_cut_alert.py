#!/usr/bin/env python3
# Kaspa Pulse - Reward Cut Alert v4
# Ablageort im Repo: scripts/reward_cut_alert.py
#
# Kaspa halbiert nicht alle vier Jahre, sondern jeden Monat ein Stueck.
# Der Zeitpunkt ist deterministisch, wir muessen ihn also nicht suchen,
# wir rechnen ihn aus einem Anker vor. Die API /info/blockreward ist
# veraltet und wird bewusst NICHT benutzt.
#
# Neu gegenueber v3 (Lesbarkeit, keine Logikaenderung):
#   1. ZAHLENDIAET. Die Vorwarnung hatte zwoelf Zahlen in fuenf Zeilen.
#      Jetzt sind es drei plus ein Vergleich. Wer mehr will, klickt die
#      Halving-Seite in der Fusszeile.
#   2. context_lines() liefert EINE Zeile statt zwei. Die Jahresausgabe
#      (542M KAS, 1,96 Prozent, Dollarwert) ist raus. Im Vorbeiscrollen
#      verarbeitet die niemand.
#   3. VERGLEICH STATT DEFINITION. "one step of twelve" und die Klippe
#      gegen die Treppe erklaeren den Mechanismus ohne eine einzige
#      Nachkommastelle.
#   4. EHRLICHER SCHLUSSSATZ. "the schedule has never moved" ist raus.
#      Der Zeitplan steht, die geschaetzten Uhrzeiten wandern, weil der
#      Schritt auf einem Block Score landet und nicht auf einer Uhr. Der
#      neue Satz sagt beides und macht aus der Abweichung ein Argument.
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
UA = {"User-Agent": "kaspapulse-rewardcut/4.0"}


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
    """Gibt (circulating, max) zurueck. Faellt still auf None zurueck.

    Seit v4 nicht mehr im Nachrichtentext benutzt. Bleibt stehen, weil die
    Zahl fuer kuenftige Auswertungen gebraucht wird und der Abruf nichts
    kostet, solange ihn niemand aufruft.
    """
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
    """Genau eine Zeile. Uebersetzt den Reward in etwas Vorstellbares.

    Vorher standen hier zwei Zeilen mit sechs Zahlen, darunter die
    Jahresausgabe. Die ist raus. Sie ist richtig, aber sie beantwortet
    keine Frage, die jemand beim Lesen tatsaechlich hat.
    """
    d_now = daily(reward_after / RATIO)
    d_new = daily(reward_after)
    drop = d_now - d_new
    usd = f", about {fmt_usd(drop * price)} at today's price" if price else ""
    return (f"in plain terms, the network creates about **{fmt(drop)} fewer KAS "
            f"every day** from now on{usd}.")


def announce_cut(before, after, ts, price):
    pct = (1 - after / before) * 100
    send_embed(
        "🟣 it happened. the reward just got cut",
        f"the block reward went from **{before:.8f} KAS** to **{after:.8f} KAS**. "
        f"that is **{pct:.2f} percent** less, and it is the same number this "
        "channel posted yesterday, down to the eighth decimal.\n\n"
        "no cliff, no shock. one step down a staircase that takes twelve steps "
        "to reach the half.\n\n"
        f"{context_lines(after, price)}\n\n"
        f"the next step is estimated for {utc_str(schedule(ts + 60)[0])}.",
        PURPLE, price=price,
    )


def announce_prewarn(before, after, ts, price):
    pct = (1 - after / before) * 100
    send_embed(
        "🔵 heads up. the reward gets cut tomorrow",
        f"the block reward drops from **{before:.8f} KAS** to **{after:.8f} KAS**. "
        f"that is **{pct:.2f} percent** less.\n\n"
        "this is not a halving. it is one step of twelve. walk down all twelve "
        "and the reward has halved, then the count starts again.\n\n"
        "bitcoin does the same thing once every four years, all at once. kaspa "
        "spreads it across the year, so no miner wakes up to half the revenue.\n\n"
        f"{context_lines(after, price)}\n\n"
        f"the estimate right now is {utc_str(ts)}. that minute will shift a "
        "little, because the step lands on a block score and not on a clock. "
        "the number does not shift at all.",
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
