#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_sekunden.py, angenommene Covenant-Hops je Familie und Sekunde (Ben, 06.11.2026).

STP-Lauf Sa 7.11.2026: ein Sender, 1, 2, 4, dann 8 Familien, danach eine
Rampe mit Schritten von 50 s an und 10 s aus. Dieses Skript liest die
Tx-Listen der Nachzaehlung (s*-k1-covenant.csv und s*-k2-covenant.csv aus
tn10_nachzaehlung.py) und gibt NUR Zahlen aus, keine Tx-ID:

    sekunden.csv   je UTC-Sekunde und Familie: angenommen k1, k2 (zur
                   Kopfzeit des annehmenden Kettenblocks)
    schritte.csv   je Schritt und Familie: angenommen im Schritt, im
                   Nachlauf (bis NACHLAUF_S nach dem Ende), je Sekunde,
                   Landung (Anteil der Sekunden mit mindestens einem Hop)
    schritte.json  dazu die Landung ueber alle Familien (union) und welcher
                   Plan galt (mit oder ohne f8)

Eine Tx aus zwei Stuecken zaehlt einmal. Knoten k1 und k2 werden getrennt
gezaehlt und verglichen.

    python3 scripts/tn10_sekunden.py --listen DIR --plan messung/tn10/lauf-2026-11-07.txt --out DIR
    python3 scripts/tn10_sekunden.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import sys
import tempfile

NACHLAUF_S = 10


def ms(text):
    return int(dt.datetime.fromisoformat(text.strip().replace("Z", "+00:00")).timestamp() * 1000)


def iso_s(s):
    return dt.datetime.fromtimestamp(s, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def praefix_lesen(text):
    """Familienpraefix aus einer Zeile praefix=g (Ben, 07.11.2026: zweite
    Last mit g1 bis g32), sonst f."""
    for z in text.splitlines():
        if z.strip().startswith("praefix="):
            return z.split("=", 1)[1].strip() or "f"
    return "f"


def plan_lesen(text):
    """Zeilen "variante name von bis familien an_s". variante "mit_f8",
    "ohne_f8" oder "beide". an_s: Sekunden mit Sender, leer heisst bis-von."""
    aus = []
    for z in text.splitlines():
        z = z.strip()
        if not z or z.startswith("#") or "=" in z:
            continue
        t = z.split()
        var, name, von, bis, fam = t[:5]
        an = int(t[5]) if len(t) > 5 else (ms(bis) - ms(von)) // 1000
        aus.append({"variante": var, "name": name, "von": ms(von), "bis": ms(bis), "familien": int(fam), "an_s": an})
    return aus


def listen_lesen(ordner):
    """{k: {tx: (familien, annehmender_ms oder None)}} fuer k1 und k2."""
    aus = {}
    for k in ("k1", "k2"):
        tx = {}
        for p in sorted(glob.glob(os.path.join(ordner, "**", "*%s-covenant.csv" % k), recursive=True)):
            for z in csv.DictReader(open(p, encoding="utf-8")):
                fam = tuple(sorted(f for f in (z.get("familie") or "").split("+") if f))
                an = int(z["annehmender_block_ms"]) if z.get("angenommen") == "1" and z.get("annehmender_block_ms") else None
                alt = tx.get(z["tx_id"])
                if alt is None or (alt[1] is None and an is not None):
                    tx[z["tx_id"]] = (fam, an)
        aus[k] = tx
    return aus


def je_sekunde(tx):
    """{(sekunde, familie): anzahl} der angenommenen Hops."""
    aus = {}
    for fam, an in tx.values():
        if an is None:
            continue
        for f in fam:
            k = (an // 1000, f)
            aus[k] = aus.get(k, 0) + 1
    return aus


def variante(sek, plan):
    """mit_f8, wenn im f8-Schritt Hops der Familien 5 bis 8 angenommen wurden."""
    f8 = [s for s in plan if s["name"] == "f8"]
    if not f8:
        return "ohne_f8"
    a, b = f8[0]["von"] // 1000, f8[0]["bis"] // 1000
    hoch = sum(n for (s, f), n in sek.items() if a <= s < b and f in ("f5", "f6", "f7", "f8"))
    return "mit_f8" if hoch > 0 else "ohne_f8"


def schritte(sek, plan, var, praefix="f"):
    zeilen, union = [], {}
    for s in plan:
        if s["variante"] not in ("beide", var):
            continue
        a, b = s["von"] // 1000, s["bis"] // 1000
        fams = ["%s%d" % (praefix, i) for i in range(1, s["familien"] + 1)]
        # rampenschritte tragen ihre 10 s aus schon im schlitz, dort kein nachlauf
        nl = NACHLAUF_S if s["an_s"] >= b - a else 0
        mit = set()
        for f in fams:
            im = sum(sek.get((x, f), 0) for x in range(a, b))
            nach = sum(sek.get((x, f), 0) for x in range(b, b + nl))
            sek_mit = sum(1 for x in range(a, b) if sek.get((x, f), 0) > 0)
            mit |= {x for x in range(a, b) if sek.get((x, f), 0) > 0}
            zeilen.append({"schritt": s["name"], "von": iso_s(a), "bis": iso_s(b), "familie": f, "an_s": s["an_s"],
                           "angenommen": im, "nachlauf": nach,
                           "je_s": round((im + nach) / s["an_s"], 3) if s["an_s"] else "",
                           "landung_pct": round(100 * sek_mit / (b - a), 2) if b > a else ""})
        if fams:
            union[s["name"]] = {"sekunden": b - a, "mit_hop": len(mit),
                                "landung_union_pct": round(100 * len(mit) / (b - a), 2) if b > a else None}
        else:
            # luecke oder ruhe: hops aller familien, die ersten NACHLAUF_S sekunden getrennt
            alle = [(x, n) for (x, f), n in sek.items() if a <= x < b]
            union[s["name"]] = {"sekunden": b - a, "hops": sum(n for _, n in alle),
                                "hops_nach_nachlauf": sum(n for x, n in alle if x >= a + NACHLAUF_S)}
    return zeilen, union


def minuten(sek, plan, var, praefix="f"):
    """je UTC-Minute im Plan: Summe aller Familien, je s, langsamste Familie
    (je s) unter den Familien des Schritts, der die Minute beginnt."""
    aus = {}
    for s in plan:
        if s["variante"] not in ("beide", var):
            continue
        fams = ["%s%d" % (praefix, i) for i in range(1, s["familien"] + 1)]
        for m in range(s["von"] // 60000, -(-s["bis"] // 60000)):
            if m in aus:
                continue
            je = {f: sum(sek.get((x, f), 0) for x in range(m * 60, m * 60 + 60)) for f in fams}
            ges = sum(n for (x, f), n in sek.items() if m * 60 <= x < m * 60 + 60)
            aus[m] = {"schritt": s["name"], "familien": len(fams), "summe": ges, "summe_je_s": round(ges / 60, 3),
                      "langsamste_je_s": round(min(je.values()) / 60, 3) if je else "",
                      "langsamste": min(je, key=lambda f: (je[f], f)) if je else ""}
    return aus


def auswerten(ordner, plan_text, out):
    plan = plan_lesen(plan_text)
    praefix = praefix_lesen(plan_text)
    tx = listen_lesen(ordner)
    sek = {k: je_sekunde(v) for k, v in tx.items()}
    var = variante(sek.get("k1") or sek.get("k2") or {}, plan)
    os.makedirs(out, exist_ok=True)
    alle = sorted(set(sek.get("k1", {})) | set(sek.get("k2", {})))
    with open(os.path.join(out, "sekunden.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sekunde_utc", "familie", "k1", "k2", "gleich"])
        for s, f in alle:
            a, b = sek.get("k1", {}).get((s, f), 0), sek.get("k2", {}).get((s, f), 0)
            w.writerow([iso_s(s), f, a, b, int(a == b)])
    erg = {"variante": var, "nachlauf_s": NACHLAUF_S, "tx_k1": len(tx.get("k1", {})), "tx_k2": len(tx.get("k2", {}))}
    sp = ["schritt", "von", "bis", "familie", "an_s"]
    je = {}
    for k in ("k1", "k2"):
        z, u = schritte(sek.get(k, {}), plan, var, praefix)
        erg["union_" + k] = u
        for r in z:
            je.setdefault((r["schritt"], r["familie"]), {c: r[c] for c in sp}).update(
                {"%s_%s" % (k, c): r[c] for c in ("angenommen", "nachlauf", "je_s", "landung_pct")})
    kopf = sp + ["%s_%s" % (k, c) for k in ("k1", "k2") for c in ("angenommen", "nachlauf", "je_s", "landung_pct")]
    with open(os.path.join(out, "schritte.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=kopf, lineterminator="\n")
        w.writeheader()
        w.writerows(je.values())
    mk = {k: minuten(sek.get(k, {}), plan, var, praefix) for k in ("k1", "k2")}
    with open(os.path.join(out, "minuten.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["minute_utc", "schritt", "familien", "k1_summe", "k1_summe_je_s", "k1_langsamste", "k1_langsamste_je_s",
                    "k2_summe", "k2_summe_je_s", "k2_langsamste", "k2_langsamste_je_s", "gleich"])
        for m in sorted(mk["k1"]):
            a, b = mk["k1"][m], mk["k2"][m]
            w.writerow([iso_s(m * 60)[:16] + "Z", a["schritt"], a["familien"], a["summe"], a["summe_je_s"], a["langsamste"],
                        a["langsamste_je_s"], b["summe"], b["summe_je_s"], b["langsamste"], b["langsamste_je_s"],
                        int(a["summe"] == b["summe"] and a["langsamste_je_s"] == b["langsamste_je_s"])])
    erg["praefix"] = praefix
    erg["sekunden_ungleich"] = sum(1 for s, f in alle if sek.get("k1", {}).get((s, f), 0) != sek.get("k2", {}).get((s, f), 0))
    with open(os.path.join(out, "schritte.json"), "w", encoding="utf-8") as fh:
        json.dump(erg, fh, indent=1)
    return erg


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)
    t0 = ms("2026-11-07T19:00:00Z")
    plan = ("beide f1 2026-11-07T19:00:00Z 2026-11-07T19:01:00Z 1\n"
            "mit_f8 f8 2026-11-07T19:02:00Z 2026-11-07T19:03:00Z 8\n"
            "ohne_f8 r1 2026-11-07T19:02:00Z 2026-11-07T19:03:00Z 4 50\n")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "s1"))
        for k in ("k1", "k2"):
            with open(os.path.join(d, "s1", "s1-%s-covenant.csv" % k), "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["tx_id", "familie", "erster_block_ms", "bloecke", "angenommen", "annehmender_block_ms"])
                for i in range(30):          # f1: 30 hops in den ersten 30 sekunden
                    w.writerow(["a%02d" % i, "f1", t0 + i * 1000, 1, 1, t0 + i * 1000 + 500])
                w.writerow(["n1", "f1", t0 + 61000, 1, 1, t0 + 62000])   # nachlauf
                w.writerow(["x1", "f1", t0 + 5000, 1, 0, ""])             # nie angenommen
                for i in range(10):          # rampe, familien 1 bis 4, keine f5-f8
                    w.writerow(["r%02d" % i, "f%d" % (1 + i % 4), t0 + 120000 + i * 1000, 1, 1, t0 + 120000 + i * 1000 + 200])
                if k == "k2":
                    w.writerow(["a29", "f1", t0, 1, 1, t0 + 29500])  # doppelt aus einem zweiten stueck
        out = os.path.join(d, "aus")
        e = auswerten(d, plan, out)
        r = {(x["schritt"], x["familie"]): x for x in csv.DictReader(open(os.path.join(out, "schritte.csv")))}
        ok("ohne f8 erkannt", e["variante"] == "ohne_f8")
        ok("f1: 30 im schritt, 1 im nachlauf, 31/60 je s", r[("f1", "f1")]["k1_angenommen"] == "30"
           and r[("f1", "f1")]["k1_nachlauf"] == "1" and r[("f1", "f1")]["k1_je_s"] == "0.517")
        ok("landung f1 50 %", r[("f1", "f1")]["k1_landung_pct"] == "50.0")
        ok("rampe je familie durch 50 s, ohne nachlauf", r[("r1", "f1")]["k1_je_s"] == str(round(3 / 50, 3))
           and r[("r1", "f1")]["k1_nachlauf"] == "0")
        ok("union-landung der rampe 10 von 60", e["union_k1"]["r1"]["mit_hop"] == 10)
        ok("doppelte tx zaehlt einmal, k1 gleich k2", e["sekunden_ungleich"] == 0)
        mz = {x["minute_utc"]: x for x in csv.DictReader(open(os.path.join(out, "minuten.csv")))}
        ok("minute 19:00: summe 30, langsamste f1 0.5 je s", mz["2026-11-07T19:00Z"]["k1_summe"] == "30"
           and mz["2026-11-07T19:00Z"]["k1_langsamste_je_s"] == "0.5")
        ok("rampe: langsamste familie f2 mit 2 hops", mz["2026-11-07T19:02Z"]["k1_langsamste"] in ("f2", "f3", "f4")
           and mz["2026-11-07T19:02Z"]["k1_summe"] == "10")
        # praefix g fuer die zweite last
        with open(os.path.join(d, "s1", "s1-k1-covenant.csv"), "a", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(["g001", "g2", t0 + 3000, 1, 1, t0 + 3500])
        e3 = auswerten(d, "praefix=g\nbeide load32 2026-11-07T19:00:00Z 2026-11-07T19:01:00Z 32\n", os.path.join(d, "aus3"))
        r3 = list(csv.DictReader(open(os.path.join(d, "aus3", "schritte.csv"))))
        ok("praefix g: 32 familien, g2 mit einem hop", e3["praefix"] == "g" and len(r3) == 32
           and [x["k1_angenommen"] for x in r3 if x["familie"] == "g2"] == ["1"])
        txt = "".join(open(os.path.join(out, n)).read() for n in os.listdir(out))
        e2 = auswerten(d, plan + "beide ruhe 2026-11-07T19:01:00Z 2026-11-07T19:02:00Z 0\n", os.path.join(d, "aus2"))
        ok("luecke: ein hop im nachlauf, keiner danach", e2["union_k1"]["ruhe"]["hops"] == 1
           and e2["union_k1"]["ruhe"]["hops_nach_nachlauf"] == 0)
        ok("keine tx-id in der ausgabe", "a01" not in txt and "r01" not in txt)
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen")
    ap.add_argument("--plan")
    ap.add_argument("--out", default="out/sekunden")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    print(json.dumps(auswerten(a.listen, open(a.plan, encoding="utf-8").read(), a.out), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
