#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""alexandria_anker.py, ein Alexandria-Anker auf Testnet-10 unabhaengig pruefen (Ben, 02.11.2026).

Liest eine Tx ueber einen Knoten, nur lesend, und schreibt Rohdaten und
Pruefung als JSON. Zwei Prozesse, k1 und k2, auf zwei verschiedenen Knoten
(wie bei der STP-Zaehlung, k2 meidet den Knoten von k1).

Je Knoten
    1. annehmender Block laut Team: Kopf, Kettenblock ja/nein, Mergeset
    2. die Tx in den Bloecken des Mergesets suchen, enthaltende Bloecke
    3. Annahme ueber get_virtual_chain_from_block ab dem Selected Parent
    4. Payload byte-genau, Laenge, Text, gleich dem erwarteten
    5. Eingang: vorherige Tx suchen, erst im Mergeset, dann vorwaerts ab
       SUCHE_H Stunden vor dem Block. Gefunden: Betrag des Outputs, Summe der
       Ausgaenge, Gebuehr nachgerechnet. Nicht gefunden: steht so im JSON.

Ins Log geht nur, was keine Adresse und kein Script ist: ja/nein, Zeiten,
DAA-Score, Betraege, Laengen. Die Rohdaten (mit Scripts der Ausgaenge) gehen
nur ins JSON, das der Workflow auf den Messbranch legt.

    python3 scripts/alexandria_anker.py --anker messung/alexandria/anker.txt --rolle k1 --partner P --out out/k1
    python3 scripts/alexandria_anker.py --archiv URL [URL ...] --out out/archiv
    python3 scripts/alexandria_anker.py --selbsttest
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tn10_zaehler import Takt, feld, iso_ms, zahl  # noqa: E402
import tn10_nachzaehlung as nz  # noqa: E402

SUCHE_H = 6
nz.MAX_ABFRAGEN = 9000      # die suche nach dem eingang braucht mehr als eine zaehlung
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def anker_lesen(text):
    """tx, block, payload (erwartet), optional eingang_sompi, ausgaenge_sompi,
    gebuehr_sompi, annahme_utc; je Zeile key=wert."""
    w = {}
    for z in text.splitlines():
        z = z.strip()
        if z and not z.startswith("#") and "=" in z:
            k, v = z.split("=", 1)
            w[k.strip()] = v.strip()
    for k in ("tx", "block"):
        if not HEX64.match(w.get(k, "").lower()):
            raise ValueError("%s ist nicht 64 hex-zeichen" % k)
        w[k] = w[k].lower()
    return w


def payload_bytes(p):
    """Payload aus dem Knoten als Bytes: Hex-Text oder Liste von Zahlen."""
    if p is None:
        return b""
    if isinstance(p, (bytes, bytearray)):
        return bytes(p)
    if isinstance(p, (list, tuple)):
        return bytes(int(x) for x in p)
    s = str(p).strip()
    if s.startswith("0x"):
        s = s[2:]
    return bytes.fromhex(s) if re.fullmatch(r"(?:[0-9a-fA-F]{2})*", s) else s.encode()


def tx_id(tx):
    return (feld(feld(tx, "verboseData") or {}, "transactionId") or "").lower()


def rein(x):
    """Objekt aus dem SDK in reines JSON."""
    if isinstance(x, dict):
        return {str(k): rein(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rein(v) for v in x]
    if isinstance(x, (bytes, bytearray)):
        return x.hex()
    if isinstance(x, (int, float, str, bool)) or x is None:
        return x
    if hasattr(x, "to_dict"):
        return rein(x.to_dict())
    if hasattr(x, "__dict__"):
        return rein(vars(x))
    return str(x)


ADRESSFELDER = ("scriptPublicKeyAddress", "scriptPublicKey", "address", "scriptPublicKeyAddresses")
ADRESSE = re.compile(r"kaspa(?:test|dev|sim)?:[a-z0-9]{20,}")


def ersatz(wert):
    """Laenge und sha256 statt eines Adressfelds (Ben, 03.11.2026)."""
    s = wert if isinstance(wert, str) else json.dumps(wert, sort_keys=True)
    return {"laenge": len(s), "sha256": hashlib.sha256(s.encode()).hexdigest()}


def ohne_adressen(x):
    """Kopie ohne Adressen: Adressfelder werden Laenge und sha256, Adressen in
    anderen Texten ebenso."""
    if isinstance(x, dict):
        return {k: (ersatz(v) if k in ADRESSFELDER and v not in (None, "") else ohne_adressen(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [ohne_adressen(v) for v in x]
    if isinstance(x, str) and ADRESSE.search(x):
        return ADRESSE.sub(lambda m: "[adresse sha256 %s]" % hashlib.sha256(m.group(0).encode()).hexdigest(), x)
    return x


def kopf(b):
    blk = feld(b, "block") or b
    h, v = feld(blk, "header") or {}, feld(blk, "verboseData") or {}
    return blk, {"hash": (feld(v, "hash") or feld(h, "hash") or "").lower(),
                 "zeit_ms": zahl(feld(h, "timestamp")), "daa_score": zahl(feld(h, "daaScore")),
                 "blue_score": zahl(feld(h, "blueScore")), "kettenblock": feld(v, "isChainBlock"),
                 "selected_parent": (feld(v, "selectedParentHash") or "").lower(),
                 "mergeset_blau": [x.lower() for x in feld(v, "mergeSetBluesHashes") or []],
                 "mergeset_rot": [x.lower() for x in feld(v, "mergeSetRedsHashes") or []]}


def betraege(tx, vorher):
    """Summe der Ausgaenge, Eingaenge aus den gefundenen vorherigen Outputs,
    Gebuehr. vorher: {"txid:index": amount}."""
    aus = sum(zahl(feld(o, "value", "amount")) or 0 for o in feld(tx, "outputs") or [])
    ein, fehlt = 0, []
    for e in feld(tx, "inputs") or []:
        po = feld(e, "previousOutpoint") or {}
        k = "%s:%s" % ((feld(po, "transactionId") or "").lower(), feld(po, "index"))
        if k in vorher:
            ein += vorher[k]
        else:
            fehlt.append(k)
    return {"ausgaenge_sompi": aus, "eingaenge_sompi": ein if not fehlt else None,
            "gebuehr_sompi": ein - aus if not fehlt else None, "eingaenge_fehlen": len(fehlt),
            "zahl_eingaenge": len(feld(tx, "inputs") or []), "zahl_ausgaenge": len(feld(tx, "outputs") or [])}


def vorher_aus(txs, gesucht):
    """{"txid:index": amount} fuer gesuchte vorherige Tx in einer Tx-Liste."""
    aus = {}
    for t in txs:
        i = tx_id(t)
        if i in gesucht:
            for n, o in enumerate(feld(t, "outputs") or []):
                aus["%s:%d" % (i, n)] = zahl(feld(o, "value", "amount")) or 0
    return aus


def payload_pruefen(pb, erwartet):
    try:
        text = pb.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return {"payload_hex": pb.hex(), "payload_laenge": len(pb), "payload_text": text,
            "payload_sha256": hashlib.sha256(pb).hexdigest(),
            "erwartet_laenge": len(erwartet.encode()) if erwartet else None,
            "gleich_erwartet": (pb == erwartet.encode()) if erwartet else None}


async def pruefen(les, a, suche_h=SUCHE_H):
    txid, block = a["tx"], a["block"]
    erg = {"tx_gefunden": False, "meldungen": []}
    dag = await les.rufe("get_block_dag_info")
    pp = feld(dag, "pruningPointHash")
    erg["pruning_punkt_utc"] = iso_ms(await les.ts(pp)) if pp else ""
    erg["virtual_daa_score"] = zahl(feld(dag, "virtualDaaScore"))
    roh_ab, k = kopf(await les.rufe("get_block", {"hash": block, "includeTransactions": True}))
    erg["annehmender_block"] = dict(k, gleich_angabe=k["hash"] == block)
    erg["annehmender_block"]["zeit_utc"] = iso_ms(k["zeit_ms"]) if k["zeit_ms"] else ""
    # tx in den bloecken des mergesets (der annehmende block selbst gehoert dazu)
    enthaltend, tx, alle_tx = [], None, []
    for h in [block] + k["mergeset_blau"] + k["mergeset_rot"]:
        blk = roh_ab if h == block else feld(await les.rufe("get_block", {"hash": h, "includeTransactions": True}),
                                                "block")
        blk = blk or {}
        _, kh = kopf(blk)
        txs = feld(blk, "transactions") or []
        alle_tx += txs
        for t in txs:
            if tx_id(t) == txid:
                tx = tx or t
                enthaltend.append({"hash": h, "zeit_ms": kh["zeit_ms"], "zeit_utc": iso_ms(kh["zeit_ms"]) if kh["zeit_ms"] else "",
                                   "daa_score": kh["daa_score"], "blau": h in k["mergeset_blau"] or h == block})
    erg["enthaltende_bloecke"] = enthaltend
    if tx is None:
        erg["meldungen"].append("tx in keinem block des mergesets")
        return erg, None
    erg["tx_gefunden"] = True
    erg["tx_id_gleich_angabe"] = tx_id(tx) == txid
    erg["masse"] = zahl(feld(feld(tx, "verboseData") or {}, "computeMass"))
    # annahme: kette ab dem selected parent des annehmenden blocks
    r = await les.rufe("get_virtual_chain_from_block",
                       {"startHash": k["selected_parent"], "includeAcceptedTransactionIds": True,
                        "minConfirmationCount": None})
    acc = {(feld(e, "acceptingBlockHash") or "").lower(): [x.lower() for x in feld(e, "acceptedTransactionIds") or []]
           for e in feld(r, "acceptedTransactionIds") or []}
    erg["annahme"] = {"erster_kettenblock_ist_angabe": ((feld(r, "addedChainBlockHashes") or [""])[0] or "").lower() == block,
                      "annehmender_block_gelesen": block in acc,
                      "tx_angenommen_in_angabe": txid in acc.get(block, []),
                      "anderer_annehmender_block": sorted(h for h, ids in acc.items() if txid in ids and h != block)}
    erg.update(payload_pruefen(payload_bytes(feld(tx, "payload")), a.get("payload", "")))
    # eingang: vorherige tx erst im mergeset, dann vorwaerts gesucht
    gesucht = {(feld(feld(e, "previousOutpoint") or {}, "transactionId") or "").lower() for e in feld(tx, "inputs") or []}
    vorher = vorher_aus(alle_tx, gesucht)
    weg = "mergeset" if vorher else ""
    if not vorher and enthaltend:
        t_ms = min(e["zeit_ms"] for e in enthaltend if e["zeit_ms"])
        try:
            s0 = await nz.start_finden(les, pp, t_ms - suche_h * 3600000)
            low, gesehen = s0, set()
            while not vorher:
                rb = await les.rufe("get_blocks", {"lowHash": low, "includeBlocks": True, "includeTransactions": True})
                bl, hs = feld(rb, "blocks") or [], feld(rb, "blockHashes") or []
                neu, spaet = 0, 0
                for b in bl:
                    _, kb = kopf(b)
                    if kb["hash"] in gesehen:
                        continue
                    gesehen.add(kb["hash"])
                    neu += 1
                    spaet = max(spaet, kb["zeit_ms"] or 0)
                    vorher.update(vorher_aus(feld(b, "transactions") or [], gesucht))
                if vorher:
                    weg = "vorwaerts ab %d h vor dem block" % suche_h
                if not neu or not hs or spaet > t_ms + 60000:
                    break
                low = hs[-1]
            erg["suche_bloecke"] = len(gesehen)
        except Exception as exc:  # noqa: BLE001
            erg["meldungen"].append("suche nach dem eingang: %s" % type(exc).__name__)
    erg["eingang_quelle"] = weg or "nicht gefunden, %d h vor dem block nicht mehr lesbar oder aelter" % suche_h
    erg.update(betraege(tx, vorher))
    return erg, {"tx": rein(tx), "annehmender_block_kopf": rein(feld(roh_ab, "header")),
                 "vorherige_outputs": vorher}


def zusammenfassung(rolle, meta, erg):
    """Zeilen fuer das Log: keine Adresse, kein Script, keine Hashes ausser
    ja/nein."""
    a = erg.get("annehmender_block", {})
    z = ["%s kennung %s version %s gleich wie partner %s pruning-punkt %s" % (
        rolle, meta.get("kennung", ""), meta.get("version", ""), meta.get("gleich_wie_partner", ""),
        erg.get("pruning_punkt_utc", ""))]
    z.append("annehmender block gelesen %s, kettenblock %s, zeit %s, daa %s, mergeset %d blau %d rot" % (
        a.get("gleich_angabe"), a.get("kettenblock"), a.get("zeit_utc"), a.get("daa_score"),
        len(a.get("mergeset_blau", [])), len(a.get("mergeset_rot", []))))
    z.append("tx gefunden %s, in %d bloecken: %s" % (erg.get("tx_gefunden"), len(erg.get("enthaltende_bloecke", [])),
             "; ".join("%s daa %s blau %s" % (e["zeit_utc"], e["daa_score"], e["blau"]) for e in erg.get("enthaltende_bloecke", []))))
    an = erg.get("annahme", {})
    z.append("annahme im angegebenen block %s, erster kettenblock nach selected parent ist angabe %s, andere %d" % (
        an.get("tx_angenommen_in_angabe"), an.get("erster_kettenblock_ist_angabe"), len(an.get("anderer_annehmender_block", []))))
    z.append("payload laenge %s, gleich erwartet %s, text %s" % (erg.get("payload_laenge"), erg.get("gleich_erwartet"),
                                                                json.dumps(erg.get("payload_text"))))
    z.append("eingaenge %s, ausgaenge %s, eingang %s sompi, ausgaenge %s sompi, gebuehr %s sompi, masse %s, quelle %s" % (
        erg.get("zahl_eingaenge"), erg.get("zahl_ausgaenge"), erg.get("eingaenge_sompi"), erg.get("ausgaenge_sompi"),
        erg.get("gebuehr_sompi"), erg.get("masse"), erg.get("eingang_quelle")))
    if erg.get("meldungen"):
        z.append("meldungen: " + "; ".join(erg["meldungen"]))
    return z


async def knoten_lauf(anker, rolle, partner, out, suche_h):
    a = anker_lesen(open(anker, encoding="utf-8").read())
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    rpc, takt, meta = await nz.verbinden(rolle, partner)
    try:
        les = nz.Leser(rpc, takt)
        try:
            erg, roh = await pruefen(les, a, suche_h)
        except Exception as exc:  # noqa: BLE001
            erg, roh = {"meldungen": ["fehler, %s" % type(exc).__name__]}, None
        erg["abfragen"] = les.abfragen
    finally:
        try:
            await rpc.disconnect()
        except Exception:  # noqa: BLE001
            pass
    erg["knoten"] = meta
    erg["gelesen_utc"] = iso_ms(int(time.time() * 1000))
    with open(out + ".json", "w", encoding="utf-8") as fh:
        json.dump(ohne_adressen({"pruefung": erg, "roh": roh}), fh, ensure_ascii=False, indent=1, sort_keys=True)
    for z in zusammenfassung(rolle, meta, erg):
        print(z)
    return 0 if erg.get("tx_gefunden") else 1


async def eingang_suchen(les, gesucht, von_ms, bis_ms):
    """Vorherige Tx vorwaerts suchen, von von_ms bis bis_ms (Blockzeit)."""
    erg = {"von_utc": iso_ms(von_ms), "bis_utc": iso_ms(bis_ms), "gefunden": [], "meldungen": []}
    dag = await les.rufe("get_block_dag_info")
    pp = feld(dag, "pruningPointHash")
    pp_ts = await les.ts(pp) if pp else None
    erg["pruning_punkt_utc"] = iso_ms(pp_ts) if pp_ts else ""
    if pp_ts is None or pp_ts > von_ms:
        erg["meldungen"].append("pruning-punkt liegt nach dem anfang, gesucht ab dem pruning-punkt")
        s0 = pp
    else:
        s0 = await nz.start_finden(les, pp, von_ms)
    low, gesehen, spaet_max = s0, set(), 0
    while True:
        rb = await les.rufe("get_blocks", {"lowHash": low, "includeBlocks": True, "includeTransactions": True})
        bl, hs = feld(rb, "blocks") or [], feld(rb, "blockHashes") or []
        neu, spaet = 0, 0
        for b in bl:
            _, kb = kopf(b)
            if kb["hash"] in gesehen:
                continue
            gesehen.add(kb["hash"])
            neu += 1
            spaet = max(spaet, kb["zeit_ms"] or 0)
            for t in feld(b, "transactions") or []:
                if tx_id(t) in gesucht:
                    erg["gefunden"].append({"tx": tx_id(t), "block": kb["hash"], "zeit_utc": iso_ms(kb["zeit_ms"]),
                                            "daa_score": kb["daa_score"],
                                            "outputs_sompi": [zahl(feld(o, "value", "amount")) for o in feld(t, "outputs") or []],
                                            "roh": rein(t)})
        spaet_max = max(spaet_max, spaet)
        if erg["gefunden"] or not neu or not hs or spaet > bis_ms:
            break
        low = hs[-1]
    erg["bloecke"], erg["gelesen_bis_utc"] = len(gesehen), iso_ms(spaet_max) if spaet_max else ""
    erg["lueckenlos_bis_ende"] = bool(erg["gefunden"]) or spaet_max > bis_ms
    return erg


async def block_lesen(les, h, gesucht):
    """Einen Block direkt lesen und die gesuchten Tx darin."""
    b, k = kopf(await les.rufe("get_block", {"hash": h, "includeTransactions": True}))
    aus = [{"tx": tx_id(t), "outputs_sompi": [zahl(feld(o, "value", "amount")) for o in feld(t, "outputs") or []]}
           for t in feld(b, "transactions") or [] if tx_id(t) in gesucht]
    return {"block": k["hash"], "zeit_utc": iso_ms(k["zeit_ms"]) if k["zeit_ms"] else "", "daa_score": k["daa_score"],
            "kettenblock": k["kettenblock"], "gefunden": aus}


async def such_lauf(rolle, partner, out, gesucht, von_ms=None, bis_ms=None, block=None):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    rpc, takt, meta = await nz.verbinden(rolle, partner)
    try:
        les = nz.Leser(rpc, takt)
        try:
            erg = await (block_lesen(les, block, gesucht) if block else eingang_suchen(les, gesucht, von_ms, bis_ms))
        except Exception as exc:  # noqa: BLE001
            erg = {"meldungen": ["fehler, %s" % type(exc).__name__], "gefunden": []}
        erg["abfragen"] = les.abfragen
    finally:
        try:
            await rpc.disconnect()
        except Exception:  # noqa: BLE001
            pass
    erg["knoten"], erg["gelesen_utc"] = meta, iso_ms(int(time.time() * 1000))
    with open(out + ".json", "w", encoding="utf-8") as fh:
        json.dump(ohne_adressen(erg), fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("%s kennung %s, %s bis %s, bloecke %s, gelesen bis %s, lueckenlos %s, gefunden %d, outputs %s, block-zeit %s, meldungen %s" % (
        rolle, meta.get("kennung", ""), erg.get("von_utc", ""), erg.get("bis_utc", ""), erg.get("bloecke", ""),
        erg.get("gelesen_bis_utc", ""), erg.get("lueckenlos_bis_ende", ""), len(erg.get("gefunden", [])),
        [g.get("outputs_sompi") for g in erg.get("gefunden", [])], [g.get("zeit_utc", erg.get("zeit_utc", "")) for g in erg.get("gefunden", [])],
        "; ".join(erg.get("meldungen", []))))
    return 0


# archiv: nur die ausdruecklich genannten urls, byte-genau, keine link-verfolgung
# (Ben, 03.11.2026: der erste lauf folgte links und holte die ganze api)


def holen(url, limit=20 * 1024 * 1024):
    req = urllib.request.Request(url, headers={"User-Agent": "kaspa-pulse-pruefung/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read(limit)


def archiv(urls, out, hole=holen):
    """Holt genau die genannten urls, sonst nichts."""
    os.makedirs(out, exist_ok=True)
    liste = []
    for u in dict.fromkeys(urls):
        try:
            st, ct, daten = hole(u)
        except Exception as exc:  # noqa: BLE001
            liste.append({"url": u, "fehler": type(exc).__name__ + " " + str(exc)[:120]})
            continue
        name = "%03d" % len(liste)
        with open(os.path.join(out, name + ".bin"), "wb") as fh:
            fh.write(daten)
        liste.append({"url": u, "status": st, "typ": ct, "bytes": len(daten), "datei": name + ".bin",
                      "sha256": hashlib.sha256(daten).hexdigest()})
    with open(os.path.join(out, "liste.json"), "w", encoding="utf-8") as fh:
        json.dump(liste, fh, indent=1)
    for e in liste:
        print("%s %s %s %s %s" % (e.get("status", "-"), e.get("bytes", "-"), e.get("sha256", e.get("fehler", "")),
                                  e.get("typ", ""), e["url"]))
    return liste


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)
    erw = "ALX-KASPA-1|study|52|" + "4f" * 32
    ok("erwarteter payload hat 85 byte", len(erw.encode()) == 85)
    pb = payload_bytes(erw.encode().hex())
    p = payload_pruefen(pb, erw)
    ok("payload aus hex byte-genau", p["gleich_erwartet"] and p["payload_laenge"] == 85 and p["payload_text"] == erw)
    ok("payload aus zahlenliste", payload_bytes(list(erw.encode())) == erw.encode())
    ok("anderer payload ungleich", not payload_pruefen(pb[:-1] + b"0", erw)["gleich_erwartet"])
    tx = {"inputs": [{"previousOutpoint": {"transactionId": "AA" * 32, "index": 1}}],
          "outputs": [{"value": 99000000}, {"value": 779400}], "verboseData": {"transactionId": "bb" * 32}}
    vor = {"transactions": [{"verboseData": {"transactionId": "aa" * 32}, "outputs": [{"amount": 5}, {"amount": 100000000}]}]}
    v = vorher_aus(vor["transactions"], {"aa" * 32})
    b = betraege(tx, v)
    ok("gebuehr aus vorherigem output", b["eingaenge_sompi"] == 100000000 and b["ausgaenge_sompi"] == 99779400
       and b["gebuehr_sompi"] == 220600)
    ok("ohne vorherigen output keine gebuehr", betraege(tx, {})["gebuehr_sompi"] is None)
    try:
        anker_lesen("tx=zz\nblock=" + "a" * 64)
        ok("falsche tx-id abgelehnt", False)
    except ValueError:
        ok("falsche tx-id abgelehnt", True)
    zus = "\n".join(zusammenfassung("k1", {"kennung": "abcdefghij"}, {"tx_gefunden": True, "payload_text": erw,
                                                                      "enthaltende_bloecke": []}))
    ok("log ohne script", "script" not in zus.lower() or "kein script" in zus.lower())
    adr = "kaspatest:" + "q" * 61
    roh = {"tx": {"outputs": [{"value": 1, "scriptPublicKey": "20" + "ab" * 32 + "ac",
                               "verboseData": {"scriptPublicKeyAddress": adr, "scriptPublicKeyType": "PubKey"}}],
                  "payload": "414c58"}, "notiz": "an " + adr}
    sauber = json.dumps(ohne_adressen(roh))
    ok("keine adresse und kein script im gespeicherten json", adr not in sauber and "ab" * 32 not in sauber)
    ok("adressfeld wird laenge und sha256", ohne_adressen(roh)["tx"]["outputs"][0]["verboseData"]["scriptPublicKeyAddress"]
       == {"laenge": len(adr), "sha256": hashlib.sha256(adr.encode()).hexdigest()})
    ok("betrag, typ und payload bleiben", '"value": 1' in sauber and "PubKey" in sauber and "414c58" in sauber)
    geholt = []

    def hole(u):
        geholt.append(u)
        return 200, "text/html", b'<a href="/api/studies">x</a><script src="/assets/a.js"></script>'
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        archiv(["https://beispiel.invalid/study/52", "https://beispiel.invalid/api/studies/52"], d, hole=hole)
        ok("archiv holt nur die genannten urls, folgt keinem link",
           geholt == ["https://beispiel.invalid/study/52", "https://beispiel.invalid/api/studies/52"]
           and sorted(os.listdir(d)) == ["000.bin", "001.bin", "liste.json"])
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--anker")
    ap.add_argument("--rolle", choices=["k1", "k2"])
    ap.add_argument("--partner", default="")
    ap.add_argument("--suche-h", type=int, default=SUCHE_H)
    ap.add_argument("--archiv", nargs="*", default=[], help="genau diese urls, keine link-verfolgung")
    ap.add_argument("--out", default="out/anker")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--gesucht", default="", help="vorherige tx-ids, kommagetrennt")
    ap.add_argument("--von")
    ap.add_argument("--bis")
    ap.add_argument("--block", default="")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.gesucht:
        g = {x.strip().lower() for x in a.gesucht.split(",") if HEX64.match(x.strip().lower())}
        return asyncio.run(such_lauf(a.rolle, a.partner, a.out, g, nz.utc_ms(a.von) if a.von else None,
                                     nz.utc_ms(a.bis) if a.bis else None, a.block.lower() or None))
    if a.archiv:
        archiv(a.archiv, a.out)
        return 0
    return asyncio.run(knoten_lauf(a.anker, a.rolle, a.partner, a.out, a.suche_h))


if __name__ == "__main__":
    sys.exit(main())
