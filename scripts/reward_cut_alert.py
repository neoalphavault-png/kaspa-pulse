#!/usr/bin/env python3
# Kaspa Pulse - Reward Cut Alert v4
# Ablageort im Repo: scripts/reward_cut_alert.py
#
# Kaspa halbiert nicht alle vier Jahre, sondern jeden Monat ein Stueck.
# Der Zeitpunkt ist deterministisch, wir muessen ihn also nicht suchen,
# wir rechnen ihn aus einem Anker vor. Die API /info/blockreward ist
# veraltet und wird bewusst NICHT benutzt.
#
# Neu gegenueber v3 (Lesbarkeit, keine Logikaenderung):
#   1. ZAHLENDIAET. Die Vorwarnung hatte zwoelf Zahlen in fuenf Zeilen.
#      Jetzt sind es drei plus ein Vergleich. Wer mehr will, klickt die
#      Halving-Seite in der Fusszeile.
#   2. context_lines() liefert EINE Zeile statt zwei. Die Jahresausgabe
#      (542M KAS, 1,96 Prozent, Dollarwert) ist raus. Im Vorbeiscrollen
#      verarbeitet die niemand.
#   3. VERGLEICH STATT DEFINITION. "one step of twelve" und die Klippe
#      gegen die Treppe erklaeren den Mechanismus ohne eine einzige
#      Nachkommastelle.
#   4. EHRLICHER SCHLUSSSATZ. "the schedule has never moved" ist raus.
#      Der Zeitplan steht, die geschaetzten Uhrzeiten wandern, weil der
#      Schritt auf einem Block Score landet und nicht auf einer Uhr. Der
#      neue Satz sagt beides und macht aus der Abweichung ein Argument.
#
# Korrekturen 07.10.2026, nach dem Cut vom 05.10.:
#   5. DIFFERENZEN ERST RUNDEN, DANN ABZIEHEN. In context_lines() wurde die
#      Tagesemission exakt subtrahiert und erst das Ergebnis gerundet. Am
#      05.10. stand deshalb "105,844 fewer KAS", richtig sind 105,843:
#      1.885.832 minus 1.779.989. Exakt waren es 105.843,64, und genau da
#      kippt die Rundung. Es gilt jetzt dieselbe Regel wie in
#      weekly_facts.py, und zwar durch Aufruf von dessen fenster().
#   6. NAECHSTER CUT NUR MIT DATUM. utc_str() hat die Modellzeit auf die
#      Minute gedruckt. STEP ist 30 Tage und 10,5 Stunden, die Minute
#      wandert also jeden Monat um 10,5 Stunden. Das Datum traegt diese
#      Unschaerfe, die Uhrzeit nicht. In veroeffentlichten Texten steht ab
#      jetzt nur das Datum; die Modellzeit bleibt im Log.
#
# Nur Python-Standardbibliothek. weekly_facts.py liegt im selben Ordner und
# ist die gemeinsame Quelle fuer die Rundungsregel und ihre Pruefung.

import datetime as dt
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly_facts as wf  # noqa: E402

# ---------------------------------------------------------------------------
# Anker. Ein bekannter, verifizierter Cut. Alles andere wird vorgerollt.
# 05.07.2026 19:45:44 UTC, Reward danach 2.44997148 KAS pro Block.
# ---------------------------------------------------------------------------
ANCHOR_TS = 1783280744
ANCHOR_REWARD = 2.44997148
STEP = (365.25 / 12) * 86400          # ein Monat im Kaspa-Sinn
RATIO = 0.5 ** (1 / 12)               # zwoelf Schritte ergeben eine Halbierung
BPS = 10                              # Bloecke pro Sekunde seit Crescendo

API_SUPPLY = "https://api.kaspa.org/info/coinsupply"
STATE_FILE = "scripts/reward_cut_state.json"
SOMPI = 100_000_000
MAX_SUPPLY_FALLBACK = 28_704_026_601.0

PURPLE = 0x8B5CF6   # der Cut selbst
BLUE = 0x5B8DEF     # die Vorwarnung
PRE_WARN_SECONDS = 24 * 3600
SLEEP_MAX = 900     # bis zu 15 Minuten auf die Punktlandung warten

PRICE_MIN = 0.0001
PRICE_MAX = 100.0
UA = {"User-Agent": "kaspapulse-rewardcut/4.0"}


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# Preis. Kraken zuerst, echtes USD-Paar und freundlich zu Rechenzentrums-IPs.
# CoinGecko hinten, weil die Gratisstufe Cloud-IPs gerne abweist.
# Binance fehlt bewusst, die sperren US-IPs und Runner stehen meist in den USA.
# ---------------------------------------------------------------------------
def _p_kraken():
    d = get_json("https://api.kraken.com/0/public/Ticker?pair=KASUSD", timeout=12)
    for entry in (d.get("result") or {}).values():
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
    for name, fn in PRICE_SOURCES:
        try:
            p = fn()
            if PRICE_MIN < p < PRICE_MAX:
                print(f"preis {p} von {name}")
                return p
            print(f"WARN {name} lieferte unplausible {p}", file=sys.stderr)
        except Exception as e:
            print(f"WARN preisquelle {name} fehlgeschlagen: {e}", file=sys.stderr)
    print("WARN keine preisquelle erreichbar, nachricht geht ohne dollarwert raus",
          file=sys.stderr)
    return None


def fetch_supply():
    """Gibt (circulating, max) zurueck. Faellt still auf None zurueck.

    Seit v4 nicht mehr im Nachrichtentext benutzt. Bleibt stehen, weil die
    Zahl fuer kuenftige Auswertungen gebraucht wird und der Abruf nichts
    kostet, solange ihn niemand aufruft.
    """
    try:
        d = get_json(API_SUPPLY)
        circ = int(d["circulatingSupply"]) / SOMPI
        mx = float(d.get("maxSupply", 0)) / SOMPI or MAX_SUPPLY_FALLBACK
        return circ, mx
    except Exception as e:
        print(f"WARN supply nicht abrufbar: {e}", file=sys.stderr)
        return None, None


# ---------------------------------------------------------------------------
# Zeitplan
# ---------------------------------------------------------------------------
def schedule(now=None):
    """Liefert (naechster_cut_ts, reward_davor, reward_danach)."""
    now = now if now is not None else time.time()
    n = 0
    while ANCHOR_TS + STEP * (n + 1) <= now:
        n += 1
    # n = Anzahl vollendeter Schritte seit dem Anker
    current = ANCHOR_REWARD * RATIO ** n
    next_ts = ANCHOR_TS + STEP * (n + 1)
    nxt = ANCHOR_REWARD * RATIO ** (n + 1)
    return next_ts, current, nxt


def load_state():
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_embed(title, description, color, price=None):
    url = os.environ.get("DISCORD_WEBHOOK", "").strip()
    foot = "kaspa pulse · emission schedule · kaspapulse.com/kaspa-halving.html"
    if price:
        foot = (f"kaspa pulse · emission schedule · KAS at {fmt_price(price)} · "
                "kaspapulse.com/kaspa-halving.html")
    payload = {"embeds": [{
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": foot},
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


def fmt_price(p):
    return f"${p:,.4f}" if p < 1 else f"${p:,.2f}"


def fmt_usd(v):
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


def daily(reward):
    return reward * BPS * 86400


def modell_str(ts):
    """Die vorgerollte Modellzeit auf die Minute. NUR FUERS LOG.

    Gehoert in keinen veroeffentlichten Text: der Schritt landet auf einem
    Block Score und nicht auf einer Uhr, und STEP ist 30 Tage 10,5 Stunden
    lang. Die Minute wandert damit jeden Monat.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


def date_str(ts):
    """Nur das Datum. Das ist die belastbare Aussage, siehe modell_str."""
    d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    return f"{d.day} {d.strftime('%B').lower()} {d.year}"


def context_lines(reward_before, reward_after, price):
    """Genau eine Zeile. Uebersetzt den Reward in etwas Vorstellbares.

    Vorher standen hier zwei Zeilen mit sechs Zahlen, darunter die
    Jahresausgabe. Die ist raus. Sie ist richtig, aber sie beantwortet
    keine Frage, die jemand beim Lesen tatsaechlich hat.

    Die Differenz kommt aus weekly_facts.fenster(): erst beide Endpunkte
    runden, dann abziehen. Wer die beiden gedruckten Tageszahlen selbst
    subtrahiert, muss auf dieselbe Zahl kommen. Vorher wurde exakt
    subtrahiert und erst danach gerundet, das ergab am 05.10. 105.844
    statt 105.843.

    reward_before wird uebergeben und nicht mehr aus reward_after
    zurueckgerechnet. Die alte Division durch RATIO war eine zweite,
    unnoetige Rundungsquelle.
    """
    f = wf.fenster(daily(reward_before), daily(reward_after))
    drop = f["differenz"]
    usd = f", about {fmt_usd(drop * price)} at today's price" if price else ""
    return (f"in plain terms, the network creates about **{fmt(drop)} fewer KAS "
            f"every day** from now on{usd}.")


def build_cut(before, after, ts, price):
    """Text des Cut-Posts. Reine Funktion, damit der Selbsttest ihn lesen
    kann, ohne einen Webhook zu brauchen."""
    pct = (1 - after / before) * 100
    return (
        "🟣 it happened. the reward just got cut",
        f"the block reward went from **{before:.8f} KAS** to **{after:.8f} KAS**. "
        f"that is **{pct:.2f} percent** less, and it is the same number this "
        "channel posted yesterday, down to the eighth decimal.\n\n"
        "no cliff, no shock. one step down a staircase that takes twelve steps "
        "to reach the half.\n\n"
        f"{context_lines(before, after, price)}\n\n"
        f"the next step is estimated for {date_str(schedule(ts + 60)[0])}.",
        PURPLE,
    )


def build_prewarn(before, after, ts, price):
    """Text der Vorwarnung. Reine Funktion, siehe build_cut."""
    pct = (1 - after / before) * 100
    return (
        "🔵 heads up. the reward gets cut tomorrow",
        f"the block reward drops from **{before:.8f} KAS** to **{after:.8f} KAS**. "
        f"that is **{pct:.2f} percent** less.\n\n"
        "this is not a halving. it is one step of twelve. walk down all twelve "
        "and the reward has halved, then the count starts again.\n\n"
        "bitcoin does the same thing once every four years, all at once. kaspa "
        "spreads it across the year, so no miner wakes up to half the revenue.\n\n"
        f"{context_lines(before, after, price)}\n\n"
        f"the estimate right now is {date_str(ts)}. the day can still shift a "
        "little, because the step lands on a block score and not on a clock. "
        "the number does not shift at all.",
        BLUE,
    )


def announce_cut(before, after, ts, price):
    title, body, color = build_cut(before, after, ts, price)
    send_embed(title, body, color, price=price)


def announce_prewarn(before, after, ts, price):
    title, body, color = build_prewarn(before, after, ts, price)
    send_embed(title, body, color, price=price)


# ---------------------------------------------------------------------------
# Selbsttest. Prueft die beiden Korrekturen gegen die Zahlen vom 05.10.2026
# und laesst den fertigen Text durch die Pruefung von weekly_facts laufen.
# ---------------------------------------------------------------------------

# Der Cut vom 05.10.2026 war Schritt 3 nach dem Anker, Modellzeit
# 2026-10-05 03:15:44 UTC. Davor galt Reward 2.18267645, danach 2.06017224.
CUT_0510_TS = ANCHOR_TS + STEP * 3
MONAT_RE = r"\b\d{1,2}:\d{2}\b"


def selbsttest():
    import re
    fehler = []

    def ok(was, bedingung, extra=""):
        if bedingung:
            print("  ok   %s" % was)
        else:
            fehler.append(was)
            print("  FEHL %s %s" % (was, extra))

    print("konstanten gegen weekly_facts")
    for name in ("ANCHOR_TS", "ANCHOR_REWARD", "STEP", "RATIO", "BPS"):
        ok("%s gleich" % name, globals()[name] == getattr(wf, name),
           "%r gegen %r" % (globals()[name], getattr(wf, name)))
    ok("daily() gleich emission_je_tag()",
       abs(daily(2.18267645) - wf.emission_je_tag(2.18267645)) < 1e-6)

    print("\nder cut vom 05.10.2026")
    kurz_danach = CUT_0510_TS + 60
    next_ts, before, after = schedule(kurz_danach)
    reward_vor_cut = before / RATIO
    ok("reward vor dem cut 2.18267645",
       abs(reward_vor_cut - 2.18267645) < 1e-7, "%.8f" % reward_vor_cut)
    ok("reward nach dem cut 2.06017224",
       abs(before - 2.06017224) < 1e-7, "%.8f" % before)

    d_vor, d_nach = daily(reward_vor_cut), daily(before)
    ok("emission vorher rundet auf 1.885.832", round(d_vor) == 1_885_832,
       "%.2f" % d_vor)
    ok("emission nachher rundet auf 1.779.989", round(d_nach) == 1_779_989,
       "%.2f" % d_nach)
    f = wf.fenster(d_vor, d_nach)
    ok("differenz nach der regel ist 105.843", f["differenz"] == 105_843,
       str(f["differenz"]))
    ok("exakte differenz ist 105.843,64 und wuerde falsch auf 105.844 runden",
       f["differenz_exakt"] == 105843.64 and round(d_vor - d_nach) == 105_844,
       str(f["differenz_exakt"]))

    print("\ntexte des 05.10.-cuts")
    titel, text, _ = build_cut(reward_vor_cut, before, CUT_0510_TS, None)
    ok("text nennt 105,843", "105,843" in text)
    ok("text nennt NICHT 105,844", "105,844" not in text)
    ok("kein doppelpunkt-zeitstempel im text",
       not re.search(MONAT_RE, text), re.findall(MONAT_RE, text))
    ok("naechster schritt steht als 4 november 2026 im text",
       "4 november 2026" in text, text[-120:])

    print("\ntexte der vorwarnung auf den 04.11.2026")
    vor_ts = ANCHOR_TS + STEP * 4
    nts, b2, a2 = schedule(vor_ts - PRE_WARN_SECONDS + 60)
    ok("vorwarnung zielt auf den 04.11.2026",
       dt.datetime.fromtimestamp(nts, dt.timezone.utc).date()
       == dt.date(2026, 11, 4), modell_str(nts))
    titel2, text2, _ = build_prewarn(b2, a2, nts, None)
    ok("kein doppelpunkt-zeitstempel in der vorwarnung",
       not re.search(MONAT_RE, text2), re.findall(MONAT_RE, text2))
    ok("vorwarnung nennt das datum 4 november 2026",
       "4 november 2026" in text2)
    ok("vorwarnung spricht nicht mehr von der minute",
       "that minute" not in text2)
    f2 = wf.fenster(daily(b2), daily(a2))
    ok("vorwarnung nennt die differenz 99.903",
       f2["differenz"] == 99_903 and "99,903" in text2, str(f2["differenz"]))

    print("\npruefung von weekly_facts ueber die fertigen texte")
    for name, t in (("cut", text), ("vorwarnung", text2)):
        befunde = wf.pruefe_text(t)
        ok("%s ohne befund" % name, not befunde,
           "; ".join("%s-%s!=%s" % (b["von"], b["bis"], b["gedruckt"])
                     for b in befunde))

    print("\ngegenprobe: die alte rechnung faellt auf")
    ok("weekly_facts findet die alte zahl, wenn die endpunkte dabeistehen",
       bool(wf.pruefe_text("emission 1,885,832 to 1,779,989 kas, "
                           "105,844 fewer new coins a day")))
    ok("der reparierte satz ist sauber",
       not wf.pruefe_text("emission 1,885,832 to 1,779,989 kas, "
                          "105,843 fewer new coins a day"))

    print()
    if fehler:
        print("%d FEHLER: %s" % (len(fehler), ", ".join(fehler)))
        return 1
    print("alle testfaelle bestanden")
    return 0


def main():
    now = time.time()
    next_ts, before, after = schedule(now)
    state = load_state()
    wrote = False

    # 1. Punktlandung. Der Cut kommt gleich, wir warten ihn ab.
    wait = next_ts - now
    if 0 < wait <= SLEEP_MAX:
        print(f"cut in {wait:.0f} sekunden, warte auf die punktlandung")
        time.sleep(wait + 2)
        now = time.time()
        next_ts, before, after = schedule(now)

    # 2. Ist ein Cut faellig, der noch nicht gemeldet wurde?
    #    schedule() liefert nach dem Cut bereits den naechsten Termin, also
    #    rechnen wir den gerade vergangenen zurueck.
    last_ts = next_ts - STEP
    if now >= last_ts and state.get("announced_cut_ts") != int(last_ts):
        if state.get("announced_cut_ts") is None and now - last_ts > 6 * 3600:
            # Erstlauf und der Cut liegt lange zurueck. Nicht nachtraeglich
            # posten, nur merken. Alte Nachrichten sind keine Nachrichten.
            print("erstlauf, alter cut wird nur gemerkt")
        else:
            price = fetch_price_usd()
            announce_cut(before / RATIO, before, last_ts, price)
            print(f"CUT gemeldet, {before:.8f} KAS")
        state["announced_cut_ts"] = int(last_ts)
        wrote = True

    # 3. Vorwarnung, genau einmal je Termin.
    left = next_ts - now
    if 0 < left <= PRE_WARN_SECONDS and state.get("prewarned_cut_ts") != int(next_ts):
        price = fetch_price_usd()
        announce_prewarn(before, after, next_ts, price)
        state["prewarned_cut_ts"] = int(next_ts)
        wrote = True
        print(f"VORWARNUNG gemeldet, cut in {left/3600:.1f} stunden")

    if wrote:
        save_state(state)
    else:
        print(f"nichts zu tun. naechster cut {date_str(next_ts)} "
              f"(modellzeit {modell_str(next_ts)}, nur fuers log), "
              f"in {left/3600:.1f} stunden, reward {before:.8f} KAS")

    print(f"STATE_CHANGED={'1' if wrote else '0'}")


if __name__ == "__main__":
    if "--selbsttest" in sys.argv or "--selftest" in sys.argv:
        sys.exit(selbsttest())
    main()
