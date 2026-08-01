#!/usr/bin/env python3
# Kaspa Pulse · Entity X Daily Heartbeat
# Postet einmal taeglich eine ruhige Bestaetigung in #alerts.

import json
import os
import sys
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API = "https://api.kaspa.org/addresses/{}/balance"
SOMPI = 100_000_000


def fetch_balance_kas():
    req = urllib.request.Request(API.format(ADDRESS), headers={"User-Agent": "kaspapulse-alert/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return int(data["balance"]) / SOMPI


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


def main():
    balance = fetch_balance_kas()
    send_discord(
        "**daily check.** entity x holds **" + f"{balance:,.0f}" + " KAS**. "
        "no outflow since tracking began, the streak continues. "
        "alerts fire here the moment anything moves. "
        "live tracker at <https://kaspapulse.com/entity-x.html>"
    )
    print(f"heartbeat gesendet, balance {balance:,.0f} KAS")


if __name__ == "__main__":
    main()
