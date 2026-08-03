#!/usr/bin/env python3
# Kaspa Pulse - Entity X Outflow Tracing v1.0
# Ablageort im Repo: scripts/entity_x_outflows.py
#
# Frage, die das Skript beantwortet:
#   "Entity X hat X mal Coins rausgeschickt. Wohin?"
#
# Vorgehen:
#   1. Komplette Transaktionshistorie der Entity-X-Adresse holen und die
#      echten Abfluesse isolieren. Gleiche Netto-Logik wie im Cost-Basis-
#      Skript, damit beide Skripte dieselbe Zahl an Abfluessen sehen.
#   2. Pro Abfluss die Empfaengeradressen aufloesen. Wechselgeld an uns
#      selbst zaehlt nicht als Empfaenger.
#   3. Jede Empfaengeradresse profilieren: heutiger Kontostand und Anzahl
#      Transaktionen. Eine Adresse mit zehntausenden Transaktionen ist eine
#      Boersen-Hotwallet. Eine Adresse mit drei Transaktionen ist es nicht.
#   4. Zweiter Hop. Boersen benutzen Einzahladressen, die kurz darauf in
#      eine Hotwallet geleert werden. Erst dieser zweite Sprung verraet,
#      ob verkauft wurde. Wir schauen deshalb, wohin der Empfaenger das
#      Geld weitergeschickt hat.
#
# Was das Skript NICHT tut: es behauptet nicht, dass verkauft wurde. Es
# liefert Ziel, Betrag, Datum und eine Einschaetzung mit Begruendung.
# Die Aussage "nie verkauft" ist eine Negativbehauptung. Die duerfen wir
# nur veroeffentlichen, wenn wir jede einzelne Transaktion gezaehlt haben.
# Genau das ist der Zweck hier.
#
# Nur Python-Standardbibliothek, keine Abhaengigkeiten.

import json
import os
import sys
import time
import urllib.request

ADDRESS = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
OUT_FILE = "data/entity-x-outflows.json"

API = "https://api.kaspa.org"
SOMPI = 100_000_000
UA = {"User-Agent": "kaspapulse-outflows/1.0"}

PAGE_LIMIT = 500
MAX_PAGES = 200
DUST_KAS = 1.0

# Ab dieser Anzahl Transaktionen ist eine Adresse keine Privatperson mehr.
# Bewusst hoch angesetzt. Lieber "unklar" sagen als eine Boerse erfinden.
BUSY_TX = 5000

# Adressen, die wir sicher zuordnen koennen. Bitte nur eintragen, was auf
# kaspa.stream oder von der Boerse selbst als solche ausgewiesen ist.
# Solange die Liste leer ist, arbeitet das Skript rein verhaltensbasiert.
KNOWN = {
    # "kaspa:q...": "binance hot wallet",
}

# Wie viele Transaktionen wir uns pro Empfaenger ansehen, um den zweiten
# Hop zu finden. Bei Hotwallets waeren es Millionen, das brauchen wir nicht.
HOP_PAGES = 2


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
# 1. Transaktionen holen. Bewusst identisch zum Cost-Basis-Skript.
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
# 2. Abfluesse und ihre Empfaenger. Reine Funktion, ohne Netz, damit sie
#    sich testen laesst.
# ---------------------------------------------------------------------------
def outflows_with_destinations(txs, address=ADDRESS, dust=DUST_KAS):
    """Liefert je Abfluss die Empfaenger ohne unser eigenes Wechselgeld."""
    result = []
    unresolved = 0
    for t in txs:
        bt = t.get("block_time") or 0
        gain = 0.0
        dests = {}
        for o in t.get("outputs") or []:
            a = out_addr(o)
            amt = float(o.get("amount", 0)) / SOMPI
            if a == address:
                gain += amt
            elif a:
                dests[a] = dests.get(a, 0.0) + amt
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
        if net >= -dust:
            continue
        # Wir haben mehr ausgegeben als bekommen. Das ist ein echter Abfluss.
        result.append({
            "ts": bt,
            "day": day(bt),
            "tx": t.get("transaction_id", ""),
            "net_out_kas": round(-net, 8),
            "sent_gross_kas": round(spend, 8),
            "change_back_kas": round(gain, 8),
            "destinations": [
                {"address": a, "kas": round(v, 8)}
                for a, v in sorted(dests.items(), key=lambda x: -x[1])
            ],
        })
    result.sort(key=lambda x: x["ts"])
    return result, unresolved


# ---------------------------------------------------------------------------
# 3. Empfaenger profilieren
# ---------------------------------------------------------------------------
def tx_count(address):
    """Anzahl Transaktionen. Die schnelle Route zuerst, sonst zaehlen wir."""
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
        # Wenn wir das Seitenlimit ausgereizt haben, ist n eine Untergrenze.
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


def next_hop(address, after_ts, min_kas):
    """Wohin hat der Empfaenger das Geld danach weitergeschickt.

    Wir suchen die erste Transaktion nach unserem Abfluss, in der diese
    Adresse selbst Sender ist, und nehmen den groessten Empfaenger daraus.
    """
    try:
        txs = fetch_transactions(address, max_pages=HOP_PAGES)
    except Exception:
        return None
    cands = []
    for t in txs:
        bt = t.get("block_time") or 0
        if bt <= after_ts:
            continue
        spends = any(i.get("previous_outpoint_address") == address
                     for i in (t.get("inputs") or []))
        if not spends:
            continue
        best = None
        for o in t.get("outputs") or []:
            a = out_addr(o)
            if not a or a == address:
                continue
            amt = float(o.get("amount", 0)) / SOMPI
            if best is None or amt > best["kas"]:
                best = {"address": a, "kas": round(amt, 8)}
        if best and best["kas"] >= min_kas * 0.5:
            cands.append({"ts": bt, "day": day(bt), "tx": t.get("transaction_id", ""),
                          "to": best})
    if not cands:
        return None
    cands.sort(key=lambda x: x["ts"])
    return cands[0]


def classify(addr, profile, hop, received_kas):
    """Einschaetzung mit Begruendung. Nie eine nackte Behauptung."""
    if addr in KNOWN:
        return "boerse", f"adresse ist als {KNOWN[addr]} bekannt"
    n = profile.get("tx_count")
    bal = profile.get("balance_kas")
    if n is not None and n >= BUSY_TX:
        return "boerse wahrscheinlich", (
            f"empfaenger hat {n:,} transaktionen, das ist kein privates wallet")
    if hop and hop["to"]["address"] in KNOWN:
        return "boerse wahrscheinlich", (
            f"weitergeleitet an {KNOWN[hop['to']['address']]} am {hop['day']}")
    if hop and hop.get("to_profile", {}).get("tx_count", 0) >= BUSY_TX:
        return "boerse wahrscheinlich", (
            f"weitergeleitet am {hop['day']} an eine adresse mit "
            f"{hop['to_profile']['tx_count']:,} transaktionen")
    if hop:
        return "weitergeschickt, ziel unklar", (
            f"am {hop['day']} weiter an {hop['to']['address'][:28]}")
    if bal is not None and bal >= received_kas * 0.95:
        return "liegt noch da", (
            f"empfaenger haelt heute {bal:,.0f} KAS, hat also nichts bewegt")
    if bal is not None:
        return "unklar", (
            f"empfaenger haelt heute {bal:,.0f} KAS von {received_kas:,.0f} "
            f"erhaltenen, kein weiterer sprung gefunden")
    return "unklar", "empfaenger nicht profilierbar"


# ---------------------------------------------------------------------------
def main():
    print("hole transaktionen von entity x ...")
    txs = fetch_transactions(ADDRESS)
    print(f"{len(txs)} transaktionen insgesamt")
    if not txs:
        print("ERROR keine transaktionen erhalten", file=sys.stderr)
        sys.exit(1)

    flows, unresolved = outflows_with_destinations(txs)
    if unresolved:
        print(f"hinweis: {unresolved} eingaenge ohne aufgeloeste herkunft")
    print(f"{len(flows)} echte abfluesse gefunden\n")

    if not flows:
        print("keine abfluesse. die adresse hat noch nie etwas gesendet.")

    profiles = {}
    total_out = 0.0
    for f in flows:
        total_out += f["net_out_kas"]
        print(f"{f['day']}  {f['net_out_kas']:>16,.0f} KAS  {f['tx']}")
        for d in f["destinations"]:
            a = d["address"]
            if a not in profiles:
                bal = get_balance(a)
                n, how = tx_count(a)
                profiles[a] = {"balance_kas": bal, "tx_count": n,
                               "tx_count_source": how}
            hop = next_hop(a, f["ts"], d["kas"])
            if hop:
                hb = get_balance(hop["to"]["address"])
                hn, hhow = tx_count(hop["to"]["address"])
                hop["to_profile"] = {"balance_kas": hb, "tx_count": hn,
                                     "tx_count_source": hhow}
            verdict, why = classify(a, profiles[a], hop, d["kas"])
            d["verdict"] = verdict
            d["reason"] = why
            d["profile"] = profiles[a]
            d["next_hop"] = hop
            print(f"    an {a}")
            print(f"       {d['kas']:,.0f} KAS  [{verdict}]  {why}")
        print("")

    counts = {}
    for f in flows:
        for d in f["destinations"]:
            counts[d["verdict"]] = counts.get(d["verdict"], 0) + 1

    out = {
        "generated_at": int(time.time()),
        "address": ADDRESS,
        "method": ("outputs per outflow transaction, change to self removed, "
                   "recipients profiled by balance and transaction count, "
                   "one additional hop followed"),
        "busy_tx_threshold": BUSY_TX,
        "known_labels": len(KNOWN),
        "transactions_total": len(txs),
        "outflow_count": len(flows),
        "outflow_kas": round(total_out, 2),
        "verdict_counts": counts,
        "outflows": flows,
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, indent=2)

    print("=" * 64)
    print("ENTITY X OUTFLOWS")
    print("=" * 64)
    print(f"abfluesse           {len(flows)}")
    print(f"KAS jemals raus     {total_out:,.0f}")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k:<32} {v}")
    if not KNOWN:
        print("\nhinweis: KNOWN ist leer. die einschaetzung ist rein")
        print("verhaltensbasiert. sobald wir echte boersen-labels von")
        print("kaspa.stream eintragen, wird sie belastbar.")
    print("=" * 64)
    print(f"\ngeschrieben nach {OUT_FILE}")


if __name__ == "__main__":
    main()
