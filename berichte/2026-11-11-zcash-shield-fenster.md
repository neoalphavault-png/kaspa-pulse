# Zcash, zwei Fenster der Blockabstände für den Thread „Can I Shield“ (11.11.2026)

Ben am 11.11.: Zusage im Zcash-Forum, Thread 59146. Zwei Fenster aus unserem Header-Client, Frist Fr 13.11. 09:00. Keine Wertung fremder Zahlen, keine Position zum Upgrade.

<!-- discord -->
Zcash, zwei Fenster für den Thread Can I Shield: vor NU7 (Blöcke 3.520.000 bis 3.543.404) Median 52,0 s bei n 23.404, nach NU7 (3.543.405 bis 3.559.470) Median 17,0 s bei n 16.065. Die computed Gegenprobe liegt bei 52,23 s und 17,50 s. Satz für das Forum im Bericht. Bericht berichte/2026-11-11-zcash-shield-fenster.md
<!-- /discord -->

## Grundlage

- **Köpfe:** `data/zcash-mainnet/koepfe.csv.gz` auf `messung/zcash-mainnet`, Abruf 11.11. 08:21 UTC (Commit `f88ca60b`), Spitze 3.561.317.
  - Geprüft auf Verkettung, Arbeit und Checkpoints.
  - Gegenprobe 500 von 500 gleich bei zwei Peers.
  - Den Abruf habe ich heute von Hand gestartet (`zcash-mainnet.yml`, stand=false), weil die Köpfe vom Vortag nur bis 3.558.651 reichten.
- **Abstand:** Kopfzeit eines Blocks minus Kopfzeit seines Vorgängers, gezählt zwischen aufeinanderfolgenden Blöcken innerhalb des Fensters.
  - Bei n+1 Blöcken gibt es also n Abstände.
  - Der Abstand von 3.543.404 zu 3.543.405, also über die Aktivierung, gehört zu keinem der beiden Fenster.
  - Der Report PH-UR-2026-001 rechnet M1 anders, nämlich mit dem Abstand jedes Blocks zu seinem Vorgänger ab 3.543.405. Die Zahlen sind deshalb nicht eins zu eins vergleichbar.
- **Quantile:** linear interpoliert.
- **Gegenprobe (computed):** Median gleich Mittel mal ln 2, wie bei exponentiell verteilten Abständen.

## Ergebnis

| | Vorher | Nachher |
|---|---|---|
| Blöcke | 3.520.000 bis 3.543.404 | 3.543.405 bis 3.559.470 |
| Zeitraum (Kopfzeit, UTC) | 16.10.2026 16:40:25 bis 6.11.2026 02:33:21 | 6.11.2026 02:34:02 bis 10.11.2026 19:15:07 |
| n Abstände | 23.404 | 16.065 |
| Median (counted) | 52,0 s | 17,0 s |
| Mittel (counted) | 75,354 s | 25,251 s |
| p90 (counted) | 172,0 s | 59,0 s |
| p99 (counted) | 348,0 s | 116,0 s |
| negative Abstände | 0 | 0 |
| Median computed, Mittel × ln 2 | 52,23 s | 17,50 s |

- **Endhöhe des Nachher-Fensters:** 3.559.470, also 3.543.405 + 16.065.
- Die Werte sind auch als JSON im Bericht unten.

## Satz für den Forumsbeitrag

> From our own header client, the 23,404 block intervals from block 3,520,000 to 3,543,404 (16 Oct 16:40 utc to 6 Nov 02:33 utc) have a median of 52 s, and the first 16,065 intervals from block 3,543,405 to 3,559,470 (6 Nov 02:34 utc to 10 Nov 19:15 utc) have a median of 17 s.

Mit Gegenprobe, falls gewünscht:

> For comparison, the mean interval times ln 2, the median an exponential distribution would give, is 52.2 s before and 17.5 s after.

Textregeln geprüft: kein Doppelpunkt außer in Uhrzeiten, kein Gedankenstrich, kein Pfeil, kein Satz beginnt mit einer Ziffer.

## Zahlen als JSON

```
{"vorher": {"bloecke": [3520000, 3543404], "zeit_utc": ["2026-10-16 16:40:25", "2026-11-06 02:33:21"], "n": 23404,
            "median_s": 52.0, "mittel_s": 75.354, "p90_s": 172.0, "p99_s": 348.0, "negativ": 0, "computed_median_s": 52.23},
 "nachher": {"bloecke": [3543405, 3559470], "zeit_utc": ["2026-11-06 02:34:02", "2026-11-10 19:15:07"], "n": 16065,
             "median_s": 17.0, "mittel_s": 25.251, "p90_s": 59.0, "p99_s": 116.0, "negativ": 0, "computed_median_s": 17.5},
 "quelle": "data/zcash-mainnet/koepfe.csv.gz auf messung/zcash-mainnet, Commit f88ca60b"}
```

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

- Den Forumsbeitrag im Thread 59146 posten.
