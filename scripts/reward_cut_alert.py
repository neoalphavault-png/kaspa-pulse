#!/usr/bin/env python3
# Kaspa Pulse · Reward Cut Alert
# Meldet den monatlichen Reward-Cut in #alerts, berechnet aus dem Anker (keine API noetig).

import json
import os
import sys
import time
import urllib.request

ANCHOR_TS = 1783280744.0          # Cut vom 05.07.2026 (Sekunden)
ANCHOR_REWARD = 2.44997148        # KAS pro Block ab diesem Cut
STEP = (365.25 / 12) * 86400      # ein Emissions-Monat in Sekunden
R = 0.5 ** (1.0 / 12.0)           # minus ~5.6 Prozent pro Monat
STATE_FILE = "scripts/reward_cut_state.json"


def latest_cut(now):
    k = int((now - ANCHOR_TS) // STEP)
    if k < 0:
        k = 0
    return k, ANCHOR_TS + k * STEP


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(k):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_posted_k": k}, f)


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
    now = time.time()
    k, cut_ts = latest_cut(now)
    state = load_state()

    if state is None:
        save_state(k)
        print(f"init, letzter cut k={k}, kein post")
        return

    if k <= state["last_posted_k"]:
        print(f"kein neuer cut, k={k}")
        return

    new_reward = ANCHOR_REWARD * (R ** k)
    old_reward = ANCHOR_REWARD * (R ** (k - 1))
    next_ts = cut_ts + STEP
    next_date = time.strftime("%B %-d", time.gmtime(next_ts))

    send_discord(
        "**the monthly reward cut just happened.** kaspa's block reward stepped down from **"
        f"{old_reward:.2f}** to **{new_reward:.2f} KAS** per block, minus 5.6 percent, exactly as coded. "
        "no shock event, no drama, this happens every month. next cut lands around **"
        + next_date + "**. the full math at <https://kaspapulse.com/kaspa-halving.html>"
    )
    save_state(k)
    print(f"CUT alert, {old_reward:.2f} -> {new_reward:.2f}, next {next_date}")


if __name__ == "__main__":
    main()
