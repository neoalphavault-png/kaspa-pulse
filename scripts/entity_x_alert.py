#!/usr/bin/env python3
# Kaspa Pulse - Entity X Watcher v2
# Ablageort im Repo: scripts/entity_x_alert.py
#
# Neu gegenueber v1:
#   1. NAHEZU ECHTZEIT. Der Job laeuft nicht mehr einmal und beendet sich, sondern
#      pollt in einer Schleife alle 60 Sekunden, bis LOOP_SECONDS abgelaufen sind.
#      Der Workflow startet ihn alle 10 Minuten neu. Erkennungszeit ca. 1 Minute
#      statt bis zu 30 Minuten plus GitHub-Verzoegerung.
#   2. NIEDRIGERE ZUFLUSS-SCHWELLE. 500.000 KAS statt 5.000.000. Der Kauf vom
#      1. August (3,78 Mio KAS) lag unter der alten Schwelle und hat deshalb
#      GAR KEINEN Alarm ausgeloest. Das war der eigentliche Fehler.
#   3. FARBIGE EMBEDS. rot = Abfluss, gruen = Zufluss. Discord faerbt den Balken
#      links neben der Nachricht ein, dazu Emoji im Titel.
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
UA = {"User-Agent": "kaspapulse-watch/2.0"}


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


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(balance_kas):
    with open(STATE_FILE, "w") as f:
        json.dump({"balance_kas": round(balance_kas, 2)}, f)


def send_embed(title, description, color, ping=False):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "kaspa pulse · live tracker at kaspapulse.com/entity-x.html"},
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
        pctline = f"\nthat is **{pct:.2f} percent** of all coins in circulation." if pct else ""
        send_embed(
            "🔴 entity x outflow detected",
            f"**{fmt(-diff)} KAS** left the wallet.\n"
            f"balance is now **{fmt(balance)} KAS**, it was {fmt(last)} KAS."
            f"{pctline}\n\n"
            "this address had zero outflows since tracking began, so this is the first move of its kind. "
            "coins leaving a wallet can mean a sale, an exchange deposit or an internal transfer. "
            "we report the movement, never the motive.",
            RED, ping=True,
        )
        save_state(balance)
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
        return True

    if diff >= INFLOW_MIN_KAS:
        pct = fetch_supply_pct(balance)
        pctline = f"\nthat is **{pct:.2f} percent** of all coins in circulation." if pct else ""
        send_embed(
            "🟢 entity x added more",
            f"**{fmt(diff)} KAS** arrived since the last checkpoint.\n"
            f"balance is now **{fmt(balance)} KAS**."
            f"{pctline}\n\n"
            "still zero outflows since tracking began. the pile only grows.",
            GREEN,
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
