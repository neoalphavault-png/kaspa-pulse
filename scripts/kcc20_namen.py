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
import csv
import hashlib
import json
import os
import struct
import sys
import time
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
                                 "vorbereitung_tx": nxt})
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
        md = metadaten((t or {}).get("payload", ""))
        a["metadaten"] = md
    return aus, geholt


def kasplex(symbol):
    req = urllib.request.Request(KASPLEX + urllib.request.quote(symbol.upper()),
                                 headers={"User-Agent": kcc20_api.UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
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
             "decimals": md.get("decimals"), "genesis_tx": a.get("genesis_tx"), "genesis_t": a.get("genesis_t"),
             "payload_quelle": a.get("payload_quelle"), "schritte": a.get("schritte")}
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
           "mit_metadaten": sum(1 for z in zeilen if z["symbol"] or z["name"]), "api_abrufe": geholt}
    print(json.dumps(zus))
    w = csv.DictWriter(sys.stdout, fieldnames=felder)
    w.writeheader()
    w.writerows(zeilen)
    return zeilen, zus


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
    ok("metadaten aus der vorbereitung", (a.get("metadaten") or {}).get("symbol") == "EXT", a)
    ok("zwei api-abrufe (genesis, vorbereitung)", rufe == [1, 1], rufe)
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
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    laufen(a.tokens, a.bestand, a.tx, a.out, krc=not a.ohne_krc20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
