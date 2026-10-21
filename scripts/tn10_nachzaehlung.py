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
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tn10_zaehler import (NETZ, Takt, Zaehler, adressfrei, eimer, fake_kaspa, feld, iso_ms,  # noqa: E402
                          kennung, ohne_adresse, schluessel, wirt, zahl)

RAND_MS = 60000            # so weit vor und nach dem fenster wird gelesen
MAX_ABFRAGEN = 4000        # sicherung, je knoten
SPALTEN = ["minute_utc", "voll", "bloecke", "bloecke_pro_s", "tx_in_bloecken", "tx_je_block_mittel",
           "leere_bloecke", "angenommen_tx", "angenommen_pro_s", "daa_min", "daa_max", "blau_min", "blau_max",
           "ziel_bloecke", "ziel_anteil_pct", "ziel_je", "miner_verschieden", "coinbase_unlesbar",
           "cov_in_bloecken", "cov_angenommen", "cov_nie_angenommen"]
COV_SPALTEN = ["tx_id", "familie", "erster_block_ms", "bloecke", "angenommen", "annehmender_block_ms"]
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


def ziele_lesen(text):
    """Ziel-Hashes aus der Zieldatei: je Zeile "name sha256" oder nur "sha256"
    (Name dann "ziel"), Kommentarzeilen mit #. Ergibt {sha256: name}. Nie
    Adresse oder Script, nur der Hash (Ben, 17.10.2026: zwei Ziele, Bot und
    Build)."""
    aus = {}
    for z in (text or "").splitlines():
        t = z.split("#", 1)[0].split()
        if not t:
            continue
        name, sha = (t[0], t[1]) if len(t) > 1 else ("ziel", t[0])
        if len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
            raise ValueError("ziel-zeile ohne sha256")
        aus[sha.lower()] = name
    return aus


class Miner:
    """Je Minute nach Blockzeit: Bloecke, deren Miner-Script einen der
    Ziel-Hashes hat (sha256 des Script-Hex), je Ziel und zusammen, Zahl
    verschiedener Miner, unlesbare Coinbase. Weder Script noch Adresse
    verlassen den Prozess, nur Zaehlungen."""

    def __init__(self, ziel_sha=""):
        self.ziele = ziele_lesen(ziel_sha) if isinstance(ziel_sha, str) else dict(ziel_sha or {})
        self.ziel = bool(self.ziele)
        self.je = {}
        self.blau_falsch = 0

    def block(self, b, ts):
        m = self.je.setdefault(ts // 60000, {"ziel": 0, "je": {}, "scripts": set(), "unlesbar": 0})
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
        if sha in self.ziele:
            m["ziel"] += 1
            m["je"][self.ziele[sha]] = m["je"].get(self.ziele[sha], 0) + 1

    def spalten(self, minute, bloecke):
        m = self.je.get(minute)
        if not m:
            return {"ziel_bloecke": "", "ziel_anteil_pct": "", "ziel_je": "", "miner_verschieden": "",
                    "coinbase_unlesbar": ""}
        je = " ".join("%s %d" % (n, m["je"].get(n, 0)) for n in sorted(set(self.ziele.values())))
        return {"ziel_bloecke": m["ziel"] if self.ziel else "",
                "ziel_anteil_pct": round(m["ziel"] / bloecke * 100, 2) if self.ziel and bloecke else "",
                "ziel_je": je, "miner_verschieden": len(m["scripts"]), "coinbase_unlesbar": m["unlesbar"]}


def cov_hash(cid):
    """sha256 der Covenant-ID als kleingeschriebenes Hex. Nur dieser Hash steht
    in der Zieldatei, nie die ID (Ben, 21.10.2026)."""
    return hashlib.sha256(str(cid).strip().lower().encode()).hexdigest()


FAMILIE = re.compile(r"^[a-z0-9_]{1,24}$")


def familien_lesen(text):
    """Covenant-Familien aus der Zieldatei: je Zeile "name sha256" (sha256 der
    Covenant-ID, nie die ID). Ergibt {sha256: name} in Dateireihenfolge. Namen
    werden Spaltennamen: klein, Ziffern, Unterstrich, eindeutig (Ben,
    23.10.2026: 1, 2, dann 4 Familien parallel)."""
    z = ziele_lesen(text)
    namen = list(z.values())
    for n in namen:
        if not FAMILIE.match(n):
            raise ValueError("familienname nur a-z, 0-9, _: %r" % n)
    if len(set(namen)) != len(namen):
        raise ValueError("familienname doppelt")
    return z


class Covenant:
    """Contention-Phase (Ben, 21.10.2026, ab 23.10. mehrere Familien):
    Ausgaben benannter Covenants, je Familie getrennt und zusammen.

    Eine Tx zaehlt als Ausgabe einer Familie, wenn einer ihrer Ausgaenge an
    deren Covenant-ID gebunden ist (Fortsetzung, auch die Entstehung) oder
    einer ihrer Eingaenge einen solchen Ausgang ausgibt, der vorher gelesen
    wurde. Je Tx: Blockzeit des ersten Blocks, der sie enthaelt, Zahl der
    Bloecke, und ob die Kette sie angenommen hat, mit der Blockzeit des
    annehmenden Kettenblocks. Konkurrierende Ausgaben, die in einem Block
    stehen, aber nie angenommen werden, bleiben als "nie angenommen" sichtbar.
    Beruehrt eine Tx zwei Familien, zaehlt sie bei beiden, in der Summe einmal.
    Grenze: eine Ausgabe ohne Fortsetzung, deren Block vor dem Block der
    Entstehung gelesen wird, faellt durch; meta zaehlt, wie viele Treffer nur
    ueber Eingaenge kamen."""

    def __init__(self, ziel_sha=""):
        self.ziele = familien_lesen(ziel_sha) if isinstance(ziel_sha, str) else dict(ziel_sha or {})
        self.familien = list(dict.fromkeys(self.ziele.values()))
        self.aktiv = bool(self.ziele)
        self.ausgaenge = {}         # "txid:index" -> familie
        self.tx = {}                # txid -> {"erst": ms, "bloecke": n, "familien": set}
        self.annahme = {}           # txid -> annehmender block
        self.ohne_id = 0
        self.nur_eingang = 0

    def block(self, b, ts):
        if not self.aktiv:
            return
        for tx in feld(b, "transactions") or []:
            tid = feld(feld(tx, "verboseData") or {}, "transactionId")
            aus = set()
            for i, o in enumerate(feld(tx, "outputs") or []):
                cid = feld(feld(o, "covenant") or {}, "covenantId")
                f = self.ziele.get(cov_hash(cid)) if cid else None
                if f:
                    aus.add(f)
                    if tid:
                        self.ausgaenge["%s:%d" % (tid, i)] = f
            ein = {self.ausgaenge.get("%s:%s" % (feld(feld(e, "previousOutpoint") or {}, "transactionId"),
                                                 feld(feld(e, "previousOutpoint") or {}, "index")))
                   for e in feld(tx, "inputs") or []} - {None}
            if not (aus or ein):
                continue
            if not tid:
                self.ohne_id += 1
                continue
            if ein and not aus and tid not in self.tx:
                self.nur_eingang += 1
            e = self.tx.setdefault(tid, {"erst": ts, "bloecke": 0, "familien": set()})
            e["erst"] = min(e["erst"], ts)
            e["bloecke"] += 1
            e["familien"] |= aus | ein

    def kette(self, r):
        if not self.aktiv:
            return
        weg = set(feld(r, "removedChainBlockHashes") or [])
        if weg:
            self.annahme = {t: h for t, h in self.annahme.items() if h not in weg}
        for eintrag in feld(r, "acceptedTransactionIds") or []:
            h = feld(eintrag, "acceptingBlockHash")
            for t in feld(eintrag, "acceptedTransactionIds") or []:
                if t in self.tx and h:
                    self.annahme[t] = h

    def spalten(self):
        return [("cov_%s_%s" % (f, k)) for f in self.familien for k in ("in_bloecken", "angenommen", "nie_angenommen")]

    def auswerten(self, blockzeit, kette_gelesen):
        """je minute {"summe": {...}, familie: {...}} und je tx eine zeile."""
        leer = lambda: {"in": 0, "an": 0, "nie": 0}  # noqa: E731
        je, txz = {}, []
        for t, e in sorted(self.tx.items(), key=lambda kv: (kv[1]["erst"], kv[0])):
            h = self.annahme.get(t)
            ats = blockzeit(h) if h else None
            for f in ["summe"] + sorted(e["familien"]):
                m = je.setdefault(e["erst"] // 60000, {}).setdefault(f, leer())
                m["in"] += 1
                if ats is not None:
                    je.setdefault(ats // 60000, {}).setdefault(f, leer())["an"] += 1
                elif kette_gelesen:
                    m["nie"] += 1
            txz.append({"tx_id": t, "familie": "+".join(sorted(e["familien"])), "erster_block_ms": e["erst"],
                        "bloecke": e["bloecke"],
                        "angenommen": (1 if ats is not None else 0) if kette_gelesen else "",
                        "annehmender_block_ms": ats if ats is not None else ""})
        return je, txz


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


async def bloecke_lesen(les, z, s0, ende_ms, miner=None, cov=None):
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
                if cov is not None:
                    cov.block(b, ts)
        if not neu or not hs:
            return bis
        if frueh is not None and frueh > ende_ms:
            return bis
        low = hs[-1]


async def kette_lesen(les, z, s0, ende_ms, cov=None):
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
        if cov is not None:
            cov.kette(r)
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


async def zaehle(rpc, takt, von_ms, bis_ms, rand_ms=RAND_MS, ziel_sha="", kette=True, cov_sha=""):
    """Ergebnis fuer einen Knoten: zeilen je minute und meta. kette False
    liest nur die Bloecke (Miner-Anteil), angenommen bleibt dann leer."""
    les, z, mi, cv = Leser(rpc, takt), Zaehler(), Miner(ziel_sha), Covenant(cov_sha)
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
        b_bis = await bloecke_lesen(les, z, s0, bis_ms + rand_ms, mi, cv)
        phase("bloecke", a0, t0)
        a0, t0 = les.abfragen, time.time()
        k_bis = await kette_lesen(les, z, s0, bis_ms + rand_ms, cv) if kette else b_bis
        phase("kette", a0, t0)
        meta["bloecke_bis_utc"], meta["kette_bis_utc"] = iso_ms(b_bis), iso_ms(k_bis)
        gelesen_bis = min(b_bis, k_bis)
    except Abbruch as exc:
        meta["status"] = "abbruch, %s" % exc
        return [], meta
    except Exception as exc:                             # noqa: BLE001
        meta["status"] = "fehler, %s" % type(exc).__name__
        meta["meldungen"].append(ohne_adresse(str(exc))[:300])
        return [], meta
    # nachtraeglich gibt es keine empfangspausen; voll ist eine minute, wenn
    # bloecke und kette lueckenlos ueber sie hinaus gelesen sind
    takte = list(range(von_ms - rand_ms, bis_ms + rand_ms + 1, 1000))
    z.empfang_bloecke, z.empfang_kette = takte, list(takte)
    luecken = [] if gelesen_bis >= bis_ms else [(gelesen_bis, bis_ms)]
    zeilen, extra = eimer(z, von_ms, bis_ms, luecken)
    meta.update({"status": meta["status"] or "gelesen", "abfragen": les.abfragen, "datenform": les.form,
                 "angenommen_ohne_blockzeit": extra["angenommen_ohne_blockzeit"], "phasen": phasen,
                 "ziel_gesetzt": len(mi.ziele), "blau_score_im_payload_falsch": mi.blau_falsch,
                 "kette_gelesen": kette})
    cov_je, cov_tx = cv.auswerten(lambda h: z.bloecke.get(h, {}).get("ts"), kette)
    if cv.aktiv:
        meta["covenant"] = {"ziel_gesetzt": len(cv.ziele), "familien": cv.familien, "tx": len(cov_tx), "ohne_txid": cv.ohne_id,
                            "nur_ueber_eingang": cv.nur_eingang, "tx_liste": cov_tx}
    aus = []
    spalten = SPALTEN + cv.spalten()
    for m in range(von_ms // 60000, -(-bis_ms // 60000)):
        if m in zeilen:
            cj = cov_je.get(m, {})

            def cw(f, k, an=False):
                if not cv.aktiv or (an and not kette):
                    return ""
                return cj.get(f, {}).get(k, 0)
            zr = dict(zeilen[m], **mi.spalten(m, zeilen[m]["bloecke"]),
                      cov_in_bloecken=cw("summe", "in"), cov_angenommen=cw("summe", "an", True),
                      cov_nie_angenommen=cw("summe", "nie", True))
            for f in cv.familien:
                zr["cov_%s_in_bloecken" % f] = cw(f, "in")
                zr["cov_%s_angenommen" % f] = cw(f, "an", True)
                zr["cov_%s_nie_angenommen" % f] = cw(f, "nie", True)
            if not kette:
                zr["angenommen_tx"] = zr["angenommen_pro_s"] = ""
            aus.append({k: zr[k] for k in spalten})
        else:                                            # minute ohne block: nie still als null
            aus.append(dict({k: "" for k in spalten}, minute_utc=iso_ms(m * 60000)[:16] + "Z", voll=0))
    return aus, meta


MEMPOOL_MAX_WARTEN_S = 340 * 60   # laenger schlaeft ein job nicht


def mempool_auswerten(antwort, ziele):
    """Mempool samt Orphan-Pool: wie viele Eintraege, wie viele Orphans, und je
    Familie die Eintraege mit einem an ihre Covenant-ID gebundenen Ausgang,
    getrennt nach Orphan und wartend. Nur Zahlen."""
    eintraege = feld(antwort, "mempoolEntries") or feld(antwort, "entries") or (
        antwort if isinstance(antwort, list) else [])
    aus = {"eintraege": len(eintraege), "orphans": 0, "familien": {}}
    for f in dict.fromkeys(ziele.values()):
        aus["familien"][f] = {"orphans": 0, "wartend": 0}
    for e in eintraege:
        orphan = bool(feld(e, "isOrphan"))
        aus["orphans"] += orphan
        tx = feld(e, "transaction") or {}
        fam = {ziele.get(cov_hash(c)) for c in (feld(feld(o, "covenant") or {}, "covenantId")
                                               for o in feld(tx, "outputs") or []) if c} - {None}
        for f in fam:
            aus["familien"][f]["orphans" if orphan else "wartend"] += 1
    return aus


async def mempool_lauf(um_ms, rolle, partner, out, cov_sha="", jetzt=time.time, schlafen=asyncio.sleep):
    """Wartet bis um_ms (15 min nach END), liest dann einmal den Mempool samt
    Orphan-Pool eines Knotens (Ben, 23.10.2026). Ergebnis in out.json."""
    warten = um_ms / 1000 - jetzt()
    if warten > MEMPOOL_MAX_WARTEN_S:
        schreiben_json(out, {"status": "zu frueh gestartet, %d min bis zur lesung" % (warten // 60)})
        print("%s zu frueh gestartet" % rolle)
        return 1
    if warten > 0:
        await schlafen(warten)
    try:
        ziele = familien_lesen(cov_sha) if cov_sha else {}
        rpc, takt, kn = await verbinden(rolle, partner)
        les = Leser(rpc, takt)
        info = await les.rufe("get_info")
        r = await les.rufe("get_mempool_entries", {"includeOrphanPool": True, "filterTransactionPool": False})
        meta = dict(mempool_auswerten(r, ziele), **kn, status="gelesen", gelesen_utc=iso_ms(int(jetzt() * 1000)),
                    synchron=feld(info, "isSynced"), datenform=les.form)
        try:
            await rpc.disconnect()
        except Exception:                                # noqa: BLE001
            pass
    except Exception as exc:                             # noqa: BLE001
        meta = {"status": "fehler, %s" % type(exc).__name__, "meldung": ohne_adresse(str(exc))[:300]}
    schreiben_json(out, meta)
    print("%s mempool %s: eintraege %s, orphans %s, je familie %s" % (
        rolle, meta["status"], meta.get("eintraege", ""), meta.get("orphans", ""),
        json.dumps(meta.get("familien", {}))))
    return 0 if meta["status"] == "gelesen" else 1


def schreiben_json(basis, meta):
    os.makedirs(os.path.dirname(basis) or ".", exist_ok=True)
    with open(basis + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


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
    cov = (meta.get("covenant") or {}).pop("tx_liste", None)
    if cov is not None:
        with open(basis + "-covenant.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COV_SPALTEN)
            w.writeheader()
            w.writerows(cov)
    with open(basis + ".csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(zeilen[0]) if zeilen else SPALTEN)
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
    cov = list(dict.fromkeys(c for z in (z1[:1] + z2[:1]) for c in z if c.startswith("cov_")))
    spalten = ["minute_utc", "k1_voll", "k1_bloecke", "k1_angenommen", "k1_angenommen_pro_s",
               "k2_voll", "k2_bloecke", "k2_angenommen", "k2_angenommen_pro_s", "knoten_gleich",
               "k1_ziel_bloecke", "k2_ziel_bloecke", "ziel_anteil_pct", "k1_ziel_je", "k2_ziel_je",
               "miner_verschieden", "blau_min", "blau_max",
               ] + ["%s_%s" % (n, c) for c in cov for n in ("k1", "k2")]
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
                                          and a.get("ziel_bloecke") == b.get("ziel_bloecke")
                                          and a.get("ziel_je", "") == b.get("ziel_je", "")
                                          and all(a.get(c, "") == b.get(c, "") for c in cov)) if beide else ""),
                    "k1_ziel_bloecke": a.get("ziel_bloecke", ""), "k2_ziel_bloecke": b.get("ziel_bloecke", ""),
                    "ziel_anteil_pct": a.get("ziel_anteil_pct") or b.get("ziel_anteil_pct", ""),
                    "k1_ziel_je": a.get("ziel_je", ""), "k2_ziel_je": b.get("ziel_je", ""),
                    "miner_verschieden": a.get("miner_verschieden") or b.get("miner_verschieden", ""),
                    "blau_min": a.get("blau_min") or b.get("blau_min", ""),
                    "blau_max": a.get("blau_max") or b.get("blau_max", ""),
                    **{"%s_%s" % (n, c): r.get(c, "") for n, r in (("k1", a), ("k2", b)) for c in cov}})
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


async def lauf(von_ms, bis_ms, rolle, partner, out, ziel_sha="", kette=True, cov_sha=""):
    try:
        rpc, takt, kn = await verbinden(rolle, partner)
    except Exception as exc:                             # noqa: BLE001
        schreiben(out, [], {"status": "kein knoten, %s" % type(exc).__name__})
        return 1
    zeilen, meta = await zaehle(rpc, takt, von_ms, bis_ms, ziel_sha=ziel_sha, kette=kette, cov_sha=cov_sha)
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


class FakeCovKnoten(FakeKnoten):
    """Wie FakeKnoten, dazu ein Covenant: in jedem Kettenblock c<i> gibt eine
    Tx den Covenant-Ausgang der Vorgaenger-Tx aus und bindet ihren Ausgang 0
    wieder an die ID (Fortsetzung). Im Block daneben r<i> steht eine
    konkurrierende Ausgabe desselben Ausgangs, die nie angenommen wird."""
    CID = "c0de" * 16

    def blk(self, h):
        b = super().blk(h)
        i = int(h[1:])
        vor = {"transactionId": "cov-c%d" % (i - 1), "index": 0}
        if h[0] == "c":
            tx = {"subnetworkId": "00" * 20, "verboseData": {"transactionId": "cov-c%d" % i},
                  "inputs": [{"previousOutpoint": vor}],
                  "outputs": [{"covenant": {"authorizingInput": 0, "covenantId": self.CID}}, {}]}
        else:   # konkurrent ohne fortsetzung, nur ueber den eingang erkennbar
            tx = {"subnetworkId": "00" * 20, "verboseData": {"transactionId": "cov-r%d" % i},
                  "inputs": [{"previousOutpoint": vor}], "outputs": [{}]}
        b["transactions"].append(tx)
        return b

    async def get_virtual_chain_from_block(self, a):
        r = await super().get_virtual_chain_from_block(a)
        for e in r["acceptedTransactionIds"]:
            j = int(e["acceptingBlockHash"][1:])
            e["acceptedTransactionIds"] = e["acceptedTransactionIds"] + ["cov-c%d" % (j - 1)]
        return r


class FakeZweiKnoten(FakeCovKnoten):
    """Dazu eine zweite Familie: in jedem geraden Kettenblock eine Ausgabe,
    immer angenommen, ohne Konkurrenten."""
    CID2 = "beef" * 16

    def blk(self, h):
        b = super().blk(h)
        i = int(h[1:])
        if h[0] == "c" and i % 2 == 0:
            b["transactions"].append({
                "subnetworkId": "00" * 20, "verboseData": {"transactionId": "cov2-c%d" % i},
                "inputs": [{"previousOutpoint": {"transactionId": "cov2-c%d" % (i - 2), "index": 0}}],
                "outputs": [{"covenant": {"authorizingInput": 0, "covenantId": self.CID2}}]})
        return b

    async def get_virtual_chain_from_block(self, a):
        r = await super().get_virtual_chain_from_block(a)
        for e in r["acceptedTransactionIds"]:
            j = int(e["acceptingBlockHash"][1:])
            if (j - 1) % 2 == 0:
                e["acceptedTransactionIds"] = e["acceptedTransactionIds"] + ["cov2-c%d" % (j - 1)]
        return r


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
    # zwei benannte ziele (Ben, 17.10.2026): je ziel und zusammen, nur hashes
    z2 = hashlib.sha256(("20" + "cd" * 32 + "ac").encode()).hexdigest()
    zt = "# kommentar\nbot %s\nbuild %s\n" % (ziel, z2)
    ok("zieldatei mit zwei namen gelesen", ziele_lesen(zt) == {ziel: "bot", z2: "build"}
       and ziele_lesen(ziel) == {ziel: "ziel"} and ziele_lesen("") == {})
    zz, mz = asyncio.run(zaehle(FakeKnoten(t0, 600), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000,
                                ziel_sha=zt, kette=False))
    ok("zwei ziele, je 60 und zusammen 120 von 120", all(
        r["ziel_bloecke"] == 120 and r["ziel_anteil_pct"] == 100.0 and r["ziel_je"] == "bot 60 build 60"
        for r in zz) and mz["ziel_gesetzt"] == 2)
    try:
        ziele_lesen("bot keinhash")
        ok("zielzeile ohne sha256 bricht ab", False)
    except ValueError:
        ok("zielzeile ohne sha256 bricht ab", True)
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
    # covenant contention (Ben, 21.10.2026): je sekunde eine angenommene
    # ausgabe im kettenblock und eine konkurrierende im block daneben
    cz = "contention %s\n" % cov_hash(FakeCovKnoten.CID.upper())
    zc, mc = asyncio.run(zaehle(FakeCovKnoten(t0, 600), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000,
                                cov_sha=cz))
    ok("covenant: je minute 120 ausgaben in bloecken, 60 angenommen, 60 nie angenommen", all(
        r["cov_in_bloecken"] == 120 and r["cov_angenommen"] == 60 and r["cov_nie_angenommen"] == 60 for r in zc))
    ok("covenant: konkurrent nur ueber den eingang erkannt", mc["covenant"]["nur_ueber_eingang"] > 0)
    tl = mc["covenant"]["tx_liste"]
    an = [t for t in tl if t["angenommen"] == 1]
    ok("covenant: annahme eine sekunde nach dem ersten block",
       an and all(t["annehmender_block_ms"] - t["erster_block_ms"] == 1000 for t in an))
    ok("covenant: ohne zieldatei keine spalte", all(r["cov_in_bloecken"] == "" for r in zeilen))
    with tempfile.TemporaryDirectory() as tmp:
        schreiben(os.path.join(tmp, "k1"), zc, dict(mc, kennung="aaa"))
        with open(os.path.join(tmp, "k1-covenant.csv"), encoding="utf-8") as fh:
            cl = list(csv.DictReader(fh))
        mj = open(os.path.join(tmp, "k1.json"), encoding="utf-8").read()
        schreiben(os.path.join(tmp, "k2"), zc, dict(mc, kennung="bbb"))
        tc, zc2 = kombinieren(os.path.join(tmp, "k1"), os.path.join(tmp, "k2"))
    ok("covenant: tx-liste als csv, nicht im json", len(cl) == len(tl) and "tx_liste" not in mj)
    ok("covenant: kombiniert gleich, mit spalten", "davon gleich 3" in zc2[-1] and "k1_cov_angenommen" in tc)
    ok("covenant: die id selbst steht nirgends", FakeCovKnoten.CID not in json.dumps(mc) + tc + mj)
    # mehrere familien (Ben, 23.10.2026): je familie eigene spalten, dazu die summe
    zf = "# zwei familien\nf1 %s\nf2 %s\n" % (cov_hash(FakeCovKnoten.CID), cov_hash(FakeZweiKnoten.CID2))
    z2f, m2f = asyncio.run(zaehle(FakeZweiKnoten(t0, 600), OhneTakt(), t0 + 120000, t0 + 300000, rand_ms=60000,
                                  cov_sha=zf))
    ok("familien: f1 120/60/60, f2 30/30/0, summe 150/90/60 je minute", all(
        (r["cov_f1_in_bloecken"], r["cov_f1_angenommen"], r["cov_f1_nie_angenommen"]) == (120, 60, 60)
        and (r["cov_f2_in_bloecken"], r["cov_f2_angenommen"], r["cov_f2_nie_angenommen"]) == (30, 30, 0)
        and (r["cov_in_bloecken"], r["cov_angenommen"], r["cov_nie_angenommen"]) == (150, 90, 60) for r in z2f))
    ok("familien: tx-liste traegt die familie", {t["familie"] for t in m2f["covenant"]["tx_liste"]} == {"f1", "f2"}
       and m2f["covenant"]["familien"] == ["f1", "f2"])
    with tempfile.TemporaryDirectory() as tmp:
        schreiben(os.path.join(tmp, "k1"), z2f, dict(m2f))
        schreiben(os.path.join(tmp, "k2"), z2f, dict(m2f))
        t2f, s2f = kombinieren(os.path.join(tmp, "k1"), os.path.join(tmp, "k2"))
    ok("familien: kombiniert mit k1/k2 je familie, gleich", "k2_cov_f2_angenommen" in t2f.splitlines()[0]
       and "davon gleich 3" in s2f[-1])
    # mempool samt orphans 15 min nach END (Ben, 23.10.2026)
    fam = familien_lesen(zf)
    mp = {"mempoolEntries": [
        {"isOrphan": True, "transaction": {"outputs": [{"covenant": {"covenantId": FakeCovKnoten.CID}}]}},
        {"isOrphan": True, "transaction": {"outputs": [{}]}},
        {"isOrphan": False, "transaction": {"outputs": [{"covenant": {"covenantId": FakeZweiKnoten.CID2.upper()}}]}},
        {"isOrphan": False, "transaction": {"outputs": [{}]}}]}
    ok("mempool: 4 eintraege, 2 orphans, f1 ein orphan, f2 einer wartend",
       mempool_auswerten(mp, fam) == {"eintraege": 4, "orphans": 2, "familien": {
           "f1": {"orphans": 1, "wartend": 0}, "f2": {"orphans": 0, "wartend": 1}}})
    ok("mempool: leere antwort", mempool_auswerten({"mempoolEntries": []}, fam)["eintraege"] == 0)
    with tempfile.TemporaryDirectory() as tmp:
        geschlafen = []

        async def schlaf(s):
            geschlafen.append(s)
        rc = asyncio.run(mempool_lauf(1000 * (1000 + MEMPOOL_MAX_WARTEN_S + 60), "k1", "", os.path.join(tmp, "m"),
                                      zf, jetzt=lambda: 1000.0, schlafen=schlaf))
        mz = json.load(open(os.path.join(tmp, "m.json"), encoding="utf-8"))
    ok("mempool: zu frueh gestartet bricht ab, ohne zu schlafen", rc == 1 and not geschlafen
       and mz["status"].startswith("zu frueh"))
    import contextlib
    fk2, alt2 = fake_kaspa(), (sys.modules.get("kaspa"), Takt.__init__.__defaults__)
    sys.modules["kaspa"], Takt.__init__.__defaults__ = fk2, (0.01,)
    puf = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(puf):
            rcm = asyncio.run(mempool_lauf(0, "k1", os.path.join(tmp, "p.json"), os.path.join(tmp, "m"), zf))
            mtext = open(os.path.join(tmp, "m.json"), encoding="utf-8").read()
    finally:
        Takt.__init__.__defaults__ = alt2[1]
        if alt2[0] is None:
            sys.modules.pop("kaspa", None)
        else:
            sys.modules["kaspa"] = alt2[0]
    mj2 = json.loads(mtext)
    ok("mempool gegen erfundenen knoten: gelesen, nur kennung, keine adresse",
       rcm == 0 and mj2["status"] == "gelesen" and re.fullmatch(r"[0-9a-f]{10}", mj2.get("kennung", ""))
       and adressfrei(mtext + puf.getvalue()) and "beispiel" not in mtext + puf.getvalue())
    for schlecht in ("F1 %s" % ("a" * 64), "a %s\na %s" % ("a" * 64, "b" * 64)):
        try:
            familien_lesen(schlecht)
            ok("familienname geprueft: %r" % schlecht[:8], False)
        except ValueError:
            ok("familienname geprueft: %r" % schlecht[:8], True)
    datei = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "messung", "tn10", "nach", "fenster.txt")
    if os.path.exists(datei):
        with open(datei, encoding="utf-8") as fh:
            v, b, _nb = fenster_lesen(fh.read())
        ok("fensterdatei lesbar, %s bis %s" % (v, b), utc_ms(v) < utc_ms(b))
    ok("fenster mit kommentarzeile", fenster_lesen("# kommentar, mit worten\n2026-10-08T20:02:00Z\n"
                                                    "2026-10-08T20:13:00Z\n") == ("2026-10-08T20:02:00Z",
                                                                                    "2026-10-08T20:13:00Z", False))
    ok("fenster nur bloecke", fenster_lesen("2026-10-08T20:02:00Z\n2026-10-08T20:13:00Z\nnur-bloecke\n")[2])
    # Bens Regel 15.10.2026: vom knoten nur die zehnstellige kennung in log und
    # artefakt, auch wenn der knoten mit seiner adresse im fehlertext scheitert
    import contextlib
    fk, alt = fake_kaspa(fehler_bei="get_block_dag_info"), (sys.modules.get("kaspa"), Takt.__init__.__defaults__)
    sys.modules["kaspa"], Takt.__init__.__defaults__ = fk, (0.01,)
    puffer = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(puffer):
            rc = asyncio.run(lauf(utc_ms("2026-10-08T20:02:00Z"), utc_ms("2026-10-08T20:13:00Z"), "k1",
                                  os.path.join(tmp, "p.json"), os.path.join(tmp, "k1")))
            texte = {n: open(os.path.join(tmp, n), encoding="utf-8").read() for n in ("k1.csv", "k1.json")}
    finally:
        Takt.__init__.__defaults__ = alt[1]
        if alt[0] is None:
            sys.modules.pop("kaspa", None)
        else:
            sys.modules["kaspa"] = alt[0]
    m = json.loads(texte["k1.json"])
    alles = texte["k1.csv"] + texte["k1.json"] + puffer.getvalue()
    ok("lauf gegen erfundenen knoten: nur kennung, nie host oder ip in dateien und ausgabe",
       rc == 1 and fk.zustand["hosts"] and adressfrei(alles) and "beispiel" not in alles
       and re.fullmatch(r"[0-9a-f]{10}", m.get("kennung", "")) is not None
       and "[knoten]" in " ".join(m.get("meldungen", [])))
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
    ap.add_argument("--covenant-datei", default="", help="datei mit dem sha256 der covenant-id, nie die id")
    ap.add_argument("--mempool-um", default="", help="utc-zeit, zu der der mempool samt orphans gelesen wird")
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
    if a.mempool_um:
        cov = ""
        if a.covenant_datei and os.path.exists(a.covenant_datei):
            with open(a.covenant_datei, encoding="utf-8") as fh:
                cov = fh.read()
        return asyncio.run(mempool_lauf(utc_ms(a.mempool_um), a.rolle, a.partner, a.out, cov))
    von, bis, nur = a.von, a.bis, a.nur_bloecke
    if a.fenster:
        with open(a.fenster, encoding="utf-8") as fh:
            von, bis, nb = fenster_lesen(fh.read())
        nur = nur or nb
    ziel = ""
    if a.ziel_datei and os.path.exists(a.ziel_datei):
        with open(a.ziel_datei, encoding="utf-8") as fh:
            ziel = fh.read()
    cov = ""
    if a.covenant_datei and os.path.exists(a.covenant_datei):
        with open(a.covenant_datei, encoding="utf-8") as fh:
            cov = fh.read()
    return asyncio.run(lauf(utc_ms(von), utc_ms(bis), a.rolle, a.partner, a.out, ziel, not nur, cov))


if __name__ == "__main__":
    sys.exit(main())
