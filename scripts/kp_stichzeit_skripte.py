#!/usr/bin/env python3
"""Kaspa Pulse, geteilte Skripte je Skript gegen Tonys Indexer-Liste (Ben, 22.10.2026).

Liest bestand.csv aus kp-stichzeit (jeder UTXO mit Covenant-ID oder P2SH,
mit Adresse) und Tonys Liste ohne Adressen (messung/covenants-stichzeit/tony/,
Skript als sha256(adresse)[:16], Covenant-ID als sha256(id)[:32]). Gibt je
Skript nur Summen aus, nie eine Adresse oder eine ID.

Je Skript laut Knoten (counted):
    utxos_alle, kas_alle        jeder UTXO am Skript, mit oder ohne Covenant-ID
    utxos_cov, kas_cov          davon mit Covenant-ID
    ids                         verschiedene Covenant-IDs mit lebendem UTXO am Skript
Gegen Tony (source tony's indexer):
    ids_beide, ids_nur_tony, ids_nur_knoten, ids_gleiche_outputs
    d_outputs = utxos_alle - claimed_outputs, d_kas = kas_alle - claimed KAS

    python3 scripts/kp_stichzeit_skripte.py <bestand.csv> <tony.json> <aus-ordner>
    python3 scripts/kp_stichzeit_skripte.py --selbsttest
"""
import collections
import csv
import hashlib
import json
import os
import sys
import tempfile

SOMPI = 100_000_000
SPALTEN = ["nr", "skript", "tony_ids", "tony_claimed_outputs", "tony_claimed_kas", "tony_node_utxos", "tony_stimmt",
           "ids", "utxos_alle", "kas_alle", "utxos_cov", "kas_cov", "ids_beide", "ids_nur_tony", "ids_nur_knoten",
           "ids_gleiche_outputs", "d_outputs", "d_kas", "summe_stimmt_knoten"]


def h(text, n):
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:n]


def kas(s):
    return round(s / SOMPI, 8)


def je_skript(bestand):
    """skript-hash -> {"alle": [n, sompi], "cov": [n, sompi], "ids": Counter(id-hash -> utxos)}."""
    aus = collections.defaultdict(lambda: {"alle": [0, 0], "cov": [0, 0], "ids": collections.Counter()})
    with open(bestand, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["adresse"]:
                continue
            s = aus[h(r["adresse"], 16)]
            v = int(r["sompi"])
            s["alle"][0] += 1
            s["alle"][1] += v
            if r["covenant_id"]:
                s["cov"][0] += 1
                s["cov"][1] += v
                s["ids"][h(r["covenant_id"], 32)] += 1
    return aus


def abgleich(knoten, tony):
    zeilen = []
    for t in tony["skripte"]:
        k = knoten.get(t["skript"], {"alle": [0, 0], "cov": [0, 0], "ids": collections.Counter()})
        ti, ki = t["ids"], k["ids"]
        beide = set(ti) & set(ki)
        zeilen.append({
            "nr": t["nr"], "skript": t["skript"][:10], "tony_ids": t["tenants"],
            "tony_claimed_outputs": t["claimed_outputs"], "tony_claimed_kas": kas(t["claimed_sompi"]),
            "tony_node_utxos": t["node_utxos"], "tony_stimmt": int(bool(t["aggregate_matches_node"])),
            "ids": len(ki), "utxos_alle": k["alle"][0], "kas_alle": kas(k["alle"][1]),
            "utxos_cov": k["cov"][0], "kas_cov": kas(k["cov"][1]),
            "ids_beide": len(beide), "ids_nur_tony": len(set(ti) - set(ki)), "ids_nur_knoten": len(set(ki) - set(ti)),
            "ids_gleiche_outputs": sum(1 for i in beide if ti[i] == ki[i]),
            "d_outputs": k["alle"][0] - t["claimed_outputs"], "d_kas": kas(k["alle"][1] - t["claimed_sompi"]),
            "summe_stimmt_knoten": int(k["alle"][0] == t["claimed_outputs"] and k["alle"][1] == t["claimed_sompi"]),
        })
    return zeilen


def eigene_geteilte(knoten):
    """unsere Definition: Skripte mit lebenden UTXOs von mindestens zwei Covenant-IDs."""
    g = [s for s in knoten.values() if len(s["ids"]) >= 2]
    return {"skripte": len(g), "covenant_ids": sum(len(s["ids"]) for s in g),
            "utxos_cov": sum(s["cov"][0] for s in g), "kas_cov": kas(sum(s["cov"][1] for s in g))}


def summen(zeilen, tony, knoten):
    keys = ["tony_ids", "tony_claimed_outputs", "tony_node_utxos", "ids", "utxos_alle", "utxos_cov", "ids_beide",
            "ids_nur_tony", "ids_nur_knoten", "ids_gleiche_outputs", "d_outputs"]
    s = {k: sum(z[k] for z in zeilen) for k in keys}
    s.update({"tony_claimed_kas": round(sum(z["tony_claimed_kas"] for z in zeilen), 8),
              "kas_alle": round(sum(z["kas_alle"] for z in zeilen), 8),
              "kas_cov": round(sum(z["kas_cov"] for z in zeilen), 8),
              "skripte": len(zeilen), "skripte_summe_stimmt_knoten": sum(z["summe_stimmt_knoten"] for z in zeilen),
              "skripte_tony_stimmt": sum(z["tony_stimmt"] for z in zeilen),
              "skripte_am_knoten_leer": sum(1 for z in zeilen if z["utxos_alle"] == 0)})
    groesste = sorted(zeilen, key=lambda z: (-abs(z["d_outputs"]), -abs(z["d_kas"])))[:5]
    return {"summen": s, "groesste_abweichung": [{k: z[k] for k in ("nr", "skript", "tony_ids", "ids",
                                                                    "tony_claimed_outputs", "utxos_alle",
                                                                    "d_outputs", "d_kas")} for z in groesste],
            "eigene_geteilte_skripte": eigene_geteilte(knoten),
            "tony_skripte_in_eigener_definition": sum(1 for z in zeilen if z["ids"] >= 2),
            "quelle_tony": tony.get("quelle"), "census_at_tony": tony.get("census_at")}


def laufen(bestand, tony_pfad, aus):
    with open(tony_pfad, encoding="utf-8") as fh:
        tony = json.load(fh)
    kn = je_skript(bestand)
    zeilen = abgleich(kn, tony)
    zus = summen(zeilen, tony, kn)
    os.makedirs(aus, exist_ok=True)
    with open(os.path.join(aus, "skripte-abgleich.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN)
        w.writeheader()
        w.writerows(zeilen)
    with open(os.path.join(aus, "skripte-abgleich.json"), "w", encoding="utf-8") as fh:
        json.dump(zus, fh, indent=1)
    return zeilen, zus


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    a1, a2, a3 = "kaspa:pzaaa", "kaspa:pzbbb", "kaspa:pzccc"
    zeilen = [(a1, "c1", 10), (a1, "c1", 20), (a1, "c2", 5), (a1, "", 7), (a2, "c3", 100), (a3, "c4", 1), (a3, "c5", 1)]
    tony = {"quelle": "test", "skripte": [
        {"nr": 1, "skript": h(a1, 16), "tenants": 3, "claimed_outputs": 3, "claimed_sompi": 35 * SOMPI,
         "node_utxos": 4, "node_sompi": 42 * SOMPI, "aggregate_matches_node": False,
         "ids": {h("c1", 32): 2, h("c2", 32): 1, h("c9", 32): 0}},
        {"nr": 2, "skript": h(a2, 16), "tenants": 2, "claimed_outputs": 1, "claimed_sompi": 100 * SOMPI,
         "node_utxos": 1, "node_sompi": 100 * SOMPI, "aggregate_matches_node": True,
         "ids": {h("c3", 32): 1, h("c8", 32): 0}},
        {"nr": 3, "skript": h("kaspa:pzleer", 16), "tenants": 2, "claimed_outputs": 2, "claimed_sompi": 2,
         "node_utxos": 0, "node_sompi": 0, "aggregate_matches_node": False, "ids": {}}]}
    with tempfile.TemporaryDirectory() as d:
        b, t = os.path.join(d, "bestand.csv"), os.path.join(d, "tony.json")
        with open(b, "w", encoding="utf-8") as fh:
            fh.write("outpoint,sompi,block_daa_score,is_coinbase,covenant_id,klasse,adresse,spk_version,spk_hex\n")
            for i, (adr, cid, k) in enumerate(zeilen):
                fh.write("tx%d:0,%d,1,false,%s,p2sh,%s,0,aa\n" % (i, k * SOMPI, cid, adr))
        with open(t, "w", encoding="utf-8") as fh:
            json.dump(tony, fh)
        z, s = laufen(b, t, os.path.join(d, "aus"))
        text = open(os.path.join(d, "aus", "skripte-abgleich.csv"), encoding="utf-8").read() + json.dumps(s)
    r1, r2, r3 = z
    ok("skript 1: 2 ids, 4 utxos 42 kas, 3 mit id", (r1["ids"], r1["utxos_alle"], r1["kas_alle"], r1["utxos_cov"])
       == (2, 4, 42.0, 3), r1)
    ok("skript 1: beide 2, nur tony 1, gleiche outputs 2", (r1["ids_beide"], r1["ids_nur_tony"], r1["ids_nur_knoten"],
                                                            r1["ids_gleiche_outputs"]) == (2, 1, 0, 2), r1)
    ok("skript 1: abweichung +1 output, +7 kas", r1["d_outputs"] == 1 and r1["d_kas"] == 7.0, r1)
    ok("skript 2 stimmt in der summe", r2["summe_stimmt_knoten"] == 1 and r2["ids_nur_tony"] == 1, r2)
    ok("skript 3 am knoten leer", r3["utxos_alle"] == 0 and s["summen"]["skripte_am_knoten_leer"] == 1, r3)
    ok("eigene geteilte: nur a1 und a3", s["eigene_geteilte_skripte"]["skripte"] == 2
       and s["eigene_geteilte_skripte"]["covenant_ids"] == 4, s["eigene_geteilte_skripte"])
    ok("groesste abweichung zuerst skript 3 oder 1", s["groesste_abweichung"][0]["nr"] in (1, 3))
    ok("keine adresse, keine id im klartext", "kaspa:" not in text and "c1" not in text.replace("cov", ""))
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    if sys.argv[1:] == ["--selbsttest"]:
        return selbsttest()
    zeilen, zus = laufen(*sys.argv[1:4])
    w = csv.DictWriter(sys.stdout, fieldnames=SPALTEN)
    w.writeheader()
    w.writerows(zeilen)
    print(json.dumps(zus, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
