#!/usr/bin/env python3
# Kaspa Pulse - Entity X Heartbeat v2
# Ablageort im Repo: scripts/entity_x_heartbeat.py
#
# Einmal am Tag. Neu gegenueber v1: der Heartbeat vergleicht mit dem Stand von
# gestern und faerbt die Nachricht danach ein.
#   grau  = nichts bewegt, die Serie laeuft weiter
#   gruen = ueber Nacht dazugekauft, mit Tagesdifferenz
#   rot   = ueber Nacht abgeflossen (sollte der Watcher schon gemeldet haben,
#           der Heartbeat ist die Sicherheitsnetz-Zusammenfassung)
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
UA = {"User-Agent": "kaspapulse-heartbeat/2.0"}


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


def load_last():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)["balance_kas"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def save_last(balance_kas):
    with open(STATE_FILE, "w") as f:
        json.dump({"balance_kas": round(balance_kas, 2)}, f)


def send_embed(title, description, color):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    payload = {"embeds": [{
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": "kaspa pulse · daily check · kaspapulse.com/entity-x.html"},
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


def main():
    balance = fetch_balance_kas()
    last = load_last()
    pct = fetch_supply_pct(balance)
    pctline = f" that is **{pct:.2f} percent** of everything in circulation." if pct else ""

    if last is None:
        send_embed(
            "⚪ daily check",
            f"entity x holds **{fmt(balance)} KAS**.{pctline}\n"
            "no outflow since tracking began. the streak continues.",
            GREY,
        )
    else:
        diff = balance - last
        if abs(diff) < NOISE_KAS:
            send_embed(
                "⚪ daily check. nothing moved",
                f"entity x still holds **{fmt(balance)} KAS**, unchanged since yesterday.{pctline}\n"
                "no outflow since tracking began. the streak continues.",
                GREY,
            )
        elif diff > 0:
            send_embed(
                "🟢 daily check. entity x bought more",
                f"**{fmt(diff)} KAS** added in the last 24 hours.\n"
                f"the wallet now holds **{fmt(balance)} KAS**.{pctline}\n"
                "still zero outflows since tracking began.",
                GREEN,
            )
        else:
            send_embed(
                "🔴 daily check. coins left the wallet",
                f"**{fmt(-diff)} KAS** left in the last 24 hours.\n"
                f"the wallet now holds **{fmt(balance)} KAS**.{pctline}\n"
                "this ends the zero outflow streak. movement reported, motive unknown.",
                RED,
            )

    save_last(balance)
    print(f"heartbeat ok, balance {fmt(balance)} KAS")


if __name__ == "__main__":
    main()
