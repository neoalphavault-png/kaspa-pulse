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
import re
import sys
from collections import Counter
from datetime import datetime


def n(x, nk=0):
    if x is None:
        return "n/a"
    if isinstance(x, int) or nk == 0:
        return f"{round(x):,}"
    return f"{x:,.{nk}f}"


def pct(x, nk=2):
    return "n/a" if x is None else f"{x * 100:.{nk}f} %"


def fenster(L):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    a, b = (datetime.strptime(x, fmt) for x in L["fenster_utc"])
    bis = f"{b:%H:%M}" if a.date() == b.date() else f"{b:%d %b %Y %H:%M}"
    return f"{a:%d %b %Y}, {a:%H:%M} to {bis} UTC ({(b - a).total_seconds() / 60:.0f} min)"


# Regel fuer Texte nach aussen (Ben, 17.10.2026): im Fliesstext keine
# Doppelpunkte, Gedankenstriche oder Pfeile. Tabellen und Uhrzeiten sind
# ausgenommen. Die Pruefung meldet Verstoesse, statt den Lauf abzubrechen.
VERBOTEN = re.compile(r"[–—→←⇒]|->|<-|(?<!\d):(?!\d)")


def zeitstempel_satz(z):
    rw, vo = z["rueckwaerts_anzahl"], z["voraus_anzahl"]
    a = "No timestamps went backwards" if rw == 0 else f"There were {n(rw)} timestamps going backwards"
    b = "none were" if vo == 0 else f"{n(vo)} were"
    return f"{a}, and {b} more than 10 min ahead of the median of the next 11 blocks."


# Ben, 18.10.2026: kein Satz beginnt mit einer Ziffer.
SATZ_ZIFFER = re.compile(r"(?:^|[.!?]\s+)(\d)")


def regel_pruefen(text):
    treffer = []
    for i, zeile in enumerate(text.splitlines(), 1):
        if zeile.lstrip().startswith("|"):
            continue  # Tabelle
        for m in SATZ_ZIFFER.finditer(zeile.lstrip("*- ")):
            treffer.append(f"zeile {i}, satz beginnt mit ziffer: {zeile[max(0, m.start() - 10):m.end() + 30]}")
        for m in VERBOTEN.finditer(zeile):
            treffer.append(f"zeile {i}, zeichen {m.group()!r}: {zeile[max(0, m.start() - 30):m.end() + 30]}")
    return treffer


def entwurf(r):
    B, A, E = r["bereich"], r["abstaende"], r["abstaende"]["erwartung_exponentiell"]
    nf, z, bs = r["nachfuehrung"], r["zeitstempel"], r["bestaetigungen"]
    L = r.get("lauscher")
    t = [
        f"Ahead of the mainnet go/no-go on 20 October, here are our final independent counts for NU7 on "
        f"the public testnet, covering blocks {n(B['von_hoehe'])} to {n(B['bis_hoehe'])} "
        f"({n(B['bloecke'])} blocks) with a cut-off of {r['stichtag_utc']}. These are numbers only, without assessment.",
        "",
        f"We measured each block interval as the timestamp of a block minus that of its parent, starting at "
        f"{n(B['von_hoehe'] + 1)}, and compare them with exponential intervals at a 25 s mean.",
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
        # Ben, 17.10.2026: loest das offene Versprechen aus Beitrag 24 ein. Die
        # 19.5 s ueber 300 Bloecke sind das Zitat von damals, der Rest kommt aus den Daten.
        f"In post 24 we quoted a dashboard median of 19.5 s over 300 blocks. Over {n(B['bloecke'])} blocks "
        f"the median is {n(float(A['median_s']), 1)} s against {n(E['median_s'], 1)} s expected.",
        "",
        f"We found {nf['spruenge']} hashrate jumps of 2x or more. After them the difficulty came within ±15 % of "
        f"the new level after a median of {n(nf['median_bloecke'])} blocks ({n(nf['median_min'], 1)} min), "
        f"and the longest catch-up took {n(nf['max_bloecke'])} blocks. "
        f"{zeitstempel_satz(z)} Since activation there "
        f"{'was' if r['mindestschwierigkeit']['anzahl'] == 1 else 'were'} "
        f"{n(r['mindestschwierigkeit']['anzahl'])} minimum-difficulty "
        f"{'block' if r['mindestschwierigkeit']['anzahl'] == 1 else 'blocks'}.",
        "",
        "**Listener, as promised in post 24**",
        "",
    ]
    if L:
        sw = Counter(p["software"] for p in L["peers"])
        versionen = ", ".join(f"`{v}` ({c})" for v, c in sorted(sw.items()))
        zk = L["zakura_minus_zebra_ms"]
        t += [
            f"One listener at one location ran on Saturday, not our own node. The actual window was {fenster(L)}. "
            "It kept connections to Zebra and Zakura nodes and logged every block announcement with its arrival "
            "time, and these arrival times include the path from the node to the listener. "
            f"Of {n(L['kettenbloecke_im_fenster'])} chain blocks with timestamps in the window it saw "
            f"{n(L['davon_angekuendigt_gesehen'])} announced. "
            + (f"Of the announced blocks {n(L['abgehaengt_anzahl'])} did not end up in the chain"
               if L['abgehaengt_anzahl'] else "Every announced block ended up in the chain")
            + f", and the deepest branch was {n(L['groesste_tiefe'])} "
            f"{'block' if L['groesste_tiefe'] == 1 else 'blocks'}. "
            + (f"For the {n(zk['bloecke'])} blocks announced by both, the first Zakura announcement came a median of "
               f"{n(zk['median'])} ms after the first Zebra announcement (p10 {n(zk['p10'])} ms, p90 {n(zk['p90'])} ms). "
               if zk["bloecke"] else "No block was announced by both Zebra and Zakura peers. ")
            + f"The peers ran {versionen}, with the number of connections in brackets.",
            "",
        ]
    else:
        t += [f"We could not measure this part because {r.get('lauscher_pruefung_en') or 'there was no listener run'}.", ""]
    G, T, Z = bs["gemessen_spanne_30_bloecke"], bs["theorie_erlang"], bs.get("zuhoerer")
    alt, neu = T["10_bei_75s"], T["30_bei_25s"]
    t += [
        "**@shabam, confirmations at 25 s** (your question in post 13, measurement and arithmetic only)",
        "",
        f"Ten blocks at 75 s cover {n(bs['zeit_von_10_bei_75s_s'])} s on average, and at 25 s the same expected time "
        f"is {bs['bloecke_gleiche_zeit_bei_25s']} blocks ({bs['bloecke_gleiche_zeit_beim_gemessenen_mittel']} blocks "
        f"with the measured mean of {n(bs['gemessenes_mittel_s'], 2)} s). On the testnet 30 consecutive NU7 blocks "
        f"spanned a median of {n(G['median_s'])} s, p90 {n(G['p90_s'])} s and p99 {n(G['p99_s'])} s over "
        f"{n(G['fenster'])} overlapping windows. With exponential intervals 10 × 75 s give a median of "
        f"{n(alt['median_s'])} s, p90 {n(alt['p90_s'])} s and p99 {n(alt['p99_s'])} s, and 30 × 25 s give "
        f"{n(neu['median_s'])} s, {n(neu['p90_s'])} s and {n(neu['p99_s'])} s.",
        "",
    ]
    if Z:
        satz = (f"In the listener window {n(Z['abgehaengt'])} of {n(Z['angekuendigte_bloecke'])} announced blocks "
                f"were stale or orphaned ({pct(Z['anteil_abgehaengt'], 2)})")
        if Z.get("obergrenze_95_bei_null") is not None:
            satz += f", and with none observed the 95 % upper bound is {pct(Z['obergrenze_95_bei_null'], 2)}"
        satz += f". The deepest reorg we observed was {n(Z['tiefster_zweig'])} {'block' if Z['tiefster_zweig'] == 1 else 'blocks'}."
        t += [satz, ""]
    else:
        t += ["We could not measure the stale or orphan rate and the deepest reorg without a valid listener run.", ""]
    # Ben, 17.10.2026: letzte Zeile, reine Rechnung. Nur wenn die Zahlen es tragen.
    if G["p99_s"] < alt["p99_s"]:
        t += [f"Thirty blocks at 25 s vary less than ten blocks at 75 s, p99 {n(G['p99_s'])} s measured against "
              f"{n(alt['p99_s'])} s expected for the old target.", ""]
    # Ben, 18.10.2026: Satz zu perfekten 25-s-Bloecken. "partly", weil die
    # Spruenge den Abstand zur Theorie nur zum Teil erklaeren (p99 ohne
    # Sprungphasen steht daneben).
    ohne = G.get("ohne_sprungphasen") or {}
    if G["p99_s"] > neu["p99_s"]:
        teil = (f", partly because of the hashrate jumps ({n(ohne['p99_s'])} s without the windows around them)"
                if ohne.get("p99_s") and ohne["p99_s"] > neu["p99_s"] else " because of the hashrate jumps")
        t += [f"For perfect 25 s blocks the p99 over 30 blocks would be about {n(neu['p99_s'])} s. The measured "
              f"{n(G['p99_s'])} s sits above that{teil}, and still well below the {n(alt['p99_s'])} s for "
              "10 blocks at 75 s.", ""]
    else:
        t += [f"The p99 of 30 blocks at 25 s is {n(G['p99_s'])} s measured against {n(alt['p99_s'])} s expected "
              "for 10 blocks at the old target.", ""]
    t += [
        "We did not measure orphaned blocks and reorg depth since activation outside the listener window, arrival "
        "times on our own nodes because we run none, or Equihash solutions and block contents because we only "
        "fetched headers.",
        "",
        "We fetched the headers directly from testnet peers via P2P (`getheaders`), anchored them at a Zebra "
        "checkpoint, checked hash linkage and proof of work against nBits and cross-checked them against further peers.",
        "",
        # Ben, 17.10.2026: kein Verweis auf das Repo, die Seite fuellen wir Sonntag.
        "Method, CSV and the full report are at pulsehawk.io/zcash-nu7.",
        "",
    ]
    return "\n".join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()
    r = json.load(open(args.json))
    text = entwurf(r)
    for t in regel_pruefen(text):
        print(f"WARNUNG regel fliesstext: {t}", file=sys.stderr)
    with open(args.aus, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
