#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_nachzaehlung.py, Testnet-10 nachtraeglich zaehlen, nur lesend (Ben, 09.10.2026).

Zaehlt ein vergangenes Fenster aus dem, was zwei Knoten noch vorhalten, mit
derselben Zaehlweise wie tn10_zaehler.py: dieselbe Klasse Zaehler (Bloecke,
Coinbase, angenommene Tx je annehmendem Kettenblock) und dieselben
Minuten-Eimer nach Blockzeit (eimer). Statt Abos liest sie
    get_blocks             jeden Block ab einem Kettenblock vor dem Fenster
    get_virtual_chain_from_block  die Kette mit den angenommenen Tx-IDs
Liegt der Pruning-Punkt des Knotens nach dem Fensteranfang, sind die Bloecke
weg; das steht dann so im Ergebnis, geschaetzt wird nichts.

Grenze gegenueber der Live-Zaehlung: get_blocks liefert nur Bloecke, die im
Past des heutigen Sinks liegen. Ein Block, den nie ein Kettenblock gemergt hat,
fehlt hier, live waere er gezaehlt worden. Die Spalten zum Empfang (Verzug,
bloecke_nach_empfang) gibt es nachtraeglich nicht.

Sendet nichts, keine Wallet, keine Schluessel, keine Secrets. Hoechstens eine
Abfrage je Sekunde je Knoten. Ausgabe ohne Adressen von Knoten, nur Kennung
aus der p2p-Kennung.

    python3 scripts/tn10_nachzaehlung.py --von 2026-10-08T20:02:00Z --bis 2026-10-08T20:12:00Z --rolle k1 --partner P --out out/einzeln/nach-k1
    python3 scripts/tn10_nachzaehlung.py --kombinieren out/einzeln/nach-k1 out/einzeln/nach-k2 --out out/nach
    python3 scripts/tn10_nachzaehlung.py --selbsttest
"""
import argparse
import asyncio
import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tn10_zaehler import (NETZ, Takt, Zaehler, eimer, feld, iso_ms, kennung, schluessel,  # noqa: E402
                          wirt, zahl)

RAND_MS = 60000            # so weit vor und nach dem fenster wird gelesen
MAX_ABFRAGEN = 4000        # sicherung, je knoten
SPALTEN = ["minute_utc", "voll", "bloecke", "bloecke_pro_s", "tx_in_bloecken", "tx_je_block_mittel",
           "leere_bloecke", "angenommen_tx", "angenommen_pro_s", "daa_min", "daa_max", "blau_min", "blau_max",
           "ziel_bloecke", "ziel_anteil_pct", "miner_verschieden", "coinbase_unlesbar"]
COINBASE_SUBNETZ = "0100000000000000000000000000000000000000"


def miner_aus_coinbase(payload_hex):
    """(blue score, script hex) aus dem Payload der Coinbase: blue score u64,
    subsidy u64, script-version u16, laenge u8, script, extra. Der Script ist
    der, an den die Belohnung fuer DIESEN Block geht, also sein Miner. Die
    Ausgaben der Coinbase bezahlen dagegen die gemergten Bloecke. Unlesbar
    gibt None."""
    try:
        b = bytes.fromhex(payload_hex or "")
    except ValueError:
        return None
    if len(b) < 19 or len(b) < 19 + b[18]:
        return None
    return int.from_bytes(b[0:8], "little"), b[19:19 + b[18]].hex()


class Miner:
    """Je Minute nach Blockzeit: Bloecke, deren Miner-Script den Ziel-Hash hat
    (sha256 des Script-Hex), Zahl verschiedener Miner, unlesbare Coinbase.
    Weder Script noch Adresse verlassen den Prozess, nur Zaehlungen."""

    def __init__(self, ziel_sha=""):
        self.ziel = (ziel_sha or "").strip().lower()
        self.je = {}
        self.blau_falsch = 0

    def block(self, b, ts):
        m = self.je.setdefault(ts // 60000, {"ziel": 0, "scripts": set(), "unlesbar": 0})
        txs = feld(b, "transactions") or []
        cb = next((t for t in txs if str(feld(t, "subnetworkId") or "") == COINBASE_SUBNETZ), txs[0] if txs else None)
        x = miner_aus_coinbase(feld(cb, "payload") if cb else "")
        if x is None:
            m["unlesbar"] += 1
            return
        blau, script = x
        if zahl(feld(feld(b, "header") or {}, "blueScore")) not in (None, blau):
            self.blau_falsch += 1
        sha = hashlib.sha256(script.encode()).hexdigest()
        m["scripts"].add(sha)
        if self.ziel and sha == self.ziel:
            m["ziel"] += 1

    def spalten(self, minute, bloecke):
        m = self.je.get(minute)
        if not m:
            return {"ziel_bloecke": "", "ziel_anteil_pct": "", "miner_verschieden": "", "coinbase_unlesbar": ""}
        return {"ziel_bloecke": m["ziel"] if self.ziel else "",
                "ziel_anteil_pct": round(m["ziel"] / bloecke * 100, 2) if self.ziel and bloecke else "",
                "miner_verschieden": len(m["scripts"]), "coinbase_unlesbar": m["unlesbar"]}


def utc_ms(text):
    return int(dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


class Abbruch(Exception):
    pass


class Leser:
    """Liest ueber einen Knoten, haelt den Takt, zaehlt Abfragen."""

    def __init__(self, rpc, takt):
        self.rpc, self.takt, self.abfragen, self.form = rpc, takt, 0, {}
        self.ts_cache = {}

    async def rufe(self, name, anfrage=None):
        if self.abfragen >= MAX_ABFRAGEN:
            raise Abbruch("mehr als %d abfragen" % MAX_ABFRAGEN)
        await self.takt.warte()
        self.abfragen += 1
        f = getattr(self.rpc, name)
        d = await (f(anfrage) if anfrage is not None else f())
        self.form.setdefault(name, schluessel(d))
        return d

    async def ts(self, h):
        if h not in self.ts_cache:
            b = await self.rufe("get_block", {"hash": h, "includeTransactions": False})
            blk = feld(b, "block") or b
            self.ts_cache[h] = zahl(feld(feld(blk, "header") or {}, "timestamp"))
        return self.ts_cache[h]


async def start_finden(les, pp, ziel_ms):
    """Der letzte Kettenblock mit Blockzeit vor ziel_ms, ab dem Pruning-Punkt
    gesucht: die Kette in Stuecken, je Stueck die Zeit des letzten Blocks, im
    passenden Stueck binaer."""
    start = pp
    while True:
        r = await les.rufe("get_virtual_chain_from_block",
                           {"startHash": start, "includeAcceptedTransactionIds": False, "minConfirmationCount": None})
        neu = feld(r, "addedChainBlockHashes") or []
        if not neu:
            raise Abbruch("kette endet vor dem fenster")
        if (await les.ts(neu[-1]) or 0) >= ziel_ms:
            lo, hi = -1, len(neu) - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if (await les.ts(neu[mid]) or 0) < ziel_ms:
                    lo = mid
                else:
                    hi = mid
            return neu[lo] if lo >= 0 else start
        start = neu[-1]


async def bloecke_lesen(les, z, s0, ende_ms, miner=None):
    """Jeder Block ab s0, bis ein ganzes Stueck nach ende_ms liegt. Gibt die
    spaeteste Blockzeit zurueck, bis zu der lueckenlos gelesen ist."""
    low, gesehen, bis = s0, set(), 0
    while True:
        r = await les.rufe("get_blocks", {"lowHash": low, "includeBlocks": True, "includeTransactions": True})
        bl = feld(r, "blocks") or []
        hs = feld(r, "blockHashes") or []
        neu, frueh = 0, None
        for b in bl:
            h = feld(feld(b, "verboseData") or {}, "hash") or feld(feld(b, "header") or {}, "hash")
            if not h or h in gesehen:
                continue
            gesehen.add(h)
            neu += 1
            z.block({"block": b})
            ts = zahl(feld(feld(b, "header") or {}, "timestamp"))
            if ts is not None:
                frueh = ts if frueh is None else min(frueh, ts)
                bis = max(bis, ts)
                if miner is not None:
                    miner.block(b, ts)
        if not neu or not hs:
            return bis
        if frueh is not None and frueh > ende_ms:
            return bis
        low = hs[-1]


async def kette_lesen(les, z, s0, ende_ms):
    """Die Kette ab s0 mit den angenommenen Tx-IDs, in Stuecken, weiter ab dem
    letzten Kettenblock, zu dem die Antwort Annahmen enthaelt. Gibt die
    Blockzeit des letzten so gelesenen Kettenblocks zurueck."""
    start, bis = s0, 0
    while True:
        r = await les.rufe("get_virtual_chain_from_block",
                           {"startHash": start, "includeAcceptedTransactionIds": True, "minConfirmationCount": None})
        neu = feld(r, "addedChainBlockHashes") or []
        acc = feld(r, "acceptedTransactionIds") or []
        if not neu:
            return bis
        z.kette(r)
        letzter = feld(acc[-1], "acceptingBlockHash") if acc else neu[-1]
        if letzter == start:
            return bis
        t = z.bloecke.get(letzter, {}).get("ts") or await les.ts(letzter) or 0
        bis = max(bis, t)
        if t > ende_ms:
            return bis
        start = letzter


async def verbinden(rolle, partner):
    import kaspa                                         # noqa: WPS433
    takt = Takt()
    meide_wirt, meide_p2p = "", ""
    if rolle == "k2" and partner:
        from tn10_zaehler import partner_lesen
        meide_wirt, meide_p2p = partner_lesen(partner, 120)
    for versuch in range(8):
        await takt.warte()
        url = await kaspa.Resolver().get_url("borsh", kaspa.NetworkId(NETZ))
        if meide_wirt and wirt(url) == meide_wirt and versuch < 7:
            continue
        rpc = kaspa.RpcClient(url=url, network_id=NETZ)
        await rpc.connect()
        await takt.warte()
        info = await rpc.get_info()
        p2p = str(feld(info, "p2pId") or "")
        if meide_p2p and p2p == meide_p2p and versuch < 7:
            await rpc.disconnect()
            continue
        if rolle == "k1" and partner:
            with open(partner + ".neu", "w", encoding="utf-8") as fh:
                json.dump({"wirt": wirt(url), "p2p": p2p}, fh)
            os.replace(partner + ".neu", partner)
        return rpc, takt, {"kennung": kennung(p2p), "version": str(feld(info, "serverVersion") or ""),
                           "gleich_wie_partner": bool(meide_p2p and p2p == meide_p2p)}
    raise Abbruch("kein knoten")


async def zaehle(rpc, takt, von_ms, bis_ms, rand_ms=RAND_MS, ziel_sha="", kette=True):
    """Ergebnis fuer einen Knoten: zeilen je minute und meta. kette False
    liest nur die Bloecke (Miner-Anteil), angenommen bleibt dann leer."""
    les, z, mi = Leser(rpc, takt), Zaehler(), Miner(ziel_sha)
    phasen = {}

    def phase(name, a0, t0):
        phasen[name] = {"abfragen": les.abfragen - a0, "sekunden": round(time.time() - t0, 1)}
    meta = {"von": iso_ms(von_ms), "bis": iso_ms(bis_ms), "status": "", "meldungen": []}
    try:
        dag = await les.rufe("get_block_dag_info")
        pp = feld(dag, "pruningPointHash")
        pp_ts = await les.ts(pp) if pp else None
        meta["pruning_punkt_utc"] = iso_ms(pp_ts) if pp_ts else ""
        if pp_ts is None or pp_ts > von_ms - rand_ms:
            meta["status"] = "bloecke weg, pruning-punkt %s liegt nach dem fensteranfang" % meta["pruning_punkt_utc"]
            return [], meta
        a0, t0 = les.abfragen, time.time()
        s0 = await start_finden(les, pp, von_ms - rand_ms)
        meta["start_utc"] = iso_ms(await les.ts(s0))
        phase("start", a0, t0)
        a0, t0 = les.abfragen, time.time()
        b_bis = await bloecke_lesen(les, z, s0, bis_ms + rand_ms, mi)
        phase("bloecke", a0, t0)
        a0, t0 = les.abfragen, time.time()
        k_bis = await kette_lesen(les, z, s0, bis_ms + rand_ms) if kette else b_bis
        phase("kette", a0, t0)
        meta["bloecke_bis_utc"], meta["kette_bis_utc"] = iso_ms(b_bis), iso_ms(k_bis)
        gelesen_bis = min(b_bis, k_bis)
    except Abbruch as exc:
        meta["status"] = "abbruch, %s" % exc
        return [], meta
    except Exception as exc:                             # noqa: BLE001
        meta["status"] = "fehler, %s" % type(exc).__name__
        meta["meldungen"].append(str(exc)[:300])
        return [], meta
    # nachtraeglich gibt es keine empfangspausen; voll ist eine minute, wenn
    # bloecke und kette lueckenlos ueber sie hinaus gelesen sind
    takte = list(range(von_ms - rand_ms, bis_ms + rand_ms + 1, 1000))
    z.empfang_bloecke, z.empfang_kette = takte, list(takte)
    luecken = [] if gelesen_bis >= bis_ms else [(gelesen_bis, bis_ms)]
    zeilen, extra = eimer(z, von_ms, bis_ms, luecken)
    meta.update({"status": meta["status"] or "gelesen", "abfragen": les.abfragen, "datenform": les.form,
                 "angenommen_ohne_blockzeit": extra["angenommen_ohne_blockzeit"], "phasen": phasen,
                 "ziel_gesetzt": bool(mi.ziel), "blau_score_im_payload_falsch": mi.blau_falsch,
                 "kette_gelesen": kette})
    aus = []
    for m in range(von_ms // 60000, -(-bis_ms // 60000)):
        if m in zeilen:
            zr = dict(zeilen[m], **mi.spalten(m, zeilen[m]["bloecke"]))
            if not kette:
                zr["angenommen_tx"] = zr["angenommen_pro_s"] = ""
            aus.append({k: zr[k] for k in SPALTEN})
        else:                                            # minute ohne block: nie still als null
            aus.append(dict({k: "" for k in SPALTEN}, minute_utc=iso_ms(m * 60000)[:16] + "Z", voll=0))
    return aus, meta


def fenster_lesen(text):
    """Zwei Zeiten in UTC aus der Fensterdatei, Kommentarzeilen mit # zaehlen
    nicht. Eine dritte Zeile "nur-bloecke" laesst die Kette weg."""
    zeilen = [z.strip() for z in text.splitlines() if z.strip() and not z.strip().startswith("#")]
    von, bis = zeilen[0], zeilen[1]
    if utc_ms(bis) <= utc_ms(von):
        raise ValueError("fensterende vor fensteranfang")
    return von, bis, (len(zeilen) > 2 and zeilen[2] == "nur-bloecke")


def schreiben(basis, zeilen, meta):
    os.makedirs(os.path.dirname(basis) or ".", exist_ok=True)
    with open(basis + ".csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN)
        w.writeheader()
        w.writerows(zeilen)
    with open(basis + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


def lesen(basis):
    try:
        with open(basis + ".json", encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        meta = {"status": "keine ergebnisdatei"}
    try:
        with open(basis + ".csv", encoding="utf-8") as fh:
            zeilen = list(csv.DictReader(fh))
    except OSError:
        zeilen = []
    return zeilen, meta


def kombinieren(b1, b2):
    (z1, m1), (z2, m2) = lesen(b1), lesen(b2)
    r1 = {r["minute_utc"]: r for r in z1}
    r2 = {r["minute_utc"]: r for r in z2}
    spalten = ["minute_utc", "k1_voll", "k1_bloecke", "k1_angenommen", "k1_angenommen_pro_s",
               "k2_voll", "k2_bloecke", "k2_angenommen", "k2_angenommen_pro_s", "knoten_gleich",
               "k1_ziel_bloecke", "k2_ziel_bloecke", "ziel_anteil_pct", "miner_verschieden", "blau_min", "blau_max"]
    aus = []
    for m in sorted(set(r1) | set(r2)):
        a, b = r1.get(m, {}), r2.get(m, {})
        beide = a.get("voll") == "1" and b.get("voll") == "1"
        aus.append({"minute_utc": m, "k1_voll": a.get("voll", ""), "k1_bloecke": a.get("bloecke", ""),
                    "k1_angenommen": a.get("angenommen_tx", ""), "k1_angenommen_pro_s": a.get("angenommen_pro_s", ""),
                    "k2_voll": b.get("voll", ""), "k2_bloecke": b.get("bloecke", ""),
                    "k2_angenommen": b.get("angenommen_tx", ""), "k2_angenommen_pro_s": b.get("angenommen_pro_s", ""),
                    "knoten_gleich": (int(a.get("bloecke") == b.get("bloecke")
                                          and a.get("angenommen_tx") == b.get("angenommen_tx")
                                          and a.get("ziel_bloecke") == b.get("ziel_bloecke")) if beide else ""),
                    "k1_ziel_bloecke": a.get("ziel_bloecke", ""), "k2_ziel_bloecke": b.get("ziel_bloecke", ""),
                    "ziel_anteil_pct": a.get("ziel_anteil_pct") or b.get("ziel_anteil_pct", ""),
                    "miner_verschieden": a.get("miner_verschieden") or b.get("miner_verschieden", ""),
                    "blau_min": a.get("blau_min") or b.get("blau_min", ""),
                    "blau_max": a.get("blau_max") or b.get("blau_max", "")})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=spalten, lineterminator="\n")
    w.writeheader()
    w.writerows(aus)
    zus = []
    for n, m in (("k1", m1), ("k2", m2)):
        zus.append("%s kennung %s version %s status %s pruning-punkt %s start %s bloecke bis %s kette bis %s "
                   "abfragen %s ohne blockzeit %s phasen %s ziel %s blau-score im payload falsch %s%s" % (
                       n, m.get("kennung", ""), m.get("version", ""), m.get("status", ""),
                       m.get("pruning_punkt_utc", ""), m.get("start_utc", ""), m.get("bloecke_bis_utc", ""),
                       m.get("kette_bis_utc", ""), m.get("abfragen", ""), m.get("angenommen_ohne_blockzeit", ""),
                       json.dumps(m.get("phasen", {})), m.get("ziel_gesetzt", ""), m.get("blau_score_im_payload_falsch", ""),
                       ", gleicher knoten wie k1" if m.get("gleich_wie_partner") else ""))
    beide = [r for r in aus if r["knoten_gleich"] != ""]
    zus.append("minuten mit beiden knoten voll %d, davon gleich %d" % (
        len(beide), sum(1 for r in beide if r["knoten_gleich"] == 1)))
    return buf.getvalue(), zus


async def lauf(von_ms, bis_ms, rolle, partner, out, ziel_sha="", kette=True):
    try:
        rpc, takt, kn = await verbinden(rolle, partner)
    except Exception as exc:                             # noqa: BLE001
        schreiben(out, [], {"status": "kein knoten, %s" % type(exc).__name__})
        return 1
    zeilen, meta = await zaehle(rpc, takt, von_ms, bis_ms, ziel_sha=ziel_sha, kette=kette)
    meta.update(kn)
    schreiben(out, zeilen, meta)
    try:
        await rpc.disconnect()
    except Exception:                                    # noqa: BLE001
        pass
    print("%s %s, %d minuten, %s abfragen" % (rolle, meta["status"], len(zeilen), meta.get("abfragen", "")))
    # nichts gelesen ist ein fehler, der lauf wird rot (09.10.: websocket getrennt, lauf blieb gruen)
    return 0 if meta["status"] == "gelesen" else 1


# ---------------------------------------------------------------- selbsttest

class FakeKnoten:
    """Eine kleine Kette: je Sekunde ein Kettenblock c<i> mit einem Block
    daneben r<i>; c<i> nimmt die Tx von c<i-1> und r<i-1> an. Stueckgroesse
    wie beim Knoten begrenzt."""

    def __init__(self, t0_ms, n, stueck=7, pp=0):
        self.t0, self.n, self.stueck, self.pp = t0_ms, n, stueck, pp

    def blk(self, h):
        i = int(h[1:])
        ts = self.t0 + i * 1000 + (300 if h[0] == "r" else 0)
        script = ("20" + "ab" * 32 + "ac") if h[0] == "r" else ("20" + "cd" * 32 + "ac")
        payload = (i.to_bytes(8, "little") + (5).to_bytes(8, "little") + (0).to_bytes(2, "little")
                   + bytes([len(script) // 2]) + bytes.fromhex(script) + b"x").hex()
        txs = [{"subnetworkId": "0100000000000000000000000000000000000000", "payload": payload,
                "verboseData": {"transactionId": "cb-" + h}}] + [
            {"subnetworkId": "0000000000000000000000000000000000000000",
             "verboseData": {"transactionId": "%s-%d" % (h, k)}} for k in range(2)]
        return {"header": {"timestamp": ts, "daaScore": i, "blueScore": i},
                "verboseData": {"hash": h}, "transactions": txs}

    async def get_block_dag_info(self):
        return {"pruningPointHash": "c%d" % self.pp}

    async def get_block(self, a):
        return {"block": self.blk(a["hash"])}

    async def get_blocks(self, a):
        i = int(a["lowHash"][1:])
        hs = []
        for j in range(i, min(i + self.stueck, self.n)):
            hs += ["c%d" % j, "r%d" % j]
        return {"blockHashes": hs, "blocks": [self.blk(h) for h in hs]}

    async def get_virtual_chain_from_block(self, a):
        i = int(a["startHash"][1:])
        neu = ["c%d" % j for j in range(i + 1, min(i + 1 + self.stueck, self.n))]
        acc = []
        if a["includeAcceptedTransactionIds"]:
            for h in neu[:max(1, len(neu) - 2)]:          # annahmen kuerzer als die kette
                j = int(h[1:])
                ids = ["cb-c%d" % (j - 1), "c%d-0" % (j - 1), "c%d-1" % (j - 1),
                       "cb-r%d" % (j - 1), "r%d-0" % (j - 1), "r%d-1" % (j - 1)]
                acc.append({"acceptingBlockHash": h, "acceptedTransactionIds": ids})
        return {"addedChainBlockHashes": neu, "removedChainBlockHashes": [], "acceptedTransactionIds": acc}


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    class OhneTakt:
        async def warte(self):
            return None

        def zuviel(self):
            return None

    t0 = utc_ms("2026-10-08T20:00:00Z")
    k = FakeKnoten(t0, 600)            # 10 minuten, je sekunde 2 bloecke, 4 tx, 4 angenommen
    ziel = hashlib.sha256(("20" + "ab" * 32 + "ac").encode()).hexdigest()
    zeilen, meta = asyncio.run(zaehle(k, OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000, ziel_sha=ziel))
    ok("nachzaehlung gelesen, %s" % meta["status"], meta["status"] == "gelesen")
    ok("drei volle minuten 20:02 bis 20:04", [r["minute_utc"][11:16] for r in zeilen] == ["20:02", "20:03", "20:04"]
       and all(r["voll"] == 1 for r in zeilen))
    ok("120 bloecke je minute", all(r["bloecke"] == 120 for r in zeilen))
    ok("240 angenommene tx je minute, coinbase nicht", all(r["angenommen_tx"] == 240 for r in zeilen))
    ok("start vor dem fenster mit rand", meta["start_utc"] < "2026-10-08T20:01:00")
    ok("miner aus der coinbase, 60 von 120 bloecken vom ziel, 50 %", all(
        r["ziel_bloecke"] == 60 and r["ziel_anteil_pct"] == 50.0 and r["miner_verschieden"] == 2
        and r["coinbase_unlesbar"] == 0 for r in zeilen))
    ok("blue score im payload passt zum kopf", meta["blau_score_im_payload_falsch"] == 0)
    ok("payload zu kurz gibt none", miner_aus_coinbase("00" * 10) is None and miner_aus_coinbase("zz") is None)
    zn, mn = asyncio.run(zaehle(FakeKnoten(t0, 600), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000,
                                ziel_sha=ziel, kette=False))
    ok("nur bloecke, angenommen leer, miner gezaehlt", all(r["angenommen_tx"] == "" and r["ziel_bloecke"] == 60
                                                          for r in zn) and mn["phasen"]["kette"]["abfragen"] == 0)
    zo, _mo = asyncio.run(zaehle(FakeKnoten(t0, 600), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000))
    ok("ohne ziel keine zielspalte, miner trotzdem gezaehlt", all(r["ziel_bloecke"] == "" and r["miner_verschieden"] == 2
                                                                 for r in zo))
    zw, mw = asyncio.run(zaehle(FakeKnoten(t0, 600, pp=200), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000))
    ok("pruning-punkt nach dem fensteranfang, bloecke weg, keine zeile",
       zw == [] and mw["status"].startswith("bloecke weg"))
    zk, mk = asyncio.run(zaehle(FakeKnoten(t0, 230), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000))
    ok("kette endet im fenster, spaete minuten nicht voll", [r["voll"] for r in zk][-1] == 0
       and [r["voll"] for r in zk][0] == 1)
    with tempfile.TemporaryDirectory() as tmp:
        schreiben(os.path.join(tmp, "k1"), zeilen, dict(meta, kennung="aaa"))
        schreiben(os.path.join(tmp, "k2"), zeilen, dict(meta, kennung="bbb"))
        text, zus = kombinieren(os.path.join(tmp, "k1"), os.path.join(tmp, "k2"))
    ok("kombinieren, beide knoten gleich", "minuten mit beiden knoten voll 3, davon gleich 3" in zus[-1])
    ok("keine adressen in der ausgabe", "://" not in text + " ".join(zus))
    ok("kein script in der ausgabe", "ab" * 32 not in text + " ".join(zus) + json.dumps(meta))
    datei = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "messung", "tn10", "nach", "fenster.txt")
    if os.path.exists(datei):
        with open(datei, encoding="utf-8") as fh:
            v, b, _nb = fenster_lesen(fh.read())
        ok("fensterdatei lesbar, %s bis %s" % (v, b), utc_ms(v) < utc_ms(b))
    ok("fenster mit kommentarzeile", fenster_lesen("# kommentar, mit worten\n2026-10-08T20:02:00Z\n"
                                                    "2026-10-08T20:13:00Z\n") == ("2026-10-08T20:02:00Z",
                                                                                    "2026-10-08T20:13:00Z", False))
    ok("fenster nur bloecke", fenster_lesen("2026-10-08T20:02:00Z\n2026-10-08T20:13:00Z\nnur-bloecke\n")[2])
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--von", help="fensteranfang utc, 2026-10-08T20:02:00Z")
    ap.add_argument("--bis", help="fensterende utc")
    ap.add_argument("--fenster", help="datei mit zwei zeilen von und bis")
    ap.add_argument("--rolle", choices=["k1", "k2"], default="k1")
    ap.add_argument("--partner", default="")
    ap.add_argument("--out", default="out/nach")
    ap.add_argument("--kombinieren", nargs=2, metavar=("K1", "K2"))
    ap.add_argument("--ziel-datei", default="", help="datei mit dem sha256 des miner-scripts, nie die adresse")
    ap.add_argument("--nur-bloecke", action="store_true", help="kette nicht lesen, nur bloecke und miner")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.kombinieren:
        text, zus = kombinieren(*a.kombinieren)
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out + ".csv", "w", encoding="utf-8") as fh:
            fh.write(text)
        print("=== nachzaehlung, beide knoten, minuten csv")
        print(text)
        print("=== zusammenfassung")
        print("\n".join(zus))
        return 0
    von, bis, nur = a.von, a.bis, a.nur_bloecke
    if a.fenster:
        with open(a.fenster, encoding="utf-8") as fh:
            von, bis, nb = fenster_lesen(fh.read())
        nur = nur or nb
    ziel = ""
    if a.ziel_datei and os.path.exists(a.ziel_datei):
        with open(a.ziel_datei, encoding="utf-8") as fh:
            ziel = next((z.strip() for z in fh if z.strip() and not z.startswith("#")), "")
    return asyncio.run(lauf(utc_ms(von), utc_ms(bis), a.rolle, a.partner, a.out, ziel, not nur))


if __name__ == "__main__":
    sys.exit(main())
