#!/usr/bin/env python3
# Kaspa Pulse - Entity X Watcher v3
# Ablageort im Repo: scripts/entity_x_alert.py
#
# Neu gegenueber v2:
#   1. DOLLARWERTE. Jede Zahl steht jetzt doppelt da, in KAS und in USD.
#      Betroffen sind der Bewegungsbetrag und der Kontostand.
#   2. DER PREIS WIRD FAUL GEHOLT. Nur dann, wenn wirklich eine Nachricht
#      rausgeht. Der Watcher pollt 1440 mal am Tag, aber er fragt den Preis
#      nur ein paar mal im Monat ab. Kein Ratelimit-Risiko.
#   3. FALLBACK-KETTE. Fuenf Preisquellen hintereinander. Faellt eine aus,
#      nimmt der Bot die naechste. Faellt alles aus, kommt der Alarm trotzdem,
#      dann eben nur in KAS. Ein Preisproblem darf niemals einen Alarm
#      verschlucken.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import sys
import time
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API_BALANCE = "https://api.kaspa.org/addresses/{}/balance"
API_SUPPLY = "https://api.kaspa.org/info/coinsupply"
STATE_FILE = "scripts/entity_x_state.json"
SOMPI = 100_000_000  # 1 KAS = 1e8 sompi

# Schwellwerte. Beide Zahlen sind bewusst hier oben, damit du sie in 5 Sekunden
# aendern kannst, wenn dir der Kanal zu laut oder zu leise wird.
OUTFLOW_MIN_KAS = 1_000       # jeder Abfluss ab 1.000 KAS ist ein Alarm
INFLOW_MIN_KAS = 500_000      # Zufluss ab 500.000 KAS ist ein Alarm

# Discord-Farben
RED = 0xFF4D4D
GREEN = 0x49EACB
POLL_SECONDS = 60
UA = {"User-Agent": "kaspapulse-watch/3.0"}

# Plausibilitaetsfenster fuer den Preis. Was ausserhalb liegt, ist ein Fehler
# der Boerse und keine Marktbewegung. Lieber kein Dollarwert als ein falscher.
PRICE_MIN = 0.0001
PRICE_MAX = 100.0
PRICE_TTL = 300  # Sekunden, gilt nur innerhalb eines Laufs
_price_cache = {"ts": 0.0, "value": None}


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def fetch_balance_kas():
    return int(get_json(API_BALANCE.format(ADDRESS))["balance"]) / SOMPI


def fetch_supply_pct(balance_kas):
    """Anteil an der zirkulierenden Menge. Faellt still aus, wenn die API zickt."""
    try:
        circ = int(get_json(API_SUPPLY)["circulatingSupply"]) / SOMPI
        if circ > 0:
            return balance_kas / circ * 100
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Preis. Reihenfolge ist bewusst gewaehlt.
# Kraken zuerst, weil es ein echtes USD-Paar ist und Rechenzentrums-IPs mag.
# Danach drei Boersen mit USDT, das weicht um Bruchteile eines Prozents ab.
# CoinGecko steht hinten, weil die Gratisstufe Cloud-IPs gerne abweist.
# ---------------------------------------------------------------------------
def _p_kraken():
    d = get_json("https://api.kraken.com/0/public/Ticker?pair=KASUSD", timeout=12)
    result = d.get("result") or {}
    for entry in result.values():
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
    """KAS-Preis in USD. Gibt None zurueck, wenn keine einzige Quelle antwortet."""
    now = time.time()
    if _price_cache["value"] is not None and now - _price_cache["ts"] < PRICE_TTL:
        return _price_cache["value"]
    for name, fn in PRICE_SOURCES:
        try:
            p = fn()
            if PRICE_MIN < p < PRICE_MAX:
                _price_cache["ts"] = now
                _price_cache["value"] = p
                print(f"preis {p} von {name}")
                return p
            print(f"WARN {name} lieferte unplausible {p}", file=sys.stderr)
        except Exception as e:
            print(f"WARN preisquelle {name} fehlgeschlagen: {e}", file=sys.stderr)
    print("WARN keine preisquelle erreichbar, alarm geht ohne dollarwert raus",
          file=sys.stderr)
    return None


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(balance_kas):
    with open(STATE_FILE, "w") as f:
        json.dump({"balance_kas": round(balance_kas, 2)}, f)


def send_embed(title, description, color, price=None, ping=False):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    foot = "kaspa pulse · live tracker at kaspapulse.com/entity-x.html"
    if price:
        foot = f"kaspa pulse · KAS at {fmt_price(price)} · kaspapulse.com/entity-x.html"
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": foot},
        }]
    }
    if ping:
        payload["content"] = "@everyone"

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
    """Preis pro KAS. Unter einem Dollar brauchen wir vier Stellen."""
    return f"${p:,.4f}" if p < 1 else f"${p:,.2f}"


def fmt_usd(v):
    """Dollarbetrag kurz und lesbar. 43.6M liest sich schneller als 43,600,000."""
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
    """Haengt den Dollarwert an, oder nichts, wenn kein Preis da ist."""
    if not price:
        return ""
    return f"{lead}**{fmt_usd(kas * price)}**"


def check_once():
    """Ein Durchgang. Gibt True zurueck, wenn die State-Datei geschrieben wurde."""
    balance = fetch_balance_kas()
    state = load_state()

    if state is None:
        save_state(balance)
        print(f"init, balance {fmt(balance)} KAS gespeichert")
        return True

    last = state["balance_kas"]
    diff = balance - last

    if diff <= -OUTFLOW_MIN_KAS:
        pct = fetch_supply_pct(balance)
        price = fetch_price_usd()
        pctline = f"\nthat is **{pct:.2f} percent** of all coins in circulation." if pct else ""
        send_embed(
            "🔴 entity x outflow detected",
            f"**{fmt(-diff)} KAS** left the wallet{usd_part(-diff, price)}.\n"
            f"balance is now **{fmt(balance)} KAS**{usd_part(balance, price, lead=', about ')}, "
            f"it was {fmt(last)} KAS."
            f"{pctline}\n\n"
            "this address had zero outflows since tracking began, so this is the first move of its kind. "
            "coins leaving a wallet can mean a sale, an exchange deposit or an internal transfer. "
            "we report the movement, never the motive.",
            RED, price=price, ping=True,
        )
        save_state(balance)
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
        return True

    if diff >= INFLOW_MIN_KAS:
        pct = fetch_supply_pct(balance)
        price = fetch_price_usd()
        pctline = f"\nthat is **{pct:.2f} percent** of all coins in circulation." if pct else ""
        send_embed(
            "🟢 entity x added more",
            f"**{fmt(diff)} KAS** arrived since the last checkpoint"
            f"{usd_part(diff, price)}.\n"
            f"balance is now **{fmt(balance)} KAS**"
            f"{usd_part(balance, price, lead=', about ')}."
            f"{pctline}\n\n"
            "still zero outflows since tracking began. the pile only grows.",
            GREEN, price=price,
        )
        save_state(balance)
        print(f"INFLOW alert, +{fmt(diff)} KAS")
        return True

    print(f"kein alarm, balance {fmt(balance)} KAS, delta {diff:+,.0f} KAS")
    return False


def main():
    loop_seconds = int(os.environ.get("LOOP_SECONDS", "0"))
    changed = False
    deadline = time.time() + loop_seconds

    while True:
        try:
            if check_once():
                changed = True
        except Exception as e:
            # Ein einzelner API-Aussetzer darf den ganzen Lauf nicht killen.
            print(f"WARN durchgang fehlgeschlagen: {e}", file=sys.stderr)

        if time.time() + POLL_SECONDS >= deadline:
            break
        time.sleep(POLL_SECONDS)

    print(f"STATE_CHANGED={'1' if changed else '0'}")


if __name__ == "__main__":
    main()
