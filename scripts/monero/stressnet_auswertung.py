#!/usr/bin/env python3
"""stressnet_auswertung.py - taegliche Auswertung des Monero-Stressnet-Zuhoerers (Ben, 07.11.2026).

Liest alle Laeufe unter data/monero-stressnet (*/bloecke.csv und
*/ankuendigungen.csv), vereinigt die Bloecke nach Hash und baut die
Hauptkette von der hoechsten Spitze rueckwaerts ueber die Vorgaenger.

Je UTC-Tag (nach Kopfzeit des Blocks):
  - Blockabstaende nach Kopfzeit, counted: Median, p90, p99, Mittel, Anteil
    ueber 10 min, negative Abstaende, laengste Luecke
  - dagegen computed fuer ein Ziel von 120 s und exponentielle Abstaende:
    Median 83,2 s, p90 276,3 s, p99 552,6 s, Anteil ueber 10 min 0,674 %
  - Spread der Ersten Sicht ueber unsere Peers (je Block erste minus letzte
    Ankunft, nur Bloecke mit mindestens 2 Peers): Median, p90
  - Erste Sicht minus Kopfzeit: Median
  - Abdeckung: Anteil der Kettenbloecke, die uns angekuendigt wurden

Quantile mit linearer Interpolation wie PH-M-001. Keine Adressen, Peers nur
als peer_N je Lauf.

  python3 scripts/monero/stressnet_auswertung.py --daten data/monero-stressnet
  python3 scripts/monero/stressnet_auswertung.py --selbsttest
"""
import argparse
import csv
import glob
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

ZIEL_S = 120
MODELL = {"median_s": round(ZIEL_S * math.log(2), 1), "p90_s": round(ZIEL_S * math.log(10), 1),
          "p99_s": round(ZIEL_S * math.log(100), 1), "anteil_ueber_600s_pct": round(100 * math.exp(-600 / ZIEL_S), 3)}


def t(s):
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    raise ValueError(s)


def quantil(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    p = (len(xs) - 1) * q
    u = math.floor(p)
    o = min(u + 1, len(xs) - 1)
    return xs[u] + (xs[o] - xs[u]) * (p - u)


def r1(x):
    return None if x is None else round(x, 1)


def lesen(daten):
    bloecke, ank = {}, {}
    for f in sorted(glob.glob(os.path.join(daten, "**", "bloecke.csv"), recursive=True)):
        lauf = os.path.relpath(os.path.dirname(f), daten)
        with open(f, newline="") as fh:
            for z in csv.DictReader(fh):
                b = bloecke.setdefault(z["hash"], {"hoehe": int(z["hoehe"]), "hash": z["hash"], "prev": z["prev_hash"],
                                                   "zeit": t(z["header_zeit_utc"]), "major": z["major"],
                                                   "minor": z["minor"], "n_tx": int(z["n_tx"]), "first_seen": None})
                fs = z.get("first_seen_utc") or ""
                if fs and (b["first_seen"] is None or t(fs) < b["first_seen"]):
                    b["first_seen"] = t(fs)
        a = os.path.join(os.path.dirname(f), "ankuendigungen.csv")
        if os.path.exists(a):
            with open(a, newline="") as fh:
                for z in csv.DictReader(fh):
                    key = (lauf, z["peer"])
                    d = ank.setdefault(z["hash"], {})
                    d[key] = min(d.get(key, 1e18), t(z["ankunft_utc"]))
    return bloecke, ank


def hauptkette(bloecke):
    if not bloecke:
        return []
    spitze = max(bloecke.values(), key=lambda b: (b["hoehe"], -b["zeit"]))
    kette, b = [], spitze
    while b:
        kette.append(b)
        b = bloecke.get(b["prev"])
    return kette[::-1]


def auswerten(daten):
    bloecke, ank = lesen(daten)
    kette = hauptkette(bloecke)
    in_kette = {b["hash"] for b in kette}
    abseits = [b for b in bloecke.values() if b["hash"] not in in_kette and b["hoehe"] <= (kette[-1]["hoehe"] if kette else 0)]
    tage = {}
    for i, b in enumerate(kette):
        tag = datetime.fromtimestamp(b["zeit"], timezone.utc).strftime("%Y-%m-%d")
        d = tage.setdefault(tag, {"abstaende": [], "bloecke": 0, "angekuendigt": 0, "spreads": [], "verzug": [],
                                  "peers": [], "hoehen": [b["hoehe"], b["hoehe"]], "n_tx": 0})
        d["bloecke"] += 1
        d["n_tx"] += b["n_tx"]
        d["hoehen"][1] = b["hoehe"]
        if i > 0:
            d["abstaende"].append((b["zeit"] - kette[i - 1]["zeit"], b["hoehe"]))
        a = ank.get(b["hash"], {})
        if a:
            d["angekuendigt"] += 1
            d["peers"].append(len(a))
            d["verzug"].append(min(a.values()) - b["zeit"])
            if len(a) >= 2:
                d["spreads"].append((max(a.values()) - min(a.values())) * 1000)
    zeilen = []
    for tag in sorted(tage):
        d = tage[tag]
        ab = [x for x, _ in d["abstaende"]]
        lang = max(d["abstaende"], default=(None, None))
        zeilen.append({
            "tag_utc": tag, "hoehen": d["hoehen"], "bloecke": d["bloecke"], "abstaende": len(ab),
            "median_s": r1(quantil(ab, 0.5)), "p90_s": r1(quantil(ab, 0.9)), "p99_s": r1(quantil(ab, 0.99)),
            "mittel_s": r1(statistics.fmean(ab)) if ab else None,
            "anteil_ueber_600s_pct": round(100 * sum(1 for x in ab if x > 600) / len(ab), 2) if ab else None,
            "negative": sum(1 for x in ab if x < 0),
            "laengste_luecke_s": lang[0], "laengste_luecke_vor_block": lang[1],
            "tx_in_bloecken": d["n_tx"],
            "abdeckung_pct": round(100 * d["angekuendigt"] / d["bloecke"], 1),
            "peers_je_block_median": r1(quantil(d["peers"], 0.5)),
            "spread_ms_median": r1(quantil(d["spreads"], 0.5)), "spread_ms_p90": r1(quantil(d["spreads"], 0.9)),
            "bloecke_mit_spread": len(d["spreads"]),
            "erste_sicht_minus_kopfzeit_s_median": r1(quantil(d["verzug"], 0.5)),
        })
    zus = {
        "erstellt_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "ziel_s": ZIEL_S, "computed": MODELL,
        "kette": {"bloecke": len(kette), "hoehen": [kette[0]["hoehe"], kette[-1]["hoehe"]] if kette else None,
                  "von_utc": datetime.fromtimestamp(kette[0]["zeit"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if kette else None,
                  "bis_utc": datetime.fromtimestamp(kette[-1]["zeit"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if kette else None,
                  "luecken_in_der_kette": sum(1 for i in range(1, len(kette)) if kette[i]["hoehe"] != kette[i - 1]["hoehe"] + 1)},
        "abseits_der_kette": len(abseits),
        "tage": zeilen,
        "art": "counted aus eigenen Koepfen und eigener Ersten Sicht, computed fuer exponentielle Abstaende mit Mittel 120 s",
        "grenzen": "ein Zuhoerer an einem Ort; Arbeitsnachweis nicht geprueft, Hash selbst nachgerechnet und durch den Nachfolger bestaetigt",
    }
    return kette, zus


def schreiben(daten, kette, zus):
    aus = os.path.join(daten, "auswertung")
    os.makedirs(aus, exist_ok=True)
    with open(os.path.join(daten, "koepfe.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hoehe", "hash", "prev_hash", "header_zeit_utc", "major", "minor", "n_tx"])
        for b in kette:
            w.writerow([b["hoehe"], b["hash"], b["prev"],
                        datetime.fromtimestamp(b["zeit"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        b["major"], b["minor"], b["n_tx"]])
    with open(os.path.join(aus, "zusammenfassung.json"), "w") as f:
        json.dump(zus, f, indent=1)
    if zus["tage"]:
        with open(os.path.join(aus, "tage.csv"), "w", newline="") as f:
            felder = [k for k in zus["tage"][0] if k != "hoehen"]
            w = csv.DictWriter(f, fieldnames=["hoehe_von", "hoehe_bis"] + felder)
            w.writeheader()
            for z in zus["tage"]:
                w.writerow({"hoehe_von": z["hoehen"][0], "hoehe_bis": z["hoehen"][1],
                            **{k: z[k] for k in felder}})


def selbsttest():
    import tempfile
    fehler = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, "" if bed else "  " + str(info)))
        if not bed:
            fehler.append(name)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "lauf", "a"))
        h = lambda n: f"{n:064x}"
        zeit0 = t("2026-11-07 10:00:00")
        abst = [100, 200, 50, 700, -5, 120]
        with open(os.path.join(d, "lauf", "a", "bloecke.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hoehe", "hash", "prev_hash", "header_zeit_utc", "major", "minor", "n_tx", "quelle",
                        "first_seen_utc", "peers_n", "spread_ms", "prev_ist_unser_hash"])
            z = zeit0
            for i in range(7):
                z += abst[i - 1] if i else 0
                fs = datetime.fromtimestamp(z + 10, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if i % 2 == 0 else ""
                w.writerow([1000 + i, h(1000 + i), h(999 + i), datetime.fromtimestamp(z, timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"), 18, 18, 0, "x", fs, 0, "", "ja"])
            w.writerow([1003, h(9999), h(1002), "2026-11-07 10:06:00", 18, 18, 0, "x", "", 0, "", "ja"])  # abseits
        with open(os.path.join(d, "lauf", "a", "ankuendigungen.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hash", "peer", "ankunft_utc"])
            w.writerow([h(1000), "peer_1", "2026-11-07 10:00:10.000"])
            w.writerow([h(1000), "peer_2", "2026-11-07 10:00:10.250"])
        kette, zus = auswerten(d)
        tag = zus["tage"][0]
        ok("kette ohne abseits-block", len(kette) == 7 and zus["abseits_der_kette"] == 1, (len(kette), zus["abseits_der_kette"]))
        ok("sechs abstaende", tag["abstaende"] == 6, tag)
        ok("median linear", tag["median_s"] == 110.0, tag["median_s"])
        ok("negativer abstand gezaehlt", tag["negative"] == 1)
        ok("anteil ueber 600 s", tag["anteil_ueber_600s_pct"] == round(100 / 6, 2), tag["anteil_ueber_600s_pct"])
        ok("laengste luecke", tag["laengste_luecke_s"] == 700 and tag["laengste_luecke_vor_block"] == 1004)
        ok("spread 250 ms", tag["spread_ms_median"] == 250.0, tag["spread_ms_median"])
        ok("computed median 83.2", zus["computed"]["median_s"] == 83.2)
        schreiben(d, kette, zus)
        ok("koepfe.csv geschrieben", os.path.exists(os.path.join(d, "koepfe.csv")))
    print("")
    print("%d fehler" % len(fehler) if fehler else "alle testfaelle bestanden")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--daten", default="data/monero-stressnet")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    kette, zus = auswerten(a.daten)
    schreiben(a.daten, kette, zus)
    print(json.dumps({"kette": zus["kette"], "tage": len(zus["tage"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
