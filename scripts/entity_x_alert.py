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
import time
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

# Schreibregel, identisch zu den anderen Bots. Uhrzeiten und URLs sind
# ausgenommen, deshalb wird vor der Pruefung alles in spitzen Klammern
# und jede Ziffernuhrzeit entfernt.
FORBIDDEN = ["—", "–", " - ", ":", "→"]

# Woerter, die dem Bot eine Absicht unterstellen, die er nicht messen kann.
# Der Bot sieht einen Kontostand, sonst nichts. Er weiss nicht, wohin die
# Coins gehen, von wem sie kommen oder warum sie sich bewegen.
BANNED_CLAIMS = ["sold", "sell", "selling", "bought", "buying", "stacking",
                 "dumped", "accumulating", "whale is", "zero outflows",
                 "never sold", "first time"]


def assert_text(msg):
    """
    Prueft jede Nachricht, bevor sie den Rechner verlaesst.

    Hintergrund 12.08.2026. Im Abflusstext stand der Satz, diese Adresse
    haette seit Beginn der Beobachtung keinen einzigen Abfluss gehabt. Das
    war falsch, unser eigener Tracer weist 21 Abfluesse seit September 2024
    nach, zusammen rund 41 Millionen KAS. Der Satz kam aus der Erinnerung
    und nicht aus den Daten, und er ist trotzdem zweimal oeffentlich
    gelaufen. Ab jetzt faellt so ein Satz hier auf, bevor er rausgeht.
    """
    probe = msg
    for opener, closer in (("<", ">"),):
        out = []
        depth = 0
        for ch in probe:
            if ch == opener:
                depth += 1
            elif ch == closer and depth:
                depth -= 1
            elif not depth:
                out.append(ch)
        probe = "".join(out)

    hits = [c for c in FORBIDDEN if c in probe]
    if hits:
        raise ValueError("schreibregel verletzt, gefunden %r" % hits)
    low = probe.lower()
    claims = [w for w in BANNED_CLAIMS if w in low]
    if claims:
        raise ValueError(
            "der text behauptet etwas, das der bot nicht misst, %r. er liest "
            "einen kontostand und sonst nichts" % claims)
    return msg


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
    assert_text(message)
    send_discord(message)
    telegram_post.send_text(message)


def fmt(n):
    return f"{n:,.0f}"


# ---------------------------------------------------------------- texte
# Beide Texte sagen nur, was gemessen wurde, und einen Satz dazu, was daraus
# ausdruecklich nicht folgt. Der zweite Satz ist kein Beiwerk. Ohne ihn liest
# ein Abfluss sich wie ein Verkauf und ein Zufluss wie ein Kauf, und beides
# steht nirgends in der Kette.

def build_outflow(balance, last, diff):
    return (
        "@everyone **ENTITY X OUTFLOW DETECTED**\n"
        f"balance dropped by **{fmt(-diff)} KAS**\n"
        f"now {fmt(balance)} KAS, was {fmt(last)} KAS\n"
        "we see the movement and not the destination. coins leaving a wallet "
        "are not proof of anything else.\n"
        "check it yourself at <https://kaspapulse.com/entity-x.html>"
    )


def build_inflow(balance, diff):
    return (
        "**ENTITY X INFLOW DETECTED**\n"
        f"balance up **{fmt(diff)} KAS** since the last checkpoint\n"
        f"now {fmt(balance)} KAS\n"
        "coins arriving are not proof of a purchase.\n"
        "check it yourself at <https://kaspapulse.com/entity-x.html>"
    )


def check_once():
    """Eine Pruefung. Gibt True zurueck, wenn sich der Stand geaendert hat."""
    balance = fetch_balance_kas()
    state = load_state()

    if state is None:
        # Erster Lauf. Nur Stand speichern, kein Alarm.
        save_state(balance)
        print(f"init, balance {fmt(balance)} KAS gespeichert")
        print("STATE_CHANGED=1")
        return True

    last = state["balance_kas"]
    diff = balance - last

    if diff <= -OUTFLOW_EPSILON_KAS:
        send_all(build_outflow(balance, last, diff))
        save_state(balance)
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
        print("STATE_CHANGED=1")
        return True
    elif diff >= INFLOW_STEP_KAS:
        send_all(build_inflow(balance, diff))
        save_state(balance)
        print(f"INFLOW alert, +{fmt(diff)} KAS")
        print("STATE_CHANGED=1")
        return True
    print(f"no alert, balance {fmt(balance)} KAS, delta {diff:+,.0f} KAS")
    print("STATE_CHANGED=0")
    return False


def main():
    """Poll-Schleife.

    Hintergrund, gemessen am 11.08.2026: GitHub startet den Zeitplan
    */10 nicht alle zehn Minuten, sondern in der Praxis rund stuendlich.
    Ein Lauf, der nur einmal prueft, hat deshalb eine Erkennungszeit von
    bis zu einer Stunde. Der Job bleibt darum absichtlich lange am Leben
    und prueft im Minutentakt, bis LOOP_SECONDS abgelaufen sind. Damit
    deckt ein einzelner Start fast die gesamte Luecke bis zum naechsten ab.

    LOOP_SECONDS=0 prueft genau einmal, das ist der Modus fuer Tests.
    """
    loop = int(os.environ.get("LOOP_SECONDS", "0") or 0)
    interval = int(os.environ.get("POLL_INTERVAL", "60") or 60)
    started = time.monotonic()
    checks = 0
    alerts = 0

    while True:
        checks += 1
        try:
            if check_once():
                alerts += 1
        except Exception as exc:  # noqa: BLE001
            # ein einzelner fehlschlag darf die schleife nicht beenden,
            # sonst reisst eine api-stoerung das ganze fenster.
            print("pruefung fehlgeschlagen (%s)" % exc, file=sys.stderr)

        elapsed = time.monotonic() - started
        if elapsed + interval >= loop:
            break
        time.sleep(interval)

    print("fertig nach %d pruefungen in %.0f sekunden, %d alarme"
          % (checks, time.monotonic() - started, alerts))


def run_selftest():
    fails = []

    def ok(what, cond, extra=""):
        print(("  ok   " if cond else "  FEHL ") + what +
              ("" if cond else "  " + str(extra)))
        if not cond:
            fails.append(what)

    def raises(what, text):
        try:
            assert_text(text)
        except ValueError as exc:
            print("  ok   %s (%s)" % (what, str(exc)[:52]))
            return
        print("  FEHL " + what + "  kein abbruch, obwohl erwartet")
        fails.append(what)

    print("selftest entity x alert")

    out = build_outflow(1_442_000_000, 1_444_396_922, -2_396_922)
    inn = build_inflow(1_446_568_127, 4_568_127)
    for name, msg in (("abflusstext", out), ("zuflusstext", inn)):
        try:
            assert_text(msg)
            print("  ok   %s haelt schreibregel und doktrin" % name)
        except ValueError as exc:
            fails.append(name)
            print("  FEHL %s %s" % (name, exc))

    ok("abflusstext nennt die menge", "2,396,922 KAS" in out, out)
    ok("abflusstext nennt den alten stand", "1,444,396,922" in out)
    ok("zuflusstext nennt die menge", "4,568,127 KAS" in inn, inn)
    ok("beide texte verlinken die pruefseite",
       "entity-x.html" in out and "entity-x.html" in inn)

    # der eigentliche punkt. genau dieser satz lief zweimal oeffentlich.
    raises("die alte falschbehauptung faellt auf",
           "balance dropped\nthis address had zero outflows since tracking began")
    raises("verkauf wird abgefangen", "entity x sold a part of its stack")
    raises("kauf wird abgefangen", "entity x keeps stacking")
    raises("doppelpunkt wird abgefangen", "balance: 1,442,000,000 KAS")
    raises("gedankenstrich wird abgefangen", "balance down — 2,396,922 KAS")
    ok("eine url in klammern stoert die pruefung nicht",
       assert_text("check it at <https://kaspapulse.com/entity-x.html>") is not None)

    print("")
    if fails:
        print("%d fehlgeschlagen %s" % (len(fails), fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    main()
