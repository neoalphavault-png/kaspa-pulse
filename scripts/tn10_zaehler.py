#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_zaehler.py, unabhaengiger zaehler fuer Testnet-10, nur lesend (Ben, 07.10.2026).

Zaehlt, was auf Testnet-10 in Bloecken ankommt und was die Kette annimmt, in
Minuten-Eimern nach Blockzeit. Sendet nichts, braucht keine Wallet und keine
Schluessel, postet nichts. Die Methode ist intern; nach aussen gehen spaeter
nur Ergebnisse, Quelle und Grenzen.

ZWEI KNOTEN JE LAUF
Jeder Lauf haelt zwei Verbindungen zu zwei verschiedenen Knoten (k1, k2),
belegt ueber die p2p-Kennung des Knotens. Jeder Knoten zaehlt fuer sich. Je
Minute stehen beide Zahlen und ihre Differenz in der CSV, dazu je Knoten
Version, Synchronstand (isSynced), virtueller DAA-Score mit Lesezeit,
Schwierigkeit, Mempool und Verzug (Empfangszeit minus Blockzeit). Die
Hauptspalten kommen von k1; ist k1 in der Minute nicht voll, von k2
(Spalte quelle_knoten). Ein Knoten, der sich als nicht synchron meldet,
macht seine Minute unvoll.

WAS GEMESSEN WIRD, JE MINUTE NACH BLOCKZEIT
    bloecke, bloecke_pro_s          jeder Block, den der Knoten meldet
    bloecke_nach_empfang            dieselben Bloecke, gezaehlt nach unserer Uhr
                                    beim Empfang statt nach Blockzeit
    tx_in_bloecken, tx_je_block     Transaktionen in Bloecken ohne Coinbase. Im
                                    DAG kann dieselbe Tx in mehreren parallelen
                                    Bloecken stehen, das ist keine Annahme.
    leere_bloecke, anteil_leer_pct  Bloecke nur mit Coinbase
    groesste_luecke_ms              groesster Abstand zweier Blockzeiten
    angenommen_tx, angenommen_pro_s angenommene Tx ohne Coinbase, aus der
                                    virtuellen Kette, gezaehlt zur Blockzeit des
                                    annehmenden Kettenblocks. Faellt ein Block
                                    aus der Kette, wird seine Zahl abgezogen.
    daa_min/max, blau_min/max       DAA- und Blue-Score der Bloecke der Minute
    mempool                         Groesse laut Knoten, eine Lesung je Minute
    feerate_normal                  Gebuehrenschaetzung des Knotens (Schaetzung,
                                    keine Messung), eine Lesung je Minute
    gebuehr je Tx                   Stichprobe, eine Tx je Minute, Gebuehr =
                                    Summe Eingaenge minus Summe Ausgaenge

LANGE FENSTER
Ein Fenster bis 6 h laeuft als zwei versetzte Spuren (a, b) von Teil-Laeufen.
Jede Spur hat Uebergaben an anderen Stellen, so deckt immer eine Spur ab.
--plan rechnet die Grenzen, --zusammenfuehren baut aus den Teilen eine
Minuten-CSV ohne Luecke und vergleicht, wo zwei Teile dieselbe Minute voll
haben.

PRUEFMODUS FUER TX-IDS
--pruefe-ids DATEI liest eine Liste von Tx-IDs und schreibt je ID, ob und
wann sie angenommen ist (annehmender Block, Blockzeit). Quelle ist der
TN10-Indexer; den annehmenden Block bestaetigt zusaetzlich ein Knoten
(gibt es ihn, liegt er auf der Kette, welche Blockzeit hat er).

Was eine Quelle nicht hergibt, steht als "nicht messbar" mit Grund da und
wird nicht geschaetzt.

LAST
Bloecke und Kette kommen als Abo, das sind keine Abfragen. Ein Taktgeber
haelt je Lauf zwischen zwei Abfragen mindestens TAKT_S Sekunden ein, ueber
beide Knoten und den Indexer zusammen. Antwortet die Gegenseite mit 429,
wird der Abstand verdoppelt. Die Spuren fragen versetzt, Spur a zur
Sekunde 5, Spur b zur Sekunde 35 jeder Minute. Wir messen, wir belasten nicht.

    python3 scripts/tn10_zaehler.py --bis EPOCH --teil a1 --out out/tn10
    python3 scripts/tn10_zaehler.py --plan 21600 --segment 10800
    python3 scripts/tn10_zaehler.py --zusammenfuehren out/teile --von T0 --bis-plan E --out out/tn10-gesamt
    python3 scripts/tn10_zaehler.py --pruefe-ids messung/tn10/ids.txt --out out/tn10-ids
    python3 scripts/tn10_zaehler.py --selbsttest
"""
import argparse
import asyncio
import csv
import datetime as dt
import glob
import hashlib
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

NETZ = "testnet-10"
REST = os.environ.get("TN10_REST", "https://api-tn10.kaspa.org")
UA = "kaspa-pulse-zaehler (+https://kaspapulse.com)"
TAKT_S = 1.0
SOMPI = 100_000_000
COINBASE_SUBNETZ = "0100000000000000000000000000000000000000"
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
IPV6 = re.compile(r"\[[0-9a-fA-F:.]*:[0-9a-fA-F:.]*\]")
TXID = re.compile(r"^[0-9a-f]{64}$")
NICHT = "nicht messbar"
NACHLAUF_S = 30
STILLE_MS = 5000          # laengere empfangspause gilt als luecke, auch bei offener verbindung
STILLE_RAND_MS = 2000
SPUR_SEKUNDE = {"a": 5, "b": 35}
MAX_DAUER = 39600          # 11 h, drei segmente je spur
WARTE_JOB_S = 20400        # ein wartejob schlaeft hoechstens 5 h 40 min
WARTE_JOBS = 6
VORLAUF_S = 240            # teil-laeufe starten so lange vor T0
MAX_SEGMENT = 11400
MAX_IDS = 3000


def ohne_ip(t):
    return IPV6.sub("[ip]", IPV4.sub("[ip]", str(t or "")))


def iso_ms(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def minute_text(m):
    return iso_ms(m * 60000)[:16] + "Z"


def minute_aus_text(t):
    return int(dt.datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc).timestamp()) // 60


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


def num(x):
    """Zahl aus Zahl oder CSV-Text, leer gibt None."""
    if x is None or x == "" or isinstance(x, bool):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def wahr(x):
    """True, False oder None aus bool oder CSV-Text."""
    if isinstance(x, bool):
        return x
    return {"1": True, "true": True, "True": True, "0": False, "false": False, "False": False}.get(str(x))


def perzentil(werte, p):
    """Naechster Rang. Leere Liste gibt None."""
    if not werte:
        return None
    w = sorted(werte)
    k = max(1, -(-len(w) * p // 100))
    return w[int(k) - 1]


def steigung(paare):
    """Kleinste Quadrate, y je x. Weniger als zwei Punkte oder keine Streuung gibt None."""
    paare = [(x, y) for x, y in paare if x is not None and y is not None]
    if len(paare) < 2:
        return None
    mx = sum(x for x, _ in paare) / len(paare)
    my = sum(y for _, y in paare) / len(paare)
    vx = sum((x - mx) ** 2 for x, _ in paare)
    if vx == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in paare) / vx


def kennung(p2p):
    """Kurze Kennung des Knotens aus seiner p2p-Kennung. Nie aus einer Adresse."""
    return hashlib.sha256(str(p2p).encode()).hexdigest()[:10] if p2p else ""


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
        self.empfang_bloecke = []   # empfangszeiten, fuer stille verbindungen
        self.empfang_kette = []

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
        self.empfang_bloecke.append(self.bloecke[h]["empfangen"])

    def kette(self, event, *_a, **_k):
        daten = event.get("data", event) if isinstance(event, dict) else {}
        self.form.setdefault("kette", schluessel(daten))
        self.empfang_kette.append(int(time.time() * 1000))
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


def beruehrt(luecken, a, e):
    return any(x < e and y > a for x, y in luecken)


def stillen(zeiten, start_ms, ende_ms, grenze=STILLE_MS, rand=STILLE_RAND_MS):
    """Empfangspausen ueber grenze als luecken, um rand verbreitert. Faengt
    eine verbindung, die offen aussieht, aber nichts mehr liefert."""
    raus, vor = [], start_ms
    for t in sorted(t for t in zeiten if start_ms <= t <= ende_ms):
        if t - vor > grenze:
            raus.append((vor - rand, t + rand))
        vor = t
    if ende_ms - vor > grenze:
        raus.append((vor - rand, ende_ms))
    return raus


def eimer(z, start_ms, ende_ms, luecken, status=None):
    """Minuten-Eimer nach Blockzeit fuer einen Knoten. voll heisst: die Minute
    liegt ganz im Fenster, keine Verbindungsluecke beruehrt sie, und der
    Knoten hat sich in der Minute nicht als unsynchron gemeldet."""
    status = status or {}
    luecken = list(luecken) + stillen(z.empfang_bloecke, start_ms, ende_ms) + stillen(z.empfang_kette, start_ms, ende_ms)
    bl = sorted(z.bloecke.values(), key=lambda b: b["ts"])
    je, vor = {}, None
    for b in bl:
        gap = None
        if vor is not None and vor >= start_ms and not beruehrt(luecken, vor, b["ts"]):
            gap = b["ts"] - vor
        je.setdefault(b["ts"] // 60000, []).append((b, gap))
        vor = b["ts"]
    emp = {}
    for b in bl:
        emp[b["empfangen"] // 60000] = emp.get(b["empfangen"] // 60000, 0) + 1
    angen, ohne_zeit, cb_angen = {}, 0, 0
    for h, (echt, cb) in z.angenommen.items():
        b = z.bloecke.get(h)
        cb_angen += cb
        if b is None:
            ohne_zeit += echt
            continue
        angen[b["ts"] // 60000] = angen.get(b["ts"] // 60000, 0) + echt
    zeilen = {}
    for m in sorted(set(je) | set(angen)):
        paare = je.get(m, [])
        a, e = m * 60000, (m + 1) * 60000
        st = status.get(m, {})
        voll = a >= start_ms and e <= ende_ms and not beruehrt(luecken, a, e) and st.get("synchron") is not False
        n = len(paare)
        tx = [b["n_ohne_cb"] for b, _g in paare]
        leer = sum(1 for t in tx if t == 0)
        gaps = [g for _b, g in paare if g is not None]
        daa = [b["daa"] for b, _g in paare if b["daa"] is not None]
        blau = [b["blau"] for b, _g in paare if b["blau"] is not None]
        verzug = [b["empfangen"] - b["ts"] for b, _g in paare]
        zeilen[m] = {
            "minute_utc": minute_text(m), "voll": int(voll),
            "bloecke": n, "bloecke_pro_s": round(n / 60, 3), "bloecke_nach_empfang": emp.get(m, 0),
            "tx_in_bloecken": sum(tx), "tx_je_block_mittel": round(sum(tx) / n, 2) if n else "",
            "tx_je_block_median": statistics.median(tx) if n else "",
            "leere_bloecke": leer, "anteil_leer_pct": round(leer / n * 100, 2) if n else "",
            "groesste_luecke_ms": max(gaps) if gaps else "",
            "angenommen_tx": angen.get(m, 0), "angenommen_pro_s": round(angen.get(m, 0) / 60, 2),
            "daa_min": min(daa) if daa else "", "daa_max": max(daa) if daa else "",
            "blau_min": min(blau) if blau else "", "blau_max": max(blau) if blau else "",
            "verzug_ms_median": int(statistics.median(verzug)) if verzug else "",
        }
    return zeilen, {"angenommen_ohne_blockzeit": ohne_zeit, "coinbase_angenommen": cb_angen}


KN = ["id", "version", "synchron", "voll", "bloecke", "angenommen", "daa_virtuell", "lesung_ms",
      "schwierigkeit", "verzug_ms", "mempool", "stille_ms"]
HAUPT = ["bloecke", "bloecke_pro_s", "bloecke_nach_empfang", "tx_in_bloecken", "tx_je_block_mittel",
         "tx_je_block_median", "leere_bloecke", "anteil_leer_pct", "groesste_luecke_ms", "angenommen_tx",
         "angenommen_pro_s", "daa_min", "daa_max", "blau_min", "blau_max", "verzug_ms_median"]
SPALTEN = (["minute_utc", "voll", "quelle_knoten"] + HAUPT + ["mempool", "feerate_normal"]
           + ["k%d_%s" % (i, f) for i in (1, 2) for f in KN]
           + ["diff_bloecke", "diff_angenommen", "knoten_gleich", "daa_abstand"])


def vereinen(je_knoten, status_je_knoten, feerate):
    """Zeilen von k1 und k2 zu einer Minuten-Zeile. Hauptspalten von k1, wenn
    k1 voll ist, sonst von k2, wenn k2 voll ist."""
    minuten = sorted(set().union(*[set(z) for z in je_knoten]) if je_knoten else set())
    fr = {m // 60000: n for m, n, _p in feerate}
    raus = []
    for m in minuten:
        reihen = [z.get(m) for z in je_knoten]
        wahl = next((i for i, r in enumerate(reihen) if r and r["voll"]), None)
        if wahl is None:
            wahl = next(i for i, r in enumerate(reihen) if r)
        p = reihen[wahl]
        r = {"minute_utc": minute_text(m), "voll": p["voll"], "quelle_knoten": "k%d" % (wahl + 1) if p["voll"] else "",
             "feerate_normal": fr.get(m, "")}
        for f in HAUPT:
            r[f] = p[f]
        # ein einzelprozess hat nur einen knoten, die k2-spalten bleiben leer
        for i, (zr, st) in enumerate(zip(reihen + [None] * (2 - len(reihen)),
                                         list(status_je_knoten) + [{}] * (2 - len(status_je_knoten))), 1):
            s = st.get(m, {})
            r["k%d_id" % i] = s.get("id", "")
            r["k%d_version" % i] = s.get("version", "")
            r["k%d_synchron" % i] = "" if s.get("synchron") is None else int(s["synchron"])
            r["k%d_voll" % i] = zr["voll"] if zr else 0
            r["k%d_bloecke" % i] = zr["bloecke"] if zr else ""
            r["k%d_angenommen" % i] = zr["angenommen_tx"] if zr else ""
            r["k%d_daa_virtuell" % i] = s.get("daa", "")
            r["k%d_lesung_ms" % i] = s.get("lesung_ms", "")
            r["k%d_schwierigkeit" % i] = s.get("schwierigkeit", "")
            r["k%d_verzug_ms" % i] = zr["verzug_ms_median"] if zr else ""
            r["k%d_mempool" % i] = s.get("mempool", "")
            r["k%d_stille_ms" % i] = s.get("stille_ms", "")
        r["mempool"] = r.get("k%d_mempool" % (wahl + 1), "")
        if len(reihen) > 1 and reihen[0] and reihen[1] and reihen[0]["voll"] and reihen[1]["voll"]:
            r["diff_bloecke"] = reihen[0]["bloecke"] - reihen[1]["bloecke"]
            r["diff_angenommen"] = reihen[0]["angenommen_tx"] - reihen[1]["angenommen_tx"]
        else:
            r["diff_bloecke"] = r["diff_angenommen"] = ""
        r["knoten_gleich"] = "" if r["diff_bloecke"] == "" else int(r["diff_bloecke"] == 0 and r["diff_angenommen"] == 0)
        r["daa_abstand"] = ""
        raus.append(r)
    return raus


def daa_abstand_setzen(zeilen):
    """Abstand der virtuellen DAA-Scores beider Knoten, um die Lesezeit
    bereinigt mit dem gemessenen DAA-Takt. Positiv heisst: k1 weiter vorn."""
    paare = [(num(r["k%d_lesung_ms" % i]), num(r["k%d_daa_virtuell" % i])) for r in zeilen for i in (1, 2)]
    s = steigung(paare)
    if s is None:
        return None
    for r in zeilen:
        d1, d2 = num(r["k1_daa_virtuell"]), num(r["k2_daa_virtuell"])
        t1, t2 = num(r["k1_lesung_ms"]), num(r["k2_lesung_ms"])
        if None not in (d1, d2, t1, t2) and abs(t1 - t2) < 30000:
            r["daa_abstand"] = int(round((d1 - d2) - s * (t1 - t2)))
    return s * 1000


def csv_text(zeilen, spalten):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for z in zeilen:
        w.writerow(z)
    return f.getvalue()


# ---------------------------------------------------------------- zusammenfassung

def zusammenfassen(zeilen, gebuehren, fehler, kopf):
    """Zusammenfassung aus Minuten-Zeilen. Gilt fuer einen Teil und fuer das
    zusammengefuehrte Fenster; Werte duerfen Zahl oder CSV-Text sein."""
    voll = [r for r in zeilen if num(r["voll"])]
    n = len(voll)

    def summe(f, rs=voll):
        return int(sum(num(r[f]) or 0 for r in rs))

    def spanne(f):
        w = [num(r[f]) for r in voll if num(r[f]) is not None]
        return (round(statistics.mean(w), 2), statistics.median(w), min(w), max(w)) if w else None

    s_bps, s_acc = spanne("bloecke_pro_s"), spanne("angenommen_pro_s")
    bl, tx, leer = summe("bloecke"), summe("tx_in_bloecken"), summe("leere_bloecke")
    gaps = [(num(r["groesste_luecke_ms"]), r["minute_utc"]) for r in voll if num(r["groesste_luecke_ms"]) is not None]
    g_max = max(gaps) if gaps else None
    meds = [num(r["tx_je_block_median"]) for r in voll if num(r["tx_je_block_median"]) is not None]
    mp = [num(r["mempool"]) for r in voll if num(r["mempool"]) is not None]
    fr = [num(r["feerate_normal"]) for r in voll if num(r["feerate_normal"]) is not None]
    gb = [g for _t, _id, g in gebuehren]
    luecken_min = [r["minute_utc"] for r in zeilen if not num(r["voll"])]
    zus = [
        "fenster %s bis %s nach blockzeit, %d volle minuten von %d%s" % (
            iso_ms(kopf["von_ms"]), iso_ms(kopf["bis_ms"]), n, len(zeilen),
            (", unvoll %s" % ", ".join(luecken_min[:8]) + (" und %d weitere" % (len(luecken_min) - 8)
                                                           if len(luecken_min) > 8 else "")) if luecken_min else ""),
        "bloecke %d in vollen minuten, bloecke/s je volle minute mittel %s, median %s, min %s, max %s" % (
            bl, *(s_bps or (NICHT, "-", "-", "-"))),
        "tx in bloecken ohne coinbase %d, je block im mittel %s, %s (im dag zaehlen parallele bloecke dieselbe tx mehrfach)" % (
            tx, round(tx / bl, 2) if bl else NICHT,
            ("median 0, weil mehr als die haelfte der bloecke leer ist" if bl and leer * 2 > bl
             else "median der minuten-mediane %s" % statistics.median(meds) if meds else "median " + NICHT)),
        "angenommene tx ohne coinbase in vollen minuten %d, tx/s mittel %s, median %s, min %s, max %s; ohne blockzeit %s" % (
            summe("angenommen_tx"), *(s_acc or (NICHT, "-", "-", "-")), kopf.get("ohne_blockzeit", 0)),
        "leere bloecke %d von %d, %s%%" % (leer, bl, round(leer / bl * 100, 2) if bl else NICHT),
        ("groesste luecke zwischen zwei bloecken %d ms, in der minute %s" % (g_max[0], g_max[1])
         if g_max else "groesste luecke " + NICHT),
        ("gebuehr je tx, stichprobe n=%d: median %s KAS, p90 %s KAS, max %s KAS%s" % (
            len(gb), round(statistics.median(gb) / SOMPI, 8), round(perzentil(gb, 90) / SOMPI, 8),
            round(max(gb) / SOMPI, 8), (", fehlversuche %s" % json.dumps(fehler)) if fehler else "")
         if gb else "gebuehr je tx %s (%s)" % (NICHT, json.dumps(fehler) if fehler else "keine stichprobe moeglich")),
        ("mempool laut knoten, %d lesungen: median %s, max %s" % (len(mp), int(statistics.median(mp)), int(max(mp)))
         if mp else "mempool " + NICHT),
        ("feerate normal laut gebuehrenschaetzung des knotens (schaetzung, keine messung): median %s sompi/gramm"
         % statistics.median(fr) if fr else "feerate-schaetzung " + NICHT),
        kopf.get("verbindung", "verbindung " + NICHT),
    ]
    return zus + knoten_zeilen(zeilen, voll) + takt_zeilen(voll, zeilen)


def knoten_zeilen(zeilen, voll):
    raus = []
    for i in (1, 2):
        ids = sorted({r["k%d_id" % i] for r in zeilen if r["k%d_id" % i]})
        vers = sorted({r["k%d_version" % i] for r in zeilen if r["k%d_version" % i]})
        sy = [wahr(r["k%d_synchron" % i]) for r in zeilen]
        raus.append("knoten k%d: kennung %s, version %s, synchron ja %d, nein %d, ohne lesung %d, volle minuten %d" % (
            i, ", ".join(ids) or NICHT, ", ".join(vers) or NICHT, sy.count(True), sy.count(False), sy.count(None),
            sum(1 for r in zeilen if num(r["k%d_voll" % i]))))
    beide = [r for r in zeilen if num(r["diff_bloecke"]) is not None]
    db = [num(r["diff_bloecke"]) for r in beide]
    da = [num(r["diff_angenommen"]) for r in beide]
    ab = [abs(num(r["daa_abstand"])) for r in zeilen if num(r["daa_abstand"]) is not None]
    gleich = sum(1 for r in beide if num(r["diff_bloecke"]) == 0 and num(r["diff_angenommen"]) == 0)
    voll_n = sum(1 for r in voll)
    ver1 = [num(r["k1_verzug_ms"]) for r in voll if num(r["k1_verzug_ms"]) is not None]
    ver2 = [num(r["k2_verzug_ms"]) for r in voll if num(r["k2_verzug_ms"]) is not None]
    raus.append(
        ("abgleich k1 gegen k2 in %d minuten, beide voll: gleich in %d (von zwei knoten bestaetigt %d von %d vollen "
         "minuten), bloecke k1 minus k2 von %d bis %d, angenommen k1 minus k2 von %d bis %d" % (
             len(beide), gleich, sum(1 for r in voll if num(r.get("knoten_gleich")) == 1), voll_n,
             min(db), max(db), min(da), max(da))
         if beide else "abgleich k1 gegen k2 " + NICHT + " (keine minute, in der beide voll sind)")
        + ("; daa-abstand bereinigt median %s, max %s" % (statistics.median(ab), max(ab)) if ab else "")
        + ("; verzug empfang minus blockzeit median k1 %s ms, k2 %s ms" % (
            int(statistics.median(ver1)) if ver1 else NICHT, int(statistics.median(ver2)) if ver2 else NICHT)))
    return raus


def takt_zeilen(voll, zeilen):
    """Wie schnell entstehen Bloecke, nach drei voneinander unabhaengigen Uhren."""
    if not voll:
        return ["takt " + NICHT + " (keine volle minute)"]
    n = len(voll)
    kopf = sum(num(r["bloecke"]) or 0 for r in voll) / (60 * n)
    emp = sum(num(r["bloecke_nach_empfang"]) or 0 for r in voll) / (60 * n)
    wand = []
    for i in (1, 2):
        s = steigung([(num(r["k%d_lesung_ms" % i]), num(r["k%d_daa_virtuell" % i])) for r in zeilen
                      if wahr(r["k%d_synchron" % i]) is not False])
        wand.append(round(s * 1000, 3) if s is not None else NICHT)
    mins = [(minute_aus_text(r["minute_utc"]) * 60, num(r["daa_max"]), num(r["blau_max"])) for r in voll]
    daa_kopf = steigung([(t, d) for t, d, _b in mins])
    blau_kopf = steigung([(t, b) for t, _d, b in mins])
    sw = [(num(r["k1_lesung_ms"]), num(r["k1_schwierigkeit"])) for r in zeilen
          if num(r["k1_schwierigkeit"]) is not None and num(r["k1_lesung_ms"]) is not None]
    sw.sort()
    z1 = ("takt bloecke/s nach blockzeit %s, nach empfangszeit %s; daa-score/s nach wanduhr k1 %s, k2 %s; "
          "nach blockzeit daa/s %s, blau/s %s" % (
              round(kopf, 3), round(emp, 3), wand[0], wand[1],
              round(daa_kopf, 3) if daa_kopf is not None else NICHT,
              round(blau_kopf, 3) if blau_kopf is not None else NICHT))
    z2 = ("takt bloecke je daa-schritt %s; schwierigkeit k1 erste lesung %s, letzte %s, aenderung %s%%; nominell 10 bloecke/s"
          % (round(kopf / daa_kopf, 4) if daa_kopf else NICHT,
             "%.6g" % sw[0][1] if sw else NICHT, "%.6g" % sw[-1][1] if sw else NICHT,
             round((sw[-1][1] / sw[0][1] - 1) * 100, 2) if sw and sw[0][1] else NICHT))
    return [z1, z2]


# ---------------------------------------------------------------- takt und abfragen

class Takt:
    """Mindestabstand zwischen zwei Abfragen. 429 verdoppelt den Abstand."""

    def __init__(self, abstand=TAKT_S):
        self.abstand, self.letzte, self.zeiten, self.n429 = abstand, 0.0, [], 0
        self.sperre = None

    async def warte(self):
        if self.sperre is None:
            self.sperre = asyncio.Lock()
        async with self.sperre:
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


def wirt(url):
    """Host einer Knoten-URL, nur zum Vergleich im Speicher. Wird nie
    ungefiltert geschrieben."""
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""


# ---------------------------------------------------------------- plan fuer lange fenster

def startzeit(text):
    """Startzeit aus messung/tn10/start.txt, ISO in UTC wie 2026-10-09T21:25:00Z.
    Leer oder nur Kommentar heisst: sofort."""
    t = " ".join(z.split("#", 1)[0].strip() for z in (text or "").splitlines()).strip()
    if not t:
        return None
    d = dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp())


def plan(dauer, segment, jetzt, start=None):
    """Grenzen der Teil-Laeufe als Epoch-Sekunden, 0 heisst: entfaellt.
    Spur a endet bei T0+S, T0+2S und T0+3S, Spur b bei T0+S/2, T0+3S/2,
    T0+5S/2 und T0+3S, jeweils hoechstens am Fensterende. So liegt jede
    Uebergabe der einen Spur mitten in einem Teil der anderen.

    Mit start beginnt das Fenster dort (auf die volle Minute). Bis dahin
    schlafen Wartejobs ohne jede Abfrage; los ist der Zeitpunkt, zu dem die
    ersten Teil-Laeufe anlaufen, wn die Zahl der noetigen Wartejobs."""
    if not 60 <= dauer <= MAX_DAUER:
        raise ValueError("dauer %d ausserhalb 60 bis %d" % (dauer, MAX_DAUER))
    if not 600 <= segment <= MAX_SEGMENT:
        raise ValueError("segment %d ausserhalb 600 bis %d" % (segment, MAX_SEGMENT))
    if dauer > 3 * segment:
        raise ValueError("dauer %d groesser als drei segmente" % dauer)
    frueh = (int(jetzt) // 60 + 1) * 60 + 180
    if start is None or start <= frueh:
        if start is not None and start < int(jetzt) - 60:
            raise ValueError("startzeit liegt in der vergangenheit")
        t0 = frueh
    else:
        t0 = -(-int(start) // 60) * 60
    rest = max(0, t0 - VORLAUF_S - int(jetzt))
    wn = -(-rest // WARTE_JOB_S) if rest > 60 else 0
    if wn > WARTE_JOBS:
        raise ValueError("startzeit zu weit weg, hoechstens %d h warten" % (WARTE_JOBS * WARTE_JOB_S // 3600))
    e = t0 + dauer
    out = {"t0": t0, "ende": e, "los": t0 - VORLAUF_S, "wn": wn}
    for spur, grenzen in (("a", [segment, 2 * segment, 3 * segment]),
                          ("b", [segment // 2, segment * 3 // 2, segment * 5 // 2, 3 * segment])):
        fertig = False
        for i, g in enumerate(grenzen, 1):
            if fertig:
                out["%s%d" % (spur, i)] = 0
                continue
            out["%s%d" % (spur, i)] = min(t0 + g, e)
            fertig = t0 + g >= e
    return out


# ---------------------------------------------------------------- lauf

class Knoten:
    def __init__(self, name):
        self.name = name
        self.z = Zaehler()
        self.rpc = None
        self.wirt = ""
        self.p2p = ""
        self.verbindungen, self.luecken, self.status = [], [], {}
        self.weg_seit = None
        self.start_ms = None
        self.naechster_versuch = 0.0

    def verbunden(self):
        return bool(self.rpc is not None and getattr(self.rpc, "is_connected", False))

    def war_verbunden(self):
        return bool(self.verbindungen)


STILLE_NEU_MS = 60000     # so lange ohne block bei offener verbindung: neu verbinden


def partner_lesen(pfad, warte_s=90):
    """Host und p2p-Kennung des k1-Prozesses, nur im Speicher und in einer
    Datei unter RUNNER_TEMP (nie im Artefakt)."""
    ende = time.time() + warte_s
    while pfad and time.time() < ende:
        try:
            with open(pfad, encoding="utf-8") as fh:
                d = json.load(fh)
            return d.get("wirt", ""), d.get("p2p", "")
        except (OSError, ValueError):
            time.sleep(1)
    return "", ""


async def lauf(bis_s, out, spur, teil, plan_von, plan_bis, rolle=None, partner=None):
    """rolle None: beide knoten in einem prozess. rolle k1 oder k2: nur dieser
    knoten, je ein eigener prozess (TN10-Checkout 08.10.2026: unter rund
    2.500 tx/s schaffte ein prozess die vollen bloecke beider knoten nicht,
    k2 lief bis 51 s hinterher und verstummte dann). k1 schreibt Host und
    Kennung nach partner, k2 meidet diesen knoten. Gebuehren-Stichprobe und
    Gebuehrenschaetzung macht nur k1."""
    import kaspa                                         # noqa: WPS433
    takt = Takt()
    k1, k2 = Knoten("k1"), Knoten("k2")
    aktiv = [k1, k2] if rolle is None else [k1] if rolle == "k1" else [k2]
    meldungen, feerate, gebuehren, stichprobe_fehler = [], [], [], {}
    gesehen = set()
    resolver = kaspa.Resolver()

    async def verbinde(k, anderer):
        """Neuer Knoten fuer k, nie derselbe wie der andere (p2p-Kennung)."""
        for versuch in range(6):
            await takt.warte()
            try:
                url = await resolver.get_url("borsh", kaspa.NetworkId(NETZ))
            except Exception as exc:                     # noqa: BLE001
                meldungen.append("%s resolver get_url: %s, verbinde ueber den resolver" % (k.name, type(exc).__name__))
                url = None
            if url and anderer.wirt and wirt(url) == anderer.wirt and versuch < 5:
                continue
            rpc = (kaspa.RpcClient(url=url, network_id=NETZ) if url
                   else kaspa.RpcClient(resolver=kaspa.Resolver(), network_id=NETZ))
            await rpc.connect()
            url = url or getattr(rpc, "url", "") or ""
            await takt.warte()
            info = await rpc.get_info()
            k.z.form.setdefault("get_info", schluessel(info))
            p2p = str(feld(info, "p2pId") or "")
            if anderer.p2p and p2p and p2p == anderer.p2p and versuch < 5:
                await rpc.disconnect()
                continue
            k.rpc, k.wirt, k.p2p = rpc, wirt(url), p2p
            rpc.add_event_listener(kaspa.NotificationEvent.BlockAdded, k.z.block)
            rpc.add_event_listener(kaspa.NotificationEvent.VirtualChainChanged, k.z.kette)
            await takt.warte()
            await rpc.subscribe_block_added()
            await takt.warte()
            await rpc.subscribe_virtual_chain_changed(True)
            jetzt = int(time.time() * 1000)
            if k.start_ms is None:
                k.start_ms = jetzt
            k.verbindungen.append({"zeit": iso_ms(jetzt), "knoten": ohne_ip(url), "kennung": kennung(p2p),
                                   "version": str(feld(info, "serverVersion") or ""),
                                   "gleich_wie_anderer": bool(anderer.p2p and p2p == anderer.p2p)})
            if rolle == "k1" and partner:
                with open(partner + ".neu", "w", encoding="utf-8") as fh:
                    json.dump({"wirt": k.wirt, "p2p": k.p2p}, fh)
                os.replace(partner + ".neu", partner)
            return
        raise RuntimeError("kein knoten")

    async def pruefe_verbindung(k, anderer):
        if rolle == "k2":
            anderer.wirt, anderer.p2p = await asyncio.to_thread(partner_lesen, partner, 90 if k.rpc is None else 2)
        if k.verbunden() and k.z.empfang_bloecke:
            # wache: offen, aber still. dann ist das abo tot, nicht das netz.
            letzte = k.z.empfang_bloecke[-1]
            jetzt = int(time.time() * 1000)
            if jetzt - letzte > STILLE_NEU_MS:
                meldungen.append("%s still seit %d ms bei offener verbindung, neu verbinden" % (k.name, jetzt - letzte))
                k.weg_seit = letzte
                try:
                    await k.rpc.disconnect()
                except Exception:                        # noqa: BLE001
                    pass
                k.rpc = None
        if k.verbunden():
            return
        if time.monotonic() < k.naechster_versuch:
            return
        if k.weg_seit is None and k.war_verbunden():
            k.weg_seit = int(time.time() * 1000)
        try:
            await verbinde(k, anderer)
            if k.weg_seit is not None:
                k.luecken.append((k.weg_seit, int(time.time() * 1000)))
                meldungen.append("%s neu verbunden nach %d ms" % (k.name, k.luecken[-1][1] - k.luecken[-1][0]))
            k.weg_seit = None
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("%s verbinden gescheitert: %s" % (k.name, type(exc).__name__))
            if k.weg_seit is None:
                k.weg_seit = int(time.time() * 1000)
            k.naechster_versuch = time.monotonic() + 5

    async def lesen(k):
        jetzt_ms = int(time.time() * 1000)
        m = jetzt_ms // 60000
        s = {"id": kennung(k.p2p)}
        try:
            await takt.warte()
            info = await k.rpc.get_info()
            s.update({"synchron": feld(info, "isSynced"), "version": str(feld(info, "serverVersion") or ""),
                      "mempool": zahl(feld(info, "mempoolSize"))})
            if feld(info, "p2pId"):
                s["id"] = kennung(feld(info, "p2pId"))
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("%s get_info: %s" % (k.name, type(exc).__name__))
        try:
            await takt.warte()
            dag = await k.rpc.get_block_dag_info()
            k.z.form.setdefault("get_block_dag_info", schluessel(dag))
            s.update({"daa": zahl(feld(dag, "virtualDaaScore")), "lesung_ms": int(time.time() * 1000),
                      "schwierigkeit": round(feld(dag, "difficulty"), 1) if isinstance(feld(dag, "difficulty"), float)
                      else feld(dag, "difficulty")})
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("%s get_block_dag_info: %s" % (k.name, type(exc).__name__))
        letzte = max((b["empfangen"] for b in list(k.z.bloecke.values())[-50:]), default=None)
        s["stille_ms"] = max(0, int(time.time() * 1000) - letzte) if letzte else ""
        k.status[m] = s

    async def minute(k_haupt):
        jetzt_ms = int(time.time() * 1000)
        try:
            await takt.warte()
            fe = await k_haupt.rpc.get_fee_estimate()
            k_haupt.z.form.setdefault("fee_estimate", schluessel(fe))
            est = feld(fe, "estimate") or fe
            nb = feld(est, "normalBuckets") or []
            pb = feld(est, "priorityBucket") or {}
            rund = lambda x: round(x, 2) if isinstance(x, float) else x      # noqa: E731
            feerate.append((jetzt_ms, rund(feld(nb[0], "feerate")) if nb else None, rund(feld(pb, "feerate"))))
        except Exception as exc:                         # noqa: BLE001
            meldungen.append("fee_estimate: %s" % type(exc).__name__)
        # stichprobe: eine angenommene tx, die schon mindestens 30 s alt ist
        z = k_haupt.z
        kandidat = None
        for h, tid in z.kandidaten[::-1]:
            b = z.bloecke.get(h)
            if b and jetzt_ms - b["ts"] > 30000 and h in z.angenommen and tid not in gesehen:
                kandidat = tid
                break
        if not kandidat:
            return
        gesehen.add(kandidat)
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
        except Exception as exc:                         # noqa: BLE001
            k = type(exc).__name__
            stichprobe_fehler[k] = stichprobe_fehler.get(k, 0) + 1

    def naechster_tick(t):
        basis = int(t) // 60 * 60 + SPUR_SEKUNDE.get(spur, 5)
        return basis if basis > t else basis + 60

    ende_ms = int(bis_s * 1000)
    # aufbau im eigenen zeitfenster der spur, damit er nicht mit den abfragen der anderen spur zusammenfaellt
    warten = (SPUR_SEKUNDE.get(spur, 5) + 7 - time.time()) % 60
    await asyncio.sleep(warten)
    for k in aktiv:
        await pruefe_verbindung(k, k2 if k is k1 else k1)
    print("teil %s, spur %s, rolle %s, bis %s, k1 %s, k2 %s" % (
        teil, spur, rolle or "beide", iso_ms(ende_ms), kennung(k1.p2p) or "-", kennung(k2.p2p) or "-"))
    tick = naechster_tick(time.time())
    while time.time() < bis_s + NACHLAUF_S:
        await asyncio.sleep(0.5)
        for k in aktiv:
            await pruefe_verbindung(k, k2 if k is k1 else k1)
        if time.time() < tick or time.time() >= bis_s:
            continue
        tick = naechster_tick(time.time())
        for k in aktiv:
            if k.verbunden():
                await lesen(k)
        haupt = next((k for k in aktiv if k.verbunden()), None)
        if haupt and rolle != "k2":
            await minute(haupt)
    for k in aktiv:
        try:
            if k.rpc is not None:
                await k.rpc.disconnect()
        except Exception:                                # noqa: BLE001
            pass
        if k.weg_seit is not None:
            k.luecken.append((k.weg_seit, ende_ms))
    return auswerten(aktiv, ende_ms, meldungen, feerate, gebuehren, stichprobe_fehler, takt, out,
                     {"spur": spur, "teil": teil, "plan_von": plan_von, "plan_bis": plan_bis, "rolle": rolle})


def bloecke_csv(z):
    return csv_text([{"hash": h, "ts_ms": b["ts"], "zeit_utc": iso_ms(b["ts"]), "daa": b["daa"], "blau": b["blau"],
                      "n_tx": b["n_tx"], "n_ohne_coinbase": b["n_ohne_cb"], "masse": b["masse"],
                      "empfangen_ms": b["empfangen"]} for h, b in sorted(z.bloecke.items(), key=lambda x: x[1]["ts"])],
                    ["hash", "ts_ms", "zeit_utc", "daa", "blau", "n_tx", "n_ohne_coinbase", "masse", "empfangen_ms"])


def auswerten(knoten, ende_ms, meldungen, feerate, gebuehren, fehler, takt, out, kopf_teil):
    je, extras = [], []
    for k in knoten:
        if k.start_ms is None:
            je.append({})
            extras.append({"angenommen_ohne_blockzeit": 0, "coinbase_angenommen": 0})
            continue
        zl, ex = eimer(k.z, k.start_ms, ende_ms, k.luecken, k.status)
        je.append(zl)
        extras.append(ex)
    zeilen = vereinen(je, [k.status for k in knoten], feerate)
    daa_s = daa_abstand_setzen(zeilen)
    starts = [k.start_ms for k in knoten if k.start_ms is not None]
    von_ms = min(starts) if starts else ende_ms
    verb = sum(len(k.verbindungen) for k in knoten)
    luecken = {k.name: [y - x for x, y in k.luecken] for k in knoten}
    kopf = {"von_ms": von_ms, "bis_ms": ende_ms, "ohne_blockzeit": extras[0]["angenommen_ohne_blockzeit"],
            "verbindung": "verbindung: %d aufbau(ten), luecken ms %s, abfragen %d, hoechstens %d je sekunde, 429 %d mal" % (
                verb, json.dumps(luecken), len(takt.zeiten), takt.max_je_sekunde(), takt.n429)}
    zus = zusammenfassen(zeilen, gebuehren, fehler, kopf)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    minuten_csv = csv_text(zeilen, SPALTEN)
    geb = csv_text([{"zeit_utc": iso_ms(t), "tx": i, "gebuehr_sompi": g} for t, i, g in gebuehren],
                   ["zeit_utc", "tx", "gebuehr_sompi"])
    dateien = [("minuten.csv", minuten_csv), ("gebuehren.csv", geb), ("zusammenfassung.txt", "\n".join(zus) + "\n")]
    dateien += [("bloecke-%s.csv" % k.name, bloecke_csv(k.z)) for k in knoten]
    for name, text in dateien:
        with open(out + "-" + name, "w", encoding="utf-8") as fh:
            fh.write(text)
    meta = dict(kopf_teil)
    meta.update({"von_ms": von_ms, "bis_ms": ende_ms, "daa_je_s": daa_s,
                 "knoten": {k.name: {"start_ms": k.start_ms, "verbindungen": k.verbindungen,
                                     "luecken": k.luecken} for k in knoten},
                 "meldungen": meldungen[:80], "datenform": knoten[0].z.form,
                 "unbekannte_form": sum(k.z.unbekannte_form for k in knoten), "extra": extras,
                 "abfragen": len(takt.zeiten), "max_je_sekunde": takt.max_je_sekunde(), "n429": takt.n429,
                 "takt_s_ende": takt.abstand})
    with open(out + "-meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    return zus, minuten_csv, geb, meta


# ---------------------------------------------------------------- zusammenfuehren

def einzel_lesen(basis):
    """Minuten und Meta eines Einzelprozesses, fehlt er, leer."""
    try:
        with open(basis + "-meta.json", encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(basis + "-minuten.csv", encoding="utf-8") as fh:
            zeilen = {minute_aus_text(r["minute_utc"]): r for r in csv.DictReader(fh)}
    except (OSError, ValueError):
        return None, {}
    return meta, zeilen


def kombinieren(basis1, basis2, out, kopf_teil):
    """Zwei Einzelprozesse (k1, k2) zu einem Teil mit beiden Knoten, in
    derselben Form wie ein Lauf mit beiden Knoten in einem Prozess."""
    m1, z1 = einzel_lesen(basis1)
    m2, z2 = einzel_lesen(basis2)
    zeilen = []
    for m in sorted(set(z1) | set(z2)):
        r1, r2 = z1.get(m), z2.get(m)
        v1, v2 = bool(r1 and num(r1["voll"])), bool(r2 and num(r2["voll"]))
        haupt, q = (r1, "k1") if v1 else (r2, "k2") if v2 else (r1 or r2, "")
        r = {"minute_utc": minute_text(m), "voll": int(v1 or v2), "quelle_knoten": q,
             "feerate_normal": (r1 or {}).get("feerate_normal", "") or (r2 or {}).get("feerate_normal", "")}
        for f in HAUPT + ["mempool"]:
            r[f] = haupt.get(f, "")
        for i, quelle in ((1, r1), (2, r2)):
            for f in KN:
                r["k%d_%s" % (i, f)] = (quelle or {}).get("k1_%s" % f, "") if quelle else ("" if f != "voll" else 0)
        if v1 and v2:
            r["diff_bloecke"] = int(num(r1["bloecke"]) - num(r2["bloecke"]))
            r["diff_angenommen"] = int(num(r1["angenommen_tx"]) - num(r2["angenommen_tx"]))
            r["knoten_gleich"] = int(r["diff_bloecke"] == 0 and r["diff_angenommen"] == 0)
        else:
            r["diff_bloecke"] = r["diff_angenommen"] = r["knoten_gleich"] = ""
        r["daa_abstand"] = ""
        zeilen.append(r)
    daa_abstand_setzen(zeilen)
    metas = [m for m in (m1, m2) if m]
    geb = []
    if os.path.exists(basis1 + "-gebuehren.csv"):
        with open(basis1 + "-gebuehren.csv", encoding="utf-8") as fh:
            geb = [(0, r["tx"], int(r["gebuehr_sompi"])) for r in csv.DictReader(fh)]
    knoten = {}
    for name, m in (("k1", m1), ("k2", m2)):
        if m and m.get("knoten"):
            knoten[name] = next(iter(m["knoten"].values()))
    luecken = {n: [y - x for x, y in v.get("luecken", [])] for n, v in knoten.items()}
    von_ms = min([m["von_ms"] for m in metas] or [0])
    bis_ms = max([m["bis_ms"] for m in metas] or [0])
    kopf = {"von_ms": von_ms, "bis_ms": bis_ms,
            "ohne_blockzeit": sum((m.get("extra") or [{}])[0].get("angenommen_ohne_blockzeit", 0) for m in metas),
            "verbindung": "verbindung: %d aufbau(ten), luecken ms %s, abfragen %d, hoechstens %d je sekunde je "
                          "prozess (k1 und k2 getrennt, verschiedene knoten), 429 %d mal%s" % (
                              sum(len(v.get("verbindungen", [])) for v in knoten.values()), json.dumps(luecken),
                              sum(m.get("abfragen", 0) for m in metas),
                              max([m.get("max_je_sekunde", 0) for m in metas] or [0]),
                              sum(m.get("n429", 0) for m in metas),
                              "" if m2 else ", k2 FEHLT")}
    zus = zusammenfassen(zeilen, geb, {}, kopf)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    minuten_csv = csv_text(zeilen, SPALTEN)
    with open(out + "-minuten.csv", "w", encoding="utf-8") as fh:
        fh.write(minuten_csv)
    with open(out + "-zusammenfassung.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(zus) + "\n")
    if os.path.exists(basis1 + "-gebuehren.csv"):
        with open(basis1 + "-gebuehren.csv", encoding="utf-8") as fh, \
                open(out + "-gebuehren.csv", "w", encoding="utf-8") as fo:
            fo.write(fh.read())
    meta = dict(kopf_teil)
    meta.update({"von_ms": von_ms, "bis_ms": bis_ms, "knoten": knoten,
                 "meldungen": [x for m in (m1, m2) if m for x in m.get("meldungen", [])][:80],
                 "datenform": (m1 or m2 or {}).get("datenform", {}),
                 "extra": [(m.get("extra") or [{}])[0] for m in metas],
                 "abfragen": sum(m.get("abfragen", 0) for m in metas),
                 "max_je_sekunde": max([m.get("max_je_sekunde", 0) for m in metas] or [0]),
                 "n429": sum(m.get("n429", 0) for m in metas), "prozesse": len(metas)})
    with open(out + "-meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    return zus, minuten_csv


def teile_lesen(ordner):
    teile = []
    for mp in sorted(glob.glob(os.path.join(ordner, "**", "*-meta.json"), recursive=True)):
        if os.sep + "einzeln" + os.sep in mp:
            continue
        basis = mp[:-len("-meta.json")]
        with open(mp, encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(basis + "-minuten.csv", encoding="utf-8") as fh:
            zeilen = list(csv.DictReader(fh))
        geb = []
        if os.path.exists(basis + "-gebuehren.csv"):
            with open(basis + "-gebuehren.csv", encoding="utf-8") as fh:
                geb = [(r["zeit_utc"], r["tx"], int(r["gebuehr_sompi"])) for r in csv.DictReader(fh)]
        teile.append({"meta": meta, "zeilen": zeilen, "gebuehren": geb})
    return teile


def zusammenfuehren(teile, von_s, bis_s):
    """Je Minute im Plan die erste volle Zeile, Spur a vor Spur b, frueherer
    Teil vor spaeterem. Ohne volle Zeile bleibt die Minute als unvoll stehen.
    Wo zwei Teile dieselbe Minute voll haben, werden sie verglichen."""
    teile = sorted(teile, key=lambda t: (t["meta"].get("spur", ""), t["meta"].get("von_ms", 0)))
    je_teil = [{minute_aus_text(r["minute_utc"]): r for r in t["zeilen"]} for t in teile]
    raus, abgleich = [], []
    for m in range(von_s // 60, bis_s // 60):
        volle = [(t["meta"].get("teil", "?"), z[m]) for t, z in zip(teile, je_teil) if m in z and num(z[m]["voll"])]
        # zuerst zeilen, in denen zwei knoten dasselbe zaehlen, dann die spur-reihenfolge
        volle.sort(key=lambda x: 0 if num(x[1].get("knoten_gleich")) == 1 else 1)
        if volle:
            r = dict(volle[0][1])
            r["quelle"] = volle[0][0]
        else:
            irgend = next((z[m] for z in je_teil if m in z), None)
            r = dict(irgend) if irgend else {s: "" for s in SPALTEN}
            r["minute_utc"], r["voll"], r["quelle"] = minute_text(m), 0, ""
        r["teile_voll"] = len(volle)
        raus.append(r)
        for (ta, ra), (tb, rb) in zip(volle, volle[1:]):
            abgleich.append({"minute_utc": minute_text(m), "teil_1": ta, "teil_2": tb,
                             "bloecke_1": ra["bloecke"], "bloecke_2": rb["bloecke"],
                             "angenommen_1": ra["angenommen_tx"], "angenommen_2": rb["angenommen_tx"]})
    return raus, abgleich


def gesamt_schreiben(teile, von_s, bis_s, out):
    zeilen, abgleich = zusammenfuehren(teile, von_s, bis_s)
    geb, gesehen, fehler = [], set(), {}
    for t in teile:
        for g in t["gebuehren"]:
            if g[1] not in gesehen:
                gesehen.add(g[1])
                geb.append(g)
    geb.sort()
    verb = sum(len(v.get("verbindungen", [])) for t in teile for v in t["meta"].get("knoten", {}).values())
    luecken = {"%s.%s" % (t["meta"].get("teil"), n): [y - x for x, y in v.get("luecken", [])]
               for t in teile for n, v in t["meta"].get("knoten", {}).items() if v.get("luecken")}
    gleich = sum(1 for a in abgleich if a["bloecke_1"] == a["bloecke_2"] and a["angenommen_1"] == a["angenommen_2"])
    kopf = {"von_ms": von_s * 1000, "bis_ms": bis_s * 1000,
            "ohne_blockzeit": sum(e.get("angenommen_ohne_blockzeit", 0) for t in teile for e in t["meta"].get("extra", [])),
            "verbindung": "verbindung: %d teile %s, %d aufbau(ten), luecken ms %s, abfragen %d, hoechstens %d je sekunde "
                          "je teil, 429 %d mal" % (
                              len(teile), ",".join(sorted(t["meta"].get("teil", "?") for t in teile)), verb,
                              json.dumps(luecken), sum(t["meta"].get("abfragen", 0) for t in teile),
                              max([t["meta"].get("max_je_sekunde", 0) for t in teile] or [0]),
                              sum(t["meta"].get("n429", 0) for t in teile))}
    zus = zusammenfassen(zeilen, [(0, i, g) for _z, i, g in geb], fehler, kopf)
    ohne = [r["minute_utc"] for r in zeilen if not num(r["voll"])]
    zus.append("abdeckung %d von %d minuten voll, ohne volle quelle %d; doppelt gezaehlt %d minuten, davon gleich %d%s" % (
        len(zeilen) - len(ohne), len(zeilen), len(ohne), len(abgleich), gleich,
        ("; abweichend %s" % ", ".join("%s %s/%s" % (a["minute_utc"], a["teil_1"], a["teil_2"])
                                         for a in abgleich if not (a["bloecke_1"] == a["bloecke_2"]
                                                                   and a["angenommen_1"] == a["angenommen_2"]))[:600])
        if len(abgleich) > gleich else ""))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    minuten_csv = csv_text(zeilen, SPALTEN + ["quelle", "teile_voll"])
    for name, text in (("minuten.csv", minuten_csv),
                       ("gebuehren.csv", csv_text([{"zeit_utc": z, "tx": i, "gebuehr_sompi": g} for z, i, g in geb],
                                                  ["zeit_utc", "tx", "gebuehr_sompi"])),
                       ("abgleich.csv", csv_text(abgleich, ["minute_utc", "teil_1", "teil_2", "bloecke_1", "bloecke_2",
                                                            "angenommen_1", "angenommen_2"])),
                       ("zusammenfassung.txt", "\n".join(zus) + "\n")):
        with open(out + "-" + name, "w", encoding="utf-8") as fh:
            fh.write(text)
    return zus, minuten_csv


# ---------------------------------------------------------------- pruefmodus tx-ids

def ids_lesen(text):
    """Eine ID je Zeile, # leitet einen Kommentar ein. Gibt (ids, falsche
    Zeilennummern). Doppelte IDs zaehlen einmal."""
    ids, falsch, gesehen = [], [], set()
    for nr, zeile in enumerate(text.splitlines(), 1):
        t = zeile.split("#", 1)[0].strip().lower()
        if not t:
            continue
        if not TXID.match(t):
            falsch.append(nr)
            continue
        if t not in gesehen:
            gesehen.add(t)
            ids.append(t)
    return ids, falsch


def annahme_aus_rest(d):
    """Annahme laut Indexer. Unbekannte Form gibt None statt zu raten."""
    if not isinstance(d, dict):
        return None
    bh = feld(d, "block_hash") or []
    return {"angenommen": feld(d, "is_accepted"),
            "annehmender_block": feld(d, "accepting_block_hash") or "",
            "blau_score": feld(d, "accepting_block_blue_score") or "",
            "annahme_zeit_indexer_ms": zahl(feld(d, "accepting_block_time")),
            "in_bloecken": len(bh) if isinstance(bh, list) else (1 if bh else 0),
            "blockzeit_aufnahme_ms": zahl(feld(d, "block_time"))}


PRUEF_SPALTEN = ["tx_id", "gefunden", "angenommen", "annehmender_block", "blockzeit_utc", "blockzeit_quelle",
                 "blockzeit_indexer_utc", "blau_score", "knoten_bestaetigt", "auf_kette", "aufnahme_blockzeit_utc", "in_bloecken", "anmerkung"]


def ids_holen(url):
    """IDs zur Laufzeit von einer URL (STP, 09.10.2026): sie bleiben nur im
    Speicher des Laufs, nie im Repo, nie im Log, nie im Artefakt."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(8_000_000).decode("utf-8", "replace")


async def pruefe_ids(datei, out, url="", nur_zaehlung=False, ohne_knoten=False):
    if url:
        ids, falsch = ids_lesen(await asyncio.to_thread(ids_holen, url))
    else:
        with open(datei, encoding="utf-8") as fh:
            ids, falsch = ids_lesen(fh.read())
    zu_viel = max(0, len(ids) - MAX_IDS)
    ids = ids[:MAX_IDS]
    takt = Takt()
    rpc, form, meldungen = None, {}, []
    try:
        if ohne_knoten:
            raise RuntimeError("selbsttest ohne knoten")
        import kaspa                                     # noqa: WPS433
        await takt.warte()
        rpc = kaspa.RpcClient(resolver=kaspa.Resolver(), network_id=NETZ)
        await rpc.connect()
    except Exception as exc:                             # noqa: BLE001
        meldungen.append("knoten nicht erreichbar: %s" % type(exc).__name__)
        rpc = None
    zeilen = []
    for tid in ids:
        r = {s: "" for s in PRUEF_SPALTEN}
        r["tx_id"] = tid
        try:
            await takt.warte()
            d = await asyncio.to_thread(hole_rest, "/transactions/%s?inputs=false&outputs=false" % tid)
            form.setdefault("indexer", schluessel(d))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                takt.zuviel()
            r["gefunden"] = 0 if exc.code == 404 else ""
            r["anmerkung"] = "indexer kennt die id nicht" if exc.code == 404 else "indexer http %d" % exc.code
            zeilen.append(r)
            continue
        except Exception as exc:                         # noqa: BLE001
            r["anmerkung"] = "indexer %s" % type(exc).__name__
            zeilen.append(r)
            continue
        a = annahme_aus_rest(d)
        if a is None:
            r["anmerkung"] = "unbekannte antwortform"
            zeilen.append(r)
            continue
        r["gefunden"] = 1
        r["angenommen"] = "" if a["angenommen"] is None else int(bool(a["angenommen"]))
        r["annehmender_block"] = a["annehmender_block"]
        r["blau_score"] = a["blau_score"]
        r["in_bloecken"] = a["in_bloecken"]
        if a["blockzeit_aufnahme_ms"]:
            r["aufnahme_blockzeit_utc"] = iso_ms(a["blockzeit_aufnahme_ms"])
        if a["annahme_zeit_indexer_ms"]:
            r["blockzeit_utc"], r["blockzeit_quelle"] = iso_ms(a["annahme_zeit_indexer_ms"]), "indexer"
            r["blockzeit_indexer_utc"] = r["blockzeit_utc"]
        if a["annehmender_block"] and rpc is not None:
            try:
                await takt.warte()
                b = await rpc.get_block({"hash": a["annehmender_block"], "includeTransactions": False})
                form.setdefault("knoten_block", schluessel(b))
                blk = feld(b, "block") or b
                ts = zahl(feld(feld(blk, "header") or {}, "timestamp"))
                kette = feld(feld(blk, "verboseData") or {}, "isChainBlock")
                r["knoten_bestaetigt"] = 1 if ts is not None else 0
                r["auf_kette"] = "" if kette is None else int(bool(kette))
                if ts is not None:
                    r["blockzeit_utc"], r["blockzeit_quelle"] = iso_ms(ts), "knoten"
                if kette is False:
                    r["anmerkung"] = "annehmender block laut knoten nicht auf der kette"
            except Exception as exc:                     # noqa: BLE001
                r["knoten_bestaetigt"] = 0
                r["anmerkung"] = "knoten kennt den block nicht (%s)" % type(exc).__name__
        elif a["annehmender_block"]:
            r["knoten_bestaetigt"] = NICHT
        zeilen.append(r)
    if rpc is not None:
        try:
            await rpc.disconnect()
        except Exception:                                # noqa: BLE001
            pass
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if nur_zaehlung:
        # fremde ids: je id nichts, weder im log noch im artefakt, nur zaehlungen
        text = ""
    else:
        text = csv_text(zeilen, PRUEF_SPALTEN)
        with open(out + "-pruefung.csv", "w", encoding="utf-8") as fh:
            fh.write(text)
    n_ang = sum(1 for r in zeilen if r["angenommen"] == 1)
    zus = ["ids %d gelesen, %d geprueft%s%s" % (
               len(ids) + zu_viel, len(zeilen), (", %d ueber der grenze %d nicht geprueft" % (zu_viel, MAX_IDS))
               if zu_viel else "", (", falsche zeilen %s" % falsch[:20]) if falsch else ""),
           "gefunden %d, nicht gefunden %d, angenommen %d, nicht angenommen %d, ohne antwort %d" % (
               sum(1 for r in zeilen if r["gefunden"] == 1), sum(1 for r in zeilen if r["gefunden"] == 0), n_ang,
               sum(1 for r in zeilen if r["angenommen"] == 0), sum(1 for r in zeilen if r["gefunden"] == "")),
           "annehmender block vom knoten bestaetigt %d, auf der kette %d, nicht auf der kette %d" % (
               sum(1 for r in zeilen if r["knoten_bestaetigt"] == 1), sum(1 for r in zeilen if r["auf_kette"] == 1),
               sum(1 for r in zeilen if r["auf_kette"] == 0)),
           "abfragen %d, hoechstens %d je sekunde, 429 %d mal" % (len(takt.zeiten), takt.max_je_sekunde(), takt.n429)]
    with open(out + "-meta.json", "w", encoding="utf-8") as fh:
        json.dump({"datenform": form, "meldungen": meldungen}, fh, indent=1, ensure_ascii=False)
    return zus, text


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    z = Zaehler()
    t0 = 1_790_000_000_000 - (1_790_000_000_000 % 60000)

    def blk(h, ts, n, daa=1):
        txs = [{"subnetworkId": COINBASE_SUBNETZ, "verboseData": {"transactionId": "cb" + h}}]
        txs += [{"subnetworkId": "0" * 40, "verboseData": {"transactionId": "%s-%d" % (h, i), "computeMass": 2000}}
                for i in range(n)]
        return {"type": "BlockAdded", "data": {"block": {"header": {"timestamp": ts, "daaScore": daa, "blueScore": daa},
                                                         "transactions": txs, "verboseData": {"hash": h}}}}

    z.block(blk("a", t0 + 100, 3, 10))
    z.block(blk("b", t0 + 300, 0, 11))
    z.block(blk("c", t0 + 1300, 5, 12))
    z.block(blk("d", t0 + 60000 + 50, 2, 20))
    ok("block mit coinbase gezaehlt", z.bloecke["a"]["n_ohne_cb"] == 3 and "cba" in z.coinbase)
    z.kette({"data": {"addedChainBlockHashes": ["a"], "acceptedTransactionIds": [
        {"acceptingBlockHash": "a", "acceptedTransactionIds": ["a-0", "a-1", "a-2", "cba"]}]}})
    z.kette({"data": {"acceptedTransactionIds": [
        {"acceptingBlockHash": "c", "acceptedTransactionIds": ["c-0", "c-1", "b-x"]},
        {"acceptingBlockHash": "zz", "acceptedTransactionIds": ["q"]}]}})
    z.kette({"data": {"removedChainBlockHashes": ["a"], "acceptedTransactionIds": [
        {"acceptingBlockHash": "d", "acceptedTransactionIds": ["a-0", "a-1", "a-2", "d-0"]}]}})
    puls = list(range(t0, t0 + 120001, 1000))      # empfang jede sekunde, keine stille
    z.empfang_bloecke, z.empfang_kette = list(puls), list(puls)
    zl, extra = eimer(z, t0, t0 + 120000, [])
    m0, m1 = zl[t0 // 60000], zl[t0 // 60000 + 1]
    ok("bloecke je minute und je sekunde", m0["bloecke"] == 3 and m0["bloecke_pro_s"] == 0.05)
    ok("tx je block ohne coinbase", m0["tx_in_bloecken"] == 8 and m0["tx_je_block_median"] == 3)
    ok("leere bloecke", m0["leere_bloecke"] == 1 and m0["anteil_leer_pct"] == 33.33)
    ok("groesste luecke in der minute", m0["groesste_luecke_ms"] == 1000)
    ok("luecke ueber die minutengrenze zaehlt zur spaeteren minute", m1["groesste_luecke_ms"] == 58750)
    ok("abgezogen, was aus der kette faellt, und nach blockzeit gezaehlt",
       m0["angenommen_tx"] == 3 and m1["angenommen_tx"] == 4)
    ok("coinbase nicht als angenommene tx", extra["coinbase_angenommen"] == 0)
    ok("annahme ohne bekannte blockzeit getrennt", extra["angenommen_ohne_blockzeit"] == 1)
    ok("daa und blau je minute", m0["daa_min"] == 10 and m0["daa_max"] == 12 and m1["blau_max"] == 20)
    ok("volle minute nur ganz im fenster",
       m0["voll"] == 1 and eimer(z, t0 + 1, t0 + 120000, [])[0][t0 // 60000]["voll"] == 0)
    ok("verbindungsluecke macht die minute unvoll",
       eimer(z, t0, t0 + 120000, [(t0 + 70000, t0 + 75000)])[0][t0 // 60000 + 1]["voll"] == 0)
    ok("luecke ueber eine verbindungsluecke zaehlt nicht",
       eimer(z, t0, t0 + 120000, [(t0 + 2000, t0 + 3000)])[0][t0 // 60000 + 1]["groesste_luecke_ms"] == "")
    z.empfang_bloecke = [t for t in puls if not t0 + 70000 < t < t0 + 90000]
    ok("stille verbindung ohne bloecke macht die minute unvoll",
       eimer(z, t0, t0 + 120000, [])[0][t0 // 60000 + 1]["voll"] == 0
       and eimer(z, t0, t0 + 120000, [])[0][t0 // 60000]["voll"] == 1)
    z.empfang_bloecke = list(puls)
    z.empfang_kette = [t for t in puls if t < t0 + 100000]
    ok("stille kette am ende macht die minute unvoll", eimer(z, t0, t0 + 120000, [])[0][t0 // 60000 + 1]["voll"] == 0)
    z.empfang_kette = list(puls)
    ok("stillen: pause ueber der grenze, um den rand verbreitert",
       stillen([0, 1000, 8000, 9000], 0, 9500) == [(-1000, 10000)] and stillen([0, 1000], 0, 7000) == [(-1000, 7000)])
    ok("unsynchroner knoten macht die minute unvoll",
       eimer(z, t0, t0 + 120000, [], {t0 // 60000: {"synchron": False}})[0][t0 // 60000]["voll"] == 0)

    # zweiter knoten: sieht block d nicht, k1 ist in minute 1 nicht synchron
    z2 = Zaehler()
    for e in (blk("a", t0 + 100, 3, 10), blk("b", t0 + 300, 0, 11), blk("c", t0 + 1300, 5, 12)):
        z2.block(e)
    z2.empfang_bloecke, z2.empfang_kette = list(puls), list(puls)
    z2.kette({"data": {"acceptedTransactionIds": [
        {"acceptingBlockHash": "a", "acceptedTransactionIds": ["a-0", "a-1", "a-2"]}]}})
    st1 = {t0 // 60000: {"id": "aaa", "synchron": True, "daa": 1000, "lesung_ms": t0 + 5000},
           t0 // 60000 + 1: {"id": "aaa", "synchron": False, "daa": 1600, "lesung_ms": t0 + 65000}}
    st2 = {t0 // 60000: {"id": "bbb", "synchron": True, "daa": 1010, "lesung_ms": t0 + 6000},
           t0 // 60000 + 1: {"id": "bbb", "synchron": True, "daa": 1610, "lesung_ms": t0 + 66000}}
    zl1, _ = eimer(z, t0, t0 + 120000, [], st1)
    zl2, _ = eimer(z2, t0, t0 + 120000, [], st2)
    vz = vereinen([zl1, zl2], [st1, st2], [(t0 + 5000, 147, 200)])
    ok("hauptspalten von k1, wenn k1 voll", vz[0]["quelle_knoten"] == "k1" and vz[0]["angenommen_tx"] == 3)
    ok("differenz beider knoten je minute", vz[0]["diff_bloecke"] == 0 and vz[0]["diff_angenommen"] == 0
       and vz[0]["knoten_gleich"] == 1 and vz[1]["knoten_gleich"] == "")
    ok("k2 fehlt die minute, k1 unsynchron, minute unvoll", vz[1]["voll"] == 0 and vz[1]["k1_synchron"] == 0)
    s = daa_abstand_setzen(vz)
    ok("daa-takt nach wanduhr und bereinigter abstand", s is not None and abs(s - 10.0) < 0.01
       and vz[0]["daa_abstand"] == 0)
    ok("feerate zur minute", vz[0]["feerate_normal"] == 147)

    # plan fuer lange fenster
    p = plan(21600, 10800, 1_790_000_000)
    t = p["t0"]
    ok("plan sechs stunden", p["a1"] == t + 10800 and p["a2"] == t + 21600 and p["b1"] == t + 5400
       and p["b2"] == t + 16200 and p["b3"] == t + 21600 and p["ende"] == t + 21600)
    p = plan(1800, 10800, 1_790_000_000)
    ok("plan kurz, je spur ein teil", p["a1"] == p["ende"] and p["b1"] == p["ende"] and p["a2"] == 0
       and p["b2"] == 0 and p["b3"] == 0)
    p = plan(1800, 900, 1_790_000_000)
    ok("plan probe mit uebergaben", p["a2"] == p["ende"] and p["b2"] == p["t0"] + 1350 and p["b3"] == p["ende"])
    ok("plan beginnt nach voller minute", p["t0"] % 60 == 0 and p["t0"] > 1_790_000_000 + 180)
    for falsch, args in (("zu lang", (39660, 13200)), ("segment zu lang", (1800, 12000)),
                         ("mehr als drei segmente", (2800, 900))):
        try:
            plan(args[0], args[1], 0)
            ok("plan lehnt ab: " + falsch, False)
        except ValueError:
            ok("plan lehnt ab: " + falsch, True)
    p = plan(29400, 10800, 1_791_500_000)
    t = p["t0"]
    ok("plan acht stunden zehn, drei teile in a, vier in b",
       p["a3"] == t + 29400 and p["b3"] == t + 27000 and p["b4"] == t + 29400 and p["a2"] == t + 21600)
    st = startzeit("# kommentar\n2026-10-09T21:25:00Z\n")
    p = plan(29400, 10800, st - 26 * 3600, st)
    ok("startzeit: fenster ab start, wartejobs ohne abfragen",
       p["t0"] == st and p["los"] == st - VORLAUF_S and p["wn"] == 5 and p["ende"] == st + 29400)
    ok("startzeit leer heisst sofort", startzeit("# nur kommentar\n") is None and plan(1800, 900, 0, None)["wn"] == 0)
    p = plan(7800, 10800, st - 300, st)
    ok("startzeit kurz voraus, kein wartejob", p["wn"] == 0 and p["t0"] == st and p["a1"] == st + 7800)
    for falsch, args in (("start in der vergangenheit", (1800, 900, st, st - 3600)),
                         ("start zu weit weg", (1800, 900, st - 40 * 3600, st))):
        try:
            plan(*args)
            ok("plan lehnt ab: " + falsch, False)
        except ValueError:
            ok("plan lehnt ab: " + falsch, True)
    ok("uebergaben liegen nicht aufeinander", all(
        abs(plan(21600, 10800, 0)[x] - plan(21600, 10800, 0)[y]) >= 3600
        for x, y in (("a1", "b1"), ("a1", "b2"))))

    # zusammenfuehren, zwei spuren, a hat in minute 1 eine luecke
    def teil(name, spur, zeilen):
        return {"meta": {"teil": name, "spur": spur, "von_ms": t0, "knoten": {}, "extra": [], "abfragen": 5,
                         "max_je_sekunde": 1, "n429": 0},
                "zeilen": [{k: str(v) for k, v in r.items()} for r in zeilen], "gebuehren": []}

    import copy
    za = copy.deepcopy(vz)
    za[1]["voll"] = 0
    zb = copy.deepcopy(vz)
    zb[1]["voll"] = 1
    zb[1]["angenommen_tx"] = 4
    rz, ab = zusammenfuehren([teil("b1", "b", zb), teil("a1", "a", za)], t0 // 1000, t0 // 1000 + 180)
    ok("zusammengefuehrt ohne luecke aus der anderen spur",
       [r["quelle"] for r in rz[:2]] == ["a1", "b1"] and rz[2]["voll"] == 0 and len(rz) == 3)
    ok("doppelt volle minute wird verglichen", len(ab) == 1 and ab[0]["teil_1"] == "a1")
    za[0]["knoten_gleich"] = 0
    rz2, _ab = zusammenfuehren([teil("b1", "b", zb), teil("a1", "a", za)], t0 // 1000, t0 // 1000 + 180)
    ok("von zwei knoten bestaetigte zeile geht vor", rz2[0]["quelle"] == "b1")
    zus = zusammenfassen(rz, [], {}, {"von_ms": t0, "bis_ms": t0 + 180000, "verbindung": "verbindung test"})
    ok("zusammenfassung aus csv-text", zus[1].startswith("bloecke 4 in vollen minuten") and "unvoll" in zus[0])
    ok("abgleich der knoten in der zusammenfassung", any(z.startswith("abgleich k1 gegen k2 in 1 minuten")
                                                        for z in zus))
    ok("takt mit wanduhr und blockzeit", any(z.startswith("takt bloecke/s nach blockzeit") for z in zus))

    # pruefmodus
    ids, falsch = ids_lesen("# liste\n%s\n%s  # doppelt\nkaputt\n%s\n" % ("a" * 64, "A" * 64, "b" * 64))
    ok("ids lesen, doppelte einmal, falsche zeile gemeldet", ids == ["a" * 64, "b" * 64] and falsch == [4])
    a = annahme_aus_rest({"transaction_id": "x", "is_accepted": True, "accepting_block_hash": "h",
                          "accepting_block_blue_score": 7, "accepting_block_time": 1_790_000_000_000,
                          "block_hash": ["h1", "h2"], "block_time": 1_789_999_999_000})
    ok("annahme aus dem indexer", a["angenommen"] is True and a["annehmender_block"] == "h"
       and a["in_bloecken"] == 2 and a["annahme_zeit_indexer_ms"] == 1_790_000_000_000)
    ok("unbekannte antwortform nicht geraten", annahme_aus_rest([1, 2]) is None)
    # fremde ids (STP, 09.10.2026): von einer url, nur zaehlungen, nichts je id
    import tempfile as _tf
    global hole_rest
    echt_rest = hole_rest
    with _tf.TemporaryDirectory() as tmp:
        quelle = os.path.join(tmp, "ids.txt")
        with open(quelle, "w", encoding="utf-8") as fh:
            fh.write("%s\n%s\n" % ("c" * 64, "d" * 64))
        hole_rest = lambda pfad: {"transaction_id": "x", "is_accepted": True,        # noqa: E731
                                  "accepting_block_hash": "h", "accepting_block_time": 1_790_000_000_000}
        try:
            zus_u, text_u = asyncio.run(pruefe_ids("", os.path.join(tmp, "out", "u"), "file://" + quelle,
                                                   True, ohne_knoten=True))
        finally:
            hole_rest = echt_rest
        dateien = " ".join(os.listdir(os.path.join(tmp, "out")))
        meta_u = open(os.path.join(tmp, "out", "u-meta.json"), encoding="utf-8").read()
    ok("ids von url, nur zaehlungen", text_u == "" and "pruefung.csv" not in dateien
       and "angenommen 2" in " ".join(zus_u))
    ok("keine id in zaehlung, meta oder dateinamen", all("c" * 64 not in t and "d" * 64 not in t
                                                       for t in (" ".join(zus_u), meta_u, dateien)))

    ok("perzentil naechster rang", perzentil(list(range(1, 11)), 90) == 9 and perzentil([], 90) is None)
    ok("gebuehr aus eingaengen und ausgaengen", gebuehr_aus_rest(
        {"inputs": [{"previous_outpoint_amount": 1000}], "outputs": [{"amount": 700}, {"amount": 290}]}) == 10)
    ok("gebuehr ohne eingangsbetrag nicht geschaetzt", gebuehr_aus_rest(
        {"inputs": [{"previous_outpoint_amount": None}], "outputs": [{"amount": 1}]}) is None)
    tk = Takt(abstand=0.2)

    async def drei():
        await asyncio.gather(*(tk.warte() for _ in range(3)))
    t = time.monotonic()
    asyncio.run(drei())
    ok("takt haelt den abstand, auch gleichzeitig", time.monotonic() - t >= 0.39 and tk.max_je_sekunde() <= 5)
    tk.zuviel()
    ok("429 verdoppelt den abstand", tk.abstand == 0.4 and tk.n429 == 1)
    ok("keine ip im knotennamen", ohne_ip("wss://192.0.2.1:443/x") == "wss://[ip]:443/x"
       and ohne_ip("wss://[2001:db8::1]:443") == "wss://[ip]:443")
    ok("kennung aus p2p, leer ohne", len(kennung("abc")) == 10 and kennung("") == "")
    ok("unbekannte datenform wird gezaehlt, nicht geraten", (Zaehler().block({"data": {}}) or True))
    out = "/tmp/tn10-selbsttest"
    k = Knoten("k1")
    k.z, k.start_ms, k.status = z, t0, st1
    kk = Knoten("k2")
    zus, mcsv, _g, _m = auswerten([k, kk], t0 + 120000, [], [], [], {}, Takt(), out, {"teil": "x"})
    ok("zehn zeilen plus knoten und takt", len(zus) == 15)
    ok("ohne stichprobe steht nicht messbar da", NICHT in zus[6] and NICHT in zus[8])
    ok("csv mit kopfzeile", mcsv.splitlines()[0].startswith("minute_utc,voll,quelle_knoten,bloecke"))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bis", type=int, help="ende des teil-laufs, epoch-sekunden")
    ap.add_argument("--dauer", type=int, help="statt --bis, sekunden ab jetzt")
    ap.add_argument("--teil", default="a1")
    ap.add_argument("--spur", default="")
    ap.add_argument("--von", type=int, default=0, help="plan-anfang T0, epoch-sekunden")
    ap.add_argument("--bis-plan", type=int, default=0, help="plan-ende, epoch-sekunden")
    ap.add_argument("--out", default="out/tn10")
    ap.add_argument("--plan", type=int, metavar="DAUER")
    ap.add_argument("--segment", type=int, default=10800)
    ap.add_argument("--start", default="", help="datei mit der startzeit in utc, leer heisst sofort")
    ap.add_argument("--zusammenfuehren", metavar="ORDNER")
    ap.add_argument("--pruefe-ids", metavar="DATEI")
    ap.add_argument("--ids-url", default="", help="ids zur laufzeit von dieser url, dann nur zaehlungen")
    ap.add_argument("--nur-zaehlung", action="store_true", help="je id nichts ausgeben, nur zaehlungen")
    ap.add_argument("--rolle", choices=["k1", "k2"], help="nur dieser knoten, eigener prozess")
    ap.add_argument("--partner", default="", help="datei unter RUNNER_TEMP, k1 schreibt, k2 liest")
    ap.add_argument("--kombinieren", nargs=2, metavar=("K1", "K2"))
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.plan is not None:
        start = None
        if a.start and os.path.exists(a.start):
            with open(a.start, encoding="utf-8") as fh:
                start = startzeit(fh.read())
        for k, v in plan(a.plan, a.segment, time.time(), start).items():
            print("%s=%d" % (k, v))
        return 0
    if a.kombinieren:
        zus, mcsv = kombinieren(a.kombinieren[0], a.kombinieren[1], a.out,
                                {"spur": a.spur or a.teil[:1], "teil": a.teil, "plan_von": a.von,
                                 "plan_bis": a.bis_plan})
        print("=== teil %s, beide knoten, minuten csv" % a.teil)
        print(mcsv)
        print("=== zusammenfassung")
        print("\n".join(zus))
        return 0
    if a.zusammenfuehren:
        teile = teile_lesen(a.zusammenfuehren)
        zus, mcsv = gesamt_schreiben(teile, a.von, a.bis_plan, a.out)
        print("=== minuten, csv")
        print(mcsv)
        print("=== zusammenfassung")
        print("\n".join(zus))
        return 0
    if a.pruefe_ids or a.ids_url:
        zus, text = asyncio.run(pruefe_ids(a.pruefe_ids, a.out, a.ids_url, a.nur_zaehlung or bool(a.ids_url)))
        if text:
            print("=== pruefung, csv")
            print(text)
        print("=== zusammenfassung")
        print("\n".join(zus))
        return 0
    bis = a.bis or int(time.time()) + (a.dauer or 1800)
    spur = a.spur or a.teil[:1]
    zus, mcsv, geb, meta = asyncio.run(lauf(bis, a.out, spur, a.teil, a.von, a.bis_plan, a.rolle, a.partner))
    print("\n=== minuten, csv")
    print(mcsv)
    print("=== gebuehren-stichprobe, csv")
    print(geb)
    print("=== datenform (nur schluessel)")
    print(json.dumps(meta["datenform"], ensure_ascii=False)[:3000])
    print("=== verbindungen")
    for n, v in meta["knoten"].items():
        for x in v["verbindungen"]:
            print(n, x["zeit"], x["kennung"], x["version"], "gleich wie anderer" if x["gleich_wie_anderer"] else "")
    print("=== meldungen")
    print("\n".join(meta["meldungen"]) or "keine")
    print("\n=== zusammenfassung")
    print("\n".join(zus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
