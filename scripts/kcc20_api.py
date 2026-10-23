#!/usr/bin/env python3
"""Kaspa Pulse, Transaktionen fuer die KCC-20-Zaehlung nachladen (Ben, 23.10.2026).

Der eigene Knoten haelt Transaktionen nur ab seinem Pruning-Punkt (rund 30 bis
42 Stunden). Fuer zwei Faelle kommen Transaktionen deshalb von api.kaspa.org:

  1. die erzeugende Tx eines lebenden Covenant-Outputs, die aelter ist als der
     Pruning-Punkt. Die Menge wird danach trotzdem per Blake2b-Hash gegen das
     Skript des Outputs bewiesen, die Quelle kann also nichts unterschieben.
  2. KCC-20-Transaktionen zwischen --seit und dem Pruning-Punkt, gefunden
     ueber die Vorfahren bekannter KCC-20-Transaktionen (Eingaenge rueckwaerts,
     solange die Tx nach --seit liegt). Grenze: eine Kette, die vor dem
     Pruning-Punkt endete (zum Beispiel ein Burn ohne Fortsetzung), wird so nicht
     gefunden. Diese Transaktionen tragen "quelle": "api.kaspa.org".

Ausgabe im Format von kp-stichzeit KP_TX=1 (eine JSON-Zeile je Tx). Druckt nur
Zahlen und Feldnamen, keine Adressen.

    python3 scripts/kcc20_api.py --bestand bestand.csv --tx tx.jsonl --seit 2026-10-21T00:00:00Z --out api-tx.jsonl
    python3 scripts/kcc20_api.py --probe
    python3 scripts/kcc20_api.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import tempfile
import time
import urllib.request

REST = "https://api.kaspa.org"
UA = "kaspa-pulse-kcc20 (+https://kaspapulse.com)"
BATCH = 50
TAGS = ("0479c71c23", "04fd3ef14a")


def hole(pfad, daten=None, versuche=4):
    url = REST + pfad
    letzter = None
    for i in range(versuche):
        try:
            body = json.dumps(daten).encode() if daten is not None else None
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA, "Accept": "application/json",
                **({"Content-Type": "application/json"} if body else {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                    # noqa: BLE001
            letzter = type(exc).__name__
            time.sleep(2 * (i + 1))
    raise RuntimeError("api.kaspa.org %s nicht erreichbar (%s)" % (pfad.split("?")[0], letzter))


def ms(text):
    return int(dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def normal(t):
    """api-Tx in das Zeilenformat von kp-stichzeit."""
    ein = []
    for x in sorted(t.get("inputs") or [], key=lambda x: int(x.get("index") or 0)):
        ein.append(["%s:%s" % (x.get("previous_outpoint_hash"), x.get("previous_outpoint_index")),
                    x.get("signature_script") or ""])
    aus = []
    for o in sorted(t.get("outputs") or [], key=lambda o: int(o.get("index") or 0)):
        spk = o.get("script_public_key") or ""
        ver = 0
        if len(spk) >= 4 and len(spk) % 2 == 0 and spk.startswith("0000"):
            ver, spk = 0, spk[4:]           # manche api-versionen stellen die version voran
        cov = o.get("covenant_id")
        auth = o.get("covenant_authorizing_input")
        aus.append([int(o.get("amount") or 0), ver, spk, cov or None, auth if cov else None])
    zeit = t.get("block_time") or t.get("accepting_block_time")
    return {"id": t.get("transaction_id"), "t": int(zeit) if zeit else None, "in": ein, "out": aus,
            "payload": t.get("payload") or "", "quelle": "api.kaspa.org"}


def relevant(t):
    return any(o[3] for o in t["out"]) or any(any(g in s for g in TAGS) for _p, s in t["in"])


def holen(ids, abruf):
    aus = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), BATCH):
        for t in abruf("/transactions/search?resolve_previous_outpoints=no",
                       {"transactionIds": ids[i:i + BATCH]}) or []:
            n = normal(t)
            if n["id"]:
                aus[n["id"]] = n
        time.sleep(0.2)
    return aus


def laufen(bestand, tx_pfade, seit_ms, out, abruf=hole, budget=40000):
    eigen = {}
    for p in tx_pfade:
        if os.path.exists(p):
            for z in open(p, encoding="utf-8"):
                t = json.loads(z)
                eigen[t["id"]] = t
    eigen_von = min((t["t"] for t in eigen.values() if t.get("t")), default=None)
    fehlt = set()
    with open(bestand, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["covenant_id"]:
                txid = r["outpoint"].split(":")[0]
                if txid not in eigen:
                    fehlt.add(txid)
    geholt = holen(fehlt, abruf)
    meta = {"lebend_erzeugende_tx_gesucht": len(fehlt), "lebend_erzeugende_tx_gefunden": len(geholt)}
    # vorfahren ab den fruehesten bekannten kcc20-tx, solange nach seit_ms
    bekannt = dict(geholt)
    rand = {t["id"] for t in list(eigen.values()) + list(geholt.values()) if relevant(t)}
    gesehen, runden = set(eigen) | set(geholt), 0
    while rand and len(bekannt) < budget:
        runden += 1
        eltern = set()
        for txid in rand:
            t = eigen.get(txid) or bekannt.get(txid)
            if not t or not t.get("t") or t["t"] < seit_ms:
                continue
            for p, s in t["in"]:
                ptx = p.split(":")[0]
                if ptx not in gesehen and (any(g in s for g in TAGS) or len(s) > 400):
                    eltern.add(ptx)
        if not eltern:
            break
        neu = holen(eltern, abruf)
        gesehen |= eltern
        rand = set()
        for txid, t in neu.items():
            if relevant(t) and t.get("t") and t["t"] >= seit_ms:
                bekannt[txid] = t
                rand.add(txid)
    meta.update({"vorfahren_runden": runden, "api_tx": len(bekannt), "eigen_tx": len(eigen),
                 "eigen_ab_utc": dt.datetime.fromtimestamp(eigen_von / 1000, dt.timezone.utc).isoformat()
                 if eigen_von else None, "budget_erreicht": len(bekannt) >= budget})
    with open(out, "w", encoding="utf-8") as fh:
        for t in sorted(bekannt.values(), key=lambda x: (x.get("t") or 0, x["id"])):
            fh.write(json.dumps(t) + "\n")
    print(json.dumps(meta))
    return meta


def probe():
    """Feldnamen und Erreichbarkeit, nur Schluessel und Zahlen im Log."""
    aus = {}
    try:
        info = hole("/info/blockdag", versuche=2)
        aus["blockdag_felder"] = sorted(info)[:20]
        tip = (info.get("tipHashes") or [None])[0]
        b = hole("/blocks/%s?includeTransactions=true" % tip, versuche=2) if tip else {}
        txs = b.get("transactions") or []
        if txs:
            tid = (txs[-1].get("verboseData") or {}).get("transactionId")
            t = hole("/transactions/search?resolve_previous_outpoints=no", {"transactionIds": [tid]})[0]
            aus["tx_felder"] = sorted(t)
            aus["input_felder"] = sorted((t.get("inputs") or [{}])[0])
            aus["output_felder"] = sorted((t.get("outputs") or [{}])[0])
    except Exception as exc:                        # noqa: BLE001
        aus["api_fehler"] = str(exc)[:200]
    for name, url in (("kcc20_info", "https://kcc20.info/"), ("kasplex", "https://api.kasplex.org/v1/info")):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            aus[name] = {"http": 200, "bytes": len(body), "typ": r.headers.get("Content-Type", "")[:40]}
        except Exception as exc:                    # noqa: BLE001
            aus[name] = {"fehler": type(exc).__name__}
    print(json.dumps(aus, indent=1))
    return 0


def seite_text(html):
    """sichtbarer Text einer HTML-Seite, ohne Skripte und Stile, Leerraum zusammengefasst."""
    import re
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    links = sorted(set(re.findall(r'(?i)(?:href|src)="(/[^"#?]*|[^"]*\.json)"', html)))
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#x27;", "'"), ("&quot;", '"')):
        text = text.replace(a, b)
    zeilen = [" ".join(z.split()) for z in text.split("\n")]
    return [z for z in zeilen if z], links


def kcc20info(url="https://kcc20.info/"):
    """Zahlen von kcc20.info, nur als 'source kcc20.info'. Druckt Textzeilen mit
    Ziffern oder Stichwoertern und die Pfade der Seite (fuer eine moegliche API)."""
    import re
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    zeilen, links = seite_text(html)
    wort = re.compile(r"(?i)token|utxo|covenant|holder|transfer|mint|supply|kcc|krc|stand|updated|as of")
    treffer = [z for z in zeilen if (re.search(r"\d", z) or wort.search(z)) and len(z) <= 160]
    print(json.dumps({"quelle": "source kcc20.info", "url": url, "zeilen": treffer[:150],
                      "pfade": [l for l in links if not re.search(r"\.(css|png|svg|ico|woff2?|jpg|webp)$", l)][:80]},
                     indent=1, ensure_ascii=False))
    return 0


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    seit = ms("2026-10-21T00:00:00Z")
    tag_sig = "aa" + TAGS[0] + "bb"

    def api_tx(tid, t, eltern, cov=True):
        return {"transaction_id": tid, "block_time": t,
                "inputs": [{"index": i, "previous_outpoint_hash": p, "previous_outpoint_index": 0,
                            "signature_script": tag_sig} for i, p in enumerate(eltern)],
                "outputs": [{"index": 0, "amount": 100, "script_public_key": "aa20" + "11" * 32 + "87",
                             "covenant_id": "c0" * 32 if cov else None, "covenant_authorizing_input": 0}]}
    kette = {"t3": api_tx("t3", seit + 3000, ["t2"]), "t2": api_tx("t2", seit + 2000, ["t1"]),
             "t1": api_tx("t1", seit - 1000, ["t0"]), "t0": api_tx("t0", seit - 2000, [])}
    rufe = []

    def abruf(pfad, daten):
        rufe.append(len(daten["transactionIds"]))
        return [kette[i] for i in daten["transactionIds"] if i in kette]
    with tempfile.TemporaryDirectory() as d:
        bp, tp, op = os.path.join(d, "b.csv"), os.path.join(d, "tx.jsonl"), os.path.join(d, "api.jsonl")
        with open(bp, "w", encoding="utf-8") as fh:
            fh.write("outpoint,sompi,block_daa_score,is_coinbase,covenant_id,klasse,adresse,spk_version,spk_hex\n")
            fh.write("t3:0,100,1,false,%s,p2sh,,0,aa\n" % ("c0" * 32))
        open(tp, "w").close()
        meta = laufen(bp, [tp], seit, op, abruf=abruf)
        ids = [json.loads(z)["id"] for z in open(op, encoding="utf-8")]
    ok("erzeugende tx geholt, vorfahren bis vor seit verfolgt, t1 nicht mehr behalten", ids == ["t2", "t3"], ids)
    ok("t0 nicht mehr geholt (t1 liegt vor seit)", meta["lebend_erzeugende_tx_gefunden"] == 1 and len(rufe) == 3, rufe)
    n = normal(kette["t3"])
    ok("normalform wie kp-stichzeit", n["in"][0] == ["t2:0", tag_sig] and n["out"][0][3] == "c0" * 32
       and n["out"][0][2] == "aa20" + "11" * 32 + "87", n)
    z, l = seite_text('<html><style>x{}</style><a href="/api/tokens">97</a><p>KCC20 Tokens</p><script>1</script></html>')
    ok("seitentext ohne skript und stil, pfade", z == ["97", "KCC20 Tokens"] and l == ["/api/tokens"], (z, l))
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bestand")
    ap.add_argument("--tx", action="append", default=[])
    ap.add_argument("--seit", default="2026-10-21T00:00:00Z")
    ap.add_argument("--out", default="api-tx.jsonl")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--kcc20info", nargs="?", const="https://kcc20.info/")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.probe:
        return probe()
    if a.kcc20info:
        return kcc20info(a.kcc20info)
    laufen(a.bestand, a.tx, ms(a.seit), a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
