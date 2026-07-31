#!/usr/bin/env python3
# Kaspa Pulse · Entity X Alert Bot

import json
import os
import sys
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API = "https://api.kaspa.org/addresses/{}/balance"
STATE_FILE = "scripts/entity_x_state.json"
SOMPI = 100_000_000  # 1 KAS = 1e8 sompi

OUTFLOW_EPSILON_KAS = 1_000
INFLOW_STEP_KAS = 5_000_000


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


def fmt(n):
    return f"{n:,.0f}"


def main():
    balance = fetch_balance_kas()
    state = load_state()

    if state is None:
        save_state(balance)
        print(f"init, balance {fmt(balance)} KAS gespeichert")
        return

    last = state["balance_kas"]
    diff = balance - last

    if diff <= -OUTFLOW_EPSILON_KAS:
        send_discord(
            "@everyone **ENTITY X OUTFLOW DETECTED**\n"
            f"balance dropped by **{fmt(-diff)} KAS**\n"
            f"now {fmt(balance)} KAS, was {fmt(last)} KAS\n"
            "this address had zero outflows since tracking began. "
            "verify live at <https://kaspapulse.com/entity-x.html>"
        )
        save_state(balance)
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
    elif diff >= INFLOW_STEP_KAS:
        send_discord(
            "**entity x keeps stacking**\n"
            f"balance up **{fmt(diff)} KAS** since the last checkpoint\n"
            f"now {fmt(balance)} KAS\n"
            "live tracker at <https://kaspapulse.com/entity-x.html>"
        )
        save_state(balance)
        print(f"INFLOW alert, +{fmt(diff)} KAS")
    else:
        print(f"no alert, balance {fmt(balance)} KAS, delta {diff:+,.0f} KAS")


if __name__ == "__main__":
    main()
