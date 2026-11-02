#!/usr/bin/env python3
"""report_v1.py - Rohwerte M1 bis M7 fuer den PulseHawk Upgrade Report v1 (Ben, 02.11.2026).

Spezifikation v1 (pulsehawk.io/standard), je Upgrade:
  M1  Blockabstaende p50, p90, p99 gegen das Ziel
  M2  laengste Luecke, Zahl der Luecken ueber 5 x Ziel
  M3  Reorgs: Zahl und groesste Tiefe
  M4  Kettenspaltung: Dauer
  M5  Peer-Probe bei Aktivierung, +24 h, +72 h (dazu +6 h), jeweils mit n
  M6  Zeit bis stabil: gleitender 1-h-p50 innerhalb 10 % des Ziels
  M7  erster Block ab der Aktivierungshoehe: Zeit und Abstand zu unserer Schaetzung

Jede Zeile traegt ihre Art: counted (selbst gezaehlt), source (fremde Angabe,
Quelle genannt), computed (gerechnet: Modell, Schaetzung, Differenz zu einer
Schaetzung). Dazu Fenster in UTC und n. Die CSV bekommt eine Datei .sha256 im
Format von sha256sum.

Fenster: t_akt ist die Kopfzeit des Blocks auf der Aktivierungshoehe.
  vor   Bloecke unter der Aktivierungshoehe ab t_akt - 24 h
  nach  Bloecke ab der Aktivierungshoehe bis t_akt + 72 h
Abgegrenzt wird ueber die Hoehe: der erste Block mit Kopfzeit ab der
Grenze und alle danach (Kopfzeiten muessen nicht steigen).

Eingang:
  --koepfe  eigene gepruefte Koepfe (hoehe,hash,zeit,nbits), z. B.
            data/zcash-mainnet/koepfe.csv.gz von messung/zcash-mainnet
  --roh     Ordner aus roh_export.py (wache-log.csv, zustand.json,
            ereignisse.jsonl.gz), fuer M3, M4, M5 und die erste Sicht in M7.
            Ohne --roh stehen diese Zeilen mit "fehlt" im Bericht.

  python3 scripts/wache/report_v1.py --kette scripts/wache/ketten/zcash-mainnet.json \\
      --koepfe koepfe.csv.gz --roh wache/roh --aus wache/report
"""
import argparse
import bisect
import csv
import gzip
import hashlib
import io
import json
import math
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from wache_kern import ts, utc  # noqa: E402

SPALTEN = ["metrik", "kennzahl", "wert", "einheit", "art", "fenster_von_utc", "fenster_bis_utc", "n", "quelle",
           "anmerkung"]
VOR_H, NACH_H = 24, 72
STABIL_FENSTER_S, STABIL_HALTEN_S, STABIL_TOLERANZ = 3600, 3600, 0.10


def quantil(s, q):
    s = sorted(s)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def r(x, n=1):
    return "" if x is None else round(x, n)


def koepfe_lesen(pfad):
    opener = gzip.open if pfad.endswith(".gz") else open
    with opener(pfad, "rt") as f:
        z = {int(x["hoehe"]): (x["hash"], int(x["zeit"])) for x in csv.DictReader(f)}
    return z


def grenzen(kette, akt, t_akt):
    hoehen = sorted(kette)
    vor = [h for h in hoehen if h < akt]
    a = next((i for i, h in enumerate(vor) if kette[h][1] >= t_akt - VOR_H * 3600), None)
    vor = vor[a:] if a is not None else []
    nach = [h for h in hoehen if h >= akt]
    e = next((i for i, h in enumerate(nach) if kette[h][1] >= t_akt + NACH_H * 3600), None)
    nach = nach[:e] if e is not None else nach
    return vor, nach


def abstaende(kette, hoehen):
    return [(h, kette[h][1] - kette[h - 1][1]) for h in hoehen if h - 1 in kette]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kette", required=True)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--roh")
    ap.add_argument("--aus", required=True)
    ap.add_argument("--hoehe", type=int, help="Aktivierungshoehe statt der aus der Konfiguration (Test)")
    ap.add_argument("--schaetzung", help="Schaetzung UTC statt erwartet_utc (Test)")
    ap.add_argument("--band", nargs=2, help="90-%%-Band UTC statt band_utc (Test)")
    ap.add_argument("--quelle-hoehe", default="ZIP 259; Zebra 7.0.0 zebra-chain/src/parameters/constants.rs",
                    help="Beleg der Aktivierungshoehe")
    args = ap.parse_args()

    cfg = json.load(open(args.kette))
    akt = args.hoehe or cfg["aktivierung"]["hoehe"]
    name = cfg["aktivierung"]["name"]
    ziel_vor, ziel_nach = cfg["ziel_s"], cfg["ziel_nach_s"]
    schaetzung = ts(args.schaetzung or cfg["aktivierung"]["erwartet_utc"])
    band = args.band or cfg["aktivierung"].get("band_utc")
    kette = koepfe_lesen(args.koepfe)
    if akt not in kette:
        sys.exit(f"hoehe {akt} nicht in den koepfen (bereich {min(kette)} bis {max(kette)})")
    t_akt = kette[akt][1]
    vor, nach = grenzen(kette, akt, t_akt)
    zeilen = []
    quelle_k = os.path.basename(args.koepfe)

    def zeile(m, k, wert, einheit, art, von, bis, n, quelle="", anm=""):
        zeilen.append({"metrik": m, "kennzahl": k, "wert": wert, "einheit": einheit, "art": art,
                       "fenster_von_utc": utc(von) if isinstance(von, (int, float)) else von,
                       "fenster_bis_utc": utc(bis) if isinstance(bis, (int, float)) else bis,
                       "n": n, "quelle": quelle, "anmerkung": anm})

    fenster = {}
    for teil, hoehen, ziel in (("vor", vor, ziel_vor), ("nach", nach, ziel_nach)):
        if not hoehen:
            continue
        ab = abstaende(kette, hoehen)
        w = [x for _, x in ab]
        von, bis = kette[hoehen[0]][1], kette[hoehen[-1]][1]
        fenster[teil] = (von, bis, ab, ziel)
        n = len(w)
        hb = f"hoehen {hoehen[0]} bis {hoehen[-1]}"
        zeile("M1", f"ziel_{teil}", ziel, "s", "source", von, bis, "", cfg.get("_ziel_quelle", "ZIP 208, ZIP 218"),
              "Zielabstand")
        for q, nm, faktor in ((0.5, "p50", math.log(2)), (0.9, "p90", math.log(10)), (0.99, "p99", math.log(100))):
            zeile("M1", f"{nm}_{teil}", r(quantil(w, q)), "s", "counted", von, bis, n, quelle_k, hb)
            zeile("M1", f"{nm}_{teil}_modell", r(faktor * ziel), "s", "computed", von, bis, "", "",
                  "Erwartung bei exponentiellen Abstaenden mit Mittel = Ziel")
        zeile("M1", f"mittel_{teil}", r(sum(w) / n, 2), "s", "counted", von, bis, n, quelle_k, hb)
        zeile("M1", f"negativ_{teil}", sum(1 for x in w if x < 0), "abstaende", "counted", von, bis, n, quelle_k,
              "Kopfzeit kleiner als beim Vorgaenger")
        h_max, l_max = max(ab, key=lambda z: z[1])
        zeile("M2", f"laengste_luecke_{teil}", l_max, "s", "counted", von, bis, n, quelle_k,
              f"vor Block {h_max}, Kopfzeit {utc(kette[h_max][1])} UTC")
        ueber = sum(1 for x in w if x > 5 * ziel)
        zeile("M2", f"luecken_ueber_5x_ziel_{teil}", ueber, "abstaende", "counted", von, bis, n, quelle_k,
              f"Abstand ueber {5 * ziel} s")
        zeile("M2", f"luecken_ueber_5x_ziel_{teil}_modell", r(n * math.exp(-5), 1), "abstaende", "computed",
              von, bis, n, "", "n x e^-5 bei exponentiellen Abstaenden")

    # ---------------------------------------------------- Rohdaten der Wache
    log, zustand, erst_ms = [], {}, {}
    if args.roh:
        lp = os.path.join(args.roh, "wache-log.csv")
        if os.path.exists(lp):
            log = list(csv.DictReader(open(lp)))
        zp = os.path.join(args.roh, "zustand.json")
        if os.path.exists(zp):
            zustand = json.load(open(zp))
        ep = os.path.join(args.roh, "ereignisse.jsonl.gz")
        if os.path.exists(ep):
            with gzip.open(ep, "rt") as f:
                for z in f:
                    e = json.loads(z)
                    if e["hash"] not in erst_ms or e["t_ms"] < erst_ms[e["hash"]]:
                        erst_ms[e["hash"]] = e["t_ms"]
    quelle_w = "wache-log.csv (eigener Zuhoerer)"

    def im(zeit_text, von, bis):
        t = ts(zeit_text.replace(" ", "T") + "Z")
        return von <= t < bis

    for teil, (von, bis, ab, _) in fenster.items():
        bis_log = bis + 1  # die letzte Sekunde des Fensters mitnehmen
        if not log:
            zeile("M3", f"reorgs_{teil}", "fehlt", "", "counted", von, bis, "", "", "kein Log der Wache")
            zeile("M4", f"kettenspaltung_dauer_{teil}", "fehlt", "", "counted", von, bis, "", "", "kein Log der Wache")
            continue
        ro = [z for z in log if z["signal"] == "reorg_gesehen" and im(z["utc"], von, bis_log)]
        tiefen = [int(float(z["wert"])) for z in ro]
        zeile("M3", f"reorgs_{teil}", len(tiefen), "reorgs", "counted", von, bis, len(ab), quelle_w,
              "jeder Wechsel unserer Spitze auf einen anderen Zweig, auch Tiefe 1; n = Bloecke im Fenster")
        zeile("M3", f"reorg_max_tiefe_{teil}", max(tiefen) if tiefen else 0, "bloecke", "counted", von, bis,
              len(tiefen), quelle_w, "")
        # M4: Episoden des Signals kettenspaltung (Alarm bis Entwarnung)
        eps, start = [], None
        for z in log:
            if z["signal"] != "kettenspaltung":
                continue
            t = ts(z["utc"].replace(" ", "T") + "Z")
            if z["stufe"] == "alarm" and start is None:
                start = t
            elif z["stufe"] == "entwarnung" and start is not None:
                eps.append((start, t))
                start = None
        if start is not None:
            eps.append((start, bis))
        eps = [(max(a, von), min(b, bis)) for a, b in eps if b > von and a < bis]
        k = cfg["signale"]["kettenspaltung"]
        defi = (f"Signal kettenspaltung: zwei Zweige ab der Aktivierungshoehe, je mindestens {k['min_peers']} Peers, "
                f"beide tiefer als {k['min_tiefe']} Bloecke")
        zeile("M4", f"kettenspaltung_dauer_{teil}", round(sum(b - a for a, b in eps)), "s", "counted", von, bis,
              len(eps), quelle_w, defi + "; n = Episoden")
        zeile("M4", f"kettenspaltung_laengste_{teil}", round(max((b - a for a, b in eps), default=0)), "s",
              "counted", von, bis, len(eps), quelle_w, "")

    # M5 Peer-Proben
    proben = zustand.get("proben", {})
    for vers in [str(x) for x in cfg["signale"]["peers_vor_upgrade"]["zeitpunkte_h"]]:
        titel = "aktivierung" if vers == "0" else f"aktivierung_plus_{vers}h"
        p = proben.get(vers)
        if not p:
            zeile("M5", f"peers_unter_min_protokoll_{titel}", "fehlt", "%", "counted", "", "", "", "",
                  "keine Probe im Zustand der Wache")
            continue
        zeile("M5", f"peers_unter_min_protokoll_{titel}", p["anteil_prozent"], "%", "counted", p["utc"], p["utc"],
              p["peers"], "zustand.json (eigene Probe, Handschlag)",
              f"{p['vor_upgrade']} von {p['peers']} unter {cfg['min_protokoll']}; versionen {p.get('versionen', {})}")

    # M6 Zeit bis stabil
    if "nach" in fenster:
        von, bis, ab, ziel = fenster["nach"]
        punkte = sorted((kette[h][1], x) for h, x in ab)
        zeiten = [t for t, _ in punkte]
        p50, mittel = [], []
        for i, (t, _) in enumerate(punkte):
            if t < von + STABIL_FENSTER_S:
                continue
            a = bisect.bisect_right(zeiten, t - STABIL_FENSTER_S)
            w60 = [x for _, x in punkte[a:i + 1]]
            p50.append((t, quantil(w60, 0.5)))
            mittel.append((t, sum(w60) / len(w60)))
        # "ziel" ist die Spezifikation woertlich. Bei exponentiellen Abstaenden
        # liegt der Median aber bei ln2 x Ziel (25 s: 17,3 s); deshalb zum
        # Vergleich "modell" und das 60-min-Mittel gegen das Ziel (Frage an Ben).
        for bez, verlauf, ref, art_ref in (("ziel", p50, ziel, "p50 gegen Ziel"),
                                           ("modell", p50, math.log(2) * ziel, "p50 gegen ln2 x Ziel"),
                                           ("mittel", mittel, ziel, "Mittel gegen Ziel")):
            lo, hi = ref * (1 - STABIL_TOLERANZ), ref * (1 + STABIL_TOLERANZ)
            drin = [lo <= p <= hi for _, p in verlauf]
            stabil = None
            for i, (t, _) in enumerate(verlauf):
                if not drin[i]:
                    continue
                j = i
                while j < len(verlauf) and verlauf[j][0] <= t + STABIL_HALTEN_S and drin[j]:
                    j += 1
                if j == len(verlauf) or verlauf[j][0] > t + STABIL_HALTEN_S:
                    stabil = t
                    break
            anm = (f"gleitend ueber die Abstaende der letzten 60 min, {art_ref} = {round(ref, 2)} s "
                   f"+-10 %; stabil = erster Zeitpunkt, ab dem er 60 min ohne Unterbrechung im Band bleibt")
            zeile("M6", f"zeit_bis_stabil_{bez}", round((stabil - von) / 60, 1) if stabil else "nie", "min",
                  "counted", von, bis, len(verlauf), quelle_k, anm + (f"; stabil ab {utc(stabil)} UTC" if stabil else ""))
            zeile("M6", f"anteil_im_band_{bez}", r(100 * sum(drin) / len(drin) if drin else None), "%", "counted",
                  von, bis, len(verlauf), quelle_k, "Anteil der Zeitpunkte, an denen der gleitende p50 im Band liegt")
        zeile("M6", "p50_modell", r(math.log(2) * ziel, 2), "s", "computed", von, bis, "", "",
              "Median exponentieller Abstaende mit Mittel = Ziel")

    # M7 erster Block ab der Aktivierungshoehe
    h_akt, t_kopf = kette[akt]
    zeile("M7", "aktivierungshoehe", akt, "hoehe", "source", "", "", "", args.quelle_hoehe, name)
    zeile("M7", "erster_block_kopfzeit", utc(t_kopf), "UTC", "counted", t_kopf, t_kopf, 1, quelle_k,
          f"hash {h_akt}")
    erst = erst_ms.get(h_akt)
    if erst is None and zustand.get("aktiv_gesehen_utc"):
        erst = ts(zustand["aktiv_gesehen_utc"]) * 1000
    if erst is not None:
        zeile("M7", "erster_block_erste_sicht", utc(erst / 1000), "UTC", "counted", erst / 1000, erst / 1000, 1,
              "eigener Zuhoerer", "erste Ankuendigung bei uns")
        zeile("M7", "erste_sicht_minus_kopfzeit", round(erst / 1000 - t_kopf, 1), "s", "counted", "", "", 1,
              "", "")
    else:
        zeile("M7", "erster_block_erste_sicht", "fehlt", "UTC", "counted", "", "", "", "", "keine Rohdaten des Zuhoerers")
    zeile("M7", "schaetzung", utc(schaetzung), "UTC", "computed", "", "", "", "unsere Vorhersage",
          f"90-%-Band {band[0]} bis {band[1]}" if band else "")
    zeile("M7", "kopfzeit_minus_schaetzung", round(t_kopf - schaetzung), "s", "computed", "", "", 1, "",
          "positiv: spaeter als geschaetzt")
    if band:
        drin = ts(band[0]) <= t_kopf <= ts(band[1])
        zeile("M7", "im_band", "ja" if drin else "nein", "", "computed", band[0], band[1], 1, "", "")

    os.makedirs(args.aus, exist_ok=True)
    stamm = f"report-v1-{cfg['kette']}-{name}"
    puffer = io.StringIO()
    w = csv.DictWriter(puffer, fieldnames=SPALTEN, lineterminator="\n")
    w.writeheader()
    w.writerows(zeilen)
    inhalt = puffer.getvalue().encode()
    pfad = os.path.join(args.aus, stamm + ".csv")
    with open(pfad, "wb") as f:
        f.write(inhalt)
    summe = hashlib.sha256(inhalt).hexdigest()
    with open(pfad + ".sha256", "w") as f:
        f.write(f"{summe}  {stamm}.csv\n")
    eingang = {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest()
               for p in [args.koepfe] + ([os.path.join(args.roh, x) for x in sorted(os.listdir(args.roh))]
                                         if args.roh and os.path.isdir(args.roh) else []) if os.path.isfile(p)}
    with open(os.path.join(args.aus, stamm + "-eingang.json"), "w") as f:
        json.dump({"csv_sha256": summe, "eingang_sha256": eingang, "aktivierungshoehe": akt,
                   "t_akt_kopfzeit_utc": utc(t_akt)}, f, indent=1)
    print(json.dumps({"csv": pfad, "sha256": summe, "zeilen": len(zeilen)}))


if __name__ == "__main__":
    main()
