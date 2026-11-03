#!/usr/bin/env python3
"""forum_woche3.py - Zahlen fuer den Forumsbeitrag BCH Tempnet Woche 3 (Ben, 03.11.2026).

Fenster aus dem Wochenlauf (Stichtag zu Stichtag), getrennt vor und nach dem
Schnitt 29.10.2026 21:00 UTC (ab dieser Stunde aendern sich unsere Zahlen,
kurz vor dem Neustart des Knotens um 22:35 UTC). Nie ein Mittel ueber beide
Teile.

Je Teil:
- aus den eigenen Koepfen (tempnet-koepfe.csv.gz): Abstaende (Mittel,
  Median, p90, p99, Anteil ueber 5 min, laengste Luecke), Bloecke mit
  Mindestschwierigkeit; dazu die gerechneten Werte fuer 60 s
- aus dem Zuhoerer (lauscher/bloecke.csv, zusammenfassung.json, Laeufe):
  Abdeckung und Luecken, timestamp_deviation alle und ohne die Bloecke mit
  Kopfzeit genau 120 s nach dem Vorgaenger (Anzahl), propagation_spread,
  erste Sicht nach Nachrichtentyp, stale nach 6 Bestaetigungen wie in
  Woche 2 (angekuendigt, 6 Bloecke spaeter nicht in der Kette; Anteil an
  Kettenbloecken plus stale)
- Woche 2 zum Vergleich: timestamp_deviation mit und ohne die 120-s-Bloecke

Keine Adressen, keine Software-Kennungen, keine Coinbase-Daten.

  python3 scripts/bch/forum_woche3.py --koepfe data/bch/tempnet-koepfe.csv.gz --lauscher data/bch/lauscher \\
      --von 2026-10-28T10:00:00Z --bis 2026-11-04T10:00:00Z --schnitt 2026-10-29T21:00:00Z \\
      --json data/bch/tempnet-woche3-forum-2026-11-04.json
"""
import argparse
import csv
import glob
import gzip
import json
import math
import os
from datetime import datetime, timezone

POW_LIMIT_BITS = 0x1D00FFFF
ZIEL_S = 60
GENAU_S = 120
WOCHE2 = ("2026-10-25T09:15:47Z", "2026-10-28T07:36:11Z")


def ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def quantil(s, q):
    s = sorted(s)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def r(x, n=2):
    return None if x is None else round(x, n)


def drei(w, n=2):
    return {"median": r(quantil(w, 0.5), n), "p90": r(quantil(w, 0.9), n), "p99": r(quantil(w, 0.99), n), "n": len(w)}


def koepfe_teil(kette, von, bis):
    """Abstaende mit Blockzeit in [von, bis), ueber die Hoehe abgegrenzt wie im Wochenlauf."""
    hs = [h for h in sorted(kette) if von <= kette[h][0] < bis and h - 1 in kette]
    ab = [(h, kette[h][0] - kette[h - 1][0]) for h in hs]
    w = [x for _, x in ab]
    if not w:
        return None
    h_max, l_max = max(ab, key=lambda z: z[1])
    n = len(w)
    return {
        "bloecke": [hs[0], hs[-1]], "abstaende": n, "mittel_s": r(sum(w) / n), "median_s": r(quantil(w, 0.5), 1),
        "p90_s": r(quantil(w, 0.9), 1), "p99_s": r(quantil(w, 0.99), 1),
        "ueber_5min": sum(1 for x in w if x > 300), "ueber_5min_prozent": r(100 * sum(1 for x in w if x > 300) / n),
        "laengste_luecke_s": l_max, "laengste_luecke_vor_block": h_max, "laengste_luecke_utc": utc(kette[h_max][0]),
        "mindestschwierigkeit": sum(1 for h in hs if kette[h][1] == POW_LIMIT_BITS),
        "genau_120s": sum(1 for x in w if x == GENAU_S),
        "computed_60s": {"median_s": r(ZIEL_S * math.log(2), 1), "p90_s": r(ZIEL_S * math.log(10), 1),
                         "p99_s": r(ZIEL_S * math.log(100), 1), "ueber_5min_prozent": r(100 * math.exp(-5)),
                         "laengste_luecke_s": round(ZIEL_S * (math.log(n) + 0.5772))},
    }


def spaet(b):
    """Bloecke mit propagation_spread ueber 10 min: Zahl und Zeitraum (ein spaeter Peer)."""
    s = [z for z in b if z["propagation_spread_ms"] and int(z["propagation_spread_ms"]) > 600_000]
    if not s:
        return {"anzahl": 0}
    return {"anzahl": len(s), "von_utc": s[0]["first_seen_utc"][:16].replace("T", " "),
            "bis_utc": s[-1]["first_seen_utc"][:16].replace("T", " ")}


def je_stunde_median(b):
    je = {}
    for z in b:
        je[z["first_seen_utc"][:13]] = je.get(z["first_seen_utc"][:13], 0) + 1
    return round(quantil(list(je.values()), 0.5))


def wellen(s, b, ab=20):
    """Zusammenhaengende Stunden mit mindestens ab stale-Bloecken."""
    je = {}
    for z in s:
        je[z["first_seen_utc"][:13]] = je.get(z["first_seen_utc"][:13], 0) + 1
    out, cur = [], None
    for h in sorted(je):
        if je[h] < ab:
            continue
        t0 = ts(h + ":00:00Z")
        if cur and t0 - cur["_bis"] <= 3600:
            cur["anzahl"] += je[h]
            cur["_bis"] = t0
        else:
            cur = {"anzahl": je[h], "_von": t0, "_bis": t0}
            out.append(cur)
    kette = {}
    for z in b:
        kette[z["first_seen_utc"][:13]] = kette.get(z["first_seen_utc"][:13], 0) + 1
    res = []
    for c in out:
        stunden = [h for h in kette if c["_von"] <= ts(h + ":00:00Z") <= c["_bis"]]
        res.append({"anzahl": c["anzahl"], "von_utc": utc(c["_von"]), "bis_utc": utc(c["_bis"] + 3600),
                    "kette_je_h": round(sum(kette[h] for h in stunden) / max(1, len(stunden)))})
    return res


def lauscher_teil(bloecke, stale, von, bis):
    b = [z for z in bloecke if von <= ts(z["first_seen_utc"]) < bis]
    s = [z for z in stale if von <= ts(z["first_seen_utc"]) < bis]
    if not b:
        return None
    dev = [float(z["timestamp_deviation_s"]) for z in b if z["timestamp_deviation_s"]]
    ohne = [float(z["timestamp_deviation_s"]) for z in b if z["timestamp_deviation_s"] and z["interval_s"] != str(GENAU_S)]
    spr = [int(z["propagation_spread_ms"]) / 1000 for z in b if z["propagation_spread_ms"]]
    peers = [int(z["peers_announced"]) for z in b if z["peers_announced"]]
    typ = {}
    for z in b:
        typ[z["first_seen_type"]] = typ.get(z["first_seen_type"], 0) + 1
    return {
        "kettenbloecke": len(b), "hoehen": [int(b[0]["height"]), int(b[-1]["height"])],
        "erste_sicht_typ": typ, "peers_je_block_median": quantil(peers, 0.5),
        "timestamp_deviation_s": drei(dev), "timestamp_deviation_ohne_120s": {**drei(ohne), "ausgelassen": len(dev) - len(ohne)},
        "propagation_spread_s": drei(spr, 1),
        "spread_ueber_10min": spaet(b),
        "stale_wellen": wellen(s, b),
        "kette_je_h_median": je_stunde_median(b),
        "stale": {"anzahl": len(s), "angekuendigt": len(b) + len(s), "anteil_prozent": r(100 * len(s) / (len(b) + len(s))),
                  "ohne_kopf": sum(1 for z in s if not z.get("header_time_utc"))},
    }


def abdeckung(ordner, von, bis):
    laeufe = []
    for d in sorted(glob.glob(os.path.join(ordner, "2*"))):
        m = json.load(open(os.path.join(d, "meta.json")))
        a, e = max(ts(m["start_utc"]), von), min(ts(m["ende_utc"]), bis)
        if e > a:
            laeufe.append((a, e, len(m["peers"])))
    laeufe.sort()
    luecken, bis_jetzt = [], von
    for a, e, _ in laeufe:
        if a > bis_jetzt + 1:
            luecken.append({"von_utc": utc(bis_jetzt), "bis_utc": utc(a), "dauer_s": round(a - bis_jetzt)})
        bis_jetzt = max(bis_jetzt, e)
    if bis_jetzt < bis - 1:
        luecken.append({"von_utc": utc(bis_jetzt), "bis_utc": utc(bis), "dauer_s": round(bis - bis_jetzt), "fensterende": True})
    return {"laeufe": len(laeufe), "abgedeckt_h": r(sum(e - a for a, e, _ in laeufe) / 3600, 1),
            "peers_je_lauf": [min((p for *_, p in laeufe), default=0), max((p for *_, p in laeufe), default=0)],
            "luecken": luecken}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--lauscher", required=True)
    ap.add_argument("--von", required=True)
    ap.add_argument("--bis", required=True)
    ap.add_argument("--schnitt", default="2026-10-29T21:00:00Z")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", help="Forumsentwurf (englisch) schreiben")
    a = ap.parse_args()
    von, bis, schnitt = ts(a.von), ts(a.bis), ts(a.schnitt)

    with gzip.open(a.koepfe, "rt") as f:
        kette = {int(z["hoehe"]): (int(z["zeit"]), int(z["nbits"], 16)) for z in csv.DictReader(f)}
    with open(os.path.join(a.lauscher, "bloecke.csv")) as f:
        bloecke = list(csv.DictReader(f))
    stale = json.load(open(os.path.join(a.lauscher, "zusammenfassung.json")))["stale"]["bloecke"]

    r_ = {"fenster_utc": [utc(von), utc(bis)], "schnitt_utc": utc(schnitt),
          "koepfe_spitze": max(kette), "lauscher_bis_utc": max(z["first_seen_utc"] for z in bloecke),
          "teile": {}}
    for teil, (x, y) in (("vor", (von, schnitt)), ("nach", (schnitt, bis))):
        r_["teile"][teil] = {"fenster_utc": [utc(x), utc(y)], "koepfe": koepfe_teil(kette, x, y),
                             "lauscher": lauscher_teil(bloecke, stale, x, y), "abdeckung": abdeckung(a.lauscher, x, y)}
    w2 = lauscher_teil(bloecke, stale, ts(WOCHE2[0]), ts(WOCHE2[1]) + 1)
    r_["woche2_vergleich"] = {"fenster_utc": list(WOCHE2), "timestamp_deviation_s": w2["timestamp_deviation_s"],
                              "timestamp_deviation_ohne_120s": w2["timestamp_deviation_ohne_120s"]}
    with open(a.json, "w") as f:
        json.dump(r_, f, indent=1, ensure_ascii=False)
    if a.md:
        text = forum(r_)
        fehler = regeln(text.split(TRENNER, 1)[1])
        with open(a.md, "w") as f:
            f.write(text)
        print("textregeln: " + ("ok" if not fehler else "; ".join(fehler)))
    print(json.dumps(r_, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- forum
TRENNER = "Everything below this line is the post.\n"
MONAT = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def tag(text):
    """'2026-10-29 21:00:00' -> '29 Oct 21:00 utc'"""
    d = datetime.fromisoformat(text.replace("T", " ")[:19])
    return f"{d.day} {MONAT[d.month - 1].capitalize()} {d:%H:%M} utc"


def z(x, n=None):
    if x is None:
        return "n/a"
    if n is not None:
        x = round(x, n)
    if isinstance(x, float) and n is not None:
        return f"{x:,.{n}f}"
    return f"{x:,}"


def regeln(text):
    f = []
    for zeichen, art in {"\u2013": "gedankenstrich", "\u2014": "gedankenstrich", "\u2192": "pfeil",
                         "\u2190": "pfeil", "\u21d2": "pfeil", "#": "hashtag"}.items():
        if zeichen in text:
            f.append(art)
    import re
    if re.search(r"\s-\s|->|<-|=>", text):
        f.append("gedankenstrich oder pfeil aus ascii")
    if re.search(r"(?<!\d):|:(?!\d)", text.replace("|---|", "").replace("---:", "")):
        f.append("doppelpunkt ausserhalb einer uhrzeit")
    for satz in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = satz.strip().lstrip("*|").strip()
        if s and s[0].isdigit():
            f.append(f"satz beginnt mit ziffer ({s[:30]!r})")
    if "http" in text or "github.com" in text:
        f.append("link")
    return f


def forum(r_):
    v, n = r_["teile"]["vor"], r_["teile"]["nach"]
    kv, kn, lv, ln = v["koepfe"], n["koepfe"], v["lauscher"], n["lauscher"]
    w2 = r_["woche2_vergleich"]
    fv, fn = v["fenster_utc"], n["fenster_utc"]
    zeilen = [
        "# Forum draft, BCH tempnet week 3 (Ben posts)", "",
        f"Window {tag(r_['fenster_utc'][0])} to {tag(r_['fenster_utc'][1])}, split at {tag(r_['schnitt_utc'])}. "
        f"Header chain up to block {r_['koepfe_spitze']:,}, listener data up to {tag(r_['lauscher_bis_utc'])}. "
        "Reply to bitcoincashautist and rufitnes. " + TRENNER,
        "@bitcoincashautist @rufitnes week three of our tempnet counts.", "",
        f"**Two windows.** Our listener numbers change from {tag(r_['schnitt_utc'])} on, shortly before the node "
        "restart discussed in this thread. So every table below has one column before and one after that hour, "
        "and no value is averaged across both.", "",
        f"**Block intervals from our own headers**", "",
        f"| | before, {tag(fv[0])} to {tag(fv[1])} | after, {tag(fn[0])} to {tag(fn[1])} | computed for 60 s |",
        "|---|---:|---:|---:|",
    ]
    def k(teil, schl, fmt=lambda x: z(x)):
        return fmt(teil[schl]) if teil else "n/a"
    zeilen += [
        f"| blocks | {k(kv, 'bloecke', lambda b: f'{b[0]:,} to {b[1]:,}')} | {k(kn, 'bloecke', lambda b: f'{b[0]:,} to {b[1]:,}')} | |",
        f"| intervals | {k(kv, 'abstaende')} | {k(kn, 'abstaende')} | |",
        f"| mean | {k(kv, 'mittel_s')} s | {k(kn, 'mittel_s')} s | 60 s |",
        f"| median | {k(kv, 'median_s')} s | {k(kn, 'median_s')} s | 41.6 s |",
        f"| p90 | {k(kv, 'p90_s')} s | {k(kn, 'p90_s')} s | 138.2 s |",
        f"| p99 | {k(kv, 'p99_s')} s | {k(kn, 'p99_s')} s | 276.3 s |",
        f"| share above 5 min | {k(kv, 'ueber_5min_prozent')} % ({k(kv, 'ueber_5min')}) | "
        f"{k(kn, 'ueber_5min_prozent')} % ({k(kn, 'ueber_5min')}) | 0.67 % |",
        f"| longest gap | {k(kv, 'laengste_luecke_s')} s | {k(kn, 'laengste_luecke_s')} s | "
        f"about {k(kn or kv, 'computed_60s', lambda c: z(c['laengste_luecke_s']))} s |",
        f"| blocks with minimum difficulty | {k(kv, 'mindestschwierigkeit')} | {k(kn, 'mindestschwierigkeit')} | |",
        f"| intervals of exactly 120 s | {k(kv, 'genau_120s')} | {k(kn, 'genau_120s')} | |", "",
        "**Listener on our own network path**", "",
        "| | before | after |", "|---|---:|---:|",
        f"| chain blocks seen | {z(lv['kettenbloecke'])} | {z(ln['kettenbloecke'])} |",
        f"| peers announcing a block, median | {z(round(lv['peers_je_block_median']))} | {z(round(ln['peers_je_block_median']))} |",
        f"| timestamp_deviation, median / p90 / p99, all blocks | {z(lv['timestamp_deviation_s']['median'], 2)} / "
        f"{z(lv['timestamp_deviation_s']['p90'], 2)} / {z(lv['timestamp_deviation_s']['p99'], 1)} s | "
        f"{z(ln['timestamp_deviation_s']['median'], 2)} / {z(ln['timestamp_deviation_s']['p90'], 2)} / "
        f"{z(ln['timestamp_deviation_s']['p99'], 1)} s |",
        f"| same without blocks exactly 120 s after their parent | {z(lv['timestamp_deviation_ohne_120s']['median'], 2)} / "
        f"{z(lv['timestamp_deviation_ohne_120s']['p90'], 2)} / {z(lv['timestamp_deviation_ohne_120s']['p99'], 1)} s "
        f"(without {lv['timestamp_deviation_ohne_120s']['ausgelassen']}) | "
        f"{z(ln['timestamp_deviation_ohne_120s']['median'], 2)} / {z(ln['timestamp_deviation_ohne_120s']['p90'], 2)} / "
        f"{z(ln['timestamp_deviation_ohne_120s']['p99'], 1)} s (without {ln['timestamp_deviation_ohne_120s']['ausgelassen']}) |",
        f"| propagation_spread, median / p90 | {z(lv['propagation_spread_s']['median'], 1)} / "
        f"{z(lv['propagation_spread_s']['p90'], 1)} s | {z(ln['propagation_spread_s']['median'], 1)} / "
        f"{z(ln['propagation_spread_s']['p90'], 1)} s |",
        f"| stale blocks after 6 confirmations | {lv['stale']['anzahl']} of {lv['stale']['angekuendigt']:,} announced "
        f"({z(lv['stale']['anteil_prozent'], 2)} %) | {ln['stale']['anzahl']} of {ln['stale']['angekuendigt']:,} announced "
        f"({z(ln['stale']['anteil_prozent'], 2)} %) |", "",
    ]
    w2a, w2o = w2["timestamp_deviation_s"], w2["timestamp_deviation_ohne_120s"]
    zeilen += [
        f"**A correction to how we showed week two.** We gave a timestamp_deviation p99 of {z(w2a['p99'], 1)} s. "
        f"Without the {w2o['ausgelassen']} blocks whose header timestamp is exactly 120 s after their parent the p99 "
        f"is {z(w2o['p99'], 1)} s, so that tail came almost entirely from those blocks. Thanks to rufitnes, who showed "
        "on 30 Oct that 101 of these blocks come from one miner. We only count timestamps and do not look at who mined "
        "a block.", "",
        "**Stale blocks** use the same definition as in week two. A block counts as stale when it was announced to us "
        "and is not in the chain 6 blocks later, and the share is stale blocks over chain blocks plus stale blocks.", "",
    ]
    for teil, l_ in (("before", lv), ("after", ln)):
        s = l_["spread_ueber_10min"]
        if s["anzahl"]:
            zeilen.append(f"In the {teil} window {s['anzahl']} blocks reached one of our peers more than 10 min after "
                          f"the first announcement, between {tag(s['von_utc'])} and {tag(s['bis_utc'])}. That is why we "
                          "leave out the p99 of propagation_spread this week.")
            zeilen.append("")
    for teil, l_ in (("before", lv), ("after", ln)):
        w = l_["stale_wellen"]
        if w and sum(x["anzahl"] for x in w) >= l_["stale"]["anzahl"] / 2:
            teile = [f"{x['anzahl']} from {tag(x['von_utc'])} to {tag(x['bis_utc'])} with {x['kette_je_h']} chain blocks "
                     f"per hour" for x in w]
            liste = teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " and " + teile[-1]
            zeilen.append(f"Of the {l_['stale']['anzahl']} stale blocks in the {teil} window, "
                          f"{sum(x['anzahl'] for x in w)} fall into {['no', 'one', 'two', 'three', 'four', 'five'][len(w)] if len(w) < 6 else len(w)} short "
                          f"{'period' if len(w) == 1 else 'periods'}, {liste}. Across the whole {teil} window the "
                          f"median is {l_['kette_je_h_median']} chain blocks per hour.".replace("{teil}", teil))
            zeilen.append("")
    luecken = [l_ for t_ in (v, n) for l_ in t_["abdeckung"]["luecken"] if not l_.get("fensterende")]
    abg = v["abdeckung"]["abgedeckt_h"] + n["abdeckung"]["abgedeckt_h"]
    zeilen.append(f"**Coverage.** The listener covered {z(round(abg, 1))} h of the window in "
                  f"{v['abdeckung']['laeufe'] + n['abdeckung']['laeufe']} segments, with "
                  f"{min(v['abdeckung']['peers_je_lauf'][0], n['abdeckung']['peers_je_lauf'][0])} to "
                  f"{max(v['abdeckung']['peers_je_lauf'][1], n['abdeckung']['peers_je_lauf'][1])} peers that confirm the "
                  "fork at block 327,989." + (" Gaps between segments were " + ", ".join(
                      f"{round(l_['dauer_s'] / 60)} min from {tag(l_['von_utc'])}" for l_ in luecken) + "." if luecken else
                      " There was no gap between segments."))
    zeilen += ["", "All numbers in the tables are counted by us from our own header chain and our own listener, "
               "except the column computed for an ideal 60 s chain. The listener keeps running until the tempnet ends "
               "on 15 Nov.", ""]
    return "\n".join(zeilen)


if __name__ == "__main__":
    main()
