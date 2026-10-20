#!/usr/bin/env python3
"""tempnet_auswertung.py - zaehlt das BCH Tempnet 2027 (Faster Blocks, 60 s).

Eingang: CSV aus tempnet_koepfe.py (hoehe,hash,zeit,nbits,version), deren
Meta-JSON, optional die chaingraph-Gegenprobe (bch_gegenprobe.py).
Ausgang: JSON mit allen Zahlen und ein kurzer Bericht (Markdown), beide mit
Fenster (von/bis UTC, Blockhoehen).

Festlegungen, absichtlich hier im Code:
- Bereich: ab 327.989 (erster Tempnet-Block) bis zum hoechsten Block mit
  Zeitstempel <= Stichtag. Der erste gezaehlte Abstand ist der von 327.990;
  327.988 ist noch ein Chipnet-Block.
- Abstand = Zeitstempel minus Zeitstempel des Vorgaengers, ungeschoent (null
  und negativ bleiben drin).
- MTP = Median der Zeitstempel der letzten 11 Bloecke. MTP-Verzug eines Blocks
  = sein Zeitstempel minus MTP der 11 Bloecke davor. Gegen die Abrufzeit:
  Abrufzeit minus MTP der Spitze, und Abrufzeit minus Zeitstempel der Spitze.
- Schwierigkeit = Ziel(powLimit 0x1d00ffff) / Ziel(nBits), wie getdifficulty.
- Nachfuehrung wie beim Zcash-NU7-Bericht: Fenster 100 Bloecke, Sprung ab
  Faktor 2 (vom folgenden Fenster bestaetigt), eingeholt bei +-15 % der
  Hashrate der folgenden 100 Bloecke mal 60 s; Bloecke und Minuten werden je
  Sprung zusammen gemessen.
- Erwartung: exponentielle Abstaende mit 60 s Mittel; Summen davon nach
  Erlang; MTP-Groessen per Simulation (feste Saat, 200.000 Ziehungen).

Kein Kurs, keine Bewertung. Nur Zahlen.
"""
import argparse
import csv
import gzip
import json
import math
import random
import statistics
from collections import OrderedDict
from datetime import datetime, timezone

ERSTER = 327_989
ZIEL_S = 60.0
POW_LIMIT_BITS = 0x1D00FFFF
FENSTER = 100
SPRUNG = 2.0
NAEHE = 0.15
LANG_S = 300          # "ueber 5 min"
N_FENSTER = 10        # 10 Bloecke gegen 1 Block a 600 s
ALT_S = 600.0


def ziel(bits):
    exp, mant = bits >> 24, bits & 0x007FFFFF
    return mant >> (8 * (3 - exp)) if exp <= 3 else mant << (8 * (exp - 3))


def schwierigkeit(bits):
    return ziel(POW_LIMIT_BITS) / ziel(bits)


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(s, q):
    s = sorted(s)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def erlang_cdf(x, n, m):
    lam, term, summe = x / m, math.exp(-x / m), 0.0
    for k in range(n):
        summe += term
        term *= lam / (k + 1)
    return 1 - summe


def erlang_q(q, n, m):
    lo, hi = 0.0, m * n * 20
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if erlang_cdf(mid, n, m) < q else (lo, mid)
    return (lo + hi) / 2


def kennzahlen(werte):
    s = sorted(werte)
    return {"anzahl": len(s), "mittel": round(sum(s) / len(s), 2), "median": quantil(s, 0.5),
            "p90": round(quantil(s, 0.9), 1), "p99": round(quantil(s, 0.99), 1), "max": s[-1]}


def mtp_simulation(n=200_000, saat=2027):
    """Erwartung fuer den MTP-Verzug bei idealen 60-s-Bloecken (exponentiell)."""
    rnd = random.Random(saat)
    verzug, alter_mtp, alter_spitze = [], [], []
    for _ in range(n):
        # 11 Abstaende vor dem Block: Zeitstempel relativ zum Block (0)
        t, zeiten = 0.0, []
        for _ in range(11):
            t -= rnd.expovariate(1 / ZIEL_S)
            zeiten.append(t)
        verzug.append(-statistics.median(zeiten))
        # Abruf zu zufaelliger Zeit: Alter der Spitze ist exponentiell (gedaechtnislos)
        a = rnd.expovariate(1 / ZIEL_S)
        alter_spitze.append(a)
        # MTP der Spitze = Median der letzten 11 Bloecke inkl. Spitze
        letzte = [0.0] + zeiten[:10]
        alter_mtp.append(a - statistics.median(letzte))
    return {"verzug_block": kennzahlen(verzug), "abruf_minus_mtp": kennzahlen(alter_mtp),
            "abruf_minus_spitze": kennzahlen(alter_spitze), "ziehungen": n, "saat": saat}


def nachfuehrung(hoehen, zeiten, diffs):
    W, n = FENSTER, len(hoehen)

    def rate(a, b):
        dt = zeiten[b] - zeiten[a]
        return sum(diffs[a + 1:b + 1]) / dt if dt > 0 else None

    def passt(j):
        if j + W >= n:
            return False
        h = rate(j, j + W)
        return bool(h) and abs(diffs[j] / (h * ZIEL_S) - 1) <= NAEHE

    grenzen, b = [], W
    while b + 2 * W < n:
        vor, nach, danach = rate(b - W, b), rate(b, b + W), rate(b + W, b + 2 * W)
        ok = (vor and nach and danach and nach != vor
              and math.log(danach / vor) / math.log(nach / vor) >= 0.5)
        if ok and (nach / vor >= SPRUNG or vor / nach >= SPRUNG):
            grenzen.append((b, nach / vor))
            b += 2 * W
        else:
            b += W // 2
    ev = []
    for i, (b, f) in enumerate(grenzen):
        ende = grenzen[i + 1][0] if i + 1 < len(grenzen) else n
        k = next((j for j in range(b, min(b + 2000, ende)) if passt(j) and passt(j + W // 4)), None)
        ev.append({"grenze_hoehe": hoehen[b], "zeit_utc": utc(zeiten[b]), "faktor_hashrate": round(f, 2),
                   "eingeholt_nach_bloecken": (k - b) if k is not None else None,
                   "eingeholt_nach_min": round((zeiten[k] - zeiten[b]) / 60, 1) if k is not None else None,
                   "abgeloest": k is None and ende < n and ende < b + 2000,
                   "offen_am_stichtag": k is None and ende >= n})
    ein = [e for e in ev if e["eingeholt_nach_bloecken"] is not None]
    return {
        "methode": f"Fenster {W} Bloecke, Sprung ab Faktor {SPRUNG} (bestaetigt), eingeholt bei +-{int(NAEHE*100)} %",
        "spruenge": len(ev), "eingeholt": len(ein),
        "abgeloest": sum(1 for e in ev if e["abgeloest"]),
        "offen_am_stichtag": sum(1 for e in ev if e["offen_am_stichtag"]),
        # Bloecke und Minuten ueber dieselben eingeholten Spruenge
        "median_bloecke": statistics.median([e["eingeholt_nach_bloecken"] for e in ein]) if ein else None,
        "median_min": statistics.median([e["eingeholt_nach_min"] for e in ein]) if ein else None,
        "max_bloecke": max((e["eingeholt_nach_bloecken"] for e in ein), default=None),
        "ereignisse": ev,
    }


def je_tag(hoehen, zeiten, diffs):
    tage = OrderedDict()
    for i in range(len(hoehen)):
        tage.setdefault(datetime.fromtimestamp(zeiten[i], timezone.utc).strftime("%Y-%m-%d"), []).append(i)
    out = []
    for tag, idx in sorted(tage.items()):
        ab = [zeiten[i] - zeiten[i - 1] for i in idx if i > 0]
        out.append({"tag_utc": tag, "bloecke": len(idx), "von": hoehen[min(idx)], "bis": hoehen[max(idx)],
                    "mittlerer_abstand_s": round(sum(ab) / len(ab), 1) if ab else None,
                    "schwierigkeit_median": round(statistics.median(diffs[i] for i in idx), 2)})
    return out


def tabelle(kopf, zeilen):
    t = ["| " + " | ".join(kopf) + " |", "|" + "|".join(" --- " for _ in kopf) + "|"]
    return "\n".join(t + ["| " + " | ".join(str(x) for x in z) + " |" for z in zeilen])


def de(x, nk=1):
    if x is None:
        return "–"
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bericht(r):
    B, A, E, M, F, N, G = (r["bereich"], r["abstaende"], r["erwartung_abstaende"], r["mtp"],
                          r["fenster_10"], r["nachfuehrung"], r.get("gegenprobe_chaingraph"))
    z = [f"# BCH Tempnet 2027 (Faster Blocks), Zählung Stand {r['stichtag_utc']}", "",
         f"**Fenster:** {B['von_zeit_utc']} bis {B['bis_zeit_utc']} UTC, Blöcke {de(B['von_hoehe'])} bis "
         f"{de(B['bis_hoehe'])} ({de(B['bloecke'])} Blöcke). **Abruf:** {r['quelle']['abruf_utc']}.", "",
         "Quelle: eigene Header über P2P (`scripts/bch/tempnet_koepfe.py`), geprüft auf Verkettung und PoW gegen "
         "nBits, erster Tempnet-Block 327.989 als Fixpunkt, Gegenprobe mit weiteren Peers: "
         + (", ".join(f"{g['agent']} {g['gleich']}/{g['verglichen']}" for g in r["quelle"].get("gegenproben", [])) or "keine")
         + ". Peer-Software: " + ", ".join(r["quelle"].get("peer_software", [])) + ".", "",
         "Gegenprobe source chaingraph: " + (
             f"{G['gleich']} von {G['verglichen']} Stichproben-Hashes gleich" if G and G.get("verglichen")
             else f"nicht verfügbar ({(G or {}).get('fehler', 'nicht gelaufen')})") + ".", "",
         "## Blockabstände gegen 60 s", "",
         tabelle(["", "gemessen", "erwartet (exponentiell, 60 s)"], [
             ["Mittel", f"{de(A['mittel'], 2)} s", "60 s"],
             ["Median", f"{de(float(A['median']))} s", f"{de(E['median'])} s"],
             ["p90", f"{de(A['p90'])} s", f"{de(E['p90'])} s"],
             ["p99", f"{de(A['p99'])} s", f"{de(E['p99'])} s"],
             ["über 5 min", f"{de(r['anteil_ueber_5min'] * 100, 2)} % ({de(r['anzahl_ueber_5min'])})",
              f"{de(E['anteil_ueber_5min'] * 100, 2)} %"],
             ["längste Lücke", f"{de(A['max'])} s (Höhe {de(r['laengste_luecke_hoehe'])})",
              f"≈ {de(E['laengste_luecke'], 0)} s"],
             ["Abstand 0 / negativ", f"{de(r['null'])} / {de(r['negativ'])}", ""]]), "",
         "## MTP-Verzug (Median der letzten 11 Blöcke)", "",
         tabelle(["", "gemessen", "erwartet (Simulation, 60 s)"], [
             ["Block-Zeitstempel minus MTP davor, Median", f"{de(float(M['verzug_block']['median']))} s",
              f"{de(float(M['erwartung']['verzug_block']['median']))} s"],
             ["dto. p90 / p99", f"{de(M['verzug_block']['p90'])} / {de(M['verzug_block']['p99'])} s",
              f"{de(M['erwartung']['verzug_block']['p90'])} / {de(M['erwartung']['verzug_block']['p99'])} s"],
             ["dto. kleinster Wert (Konsens verlangt > 0)", f"{de(M['verzug_block_min'])} s", ""],
             ["Abrufzeit minus MTP der Spitze", f"{de(M['abruf_minus_mtp'])} s",
              f"Median {de(float(M['erwartung']['abruf_minus_mtp']['median']))} s, p90 {de(M['erwartung']['abruf_minus_mtp']['p90'])} s"],
             ["Abrufzeit minus Zeitstempel der Spitze", f"{de(M['abruf_minus_spitze'])} s",
              f"Median {de(float(M['erwartung']['abruf_minus_spitze']['median']))} s, p90 {de(M['erwartung']['abruf_minus_spitze']['p90'])} s"]]),
         "", "Die Abrufzeit ist eine einzelne Messung je Lauf; die wöchentlichen Läufe sammeln weitere.", "",
         "## 10 Blöcke gegen 1 Block à 600 s", "",
         tabelle(["", "10 Blöcke gemessen", "10 × 60 s erwartet", "1 × 600 s erwartet"], [
             [q, f"{de(float(F['gemessen'][k]))} s", f"{de(F['erwartung_10x60'][k])} s", f"{de(F['erwartung_1x600'][k])} s"]
             for q, k in (("Median", "median"), ("p90", "p90"), ("p99", "p99"))]),
         "", f"{de(F['gemessen']['anzahl'])} überlappende Fenster.", "",
         "## Nachführung der Schwierigkeit", "",
         f"{N['methode']}. Sprünge: {N['spruenge']}, eingeholt {N['eingeholt']}, vom nächsten Sprung abgelöst "
         f"{N['abgeloest']}, am Stichtag offen {N['offen_am_stichtag']}. Eingeholt im Median nach "
         f"{de(N['median_bloecke'])} Blöcken bzw. {de(N['median_min'])} min (dieselben Sprünge), längstens "
         f"{de(N['max_bloecke'])} Blöcke.", ""]
    if N["ereignisse"]:
        z += [tabelle(["Höhe", "Zeit UTC", "Faktor", "eingeholt nach Blöcken", "min"], [
            [de(e["grenze_hoehe"]), e["zeit_utc"], de(e["faktor_hashrate"], 2),
             "abgelöst" if e["abgeloest"] else ("offen" if e["offen_am_stichtag"] else de(e["eingeholt_nach_bloecken"])),
             de(e["eingeholt_nach_min"])] for e in N["ereignisse"][:20]]), ""]
    z += ["## Je Tag (UTC)", "", tabelle(["Tag", "Blöcke", "Höhen", "mittl. Abstand", "Schwierigkeit Median"], [
        [t["tag_utc"], de(t["bloecke"]), f"{de(t['von'])}–{de(t['bis'])}", f"{de(t['mittlerer_abstand_s'])} s",
         de(t["schwierigkeit_median"], 2)] for t in r["je_tag"]]), "",
          f"Blöcke mit Mindestschwierigkeit (nBits = powLimit): {de(r['mindestschwierigkeit'])}.", "",
          "## Nicht gemessen", "",
          "- Blockinhalte und die ASERT-Regel selbst (nur Kopf, Verkettung, PoW gegen nBits).",
          "- Verwaiste Blöcke und Ankunftszeiten (kein Zuhörer, kein eigener Knoten).", ""]
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--stichtag", required=True)
    ap.add_argument("--gegenprobe")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()

    meta = json.load(open(args.meta))
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    st = int(datetime.strptime(args.stichtag, fmt).replace(tzinfo=timezone.utc).timestamp())
    abruf = int(datetime.strptime(meta["abruf_utc"], fmt).replace(tzinfo=timezone.utc).timestamp())
    with gzip.open(args.koepfe, "rt") as f:
        rows = sorted((int(z["hoehe"]), int(z["zeit"]), int(z["nbits"], 16)) for z in csv.DictReader(f))
    for i in range(1, len(rows)):
        assert rows[i][0] == rows[i - 1][0] + 1, "luecke in den hoehen"
    ab = next(i for i, r in enumerate(rows) if r[0] == ERSTER)
    bis = max(i for i, r in enumerate(rows) if r[1] <= st)
    sel = rows[ab:bis + 1]
    h = [r[0] for r in sel]
    t = [r[1] for r in sel]
    d = [schwierigkeit(r[2]) for r in sel]
    iv = [t[i] - t[i - 1] for i in range(1, len(t))]
    A = kennzahlen(iv)
    n = len(iv)
    E = {"mittel": ZIEL_S, "median": round(ZIEL_S * math.log(2), 1), "p90": round(ZIEL_S * math.log(10), 1),
         "p99": round(ZIEL_S * math.log(100), 1), "anteil_ueber_5min": round(math.exp(-LANG_S / ZIEL_S), 5),
         "laengste_luecke": round(ZIEL_S * (math.log(n) + 0.5772), 1)}

    # MTP-Verzug: Block i gegen den Median der 11 Bloecke davor (auch Chipnet-Bloecke vor dem Abzweig zaehlen mit)
    alle_t = [r[1] for r in rows[:bis + 1]]
    off = ab
    verzug = [alle_t[off + i] - statistics.median(alle_t[off + i - 11:off + i]) for i in range(len(t)) if off + i >= 11]
    mtp_spitze = statistics.median([r[1] for r in rows[-11:]])
    M = {"verzug_block": kennzahlen(verzug), "verzug_block_min": min(verzug),
         "abruf_minus_mtp": abruf - mtp_spitze, "abruf_minus_spitze": abruf - rows[-1][1],
         "spitze_beim_abruf": rows[-1][0], "erwartung": mtp_simulation()}

    sp = sorted(t[i + N_FENSTER] - t[i] for i in range(len(t) - N_FENSTER))
    F = {"gemessen": kennzahlen(sp),
         "erwartung_10x60": {k: round(erlang_q(q, N_FENSTER, ZIEL_S), 1) for k, q in (("median", .5), ("p90", .9), ("p99", .99))},
         "erwartung_1x600": {k: round(-ALT_S * math.log(1 - q), 1) for k, q in (("median", .5), ("p90", .9), ("p99", .99))}}

    i_max = max(range(n), key=lambda i: iv[i])
    r = {
        "titel": "BCH Tempnet 2027, unabhaengige Zaehlung",
        "stichtag_utc": datetime.fromtimestamp(st, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "bereich": {"von_hoehe": h[0], "bis_hoehe": h[-1], "bloecke": len(h),
                    "von_zeit_utc": utc(t[0]), "bis_zeit_utc": utc(t[-1])},
        "quelle": meta,
        "abstaende": A, "erwartung_abstaende": E,
        "anteil_ueber_5min": round(sum(1 for x in iv if x > LANG_S) / n, 5),
        "anzahl_ueber_5min": sum(1 for x in iv if x > LANG_S),
        "laengste_luecke_hoehe": h[i_max + 1],
        "null": sum(1 for x in iv if x == 0), "negativ": sum(1 for x in iv if x < 0),
        "mtp": M, "fenster_10": F,
        "nachfuehrung": nachfuehrung(h, t, d),
        "je_tag": je_tag(h, t, d),
        "mindestschwierigkeit": sum(1 for r_ in sel if r_[2] == POW_LIMIT_BITS),
        "gegenprobe_chaingraph": json.load(open(args.gegenprobe)) if args.gegenprobe else None,
    }
    with open(args.json, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(args.md, "w") as f:
        f.write(bericht(r))
    print(json.dumps({"bloecke": len(h), "von": h[0], "bis": h[-1], "mittel": A["mittel"], "median": A["median"]}))


if __name__ == "__main__":
    main()
