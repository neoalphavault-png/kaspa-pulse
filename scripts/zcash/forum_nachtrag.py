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


def wochentag(L):
    return datetime.strptime(L["fenster_utc"][0], "%Y-%m-%dT%H:%M:%SZ").strftime("%A")


def fenster(L):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    a, b = (datetime.strptime(x, fmt) for x in L["fenster_utc"])
    bis = f"{b:%H:%M}" if a.date() == b.date() else f"{b:%d %b %Y %H:%M}"
    return f"{a:%d %b %Y}, {a:%H:%M} to {bis} UTC ({(b - a).total_seconds() / 60:.0f} min)"


# Regel fuer Texte nach aussen (Ben, 17.10.2026): im Fliesstext keine
# Doppelpunkte, Gedankenstriche oder Pfeile. Tabellen und Uhrzeiten sind
# ausgenommen. Die Pruefung meldet Verstoesse, statt den Lauf abzubrechen.
VERBOTEN = re.compile(r"[–—→←⇒]|->|<-|(?<!\d):(?!\d)")


ZAHLWORT = "No One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve".split()


def satzanfang_zahl(x):
    """Zahl am Satzanfang als Wort (Ben, 18.10.2026: kein Satz beginnt mit einer Ziffer)."""
    return ZAHLWORT[x] if 0 <= x < len(ZAHLWORT) else None


def stale_satz(L):
    """Ben, 18.10.2026: "Five of the 780 announced blocks did not end up in the chain, each at depth 1." """
    k, n_ang, tief = L["abgehaengt_anzahl"], L["davon_angekuendigt_gesehen"] + L["abgehaengt_anzahl"], L["groesste_tiefe"]
    if k == 0:
        return f"All {n(n_ang)} announced blocks ended up in the chain. "
    wort = satzanfang_zahl(k)
    anfang = f"{wort} of the {n(n_ang)} announced blocks" if wort else f"In total {n(k)} of the {n(n_ang)} announced blocks"
    tiefe = (f", each at depth {n(tief)}" if all(x == tief for x in L.get("tiefen", [tief])) and len(L.get("tiefen", [])) == L.get("zweige", k)
             else f", the deepest at depth {n(tief)}")
    return f"{anfang} {'did' if k != 1 else 'did'} not end up in the chain{tiefe}. "


def zeitstempel_satz(z):
    """Genau das, was zeitstempel() in nu7_auswertung.py misst (Ben, 18.10.2026):
    voraus = mehr als 600 s nach dem Median der 11 FOLGENDEN Bloecke; dazu die
    Gegenprobe Zeitstempel ueber dem Median der 11 VORHERIGEN (Konsensregel)."""
    rw, vo, mtp = z["rueckwaerts_anzahl"], z["voraus_anzahl"], z["verletzt_median_der_11_vorgaenger"]
    a = "No timestamps went backwards" if rw == 0 else f"In total {n(rw)} timestamps went backwards"
    b = "none were" if vo == 0 else f"{n(vo)} were"
    c = ("Every timestamp was above the median of the 11 previous blocks." if mtp == 0
         else f"In total {n(mtp)} timestamps were at or below the median of the 11 previous blocks.")
    return f"{a}, and {b} more than 10 min ahead of the median of the 11 following blocks. {c}"


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
            f"On {wochentag(L)} we ran one listener at one location. It is not a full node. "
            f"The actual window was {fenster(L)}. "
            "It kept connections to Zebra and Zakura nodes and logged every block announcement with its arrival "
            "time, and these arrival times include the path from the node to the listener. "
            f"Of {n(L['kettenbloecke_im_fenster'])} chain blocks with timestamps in the window it saw "
            f"{n(L['davon_angekuendigt_gesehen'])} announced. "
            + stale_satz(L)
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
    # Ben, 18.10.2026: ein Absatz statt drei. Erst der Vergleich mit 10 x 75 s,
    # dann der Abstand zu perfekten 25-s-Bloecken ("partly", weil das p99 ohne
    # die Sprungphasen noch darueber liegt), dann der tiefste Reorg.
    ohne = G.get("ohne_sprungphasen") or {}
    teile = []
    if G["p99_s"] < alt["p99_s"]:
        teile.append(f"Thirty blocks at 25 s vary less than ten blocks at 75 s, p99 {n(G['p99_s'])} s measured "
                     f"against {n(alt['p99_s'])} s expected for the old target.")
    else:
        teile.append(f"The p99 of thirty blocks at 25 s is {n(G['p99_s'])} s measured against {n(alt['p99_s'])} s "
                     "expected for ten blocks at the old target.")
    if G["p99_s"] > neu["p99_s"]:
        if ohne.get("p99_s") and ohne["p99_s"] > neu["p99_s"]:
            grund = f", partly because of the hashrate jumps ({n(ohne['p99_s'])} s without the windows around them)"
        else:
            grund = " because of the hashrate jumps"
        teile.append(f"The measured value sits above the {n(neu['p99_s'])} s of perfect 25 s blocks{grund}.")
    if Z:
        teile.append(f"In the listener window the deepest reorg we observed was {n(Z['tiefster_zweig'])} "
                     f"{'block' if Z['tiefster_zweig'] == 1 else 'blocks'}.")
    else:
        teile.append("Without a valid listener run we could not measure the deepest reorg.")
    t += [" ".join(teile), ""]
    t += [
        "We did not measure orphaned blocks and reorg depth since activation outside the listener window, arrival "
        "times on our own nodes because we run none, or Equihash solutions and block contents because we only "
        "fetched headers.",
        "",
        "We fetched the headers directly from testnet peers via P2P (`getheaders`), anchored them at a Zebra "
        "checkpoint, checked hash linkage and proof of work against nBits and cross-checked them against further peers.",
        "",
        # Ben, 17.10.2026: kein Verweis auf das Repo, die Seite fuellen wir Sonntag.
        # Ben, 18.10.2026: die CSV folgt diese Woche.
        "Method and the full numbers are at pulsehawk.io/zcash-nu7. The CSV of all intervals follows there this week.",
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
