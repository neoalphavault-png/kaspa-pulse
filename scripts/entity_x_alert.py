#!/usr/bin/env python3
# Kaspa Pulse · Entity X Alert Bot
# Laeuft als GitHub Action (siehe .github/workflows/entity-x-alert.yml).
# Prueft die Entity-X-Balance gegen den letzten gespeicherten Stand und
# feuert einen Discord-Webhook bei Abfluss oder grossem Zufluss.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram_post  # noqa: E402

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API = "https://api.kaspa.org/addresses/{}/balance"
STATE_FILE = "scripts/entity_x_state.json"
SOMPI = 100_000_000  # 1 KAS = 1e8 sompi

# Schwellwerte
OUTFLOW_EPSILON_KAS = 1_000        # Abfluss-Alarm ab 1.000 KAS unter letztem Stand
INFLOW_STEP_KAS = 5_000_000       # Zufluss-Alarm je 5M KAS ueber letztem Stand


def fetch_balance_kas():
    req = urllib.request.Request(API.format(ADDRESS), headers={"User-Agent": "kaspapulse-alert/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return int(data["balance"]) / SOMPI


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(balance_kas):
    with open(STATE_FILE, "w") as f:
        json.dump({"balance_kas": round(balance_kas, 2)}, f)


def send_discord(message):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if not url:
        print("ERROR: DISCORD_WEBHOOK secret fehlt", file=sys.stderr)
        sys.exit(1)
    payload = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "kaspapulse-alert/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def send_all(message):
    """discord ist der hauptkanal, telegram der spiegel. faellt telegram
    aus, laeuft der alert trotzdem durch, siehe telegram_post.py."""
    send_discord(message)
    telegram_post.send_text(message)


def fmt(n):
    return f"{n:,.0f}"


def main():
    balance = fetch_balance_kas()
    state = load_state()

    if state is None:
        # Erster Lauf. Nur Stand speichern, kein Alarm.
        save_state(balance)
        print(f"init, balance {fmt(balance)} KAS gespeichert")
        print("STATE_CHANGED=1")
        return

    last = state["balance_kas"]
    diff = balance - last

    if diff <= -OUTFLOW_EPSILON_KAS:
        send_all(
            "@everyone **ENTITY X OUTFLOW DETECTED**\n"
            f"balance dropped by **{fmt(-diff)} KAS**\n"
            f"now {fmt(balance)} KAS, was {fmt(last)} KAS\n"
            "this address had zero outflows since tracking began. "
            "verify live at <https://kaspapulse.com/entity-x.html>"
        )
        save_state(balance)
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
        print("STATE_CHANGED=1")
    elif diff >= INFLOW_STEP_KAS:
        send_all(
            "**entity x keeps stacking**\n"
            f"balance up **{fmt(diff)} KAS** since the last checkpoint\n"
            f"now {fmt(balance)} KAS\n"
            "live tracker at <https://kaspapulse.com/entity-x.html>"
        )
        save_state(balance)
        print(f"INFLOW alert, +{fmt(diff)} KAS")
        print("STATE_CHANGED=1")
    else:
        print(f"no alert, balance {fmt(balance)} KAS, delta {diff:+,.0f} KAS")
        print("STATE_CHANGED=0")


if __name__ == "__main__":
    main()
