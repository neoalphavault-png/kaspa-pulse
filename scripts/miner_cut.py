#!/usr/bin/env python3
"""miner_cut.py, Miner nach dem Reward Cut (Ben, 02.11.2026).

Frage aus #data-requests: "after the reward cut on 4 nov, does anything change
in how fast miners move their coins?" Gezaehlt aus dem eigenen Knoten
(kp-coinbase): je Coinbase-Ausgabe ihre Entstehung und ihre erste Ausgabe.

Jeder Lauf von kp-coinbase liest nur den Teil der Kette, den die Laeufe davor
noch nicht gelesen haben (ab_daa). Dieses Skript schreibt das Ergebnis eines
Laufs in den Datenstand auf dem Messbranch fort:

    daten/stand.json       gelesener bereich, laeufe, erster beobachteter daa
    daten/daa-zeit.csv     je utc-minute kleinster und groesster daa der kettenbloecke
    daten/rein.csv         je utc-minute neue coinbase-ausgaben (anzahl, sompi)
    daten/raus-<tag>.json  je entstehungsstunde: verzug bis zur ersten ausgabe in
                           eimern, je eimer anzahl und sompi

Keine Adresse, kein Skript, keine Tx-ID, nur Summen.

    python3 miner_cut.py --fortschreiben LAUFDIR --daten miner/daten --lauf-id N
    python3 miner_cut.py --auswerten --daten miner/daten --fenster NAME VON BIS [...] --bis-ms MS
    python3 miner_cut.py --selbsttest
"""
import argparse
import bisect
import csv
import datetime as dt
import json
import os
import sys
import tempfile

STUNDE = 3600000


def eimer(verzug_ms):
    """Verzug in Eimer: bis 6 h je Minute, bis 72 h je 5 Minuten, bis 8 Tage je
    30 Minuten, danach einer. Rueckgabe: Untergrenze in Minuten."""
    m = max(0, verzug_ms) // 60000
    if m < 360:
        return m
    if m < 4320:
        return m - m % 5
    if m < 11520:
        return m - m % 30
    return 11520


def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ms(text):
    return int(dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def lies_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def schreib_csv(p, kopf, zeilen):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(kopf)
        w.writerows(zeilen)


class Karte:
    """DAA-Score zu Zeit, aus den Minuten der Kettenbloecke."""

    def __init__(self, zeilen):
        z = sorted((int(r["daa_min"]), int(r["daa_max"]), int(r["minute_ms"])) for r in zeilen)
        self.a = [x[0] for x in z]
        self.z = z

    def zeit(self, daa):
        i = bisect.bisect_right(self.a, daa) - 1
        if i < 0:
            return None
        lo, hi, m = self.z[i]
        if daa > hi:
            # zwischen zwei minuten: der naechste kettenblock liegt in der naechsten minute
            return self.z[i + 1][2] if i + 1 < len(self.z) else None
        return m + int((daa - lo) * 60000 / max(1, hi - lo + 1))


def fortschreiben(lauf, daten, lauf_id):
    os.makedirs(daten, exist_ok=True)
    st_p = os.path.join(daten, "stand.json")
    stand = json.load(open(st_p)) if os.path.exists(st_p) else {"laeufe": [], "letzter_daa": 0}
    neu = json.load(open(os.path.join(lauf, "stand.json")))
    if neu["erster_daa"] is None:
        raise SystemExit("lauf ohne kettenbloecke")
    if stand["letzter_daa"] and neu["ab_daa"] != stand["letzter_daa"]:
        raise SystemExit("lauf las ab %s, stand steht bei %s" % (neu["ab_daa"], stand["letzter_daa"]))
    # daa-zeit
    zk = {int(r["minute_ms"]): [int(r["daa_min"]), int(r["daa_max"])] for r in lies_csv(os.path.join(daten, "daa-zeit.csv"))}
    for r in lies_csv(os.path.join(lauf, "daa-zeit.csv")):
        m, a, b = int(r["minute_ms"]), int(r["daa_min"]), int(r["daa_max"])
        if m in zk:
            zk[m] = [min(zk[m][0], a), max(zk[m][1], b)]
        else:
            zk[m] = [a, b]
    schreib_csv(os.path.join(daten, "daa-zeit.csv"), ["minute_ms", "daa_min", "daa_max"],
                [[m, a, b] for m, (a, b) in sorted(zk.items())])
    karte = Karte([{"minute_ms": m, "daa_min": a, "daa_max": b} for m, (a, b) in zk.items()])
    # rein
    rk = {int(r["minute_ms"]): [int(r["anzahl"]), int(r["sompi"])] for r in lies_csv(os.path.join(daten, "rein.csv"))}
    for r in lies_csv(os.path.join(lauf, "rein.csv")):
        m = int(r["minute_ms"])
        x = rk.setdefault(m, [0, 0])
        x[0] += int(r["anzahl"])
        x[1] += int(r["sompi"])
    schreib_csv(os.path.join(daten, "rein.csv"), ["minute_ms", "anzahl", "sompi"],
                [[m, a, s] for m, (a, s) in sorted(rk.items())])
    # raus
    erster = stand.get("erster_daa") or neu["erster_daa"]
    tage, vor, ohne_zeit = {}, [0, 0], 0
    with open(os.path.join(lauf, "raus.csv"), encoding="utf-8") as fh:
        fh.readline()
        for zeile in fh:
            e_daa, aus_ms, sompi = (int(x) for x in zeile.split(","))
            if e_daa < erster:
                vor[0] += 1
                vor[1] += sompi
                continue
            e_ms = karte.zeit(e_daa)
            if e_ms is None:
                ohne_zeit += 1
                continue
            stunde = e_ms // STUNDE * STUNDE
            tag = iso(stunde)[:10]
            h = tage.setdefault(tag, {}).setdefault(str(stunde), {})
            b = h.setdefault(str(eimer(aus_ms - e_ms)), [0, 0])
            b[0] += 1
            b[1] += sompi
    for tag, stunden in tage.items():
        p = os.path.join(daten, "raus-%s.json" % tag)
        alt = json.load(open(p)) if os.path.exists(p) else {}
        for st, eim in stunden.items():
            a = alt.setdefault(st, {})
            for k, (n, s) in eim.items():
                x = a.setdefault(k, [0, 0])
                x[0] += n
                x[1] += s
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(alt, fh, sort_keys=True, separators=(",", ":"))
    stand.update({"erster_daa": erster, "erster_ms": stand.get("erster_ms") or neu["erster_ms"],
                  "letzter_daa": neu["letzter_daa"], "letzter_ms": neu["letzter_ms"]})
    stand["laeufe"].append({"lauf": lauf_id, "von_daa": neu["erster_daa"], "bis_daa": neu["letzter_daa"],
                            "von_utc": iso(neu["erster_ms"]), "bis_utc": iso(neu["letzter_ms"]),
                            "pruning_punkt_utc": iso(neu["pruning_punkt_ms"]), "kettenbloecke": neu["kettenbloecke"],
                            "coinbase_neu": neu["coinbase_neu"], "coinbase_ausgegeben": neu["coinbase_ausgegeben"],
                            "ausgegeben_vor_beobachtung": vor[0], "ohne_zeit": ohne_zeit})
    stand["erster_utc"], stand["letzter_utc"] = iso(stand["erster_ms"]), iso(stand["letzter_ms"])
    with open(st_p, "w", encoding="utf-8") as fh:
        json.dump(stand, fh, indent=1)
    return stand


def auswerten(daten, fenster, bis_ms=None):
    """je fenster: neue coinbase-ausgaben (anzahl, kas), davon in 24 h, 72 h, 7 tagen
    ausgegeben, median-verzug. Ein Verzug zaehlt nur, wenn der Beobachtungsrand
    (bis_ms, sonst letzter gelesener Kettenblock) mindestens so weit hinter dem
    Ende des Fensters liegt; sonst steht dort None."""
    stand = json.load(open(os.path.join(daten, "stand.json")))
    rand = bis_ms or stand["letzter_ms"]
    rein = lies_csv(os.path.join(daten, "rein.csv"))
    raus = {}
    for n in sorted(os.listdir(daten)):
        if n.startswith("raus-") and n.endswith(".json"):
            raus.update(json.load(open(os.path.join(daten, n))))
    aus = []
    for name, von, bis in fenster:
        a, b = ms(von), ms(bis)
        n = sum(int(r["anzahl"]) for r in rein if a <= int(r["minute_ms"]) < b)
        s = sum(int(r["sompi"]) for r in rein if a <= int(r["minute_ms"]) < b)
        hist = {}
        for st, eim in raus.items():
            if a <= int(st) < b:
                for k, (c, sp) in eim.items():
                    x = hist.setdefault(int(k), [0, 0])
                    x[0] += c
                    x[1] += sp
        e = {"fenster": name, "von": von, "bis": bis, "coinbase_ausgaben": n, "kas": s / 1e8,
             "beobachtet_bis": iso(rand), "erster_beobachtet": stand["erster_utc"]}
        for label, minuten in (("24h", 1440), ("72h", 4320), ("7d", 10080)):
            if rand - b < minuten * 60000:
                e["ausgegeben_" + label] = None
                continue
            c = sum(v[0] for k, v in hist.items() if k < minuten)
            sp = sum(v[1] for k, v in hist.items() if k < minuten)
            e["ausgegeben_" + label] = {"anzahl": c, "anteil": round(c / n, 4) if n else None, "kas": sp / 1e8,
                                        "anteil_kas": round(sp / s, 4) if s else None}
        # median ueber alle ausgaben des fensters; noch nicht ausgegebene liegen ueber jedem verzug
        ziel, lauf = n / 2, 0
        med = None
        for k in sorted(hist):
            lauf += hist[k][0]
            if lauf >= ziel and n:
                med = k
                break
        e["median_verzug_min"] = med
        e["median_bekannt_bis_min"] = (rand - b) // 60000
        aus.append(e)
    return aus


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)
    ok("eimer minute", eimer(59 * 60000 + 1) == 59 and eimer(400 * 60000) == 400 - 400 % 5 and eimer(10 ** 12) == 11520)
    with tempfile.TemporaryDirectory() as d:
        t0 = ms("2026-11-02T10:00:00Z")
        l1, l2, da = os.path.join(d, "l1"), os.path.join(d, "l2"), os.path.join(d, "daten")
        for p in (l1, l2):
            os.makedirs(p)
        # lauf 1: minuten 10:00 (daa 100..109) und 10:01 (110..119), zwei coinbase je minute
        schreib_csv(os.path.join(l1, "daa-zeit.csv"), ["minute_ms", "daa_min", "daa_max"],
                    [[t0, 100, 109], [t0 + 60000, 110, 119]])
        schreib_csv(os.path.join(l1, "rein.csv"), ["minute_ms", "anzahl", "sompi"], [[t0, 2, 200], [t0 + 60000, 2, 200]])
        schreib_csv(os.path.join(l1, "raus.csv"), ["erzeugt_daa", "ausgegeben_ms", "sompi"],
                    [[100, t0 + 30 * 60000, 100], [50, t0, 7]])
        json.dump({"ab_daa": 0, "erster_daa": 100, "erster_ms": t0, "letzter_daa": 119, "letzter_ms": t0 + 119000,
                   "pruning_punkt_ms": t0 - 1, "kettenbloecke": 20, "coinbase_neu": 4, "coinbase_ausgegeben": 2},
                  open(os.path.join(l1, "stand.json"), "w"))
        s1 = fortschreiben(l1, da, 1)
        ok("ausgabe vor der beobachtung zaehlt nicht", s1["laeufe"][0]["ausgegeben_vor_beobachtung"] == 1)
        # lauf 2: zwei tage spaeter, gibt die zweite ausgabe aus 10:01 nach 3 tagen aus
        schreib_csv(os.path.join(l2, "daa-zeit.csv"), ["minute_ms", "daa_min", "daa_max"], [[t0 + 4 * 86400000, 5000, 5000]])
        schreib_csv(os.path.join(l2, "rein.csv"), ["minute_ms", "anzahl", "sompi"], [])
        schreib_csv(os.path.join(l2, "raus.csv"), ["erzeugt_daa", "ausgegeben_ms", "sompi"],
                    [[110, t0 + 60000 + 3 * 86400000, 100]])
        json.dump({"ab_daa": 119, "erster_daa": 5000, "erster_ms": t0 + 4 * 86400000, "letzter_daa": 5000,
                   "letzter_ms": t0 + 9 * 86400000, "pruning_punkt_ms": t0, "kettenbloecke": 1, "coinbase_neu": 0,
                   "coinbase_ausgegeben": 1}, open(os.path.join(l2, "stand.json"), "w"))
        fortschreiben(l2, da, 2)
        try:
            fortschreiben(l2, da, 3)
            ok("derselbe lauf zweimal abgelehnt", False)
        except SystemExit:
            ok("derselbe lauf zweimal abgelehnt", True)
        e = auswerten(da, [("w", "2026-11-02T10:00:00Z", "2026-11-02T10:02:00Z")])[0]
        ok("vier neue, 400 sompi", e["coinbase_ausgaben"] == 4 and abs(e["kas"] - 4e-6) < 1e-12)
        ok("24 h: eine von vier", e["ausgegeben_24h"]["anzahl"] == 1 and e["ausgegeben_24h"]["anteil"] == 0.25)
        ok("7 tage: zwei von vier", e["ausgegeben_7d"]["anzahl"] == 2)
        ok("median nicht erreicht, solange die haelfte nicht ausgegeben ist", e["median_verzug_min"] == 4320)
        e2 = auswerten(da, [("w", "2026-11-02T10:00:00Z", "2026-11-02T10:02:00Z")], bis_ms=t0 + 3600000)[0]
        ok("ohne genug beobachtung kein anteil", e2["ausgegeben_24h"] is None)
        txt = "".join(open(os.path.join(da, n)).read() for n in os.listdir(da))
        ok("keine adresse im datenstand", "kaspa:" not in txt)
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fortschreiben")
    ap.add_argument("--lauf-id", default="")
    ap.add_argument("--daten", default="miner/daten")
    ap.add_argument("--auswerten", action="store_true")
    ap.add_argument("--fenster", nargs=3, action="append", metavar=("NAME", "VON", "BIS"))
    ap.add_argument("--bis-ms", type=int)
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.fortschreiben:
        s = fortschreiben(a.fortschreiben, a.daten, a.lauf_id)
        print(json.dumps(s["laeufe"][-1]))
        return 0
    if a.auswerten:
        print(json.dumps(auswerten(a.daten, a.fenster or [], a.bis_ms), indent=1))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
