#!/usr/bin/env python3
"""
kaspa pulse - kursdatenlogger fuer KASPA WEEKLY
holt die tagesreihe fuer kaspa und bitcoin und schreibt data/kas-candles.json.
daraus baut die wochenanalyse ihre charts. der logger bewertet nichts, er
sammelt nur.

quelle ist coingecko, derselbe dienst, den number_of_day_data.py schon fuer
die preise benutzt und der aus github actions erreichbar ist. tageskerzen
seit handelsbeginn november 2021, fuer kaspa preis und volumen, fuer bitcoin
nur der preis, den brauchen wir fuer das kas gegen btc verhaeltnis.

unsere wochendefinition, und sie steht bewusst hier im code: eine woche endet
sonntag 00:00 utc. das ist unsere eigene festlegung, damit die sonntagabend
eingesprochene folge auf abgeschlossenen zahlen sitzt. die definition wird
auf der seite neben die zahlen gedruckt, wie immer.

regeln aus dem haus:
- faellt die datenbeschaffung aus, bricht der lauf mit fehler ab. lieber
  keine datei als eine mit luecken, die keiner bemerkt.
- die datei wird komplett neu geschrieben, nie fortgeschrieben. die quelle
  liefert die volle historie, damit gibt es keinen driftenden zustand.
- keine geheimnisse. der endpunkt ist oeffentlich und braucht keinen key.

lokal (im sandkasten geht kein netz, dort nur --selftest):
    python3 scripts/kas_candles.py --selftest
in github actions:
    python3 scripts/kas_candles.py --out data/kas-candles.json
"""
import argparse
import datetime as dt
import json
import sys

UA = "kaspa-pulse-candles/1.0 (+https://kaspapulse.com)"
TIMEOUT = 30
RETRIES = 3
CG = "https://api.coingecko.com/api/v3/coins/%s/market_chart?vs_currency=usd&days=max&interval=daily"
# handelsbeginn. alles davor waere ein datenfehler der quelle.
KAS_FIRST = dt.date(2021, 11, 1)
# plausibilitaetsfenster, dieselben grenzen wie im number-of-day generator.
KAS_WINDOW = (0.0001, 100.0)
BTC_WINDOW = (1000.0, 10000000.0)


class Stop(Exception):
    """Abbruch mit Klartext."""


def http_json(url, tries=RETRIES):
    import time
    import urllib.request
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(5 * (i + 1))
    raise Stop("abruf fehlgeschlagen %s (%s)" % (url, last))


def daily_series(coin, price_window, want_volume):
    """
    Tagesreihe von coingecko. der letzte punkt ist der laufende tag und
    fliegt raus, wir speichern nur abgeschlossene tage.
    """
    d = http_json(CG % coin)
    prices = d.get("prices") or []
    vols = {int(ts): v for ts, v in (d.get("total_volumes") or [])}
    if len(prices) < 300:
        raise Stop("%s liefert nur %d tagespunkte, das ist keine historie"
                   % (coin, len(prices)))
    lo, hi = price_window
    out = []
    for ts, price in prices[:-1]:
        day = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).date()
        p = float(price)
        if not (lo <= p <= hi):
            raise Stop("%s preis %s am %s ausserhalb des fensters"
                       % (coin, p, day))
        row = [str(day), round(p, 8 if p < 1 else 2)]
        if want_volume:
            row.append(round(float(vols.get(int(ts), 0.0)), 0))
        out.append(row)
    # streng aufsteigend und ohne doppelte tage, sonst stimmen die wochen nicht
    days = [r[0] for r in out]
    if days != sorted(set(days)):
        # coingecko liefert gelegentlich zwei punkte fuer denselben tag.
        # der letzte gewinnt, das ist der spaetere messwert.
        dedup = {}
        for r in out:
            dedup[r[0]] = r
        out = [dedup[k] for k in sorted(dedup)]
    return out


def weekly_close(rows):
    """
    Wochenschluesse nach unserer definition, woche endet sonntag 00:00 utc.
    der schluss einer woche ist also der tageswert vom samstag. angebrochene
    erste und letzte wochen fliegen raus.
    """
    # doppelte tage abwehren, egal woher die reihe kommt. der letzte gewinnt.
    uniq = {}
    for r in rows:
        uniq[r[0]] = r
    weeks = {}
    for r in (uniq[k] for k in sorted(uniq)):
        day = dt.date.fromisoformat(r[0])
        # die woche laeuft sonntag bis samstag. week_start ist der sonntag.
        week_start = day - dt.timedelta(days=(day.weekday() + 1) % 7)
        weeks.setdefault(str(week_start), []).append(r)
    out = []
    for wk in sorted(weeks):
        rows_ = weeks[wk]
        # voll ist eine woche nur mit allen sieben tagen. eine angebrochene
        # woche, die zufaellig an einem samstag endet, ist keine volle.
        if len(rows_) != 7:
            continue
        out.append([wk] + rows_[-1][1:])
    return out


def build():
    kas = daily_series("kaspa", KAS_WINDOW, want_volume=True)
    btc = daily_series("bitcoin", BTC_WINDOW, want_volume=False)
    first = dt.date.fromisoformat(kas[0][0])
    if first > KAS_FIRST + dt.timedelta(days=120):
        raise Stop("kaspa historie beginnt erst am %s, erwartet wird "
                   "spaetestens anfang 2022" % first)
    kas_w = weekly_close(kas)
    if len(kas_w) < 150:
        raise Stop("nur %d volle kaspa wochen, das reicht nicht" % len(kas_w))
    return {
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M utc"),
        "source": "coingecko daily series, closed days only",
        "week_rule": "a week ends sunday 00:00 utc, the close is saturday's reading",
        "kas_daily": kas,      # [datum, schluss, volumen usd]
        "btc_daily": btc,      # [datum, schluss]
        "kas_weekly": kas_w,   # [wochenstart sonntag, schluss samstag, volumen usd]
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/kas-candles.json")
    a = ap.parse_args()
    data = build()
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print("geschrieben %s, %d kas tage, %d btc tage, %d volle wochen"
          % (a.out, len(data["kas_daily"]), len(data["btc_daily"]),
             len(data["kas_weekly"])))
    return 0


def run_selftest():
    fails = []

    def ok(what, cond, extra=""):
        if cond:
            print("  ok   %s" % what)
        else:
            fails.append(what)
            print("  FEHL %s %s" % (what, extra))

    # kuenstliche tagesreihe ueber drei volle wochen plus angebrochenen rand
    rows = []
    d = dt.date(2026, 1, 1)  # ein donnerstag
    v = 100.0
    while d <= dt.date(2026, 1, 27):
        rows.append([str(d), round(v, 2), 1000.0])
        v += 1.0
        d += dt.timedelta(days=1)
    w = weekly_close(rows)
    ok("angebrochene wochen fliegen raus", len(w) == 3, len(w))
    ok("die wochenmarke ist der sonntag",
       all(dt.date.fromisoformat(x[0]).weekday() == 6 for x in w))
    # volle wochen im testfenster enden am 10., 17. und 24. januar,
    # die reihe startet bei 100 am 1. januar und steigt um 1 pro tag.
    ok("wochenschluss traegt samstagszahlen",
       [x[1] for x in w] == [109.0, 116.0, 123.0], [x[1] for x in w])
    dup = rows + [rows[5]]
    ok("doppelte tage werden bereinigt",
       len(weekly_close(sorted(dup))) == 3)
    print("")
    if fails:
        print("%d fehlgeschlagen %s" % (len(fails), fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    try:
        sys.exit(main())
    except Stop as e:
        print("ABBRUCH " + str(e), file=sys.stderr)
        sys.exit(1)
