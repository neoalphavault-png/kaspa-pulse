#!/usr/bin/env python3
# Kaspa Pulse - Entity X Cost Basis v2
# Ablageort im Repo: scripts/entity_x_costbasis.py
#
# Was das Ding macht:
#   1. Zieht die komplette Transaktionshistorie der Entity-X-Adresse ueber
#      api.kaspa.org und filtert die echten Zufluesse heraus. Abfluesse
#      werden einzeln mit Datum, Menge und Transaktionsnummer festgehalten.
#   2. Holt die taegliche Preishistorie von KuCoin, luecken werden mit MEXC
#      und danach Bybit gefuellt. Bybit sperrt Rechenzentrums-IPs und
#      antwortet vom GitHub-Runner mit 403, steht deshalb ganz hinten.
#      Benutzt wird NICHT der Schlusskurs, sondern der volumen-
#      gewichtete Tagesdurchschnitt (Umsatz geteilt durch Volumen). Wer an
#      einem Tag kauft, kauft nicht um Mitternacht.
#   3. Rechnet daraus einen gewichteten Einstandspreis und schreibt alles
#      nach data/entity-x-costbasis.json, damit die Seite es lesen kann.
#
# Das ist unsere eigene Rechnung. Keine fremde Zahl, keine Schaetzung.
# Wenn zu viele Preistage fehlen, setzt das Skript "reliable": false und
# die Seite blendet die Kachel aus. Lieber keine Zahl als eine falsche.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import calendar
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
OUT_FILE = "data/entity-x-costbasis.json"

API = "https://api.kaspa.org"
SOMPI = 100_000_000
UA = {"User-Agent": "kaspapulse-costbasis/1.0"}

PAGE_LIMIT = 500          # Maximum, das die API pro Seite hergibt
MAX_PAGES = 200           # Notbremse gegen Endlosschleifen
PRICE_MIN = 0.0001
PRICE_MAX = 100.0
DUST_KAS = 1.0            # alles darunter ist kein Kauf, sondern Rauschen

# Ab wann trauen wir dem Ergebnis nicht mehr. Wenn fuer mehr als zwei Prozent
# der gekauften Coins kein Tagespreis existiert, ist der Schnitt wertlos.
MAX_MISSING_SHARE = 0.02


def get_json(url, timeout=30, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(2 * (i + 1))
    raise last


def day(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


# ---------------------------------------------------------------------------
# 1. Transaktionen
# ---------------------------------------------------------------------------
def fetch_transactions():
    """Alle Transaktionen der Adresse, neueste zuerst.

    Bevorzugt die seitenbasierte Route, weil offset-Paging bei grossen
    Adressen abbricht. Faellt still auf die alte Route zurueck.
    """
    txs = []
    seen = set()
    before = 0
    for page in range(MAX_PAGES):
        url = (f"{API}/addresses/{ADDRESS}/full-transactions-page"
               f"?limit={PAGE_LIMIT}&resolve_previous_outpoints=light")
        if before:
            url += f"&before={before}"
        try:
            batch = get_json(url)
        except Exception as e:
            if page == 0:
                print(f"WARN seitenroute nicht verfuegbar ({e}), "
                      f"versuche offset-paging", file=sys.stderr)
                return fetch_transactions_offset()
            raise
        if not batch:
            break
        fresh = 0
        oldest = None
        for t in batch:
            tid = t.get("transaction_id") or t.get("subnetwork_id", "") + str(t.get("block_time"))
            bt = t.get("block_time") or 0
            if oldest is None or bt < oldest:
                oldest = bt
            if tid in seen:
                continue
            seen.add(tid)
            txs.append(t)
            fresh += 1
        print(f"seite {page + 1}: {len(batch)} transaktionen, {fresh} neu")
        if len(batch) < PAGE_LIMIT or fresh == 0 or not oldest:
            break
        before = oldest
    return txs


def fetch_transactions_offset():
    txs = []
    for page in range(MAX_PAGES):
        url = (f"{API}/addresses/{ADDRESS}/full-transactions"
               f"?limit={PAGE_LIMIT}&offset={page * PAGE_LIMIT}"
               f"&resolve_previous_outpoints=light")
        batch = get_json(url)
        if not batch:
            break
        txs.extend(batch)
        print(f"seite {page + 1} (offset): {len(batch)} transaktionen")
        if len(batch) < PAGE_LIMIT:
            break
    return txs


def net_flows(txs):
    """Pro Transaktion der Nettozufluss an unsere Adresse.

    Ausgaenge an uns minus Eingaenge von uns. Dadurch wird Wechselgeld nicht
    als Kauf gezaehlt, falls die Adresse doch einmal etwas sendet.
    """
    inflows = []
    outflows = []
    outflow_kas = 0.0
    unresolved = 0
    dust_tx = 0
    dust_kas = 0.0
    for t in txs:
        bt = t.get("block_time") or 0
        gain = 0.0
        for o in t.get("outputs") or []:
            addr = (o.get("script_public_key_address")
                    or o.get("address") or "")
            if addr == ADDRESS:
                gain += float(o.get("amount", 0)) / SOMPI
        spend = 0.0
        for i in t.get("inputs") or []:
            addr = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if addr is None or amt is None:
                unresolved += 1
                continue
            if addr == ADDRESS:
                spend += float(amt) / SOMPI
        net = gain - spend
        if net > DUST_KAS:
            inflows.append({"ts": bt, "day": day(bt), "kas": net,
                            "tx": t.get("transaction_id", "")})
        elif net < -DUST_KAS:
            outflow_kas += -net
            # Jeder Abfluss einzeln. Ein einziger grosser Vorgang am Anfang
            # ist eine voellig andere Geschichte als viele kleine ueber Jahre.
            outflows.append({"ts": bt, "day": day(bt), "kas": -net,
                             "tx": t.get("transaction_id", "")})
        else:
            # Weder Kauf noch Abfluss. Meist Staubsendungen fremder Leute an
            # eine beruehmte Adresse. Wir zaehlen sie, damit die Summe der
            # Transaktionen aufgeht und niemand fragen kann, wo der Rest ist.
            dust_tx += 1
            dust_kas += net
    print(f"davon {dust_tx} transaktionen unter der staubgrenze "
          f"({dust_kas:,.4f} KAS netto), weder kauf noch abfluss")
    if unresolved:
        print(f"WARN {unresolved} eingaenge ohne aufgeloeste herkunft. "
              f"bei einer reinen sammeladresse ist das unkritisch.",
              file=sys.stderr)
    inflows.sort(key=lambda x: x["ts"])
    outflows.sort(key=lambda x: x["ts"])
    return inflows, outflows, outflow_kas, {"tx": dust_tx, "kas": dust_kas}


# ---------------------------------------------------------------------------
# 2. Preishistorie. VWAP je Tag, KuCoin zuerst, dann MEXC, dann Bybit.
# ---------------------------------------------------------------------------
def _vwap(volume, turnover, fallback):
    try:
        v = float(volume)
        t = float(turnover)
        if v > 0 and t > 0:
            return t / v
    except (TypeError, ValueError):
        pass
    return float(fallback)


def kucoin_days(start_s, end_s):
    """KuCoin liefert [zeit, open, close, high, low, volume, turnover]."""
    out = {}
    cur = start_s
    while cur < end_s:
        chunk_end = min(cur + 1000 * 86400, end_s)
        url = ("https://api.kucoin.com/api/v1/market/candles"
               f"?type=1day&symbol=KAS-USDT&startAt={cur}&endAt={chunk_end}")
        d = get_json(url, timeout=25)
        rows = d.get("data") or []
        for r in rows:
            ts = int(r[0])
            out[day(ts * 1000)] = _vwap(r[5], r[6], r[2])
        print(f"kucoin: {len(rows)} tageskerzen ab {day(cur * 1000)}")
        if not rows:
            break
        cur = chunk_end
    return out


def mexc_days(start_ms, end_ms):
    """MEXC liefert [zeit_ms, open, high, low, close, volume, endzeit, umsatz].

    Bybit sperrt Rechenzentrums-IPs (403 vom GitHub-Runner), MEXC nicht.
    Deshalb steht MEXC vor Bybit in der Kette.
    """
    out = {}
    cur = start_ms
    for _ in range(20):
        if cur >= end_ms:
            break
        url = ("https://api.mexc.com/api/v3/klines"
               f"?symbol=KASUSDT&interval=1d&limit=1000"
               f"&startTime={cur}&endTime={end_ms}")
        rows = get_json(url, timeout=25)
        if not rows:
            break
        newest = 0
        for r in rows:
            ts = int(r[0])
            newest = max(newest, ts)
            out[day(ts)] = _vwap(r[5], r[7], r[4])
        print(f"mexc: {len(rows)} tageskerzen bis {day(newest)}")
        # MEXC liefert weniger Zeilen als angefragt. Eine volle Seite als
        # Abbruchbedingung waere falsch, wir laufen weiter solange sich der
        # neueste Zeitstempel bewegt.
        if newest + 86400_000 <= cur:
            break
        cur = newest + 86400_000
    return out


def bybit_days(start_ms, end_ms):
    """Bybit liefert [zeit_ms, open, high, low, close, volume, turnover]."""
    out = {}
    cur = start_ms
    while cur < end_ms:
        url = ("https://api.bybit.com/v5/market/kline"
               f"?category=spot&symbol=KASUSDT&interval=D"
               f"&start={cur}&end={end_ms}&limit=1000")
        d = get_json(url, timeout=25)
        rows = (d.get("result") or {}).get("list") or []
        if not rows:
            break
        newest = 0
        for r in rows:
            ts = int(r[0])
            newest = max(newest, ts)
            out[day(ts)] = _vwap(r[5], r[6], r[4])
        print(f"bybit: {len(rows)} tageskerzen bis {day(newest)}")
        if newest + 86400_000 <= cur:
            break
        cur = newest + 86400_000
    return out


def price_history(first_ms, last_ms):
    start_s = int(first_ms / 1000) - 3 * 86400
    end_s = int(last_ms / 1000) + 2 * 86400
    prices = {}
    src = {"kucoin": 0, "mexc": 0, "bybit": 0}
    # Alle Tage, die wir im Zeitraum ueberhaupt brauchen koennten.
    wanted = set()
    t = (start_s // 86400) * 86400
    while t <= end_s:
        wanted.add(day(t * 1000))
        t += 86400
    for name, fn in [
        ("kucoin", lambda: kucoin_days(start_s, end_s)),
        ("mexc", lambda: mexc_days(start_s * 1000, end_s * 1000)),
        ("bybit", lambda: bybit_days(start_s * 1000, end_s * 1000)),
    ]:
        # Sind schon alle Tage da, fragen wir die naechste Boerse gar nicht
        # erst. Spart Zeit und vermeidet unnoetige Sperren.
        if not (wanted - set(prices)):
            print(f"alle tage vorhanden, {name} wird nicht mehr gebraucht")
            break
        try:
            got = fn()
        except Exception as e:
            print(f"WARN {name} historie fehlgeschlagen: {e}", file=sys.stderr)
            continue
        for dstr, p in got.items():
            if dstr not in prices and PRICE_MIN < p < PRICE_MAX:
                prices[dstr] = p
                src[name] += 1
    fehlend = sorted(wanted - set(prices))
    if fehlend:
        print(f"hinweis: {len(fehlend)} kalendertage ohne kurs, "
              f"z.b. {', '.join(fehlend[:5])}")
    return prices, src


def price_for(dstr, prices):
    """Exakter Tag, sonst der naechste vorhandene Tag davor, maximal drei."""
    if dstr in prices:
        return prices[dstr], 0
    base = calendar.timegm(time.strptime(dstr, "%Y-%m-%d"))
    for back in range(1, 4):
        alt = time.strftime("%Y-%m-%d", time.gmtime(base - back * 86400))
        if alt in prices:
            return prices[alt], back
    return None, None


# ---------------------------------------------------------------------------
# 3. Aktueller Preis und Kontostand
# ---------------------------------------------------------------------------
def spot_price():
    for name, url, pick in [
        ("kraken", "https://api.kraken.com/0/public/Ticker?pair=KASUSD",
         lambda d: float(list(d["result"].values())[0]["c"][0])),
        ("kucoin", "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=KAS-USDT",
         lambda d: float(d["data"]["price"])),
        ("bybit", "https://api.bybit.com/v5/market/tickers?category=spot&symbol=KASUSDT",
         lambda d: float(d["result"]["list"][0]["lastPrice"])),
        ("mexc", "https://api.mexc.com/api/v3/ticker/price?symbol=KASUSDT",
         lambda d: float(d["price"])),
    ]:
        try:
            p = pick(get_json(url, timeout=12))
            if PRICE_MIN < p < PRICE_MAX:
                print(f"spotpreis {p} von {name}")
                return p
        except Exception as e:
            print(f"WARN spotquelle {name} fehlgeschlagen: {e}", file=sys.stderr)
    return None


def balance():
    try:
        d = get_json(f"{API}/addresses/{ADDRESS}/balance")
        return float(d["balance"]) / SOMPI
    except Exception as e:
        print(f"WARN balance nicht abrufbar: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
def fmt_usd(v):
    a = abs(v)
    if a >= 1_000_000_000:
        return f"${v/1_000_000_000:,.2f}B"
    if a >= 1_000_000:
        return f"${v/1_000_000:,.1f}M"
    if a >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.2f}"


def main():
    print("hole transaktionen ...")
    txs = fetch_transactions()
    print(f"{len(txs)} transaktionen insgesamt")
    if not txs:
        print("ERROR keine transaktionen erhalten", file=sys.stderr)
        sys.exit(1)

    inflows, outflows, outflow_kas, dust = net_flows(txs)
    if not inflows:
        print("ERROR keine zufluesse gefunden", file=sys.stderr)
        sys.exit(1)
    print(f"{len(inflows)} zufluesse, {len(outflows)} abfluesse, "
          f"{outflow_kas:,.0f} KAS jemals abgeflossen")

    if outflows:
        print("\nabfluesse im einzelnen")
        for f in outflows:
            print(f"  {f['day']}  {f['kas']:>16,.0f} KAS  {f['tx']}")
        print("")

    print("hole preishistorie ...")
    prices, src = price_history(inflows[0]["ts"], inflows[-1]["ts"])
    print(f"{len(prices)} tagespreise, davon {src['kucoin']} kucoin, "
          f"{src['mexc']} mexc und {src['bybit']} bybit")

    kas_total = 0.0
    usd_total = 0.0
    kas_priced = 0.0
    missing_kas = 0.0
    missing_days = set()
    stale = 0
    by_month = defaultdict(lambda: {"kas": 0.0, "usd": 0.0})
    largest = {"kas": 0.0, "day": None}

    for f in inflows:
        kas_total += f["kas"]
        if f["kas"] > largest["kas"]:
            largest = {"kas": f["kas"], "day": f["day"]}
        p, back = price_for(f["day"], prices)
        if p is None:
            missing_kas += f["kas"]
            missing_days.add(f["day"])
            continue
        if back:
            stale += 1
        usd = f["kas"] * p
        usd_total += usd
        kas_priced += f["kas"]
        m = f["day"][:7]
        by_month[m]["kas"] += f["kas"]
        by_month[m]["usd"] += usd

    missing_share = missing_kas / kas_total if kas_total else 1.0
    reliable = missing_share <= MAX_MISSING_SHARE and kas_priced > 0
    avg = usd_total / kas_priced if kas_priced else None

    if missing_days:
        print(f"WARN {len(missing_days)} tage ohne preis, betrifft "
              f"{missing_kas:,.0f} KAS ({missing_share*100:.2f} prozent)",
              file=sys.stderr)
    if stale:
        print(f"hinweis: {stale} zufluesse mit dem preis eines vortages bewertet")

    bal = balance()
    spot = spot_price()
    value_now = bal * spot if (bal and spot) else None
    # Gewinn und Verlust nur, wenn der Einstand ueberhaupt belastbar ist.
    # Ein Vergleich gegen einen halben Einstand waere schlimmer als gar keiner.
    pnl = (value_now - usd_total) if (value_now is not None and reliable
                                      and usd_total > 0) else None

    out = {
        "generated_at": int(time.time()),
        "address": ADDRESS,
        "method": ("volume weighted daily average price, "
                   "kucoin with mexc and bybit gap fill"),
        "reliable": reliable,
        "deposits": len(inflows),
        "kas_received": round(kas_total, 2),
        "kas_priced": round(kas_priced, 2),
        "usd_invested": round(usd_total, 2),
        "avg_cost_usd": round(avg, 6) if avg else None,
        "outflow_kas": round(outflow_kas, 2),
        "outflow_count": len(outflows),
        "transactions_total": len(txs),
        "dust_transactions": dust["tx"],
        "dust_kas": round(dust["kas"], 4),
        "first_outflow": outflows[0]["day"] if outflows else None,
        "last_outflow": outflows[-1]["day"] if outflows else None,
        "outflows": [{"day": f["day"], "kas": round(f["kas"], 2),
                      "tx": f["tx"]} for f in outflows],
        "balance_kas": round(bal, 2) if bal else None,
        "first_deposit": inflows[0]["day"],
        "last_deposit": inflows[-1]["day"],
        "largest_deposit_kas": round(largest["kas"], 2),
        "largest_deposit_day": largest["day"],
        "price_now": spot,
        "value_now_usd": round(value_now, 2) if value_now else None,
        "unrealized_usd": round(pnl, 2) if pnl is not None else None,
        "unrealized_pct": round(pnl / usd_total * 100, 2) if pnl is not None else None,
        "missing_price_days": sorted(missing_days),
        "missing_share": round(missing_share, 5),
        "price_source_days": src,
        "by_month": [
            {"month": m,
             "kas": round(v["kas"], 2),
             "usd": round(v["usd"], 2),
             "avg": round(v["usd"] / v["kas"], 6) if v["kas"] else None}
            for m, v in sorted(by_month.items())
        ],
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, indent=2)

    print("\n" + "=" * 64)
    print("ENTITY X COST BASIS")
    print("=" * 64)
    print(f"zufluesse           {len(inflows)}")
    print(f"erster kauf         {inflows[0]['day']}")
    print(f"letzter kauf        {inflows[-1]['day']}")
    print(f"KAS gekauft         {kas_total:,.0f}")
    print(f"KAS jemals raus     {outflow_kas:,.0f} in {len(outflows)} vorgaengen")
    if outflows:
        print(f"erster abfluss      {outflows[0]['day']}")
        print(f"letzter abfluss     {outflows[-1]['day']}")
    print(f"groesster kauf      {largest['kas']:,.0f} KAS am {largest['day']}")
    if reliable:
        print(f"investiert          {fmt_usd(usd_total)}")
        print(f"EINSTANDSPREIS      ${avg:.6f}")
    else:
        print("investiert          unbekannt, zu viele preisluecken")
        print("EINSTANDSPREIS      unbekannt, zu viele preisluecken")
    if spot:
        print(f"kurs jetzt          ${spot:.6f}")
    if value_now is not None:
        print(f"wert jetzt          {fmt_usd(value_now)}")
    if pnl is not None:
        print(f"unrealisiert        {fmt_usd(pnl)}  ({pnl/usd_total*100:+.1f} prozent)")
    print(f"belastbar           {'ja' if reliable else 'NEIN, zahl nicht benutzen'}")
    print("=" * 64)
    print(f"\ngeschrieben nach {OUT_FILE}")


if __name__ == "__main__":
    main()
