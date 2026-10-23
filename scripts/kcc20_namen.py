#!/usr/bin/env python3
"""Kaspa Pulse, Namen der KCC-20-Tokens aus KCC-23-Metadaten (Ben, 23.10.2026).

Je Token wird die Genesis-Transaktion gesucht und bewiesen, dann die Metadaten
der Vorbereitungs-Transaktion gelesen:

  1. Start bei der erzeugenden Tx eines lebenden Outputs des Tokens.
  2. In jeder Tx die Ausgaben mit dieser Covenant-ID nach autorisierendem
     Eingang gruppieren. Ergibt KIP-20 CovenantID(Outpoint dieses Eingangs,
     Gruppe) genau die Covenant-ID, ist das die Genesis. Sonst zum Vorgaenger
     ueber diesen Eingang und weiter.
  3. Der Outpoint der Genesis zeigt auf die Vorbereitungs-Tx. Ihr Payload ist
     nach KCC-23 ein Byte 0x00 und genau ein JSON-Objekt (name, symbol,
     decimals ...).

Bewiesen ist damit die Genesis (Hash wie im Konsens, rusty-kaspa
consensus/core/src/hashing/covenant_id.rs). Den Payload liefert der eigene
Knoten, wenn die Tx noch in seinem Fenster liegt, sonst api.kaspa.org; die
Tx-ID der Vorbereitung wird hier NICHT neu gerechnet (KCC-23 nennt das
optional). Deshalb traegt jede Zeile ihre Quelle. KCC-23 ist Draft.

Optional der Vergleich mit KRC-20 ueber die Kasplex-API, je gefundenem Symbol,
nur als "source kasplex". Ein Weg der Migration wird nicht geraten.

    python3 scripts/kcc20_namen.py --tokens kcc20-tokens.csv --bestand bestand.csv --tx tx.jsonl --tx api-tx.jsonl --out aus
    python3 scripts/kcc20_namen.py --selbsttest
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kcc20_api  # noqa: E402

KASPLEX = "https://api.kasplex.org/v1/krc20/token/"
VEKTOREN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kcc20", "vektoren",
                        "kcc-0023-conformance.json")


def covenant_id(txid, index, gruppe):
    """KIP-20, gruppe = [(ausgabe_index, sompi, spk_version, spk_hex)]."""
    h = hashlib.blake2b(digest_size=32, key=b"CovenantID")
    h.update(bytes.fromhex(txid))
    h.update(struct.pack("<IQ", index, len(gruppe)))
    for i, v, ver, spk in gruppe:
        s = bytes.fromhex(spk)
        h.update(struct.pack("<IQHQ", i, v, ver, len(s)) + s)
    return h.hexdigest()


def metadaten(payload_hex):
    """KCC-23 3.1, None wenn ungueltig."""
    try:
        b = bytes.fromhex(payload_hex or "")
        if len(b) < 2 or b[0] != 0:
            return None
        d = json.loads(b[1:].decode("utf-8"))
        return d if isinstance(d, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def schritt(t, cov):
    """('genesis', vorbereitung_txid) oder ('weiter', vorgaenger_txid) oder (None, None)."""
    gruppen = {}
    for i, o in enumerate(t["out"]):
        if o[3] == cov:
            gruppen.setdefault(o[4], []).append((i, int(o[0]), int(o[1]), o[2]))
    vor = None
    for auth, g in sorted(gruppen.items(), key=lambda x: (x[0] is None, x[0] or 0)):
        if auth is None or auth >= len(t["in"]):
            continue
        txid, idx = t["in"][auth][0].split(":")
        if covenant_id(txid, int(idx), g) == cov:
            return "genesis", txid
        vor = vor or txid
    return ("weiter", vor) if vor else (None, None)


def suchen(starts, eigen, abruf, budget=20000):
    """starts: {cov: erzeugende txid}. Gibt {cov: {...}} und die Zahl der api-Abrufe."""
    cache = dict(eigen)
    offen = dict(starts)
    aus = {c: {"status": "offen", "schritte": 0} for c in starts}
    geholt = 0
    while offen and geholt < budget:
        fehlt = {t for t in offen.values() if t not in cache}
        if fehlt:
            neu = kcc20_api.holen(fehlt, abruf)
            geholt += len(fehlt)
            cache.update(neu)
        weiter = {}
        for cov, txid in offen.items():
            t = cache.get(txid)
            if not t:
                aus[cov]["status"] = "tx nicht gefunden"
                continue
            art, nxt = schritt(t, cov)
            aus[cov]["schritte"] += 1
            if art == "genesis":
                aus[cov].update({"status": "genesis bewiesen", "genesis_tx": txid, "genesis_t": t.get("t"),
                                 "vorbereitung_tx": nxt, "genesis_payload": t.get("payload") or ""})
            elif art == "weiter":
                weiter[cov] = nxt
            else:
                aus[cov]["status"] = "keine kette"
        offen = weiter
    for cov in offen:
        aus[cov]["status"] = "budget erreicht"
    # vorbereitungen holen und lesen
    prep = {a["vorbereitung_tx"] for a in aus.values() if a.get("vorbereitung_tx")}
    fehlt = {p for p in prep if p not in cache}
    if fehlt:
        cache.update(kcc20_api.holen(fehlt, abruf))
        geholt += len(fehlt)
    for a in aus.values():
        p = a.get("vorbereitung_tx")
        if not p:
            continue
        t = cache.get(p)
        a["payload_quelle"] = (t or {}).get("quelle", "eigener knoten") if t else None
        a["metadaten"] = namen_aus((t or {}).get("payload", ""), a.get("genesis_payload", ""))
        a["vorbereitung_payload"] = payload_info((t or {}).get("payload", ""))
    return aus, geholt


NAMENSFELDER = ("name", "symbol", "ticker", "tick", "decimals", "dec")


def payload_info(payload_hex):
    """kurze Beschreibung eines Payloads ohne Inhalt ausser Namensfeldern:
    Laenge, erstes Byte, ob JSON (mit oder ohne 0x00 davor), Feldnamen und die
    Werte von name, symbol, ticker, tick, decimals, dec (kurz, ohne Links)."""
    try:
        b = bytes.fromhex(payload_hex or "")
    except ValueError:
        return "kein hex"
    if not b:
        return "leer"
    teile = ["%d byte" % len(b), "erstes %02x" % b[0]]
    for name, roh in (("json nach 00", b[1:] if b[0] == 0 else None), ("json ohne praefix", b)):
        if roh is None:
            continue
        try:
            d = json.loads(roh.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(d, dict):
            teile.append(name)
            teile.append("felder " + "/".join(sorted(d)[:10]))
            for k in NAMENSFELDER:
                v = d.get(k)
                if isinstance(v, (str, int)) and "://" not in str(v) and len(str(v)) <= 40:
                    teile.append("%s=%s" % (k, str(v).replace(",", " ").replace("\n", " ")))
            break
    return "; ".join(teile)


def json_payload(payload_hex):
    """JSON-Objekt aus einem Payload ohne Praefix (Launchpad-Format im Genesis), sonst None."""
    try:
        d = json.loads(bytes.fromhex(payload_hex or "").decode("utf-8"))
        return d if isinstance(d, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def kurz(v):
    return v.strip() if isinstance(v, str) and "://" not in v and 0 < len(v.strip()) <= 40 else None


def namen_aus(prep_payload, gen_payload):
    """Name, Symbol, Dezimalstellen mit Quelle. KCC-23 aus der Vorbereitung hat
    Vorrang, sonst JSON im Genesis-Payload. Hinweis auf den Weg nur, wenn die
    Metadaten ihn selbst nennen (z.B. bridge_covenant_id), sonst unbekannt."""
    md = metadaten(prep_payload)
    quelle = "kcc-23 vorbereitung" if md else None
    if not md:
        md = json_payload(gen_payload)
        quelle = "genesis-payload, kein kcc-23" if md else None
    md = md or {}
    sym = kurz(md.get("symbol")) or kurz(md.get("ticker"))
    dec = md.get("decimals") if isinstance(md.get("decimals"), int) else None
    bruecke = sorted(k for k in md if "bridge" in k.lower() or "vault" in k.lower())
    return {"symbol": sym, "name": kurz(md.get("name")), "decimals": dec, "namensquelle": quelle,
            "weg_hinweis": ("metadaten nennen " + "/".join(bruecke)) if bruecke else "unbekannt"}


def kasplex(symbol):
    import re
    if not re.fullmatch(r"[A-Za-z]{4,6}", symbol or ""):
        return {"krc20": "kein moeglicher krc20-ticker"}
    req = urllib.request.Request(KASPLEX + urllib.request.quote(symbol.upper()),
                                 headers={"User-Agent": kcc20_api.UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"krc20": "http %d" % exc.code}
    res = (d.get("result") or [{}])[0]
    if not res or res.get("state") in (None, "unused"):
        return {"krc20": "nicht gefunden"}
    return {"krc20": "gefunden", "krc20_max": res.get("max"), "krc20_minted": res.get("minted"),
            "krc20_dec": res.get("dec"), "krc20_holder": res.get("holderTotal"), "krc20_state": res.get("state")}


def laufen(tokens, bestand, tx_pfade, out, abruf=kcc20_api.hole, krc=True):
    eigen = {}
    for p in tx_pfade:
        if os.path.exists(p):
            for z in open(p, encoding="utf-8"):
                t = json.loads(z)
                t.setdefault("quelle", "eigener knoten")
                eigen[t["id"]] = t
    with open(tokens, encoding="utf-8") as fh:
        covs = [r["covenant_id"] for r in csv.DictReader(fh)]
    starts = {}
    with open(bestand, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["covenant_id"] in covs and r["covenant_id"] not in starts:
                starts[r["covenant_id"]] = r["outpoint"].split(":")[0]
    aus, geholt = suchen(starts, eigen, abruf)
    zeilen = []
    for cov in covs:
        a = aus.get(cov, {"status": "kein lebender output"})
        md = a.get("metadaten") or {}
        z = {"covenant_id": cov, "status": a["status"], "symbol": md.get("symbol"), "name": md.get("name"),
             "decimals": md.get("decimals"), "namensquelle": md.get("namensquelle"),
             "weg_hinweis": md.get("weg_hinweis"), "genesis_tx": a.get("genesis_tx"), "genesis_t": a.get("genesis_t"),
             "payload_quelle": a.get("payload_quelle"), "schritte": a.get("schritte"),
             "vorbereitung_payload": a.get("vorbereitung_payload"),
             "genesis_payload": payload_info(a["genesis_payload"]) if "genesis_payload" in a else None}
        if krc and isinstance(md.get("symbol"), str):
            try:
                z.update(kasplex(md["symbol"]))
            except Exception as exc:        # noqa: BLE001
                z["krc20"] = "abfrage gescheitert (%s)" % type(exc).__name__
            time.sleep(0.2)
        zeilen.append(z)
    os.makedirs(out, exist_ok=True)
    felder = sorted({k for z in zeilen for k in z}, key=lambda k: list(zeilen[0]).index(k) if zeilen and k in zeilen[0]
                    else 99)
    with open(os.path.join(out, "kcc20-namen.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=felder)
        w.writeheader()
        w.writerows(zeilen)
    zus = {"tokens": len(covs), "genesis_bewiesen": sum(1 for z in zeilen if z["status"] == "genesis bewiesen"),
           "mit_metadaten": sum(1 for z in zeilen if z["symbol"] or z["name"]),
           "namensquelle": dict(collections.Counter(z["namensquelle"] for z in zeilen)), "api_abrufe": geholt}
    print(json.dumps(zus))
    w = csv.DictWriter(sys.stdout, fieldnames=felder)
    w.writeheader()
    w.writerows(zeilen)
    return zeilen, zus


def diagnose(tokens, bestand, tx_pfade, vergleich=None, n=40):
    """Covenant-IDs mit lebenden UTXOs, die kein bewiesener KCC-20-Token sind:
    Anzahl UTXOs und KAS je ID, dazu die 4-Byte-Dispatch-Tags in den
    erzeugenden Tx. Mit --vergleich (kcc20.info token_ids, nur als source)
    wird markiert, welche IDs dort gefuehrt werden. Nur IDs und Summen."""

    from kcc20_zaehlung import kcc1_aufruf
    with open(tokens, encoding="utf-8") as fh:
        tok = {r["covenant_id"] for r in csv.DictReader(fh) if int(r.get("halter_outputs") or 0) > 0}
    je = collections.defaultdict(lambda: [0, 0, set()])
    with open(bestand, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = r["covenant_id"]
            if c and c not in tok:
                je[c][0] += 1
                je[c][1] += int(r["sompi"])
                je[c][2].add(r["outpoint"].split(":")[0])
    tags = collections.defaultdict(collections.Counter)
    gesucht = {t: c for c, v in je.items() for t in v[2]}
    for p in tx_pfade:
        if not os.path.exists(p):
            continue
        for z in open(p, encoding="utf-8"):
            t = json.loads(z)
            c = gesucht.get(t["id"])
            if not c:
                continue
            for _prev, sig in t["in"]:
                auf = kcc1_aufruf(bytes.fromhex(sig or ""))
                if auf:
                    tags[c][auf[1].hex()] += 1
    vg = set(vergleich or ())
    zeilen = sorted(je.items(), key=lambda kv: -kv[1][0])
    print(json.dumps({"diagnose": "covenant-ids ohne bewiesenen kcc20-token", "ids": len(je),
                      "utxos": sum(v[0] for v in je.values()),
                      "davon_bei_kcc20info": sum(1 for c in je if c in vg),
                      "tokens_bei_kcc20info_ohne_lebende_utxos_hier": len(vg - set(je) - tok)}))
    alle_tags = collections.Counter()
    for c in tags:
        alle_tags.update(tags[c])
    print(json.dumps({"dispatch_tags_in_erzeugenden_tx": alle_tags.most_common(15)}))
    for c, (k, sompi, _t) in zeilen[:n]:
        print("%s utxos %d kas %.2f kcc20info %s tags %s" % (c, k, sompi / 1e8, "ja" if c in vg else "nein",
                                                          ",".join("%s:%d" % x for x in tags[c].most_common(3))))


def payloads(pfad, abruf=kcc20_api.hole, krc=True):
    """Ohne Knoten: je Zeile covenant_id,genesis_tx (Genesis schon bewiesen) die
    Payloads von Genesis und Vorbereitung beschreiben, KCC-23 lesen, KRC-20 fragen."""
    paare = [z.strip().split(",")[:2] for z in open(pfad, encoding="utf-8") if re.match(r"^[0-9a-f]{64},[0-9a-f]{64}", z)]
    gen = kcc20_api.holen({g for _c, g in paare}, abruf)
    prep_von = {}
    for cov, g in paare:
        t = gen.get(g)
        if not t:
            continue
        auth = next((o[4] for o in t["out"] if o[3] == cov), None)
        if auth is not None and auth < len(t["in"]):
            prep_von[cov] = t["in"][auth][0].split(":")[0]
    prep = kcc20_api.holen(set(prep_von.values()), abruf)
    w = csv.writer(sys.stdout)
    w.writerow(["covenant_id", "symbol", "name", "decimals", "namensquelle", "weg_hinweis", "krc20", "krc20_max", "krc20_minted", "krc20_dec",
                "krc20_holder", "vorbereitung_payload", "genesis_payload"])
    for cov, g in paare:
        pt = prep.get(prep_von.get(cov), {})
        md = namen_aus(pt.get("payload", ""), (gen.get(g) or {}).get("payload", ""))
        k = {}
        if krc and isinstance(md.get("symbol"), str):
            try:
                k = kasplex(md["symbol"])
            except Exception as exc:                # noqa: BLE001
                k = {"krc20": "abfrage gescheitert (%s)" % type(exc).__name__}
            time.sleep(0.2)
        w.writerow([cov, md.get("symbol"), md.get("name"), md.get("decimals"), md.get("namensquelle"),
                    md.get("weg_hinweis"), k.get("krc20"), k.get("krc20_max"),
                    k.get("krc20_minted"), k.get("krc20_dec"), k.get("krc20_holder"),
                    payload_info(pt.get("payload", "")) if pt else "nicht geholt",
                    payload_info((gen.get(g) or {}).get("payload", ""))])
    return 0


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    v = json.load(open(VEKTOREN, encoding="utf-8"))
    b = v["binding"]
    g, p = b["genesis_transaction"], b["preparation_transaction"]
    soll = g["outputs"][0]["covenant"]["covenant_id"]
    ist = covenant_id(g["inputs"][0]["previous_outpoint"]["transaction_id"], 0,
                      [(0, g["outputs"][0]["value"], 0, g["outputs"][0]["script_public_key"]["script_hex"])])
    ok("kip-20 covenant id gegen kcc-23 vektor", ist == soll, ist)
    for d in v["declarations"]:
        ok("deklaration %s" % d["name"], (metadaten(d["payload_hex"]) is not None) == d["valid"])
    ok("metadaten des bindungsvektors", metadaten(p["payload_hex"]) == {"name": "Example Token", "symbol": "EXT",
                                                                       "decimals": 8})
    # kette: genesis g0 <- t1 <- t2 (t2 erzeugt den lebenden output), vorbereitung prep
    prep_id = g["inputs"][0]["previous_outpoint"]["transaction_id"]
    g0 = {"id": "aa" * 32, "t": 1, "in": [[prep_id + ":0", ""]],
          "out": [[90000000, 0, "51", soll, 0]], "payload": "", "quelle": "api.kaspa.org"}
    t1 = {"id": "bb" * 32, "t": 2, "in": [["aa" * 32 + ":0", "00"]], "out": [[5, 0, "51", soll, 0]], "payload": ""}
    t2 = {"id": "cc" * 32, "t": 3, "in": [["dd" * 32 + ":1", ""], ["bb" * 32 + ":0", "00"]],
          "out": [[1, 0, "51", None, None], [4, 0, "51", soll, 1]], "payload": ""}
    api = {g0["id"]: g0, prep_id: {"transaction_id": prep_id, "payload": p["payload_hex"], "inputs": [],
                                   "outputs": [], "block_time": 0}}
    rufe = []

    def abruf(pfad, daten):
        rufe.append(len(daten["transactionIds"]))
        r = []
        for i in daten["transactionIds"]:
            x = api.get(i)
            if x and "transaction_id" in x:
                r.append(x)
            elif x:
                r.append({"transaction_id": x["id"], "block_time": x["t"],
                          "inputs": [{"index": k, "previous_outpoint_hash": a.split(":")[0],
                                      "previous_outpoint_index": int(a.split(":")[1]), "signature_script": s}
                                     for k, (a, s) in enumerate(x["in"])],
                          "outputs": [{"index": k, "amount": o[0], "script_public_key": o[2], "covenant_id": o[3],
                                       "covenant_authorizing_input": o[4]} for k, o in enumerate(x["out"])],
                          "payload": x["payload"]})
        return r
    aus, geholt = suchen({soll: t2["id"]}, {t1["id"]: t1, t2["id"]: t2}, abruf)
    a = aus[soll]
    ok("genesis ueber zwei schritte gefunden", a["status"] == "genesis bewiesen" and a["genesis_tx"] == g0["id"]
       and a["schritte"] == 3, a)
    ok("metadaten aus der vorbereitung", (a.get("metadaten") or {}).get("symbol") == "EXT"
       and a["metadaten"]["namensquelle"] == "kcc-23 vorbereitung", a)
    gp = json.dumps({"name": "Frog", "ticker": "FROG", "image": "https://x"}).encode().hex()
    ok("genesis-payload als ersatz", namen_aus("", gp) == {"symbol": "FROG", "name": "Frog", "decimals": None,
       "namensquelle": "genesis-payload, kein kcc-23", "weg_hinweis": "unbekannt"}, namen_aus("", gp))
    bp = "00" + json.dumps({"symbol": "W", "decimals": 6, "bridge_covenant_id": "ab", "eth_vault": "x"}).encode().hex()
    ok("weg nur aus den metadaten", namen_aus(bp, "")["weg_hinweis"] == "metadaten nennen bridge_covenant_id/eth_vault")
    ok("zwei api-abrufe (genesis, vorbereitung)", rufe == [1, 1], rufe)
    ok("payload_info kcc23", payload_info(p["payload_hex"]).startswith("53 byte; erstes 00; json nach 00")
       and "symbol=EXT" in payload_info(p["payload_hex"]), payload_info(p["payload_hex"]))
    ok("payload_info ohne praefix, link weg", payload_info(json.dumps({"tick": "ABCD", "name": "https://x"}).encode().hex())
       .endswith("json ohne praefix; felder name/tick; tick=ABCD"), payload_info(json.dumps({"tick": "ABCD"}).encode().hex()))
    ok("kein krc20-ticker", kasplex("Wobbly.k") == {"krc20": "kein moeglicher krc20-ticker"})
    falsch = dict(g0, out=[[90000001, 0, "51", soll, 0]])
    ok("falscher wert in der genesis wird nicht genesis", schritt(falsch, soll) == ("weiter", prep_id))
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens")
    ap.add_argument("--bestand")
    ap.add_argument("--tx", action="append", default=[])
    ap.add_argument("--out", default="aus")
    ap.add_argument("--ohne-krc20", action="store_true")
    ap.add_argument("--payloads")
    ap.add_argument("--vergleich", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kcc20",
                                                       "vektoren", "kcc20info-token-ids.txt"))
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.payloads:
        return payloads(a.payloads, krc=not a.ohne_krc20)
    try:
        vg = []
        if a.vergleich and os.path.exists(a.vergleich):
            vg = [x.strip() for x in open(a.vergleich, encoding="utf-8") if x.strip()]
        diagnose(a.tokens, a.bestand, a.tx, vg)
    except Exception as exc:                        # noqa: BLE001
        print("diagnose gescheitert (%s)" % type(exc).__name__)
    laufen(a.tokens, a.bestand, a.tx, a.out, krc=not a.ohne_krc20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
