#!/usr/bin/env python3
"""Kaspa Pulse, Auswertung des UTXO-Bestands zur Stichzeit (eigene Zaehlung).

Liest bestand.csv aus kp-stichzeit (nur Eintraege mit Covenant-ID oder P2SH)
und bildet die Zeilen fuer den Vergleich mit Tonys Zaehlung.

Zeile 1, Covenant-ID: UTXOs, die laut Konsens eine Covenant-ID tragen.
  getrennt nach Covenant-IDs mit genau einem lebenden UTXO und mehreren,
  und nach Skripten, die nur eine Covenant-ID tragen oder mehrere (geteilt).
Zeile 2, Inscriptions: aus dem Bestand nicht bestimmbar, ein P2SH-Output
  zeigt sein Skript erst beim Ausgeben. Kein Wert.
Zeile 3, Script-Hash ohne Covenant-ID: P2SH-UTXOs ohne Covenant-ID,
  getrennt nach Skripten mit genau einem UTXO und geteilten Skripten,
  einmal ueber den ganzen Bestand und einmal nur seit Toccata entstanden.

  python3 scripts/kp_stichzeit_auswertung.py <bestand.csv> <stand.json> <aus.json>
  python3 scripts/kp_stichzeit_auswertung.py --selbsttest
"""
import collections
import csv
import json
import os
import sys
import tempfile

TOCCATA_DAA = 474165565
SOMPI = 100_000_000


def kas(sompi):
    return round(sompi / SOMPI, 8)


def summe(zeilen):
    return {"utxos": len(zeilen), "kas": kas(sum(z["sompi"] for z in zeilen))}


def lesen(pfad):
    out = []
    with open(pfad, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({
                "outpoint": r["outpoint"],
                "sompi": int(r["sompi"]),
                "daa": int(r["block_daa_score"]),
                "cid": r["covenant_id"],
                "p2sh": r["klasse"] == "p2sh",
                "skript": "%s:%s" % (r["spk_version"], r["spk_hex"]),
            })
    return out


def zeile_covenant(rows):
    """Covenant-IDs disjunkt eingeteilt: eine ID gilt als "eigenes Skript",
    wenn KEINER ihrer UTXOs auf einem Skript liegt, das auch UTXOs einer
    anderen ID traegt. Sonst zaehlt sie ganz zu "auf geteilten Skripten"."""
    cov = [z for z in rows if z["cid"]]
    je_id = collections.defaultdict(list)
    for z in cov:
        je_id[z["cid"]].append(z)
    ids_je_skript = collections.defaultdict(set)
    for z in cov:
        ids_je_skript[z["skript"]].add(z["cid"])
    geteilt = {s for s, ids in ids_je_skript.items() if len(ids) > 1}

    def teil(bed):
        ids = [c for c, zs in je_id.items() if bed(zs)]
        zs = [z for c in ids for z in je_id[c]]
        return {"covenant_ids": len(ids), **summe(zs)}

    eigen = lambda zs: all(z["skript"] not in geteilt for z in zs)  # noqa: E731
    return {
        "alle": {"covenant_ids": len(je_id), "skripte": len(ids_je_skript), **summe(cov)},
        "ein_utxo_eigenes_skript": teil(lambda zs: len(zs) == 1 and eigen(zs)),
        "mehrere_utxos_eigenes_skript": teil(lambda zs: len(zs) > 1 and eigen(zs)),
        "auf_geteilten_skripten": {"skripte": len(geteilt), **teil(lambda zs: not eigen(zs))},
        "ids_ueber_mehrere_skripte": sum(1 for zs in je_id.values() if len({z["skript"] for z in zs}) > 1),
        "davon_p2sh": summe([z for z in cov if z["p2sh"]]),
        "seit_toccata_entstanden": summe([z for z in cov if z["daa"] >= TOCCATA_DAA]),
    }


def zeile_scripthash(rows, nur_seit_toccata=False):
    sh = [z for z in rows if z["p2sh"] and not z["cid"]]
    if nur_seit_toccata:
        sh = [z for z in sh if z["daa"] >= TOCCATA_DAA]
    je_skript = collections.defaultdict(list)
    for z in sh:
        je_skript[z["skript"]].append(z)
    einzeln = [zs[0] for zs in je_skript.values() if len(zs) == 1]
    geteilt = [z for zs in je_skript.values() if len(zs) > 1 for z in zs]
    return {
        "alle": {"skripte": len(je_skript), **summe(sh)},
        "ein_utxo_je_skript": summe(einzeln),
        "geteilte_skripte": {"skripte": sum(1 for zs in je_skript.values() if len(zs) > 1), **summe(geteilt)},
    }


def auswerten(rows, stand):
    z1 = zeile_covenant(rows)
    teile = [z1[k] for k in ("ein_utxo_eigenes_skript", "mehrere_utxos_eigenes_skript", "auf_geteilten_skripten")]
    if (sum(t["covenant_ids"] for t in teile) != z1["alle"]["covenant_ids"]
            or sum(t["utxos"] for t in teile) != z1["alle"]["utxos"]):
        raise SystemExit("zeile 1 nicht disjunkt, abbruch")
    return {
        "quelle": "counted by kaspa pulse, eigener knoten, utxo-bestand aus der knoten-datenbank",
        "stichzeit": stand.get("hauptstichzeit"),
        "stichblock": stand.get("hauptstichblock"),
        "zweitpruefung_identisch": (stand.get("zweitpruefung") or {}).get("identisch_mit_rueckweg"),
        "zeile1_covenant_id": z1,
        "zeile2_inscriptions": {"wert": None, "grund": "ein p2sh-output zeigt sein skript erst beim ausgeben, "
                                "aus dem bestand allein nicht bestimmbar"},
        "zeile3_scripthash_ohne_covenant_id": zeile_scripthash(rows),
        "zeile3_nur_seit_toccata": zeile_scripthash(rows, True),
        "stichzeiten": [{"stichzeit": s["stichzeit"], "stichblock_zeit": s["stichblock_zeit"],
                         **{k: s["bestand"][k] for k in ("mit_covenant_id", "p2sh_ohne_covenant_id", "alle_utxos")}}
                        for s in stand.get("stichzeiten", [])],
    }


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)

    p2sh = lambda n: "aa20" + ("%02x" % n) * 32 + "87"  # noqa: E731
    zeilen = [
        # covenant A: ein utxo, eigenes skript
        ("a:0", 100 * SOMPI, TOCCATA_DAA + 5, "ca", "p2sh", p2sh(1)),
        # covenant B: zwei utxos, eigenes skript
        ("b:0", 1 * SOMPI, TOCCATA_DAA + 6, "cb", "p2sh", p2sh(2)),
        ("b:1", 2 * SOMPI, TOCCATA_DAA + 6, "cb", "p2sh", p2sh(2)),
        # covenant C und D teilen ein skript
        ("c:0", 3 * SOMPI, TOCCATA_DAA + 7, "cc", "p2sh", p2sh(3)),
        ("d:0", 4 * SOMPI, TOCCATA_DAA + 8, "cd", "p2sh", p2sh(3)),
        # covenant E: ein utxo auf eigenem skript, einer auf dem geteilten skript von C und D
        ("h:0", 10 * SOMPI, TOCCATA_DAA + 7, "ce", "p2sh", p2sh(7)),
        ("h:1", 20 * SOMPI, TOCCATA_DAA + 7, "ce", "p2sh", p2sh(3)),
        # p2sh ohne id: zwei einzelne (einer alt), ein geteiltes mit drei
        ("e:0", 5 * SOMPI, TOCCATA_DAA - 10, "", "p2sh", p2sh(4)),
        ("f:0", 6 * SOMPI, TOCCATA_DAA + 9, "", "p2sh", p2sh(5)),
        ("g:0", 1 * SOMPI, TOCCATA_DAA + 9, "", "p2sh", p2sh(6)),
        ("g:1", 1 * SOMPI, TOCCATA_DAA - 9, "", "p2sh", p2sh(6)),
        ("g:2", 1 * SOMPI, TOCCATA_DAA + 9, "", "p2sh", p2sh(6)),
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bestand.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("outpoint,sompi,block_daa_score,is_coinbase,covenant_id,klasse,adresse,spk_version,spk_hex\n")
            for o, s, daa, cid, k, spk in zeilen:
                fh.write("%s,%d,%d,false,%s,%s,,0,%s\n" % (o, s, daa, cid, k, spk))
        r = auswerten(lesen(p), {"hauptstichzeit": "x", "zweitpruefung": {"identisch_mit_rueckweg": True}})
    z1 = r["zeile1_covenant_id"]
    ok("z1 alle", z1["alle"] == {"covenant_ids": 5, "skripte": 4, "utxos": 7, "kas": 140.0}, z1["alle"])
    ok("z1 ein utxo eigen", z1["ein_utxo_eigenes_skript"] == {"covenant_ids": 1, "utxos": 1, "kas": 100.0},
       z1["ein_utxo_eigenes_skript"])
    ok("z1 mehrere eigen", z1["mehrere_utxos_eigenes_skript"] == {"covenant_ids": 1, "utxos": 2, "kas": 3.0},
       z1["mehrere_utxos_eigenes_skript"])
    ok("z1 geteilt, e ganz dort", z1["auf_geteilten_skripten"] == {"skripte": 1, "covenant_ids": 3, "utxos": 4, "kas": 37.0},
       z1["auf_geteilten_skripten"])
    teile = [z1[k] for k in ("ein_utxo_eigenes_skript", "mehrere_utxos_eigenes_skript", "auf_geteilten_skripten")]
    ok("z1 disjunkt, teile ergeben das ganze", sum(t["covenant_ids"] for t in teile) == z1["alle"]["covenant_ids"]
       and sum(t["utxos"] for t in teile) == z1["alle"]["utxos"], teile)
    ok("z1 id ueber mehrere skripte", z1["ids_ueber_mehrere_skripte"] == 1)
    z3 = r["zeile3_scripthash_ohne_covenant_id"]
    ok("z3 alle", z3["alle"] == {"skripte": 3, "utxos": 5, "kas": 14.0}, z3["alle"])
    ok("z3 einzeln", z3["ein_utxo_je_skript"] == {"utxos": 2, "kas": 11.0}, z3["ein_utxo_je_skript"])
    ok("z3 geteilt", z3["geteilte_skripte"] == {"skripte": 1, "utxos": 3, "kas": 3.0}, z3["geteilte_skripte"])
    z3t = r["zeile3_nur_seit_toccata"]
    ok("z3 toccata", z3t["alle"] == {"skripte": 2, "utxos": 3, "kas": 8.0}
       and z3t["geteilte_skripte"]["utxos"] == 2, z3t)
    ok("z2 kein wert", r["zeile2_inscriptions"]["wert"] is None)
    ok("quelle counted", r["quelle"].startswith("counted by kaspa pulse"))
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    if sys.argv[1:] == ["--selbsttest"]:
        return selbsttest()
    bestand, stand_pfad, aus = sys.argv[1:4]
    with open(stand_pfad, encoding="utf-8") as fh:
        stand = json.load(fh)
    r = auswerten(lesen(bestand), stand)
    with open(aus, "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=2)
    print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
