#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_sicherung.py, Covenant-Zaehlungen je Id und Sekunde sichern (Ben, 08.11.2026).

STP-Lauf Sa 7.11.2026: keine Familie traf einen veroeffentlichten Hash. Bevor
die Knoten das Fenster 18:45 bis 22:25 UTC loeschen, wird es einmal ganz
gelesen und je Covenant-Id gezaehlt. Ins Repo kommen nur Hashes und Zahlen:

    id_sha       sha256 der Covenant-Id als lowercase hex (unsere Regel)
    genesis_sha  sha256 der Tx-Id der Transaktion, die den Covenant angelegt
                 hat, ebenfalls lowercase hex

Damit laesst sich jede spaetere Hash-Liste von STP zuordnen, ohne die Kette
noch einmal zu lesen. Keine Zuordnung wird geraten.

Modi:
    --punkt --rolle k1|k2 --partner P --out DATEI
        Pruning-Punkt eines Knotens, nur Zeit und Kennung.
    --von --bis --rolle --partner --out ORDNER
        ein Stueck lesen (Bloecke und Kette). Im Runner bleiben Tx-IDs, die
        Covenant-Id wird schon beim Lesen gehasht und verlaesst den Runner nie.
    --zusammen ORDNER --von --bis --out ORDNER
        alle Stuecke beider Knoten zusammen, ergibt ids.csv, sekunden.csv,
        meta.json. Prueft, dass keine Tx-ID im Ergebnis steht.
    --selbsttest
"""
import argparse
import asyncio
import csv
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tn10_nachzaehlung import (Covenant, Leser, VERSUCHE, cov_hash, iso_ms, utc_ms,  # noqa: E402
                               verbinden, zaehle, schreiben_json)
from tn10_zaehler import feld  # noqa: E402

PRAEFIX = 16    # so viele hex-zeichen je tx-id fuer die menge "im fenster gesehen"


def tx_sha(tid):
    return hashlib.sha256(str(tid).strip().lower().encode()).hexdigest()


class Sammler(Covenant):
    """Alle Covenant-Ausgaenge, egal welche Id. Je Tx: erster Block, Zahl der
    Bloecke, Annahme, gebundene Ausgaenge (index -> id_sha), Eingaenge. Dazu
    die Praefixe aller Tx-IDs im gelesenen Bereich."""

    def __init__(self):
        super().__init__("")
        self.aktiv = True
        self.alle = set()
        self.an_ms = {}

    def block(self, b, ts):
        for tx in feld(b, "transactions") or []:
            tid = feld(feld(tx, "verboseData") or {}, "transactionId")
            if tid:
                self.alle.add(str(tid)[:PRAEFIX])
            aus = {}
            for i, o in enumerate(feld(tx, "outputs") or []):
                cid = feld(feld(o, "covenant") or {}, "covenantId")
                if cid:
                    aus[i] = cov_hash(cid)
            eing = ["%s:%s" % (feld(feld(e, "previousOutpoint") or {}, "transactionId"),
                               feld(feld(e, "previousOutpoint") or {}, "index"))
                    for e in feld(tx, "inputs") or []]
            ein = {self.ausgaenge[x] for x in eing if x in self.ausgaenge}
            if not (aus or ein):
                continue
            if not tid:
                self.ohne_id += 1
                continue
            for i, h in aus.items():
                self.ausgaenge["%s:%d" % (tid, i)] = h
            e = self.tx.setdefault(tid, {"erst": ts, "bloecke": 0, "aus": {}, "ein": set(), "eing": set()})
            e["erst"] = min(e["erst"], ts)
            e["bloecke"] += 1
            e["aus"].update(aus)
            e["ein"] |= ein
            e["eing"] |= set(eing)

    def auswerten(self, blockzeit, kette_gelesen):
        self.kette_gelesen = kette_gelesen
        self.an_ms = {t: blockzeit(h) for t, h in self.annahme.items()}
        return {}, []

    def verteilung(self):
        return {}

    def schreiben(self, basis):
        with gzip.open(basis + "-covtx.csv.gz", "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["tx_id", "erst_ms", "bloecke", "an_ms", "aus", "ein", "eing"])
            for t, e in sorted(self.tx.items()):
                an = self.an_ms.get(t)
                w.writerow([t, e["erst"], e["bloecke"], "" if an is None else an,
                            "|".join("%d:%s" % (i, h) for i, h in sorted(e["aus"].items())),
                            "|".join(sorted(e["ein"])), "|".join(sorted(e["eing"]))])
        with gzip.open(basis + "-alle.txt.gz", "wt", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(self.alle)))


async def stueck(von_ms, bis_ms, rolle, partner, out, versuche=VERSUCHE):
    vorher = []
    for v in range(1, versuche + 1):
        try:
            rpc, takt, kn = await verbinden(rolle, partner)
        except Exception as exc:                         # noqa: BLE001
            vorher.append("verbinden, %s" % type(exc).__name__)
            continue
        sa = Sammler()
        _, meta = await zaehle(rpc, takt, von_ms, bis_ms, cv=sa)
        meta.update(kn)
        meta.pop("covenant", None)
        try:
            await rpc.disconnect()
        except Exception:                                # noqa: BLE001
            pass
        if not str(meta.get("status", "")).startswith("fehler") or v == versuche:
            break
        vorher.append(meta["status"])
    else:
        schreiben_json(out, {"status": "kein knoten, %s" % "; ".join(vorher)})
        return 1
    meta.update({"versuche": v, "fruehere_versuche": vorher, "cov_tx": len(sa.tx), "tx_gesehen": len(sa.alle),
                 "ohne_txid": sa.ohne_id})
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if meta["status"] == "gelesen":
        sa.schreiben(out)
    schreiben_json(out, meta)
    print("%s %s, %d covenant-tx, %d tx gesehen" % (rolle, meta["status"], len(sa.tx), len(sa.alle)))
    return 0 if meta["status"] == "gelesen" else 1


async def punkt(rolle, partner, out):
    rpc, takt, kn = await verbinden(rolle, partner)
    les = Leser(rpc, takt)
    dag = await les.rufe("get_block_dag_info")
    pp = feld(dag, "pruningPointHash")
    pp_ts = await les.ts(pp) if pp else None
    try:
        await rpc.disconnect()
    except Exception:                                    # noqa: BLE001
        pass
    m = {"rolle": rolle, "kennung": kn.get("kennung", ""), "version": kn.get("version", ""),
         "gleich_wie_partner": kn.get("gleich_wie_partner", False),
         "pruning_punkt_utc": iso_ms(pp_ts) if pp_ts else "", "gelesen_utc": iso_ms(int(time.time() * 1000))}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=1)
    print(json.dumps(m))
    return 0 if pp_ts else 1


def knoten_lesen(ordner, k):
    """Alle Stuecke eines Knotens: {tx: eintrag}, menge der praefixe, metas."""
    tx, alle, metas = {}, set(), []
    for p in sorted(glob.glob(os.path.join(ordner, "**", "*-%s.json" % k), recursive=True)):
        m = json.load(open(p, encoding="utf-8"))
        metas.append({"teil": os.path.basename(p)[:-5][:24], **{x: m.get(x, "") for x in (
            "status", "kennung", "version", "pruning_punkt_utc", "start_utc", "bloecke_bis_utc", "kette_bis_utc",
            "versuche", "cov_tx", "tx_gesehen", "ohne_txid", "gleich_wie_partner")}})
        basis = p[:-5]
        if not os.path.exists(basis + "-covtx.csv.gz"):
            continue
        for z in csv.DictReader(gzip.open(basis + "-covtx.csv.gz", "rt", encoding="utf-8")):
            e = tx.setdefault(z["tx_id"], {"erst": int(z["erst_ms"]), "bloecke": 0, "an": None, "aus": {},
                                           "ein": set(), "eing": set()})
            e["erst"] = min(e["erst"], int(z["erst_ms"]))
            e["bloecke"] = max(e["bloecke"], int(z["bloecke"]))
            if z["an_ms"]:
                e["an"] = int(z["an_ms"])
            for x in filter(None, z["aus"].split("|")):
                i, h = x.split(":")
                e["aus"][int(i)] = h
            e["ein"] |= set(filter(None, z["ein"].split("|")))
            e["eing"] |= set(filter(None, z["eing"].split("|")))
        alle |= set(gzip.open(basis + "-alle.txt.gz", "rt", encoding="utf-8").read().split())
    return tx, alle, metas


def je_id(tx, alle):
    """{id_sha: {"tx": [...], "genesis": (tx_id, status, kandidaten)}}. Eingaenge
    werden ueber alle Stuecke neu zugeordnet."""
    ausg = {"%s:%d" % (t, i): h for t, e in tx.items() for i, h in e["aus"].items()}
    for e in tx.values():
        e["ein"] |= {ausg[x] for x in e["eing"] if x in ausg}
    ids = {}
    for t, e in tx.items():
        for h in set(e["aus"].values()) | e["ein"]:
            ids.setdefault(h, []).append(t)
    aus = {}
    for h, ts in ids.items():
        kand = sorted((tx[t]["erst"], t) for t in ts if h in tx[t]["aus"].values() and h not in tx[t]["ein"])
        if not kand:
            gen = ("", "keine im fenster", 0)
        else:
            t = kand[0][1]
            sicher = all(x.rsplit(":", 1)[0][:PRAEFIX] in alle for x in tx[t]["eing"]) and tx[t]["eing"]
            gen = (t, "im fenster" if sicher else "unsicher, eingang von vor dem fenster", len(kand))
        aus[h] = {"tx": ts, "genesis": gen}
    return aus


def zusammen(ordner, von_ms, bis_ms, out):
    os.makedirs(out, exist_ok=True)
    k = {n: knoten_lesen(ordner, n) for n in ("k1", "k2")}
    ids = {n: je_id(k[n][0], k[n][1]) for n in k}
    alle_ids = sorted(set(ids["k1"]) | set(ids["k2"]))
    sek = {}
    for n in ("k1", "k2"):
        tx = k[n][0]
        for h, d in ids[n].items():
            for t in d["tx"]:
                s = tx[t]["erst"] // 1000
                sek.setdefault((h, s), {}).setdefault(n + "_in_bloecken", 0)
                sek[(h, s)][n + "_in_bloecken"] += 1
                if tx[t]["an"] is not None:
                    a = tx[t]["an"] // 1000
                    sek.setdefault((h, a), {}).setdefault(n + "_angenommen", 0)
                    sek[(h, a)][n + "_angenommen"] += 1
    spalten = ["id_sha", "sekunde_utc", "k1_in_bloecken", "k1_angenommen", "k2_in_bloecken", "k2_angenommen"]
    with open(os.path.join(out, "sekunden.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(spalten)
        for (h, s) in sorted(sek):
            r = sek[(h, s)]
            w.writerow([h, iso_ms(s * 1000)[:19] + "Z"] + [r.get(c, 0) for c in spalten[2:]])
    zeilen = []
    for h in alle_ids:
        g1 = ids["k1"].get(h, {}).get("genesis", ("", "nicht gesehen", 0))
        g2 = ids["k2"].get(h, {}).get("genesis", ("", "nicht gesehen", 0))
        r = {"id_sha": h, "genesis_sha": tx_sha(g1[0]) if g1[0] else "", "genesis_status": g1[1],
             "genesis_kandidaten": g1[2], "genesis_gleich_k2": int(g1[:2] == g2[:2]),
             "genesis_utc": iso_ms(k["k1"][0][g1[0]]["erst"]) if g1[0] else ""}
        for n in ("k1", "k2"):
            ts = ids[n].get(h, {}).get("tx", [])
            an = sum(1 for t in ts if k[n][0][t]["an"] is not None)
            r[n + "_tx"], r[n + "_angenommen"] = len(ts), an
            r[n + "_nie_angenommen"] = len(ts) - an
        ss = [s for (x, s) in sek if x == h]
        r["erste_sekunde_utc"] = iso_ms(min(ss) * 1000)[:19] + "Z" if ss else ""
        r["letzte_sekunde_utc"] = iso_ms(max(ss) * 1000)[:19] + "Z" if ss else ""
        zeilen.append(r)
    zeilen.sort(key=lambda r: (-r["k1_angenommen"], r["id_sha"]))
    with open(os.path.join(out, "ids.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(zeilen[0]) if zeilen else ["id_sha"], lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)
    meta = {"fenster_von_utc": iso_ms(von_ms), "fenster_bis_utc": iso_ms(bis_ms),
            "regel_id_sha": "sha256 der covenant-id, lowercase hex",
            "regel_genesis_sha": "sha256 der tx-id der genesis, lowercase hex",
            "genesis": "frueheste tx mit einem an die id gebundenen ausgang, die keinen solchen ausgang ausgibt. "
                       "im fenster: alle ihre eingaenge stammen aus tx, die im gelesenen bereich liegen. "
                       "sonst unsicher. genesis aus k1, genesis_gleich_k2 vergleicht.",
            "grenze": "eine ausgabe ohne fortsetzung, deren gebundener eingang nur in einem anderen stueck "
                      "entstand und die selbst keinen gebundenen ausgang hat, kann fehlen",
            "ids": len(alle_ids), "ids_k1": len(ids["k1"]), "ids_k2": len(ids["k2"]),
            "cov_tx_k1": len(k["k1"][0]), "cov_tx_k2": len(k["k2"][0]),
            "tx_gesehen_k1": len(k["k1"][1]), "tx_gesehen_k2": len(k["k2"][1]),
            "genesis_im_fenster": sum(1 for r in zeilen if r["genesis_status"] == "im fenster"),
            "teile_k1": k["k1"][2], "teile_k2": k["k2"][2]}
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    # keine tx-id im ergebnis: jeder 64-stellige hex-wert darf keine gelesene tx-id sein
    roh = {t.lower() for n in k for t in k[n][0]} | {x.rsplit(":", 1)[0].lower() for n in k
                                                       for e in k[n][0].values() for x in e["eing"]}
    for name in ("ids.csv", "sekunden.csv", "meta.json"):
        text = open(os.path.join(out, name), encoding="utf-8").read()
        if set(re.findall(r"[0-9a-f]{64}", text)) & roh:
            raise SystemExit("tx-id in %s, nichts gesichert" % name)
        if re.search(r"kaspa(test)?:[a-z0-9]{20,}|\b([0-9]{1,3}\.){3}[0-9]{1,3}\b", text):
            raise SystemExit("adresse oder ip in %s, nichts gesichert" % name)
    print(json.dumps({x: meta[x] for x in meta if not x.startswith("teile")}, indent=1))
    return 0


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)
    A, B = "ab" * 32, "cd" * 32
    t0 = utc_ms("2026-11-07T19:00:00Z")

    def blk(txs):
        return {"transactions": txs}

    def tx(tid, eing, aus):
        return {"verboseData": {"transactionId": tid},
                "inputs": [{"previousOutpoint": {"transactionId": a, "index": i}} for a, i in eing],
                "outputs": [{"covenant": {"covenantId": c}} if c else {} for c in aus]}
    with tempfile.TemporaryDirectory() as d:
        # stueck 1: plain p0, genesis g_a (gibt p0 aus), fortsetzung a1; covenant B mit eingang von vor dem fenster
        s1 = Sammler()
        s1.block(blk([tx("p0", [("alt", 0)], [None]), tx("ga", [("p0", 0)], [A, None]),
                      tx("gb", [("vorher", 1)], [B])]), t0)
        s1.block(blk([tx("a1", [("ga", 0)], [A])]), t0 + 1000)
        s1.annahme = {"ga": "h1", "a1": "h2"}
        s1.auswerten(lambda h: {"h1": t0 + 500, "h2": t0 + 1500}[h], True)
        # stueck 2: a2 setzt a1 fort, a3 gibt a2 aus ohne fortsetzung (nur ueber eingang, stueckuebergreifend
        # erkennbar, weil a2 einen gebundenen ausgang hat); a2 nie angenommen
        s2 = Sammler()
        s2.block(blk([tx("a2", [("a1", 0)], [A])]), t0 + 2000)
        s2.block(blk([tx("a3", [("a2", 0)], [None])]), t0 + 3000)
        s2.annahme = {"a3": "h4"}
        s2.auswerten(lambda h: t0 + 3500, True)
        for k in ("k1", "k2"):
            for n, s in (("s1", s1), ("s2", s2)):
                b = os.path.join(d, n, "%s-%s" % (n, k))
                os.makedirs(os.path.dirname(b), exist_ok=True)
                s.schreiben(b)
                schreiben_json(b, {"status": "gelesen", "pruning_punkt_utc": "2026-11-06T15:18:07.630Z"})
        out = os.path.join(d, "aus")
        zusammen(d, t0, t0 + 60000, out)
        ids = {r["id_sha"]: r for r in csv.DictReader(open(os.path.join(out, "ids.csv")))}
        ha, hb = cov_hash(A), cov_hash(B)
        ok("zwei ids, nur gehasht", set(ids) == {ha, hb})
        ok("genesis a im fenster, sha der tx-id", ids[ha]["genesis_sha"] == tx_sha("ga")
           and ids[ha]["genesis_status"] == "im fenster" and ids[ha]["genesis_gleich_k2"] == "1")
        ok("genesis b unsicher (eingang von vor dem fenster)", ids[hb]["genesis_status"].startswith("unsicher"))
        ok("a: 4 tx (ga, a1, a2, a3), 3 angenommen, 1 nie", (ids[ha]["k1_tx"], ids[ha]["k1_angenommen"],
                                                           ids[ha]["k1_nie_angenommen"]) == ("4", "3", "1"))
        sk = [r for r in csv.DictReader(open(os.path.join(out, "sekunden.csv"))) if r["id_sha"] == ha]
        ok("je sekunde: in bloecken 19:00:00 1, angenommen 19:00:03 1",
           any(r["sekunde_utc"] == "2026-11-07T19:00:00Z" and r["k1_in_bloecken"] == "1" for r in sk)
           and any(r["sekunde_utc"] == "2026-11-07T19:00:03Z" and r["k1_angenommen"] == "1" for r in sk))
        txt = "".join(open(os.path.join(out, n)).read() for n in os.listdir(out))
        ok("keine id und keine tx-id im ergebnis", A not in txt and B not in txt and "ga" not in txt.split(","))
        # eine tx-id, die zufaellig 64 hex hat, darf nicht durchrutschen
        s3 = Sammler()
        rohid = "ef" * 32
        s3.block(blk([tx(rohid, [("p0", 0)], [A])]), t0)
        b = os.path.join(d, "s3", "s3-k1")
        os.makedirs(os.path.dirname(b), exist_ok=True)
        s3.schreiben(b)
        schreiben_json(b, {"status": "gelesen"})
        ok("tx-sha ist nicht die tx-id", tx_sha(rohid) != rohid)
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--punkt", action="store_true")
    ap.add_argument("--zusammen")
    ap.add_argument("--von")
    ap.add_argument("--bis")
    ap.add_argument("--rolle", choices=("k1", "k2"))
    ap.add_argument("--partner", default="")
    ap.add_argument("--out")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.punkt:
        return asyncio.run(punkt(a.rolle, a.partner, a.out))
    if a.zusammen:
        return zusammen(a.zusammen, utc_ms(a.von), utc_ms(a.bis), a.out)
    return asyncio.run(stueck(utc_ms(a.von), utc_ms(a.bis), a.rolle, a.partner, a.out))


if __name__ == "__main__":
    sys.exit(main())
