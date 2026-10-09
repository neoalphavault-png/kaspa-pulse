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
# auf dem server c2 liegt der stand ausserhalb des repos, siehe deploy/c2/entity-x-alarm/
STATE_FILE = os.environ.get("ENTITY_X_STATE_FILE", "scripts/entity_x_state.json")
# Abdeckung (Ben, 07.10.2026). Auf der Startseite steht "every 30 minutes,
# around the clock". Damit das nachpruefbar stimmt, wird jede Minute mit
# einer erfolgreichen Pruefung markiert, je UTC-Tag als 1440 Zeichen
# ("1" beobachtet, "." nicht). Ziel mindestens 95 % je Tag, groesste
# Luecke unter 30 Minuten. Auf dem Server c2 zeigt ABDECKUNG_FILE auf
# eine lokale Datei.
ABDECKUNG_FILE = os.environ.get("ABDECKUNG_FILE", "data/entity-x-abdeckung.json")
ABDECKUNG_TAGE = 35
ZIEL_PCT = 95.0
ZIEL_LUECKE_MIN = 30
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
# Wortregel (Ben, 08.10.2026): auch buy, purchase und sale, ohne Ausnahme.
BANNED_CLAIMS = ["sold", "sell", "selling", "bought", "buying", "buy", "purchase", "sale", "stacking",
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
        "an inflow is a transfer, the chain shows the movement only.\n"
        "check it yourself at <https://kaspapulse.com/entity-x.html>"
    )


def _git(*args):
    return subprocess.run(("git",) + args, capture_output=True, text=True)


def persist_now(grund):
    """Vergleichsstand sofort festschreiben, nicht erst am Jobende.

    Seit dem Dauerlauf (#52) laeuft ein Job 5 h 35 min. Committet wird erst
    danach. Bricht der Lauf ab, bevor der letzte Schritt kommt, dann ist
    scripts/entity_x_state.json von bis zu 5 h 35 min Bewegung verloren.
    Der naechste Lauf vergleicht dann gegen den alten Stand und meldet
    dieselbe Bewegung ein zweites Mal.

    Die concurrency group verhindert, dass zwei Laeufe gleichzeitig
    denselben Zufluss sehen. Gegen diesen Fall hilft sie nicht, denn hier
    laufen die beiden Laeufe nacheinander.

    Ein Alarm ist selten, deshalb wird genau dann gepusht und nicht im
    Minutentakt. Die Abdeckungsdatei kommt mit, weil sie ohnehin
    danebenliegt; zwischen zwei Alarmen bleibt sie weiter dem Schritt am
    Jobende ueberlassen.

    Nur aktiv, wenn PERSIST_EACH gesetzt ist. Lokale Laeufe und der
    Selbsttest fassen git nicht an.
    """
    if not os.environ.get("PERSIST_EACH"):
        return False
    return festschreiben(grund)


def abdeckung_vereinen(a, b):
    """Je Tag und Minute beobachtet, wenn einer der beiden Staende sie
    beobachtet hat. So geht keine Minute verloren, egal wer zuerst pusht."""
    tage = {}
    for tag in set(a["tage"]) | set(b["tage"]):
        x = a["tage"].get(tag) or "." * 1440
        y = b["tage"].get(tag) or "." * 1440
        tage[tag] = "".join("1" if "1" in (p, q) else "." for p, q in zip(x, y))
    return {"tage": tage}


def festschreiben(grund, versuche=3):
    """Vergleichsstand und Abdeckung nach origin/main, ohne Rebase-Konflikt
    (Check-in 08.10.2026: jeder zweite Lauf scheiterte am Jobende an einem
    Konflikt in der Abdeckungsdatei und verlor damit Abdeckung und Stand).

    Der eigene Vergleichsstand ist der neueste, er gewinnt. Die Abdeckung
    wird mit dem Stand auf main vereinigt. Dann wird auf den frischen
    main-Stand committet und gepusht, bei Ablehnung von vorn."""
    _git("config", "user.name", "kaspa-pulse-bot")
    _git("config", "user.email", "bot@kaspapulse.com")
    try:
        with open(STATE_FILE) as f:
            state_text = f.read()
    except FileNotFoundError:
        state_text = None
    eigene = abdeckung_laden()
    for n in range(versuche):
        _git("rebase", "--abort")
        if _git("fetch", "origin", "main").returncode != 0:
            continue
        _git("reset", "--hard", "origin/main")
        abdeckung_speichern(abdeckung_vereinen(abdeckung_laden(), eigene))
        if state_text is not None:
            with open(STATE_FILE, "w") as f:
                f.write(state_text)
        _git("add", "--", STATE_FILE, ABDECKUNG_FILE)
        if _git("diff", "--staged", "--quiet").returncode == 0:
            print("stand und abdeckung schon auf main (%s)" % grund)
            return True
        _git("commit", "-m", "entity x state update, %s [bot]" % grund)
        if _git("push", "origin", "HEAD:main").returncode == 0:
            print("stand und abdeckung festgeschrieben (%s)" % grund)
            return True
    print("WARN festschreiben nach %d versuchen gescheitert (%s)" % (versuche, grund), file=sys.stderr)
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


# ---------------------------------------------------------------- abdeckung

def abdeckung_laden(pfad=None):
    try:
        with open(pfad or ABDECKUNG_FILE) as f:
            d = json.load(f)
        return d if isinstance(d.get("tage"), dict) else {"tage": {}}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return {"tage": {}}


def markiere(ab, ts):
    """Die Minute, in der ts liegt, gilt als beobachtet."""
    t = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    tag = t.date().isoformat()
    bits = list(ab["tage"].get(tag) or "." * 1440)
    bits[t.hour * 60 + t.minute] = "1"
    ab["tage"][tag] = "".join(bits)


def abdeckung_speichern(ab, pfad=None):
    pfad = pfad or ABDECKUNG_FILE
    tage = sorted(ab["tage"])[-ABDECKUNG_TAGE:]
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    zeilen = ['  %s: %s' % (json.dumps(t), json.dumps(ab["tage"][t])) for t in tage]
    with open(pfad, "w") as f:
        f.write('{\n "zweck": "entity x alarm, beobachtete minuten je utc-tag, 1 beobachtet, . nicht",\n'
                ' "tage": {\n' + ",\n".join(zeilen) + "\n }\n}\n")


def tageswert(bits, bis_minute=1440):
    """(prozent, beobachtet, minuten, groesste luecke, beginn der luecke)
    ueber die ersten bis_minute minuten des tages."""
    b = bits[:bis_minute]
    n = len(b)
    beob = b.count("1")
    luecke, beginn, lauf, start = 0, None, 0, 0
    for i, c in enumerate(b):
        if c == "1":
            lauf = 0
            continue
        if lauf == 0:
            start = i
        lauf += 1
        if lauf > luecke:
            luecke, beginn = lauf, start
    return (round(100.0 * beob / n, 1) if n else 0.0), beob, n, luecke, beginn


def abdeckung_bericht(ab, jetzt=None, tage=2):
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    heute = jetzt.date().isoformat()
    zeilen = []
    for tag in sorted(ab["tage"])[-tage:]:
        bis = jetzt.hour * 60 + jetzt.minute + 1 if tag == heute else 1440
        pct, beob, n, luecke, beginn = tageswert(ab["tage"][tag], bis)
        lz = ("%02d.%02d bis %02d.%02d utc" % (beginn // 60, beginn % 60, (beginn + luecke) // 60 % 24,
                                               (beginn + luecke) % 60)) if luecke else "keine"
        ziel = "ziel erreicht" if pct >= ZIEL_PCT and luecke < ZIEL_LUECKE_MIN else "UNTER ZIEL"
        zeilen.append("abdeckung %s%s %.1f%% beobachtet (%d von %d minuten), groesste luecke %d min (%s), %s"
                      % (tag, " bis jetzt" if tag == heute else "", pct, beob, n, luecke, lz, ziel))
    return zeilen


def naechste_minute(jetzt, versatz=5):
    """Sekunden bis zur naechsten vollen Minute plus versatz."""
    return 60 - (jetzt % 60) + versatz


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
    fehler = 0
    ab = abdeckung_laden()

    while True:
        checks += 1
        try:
            if check_once():
                alerts += 1
            # nur eine erfolgreiche pruefung zaehlt als beobachtete minute
            markiere(ab, time.time())
            abdeckung_speichern(ab)
        except Exception as exc:  # noqa: BLE001
            # ein einzelner fehlschlag darf die schleife nicht beenden,
            # sonst reisst eine api-stoerung das ganze fenster.
            fehler += 1
            print("pruefung fehlgeschlagen (%s)" % exc, file=sys.stderr)

        elapsed = time.monotonic() - started
        if elapsed + interval >= loop:
            break
        # im minutentakt an der vollen minute ausgerichtet, damit keine
        # minute durchrutscht, weil sich die pruefzeit langsam verschiebt
        time.sleep(naechste_minute(time.time()) if interval == 60 else interval)

    print("fertig nach %d pruefungen in %.0f sekunden, %d alarme, %d fehlgeschlagen"
          % (checks, time.monotonic() - started, alerts, fehler))


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
    raises("wortregel, purchase wird abgefangen", "this looks like a purchase")
    raises("wortregel, sale wird abgefangen", "a deposit to an exchange is not a sale")
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

    ok("persist_now fasst ohne PERSIST_EACH kein git an",
       os.environ.get("PERSIST_EACH") is None and persist_now("test") is False)

    # abdeckung
    ab = {"tage": {}}
    t0 = dt.datetime(2026, 10, 7, 0, 0, 30, tzinfo=dt.timezone.utc).timestamp()
    for m in list(range(0, 600)) + list(range(625, 1440)):
        markiere(ab, t0 + m * 60)
    pct, beob, n, luecke, beginn = tageswert(ab["tage"]["2026-10-07"])
    ok("abdeckung zaehlt beobachtete minuten", beob == 1415 and n == 1440, (beob, n))
    ok("groesste luecke und ihr beginn", luecke == 25 and beginn == 600, (luecke, beginn))
    zeile = abdeckung_bericht(ab, jetzt=dt.datetime(2026, 10, 8, 1, 0, tzinfo=dt.timezone.utc))[0]
    ok("bericht mit prozent und luecke", "98.3% beobachtet" in zeile and "25 min" in zeile
       and "ziel erreicht" in zeile, zeile)
    ab2 = {"tage": {"2026-10-07": "1" * 600 + "." * 40 + "1" * 800}}
    ok("luecke ab 30 minuten verfehlt das ziel", "UNTER ZIEL" in abdeckung_bericht(
        ab2, jetzt=dt.datetime(2026, 10, 8, 1, 0, tzinfo=dt.timezone.utc))[0])
    heute = abdeckung_bericht({"tage": {"2026-10-07": "1" * 61 + "." * 1379}},
                              jetzt=dt.datetime(2026, 10, 7, 1, 0, 40, tzinfo=dt.timezone.utc))[0]
    ok("heute zaehlt nur bis jetzt", "bis jetzt 100.0%" in heute, heute)
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "ab.json")
    abdeckung_speichern(ab, tmp)
    ok("abdeckung kommt aus der datei zurueck", abdeckung_laden(tmp) == {"tage": ab["tage"]}
       or abdeckung_laden(tmp)["tage"] == ab["tage"])
    ok("naechste volle minute", naechste_minute(120.0) == 65 and naechste_minute(179.5) == 5.5)

    # festschreiben gegen einen schnelleren push, ohne konflikt (08.10.2026)
    import tempfile
    global STATE_FILE, ABDECKUNG_FILE
    alt = (STATE_FILE, ABDECKUNG_FILE, os.getcwd())
    with tempfile.TemporaryDirectory() as tmp:
        def g(cwd, *a):
            return subprocess.run(("git",) + a, cwd=cwd, capture_output=True, text=True)
        g(tmp, "init", "-q", "--bare", "-b", "main", "origin.git")
        for wer in ("a", "b"):
            g(tmp, "clone", "-q", "origin.git", wer)
            g(os.path.join(tmp, wer), "config", "user.email", "t@t")
            g(os.path.join(tmp, wer), "config", "user.name", "t")
        a_dir, b_dir = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        os.makedirs(os.path.join(a_dir, "data"))
        os.makedirs(os.path.join(a_dir, "scripts"))
        STATE_FILE, ABDECKUNG_FILE = "scripts/entity_x_state.json", "data/entity-x-abdeckung.json"
        os.chdir(a_dir)
        abdeckung_speichern({"tage": {"2026-10-08": "." * 1440}})
        open(STATE_FILE, "w").write('{"balance_kas": 1}')
        g(a_dir, "add", "-A"); g(a_dir, "commit", "-qm", "start"); g(a_dir, "push", "-q", "origin", "HEAD:main")
        g(b_dir, "pull", "-q", "origin", "main")
        # a beobachtet minute 10 und pusht zuerst
        ab = abdeckung_laden(); markiere(ab, dt.datetime(2026, 10, 8, 0, 10, tzinfo=dt.timezone.utc).timestamp())
        abdeckung_speichern(ab); open(STATE_FILE, "w").write('{"balance_kas": 2}')
        ok_a = festschreiben("test a")
        # b hat den alten stand, beobachtet minute 20, neuerer vergleichsstand
        os.chdir(b_dir)
        ab = abdeckung_laden(); markiere(ab, dt.datetime(2026, 10, 8, 0, 20, tzinfo=dt.timezone.utc).timestamp())
        abdeckung_speichern(ab); open(STATE_FILE, "w").write('{"balance_kas": 3}')
        ok_b = festschreiben("test b")
        g(tmp, "clone", "-q", "origin.git", "c")
        os.chdir(os.path.join(tmp, "c"))
        bits = abdeckung_laden()["tage"]["2026-10-08"]
        ok("festschreiben ohne konflikt, minuten beider laeufe vereinigt, neuester stand gewinnt",
           ok_a and ok_b and bits[10] == "1" and bits[20] == "1" and bits.count("1") == 2
           and open(STATE_FILE).read() == '{"balance_kas": 3}')
    STATE_FILE, ABDECKUNG_FILE = alt[0], alt[1]
    os.chdir(alt[2])
    ok("vereinen je minute", abdeckung_vereinen({"tage": {"t": "1.." + "." * 1437}},
                                                {"tage": {"t": ".1." + "." * 1437, "u": "1" * 1440}})
       == {"tage": {"t": "11." + "." * 1437, "u": "1" * 1440}})

    print("")
    if fails:
        print("%d fehlgeschlagen %s" % (len(fails), fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    if "--festschreiben" in sys.argv:
        sys.exit(0 if festschreiben("jobende") else 1)
    if "--abdeckung" in sys.argv:
        print("\n".join(abdeckung_bericht(abdeckung_laden())) or "abdeckung, noch keine daten")
        sys.exit(0)
    main()
