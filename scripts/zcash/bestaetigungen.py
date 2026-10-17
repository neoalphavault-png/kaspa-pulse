#!/usr/bin/env python3
"""bestaetigungen.py - Bestaetigungen bei 25 s, aus den Testnet-Daten gerechnet.

Anlass: Frage im Forum-Thread "NU7 Timeline" (Beitrag 13, 28.09.2026), ob bei
25-s-Bloecken mehr Bestaetigungen noetig sind. Hier steht nur Messung und
Rechnung, keine Empfehlung.

- Zeitgleichwertig: wie viele Bloecke bei 25 s dieselbe erwartete Zeit
  abdecken wie 10 Bloecke bei 75 s (750 s): 750 / 25 = 30; mit dem gemessenen
  mittleren Abstand entsprechend.
- Gemessen: Zeitspanne von 30 aufeinanderfolgenden NU7-Bloecken (Zeitstempel
  Block i+30 minus Block i), Median, p90, p99, Anteil ueber 750 s.
- Theorie zum Vergleich: Summe exponentieller Abstaende (Erlang-Verteilung)
  fuer 10 x 75 s und 30 x 25 s.
- Abgehaengte Bloecke und tiefster Zweig: nur aus dem Zuhoerer, nur in dessen
  Fenster. Bei 0 Funden die 95-%-Obergrenze nach der Dreierregel (3/n).
"""
import math
import statistics

ALT_S, NEU_S, ALT_N = 75.0, 25.0, 10


def erlang_cdf(x, n, mittel):
    """P(Summe von n Exponentialabstaenden mit Mittel `mittel` <= x)."""
    lam = x / mittel
    term, summe = math.exp(-lam), 0.0
    for k in range(n):
        summe += term
        term *= lam / (k + 1)
    return 1 - summe


def erlang_quantil(q, n, mittel):
    lo, hi = 0.0, mittel * n * 10
    for _ in range(100):
        mitte = (lo + hi) / 2
        if erlang_cdf(mitte, n, mittel) < q:
            lo = mitte
        else:
            hi = mitte
    return (lo + hi) / 2


def quantil(s, q):
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def rechnen(zeiten, mittel_gemessen, lauscher=None):
    ziel_s = ALT_N * ALT_S
    n_gleich = round(ziel_s / NEU_S)
    n_gemessen = math.ceil(ziel_s / mittel_gemessen)
    spannen = sorted(zeiten[i + n_gleich] - zeiten[i] for i in range(len(zeiten) - n_gleich))
    theorie = {
        f"{ALT_N}_bei_{int(ALT_S)}s": {"median_s": round(erlang_quantil(0.5, ALT_N, ALT_S)),
                                       "p90_s": round(erlang_quantil(0.9, ALT_N, ALT_S)),
                                       "p99_s": round(erlang_quantil(0.99, ALT_N, ALT_S))},
        f"{n_gleich}_bei_{int(NEU_S)}s": {"median_s": round(erlang_quantil(0.5, n_gleich, NEU_S)),
                                          "p90_s": round(erlang_quantil(0.9, n_gleich, NEU_S)),
                                          "p99_s": round(erlang_quantil(0.99, n_gleich, NEU_S))},
    }
    out = {
        "zeit_von_10_bei_75s_s": ziel_s,
        "bloecke_gleiche_zeit_bei_25s": n_gleich,
        "bloecke_gleiche_zeit_beim_gemessenen_mittel": n_gemessen,
        "gemessenes_mittel_s": mittel_gemessen,
        "gemessen_spanne_30_bloecke": {
            "fenster": len(spannen),
            "median_s": quantil(spannen, 0.5), "p90_s": quantil(spannen, 0.9), "p99_s": quantil(spannen, 0.99),
            "anteil_ueber_750s": round(sum(1 for x in spannen if x > ziel_s) / len(spannen), 4),
        },
        "theorie_erlang": theorie,
        "zuhoerer": None,
    }
    if lauscher:
        gesehen = lauscher["davon_angekuendigt_gesehen"]
        stale = lauscher["abgehaengt_anzahl"]
        n = gesehen + stale
        out["zuhoerer"] = {
            "angekuendigte_bloecke": n,
            "abgehaengt": stale,
            "anteil_abgehaengt": round(stale / n, 5) if n else None,
            # Dreierregel: bei 0 Funden in n Faellen liegt die Rate mit 95 % unter 3/n.
            "obergrenze_95_bei_null": round(3 / n, 5) if n and stale == 0 else None,
            "tiefster_zweig": lauscher["groesste_tiefe"],
            "fenster_utc": lauscher["fenster_utc"],
        }
    return out
