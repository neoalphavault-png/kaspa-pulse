#!/usr/bin/env python3
"""nu7_auswertung.py - zaehlt das Zcash-NU7-Testnet aus den Blockkoepfen.

Eingang: die CSV aus testnet_koepfe.py (hoehe,hash,zeit,nbits,version) und
deren Meta-JSON. Ausgang: eine JSON-Datei mit allen Zahlen und ein kurzer
Bericht in Markdown. Beide tragen Stichtag und Blockbereich.

Festlegungen, absichtlich hier im Code:
- Bereich: ab Hoehe 4.465.026 (erster NU7-Block) bis zum hoechsten Block,
  dessen Zeitstempel <= Stichtag ist.
- Abstand eines Blocks = sein Zeitstempel minus der seines Vorgaengers. Der
  erste gezaehlte Abstand ist der von 4.465.027; der Abstand vor 4.465.026
  entstand noch mit 75-s-Ziel. Zeitstempel setzt der Miner, Abstaende koennen
  also null oder negativ sein; sie gehen ungeschoent in die Statistik ein.
- Schwierigkeit wie in der RPC von zcashd/Zebra: Ziel(powLimit) / Ziel(nBits),
  powLimit des Testnets kompakt 0x2007ffff.
- Tage in UTC, ein Block zaehlt zu dem Tag seines Zeitstempels.
- Erwartung: exponentielle Abstaende mit 25 s Mittel.

Kein Kurs, keine Bewertung. Nur Zahlen.

  python3 scripts/zcash/nu7_auswertung.py --koepfe data/zcash/testnet-koepfe.csv.gz \
      --meta data/zcash/testnet-koepfe-meta.json --stichtag 2026-10-18T06:00:00Z \
      --json data/zcash/nu7-testnet-2026-10-18.json --md docs/zcash-nu7-testnet-2026-10-18.md
"""
import argparse
import csv
import gzip
import json
import math
import statistics
from collections import OrderedDict
from datetime import datetime, timezone

NU7 = 4_465_026
ZIEL_S = 25.0
ALT_S = 75.0
POW_LIMIT_BITS = 0x2007FFFF
FENSTER = 100         # Bloecke je Fenster, ~42 min; bei 40 erzeugt reines Rauschen schon Spruenge
SPRUNG = 2.0          # Faktor zwischen zwei Fenstern, ab dem es ein Sprung ist
NAEHE = 0.15          # "eingeholt": Schwierigkeit innerhalb +-15 % des Gleichgewichts
VORAUS_S = 600        # Zeitstempel mehr als 10 min vor dem Median der 11 Nachfolger


def ziel(bits):
    exp, mant = bits >> 24, bits & 0x007FFFFF
    return mant >> (8 * (3 - exp)) if exp <= 3 else mant << (8 * (exp - 3))


def schwierigkeit(bits):
    return ziel(POW_LIMIT_BITS) / ziel(bits)


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(sortiert, q):
    # lineare Interpolation (wie numpy default)
    if not sortiert:
        return None
    pos = (len(sortiert) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(sortiert) - 1)
    return sortiert[lo] + (sortiert[hi] - sortiert[lo]) * (pos - lo)


def abstands_statistik(hoehen, zeiten, mittel_erwartet):
    d = [zeiten[i] - zeiten[i - 1] for i in range(1, len(zeiten))]
    s = sorted(d)
    n = len(d)
    i_max = max(range(n), key=lambda i: d[i])
    return {
        "anzahl_abstaende": n,
        "mittel_s": round(sum(d) / n, 3),
        "median_s": quantil(s, 0.5),
        "p90_s": round(quantil(s, 0.9), 2),
        "p99_s": round(quantil(s, 0.99), 2),
        "min_s": s[0],
        "laengste_luecke_s": d[i_max],
        "laengste_luecke_bei": {"hoehe": hoehen[i_max + 1], "vorgaenger_zeit_utc": utc(zeiten[i_max]),
                                "zeit_utc": utc(zeiten[i_max + 1])},
        "anteil_ueber_75s": round(sum(1 for x in d if x > 75) / n, 5),
        "anteil_ueber_150s": round(sum(1 for x in d if x > 150) / n, 5),
        "anzahl_ueber_75s": sum(1 for x in d if x > 75),
        "anzahl_ueber_150s": sum(1 for x in d if x > 150),
        "anzahl_null": sum(1 for x in d if x == 0),
        "anzahl_negativ": sum(1 for x in d if x < 0),
        "erwartung_exponentiell": erwartung(mittel_erwartet, n),
    }, d


def erwartung(m, n):
    return {
        "mittel_s": m,
        "median_s": round(m * math.log(2), 2),
        "p90_s": round(m * math.log(10), 2),
        "p99_s": round(m * math.log(100), 2),
        "anteil_ueber_75s": round(math.exp(-75 / m), 5),
        "anteil_ueber_150s": round(math.exp(-150 / m), 5),
        # Erwartungswert des Maximums von n Exponentialabstaenden.
        "laengste_luecke_erwartet_s": round(m * (math.log(n) + 0.5772), 1) if n else None,
    }


def je_tag(hoehen, zeiten, diffs):
    tage = OrderedDict()
    for i, h in enumerate(hoehen):
        tag = datetime.fromtimestamp(zeiten[i], timezone.utc).strftime("%Y-%m-%d")
        tage.setdefault(tag, []).append(i)
    out = []
    for tag, idx in sorted(tage.items()):
        # mittlerer Abstand = Summe der Abstaende der Bloecke dieses Tages / Anzahl
        ab = [zeiten[i] - zeiten[i - 1] for i in idx if i > 0]
        ds = [diffs[i] for i in idx]
        out.append({
            "tag_utc": tag,
            "bloecke": len(idx),
            "erste_hoehe": hoehen[min(idx)],
            "letzte_hoehe": hoehen[max(idx)],
            "mittlerer_abstand_s": round(sum(ab) / len(ab), 2) if ab else None,
            "schwierigkeit_mittel": round(statistics.fmean(ds), 3),
            "schwierigkeit_min": round(min(ds), 3),
            "schwierigkeit_max": round(max(ds), 3),
            # Arbeit je Sekunde in Schwierigkeitseinheiten; relativ vergleichbar.
            "hashrate_relativ": round(sum(diffs[i] for i in idx if i > 0) / sum(ab), 4) if ab and sum(ab) > 0 else None,
        })
    return out


def nachfuehrung(hoehen, zeiten, diffs):
    """Spruenge der Hashrate und wie schnell die Schwierigkeit folgt.

    Hashrate eines Fensters = Summe Schwierigkeit / Summe Abstaende
    (Arbeit je Sekunde). Ein Sprung: das Fenster nach einer Grenze hat das
    SPRUNG-fache (oder 1/SPRUNG) des Fensters davor. Gleichgewicht nach dem
    Sprung: Schwierigkeit = Hashrate danach * 25 s. Gezaehlt wird, wie viele
    Bloecke und Minuten ab der Grenze vergehen, bis die Schwierigkeit
    innerhalb +-NAEHE des Gleichgewichts liegt.
    """
    W = FENSTER

    def rate(a, b):  # Bloecke a+1..b
        dt = zeiten[b] - zeiten[a]
        return sum(diffs[a + 1:b + 1]) / dt if dt > 0 else None

    ereignisse = []
    b = W
    while b + 2 * W < len(hoehen):
        vor, nach, danach = rate(b - W, b), rate(b, b + W), rate(b + W, b + 2 * W)
        # Bestaetigung: auch das zweite Fenster danach liegt mindestens halb so
        # weit weg. Sonst ist es Rauschen, kein Sprung.
        bestaetigt = danach and (math.log(danach / vor) / math.log(nach / vor) >= 0.5) if vor and nach and nach != vor else False
        if vor and nach and bestaetigt and (nach / vor >= SPRUNG or vor / nach >= SPRUNG):
            gg = nach * ZIEL_S
            k = next((j for j in range(b, min(b + 2000, len(hoehen)))
                      if abs(diffs[j] / gg - 1) <= NAEHE), None)
            ereignisse.append({
                "grenze_hoehe": hoehen[b],
                "zeit_utc": utc(zeiten[b]),
                "faktor_hashrate": round(nach / vor, 2),
                "schwierigkeit_an_grenze": round(diffs[b], 3),
                "gleichgewicht": round(gg, 3),
                "eingeholt_nach_bloecken": (k - b) if k is not None else None,
                "eingeholt_nach_min": round((zeiten[k] - zeiten[b]) / 60, 1) if k is not None else None,
            })
            b += 2 * W
        else:
            b += W // 2
    eingeholt = [e["eingeholt_nach_bloecken"] for e in ereignisse if e["eingeholt_nach_bloecken"] is not None]
    minuten = [e["eingeholt_nach_min"] for e in ereignisse if e["eingeholt_nach_min"] is not None]
    return {
        "methode": (f"Fenster {W} Bloecke, Sprung ab Faktor {SPRUNG} (vom folgenden Fenster bestaetigt), eingeholt bei +-{int(NAEHE*100)} % "
                    "des Gleichgewichts (Hashrate nach dem Sprung * 25 s)"),
        "spruenge": len(ereignisse),
        "nicht_eingeholt_in_2000_bloecken": sum(1 for e in ereignisse if e["eingeholt_nach_bloecken"] is None),
        "median_bloecke": statistics.median(eingeholt) if eingeholt else None,
        "median_min": statistics.median(minuten) if minuten else None,
        "max_bloecke": max(eingeholt) if eingeholt else None,
        "ereignisse": ereignisse,
    }


def zeitstempel(hoehen, zeiten, abruf_ts):
    rueck, voraus, mtp = [], [], []
    for i in range(1, len(zeiten)):
        if zeiten[i] < zeiten[i - 1]:
            rueck.append({"hoehe": hoehen[i], "schritt_s": zeiten[i] - zeiten[i - 1], "zeit_utc": utc(zeiten[i])})
        if i >= 11 and zeiten[i] <= statistics.median(zeiten[i - 11:i]):
            mtp.append(hoehen[i])
    for i in range(len(zeiten) - 11):
        m = statistics.median(zeiten[i + 1:i + 12])
        if zeiten[i] - m > VORAUS_S:
            voraus.append({"hoehe": hoehen[i], "vor_median_nachfolger_s": int(zeiten[i] - m), "zeit_utc": utc(zeiten[i])})
    zukunft = [{"hoehe": hoehen[i], "zeit_utc": utc(zeiten[i])} for i in range(len(zeiten)) if zeiten[i] > abruf_ts]
    rueck.sort(key=lambda r: r["schritt_s"])
    voraus.sort(key=lambda r: -r["vor_median_nachfolger_s"])
    return {
        "rueckwaerts_anzahl": len(rueck),
        "rueckwaerts_beispiele": rueck[:10],
        "rueckwaerts_groesster_s": rueck[0]["schritt_s"] if rueck else 0,
        "voraus_regel": f"Zeitstempel mehr als {VORAUS_S} s nach dem Median der 11 folgenden Bloecke",
        "voraus_anzahl": len(voraus),
        "voraus_beispiele": voraus[:10],
        "nach_abrufzeit_anzahl": len(zukunft),
        "verletzt_median_der_11_vorgaenger": len(mtp),
    }


def tabelle(kopf, zeilen):
    out = ["| " + " | ".join(kopf) + " |", "|" + "|".join(" --- " for _ in kopf) + "|"]
    out += ["| " + " | ".join("" if x is None else str(x) for x in z) + " |" for z in zeilen]
    return "\n".join(out)


def de(x, nk=1):
    if x is None:
        return "–"
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pz(x, nk=2):
    return de(x * 100, nk) + " %"


def bericht(r):
    a, e, v = r["abstaende"], r["abstaende"]["erwartung_exponentiell"], r["vorher_75s"]
    B = r["bereich"]
    zeilen = [
        f"# Zcash NU7 Testnet: unabhängige Zählung, Stand {r['stichtag_utc'][:10]}",
        "",
        f"**Stichtag:** {r['stichtag_utc']} · **Blockbereich:** {de(B['von_hoehe'])} bis {de(B['bis_hoehe'])} "
        f"({de(B['bloecke'])} Blöcke, {B['von_zeit_utc']} bis {B['bis_zeit_utc']} UTC) · "
        f"**Abruf:** {r['quelle']['abruf_utc']}",
        "",
        "Nur Zahlen. Kein Kurs, keine Bewertung.",
        "",
        "## Methode und Quelle",
        "",
        "- Blockköpfe direkt aus dem P2P-Netz des Zcash-Testnets (`getheaders`), Peers über die DNS-Seeds, "
        "kein Explorer, keine API, kein Konto. Skript: `scripts/zcash/testnet_koepfe.py`.",
        f"- Startpunkt: Checkpoint {de(r['quelle']['start_checkpoint'])} aus Zebras `test-checkpoints.txt`. "
        f"Geprüft: Verkettung über den Vorgänger-Hash, Hash ≤ Ziel aus nBits, "
        f"{de(r['quelle']['checkpoints_geprueft'])} spätere Checkpoints. Die Equihash-Lösung prüfen wir nicht.",
        f"- Gegenprobe mit weiteren Peers: " + (", ".join(
            f"{g['agent']}: {g['gleich']}/{g['verglichen']} Hashes gleich" for g in r["quelle"]["gegenproben"]) or "keine"),
        f"- Software der Peers: {', '.join(r['quelle']['peer_software'])}",
        "- Abstand = Zeitstempel minus Zeitstempel des Vorgängers, erster Abstand bei 4.465.027. "
        "Zeitstempel setzt der Miner; null und negative Abstände bleiben drin.",
        "- Schwierigkeit wie in der RPC: Ziel(powLimit 0x2007ffff) / Ziel(nBits). Tage in UTC.",
        "- Auswertung: `scripts/zcash/nu7_auswertung.py`, Rohdaten: `data/zcash/testnet-koepfe.csv.gz`.",
        "",
        "## A. Abstände zwischen Blöcken",
        "",
        tabelle(["", "gemessen", "Erwartung exponentiell, 25 s"], [
            ["Abstände", de(a["anzahl_abstaende"]), ""],
            ["Mittel", de(a["mittel_s"], 2) + " s", de(e["mittel_s"], 1) + " s"],
            ["Median", de(float(a["median_s"]), 1) + " s", de(e["median_s"], 1) + " s"],
            ["p90", de(a["p90_s"], 1) + " s", de(e["p90_s"], 1) + " s"],
            ["p99", de(a["p99_s"], 1) + " s", de(e["p99_s"], 1) + " s"],
            ["längste Lücke", f"{de(a['laengste_luecke_s'])} s (Höhe {de(a['laengste_luecke_bei']['hoehe'])})",
             f"≈ {de(e['laengste_luecke_erwartet_s'], 0)} s (Erwartungswert des Maximums)"],
            ["über 75 s", f"{pz(a['anteil_ueber_75s'])} ({de(a['anzahl_ueber_75s'])})", pz(e["anteil_ueber_75s"])],
            ["über 150 s", f"{pz(a['anteil_ueber_150s'], 3)} ({de(a['anzahl_ueber_150s'])})", pz(e["anteil_ueber_150s"], 3)],
            ["Abstand 0 s / negativ", f"{de(a['anzahl_null'])} / {de(a['anzahl_negativ'])}", ""],
        ]),
        "",
        f"Zum Vergleich vor der Aktivierung ({de(v['anzahl_abstaende'])} Abstände, Höhe "
        f"{de(r['vorher_bereich'][0])} bis {de(r['vorher_bereich'][1])}): Mittel {de(v['mittel_s'], 1)} s, "
        f"Median {de(float(v['median_s']), 1)} s, über 150 s {pz(v['anteil_ueber_150s'])} "
        f"(Erwartung bei 75 s: Median {de(v['erwartung_exponentiell']['median_s'], 1)} s, "
        f"über 150 s {pz(v['erwartung_exponentiell']['anteil_ueber_150s'])}).",
        "",
        "## B. Je Tag (UTC)",
        "",
        tabelle(["Tag", "Blöcke", "Höhen", "mittl. Abstand", "Schwierigkeit Mittel", "min", "max"], [
            [t["tag_utc"], de(t["bloecke"]), f"{de(t['erste_hoehe'])}–{de(t['letzte_hoehe'])}",
             de(t["mittlerer_abstand_s"], 1) + " s", de(t["schwierigkeit_mittel"], 1),
             de(t["schwierigkeit_min"], 1), de(t["schwierigkeit_max"], 1)] for t in r["je_tag"]]),
        "",
        "Erster und letzter Tag sind angeschnitten (Aktivierung 18:21:45 UTC, Stichtag).",
        "",
        "**Wie schnell folgt die Schwierigkeit?** " + r["nachfuehrung"]["methode"] + ". "
        f"Sprünge: {r['nachfuehrung']['spruenge']}; eingeholt im Median nach "
        f"{de(r['nachfuehrung']['median_bloecke'])} Blöcken bzw. {de(r['nachfuehrung']['median_min'])} min, "
        f"längstens {de(r['nachfuehrung']['max_bloecke'])} Blöcke; nicht eingeholt in 2.000 Blöcken: "
        f"{r['nachfuehrung']['nicht_eingeholt_in_2000_bloecken']}.",
        "",
    ]
    if r["nachfuehrung"]["ereignisse"]:
        zeilen += [tabelle(["Höhe", "Zeit UTC", "Faktor Hashrate", "Schwierigkeit davor", "Gleichgewicht",
                            "eingeholt nach Blöcken", "min"], [
            [de(x["grenze_hoehe"]), x["zeit_utc"], de(x["faktor_hashrate"], 2), de(x["schwierigkeit_an_grenze"], 1),
             de(x["gleichgewicht"], 1), de(x["eingeholt_nach_bloecken"]), de(x["eingeholt_nach_min"])]
            for x in r["nachfuehrung"]["ereignisse"][:15]]), ""]
    z = r["zeitstempel"]
    zeilen += [
        "## C. Zeitstempel",
        "",
        f"- Rückwärts (Zeitstempel kleiner als der des Vorgängers): **{de(z['rueckwaerts_anzahl'])}**, "
        f"größter Schritt {de(z['rueckwaerts_groesster_s'])} s.",
        f"- Auffällig weit voraus ({z['voraus_regel']}): **{de(z['voraus_anzahl'])}**.",
        f"- Zeitstempel nach unserer Abrufzeit: {de(z['nach_abrufzeit_anzahl'])}. "
        f"Verstöße gegen die Median-Regel der 11 Vorgänger: {de(z['verletzt_median_der_11_vorgaenger'])} (Konsensregel, Gegenprobe).",
        "",
    ]
    if z["rueckwaerts_beispiele"]:
        zeilen += ["Beispiele rückwärts:", "", tabelle(["Höhe", "Schritt", "Zeit UTC"], [
            [de(x["hoehe"]), f"{x['schritt_s']} s", x["zeit_utc"]] for x in z["rueckwaerts_beispiele"]]), ""]
    if z["voraus_beispiele"]:
        zeilen += ["Beispiele voraus:", "", tabelle(["Höhe", "vor Median der Nachfolger", "Zeit UTC"], [
            [de(x["hoehe"]), f"{x['vor_median_nachfolger_s']} s", x["zeit_utc"]] for x in z["voraus_beispiele"]]), ""]
    zeilen += [
        "## D. Was wir nicht messen konnten",
        "",
        "- **Verwaiste Blöcke und Reorg-Tiefe:** nicht gemessen. Dafür braucht es einen eigenen Knoten, der "
        "ab der Aktivierung mitläuft und jeden empfangenen Block protokolliert. Die Köpfe aus `getheaders` "
        "zeigen nur die Kette, die die Peers zum Abrufzeitpunkt für die beste halten.",
        "- **Ankunftsabstand desselben Blocks auf zwei Knoten (Zebra, Zakura):** nicht gemessen, kein eigener Knoten.",
        "- **Equihash-Lösungen und Blockinhalt:** nicht geprüft, nur Kopf, Verkettung, Arbeitsnachweis gegen nBits und Checkpoints.",
        "- **Echte Hashrate:** nur relativ über Schwierigkeit und Abstände; Zeitstempel kommen vom Miner.",
        "",
    ]
    return "\n".join(zeilen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--stichtag", required=True, help="ISO UTC, z. B. 2026-10-18T06:00:00Z")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()

    meta = json.load(open(args.meta))
    stichtag = datetime.strptime(args.stichtag, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    st = int(stichtag.timestamp())
    abruf = int(datetime.strptime(meta["abruf_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    if abruf < st:
        print(f"hinweis: abruf {meta['abruf_utc']} liegt vor dem stichtag, bereich endet an der spitze")

    rows = []
    with gzip.open(args.koepfe, "rt") as f:
        for z in csv.DictReader(f):
            rows.append((int(z["hoehe"]), int(z["zeit"]), int(z["nbits"], 16)))
    rows.sort()
    for i in range(1, len(rows)):
        assert rows[i][0] == rows[i - 1][0] + 1, "luecke in den hoehen"
    ab = next(i for i, r in enumerate(rows) if r[0] == NU7)
    bis = max(i for i, r in enumerate(rows) if r[1] <= st)
    # nachher: Index ab-1 als Vorgaenger fuer den Abstand von NU7 mitnehmen, aber
    # der erste gezaehlte Abstand ist 4.465.027 -> Liste ab Index ab.
    sel = rows[ab:bis + 1]
    hoehen = [r[0] for r in sel]
    zeiten = [r[1] for r in sel]
    diffs = [schwierigkeit(r[2]) for r in sel]

    vor = rows[:ab]
    a, _ = abstands_statistik(hoehen, zeiten, ZIEL_S)
    v, _ = abstands_statistik([r[0] for r in vor], [r[1] for r in vor], ALT_S)
    for k in ("laengste_luecke_bei",):
        v.pop(k)

    r = {
        "titel": "Zcash NU7 Testnet, unabhaengige Zaehlung",
        "stichtag_utc": stichtag.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "bereich": {
            "von_hoehe": hoehen[0], "bis_hoehe": hoehen[-1], "bloecke": len(hoehen),
            "von_zeit_utc": utc(zeiten[0]), "bis_zeit_utc": utc(zeiten[-1]),
            "regel": "ab 4.465.026 bis zum hoechsten Block mit Zeitstempel <= Stichtag",
        },
        "quelle": meta,
        "abstaende": a,
        "vorher_75s": v,
        "vorher_bereich": [vor[0][0], vor[-1][0]],
        "je_tag": je_tag(hoehen, zeiten, diffs),
        "nachfuehrung": nachfuehrung(hoehen, zeiten, diffs),
        "zeitstempel": zeitstempel(hoehen, zeiten, abruf),
        "nicht_gemessen": [
            "verwaiste Bloecke und Reorg-Tiefe (kein eigener Knoten)",
            "Ankunftsabstand desselben Blocks auf zwei Knoten (kein eigener Knoten)",
            "Equihash-Loesungen und Blockinhalt",
        ],
    }
    with open(args.json, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(args.md, "w") as f:
        f.write(bericht(r))
    print(json.dumps({"bloecke": len(hoehen), "von": hoehen[0], "bis": hoehen[-1],
                      "mittel_s": a["mittel_s"], "median_s": a["median_s"]}))


if __name__ == "__main__":
    main()
