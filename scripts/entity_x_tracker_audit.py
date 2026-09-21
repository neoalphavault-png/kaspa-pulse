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

# Clusterbildung. Runden, bis nichts Neues mehr kommt, mit Notbremse.
CLUSTER_ROUNDS = 5
CLUSTER_MAX = 200
CLUSTER_PAGES = 20

# Der konkrete Verdachtsfall aus dem Pruefauftrag: diese Adresse hat
# 109.541.081,40 KAS an Entity X gesendet, und das Zufluss-Skript notiert
# als Herkunft dahinter die Entity-X-Adresse selbst.
WATCH_ADDRESS = ("kaspa:qr4znetsvjehrrfn75rra5zej50nsgx7v3zlkk54ljsddsry"
                 "6sa6y3zs6s2sz")


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
# ---------------------------------------------------------------------------
# Hops und Urteile. Wortgleich zu entity_x_inflows.py (Zufluss) und
# entity_x_outflows.py (Abfluss). Angeglichen am 21.09.2026, nachdem die
# beiden Implementierungen desselben Urteils 87,98 gegen 88,06 Prozent
# geliefert hatten. Ursache war nicht die Reihenfolge im Urteil, sondern
# die Auswahl des Hops: hier wurde der zuletzt eingegangene Betrag genommen,
# dort der letzte Eingang VOR unserem Transfer und mindestens halb so gross.
# Die zweite Definition ist die richtige, denn gesucht ist die Herkunft der
# Coins, die zu uns kamen, nicht irgendein spaeterer Eingang.
# ---------------------------------------------------------------------------
def prev_hop(address, before_ts, min_kas):
    """Woher hatte der Absender die Coins vor unserem Zufluss.

    Feldbedeutung, siehe entity_x_inflows.py:
      frm.input_kas  Groesse des Inputs DIESER Adresse in der
                     Herkunftstransaktion. NICHT der ueberwiesene Betrag.
      received_kas   Was die profilierte Adresse dort wirklich bekam.
    """
    txs = fetch_transactions(address, max_pages=HOP_PAGES, quiet=True)
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
            if best is None or amt > best["input_kas"]:
                best = {"address": a, "input_kas": round(amt, 8)}
        if best is None and not (t.get("inputs") or []):
            best = {"address": "coinbase", "input_kas": None}
        if best:
            cands.append({"ts": bt, "day": day(bt),
                          "tx": t.get("transaction_id", ""), "frm": best,
                          "received_kas": round(gain, 8)})
    if not cands:
        return None
    cands.sort(key=lambda x: -x["ts"])
    hop = cands[0]
    if hop["frm"]["address"] != "coinbase":
        hop["frm_profile"] = profile(hop["frm"]["address"])
    return hop


def next_hop(address, after_ts, min_kas):
    """Wohin hat der Empfaenger das Geld danach weitergeschickt.

    to.kas ist hier ein echter Ueberweisungsbetrag, naemlich der groesste
    Output der Weiterleitung. Deshalb bleibt der Name so.
    """
    txs = fetch_transactions(address, max_pages=HOP_PAGES, quiet=True)
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
            cands.append({"ts": bt, "day": day(bt),
                          "tx": t.get("transaction_id", ""), "to": best})
    if not cands:
        return None
    cands.sort(key=lambda x: x["ts"])
    hop = cands[0]
    hop["to_profile"] = profile(hop["to"]["address"])
    return hop


def classify_source(addr, prof, hop):
    """Zufluss-Urteil. Reihenfolge wortgleich zu entity_x_inflows.py.

    Rueckgabe (verdict, reason, exchange). Ein Boersenname kommt
    ausschliesslich aus KNOWN, also aus einem fremden Label, nie aus
    unserer eigenen Vermutung. Ein Eingang von einer Boersen-Hotwallet ist
    eine Abhebung, kein belegter Kauf.
    """
    n = prof.get("tx_count")
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
    hop_n = ((hop or {}).get("frm_profile") or {}).get("tx_count")
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


def classify_dest(addr, prof, hop, received_kas):
    """Abfluss-Urteil. Reihenfolge wortgleich zu entity_x_outflows.py.

    Auch ein sicher benannter Boersen-Eingang ist keine Aussage ueber einen
    Verkauf. Er ist eine Einzahlung. Was danach passiert, sieht die Kette
    nicht.
    """
    n = prof.get("tx_count")
    bal = prof.get("balance_kas")
    if addr in KNOWN:
        return ("boerse", f"empfaenger ist auf kaspa.stream als "
                f"{KNOWN[addr]} beschriftet", KNOWN[addr])
    hop_addr = hop["to"]["address"] if hop else None
    if hop_addr and hop_addr in KNOWN:
        return ("boerse ueber zwischenadresse",
                f"am {hop['day']} weitergeleitet an die auf kaspa.stream als "
                f"{KNOWN[hop_addr]} beschriftete adresse", KNOWN[hop_addr])
    if n is not None and n >= BUSY_TX:
        return ("boerse wahrscheinlich",
                f"empfaenger hat {n:,} transaktionen, das ist kein privates "
                f"wallet", None)
    hop_n = ((hop or {}).get("to_profile") or {}).get("tx_count")
    if hop_n is not None and hop_n >= BUSY_TX:
        return ("boerse wahrscheinlich",
                f"weitergeleitet am {hop['day']} an eine adresse mit "
                f"{hop_n:,} transaktionen", None)
    if hop:
        return ("weitergeschickt, ziel unklar",
                f"am {hop['day']} weiter an {hop_addr[:28]}", None)
    if bal is not None and bal >= received_kas * 0.95:
        return ("liegt noch da",
                f"empfaenger haelt heute {bal:,.0f} KAS, hat also nichts "
                f"bewegt", None)
    if bal is not None:
        return ("unklar",
                f"empfaenger haelt heute {bal:,.0f} KAS von "
                f"{received_kas:,.0f} erhaltenen, kein weiterer sprung "
                f"gefunden", None)
    return ("unklar", "empfaenger nicht profilierbar", None)


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
            hop = next_hop(a, f["ts"], kas) if kas > DUST_KAS else None
            verdict, reason, exch = classify_dest(a, prof, hop, kas)
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
    #
    # REGEL A, common input ownership, ausformuliert:
    #
    #   Zwei Adressen gehoeren demselben Eigentuemer, wenn sie in derselben
    #   Transaktion gemeinsam als Input auftreten. Begruendung: jeder Input
    #   wird einzeln signiert, und die Transaktion ist nur gueltig, wenn
    #   jede einzelne Signatur stimmt. Wer sie also absetzen konnte, hielt
    #   in diesem Moment die privaten Schluessel zu allen ihren Inputs.
    #
    #   Die Regel ist transitiv: gehoert B zu A und C zu B, gehoert C zu A.
    #   Deshalb wird in Runden expandiert, bis nichts Neues mehr kommt.
    #
    #   Grenzen, damit niemand die Regel ueberdehnt:
    #   - Sammeltransaktionen mehrerer Parteien (CoinJoin und Verwandte)
    #     brechen sie. Auf Kaspa sind sie nicht verbreitet, ausschliessen
    #     laesst sich das nicht.
    #   - Eine Boerse, die Einzahlungen einsammelt, signiert ebenfalls
    #     gemeinsam. Jedes Mitglied wird deshalb profiliert. Eine Adresse
    #     mit zehntausenden Transaktionen ist kein privates Wallet; sie
    #     wird markiert und nicht weiter expandiert, statt stillschweigend
    #     einsortiert zu werden.
    #   - Die Regel sagt "derselbe Schluesselhalter", nicht "dieselbe
    #     Person". Wer die Schluessel haelt, sagt die Kette nie.
    #
    # Regeln B und C sind schwaecher. Sie werden getrennt ausgewiesen und
    # NIE in den Cluster gemischt.

    def coinputs_of(address, tx_list):
        """Adressen, die mit `address` gemeinsam als Input signiert haben."""
        found = {}
        for t in tx_list:
            ins, mine = [], False
            for i in t.get("inputs") or []:
                a = i.get("previous_outpoint_address")
                amt = i.get("previous_outpoint_amount")
                if a is None or amt is None:
                    continue
                if a == address:
                    mine = True
                else:
                    ins.append((a, float(amt) / SOMPI))
            if not mine or not ins:
                continue
            bt = t.get("block_time") or 0
            for a, kas in ins:
                c = found.setdefault(a, {
                    "txs": 0, "kas": 0.0, "first": None, "last": None,
                    "via": address, "example_tx": t.get("transaction_id", "")})
                c["txs"] += 1
                c["kas"] += kas
                if c["first"] is None or bt < c["first"]:
                    c["first"] = bt
                if c["last"] is None or bt > c["last"]:
                    c["last"] = bt
        return found

    cluster = {ADDRESS}
    cluster_evidence = {}
    frontier = [(ADDRESS, txs)]
    for runde in range(CLUSTER_ROUNDS):
        neu = []
        for addr, tx_list in frontier:
            for a, ev in coinputs_of(addr, tx_list).items():
                if a in cluster:
                    continue
                cluster.add(a)
                cluster_evidence[a] = ev
                neu.append(a)
        print(f"  runde {runde + 1}: {len(neu)} neue adressen, "
              f"cluster jetzt {len(cluster)} inklusive entity x")
        if not neu or len(cluster) > CLUSTER_MAX:
            break
        frontier = []
        for a in neu:
            p = profile(a)
            if (p.get("tx_count") or 0) >= BUSY_TX:
                cluster_evidence[a]["expansion_stopped"] = (
                    f"{p['tx_count']:,} transaktionen, nicht weiter expandiert")
                continue
            frontier.append(
                (a, fetch_transactions(a, max_pages=CLUSTER_PAGES, quiet=True)))
        if not frontier:
            break

    members = sorted(cluster - {ADDRESS})
    print(f"  REGEL A findet {len(members)} adressen neben der entity-x-adresse")

    cluster_detail = []
    for a in members:
        p = profile(a)
        ev = cluster_evidence.get(a, {})
        cluster_detail.append({
            "address": a,
            "rule": "gemeinsamer input",
            "coinput_txs": ev.get("txs"),
            "coinput_kas": round(ev.get("kas", 0.0), 8),
            "first_day": day(ev["first"]) if ev.get("first") else None,
            "last_day": day(ev["last"]) if ev.get("last") else None,
            "via": ev.get("via"),
            "example_tx": ev.get("example_tx"),
            "expansion_stopped": ev.get("expansion_stopped"),
            "balance_kas": p.get("balance_kas"),
            "tx_count": p.get("tx_count"),
            "label": KNOWN.get(a),
        })
        print(f"    {a}")
        print(f"      {ev.get('txs')} gemeinsame tx, bestand "
              f"{p.get('balance_kas')}, {p.get('tx_count')} tx gesamt"
              f"{', LABEL ' + KNOWN[a] if a in KNOWN else ''}")
        if ev.get("expansion_stopped"):
            print(f"      ACHTUNG {ev['expansion_stopped']}")

    cluster_member_balance = sum((c["balance_kas"] or 0) for c in cluster_detail)
    print(f"  bestand der mitglieder zusammen: {cluster_member_balance:,.8f} KAS")

    # Wie viel der Bruttoakkumulation ist internes Umschichten? Pro Zufluss
    # der Anteil, der aus einer Clusteradresse kam, pro rata auf den Netto-
    # zufluss gerechnet. Gleiche Zurechnung wie im Zuflussledger unten.
    def cluster_share_of_inflows(member_set):
        total, hits = 0.0, 0
        per_addr = defaultdict(float)
        for f in inflows:
            gross_in = defaultdict(float)
            for i in f["raw"].get("inputs") or []:
                a = i.get("previous_outpoint_address")
                amt = i.get("previous_outpoint_amount")
                if a is None or amt is None or a == ADDRESS:
                    continue
                gross_in[a] += float(amt) / SOMPI
            tot = sum(gross_in.values())
            if tot <= 0:
                continue
            part = 0.0
            for a, kas in gross_in.items():
                if a in member_set:
                    share = f["kas"] * (kas / tot)
                    part += share
                    per_addr[a] += share
            if part > 0:
                total += part
                hits += 1
        return total, hits, per_addr

    internal_kas, internal_tx, internal_per = cluster_share_of_inflows(set(members))
    print(f"  davon internes umschichten (regel A): {internal_kas:,.2f} KAS "
          f"aus {internal_tx} zufluessen = "
          f"{internal_kas / gross * 100 if gross else 0:.4f} prozent des brutto")

    # Regel B, rundlauf. Adressen, die von der entity-x-adresse bezahlt
    # wurden UND an sie gesendet haben. Bewusst ueber ALLE transaktionen,
    # in denen entity x als input steht, nicht nur ueber die netto-
    # abfluesse. Sonst faellt genau der fall durch, in dem entity x in
    # derselben transaktion sendet und fast alles als wechselgeld
    # zurueckbekommt.
    paid_by_x, sent_to_x = set(), set()
    for t in txs:
        mine = any((i.get("previous_outpoint_address") == ADDRESS)
                   for i in (t.get("inputs") or []))
        if mine:
            for o in t.get("outputs") or []:
                a = out_addr(o)
                if a and a != ADDRESS:
                    paid_by_x.add(a)
    for f in inflows:
        for i in f["raw"].get("inputs") or []:
            a = i.get("previous_outpoint_address")
            if a and a != ADDRESS:
                sent_to_x.add(a)
    roundtrip = sorted(paid_by_x & sent_to_x)
    rt_kas, rt_tx, rt_per = cluster_share_of_inflows(set(roundtrip))
    print(f"  REGEL B, rundlauf: {len(roundtrip)} adressen wurden von entity x "
          f"bezahlt und haben an entity x gesendet")
    print(f"    sie stehen fuer {rt_kas:,.2f} KAS zufluss = "
          f"{rt_kas / gross * 100 if gross else 0:.4f} prozent des brutto")
    roundtrip_detail = []
    for a in sorted(roundtrip, key=lambda x: -rt_per.get(x, 0)):
        p = profile(a)
        roundtrip_detail.append({
            "address": a, "kas_to_x": round(rt_per.get(a, 0.0), 8),
            "balance_kas": p.get("balance_kas"), "tx_count": p.get("tx_count"),
            "in_rule_a": a in cluster, "label": KNOWN.get(a),
        })
        print(f"    {a}")
        print(f"      zufluss an entity x {rt_per.get(a, 0.0):,.2f} KAS, "
              f"bestand {p.get('balance_kas')}, {p.get('tx_count')} tx, "
              f"regel A: {'ja' if a in cluster else 'nein'}")

    # Regel C, der konkrete verdachtsfall aus dem pruefauftrag.
    print(f"  REGEL C, einzelpruefung {WATCH_ADDRESS[:24]}...")
    watch = {
        "address": WATCH_ADDRESS,
        "in_rule_a": WATCH_ADDRESS in cluster,
        "in_rule_b": WATCH_ADDRESS in set(roundtrip),
        "paid_by_entity_x": WATCH_ADDRESS in paid_by_x,
        "sent_to_entity_x": WATCH_ADDRESS in sent_to_x,
        "kas_to_entity_x": round(rt_per.get(WATCH_ADDRESS, 0.0), 8),
        "profile": profile(WATCH_ADDRESS),
        "coinput_evidence": cluster_evidence.get(WATCH_ADDRESS),
    }
    # Woher kam das geld, das entity x an diese adresse geschickt hat
    paid_detail = []
    for t in txs:
        mine = any((i.get("previous_outpoint_address") == ADDRESS)
                   for i in (t.get("inputs") or []))
        if not mine:
            continue
        got = sum(float(o.get("amount", 0)) / SOMPI
                  for o in (t.get("outputs") or [])
                  if out_addr(o) == WATCH_ADDRESS)
        if got > DUST_KAS:
            bt = t.get("block_time") or 0
            paid_detail.append({"day": day(bt), "utc": stamp(bt),
                                "kas": round(got, 8),
                                "tx": t.get("transaction_id", "")})
    watch["received_from_entity_x"] = paid_detail
    watch["received_from_entity_x_kas"] = round(
        sum(x["kas"] for x in paid_detail), 8)
    for k, v in watch.items():
        if k not in ("received_from_entity_x",):
            print(f"    {k}: {v}")
    for x in paid_detail:
        print(f"    entity x -> watch  {x['utc']}  {x['kas']:,.2f} KAS  {x['tx']}")


    # -------------------------------------------------------------- 6
    print("\n[6] zuflussledger, anteil aus benannten boersen-wallets")
    # last_ts und min_kas werden fuer die Hop-Suche gebraucht: gesucht ist
    # der letzte Eingang VOR unserem Transfer, mindestens halb so gross.
    # Gleiche Definition wie in entity_x_inflows.py.
    senders = defaultdict(lambda: {"kas": 0.0, "transfers": 0,
                                   "first": None, "last": None,
                                   "min_kas": None})
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
            anteil = f["kas"] * (kas / tot)
            s["kas"] += anteil
            s["transfers"] += 1
            if s["min_kas"] is None or anteil < s["min_kas"]:
                s["min_kas"] = anteil
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
            hop = (prev_hop(a, s["last"], s["min_kas"] or 0.0)
                   if rank < HOP_TOP else None)
            verdict, reason, exch = classify_source(a, p, hop)
        else:
            p, hop = {}, None
            verdict, reason, exch = ("nicht einzeln profiliert",
                                     "unterhalb der profilierungsgrenze", None)
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
        "netto_cluster": ledger_net + cluster_member_balance,
        "brutto_ohne_internes": gross - internal_kas,
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
            "rule_a": ("zwei adressen gehoeren demselben schluesselhalter, "
                       "wenn sie in derselben transaktion gemeinsam als "
                       "input auftreten. transitiv angewandt, in runden, "
                       "bis nichts neues mehr kommt."),
            "rule_a_member_count": len(members),
            "rule_a_members": cluster_detail,
            "rule_a_member_balance_kas": round(cluster_member_balance, 8),
            "rule_a_internal_recycling_kas": round(internal_kas, 8),
            "rule_a_internal_recycling_inflows": internal_tx,
            "rule_a_internal_recycling_share_of_gross": (
                round(internal_kas / gross, 6) if gross else None),
            "rule_b": ("adresse wurde von entity x bezahlt UND hat an "
                       "entity x gesendet. schwaecher als regel A, nicht "
                       "in den cluster gemischt."),
            "rule_b_roundtrip_count": len(roundtrip),
            "rule_b_roundtrip": roundtrip_detail,
            "rule_b_kas_to_x": round(rt_kas, 8),
            "rule_b_share_of_gross": round(rt_kas / gross, 6) if gross else None,
            "rule_c_watch_address": watch,
            "holdings_one_address_kas": round(ledger_net, 8),
            "holdings_cluster_kas": round(ledger_net + cluster_member_balance, 8),
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
