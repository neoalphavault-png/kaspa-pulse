#!/usr/bin/env python3
"""forum_nachtrag.py - Entwurf des Forum-Nachtrags (Zcash Community Forum,
Thread "NU7 Timeline") aus der fertigen Auswertung.

Nur ein Entwurf: Ben prueft und postet von Hand (Ben, 17.10.2026). Alle
Zahlen kommen aus der JSON von nu7_auswertung.py, nichts wird von Hand
eingesetzt. Englisch, weil das Forum englisch ist.

Vorgaben (Ben, 17.10.2026):
- erster Satz: Bezug auf die Mainnet-Entscheidung am 20.10.
- Beitrag 24 versprach Daten "from a listener on Saturday": tatsaechliches
  Fenster in UTC, oder offen "not measured" mit Grund.
- Abschnitt an @shabam (Beitrag 13): Bestaetigungen bei 25 s, nur Messung
  und Rechnung, keine Empfehlung.
- Software-Versionen der Peers aus dem Zuhoerer, nie Adressen.
- kein Kurs, keine Bewertung.

  python3 scripts/zcash/forum_nachtrag.py --json data/zcash/nu7-testnet-2026-10-18.json \
      --aus docs/zcash-nu7-forum-nachtrag-2026-10-18.md
"""
import argparse
import json
from collections import Counter
from datetime import datetime


def n(x, nk=0):
    if x is None:
        return "–"
    if isinstance(x, int) or nk == 0:
        return f"{round(x):,}"
    return f"{x:,.{nk}f}"


def pct(x, nk=2):
    return "–" if x is None else f"{x * 100:.{nk}f} %"


def fenster(L):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    a, b = (datetime.strptime(x, fmt) for x in L["fenster_utc"])
    bis = f"{b:%H:%M}" if a.date() == b.date() else f"{b:%d %b %Y %H:%M}"
    return f"{a:%d %b %Y}, {a:%H:%M} to {bis} UTC ({(b - a).total_seconds() / 60:.0f} min)"


def entwurf(r):
    B, A, E = r["bereich"], r["abstaende"], r["abstaende"]["erwartung_exponentiell"]
    nf, z, bs = r["nachfuehrung"], r["zeitstempel"], r["bestaetigungen"]
    L = r.get("lauscher")
    t = []
    t += [
        f"Ahead of the mainnet go/no-go on 20 October, here are our final independent counts for NU7 on "
        f"the public testnet: blocks {n(B['von_hoehe'])} to {n(B['bis_hoehe'])} "
        f"({n(B['bloecke'])} blocks), cut-off {r['stichtag_utc']}. Numbers only, no assessment.",
        "",
        "**Block intervals** (timestamp of a block minus that of its parent, first interval at "
        f"{n(B['von_hoehe'] + 1)}; expectation: exponential intervals with a 25 s mean)",
        "",
        "| | measured | expected |",
        "| --- | --- | --- |",
        f"| mean | {n(A['mittel_s'], 2)} s | 25 s |",
        f"| median | {n(float(A['median_s']), 1)} s | {n(E['median_s'], 1)} s |",
        f"| p90 / p99 | {n(A['p90_s'], 1)} s / {n(A['p99_s'], 1)} s | {n(E['p90_s'], 1)} s / {n(E['p99_s'], 1)} s |",
        f"| share > 75 s | {pct(A['anteil_ueber_75s'])} | {pct(E['anteil_ueber_75s'])} |",
        f"| share > 150 s | {pct(A['anteil_ueber_150s'], 3)} | {pct(E['anteil_ueber_150s'], 3)} |",
        f"| longest gap | {n(A['laengste_luecke_s'])} s at {n(A['laengste_luecke_bei']['hoehe'])} | "
        f"≈ {n(E['laengste_luecke_erwartet_s'])} s (expected maximum) |",
        "",
        f"Difficulty: {nf['spruenge']} hashrate jumps of 2x or more; difficulty caught up (within ±15 %) after a "
        f"median of {n(nf['median_bloecke'])} blocks / {n(nf['median_min'], 1)} min, longest "
        f"{n(nf['max_bloecke'])} blocks. Timestamps: {n(z['rueckwaerts_anzahl'])} going backwards, "
        f"{n(z['voraus_anzahl'])} far ahead ({'>'}10 min ahead of the median of the next 11). "
        f"Minimum-difficulty blocks since activation: {n(r['mindestschwierigkeit']['anzahl'])}.",
        "",
        "**Listener (as promised in post 24)**",
        "",
    ]
    if L:
        sw = Counter(p["software"] for p in L["peers"])
        versionen = ", ".join(f"`{v}` ({c})" for v, c in sorted(sw.items()))
        zk = L["zakura_minus_zebra_ms"]
        t += [
            f"One listener at one location, not our own node. Actual window: {fenster(L)}. It kept "
            "connections to Zebra and Zakura nodes and logged every block announcement with its arrival time; "
            "arrival times include the path from the node to the listener.",
            "",
            f"- chain blocks with timestamps in the window: {n(L['kettenbloecke_im_fenster'])}, seen announced: "
            f"{n(L['davon_angekuendigt_gesehen'])}",
            f"- announced blocks that did not end up in the chain: {n(L['abgehaengt_anzahl'])}; deepest branch: "
            f"{n(L['groesste_tiefe'])}",
            (f"- first Zakura announcement minus first Zebra announcement of the same block "
             f"({n(zk['bloecke'])} blocks): median {n(zk['median'])} ms, p10 {n(zk['p10'])} ms, p90 {n(zk['p90'])} ms"
             if zk["bloecke"] else "- no block was announced by both Zebra and Zakura peers"),
            f"- peer software versions (connections): {versionen}",
            "",
        ]
    else:
        t += [f"Not measured: {r.get('lauscher_pruefung_en') or 'no listener run'}.", ""]
    BS, G, T = bs, bs["gemessen_spanne_30_bloecke"], bs["theorie_erlang"]
    t += [
        "**@shabam: confirmations at 25 s** (your question in post 13; measurement and arithmetic only)",
        "",
        f"- 10 blocks at 75 s cover {n(BS['zeit_von_10_bei_75s_s'])} s on average; at 25 s the same expected "
        f"time is {BS['bloecke_gleiche_zeit_bei_25s']} blocks (with the measured mean of "
        f"{n(BS['gemessenes_mittel_s'], 2)} s: {BS['bloecke_gleiche_zeit_beim_gemessenen_mittel']} blocks).",
        f"- Measured on the testnet: 30 consecutive NU7 blocks spanned a median of {n(G['median_s'])} s, "
        f"p90 {n(G['p90_s'])} s, p99 {n(G['p99_s'])} s ({n(G['fenster'])} overlapping windows).",
        f"- For comparison, exponential intervals: 10 × 75 s median {n(T['10_bei_75s']['median_s'])} s, "
        f"p90 {n(T['10_bei_75s']['p90_s'])} s, p99 {n(T['10_bei_75s']['p99_s'])} s; "
        f"30 × 25 s median {n(T['30_bei_25s']['median_s'])} s, p90 {n(T['30_bei_25s']['p90_s'])} s, "
        f"p99 {n(T['30_bei_25s']['p99_s'])} s.",
    ]
    Z = BS.get("zuhoerer")
    if Z:
        rate = (f"{n(Z['abgehaengt'])} of {n(Z['angekuendigte_bloecke'])} announced blocks "
                f"({pct(Z['anteil_abgehaengt'], 2)})")
        if Z.get("obergrenze_95_bei_null") is not None:
            rate += f"; with none observed, the 95 % upper bound is {pct(Z['obergrenze_95_bei_null'], 2)}"
        t += [f"- Stale/orphan rate, listener window only: {rate}. Deepest reorg observed: "
              f"{n(Z['tiefster_zweig'])} block(s).", ""]
    else:
        t += ["- Stale/orphan rate and deepest reorg: not measured (no valid listener run), see above.", ""]
    t += [
        "**Not measured**: orphaned blocks and reorg depth since activation (only in the listener window), "
        "arrival times on our own nodes (we run none), Equihash solutions and block contents (headers only).",
        "",
        "Method: headers fetched directly from testnet peers via P2P (`getheaders`), anchored at a Zebra "
        "checkpoint, checked for hash linkage and proof of work against nBits, cross-checked against further "
        "peers. Scripts and data: `scripts/zcash/`, `data/zcash/` (kaspa-pulse repository).",
        "",
    ]
    return "\n".join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()
    r = json.load(open(args.json))
    with open(args.aus, "w") as f:
        f.write(entwurf(r))


if __name__ == "__main__":
    main()
