#!/usr/bin/env python3
# Kaspa Pulse - Entity X Tracker Audit v1.0
# Ablageort im Repo: scripts/entity_x_tracker_audit.py
#
# Anlass: zwei Whale-Tracker nennen fuer dieselbe Adresse am selben
# Wochenende verschiedene Bestaende.
#   @anbrandenburger, 18.09.2026: "~5,5 % of the supply"
#   @Joe Wong, 19.09.2026:        "1.52 billion $KAS ... 5.3%~ of total supply"
# Differenz in KAS, je nach Nenner, rund 59 Millionen.
#
# Leithypothese: die beiden meinen nicht dasselbe. Brutto ist nicht netto.
# Dieses Skript rechnet beide Lesarten aus, auf den Coin genau, und haengt
# an jede Zahl den Nenner und die Abrufzeit.
#
# Was hier NICHT passiert: keine Aussage ueber Absicht. Wir sehen einen
# Transfer, keinen Verkauf. Kein "sold", kein "dumped", kein Dollarbetrag
# als realisierter Gewinn, keine Behauptung ueber das, was nicht passiert
# ist. Die Kette zeigt den Weg, nie den Eigentuemer und nie das Motiv.
#
# Abschnitte, nummeriert wie der Pruefauftrag:
#   1 Brutto und Netto, plus Gegenprobe gegen unabhaengige Quellen
#   2 Abfluesse seit dem Stichtag, Ziele, ein Hop weiter
#   3 Abgleich der beiden Trackerzahlen gegen beide Lesarten
#   4 Cluster: eine Adresse oder mehrere, nach welcher Regel
#   5 Nenner: Maximalmenge und tatsaechlich Gemintes
#   6 Zuflussledger: Anteil aus benannten Boersen-Wallets
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
OUT_FILE = "data/entity-x-tracker-audit.json"

API = "https://api.kaspa.org"
SOMPI = 100_000_000
UA = {"User-Agent": "kaspapulse-tracker-audit/1.0"}

PAGE_LIMIT = 500
MAX_PAGES = 200
DUST_KAS = 1.0
BUSY_TX = 5000
HOP_PAGES = 2

# Stichtag des letzten manuell gegengeprueften Laufs. Alles danach ist neu.
CUTOFF_DAY = "2026-08-03"

# Die beiden Trackerzahlen, gegen die wir pruefen.
MAX_SUPPLY = 28_704_026_601          # Maximalmenge, Doktrin-Nenner (a)
TRACKER_BRANDENBURGER_PCT = 5.5      # "~5,5 % of the supply", 18.09.2026
TRACKER_JOEWONG_KAS = 1_520_000_000  # "1.52 billion $KAS", 19.09.2026
TRACKER_JOEWONG_PCT = 5.3            # "5.3%~ of total supply"
TRACKER_JOEWONG_USD = 54_480_000     # "USD$54.48 million"

# Stand 03.08.2026 zum Vergleich, aus dem gegengeprueften Lauf.
REF_0803 = {
    "day": "2026-08-03",
    "gross_kas": 1_542_913_144,
    "outflow_kas": 39_038_233,
    "dust_kas": 125.12,
    "net_kas": 1_503_875_036,
}

# Beschriftete Hotwallets, identisch zu entity_x_inflows.py und
# entity_x_outflows.py. Nur eintragen, was kaspa.stream oder die Boerse
# selbst ausweist.
KNOWN_SOURCE = "kaspa.stream address labels, geprueft am 2026-08-03"
KNOWN = {
    "kaspa:qrelgny7sr3vahq69yykxx36m65gvmhryxrlwngfzgu8xkdslum2yxjp3ap8m": "gate.io",
    "kaspa:qrvum29vk365g0zcd5gx3c7h829etfq2ytdmscjzw4zw04fjfnprcg9c3tges": "bybit",
    "kaspa:qqywx2wszmnrsu0mzgav85rdwvzangfpdj9j3ady9jpr7hu4u8c2wl9wqgd6j": "bitget",
    "kaspa:qzxs23g7txh3wq9d0t2z0hluhsflvzpf6d0yfum830ppumgtxa5d7zqca8r67": "bitvavo",
}

PROFILE_TOP = 60
HOP_TOP = 25


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


def get_text(url, timeout=25, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(2 * (i + 1))
    raise last


def day(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def stamp(ms):
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ms / 1000))


def out_addr(o):
    return o.get("script_public_key_address") or o.get("address") or ""


# ---------------------------------------------------------------------------
# Transaktionen. Bewusst identisch zu den drei bestehenden Skripten, damit
# alle vier dieselbe Menge sehen und niemand Zahlen vergleicht, die auf
# verschiedenen Paginierungen beruhen.
# ---------------------------------------------------------------------------
def fetch_transactions(address, max_pages=MAX_PAGES, quiet=False):
    txs = []
    seen = set()
    before = 0
    for page in range(max_pages):
        url = (f"{API}/addresses/{address}/full-transactions-page"
               f"?limit={PAGE_LIMIT}&resolve_previous_outpoints=light")
        if before:
            url += f"&before={before}"
        try:
            batch = get_json(url)
        except Exception as e:
            if page == 0:
                print(f"WARN seitenroute nicht verfuegbar ({e})", file=sys.stderr)
                return []
            raise
        if not batch:
            break
        fresh = 0
        oldest = None
        for t in batch:
            tid = t.get("transaction_id") or str(t.get("block_time"))
            bt = t.get("block_time") or 0
            if oldest is None or bt < oldest:
                oldest = bt
            if tid in seen:
                continue
            seen.add(tid)
            txs.append(t)
            fresh += 1
        if not quiet:
            print(f"  seite {page + 1}: {len(batch)} transaktionen, {fresh} neu")
        if len(batch) < PAGE_LIMIT or fresh == 0 or not oldest:
            break
        before = oldest
    return txs


def net_flows(txs, address):
    """Pro Transaktion der Nettozufluss an die Adresse.

    Ausgaenge an uns minus Eingaenge von uns. Wechselgeld zaehlt damit nicht
    als Kauf. Das ist exakt die Logik aus entity_x_costbasis.py.
    """
    inflows, outflows = [], []
    dust_tx, dust_kas, unresolved = 0, 0.0, 0
    for t in txs:
        bt = t.get("block_time") or 0
        gain = 0.0
        for o in t.get("outputs") or []:
            if out_addr(o) == address:
                gain += float(o.get("amount", 0)) / SOMPI
        spend = 0.0
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None:
                unresolved += 1
                continue
            if a == address:
                spend += float(amt) / SOMPI
        net = gain - spend
        rec = {"ts": bt, "day": day(bt), "utc": stamp(bt),
               "tx": t.get("transaction_id", ""), "kas": abs(net)}
        if net > DUST_KAS:
            rec["raw"] = t
            inflows.append(rec)
        elif net < -DUST_KAS:
            rec["raw"] = t
            outflows.append(rec)
        else:
            dust_tx += 1
            dust_kas += net
    inflows.sort(key=lambda x: x["ts"])
    outflows.sort(key=lambda x: x["ts"])
    return inflows, outflows, {"tx": dust_tx, "kas": dust_kas,
                               "unresolved_inputs": unresolved}


# ---------------------------------------------------------------------------
# Adressprofile und ein Hop. Cache, damit dieselbe Hotwallet nicht 160 mal
# abgefragt wird.
# ---------------------------------------------------------------------------
_profile_cache = {}


def profile(address):
    if address in _profile_cache:
        return _profile_cache[address]
    p = {"balance_kas": None, "tx_count": None}
    try:
        d = get_json(f"{API}/addresses/{address}/balance", timeout=20)
        p["balance_kas"] = float(d["balance"]) / SOMPI
    except Exception as e:
        p["balance_error"] = str(e)[:120]
    try:
        d = get_json(f"{API}/addresses/{address}/transactions-count", timeout=20)
        p["tx_count"] = int(d.get("total", 0))
    except Exception as e:
        p["txcount_error"] = str(e)[:120]
    _profile_cache[address] = p
    return p


def classify(address, prof, hop=None):
    """Urteil ueber eine Adresse. Streng: 'boerse' nur mit Label."""
    if address in KNOWN:
        return ("boerse", KNOWN[address],
                f"adresse ist auf kaspa.stream als {KNOWN[address]} beschriftet")
    if hop and hop.get("frm"):
        h = hop["frm"]["address"]
        if h in KNOWN:
            return ("boerse ueber zwischenadresse", KNOWN[h],
                    f"zwischenadresse wurde am {hop['day']} von der auf "
                    f"kaspa.stream als {KNOWN[h]} beschrifteten adresse befuellt")
        hp = hop.get("frm_profile") or {}
        if (hp.get("tx_count") or 0) >= BUSY_TX:
            return ("boerse ueber zwischenadresse wahrscheinlich", None,
                    f"zwischenadresse wurde am {hop['day']} von einer adresse "
                    f"mit {hp['tx_count']:,} transaktionen befuellt")
    n = prof.get("tx_count") or 0
    if n >= BUSY_TX:
        return ("boerse wahrscheinlich", None,
                f"adresse hat {n:,} transaktionen, das ist kein privates wallet")
    if n and n < 50:
        return ("frisches wallet", None,
                f"adresse hat nur {n} transaktionen und kein label")
    return ("unklar", None, f"adresse hat {n:,} transaktionen und kein label")


def prev_hop(address):
    """Woher kam das Geld, das diese Adresse zuletzt bekommen hat."""
    txs = fetch_transactions(address, max_pages=HOP_PAGES, quiet=True)
    best = None
    for t in txs:
        got = 0.0
        for o in t.get("outputs") or []:
            if out_addr(o) == address:
                got += float(o.get("amount", 0)) / SOMPI
        if got <= DUST_KAS:
            continue
        biggest = None
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None or a == address:
                continue
            kas = float(amt) / SOMPI
            if biggest is None or kas > biggest["kas"]:
                biggest = {"address": a, "kas": kas}
        if not biggest:
            continue
        bt = t.get("block_time") or 0
        if best is None or bt > best["ts"]:
            best = {"ts": bt, "day": day(bt), "tx": t.get("transaction_id", ""),
                    "frm": biggest}
    if best:
        best["frm_profile"] = profile(best["frm"]["address"])
    return best


def next_hop(address):
    """Wohin hat diese Adresse weitergeschickt, nachdem sie bekam."""
    txs = fetch_transactions(address, max_pages=HOP_PAGES, quiet=True)
    best = None
    for t in txs:
        spent = 0.0
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a == address and amt is not None:
                spent += float(amt) / SOMPI
        if spent <= DUST_KAS:
            continue
        biggest = None
        for o in t.get("outputs") or []:
            a = out_addr(o)
            if not a or a == address:
                continue
            kas = float(o.get("amount", 0)) / SOMPI
            if biggest is None or kas > biggest["kas"]:
                biggest = {"address": a, "kas": kas}
        if not biggest:
            continue
        bt = t.get("block_time") or 0
        if best is None or bt > best["ts"]:
            best = {"ts": bt, "day": day(bt), "tx": t.get("transaction_id", ""),
                    "to": biggest}
    if best:
        best["to_profile"] = profile(best["to"]["address"])
        best["to_label"] = KNOWN.get(best["to"]["address"])
    return best


# ---------------------------------------------------------------------------
# 1. Gegenprobe. Der Ledger rechnet Brutto minus Abfluss plus Staub. Die
#    Knoten-API nennt den Kontostand direkt. Beide muessen sich treffen.
# ---------------------------------------------------------------------------
def crosscheck_balances():
    out = {}
    try:
        d = get_json(f"{API}/addresses/{ADDRESS}/balance", timeout=20)
        out["api.kaspa.org"] = {"kas": float(d["balance"]) / SOMPI,
                                "raw_sompi": int(d["balance"]),
                                "fetched_at": stamp(time.time() * 1000)}
    except Exception as e:
        out["api.kaspa.org"] = {"error": str(e)[:200]}

    # kaspa.stream hat keine dokumentierte oeffentliche JSON-Route. Wir
    # probieren die naheliegenden Kandidaten und protokollieren ehrlich,
    # was geantwortet hat. Kein Treffer ist auch ein Ergebnis.
    for name, url in [
        ("kaspa.stream/api", f"https://kaspa.stream/api/address/{ADDRESS}"),
        ("kaspa.stream/addresses", f"https://kaspa.stream/api/addresses/{ADDRESS}/balance"),
        ("kaspa.stream/html", f"https://kaspa.stream/address/{ADDRESS}"),
    ]:
        try:
            body = get_text(url, timeout=20, tries=1)
            hit = None
            try:
                j = json.loads(body)
                for k in ("balance", "amount", "value"):
                    if k in j:
                        hit = float(j[k])
                        break
                out[name] = {"ok": True, "json_keys": list(j)[:12],
                             "balance_field": hit}
                continue
            except ValueError:
                pass
            m = re.search(r'"balance"\s*:\s*"?(\d+)"?', body)
            out[name] = {"ok": True, "bytes": len(body),
                         "balance_regex": int(m.group(1)) if m else None}
        except Exception as e:
            out[name] = {"error": str(e)[:160]}
    return out


def spot_price():
    for name, url, pick in [
        ("kraken", "https://api.kraken.com/0/public/Ticker?pair=KASUSD",
         lambda d: float(list(d["result"].values())[0]["c"][0])),
        ("kucoin", "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=KAS-USDT",
         lambda d: float(d["data"]["price"])),
        ("mexc", "https://api.mexc.com/api/v3/ticker/price?symbol=KASUSDT",
         lambda d: float(d["price"])),
    ]:
        try:
            p = pick(get_json(url, timeout=12))
            if 0.0001 < p < 100:
                return {"price": p, "source": name,
                        "fetched_at": stamp(time.time() * 1000)}
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    print("=" * 72)
    print("ENTITY X TRACKER AUDIT")
    print(f"lauf gestartet {stamp(t_start * 1000)}")
    print("=" * 72)

    print("\n[0] transaktionen der entity-x-adresse")
    txs = fetch_transactions(ADDRESS)
    if not txs:
        print("ERROR keine transaktionen erhalten", file=sys.stderr)
        sys.exit(1)
    fetched_at = time.time()
    print(f"  {len(txs)} transaktionen, abgerufen {stamp(fetched_at * 1000)}")

    inflows, outflows, dust = net_flows(txs, ADDRESS)
    gross = sum(f["kas"] for f in inflows)
    outflow_total = sum(f["kas"] for f in outflows)
    ledger_net = gross - outflow_total + dust["kas"]

    # -------------------------------------------------------------- 1
    print("\n[1] brutto, netto, gegenprobe")
    print(f"  bruttoakkumulation  {gross:,.8f} KAS aus {len(inflows)} zufluessen")
    print(f"  abfluesse           {outflow_total:,.8f} KAS in {len(outflows)} vorgaengen")
    print(f"  staub netto         {dust['kas']:,.8f} KAS aus {dust['tx']} transaktionen")
    print(f"  ledger netto        {ledger_net:,.8f} KAS")

    cross = crosscheck_balances()
    api_bal = (cross.get("api.kaspa.org") or {}).get("kas")
    delta = (ledger_net - api_bal) if api_bal is not None else None
    if api_bal is not None:
        print(f"  knoten-kontostand   {api_bal:,.8f} KAS")
        print(f"  abweichung          {delta:,.8f} KAS")
    for k, v in cross.items():
        print(f"    quelle {k}: {json.dumps(v)[:220]}")

    print("\n  vergleich zum gegengeprueften stand 03.08.2026")
    print(f"    brutto   {REF_0803['gross_kas']:,} -> {gross:,.2f} "
          f"({gross - REF_0803['gross_kas']:+,.2f})")
    print(f"    abfluss  {REF_0803['outflow_kas']:,} -> {outflow_total:,.2f} "
          f"({outflow_total - REF_0803['outflow_kas']:+,.2f})")
    print(f"    netto    {REF_0803['net_kas']:,} -> {ledger_net:,.2f} "
          f"({ledger_net - REF_0803['net_kas']:+,.2f})")
    print(f"    spanne brutto minus netto: {gross - ledger_net:,.2f} KAS "
          f"(am 03.08. waren es {REF_0803['gross_kas'] - REF_0803['net_kas']:,})")

    # -------------------------------------------------------------- 2
    print(f"\n[2] abfluesse seit {CUTOFF_DAY}")
    recent = [f for f in outflows if f["day"] >= CUTOFF_DAY]
    print(f"  {len(recent)} vorgaenge, {sum(f['kas'] for f in recent):,.8f} KAS")
    recent_detail = []
    for f in recent:
        t = f["raw"]
        recips = defaultdict(float)
        for o in t.get("outputs") or []:
            a = out_addr(o)
            if a and a != ADDRESS:
                recips[a] += float(o.get("amount", 0)) / SOMPI
        entry = {"day": f["day"], "utc": f["utc"], "tx": f["tx"],
                 "kas": round(f["kas"], 8), "recipients": []}
        for a, kas in sorted(recips.items(), key=lambda x: -x[1]):
            prof = profile(a)
            hop = next_hop(a) if kas > DUST_KAS else None
            verdict, exch, reason = classify(a, prof, None)
            # Fuer Ziele zaehlt der WEITERE hop, nicht der vorherige.
            if exch is None and hop:
                if hop.get("to_label"):
                    verdict = "boerse ueber zwischenadresse"
                    exch = hop["to_label"]
                    reason = (f"empfaenger leitete am {hop['day']} weiter an die "
                              f"auf kaspa.stream als {hop['to_label']} "
                              f"beschriftete adresse")
                elif ((hop.get("to_profile") or {}).get("tx_count") or 0) >= BUSY_TX:
                    verdict = "boerse ueber zwischenadresse wahrscheinlich"
                    reason = (f"empfaenger leitete am {hop['day']} weiter an eine "
                              f"adresse mit {hop['to_profile']['tx_count']:,} "
                              f"transaktionen")
            entry["recipients"].append({
                "address": a, "kas": round(kas, 8), "profile": prof,
                "verdict": verdict, "exchange": exch, "reason": reason,
                "next_hop": hop,
            })
        recent_detail.append(entry)
        print(f"  {f['utc']}  {f['kas']:>16,.2f} KAS  {f['tx']}")
        for r in entry["recipients"]:
            print(f"      -> {r['kas']:>16,.2f} KAS  {r['address'][:28]}...  "
                  f"[{r['verdict']}{'/' + r['exchange'] if r['exchange'] else ''}]  "
                  f"{r['reason']}")

    # -------------------------------------------------------------- 4
    print("\n[4] cluster")
    # Regel A, common input ownership: wer in derselben transaktion
    # gemeinsam mit uns als input signiert, kontrolliert denselben
    # schluessel. Das ist die enge, belastbare regel.
    coinput = defaultdict(lambda: {"txs": 0, "kas": 0.0, "first": None, "last": None})
    for t in txs:
        ins = []
        mine = False
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None:
                continue
            if a == ADDRESS:
                mine = True
            else:
                ins.append((a, float(amt) / SOMPI))
        if not mine:
            continue
        bt = t.get("block_time") or 0
        for a, kas in ins:
            c = coinput[a]
            c["txs"] += 1
            c["kas"] += kas
            if c["first"] is None or bt < c["first"]:
                c["first"] = bt
            if c["last"] is None or bt > c["last"]:
                c["last"] = bt
    print(f"  regel A, gemeinsamer input: {len(coinput)} weitere adressen")

    # Regel B, rundlauf: adressen, die von uns bekommen UND an uns gesendet
    # haben. Schwaecheres signal, aber bei dieser adresse relevant.
    sent_to, got_from = set(), set()
    for f in outflows:
        for o in f["raw"].get("outputs") or []:
            a = out_addr(o)
            if a and a != ADDRESS:
                sent_to.add(a)
    for f in inflows:
        for i in f["raw"].get("inputs") or []:
            a = i.get("previous_outpoint_address")
            if a and a != ADDRESS:
                got_from.add(a)
    roundtrip = sorted(sent_to & got_from)
    print(f"  regel B, rundlauf: {len(roundtrip)} adressen bekamen von uns "
          f"und sendeten an uns")

    cluster_detail = []
    for a in sorted(set(list(coinput) + roundtrip)):
        p = profile(a)
        cluster_detail.append({
            "address": a,
            "rule": ("gemeinsamer input" if a in coinput else "") +
                    ("+rundlauf" if a in roundtrip and a in coinput else
                     ("rundlauf" if a in roundtrip else "")),
            "coinput_txs": coinput[a]["txs"] if a in coinput else 0,
            "coinput_kas": round(coinput[a]["kas"], 8) if a in coinput else 0,
            "balance_kas": p.get("balance_kas"),
            "tx_count": p.get("tx_count"),
        })
        print(f"    {a[:30]}...  regel={cluster_detail[-1]['rule']:<24} "
              f"bestand={p.get('balance_kas')}  tx={p.get('tx_count')}")
    cluster_extra_balance = sum((c["balance_kas"] or 0) for c in cluster_detail)
    print(f"  zusaetzlicher bestand in diesen adressen: "
          f"{cluster_extra_balance:,.8f} KAS")

    # -------------------------------------------------------------- 6
    print("\n[6] zuflussledger, anteil aus benannten boersen-wallets")
    senders = defaultdict(lambda: {"kas": 0.0, "transfers": 0,
                                   "first": None, "last": None})
    for f in inflows:
        t = f["raw"]
        gross_in = defaultdict(float)
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None or a == ADDRESS:
                continue
            gross_in[a] += float(amt) / SOMPI
        tot = sum(gross_in.values())
        if tot <= 0:
            continue
        # Pro rata auf den NETTO-zufluss. Sonst zaehlt das wechselgeld der
        # hotwallet mit und eine boerse landet bei 155 prozent.
        for a, kas in gross_in.items():
            s = senders[a]
            s["kas"] += f["kas"] * (kas / tot)
            s["transfers"] += 1
            if s["first"] is None or f["ts"] < s["first"]:
                s["first"] = f["ts"]
            if s["last"] is None or f["ts"] > s["last"]:
                s["last"] = f["ts"]
    ranked = sorted(senders.items(), key=lambda x: -x[1]["kas"])
    print(f"  {len(inflows)} einzahlungen von {len(ranked)} sendern")

    sender_detail = []
    named_kas = 0.0
    by_exchange = defaultdict(lambda: {"kas": 0.0, "senders": 0})
    verdict_counts = defaultdict(int)
    kas_by_verdict = defaultdict(float)
    for rank, (a, s) in enumerate(ranked):
        if rank < PROFILE_TOP:
            p = profile(a)
            hop = prev_hop(a) if rank < HOP_TOP else None
            verdict, exch, reason = classify(a, p, hop)
        else:
            p, hop = {}, None
            verdict, exch, reason = ("nicht einzeln profiliert", None,
                                     "unterhalb der profilierungsgrenze")
        verdict_counts[verdict] += 1
        kas_by_verdict[verdict] += s["kas"]
        if exch:
            named_kas += s["kas"]
            by_exchange[exch]["kas"] += s["kas"]
            by_exchange[exch]["senders"] += 1
        sender_detail.append({
            "address": a, "kas": round(s["kas"], 8),
            "transfers": s["transfers"],
            "first_day": day(s["first"]), "last_day": day(s["last"]),
            "profile": p, "verdict": verdict, "exchange": exch,
            "reason": reason, "prev_hop": hop,
        })
    named_share = named_kas / gross if gross else None
    print(f"  aus benannten boersen-wallets, direkt oder ein hop: "
          f"{named_kas:,.2f} KAS = {named_share * 100:.2f} prozent")
    for e, v in sorted(by_exchange.items(), key=lambda x: -x[1]["kas"]):
        print(f"    {e:<10} {v['kas']:>16,.2f} KAS aus {v['senders']} wallets")
    for v, n in sorted(verdict_counts.items(), key=lambda x: -kas_by_verdict[x[0]]):
        print(f"    urteil {v:<46} {n:>4} sender  "
              f"{kas_by_verdict[v]:>16,.2f} KAS")

    # -------------------------------------------------------------- 5
    print("\n[5] nenner")
    supply = {}
    try:
        cs = get_json(f"{API}/info/coinsupply", timeout=20)
        supply["raw"] = cs
        circ = float(cs.get("circulatingSupply") or 0) / SOMPI
        mx = float(cs.get("maxSupply") or 0) / SOMPI
        supply["circulating_kas"] = circ
        supply["max_supply_kas"] = mx
        supply["fetched_at"] = stamp(time.time() * 1000)
        print(f"  geminted laut knoten   {circ:,.8f} KAS")
        print(f"  maximalmenge laut knoten {mx:,.8f} KAS")
        if mx:
            print(f"  geminted anteil        {circ / mx * 100:.4f} prozent")
    except Exception as e:
        supply["error"] = str(e)[:200]
        print(f"  WARN coinsupply nicht abrufbar: {e}")

    circ = supply.get("circulating_kas") or 0

    def shares(kas):
        d = {"of_max_supply_pct": kas / MAX_SUPPLY * 100}
        if circ:
            d["of_minted_pct"] = kas / circ * 100
        return d

    print(f"\n  brutto {gross:,.2f} KAS")
    print(f"    von maximalmenge {MAX_SUPPLY:,}: "
          f"{gross / MAX_SUPPLY * 100:.4f} prozent")
    if circ:
        print(f"    von geminted {circ:,.0f}: {gross / circ * 100:.4f} prozent")
    print(f"  netto  {ledger_net:,.2f} KAS")
    print(f"    von maximalmenge {MAX_SUPPLY:,}: "
          f"{ledger_net / MAX_SUPPLY * 100:.4f} prozent")
    if circ:
        print(f"    von geminted {circ:,.0f}: {ledger_net / circ * 100:.4f} prozent")

    # -------------------------------------------------------------- 3
    print("\n[3] abgleich der beiden trackerzahlen")
    price = spot_price()
    readings = {
        "brutto": gross,
        "netto": ledger_net,
        "netto_plus_cluster": ledger_net + cluster_extra_balance,
    }
    tracker_rows = []
    # Brandenburger nennt nur einen prozentsatz. Der implizierte bestand
    # haengt am nenner, den er nicht nennt. Beide moeglichkeiten rechnen.
    for nenner_name, nenner in [("maximalmenge", MAX_SUPPLY),
                                ("geminted", circ or None)]:
        if not nenner:
            continue
        implied = TRACKER_BRANDENBURGER_PCT / 100 * nenner
        row = {"tracker": "brandenburger 18.09.",
               "claim": f"~{TRACKER_BRANDENBURGER_PCT} % of the supply",
               "assumed_denominator": nenner_name,
               "implied_kas": implied, "fits": {}}
        for rname, rkas in readings.items():
            row["fits"][rname] = {"delta_kas": rkas - implied,
                                  "pct_of_reading": (rkas - implied) / rkas * 100}
        tracker_rows.append(row)
        print(f"  brandenburger, nenner {nenner_name}: "
              f"impliziert {implied:,.0f} KAS")
        for rname, rkas in readings.items():
            print(f"      gegen {rname:<20} {rkas:,.0f} -> "
                  f"{rkas - implied:+,.0f} KAS")

    print(f"  joe wong nennt {TRACKER_JOEWONG_KAS:,} KAS")
    jw = {"tracker": "joe wong 19.09.", "claim": "1.52 billion $KAS",
          "stated_kas": TRACKER_JOEWONG_KAS, "fits": {}}
    for rname, rkas in readings.items():
        jw["fits"][rname] = {"delta_kas": rkas - TRACKER_JOEWONG_KAS,
                             "pct_of_reading": (rkas - TRACKER_JOEWONG_KAS) / rkas * 100}
        print(f"      gegen {rname:<20} {rkas:,.0f} -> "
              f"{rkas - TRACKER_JOEWONG_KAS:+,.0f} KAS")
    jw["stated_pct"] = TRACKER_JOEWONG_PCT
    jw["implied_price_usd"] = TRACKER_JOEWONG_USD / TRACKER_JOEWONG_KAS
    tracker_rows.append(jw)
    print(f"  joe wong impliziter kurs "
          f"${TRACKER_JOEWONG_USD / TRACKER_JOEWONG_KAS:.6f}")
    if price:
        print(f"  kurs jetzt ${price['price']:.6f} von {price['source']} "
              f"({price['fetched_at']})")

    # Welcher prozentsatz kommt heraus, wenn man jede lesart durch jeden
    # nenner teilt. Das ist die eigentliche antwort auf frage 3.
    print("\n  kreuztabelle prozentsatz")
    print(f"    {'lesart':<22} {'/ maximalmenge':>16} {'/ geminted':>16}")
    for rname, rkas in readings.items():
        a = rkas / MAX_SUPPLY * 100
        b = (rkas / circ * 100) if circ else float("nan")
        print(f"    {rname:<22} {a:>15.4f}% {b:>15.4f}%")

    # -------------------------------------------------------------- schreiben
    out = {
        "generated_at": int(time.time()),
        "generated_at_utc": stamp(time.time() * 1000),
        "chain_fetched_at_utc": stamp(fetched_at * 1000),
        "address": ADDRESS,
        "question": ("zwei whale-tracker nennen fuer dieselbe adresse "
                     "verschiedene bestaende. welche lesart entspricht "
                     "welcher zahl."),
        "method": {
            "netto": ("pro transaktion ausgaenge an die adresse minus "
                      "eingaenge von der adresse. wechselgeld zaehlt nicht "
                      "als zufluss."),
            "brutto": "summe aller transaktionen mit positivem netto",
            "abfluss": "summe aller transaktionen mit negativem netto",
            "staub": f"betrag unter {DUST_KAS} KAS, weder kauf noch abfluss",
            "cluster_regel_a": "gemeinsamer input in derselben transaktion",
            "cluster_regel_b": "adresse bekam von uns und sendete an uns",
            "boerse": ("nur mit label von kaspa.stream. direkt oder genau "
                       "ein hop. wahrscheinlichkeitsurteile zaehlen nicht mit."),
            "caveat": ("die kette zeigt den transfer, nie den eigentuemer "
                       "und nie das motiv. eine einzahlung auf eine "
                       "boersenadresse ist kein verkauf."),
        },
        "known_label_source": KNOWN_SOURCE,
        "transactions_total": len(txs),
        "gross_accumulation_kas": round(gross, 8),
        "inflow_count": len(inflows),
        "outflow_total_kas": round(outflow_total, 8),
        "outflow_count": len(outflows),
        "dust": {"transactions": dust["tx"], "kas": round(dust["kas"], 8),
                 "unresolved_inputs": dust["unresolved_inputs"]},
        "ledger_net_kas": round(ledger_net, 8),
        "crosscheck": cross,
        "crosscheck_delta_kas": round(delta, 8) if delta is not None else None,
        "reference_2026_08_03": REF_0803,
        "cutoff_day": CUTOFF_DAY,
        "outflows_since_cutoff": recent_detail,
        "outflows_since_cutoff_count": len(recent),
        "outflows_since_cutoff_kas": round(sum(f["kas"] for f in recent), 8),
        "outflows_all": [{"day": f["day"], "utc": f["utc"],
                          "kas": round(f["kas"], 8), "tx": f["tx"]}
                         for f in outflows],
        "cluster": {
            "rule_a_coinput_addresses": len(coinput),
            "rule_b_roundtrip_addresses": len(roundtrip),
            "members": cluster_detail,
            "extra_balance_kas": round(cluster_extra_balance, 8),
        },
        "inflow_ledger": {
            "deposits": len(inflows),
            "distinct_senders": len(ranked),
            "named_exchange_kas": round(named_kas, 8),
            "named_exchange_share": round(named_share, 6) if named_share else None,
            "by_exchange": {k: {"kas": round(v["kas"], 8),
                                "senders": v["senders"]}
                            for k, v in by_exchange.items()},
            "verdict_counts": dict(verdict_counts),
            "kas_by_verdict": {k: round(v, 8) for k, v in kas_by_verdict.items()},
            "senders": sender_detail,
        },
        "supply": supply,
        "denominators": {
            "max_supply_kas": MAX_SUPPLY,
            "minted_kas": circ or None,
        },
        "readings": {k: round(v, 8) for k, v in readings.items()},
        "shares": {k: shares(v) for k, v in readings.items()},
        "trackers": tracker_rows,
        "price_now": price,
        "runtime_seconds": round(time.time() - t_start, 1),
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\ngeschrieben nach {OUT_FILE} "
          f"({out['runtime_seconds']} sekunden laufzeit)")


if __name__ == "__main__":
    main()
