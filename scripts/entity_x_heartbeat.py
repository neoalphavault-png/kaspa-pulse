#!/usr/bin/env python3
# Kaspa Pulse - Entity X Heartbeat v4
# Ablageort im Repo: scripts/entity_x_heartbeat.py
#
# Neu gegenueber v3:
#   1. KORREKTUR. Vier Stellen haben "no outflow since tracking began" oder
#      "the streak continues" behauptet. Unser eigener Tracer zaehlt 20
#      Abfluesse ueber 39.038.233 KAS. Die Behauptung war falsch und stand
#      im Widerspruch zu kaspapulse.com/entity-x.html.
#   2. STRUKTURELL. Dieser Job vergleicht nur Tagessalden. Aus einem
#      positiven Delta folgt logisch nicht, dass nichts abgeflossen ist.
#      Der Bot kann diese Aussage gar nicht treffen, also trifft er sie
#      nicht mehr.
#
# Einmal am Tag. Der Heartbeat vergleicht mit dem Stand von gestern und faerbt
# die Nachricht danach ein.
#   grau  = kein Nettounterschied zu gestern
#   gruen = ueber Nacht dazugekauft, mit Tagesdifferenz
#   rot   = ueber Nacht abgeflossen
#
# Neu gegenueber v2: Dollarwerte neben jeder KAS-Zahl. Genau ein Preisabruf
# pro Tag. Wichtig beim grauen Fall, dort wird der Dollarwert ausdruecklich
# als Momentaufnahme bezeichnet, denn er bewegt sich auch dann, wenn auf der
# Kette gar nichts passiert. Wir verkaufen keine Preisbewegung als Wallet-
# Bewegung.
#
# Eigene State-Datei, damit der 10-Minuten-Watcher davon unberuehrt bleibt.

import json
import os
import sys
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API_BALANCE = "https://api.kaspa.org/addresses/{}/balance"
API_SUPPLY = "https://api.kaspa.org/info/coinsupply"
STATE_FILE = "scripts/entity_x_daily.json"
SOMPI = 100_000_000

GREY = 0x7A828C
GREEN = 0x49EACB
RED = 0xFF4D4D
NOISE_KAS = 1  # alles darunter gilt als unveraendert
UA = {"User-Agent": "kaspapulse-heartbeat/4.0"}

PRICE_MIN = 0.0001
PRICE_MAX = 100.0


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def fetch_balance_kas():
    return int(get_json(API_BALANCE.format(ADDRESS))["balance"]) / SOMPI


def fetch_supply_pct(balance_kas):
    try:
        circ = int(get_json(API_SUPPLY)["circulatingSupply"]) / SOMPI
        if circ > 0:
            return balance_kas / circ * 100
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Preis. Gleiche Kette wie im Watcher. Kraken zuerst, echtes USD-Paar und
# freundlich zu Rechenzentrums-IPs. CoinGecko hinten, weil die Gratisstufe
# Cloud-IPs gerne abweist.
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
    print("WARN keine preisquelle erreichbar, check geht ohne dollarwert raus",
          file=sys.stderr)
    return None


def load_last():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)["balance_kas"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def save_last(balance_kas):
    with open(STATE_FILE, "w") as f:
        json.dump({"balance_kas": round(balance_kas, 2)}, f)


def send_embed(title, description, color, price=None):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    foot = "kaspa pulse · daily check · kaspapulse.com/entity-x.html"
    if price:
        foot = (f"kaspa pulse · daily check · KAS at {fmt_price(price)} · "
                "kaspapulse.com/entity-x.html")
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


def usd_part(kas, price, lead=", worth about "):
    if not price:
        return ""
    return f"{lead}**{fmt_usd(kas * price)}**"


def main():
    balance = fetch_balance_kas()
    last = load_last()
    pct = fetch_supply_pct(balance)
    price = fetch_price_usd()
    pctline = f" that is **{pct:.2f} percent** of everything in circulation." if pct else ""

    # Beim ruhigen Tag sagen wir ausdruecklich, dass nur der Preis den
    # Dollarwert bewegt. Sonst liest jemand ein Plus in die Zahl hinein,
    # das auf der Kette gar nicht existiert.
    if price:
        holdline = (f"at today's price of {fmt_price(price)} that stack is worth about "
                    f"**{fmt_usd(balance * price)}**.\n")
        driftline = ("the coin count did not move. only the dollar number does, "
                     "because the market does.\n")
    else:
        holdline = ""
        driftline = ""

    if last is None:
        send_embed(
            "⚪ daily check",
            f"entity x holds **{fmt(balance)} KAS**.{pctline}\n"
            f"{holdline}"
            "we count every coin that enters and leaves this wallet. the full "
            "history sits at kaspapulse.com/entity-x.html.",
            GREY, price=price,
        )
    else:
        diff = balance - last
        if abs(diff) < NOISE_KAS:
            send_embed(
                "⚪ daily check. nothing moved",
                f"entity x still holds **{fmt(balance)} KAS**, unchanged since yesterday.{pctline}\n"
                f"{holdline}{driftline}"
                "every coin that ever left this wallet is counted at "
                "kaspapulse.com/entity-x.html.",
                GREY, price=price,
            )
        elif diff > 0:
            send_embed(
                "🟢 daily check. entity x bought more",
                f"**{fmt(diff)} KAS** added in the last 24 hours"
                f"{usd_part(diff, price)}.\n"
                f"the wallet now holds **{fmt(balance)} KAS**"
                f"{usd_part(balance, price, lead=', about ')}.{pctline}\n"
                "this is a net figure. deposits and withdrawals inside the "
                "same day cancel out before we see them.",
                GREEN, price=price,
            )
        else:
            send_embed(
                "🔴 daily check. coins left the wallet",
                f"**{fmt(-diff)} KAS** left in the last 24 hours"
                f"{usd_part(-diff, price)}.\n"
                f"the wallet now holds **{fmt(balance)} KAS**"
                f"{usd_part(balance, price, lead=', about ')}.{pctline}\n"
                "movement reported, motive unknown.",
                RED, price=price,
            )

    save_last(balance)
    print(f"heartbeat ok, balance {fmt(balance)} KAS")


if __name__ == "__main__":
    main()
