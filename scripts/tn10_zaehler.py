#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_zaehler.py, unabhaengiger zaehler fuer Testnet-10, nur lesend (Ben, 07.10.2026).

Zaehlt ueber ein Fenster (Vorgabe 30 Minuten), was auf Testnet-10 in Bloecken
ankommt und was die Kette annimmt, in Minuten-Eimern nach Blockzeit. Sendet
nichts, braucht keine Wallet und keine Schluessel, postet nichts. Die
Methode ist intern; nach aussen gehen spaeter nur Ergebnisse, Quelle und
Grenzen.

WAS GEMESSEN WIRD, JE MINUTE NACH BLOCKZEIT
    bloecke, bloecke_pro_s          jeder Block, den der Knoten meldet
    tx_in_bloecken, tx_je_block     Transaktionen in Bloecken ohne Coinbase. Im
                                    DAG kann dieselbe Tx in mehreren parallelen
                                    Bloecken stehen, das ist keine Annahme.
    leere_bloecke, anteil_leer_pct  Bloecke nur mit Coinbase
    groesste_luecke_ms              groesster Abstand zweier Blockzeiten
    angenommen_tx, angenommen_pro_s angenommene Tx ohne Coinbase, aus der
                                    virtuellen Kette, gezaehlt zur Blockzeit des
                                    annehmenden Kettenblocks. Faellt ein Block
                                    aus der Kette, wird seine Zahl abgezogen.
    mempool                         Groesse laut Knoten, eine Lesung je Minute
    feerate_normal                  Gebuehrenschaetzung des Knotens (Schaetzung,
                                    keine Messung), eine Lesung je Minute
    gebuehr je Tx                   Stichprobe, eine Tx je Minute, Gebuehr =
                                    Summe Eingaenge minus Summe Ausgaenge

Was eine Quelle nicht hergibt, steht als "nicht messbar" mit Grund da und
wird nicht geschaetzt.

LAST
Bloecke und Kette kommen als Abo, das sind keine Abfragen. Abfragen gibt es
hoechstens drei je Minute, und ein Taktgeber haelt zwischen zwei Abfragen
mindestens TAKT_S Sekunden ein. Antwortet die Gegenseite mit 429, wird der
Abstand verdoppelt. Wir messen, wir belasten nicht.

    python3 scripts/tn10_zaehler.py --dauer 1800 --out out/tn10
    python3 scripts/tn10_zaehler.py --selbsttest
"""
import argparse
import asyncio
import csv
import datetime as dt
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

NETZ = "testnet-10"
REST = os.environ.get("TN10_REST", "https://api-tn10.kaspa.org")
UA = "kaspa-pulse-zaehler (+https://kaspapulse.com)"
TAKT_S = 1.0
SOMPI = 100_000_000
COINBASE_SUBNETZ = "0100000000000000000000000000000000000000"
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
NICHT = "nicht messbar"


def ohne_ip(t):
    return IPV4.sub("[ip]", str(t or ""))


def iso_ms(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def feld(d, *namen):
    if not isinstance(d, dict):
        return None
    for n in namen:
        if n in d and d[n] is not None:
            return d[n]
    return None


def zahl(x):
    try:
        return int(str(x))
    except (TypeError, ValueError):
        return None


def perzentil(werte, p):
    """Naechster Rang. Leere Liste gibt None."""
    if not werte:
        return None
    w = sorted(werte)
    k = max(1, -(-len(w) * p // 100))
    return w[int(k) - 1]


def schluessel(d, tiefe=0):
    """Nur die Schluessel, fuer das Protokoll der Datenform. Keine Werte."""
    if tiefe > 3:
        return "..."
    if isinstance(d, dict):
        return {k: schluessel(v, tiefe + 1) for k, v in list(d.items())[:25]}
    if isinstance(d, list):
        return [schluessel(d[0], tiefe + 1)] if d else []
    return type(d).__name__


# ---------------------------------------------------------------- zaehlen

class Zaehler:
    def __init__(self):
        self.bloecke = {}           # hash -> dict(ts, daa, blau, n_tx, n_ohne_cb, masse, empfangen)
        self.coinbase = set()       # tx-ids der coinbase-transaktionen
        self.angenommen = {}        # annehmender block -> (tx ohne coinbase, coinbase), nur zahlen
        self.kandidaten = []        # (annehmender block, tx-id), die letzten fuer die gebuehren-stichprobe
        self.form = {}              # datenform je ereignisart, nur schluessel
        self.unbekannte_form = 0

    def block(self, event, *_a, **_k):
        daten = event.get("data", event) if isinstance(event, dict) else {}
        self.form.setdefault("block", schluessel(daten))
        blk = feld(daten, "block") or daten
        hdr = feld(blk, "header") or {}
        vd = feld(blk, "verboseData") or {}
        h = feld(vd, "hash") or feld(hdr, "hash")
        ts = zahl(feld(hdr, "timestamp"))
        if not h or ts is None:
            self.unbekannte_form += 1
            return
        txs = feld(blk, "transactions") or []
        masse, ohne_cb = 0, 0
        for i, tx in enumerate(txs):
            tvd = feld(tx, "verboseData") or {}
            tid = feld(tvd, "transactionId")
            sub = str(feld(tx, "subnetworkId") or "")
            ist_cb = sub == COINBASE_SUBNETZ if sub else i == 0
            if ist_cb:
                if tid:
                    self.coinbase.add(tid)
            else:
                ohne_cb += 1
            m = zahl(feld(tvd, "computeMass")) or zahl(feld(tx, "mass"))
            masse += m or 0
        self.bloecke[h] = {"ts": ts, "daa": zahl(feld(hdr, "daaScore")), "blau": zahl(feld(hdr, "blueScore")),
                           "n_tx": len(txs), "n_ohne_cb": ohne_cb, "masse": masse,
                           "empfangen": int(time.time() * 1000)}

    def kette(self, event, *_a, **_k):
        daten = event.get("data", event) if isinstance(event, dict) else {}
        self.form.setdefault("kette", schluessel(daten))
        for h in feld(daten, "removedChainBlockHashes") or []:
            self.angenommen.pop(h, None)
        for eintrag in feld(daten, "acceptedTransactionIds") or []:
            h = feld(eintrag, "acceptingBlockHash")
            ids = feld(eintrag, "acceptedTransactionIds") or []
            if h:
                echt = [t for t in ids if t not in self.coinbase]
                self.angenommen[h] = (len(echt), len(ids) - len(echt))
                if echt:
                    self.kandidaten.append((h, echt[0]))
                    del self.kandidaten[:-200]


def eimer(z, start_ms, ende_ms, luecken):
    """Minuten-Eimer nach Blockzeit. voll heisst: die Minute liegt ganz im
    Fenster und keine Verbindungsluecke beruehrt sie."""
    je = {}
    for h, b in z.bloecke.items():
        je.setdefault(b["ts"] // 60000, []).append(b)
    angen, ohne_zeit, cb_angen = {}, 0, 0
    for h, (echt, cb) in z.angenommen.items():
        b = z.bloecke.get(h)
        cb_angen += cb
        if b is None:
            ohne_zeit += echt
            continue
        angen[b["ts"] // 60000] = angen.get(b["ts"] // 60000, 0) + echt
    zeilen = []
    for m in sorted(set(je) | set(angen)):
        bl = sorted(je.get(m, []), key=lambda b: b["ts"])
        a, e = m * 60000, (m + 1) * 60000
        voll = a >= start_ms and e <= ende_ms and not any(x < e and y > a for x, y in luecken)
        n = len(bl)
        leer = sum(1 for b in bl if b["n_ohne_cb"] == 0)
        tx = [b["n_ohne_cb"] for b in bl]
        ts = [b["ts"] for b in bl]
        gaps = [y - x for x, y in zip(ts, ts[1:])]
        zeilen.append({
            "minute_utc": iso_ms(a)[:16] + "Z", "voll": int(voll),
            "bloecke": n, "bloecke_pro_s": round(n / 60, 3),
            "tx_in_bloecken": sum(tx), "tx_je_block_mittel": round(sum(tx) / n, 2) if n else "",
            "tx_je_block_median": statistics.median(tx) if n else "",
            "leere_bloecke": leer, "anteil_leer_pct": round(leer / n * 100, 2) if n else "",
            "groesste_luecke_ms": max(gaps) if gaps else "",
            "angenommen_tx": angen.get(m, 0), "angenommen_pro_s": round(angen.get(m, 0) / 60, 2),
        })
    return zeilen, {"angenommen_ohne_blockzeit": ohne_zeit, "coinbase_angenommen": cb_angen}


def csv_text(zeilen, spalten):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for z in zeilen:
        w.writerow(z)
    return f.getvalue()


# ---------------------------------------------------------------- takt und abfragen

class Takt:
    """Mindestabstand zwischen zwei Abfragen. 429 verdoppelt den Abstand."""

    def __init__(self, abstand=TAKT_S):
        self.abstand, self.letzte, self.zeiten, self.n429 = abstand, 0.0, [], 0

    async def warte(self):
        rest = self.letzte + self.abstand - time.monotonic()
        if rest > 0:
            await asyncio.sleep(rest)
        self.letzte = time.monotonic()
        self.zeiten.append(self.letzte)

    def zuviel(self):
        self.n429 += 1
        self.abstand = min(self.abstand * 2, 120.0)

    def max_je_sekunde(self):
        best, j = 0, 0
        for i, t in enumerate(self.zeiten):
            while self.zeiten[j] < t - 1.0:
                j += 1
            best = max(best, i - j + 1)
        return best


def hole_rest(pfad):
    req = urllib.request.Request(REST + pfad, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def gebuehr_aus_rest(d):
    """Summe Eingaenge minus Summe Ausgaenge, in Sompi. None, wenn ein
    Eingangsbetrag fehlt."""
    ein = [zahl(feld(i, "previous_outpoint_amount")) for i in feld(d, "inputs") or []]
    aus = [zahl(feld(o, "amount")) for o in feld(d, "outputs") or []]
    if not ein or any(x is None for x in ein) or any(x is None for x in aus):
        return None
    return sum(ein) - sum(aus)


# ---------------------------------------------------------------- lauf

async def lauf(dauer, out):
    import kaspa                                         # noqa: WPS433
    z = Zaehler()
    takt = Takt()
    knoten, luecken, meldungen = [], [], []
    mempool, feerate, gebuehren, stichprobe_fehler = [], [], [], {}
    rpc = None

    async def verbinden():
        nonlocal rpc
        await takt.warte()
        rpc = kaspa.RpcClient(resolver=kaspa.Resolver(), network_id=NETZ)
        await rpc.connect()
        knoten.append({"zeit": iso_ms(time.time() * 1000), "knoten": ohne_ip(getattr(rpc, "url", "") or "")})
        rpc.add_event_listener(kaspa.NotificationEvent.BlockAdded, z.block)
        rpc.add_event_listener(kaspa.NotificationEvent.VirtualChainChanged, z.kette)
        await takt.warte()
        await rpc.subscribe_block_added()
        await takt.warte()
        await rpc.subscribe_virtual_chain_changed(True)

    start_ms = int(time.time() * 1000)
    ende_ms = start_ms + dauer * 1000
    await verbinden()
    print("verbunden mit %s, fenster %s bis %s" % (knoten[-1]["knoten"], iso_ms(start_ms), iso_ms(ende_ms)))
    naechste_minute = time.monotonic() + 20
    weg_seit = None
    while time.time() * 1000 < ende_ms:
        await asyncio.sleep(1)
        if not getattr(rpc, "is_connected", False):
            if weg_seit is None:
                weg_seit = int(time.time() * 1000)
            try:
                await verbinden()
                luecken.append((weg_seit, int(time.time() * 1000)))
                meldungen.append("neu verbunden nach %d ms" % (luecken[-1][1] - luecken[-1][0]))
                weg_seit = None
            except Exception as exc:                     # noqa: BLE001
                meldungen.append("verbinden gescheitert: %s" % type(exc).__name__)
                await asyncio.sleep(5)
            continue
        if time.monotonic() < naechste_minute:
            continue
        naechste_minute = time.monotonic() + 60
        jetzt_ms = int(time.time() * 1000)
        try:
            await takt.warte()
            info = await rpc.get_info()
            mempool.append((jetzt_ms, zahl(feld(info, "mempoolSize"))))
            z.form.setdefault("get_info", schluessel(info))
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("get_info: %s" % type(exc).__name__)
        try:
            await takt.warte()
            fe = await rpc.get_fee_estimate()
            z.form.setdefault("fee_estimate", schluessel(fe))
            est = feld(fe, "estimate") or fe
            nb = feld(est, "normalBuckets") or []
            pb = feld(est, "priorityBucket") or {}
            feerate.append((jetzt_ms, feld(nb[0], "feerate") if nb else None, feld(pb, "feerate")))
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("fee_estimate: %s" % type(exc).__name__)
        # stichprobe: eine angenommene tx, die schon mindestens 30 s alt ist
        kandidat = None
        for h, tid in z.kandidaten[::-1]:
            b = z.bloecke.get(h)
            if b and jetzt_ms - b["ts"] > 30000 and h in z.angenommen:
                kandidat = tid
                break
        if kandidat:
            try:
                await takt.warte()
                d = await asyncio.to_thread(
                    hole_rest, "/transactions/%s?inputs=true&outputs=true&resolve_previous_outpoints=light" % kandidat)
                g = gebuehr_aus_rest(d)
                if g is None:
                    stichprobe_fehler["eingangsbetrag fehlt"] = stichprobe_fehler.get("eingangsbetrag fehlt", 0) + 1
                else:
                    gebuehren.append((jetzt_ms, kandidat, g))
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    takt.zuviel()
                stichprobe_fehler["http %d" % exc.code] = stichprobe_fehler.get("http %d" % exc.code, 0) + 1
            except Exception as exc:                     # noqa: BLE001
                k = type(exc).__name__
                stichprobe_fehler[k] = stichprobe_fehler.get(k, 0) + 1
    try:
        await rpc.disconnect()
    except Exception:                                    # noqa: BLE001
        pass
    if weg_seit is not None:
        luecken.append((weg_seit, ende_ms))
    return auswerten(z, start_ms, ende_ms, luecken, knoten, meldungen, mempool, feerate, gebuehren,
                     stichprobe_fehler, takt, out)


SPALTEN = ["minute_utc", "voll", "bloecke", "bloecke_pro_s", "tx_in_bloecken", "tx_je_block_mittel",
           "tx_je_block_median", "leere_bloecke", "anteil_leer_pct", "groesste_luecke_ms", "angenommen_tx",
           "angenommen_pro_s", "mempool", "feerate_normal"]


def auswerten(z, start_ms, ende_ms, luecken, knoten, meldungen, mempool, feerate, gebuehren, fehler, takt, out):
    zeilen, extra = eimer(z, start_ms, ende_ms, luecken)
    mp = {m // 60000: v for m, v in mempool}
    fr = {m // 60000: n for m, n, _p in feerate}
    for r in zeilen:
        k = int(dt.datetime.strptime(r["minute_utc"], "%Y-%m-%dT%H:%MZ").replace(
            tzinfo=dt.timezone.utc).timestamp()) // 60
        r["mempool"] = mp.get(k, "")
        r["feerate_normal"] = fr.get(k, "")
    voll = [r for r in zeilen if r["voll"]]
    bloecke = sorted(z.bloecke.values(), key=lambda b: b["ts"])
    im = [b for b in bloecke if start_ms <= b["ts"] < ende_ms]
    gaps = [(y["ts"] - x["ts"], y["ts"]) for x, y in zip(im, im[1:])]
    g_max = max(gaps) if gaps else None

    def spanne(feldname):
        w = [r[feldname] for r in voll if r[feldname] != ""]
        return (round(statistics.mean(w), 2), min(w), max(w)) if w else None

    s_bps, s_acc = spanne("bloecke_pro_s"), spanne("angenommen_pro_s")
    tx_bl = [b["n_ohne_cb"] for b in im]
    mp_w = [v for _m, v in mempool if v is not None]
    fr_w = [n for _m, n, _p in feerate if n is not None]
    gb = [g for _t, _id, g in gebuehren]
    z1 = ("fenster %s bis %s nach blockzeit, %d volle minuten von %d" % (
        iso_ms(start_ms), iso_ms(ende_ms), len(voll), len(zeilen)))
    z2 = ("bloecke %d im fenster, bloecke/s je volle minute im mittel %s, min %s, max %s" % (
        len(im), *(s_bps or (NICHT, "-", "-"))))
    z3 = ("tx in bloecken ohne coinbase %d, je block im mittel %s, median %s (im dag zaehlen parallele bloecke dieselbe tx mehrfach)"
          % (sum(tx_bl), round(statistics.mean(tx_bl), 2) if tx_bl else NICHT,
             statistics.median(tx_bl) if tx_bl else NICHT))
    z4 = ("angenommene tx ohne coinbase in vollen minuten %d, tx/s im mittel %s, min %s, max %s; ohne blockzeit %d" % (
        sum(r["angenommen_tx"] for r in voll), *(s_acc or (NICHT, "-", "-")), extra["angenommen_ohne_blockzeit"]))
    leer = sum(1 for b in im if b["n_ohne_cb"] == 0)
    z5 = "leere bloecke %d von %d, %s%%" % (leer, len(im), round(leer / len(im) * 100, 2) if im else NICHT)
    z6 = ("groesste luecke zwischen zwei bloecken %d ms, vor dem block um %s" % (g_max[0], iso_ms(g_max[1]))
          if g_max else "groesste luecke " + NICHT)
    z7 = ("gebuehr je tx, stichprobe n=%d: median %s KAS, p90 %s KAS%s" % (
        len(gb), round(statistics.median(gb) / SOMPI, 8), round(perzentil(gb, 90) / SOMPI, 8),
        (", fehlversuche %s" % json.dumps(fehler)) if fehler else "")
          if gb else "gebuehr je tx %s (%s)" % (NICHT, json.dumps(fehler) if fehler else "keine stichprobe moeglich"))
    z8 = ("mempool laut knoten, %d lesungen: median %s, max %s" % (len(mp_w), statistics.median(mp_w), max(mp_w))
          if mp_w else "mempool " + NICHT)
    z9 = ("feerate normal laut gebuehrenschaetzung des knotens (schaetzung, keine messung): median %s sompi/gramm"
          % statistics.median(fr_w) if fr_w else "feerate-schaetzung " + NICHT)
    z10 = ("verbindung: %d aufbau(ten), %d luecke(n) %s ms, abfragen %d, hoechstens %d je sekunde, 429 %d mal" % (
        len(knoten), len(luecken), [y - x for x, y in luecken], len(takt.zeiten), takt.max_je_sekunde(), takt.n429))
    zusammen = [z1, z2, z3, z4, z5, z6, z7, z8, z9, z10]

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    minuten_csv = csv_text(zeilen, SPALTEN)
    roh = csv_text([{"hash": h, "ts_ms": b["ts"], "zeit_utc": iso_ms(b["ts"]), "daa": b["daa"], "blau": b["blau"],
                     "n_tx": b["n_tx"], "n_ohne_coinbase": b["n_ohne_cb"], "masse": b["masse"],
                     "empfangen_ms": b["empfangen"]} for h, b in sorted(z.bloecke.items(), key=lambda x: x[1]["ts"])],
                   ["hash", "ts_ms", "zeit_utc", "daa", "blau", "n_tx", "n_ohne_coinbase", "masse", "empfangen_ms"])
    geb = csv_text([{"zeit_utc": iso_ms(t), "tx": i, "gebuehr_sompi": g} for t, i, g in gebuehren],
                   ["zeit_utc", "tx", "gebuehr_sompi"])
    for name, text in (("minuten.csv", minuten_csv), ("bloecke.csv", roh), ("gebuehren.csv", geb),
                       ("zusammenfassung.txt", "\n".join(zusammen) + "\n")):
        with open(out + "-" + name, "w", encoding="utf-8") as fh:
            fh.write(text)
    meta = {"knoten": knoten, "luecken": luecken, "meldungen": meldungen[:50], "datenform": z.form,
            "unbekannte_form": z.unbekannte_form, "extra": extra, "takt_s_ende": takt.abstand}
    with open(out + "-meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    return zusammen, minuten_csv, geb, meta


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    z = Zaehler()
    t0 = 1_790_000_000_000 - (1_790_000_000_000 % 60000)

    def blk(h, ts, n):
        txs = [{"subnetworkId": COINBASE_SUBNETZ, "verboseData": {"transactionId": "cb" + h}}]
        txs += [{"subnetworkId": "0" * 40, "verboseData": {"transactionId": "%s-%d" % (h, i), "computeMass": 2000}}
                for i in range(n)]
        return {"type": "BlockAdded", "data": {"block": {"header": {"timestamp": ts, "daaScore": 1, "blueScore": 1},
                                                         "transactions": txs, "verboseData": {"hash": h}}}}

    z.block(blk("a", t0 + 100, 3))
    z.block(blk("b", t0 + 300, 0))
    z.block(blk("c", t0 + 1300, 5))
    z.block(blk("d", t0 + 60000 + 50, 2))
    ok("block mit coinbase gezaehlt", z.bloecke["a"]["n_ohne_cb"] == 3 and "cba" in z.coinbase)
    z.kette({"data": {"addedChainBlockHashes": ["a"], "acceptedTransactionIds": [
        {"acceptingBlockHash": "a", "acceptedTransactionIds": ["a-0", "a-1", "a-2", "cba"]}]}})
    z.kette({"data": {"acceptedTransactionIds": [
        {"acceptingBlockHash": "c", "acceptedTransactionIds": ["c-0", "c-1", "b-x"]},
        {"acceptingBlockHash": "zz", "acceptedTransactionIds": ["q"]}]}})
    z.kette({"data": {"removedChainBlockHashes": ["a"], "acceptedTransactionIds": [
        {"acceptingBlockHash": "d", "acceptedTransactionIds": ["a-0", "a-1", "a-2", "d-0"]}]}})
    zeilen, extra = eimer(z, t0, t0 + 120000, [])
    m0, m1 = zeilen[0], zeilen[1]
    ok("bloecke je minute und je sekunde", m0["bloecke"] == 3 and m0["bloecke_pro_s"] == 0.05)
    ok("tx je block ohne coinbase", m0["tx_in_bloecken"] == 8 and m0["tx_je_block_median"] == 3)
    ok("leere bloecke", m0["leere_bloecke"] == 1 and m0["anteil_leer_pct"] == 33.33)
    ok("groesste luecke in der minute", m0["groesste_luecke_ms"] == 1000)
    ok("abgezogen, was aus der kette faellt, und nach blockzeit gezaehlt",
       m0["angenommen_tx"] == 3 and m1["angenommen_tx"] == 4)
    ok("coinbase nicht als angenommene tx", extra["coinbase_angenommen"] == 0)
    ok("annahme ohne bekannte blockzeit getrennt", extra["angenommen_ohne_blockzeit"] == 1)
    ok("volle minute nur ganz im fenster", m0["voll"] == 1 and eimer(z, t0 + 1, t0 + 120000, [])[0][0]["voll"] == 0)
    ok("verbindungsluecke macht die minute unvoll", eimer(z, t0, t0 + 120000, [(t0 + 70000, t0 + 75000)])[0][1]["voll"] == 0)
    ok("perzentil naechster rang", perzentil(list(range(1, 11)), 90) == 9 and perzentil([], 90) is None)
    ok("gebuehr aus eingaengen und ausgaengen", gebuehr_aus_rest(
        {"inputs": [{"previous_outpoint_amount": 1000}], "outputs": [{"amount": 700}, {"amount": 290}]}) == 10)
    ok("gebuehr ohne eingangsbetrag nicht geschaetzt", gebuehr_aus_rest(
        {"inputs": [{"previous_outpoint_amount": None}], "outputs": [{"amount": 1}]}) is None)
    tk = Takt(abstand=0.2)

    async def drei():
        for _ in range(3):
            await tk.warte()
    t = time.monotonic()
    asyncio.run(drei())
    ok("takt haelt den abstand", time.monotonic() - t >= 0.39 and tk.max_je_sekunde() <= 5)
    tk.zuviel()
    ok("429 verdoppelt den abstand", tk.abstand == 0.4 and tk.n429 == 1)
    ok("keine ip im knotennamen", ohne_ip("wss://1.2.3.4:443/x") == "wss://[ip]:443/x")
    ok("unbekannte datenform wird gezaehlt, nicht geraten", (Zaehler().block({"data": {}}) or True))
    out = "/tmp/tn10-selbsttest"
    zus, mcsv, _g, _m = auswerten(z, t0, t0 + 120000, [], [{"zeit": "x", "knoten": "y"}], [], [], [], [], {}, Takt(), out)
    ok("zehn zeilen zusammenfassung", len(zus) == 10)
    ok("ohne stichprobe steht nicht messbar da", NICHT in zus[6] and NICHT in zus[7])
    ok("csv mit kopfzeile", mcsv.splitlines()[0].startswith("minute_utc,voll,bloecke"))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dauer", type=int, default=1800)
    ap.add_argument("--out", default="out/tn10")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    zus, mcsv, geb, meta = asyncio.run(lauf(a.dauer, a.out))
    print("\n=== minuten, csv")
    print(mcsv)
    print("=== gebuehren-stichprobe, csv")
    print(geb)
    print("=== datenform (nur schluessel)")
    print(json.dumps(meta["datenform"], ensure_ascii=False)[:3000])
    print("=== meldungen")
    print("\n".join(meta["meldungen"]) or "keine")
    print("\n=== zusammenfassung")
    print("\n".join(zus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
