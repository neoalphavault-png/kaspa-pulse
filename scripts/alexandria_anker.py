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
    python3 scripts/alexandria_anker.py --archiv URL --out out/archiv
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
import urllib.parse
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
    aus = sum(zahl(feld(o, "amount")) or 0 for o in feld(tx, "outputs") or [])
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
                aus["%s:%d" % (i, n)] = zahl(feld(o, "amount")) or 0
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
        json.dump({"pruefung": erg, "roh": roh}, fh, ensure_ascii=False, indent=1, sort_keys=True)
    for z in zusammenfassung(rolle, meta, erg):
        print(z)
    return 0 if erg.get("tx_gefunden") else 1


# archiv: seite und verlinkte dateien desselben hosts byte-genau sichern
LINK = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#]+)["']|["'](/(?:api|files?|download|manifest|study)[^"'\s]*)["']""", re.I)


def holen(url, limit=20 * 1024 * 1024):
    req = urllib.request.Request(url, headers={"User-Agent": "kaspa-pulse-pruefung/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read(limit)


def archiv(start, out, extra=(), max_dateien=60):
    os.makedirs(out, exist_ok=True)
    host = urllib.parse.urlparse(start).netloc
    offen, gesehen, liste = [start] + list(extra), set(), []
    while offen and len(gesehen) < max_dateien:
        u = offen.pop(0)
        if u in gesehen:
            continue
        gesehen.add(u)
        try:
            st, ct, daten = holen(u)
        except Exception as exc:  # noqa: BLE001
            liste.append({"url": u, "fehler": type(exc).__name__ + " " + str(exc)[:120]})
            continue
        name = "%03d" % len(liste)
        with open(os.path.join(out, name + ".bin"), "wb") as fh:
            fh.write(daten)
        liste.append({"url": u, "status": st, "typ": ct, "bytes": len(daten), "datei": name + ".bin",
                      "sha256": hashlib.sha256(daten).hexdigest()})
        if "html" in ct or "javascript" in ct or "json" in ct:
            for m in LINK.finditer(daten.decode("utf-8", "replace")):
                z = urllib.parse.urljoin(u, m.group(1) or m.group(2))
                if urllib.parse.urlparse(z).netloc == host and z not in gesehen:
                    offen.append(z)
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
          "outputs": [{"amount": 99000000}, {"amount": 779400}], "verboseData": {"transactionId": "bb" * 32}}
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
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--anker")
    ap.add_argument("--rolle", choices=["k1", "k2"])
    ap.add_argument("--partner", default="")
    ap.add_argument("--suche-h", type=int, default=SUCHE_H)
    ap.add_argument("--archiv")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--out", default="out/anker")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.archiv:
        archiv(a.archiv, a.out, a.extra)
        return 0
    return asyncio.run(knoten_lauf(a.anker, a.rolle, a.partner, a.out, a.suche_h))


if __name__ == "__main__":
    sys.exit(main())
