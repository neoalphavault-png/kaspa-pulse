#!/usr/bin/env python3
# Kaspa Pulse · Entity X Alert Bot
# Laeuft als GitHub Action (siehe .github/workflows/entity-x-alert.yml).
# Prueft die Entity-X-Balance gegen den letzten gespeicherten Stand und
# feuert einen Discord-Webhook bei Abfluss oder grossem Zufluss.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram_post  # noqa: E402

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
API = "https://api.kaspa.org/addresses/{}/balance"
STATE_FILE = "scripts/entity_x_state.json"
# Beobachtungsprotokoll. Ein Eintrag je Lauf, damit die Abdeckung messbar
# ist und nicht geschaetzt werden muss. Siehe coverage_lines().
WATCH_LOG = "data/entity-x-watch-log.json"
WATCH_LOG_KEEP = 400
SOMPI = 100_000_000  # 1 KAS = 1e8 sompi

# Schwellwerte
OUTFLOW_EPSILON_KAS = 1_000        # Abfluss-Alarm ab 1.000 KAS unter letztem Stand
INFLOW_STEP_KAS = 500_000          # Zufluss-Alarm ab 500.000 KAS ueber letztem Stand
NOISE_KAS = 1                      # darunter gilt der Stand als unveraendert

# KORREKTUR 27.09.2026. Bis hierher wurde der Vergleichsstand NUR bei einem
# Alarm gespeichert. Ein Zufluss unter der Schwelle blieb deshalb liegen und
# verdeckte den naechsten Abfluss: am 23.09. kamen 2.477.625 KAS herein (unter
# den damals 5.000.000), am 24.09. gingen 2.000.015 KAS hinaus, und der Bot
# sah gegen den Stand vom 18.09. nur "delta +477,615" (Lauf 36067897929).
# Ab jetzt ist der Vergleichsstand immer der zuletzt GESEHENE Kontostand.
# Die Zufluss-Schwelle stand seit der ersten Fassung (31.07.) auf 5.000.000;
# Ben nennt 500.000 als Regel, deshalb jetzt 500.000.

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


# ------------------------------------------------- beobachtungsprotokoll

def load_watch_log():
    try:
        with open(WATCH_LOG) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def append_watch(start_ts, end_ts, checks, alerts):
    log = load_watch_log()
    log.append({
        "start_utc": dt.datetime.fromtimestamp(start_ts, dt.timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": dt.datetime.fromtimestamp(end_ts, dt.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seconds": int(end_ts - start_ts),
        "checks": checks,
        "alerts": alerts,
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "chain": os.environ.get("ALERT_CHAIN", ""),
    })
    log = log[-WATCH_LOG_KEEP:]
    os.makedirs(os.path.dirname(WATCH_LOG), exist_ok=True)
    with open(WATCH_LOG, "w") as f:
        json.dump(log, f, indent=1)
        f.write("\n")
    return log


def _merge(spans):
    """Ueberlappende Fenster zusammenlegen, sonst kaeme Abdeckung ueber
    100 Prozent heraus, wenn zwei Laeufe sich ueberschneiden."""
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def coverage_lines(log, days=7, now=None):
    """Abdeckung je Tag aus dem Protokoll. Das ist die Zahl, an der sich
    die Kanalbeschreibung messen laesst."""
    now = now if now is not None else time.time()
    spans = []
    for e in log:
        try:
            a = dt.datetime.strptime(e["start_utc"], "%Y-%m-%dT%H:%M:%SZ") \
                  .replace(tzinfo=dt.timezone.utc).timestamp()
            b = dt.datetime.strptime(e["end_utc"], "%Y-%m-%dT%H:%M:%SZ") \
                  .replace(tzinfo=dt.timezone.utc).timestamp()
        except (KeyError, ValueError):
            continue
        if b > a:
            spans.append((a, b))
    spans = _merge(spans)
    heute = dt.datetime.fromtimestamp(now, dt.timezone.utc).date()
    zeilen = []
    for i in range(days - 1, -1, -1):
        tag = heute - dt.timedelta(days=i)
        t0 = dt.datetime.combine(tag, dt.time(0, 0), dt.timezone.utc).timestamp()
        t1 = t0 + 86400
        gedeckt = sum(max(0.0, min(b, t1) - max(a, t0)) for a, b in spans)
        teil = min(t1, now) - t0
        if teil <= 0:
            continue
        zeilen.append({
            "tag": tag.isoformat(),
            "sekunden": int(gedeckt),
            "stunden": round(gedeckt / 3600, 2),
            "anteil_pct": round(gedeckt / teil * 100, 1),
            "unvollstaendig": t1 > now,
        })
    return zeilen


def print_coverage(log, now=None):
    print("\nabdeckung je tag, aus %s" % WATCH_LOG)
    for z in coverage_lines(log, now=now):
        rest = "  (tag laeuft noch)" if z["unvollstaendig"] else ""
        print("  %s  %5.2f h  %5.1f prozent%s"
              % (z["tag"], z["stunden"], z["anteil_pct"], rest))


# ------------------------------------------------- sofort festschreiben

def _git(*args):
    return subprocess.run(("git",) + args, capture_output=True, text=True)


def persist_now(grund):
    """Vergleichsstand sofort festschreiben, nicht erst am Jobende.

    Mit der Dauerbeobachtung laeuft ein Job bis zu 5 h 40 min. Bricht er ab,
    waere der Vergleichsstand von bis zu 5 h 40 min Bewegung verloren, und
    der naechste Lauf meldete dieselbe Bewegung ein zweites Mal. Nach jedem
    Alarm wird deshalb sofort gepusht.

    Nur aktiv, wenn PERSIST_EACH gesetzt ist. Lokale Laeufe und der
    Selbsttest fassen git nicht an.
    """
    if not os.environ.get("PERSIST_EACH"):
        return False
    _git("config", "user.name", "kaspa-pulse-bot")
    _git("config", "user.email", "bot@kaspapulse.com")
    _git("add", STATE_FILE, WATCH_LOG)
    if _git("diff", "--staged", "--quiet").returncode == 0:
        return False
    _git("commit", "-m", "entity x state update, %s [bot]" % grund)
    for versuch in range(2):
        if _git("push").returncode == 0:
            print("vergleichsstand sofort festgeschrieben (%s)" % grund)
            return True
        # Ein anderer Bot war schneller. Einmal nachziehen, dann nochmal.
        _git("pull", "--rebase", "origin", "main")
    print("WARN push des vergleichsstands fehlgeschlagen, der lauf macht "
          "weiter; der jobende-commit versucht es erneut", file=sys.stderr)
    return False


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
        persist_now("abfluss")
        print(f"OUTFLOW alert, {fmt(-diff)} KAS")
        print("STATE_CHANGED=1")
        return True
    elif diff >= INFLOW_STEP_KAS:
        send_all(build_inflow(balance, diff))
        save_state(balance)
        persist_now("zufluss")
        print(f"INFLOW alert, +{fmt(diff)} KAS")
        print("STATE_CHANGED=1")
        return True
    if abs(diff) >= NOISE_KAS:
        # kein alarm, aber der stand hat sich bewegt. er wird trotzdem der
        # neue vergleichsstand, sonst verdeckt diese bewegung die naechste.
        save_state(balance)
        print(f"no alert, balance {fmt(balance)} KAS, delta {diff:+,.0f} KAS, stand fortgeschrieben")
        print("STATE_CHANGED=1")
        return False
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
    start_wall = time.time()
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

    # Was dieser Lauf wirklich beobachtet hat, ins Protokoll. Die Abdeckung
    # ist damit gemessen und nicht geschaetzt.
    log = append_watch(start_wall, time.time(), checks, alerts)
    print("\nfenster %s bis %s, %d pruefungen, %d alarme"
          % (dt.datetime.fromtimestamp(start_wall, dt.timezone.utc)
               .strftime("%H:%M:%S"),
             dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S UTC"),
             checks, alerts))
    print_coverage(log)

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

    # die woche vom 22. bis 25.09., wie sie die tagespruefung sah. mit der
    # alten logik blieb der bot bei allen drei bewegungen still.
    global fetch_balance_kas, load_state, save_state, send_all
    alt = (fetch_balance_kas, load_state, save_state, send_all)
    stand = {"balance_kas": 1_523_915_192.09}
    gesendet = []
    folge = [1_523_915_197.09, 1_526_392_821.60, 1_524_392_806.78, 1_525_975_596.46]
    try:
        load_state = lambda: dict(stand)                              # noqa: E731
        save_state = lambda b: stand.update(balance_kas=round(b, 2))  # noqa: E731
        send_all = lambda m: (assert_text(m), gesendet.append(m))     # noqa: E731
        for b in folge:
            fetch_balance_kas = lambda b=b: b                         # noqa: E731
            check_once()
    finally:
        fetch_balance_kas, load_state, save_state, send_all = alt
    arten = ["OUTFLOW" if "OUTFLOW" in m else "INFLOW" for m in gesendet]
    ok("woche 22. bis 25.09. meldet zufluss, abfluss, zufluss",
       arten == ["INFLOW", "OUTFLOW", "INFLOW"], arten)
    ok("abfluss vom 24.09. nennt 2,000,015 KAS",
       any("2,000,015 KAS" in m for m in gesendet), gesendet)
    ok("der letzte gesehene stand ist gespeichert",
       stand["balance_kas"] == 1_525_975_596.46, stand)

    # --- abdeckungsrechnung, die zahl aus punkt 5 des pruefauftrags ---
    print("abdeckung")
    ok("ueberlappende fenster werden zusammengelegt",
       _merge([(0, 100), (50, 200), (300, 400)]) == [[0, 200], [300, 400]],
       _merge([(0, 100), (50, 200), (300, 400)]))

    def tag(d, h, m=0):
        return dt.datetime(2026, 10, d, h, m, tzinfo=dt.timezone.utc) \
                 .strftime("%Y-%m-%dT%H:%M:%SZ")

    jetzt = dt.datetime(2026, 10, 9, 0, 0, tzinfo=dt.timezone.utc).timestamp()

    # ein voller tag aus vier luecklosen fenstern
    voll = [{"start_utc": tag(8, h), "end_utc": tag(8, h + 6) if h < 18
             else tag(9, 0)} for h in (0, 6, 12, 18)]
    z = {x["tag"]: x for x in coverage_lines(voll, days=2, now=jetzt)}
    ok("vier luecklose fenster ergeben 100 prozent",
       z["2026-10-08"]["anteil_pct"] == 100.0, z.get("2026-10-08"))

    # doppelt gezaehlt waeren es 200 prozent
    doppelt = voll + voll
    z2 = {x["tag"]: x for x in coverage_lines(doppelt, days=2, now=jetzt)}
    ok("doppelte eintraege ergeben trotzdem 100 prozent",
       z2["2026-10-08"]["anteil_pct"] == 100.0, z2.get("2026-10-08"))

    # ein fenster ueber mitternacht faellt auf beide tage
    nacht = [{"start_utc": tag(7, 22), "end_utc": tag(8, 2)}]
    z3 = {x["tag"]: x for x in coverage_lines(nacht, days=3, now=jetzt)}
    ok("fenster ueber mitternacht zaehlt auf beiden tagen",
       z3["2026-10-07"]["stunden"] == 2.0 and z3["2026-10-08"]["stunden"] == 2.0,
       {k: v["stunden"] for k, v in z3.items()})

    # der gemessene istzustand vor der umstellung, 50 min je lauf
    alt = [{"start_utc": tag(8, h), "end_utc": tag(8, h, 50)}
           for h in (0, 5, 10, 15, 20)]
    z4 = {x["tag"]: x for x in coverage_lines(alt, days=2, now=jetzt)}
    ok("fuenf fenster von 50 minuten ergeben die gemessenen 17 prozent",
       z4["2026-10-08"]["anteil_pct"] == 17.4, z4.get("2026-10-08"))

    # das neue fenster, 5 h 40 min, viermal
    neu = [{"start_utc": tag(8, h), "end_utc": tag(8, h + 5, 40)}
           for h in (0, 6, 12, 18)]
    z5 = {x["tag"]: x for x in coverage_lines(neu, days=2, now=jetzt)}
    ok("vier fenster von 5 h 40 min deckten 94 prozent",
       z5["2026-10-08"]["anteil_pct"] == 94.4, z5.get("2026-10-08"))

    # Mittags, damit der laufende Tag ueberhaupt verstrichene Zeit hat.
    # Um genau Mitternacht faellt er zu Recht heraus, dann gibt es fuer ihn
    # keinen sinnvollen Anteil.
    mittag = dt.datetime(2026, 10, 9, 12, 0, tzinfo=dt.timezone.utc).timestamp()
    ok("kaputte eintraege kippen die rechnung nicht",
       coverage_lines([{"start_utc": "quatsch"}, {}, {"start_utc": tag(9, 5),
                        "end_utc": tag(9, 4)}], days=1, now=mittag)
       [0]["sekunden"] == 0)
    ok("ein tag ohne verstrichene zeit wird nicht gemeldet",
       coverage_lines(voll, days=1, now=jetzt) == [])

    ok("persist_now fasst ohne PERSIST_EACH kein git an",
       os.environ.get("PERSIST_EACH") is None and persist_now("test") is False)

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
