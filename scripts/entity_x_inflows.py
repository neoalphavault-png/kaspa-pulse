#!/usr/bin/env python3
# Kaspa Pulse - Entity X Inflow Tracing v1.1
# Ablageort im Repo: scripts/entity_x_inflows.py
#
# Frage, die das Skript beantwortet:
#   "Woher kommen die Coins, die Entity X bekommt?"
#
# Anlass: die These aus der OG-Gruppe (06.08.2026), die Zufluesse seien
# Konsolidierungen frueher Miner ueber viele kleine Zwischenwallets, keine
# Kaeufe. Das Gegenmuster waere: Zufluesse kommen direkt von beschrifteten
# Boersen-Hotwallets, das saehe nach Abhebungen aus.
#
# v1.1: Zurechnungsfehler aus Lauf #2 behoben. Absender bekommen jetzt ihren
# Anteil am Netto-Zufluss zugerechnet, nicht ihren Brutto-Input. Vorher
# zaehlte das Wechselgeld der Hotwallets mit und gate.io stand bei 155.7%.
#
# Was das Skript NICHT tut: es behauptet nicht, wer Entity X ist, und es
# nennt keine Motive. Wir melden die Bewegung, nie das Motiv.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import sys
import time
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
OUT_FILE = "data/entity-x-inflows.json"

API = "https://api.kaspa.org"
SOMPI = 100_000_000
UA = {"User-Agent": "kaspapulse-inflows/1.1"}

PAGE_LIMIT = 500
MAX_PAGES = 200
DUST_KAS = 1.0
BUSY_TX = 5000
HOP_PAGES = 2

# Wie viele der groessten Absender wir einzeln profilieren und einen Hop
# zurueckverfolgen. Alles darunter wird aggregiert gezaehlt.
PROFILE_TOP = 60
HOP_TOP = 25

# Beschriftete Hotwallets, identisch zum Abfluss-Tracer. Nur eintragen, was
# kaspa.stream oder die Boerse selbst ausweist.
KNOWN_SOURCE = "kaspa.stream address labels, geprueft am 2026-08-03"
KNOWN = {
    "kaspa:qrelgny7sr3vahq69yykxx36m65gvmhryxrlwngfzgu8xkdslum2yxjp3ap8m": "gate.io",
    "kaspa:qrvum29vk365g0zcd5gx3c7h829etfq2ytdmscjzw4zw04fjfnprcg9c3tges": "bybit",
    "kaspa:qqywx2wszmnrsu0mzgav85rdwvzangfpdj9j3ady9jpr7hu4u8c2wl9wqgd6j": "bitget",
    "kaspa:qzxs23g7txh3wq9d0t2z0hluhsflvzpf6d0yfum830ppumgtxa5d7zqca8r67": "bitvavo",
}


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


def out_addr(o):
    return o.get("script_public_key_address") or o.get("address") or ""


# ---------------------------------------------------------------------------
# 1. Transaktionen holen. Identisch zum Abfluss-Tracer.
# ---------------------------------------------------------------------------
def fetch_transactions(address, max_pages=MAX_PAGES):
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
                print(f"WARN seitenroute nicht verfuegbar ({e}), "
                      f"versuche offset-paging", file=sys.stderr)
                return fetch_transactions_offset(address, max_pages)
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
        if len(batch) < PAGE_LIMIT or fresh == 0 or not oldest:
            break
        before = oldest
    return txs


def fetch_transactions_offset(address, max_pages=MAX_PAGES):
    txs = []
    for page in range(max_pages):
        url = (f"{API}/addresses/{address}/full-transactions"
               f"?limit={PAGE_LIMIT}&offset={page * PAGE_LIMIT}"
               f"&resolve_previous_outpoints=light")
        batch = get_json(url)
        if not batch:
            break
        txs.extend(batch)
        if len(batch) < PAGE_LIMIT:
            break
    return txs


# ---------------------------------------------------------------------------
# 2. Zufluesse und ihre Absender. Reine Funktion, ohne Netz.
# ---------------------------------------------------------------------------
def inflows_with_sources(txs, address=ADDRESS, dust=DUST_KAS):
    """Liefert je Zufluss die Absender. Eigene Eingaenge zaehlen nicht."""
    result = []
    unresolved = 0
    for t in txs:
        bt = t.get("block_time") or 0
        gain = 0.0
        for o in t.get("outputs") or []:
            if out_addr(o) == address:
                gain += float(o.get("amount", 0)) / SOMPI
        spend = 0.0
        srcs = {}
        inputs = t.get("inputs") or []
        for i in inputs:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None:
                unresolved += 1
                continue
            amt = float(amt) / SOMPI
            if a == address:
                spend += amt
            else:
                srcs[a] = srcs.get(a, 0.0) + amt
        net = gain - spend
        if net <= dust:
            continue
        # Zurechnung: jeder Absender bekommt seinen Anteil am NETTO-Zufluss,
        # nicht seinen Brutto-Input. Sonst zaehlt das Wechselgeld der
        # Hotwallets mit und die Summen explodieren (siehe Lauf #2, 155.7%).
        tot = sum(srcs.values())
        if tot > 0:
            f = net / tot
            srcs = {a: v * f for a, v in srcs.items()}
        # Wir haben mehr bekommen als ausgegeben. Das ist ein echter Zufluss.
        coinbase = len(inputs) == 0
        result.append({
            "ts": bt,
            "day": day(bt),
            "tx": t.get("transaction_id", ""),
            "net_in_kas": round(net, 8),
            "coinbase": coinbase,
            "sources": [
                {"address": a, "kas": round(v, 8)}
                for a, v in sorted(srcs.items(), key=lambda x: -x[1])
            ],
        })
    result.sort(key=lambda x: x["ts"])
    return result, unresolved


# ---------------------------------------------------------------------------
# 3. Absender profilieren
# ---------------------------------------------------------------------------
def tx_count(address):
    try:
        d = get_json(f"{API}/addresses/{address}/transactions-count", timeout=20)
        if isinstance(d, dict):
            for k in ("total", "count", "transaction_count"):
                if k in d:
                    return int(d[k]), "api"
        if isinstance(d, int):
            return d, "api"
    except Exception as e:
        print(f"    hinweis: transactions-count nicht verfuegbar ({e})",
              file=sys.stderr)
    try:
        txs = fetch_transactions(address, max_pages=HOP_PAGES)
        n = len(txs)
        exact = n < PAGE_LIMIT * HOP_PAGES
        return n, ("gezaehlt" if exact else "mindestens")
    except Exception as e:
        print(f"    WARN profil fehlgeschlagen fuer {address[:24]} ({e})",
              file=sys.stderr)
        return None, "unbekannt"


def get_balance(address):
    try:
        d = get_json(f"{API}/addresses/{address}/balance", timeout=20)
        return float(d["balance"]) / SOMPI
    except Exception:
        return None


def prev_hop(address, before_ts, min_kas):
    """Woher hatte der Absender die Coins vor unserem Zufluss.

    Wir suchen die letzte Transaktion VOR dem Zufluss, in der diese Adresse
    Empfaenger war, und nehmen den groessten fremden Absender daraus.
    """
    try:
        txs = fetch_transactions(address, max_pages=HOP_PAGES)
    except Exception:
        return None
    cands = []
    for t in txs:
        bt = t.get("block_time") or 0
        if bt >= before_ts:
            continue
        gain = 0.0
        for o in t.get("outputs") or []:
            if out_addr(o) == address:
                gain += float(o.get("amount", 0)) / SOMPI
        if gain < min_kas * 0.5:
            continue
        best = None
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if not a or a == address or amt is None:
                continue
            amt = float(amt) / SOMPI
            if best is None or amt > best["kas"]:
                best = {"address": a, "kas": round(amt, 8)}
        if best is None and not (t.get("inputs") or []):
            best = {"address": "coinbase", "kas": round(gain, 8)}
        if best:
            cands.append({"ts": bt, "day": day(bt),
                          "tx": t.get("transaction_id", ""), "frm": best})
    if not cands:
        return None
    cands.sort(key=lambda x: -x["ts"])
    return cands[0]


def classify_source(addr, profile, hop):
    """Einschaetzung mit Begruendung, nie eine nackte Behauptung.

    Fuer die Formulierung nach aussen gilt spiegelbildlich zur Abflussregel:
    ein Eingang von einer Boersen-Hotwallet ist eine ABHEBUNG, kein belegter
    Kauf. Die Kette zeigt den Weg, nicht den Eigentuemer und nicht das Motiv.
    """
    n = profile.get("tx_count")

    if addr == "coinbase":
        return ("mining direkt", "coinbase-transaktion, block reward", None)

    if addr in KNOWN:
        return ("boerse", f"absender ist auf kaspa.stream als "
                f"{KNOWN[addr]} beschriftet", KNOWN[addr])

    hop_addr = hop["frm"]["address"] if hop else None
    if hop_addr and hop_addr in KNOWN:
        return ("boerse ueber zwischenadresse",
                f"absender wurde am {hop['day']} von der auf kaspa.stream als "
                f"{KNOWN[hop_addr]} beschrifteten adresse befuellt",
                KNOWN[hop_addr])

    if n is not None and n >= BUSY_TX:
        return ("boerse wahrscheinlich",
                f"absender hat {n:,} transaktionen, das ist kein privates "
                f"wallet", None)

    hop_n = (hop or {}).get("frm_profile", {}).get("tx_count")
    if hop_n is not None and hop_n >= BUSY_TX:
        return ("boerse ueber zwischenadresse wahrscheinlich",
                f"absender wurde am {hop['day']} von einer adresse mit "
                f"{hop_n:,} transaktionen befuellt", None)

    if hop_addr == "coinbase":
        return ("mining ueber zwischenadresse",
                f"absender wurde am {hop['day']} direkt aus einem block "
                f"reward befuellt", None)

    if n is not None and n < 50:
        return ("frisches wallet",
                f"absender hat nur {n} transaktionen und kein label, "
                f"herkunft dahinter " +
                (f"ebenfalls unbeschriftet ({hop_addr[:24]})" if hop_addr
                 else "nicht gefunden"), None)

    return ("unklar", "kein label, kein eindeutiges profil", None)


# ---------------------------------------------------------------------------
def main():
    print("hole transaktionen von entity x ...")
    txs = fetch_transactions(ADDRESS)
    print(f"{len(txs)} transaktionen insgesamt")
    if not txs:
        print("ERROR keine transaktionen erhalten", file=sys.stderr)
        sys.exit(1)

    flows, unresolved = inflows_with_sources(txs)
    if unresolved:
        print(f"hinweis: {unresolved} eingaenge ohne aufgeloeste herkunft")
    print(f"{len(flows)} echte zufluesse gefunden\n")

    total_in = sum(f["net_in_kas"] for f in flows)
    coinbase_kas = sum(f["net_in_kas"] for f in flows if f["coinbase"])
    coinbase_n = sum(1 for f in flows if f["coinbase"])

    # Absender ueber alle Zufluesse aggregieren
    senders = {}
    for f in flows:
        if f["coinbase"]:
            continue
        for s in f["sources"]:
            rec = senders.setdefault(s["address"], {
                "kas": 0.0, "transfers": 0,
                "first_day": f["day"], "last_day": f["day"],
                "last_ts": f["ts"], "min_kas": s["kas"]})
            rec["kas"] = round(rec["kas"] + s["kas"], 8)
            rec["transfers"] += 1
            rec["min_kas"] = min(rec["min_kas"], s["kas"])
            if f["day"] < rec["first_day"]:
                rec["first_day"] = f["day"]
            if f["day"] > rec["last_day"]:
                rec["last_day"] = f["day"]
                rec["last_ts"] = f["ts"]
    print(f"{len(senders)} verschiedene absenderadressen")
    print(f"davon werden die groessten {min(PROFILE_TOP, len(senders))} "
          f"profiliert, hop zurueck bei den groessten "
          f"{min(HOP_TOP, len(senders))}\n")

    ranked = sorted(senders.items(), key=lambda x: -x[1]["kas"])
    results = []
    for idx, (addr, rec) in enumerate(ranked):
        entry = {"address": addr, **{k: rec[k] for k in
                 ("kas", "transfers", "first_day", "last_day")}}
        if idx < PROFILE_TOP:
            bal = get_balance(addr)
            n, how = tx_count(addr)
            entry["profile"] = {"balance_kas": bal, "tx_count": n,
                                "tx_count_source": how}
            hop = None
            if idx < HOP_TOP:
                hop = prev_hop(addr, rec["last_ts"], rec["min_kas"])
                if hop and hop["frm"]["address"] not in ("coinbase",):
                    hb = get_balance(hop["frm"]["address"])
                    hn, hhow = tx_count(hop["frm"]["address"])
                    hop["frm_profile"] = {"balance_kas": hb, "tx_count": hn,
                                          "tx_count_source": hhow}
            verdict, why, exch = classify_source(addr, entry["profile"], hop)
            entry["verdict"] = verdict
            entry["reason"] = why
            entry["exchange"] = exch
            entry["prev_hop"] = hop
            label = f"[{verdict}]" + (f" -> {exch}" if exch else "")
            print(f"{addr}")
            print(f"    {rec['kas']:,.0f} KAS in {rec['transfers']} transfers "
                  f"{rec['first_day']} bis {rec['last_day']}")
            print(f"    {label}  {why}")
        else:
            entry["verdict"] = "nicht einzeln profiliert"
            entry["reason"] = "unter den kleineren absendern, nur aggregiert"
            entry["exchange"] = None
        results.append(entry)

    counts = {}
    kas_by_verdict = {}
    by_exchange = {}
    named_kas = 0.0
    for e in results:
        v = e["verdict"]
        counts[v] = counts.get(v, 0) + 1
        kas_by_verdict[v] = round(kas_by_verdict.get(v, 0.0) + e["kas"], 2)
        if e.get("exchange"):
            rec = by_exchange.setdefault(
                e["exchange"], {"kas": 0.0, "senders": 0})
            rec["kas"] = round(rec["kas"] + e["kas"], 2)
            rec["senders"] += 1
            named_kas += e["kas"]
    if coinbase_n:
        counts["mining direkt"] = counts.get("mining direkt", 0) + coinbase_n
        kas_by_verdict["mining direkt"] = round(
            kas_by_verdict.get("mining direkt", 0.0) + coinbase_kas, 2)
    named_kas = round(named_kas, 2)

    out = {
        "generated_at": int(time.time()),
        "address": ADDRESS,
        "question": ("where do entity x inflows come from. exchange hot "
                     "wallets would look like withdrawals, fresh unlabeled "
                     "clusters would fit a consolidation story, coinbase "
                     "would be mining directly."),
        "method": ("inputs per inflow transaction, self-inputs removed, "
                   "net inflow attributed to senders pro rata, senders "
                   "aggregated across all inflows, top senders profiled by "
                   "balance and transaction count, one hop traced backwards"),
        "busy_tx_threshold": BUSY_TX,
        "profiled_top": PROFILE_TOP,
        "hop_top": HOP_TOP,
        "known_labels": len(KNOWN),
        "known_label_source": KNOWN_SOURCE,
        "transactions_total": len(txs),
        "inflow_count": len(flows),
        "inflow_kas": round(total_in, 2),
        "coinbase_inflows": coinbase_n,
        "coinbase_kas": round(coinbase_kas, 2),
        "distinct_senders": len(senders),
        "verdict_counts": counts,
        "kas_by_verdict": kas_by_verdict,
        "by_exchange": by_exchange,
        "named_exchange_kas": named_kas,
        "named_exchange_share": (round(named_kas / total_in, 4)
                                 if total_in else 0),
        "caveat": ("an inflow from an exchange wallet is a withdrawal, not "
                   "a proven buy. a fresh unlabeled sender is consistent "
                   "with consolidation, not proof of it. the chain shows "
                   "the path, never the owner and never the motive."),
        "senders": results,
        "inflows_head": flows[:50],
        "inflows_tail": flows[-50:],
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, indent=2)

    print("=" * 64)
    print("ENTITY X INFLOWS")
    print("=" * 64)
    print(f"zufluesse           {len(flows)}")
    print(f"KAS jemals rein     {total_in:,.0f}")
    print(f"davon coinbase      {coinbase_kas:,.0f} KAS "
          f"in {coinbase_n} block rewards")
    print(f"absender gesamt     {len(senders)}")
    for k, v in sorted(counts.items(), key=lambda x: -kas_by_verdict.get(x[0], 0)):
        print(f"  {k:<40} {v:>4}  {kas_by_verdict.get(k, 0):>16,.0f} KAS")
    if by_exchange:
        print("-" * 64)
        print("NACH BOERSE (nur belegte labels)")
        for e, r in sorted(by_exchange.items(), key=lambda x: -x[1]["kas"]):
            share = r["kas"] / total_in * 100 if total_in else 0
            print(f"  {e:<12} {r['kas']:>16,.0f} KAS  {share:5.1f}%  "
                  f"{r['senders']} absender")
    print("=" * 64)
    print("merke: eingang von einer boerse ist eine abhebung, kein belegter")
    print("kauf. frische absender passen zur konsolidierungs-these, beweisen")
    print("sie aber nicht. wir melden die bewegung, nie das motiv.")
    print(f"\ngeschrieben nach {OUT_FILE}")


if __name__ == "__main__":
    main()
