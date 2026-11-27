# Zweiter Wochenbericht Zcash und Bitcoin Cash, Entwurf (Auftrag Ben 23.11.2026, Frist Fr 27.11. 12:00 Berlin)

**Kopf:** Entwurf mit Zahlen aus unseren Datenbranches, Stand Fr 27.11. 05:32 UTC. Die Seite liegt als PR in pulsehawk-site (pulsehawk-site#107, Ben merged), die Texte für Forum und X stehen unten, Ben postet am So 29.11. Neu ist eine Lücke im Chipnet-Zuhörer vom 25.11. 15:53:16 bis 27.11. 05:36:39 UTC, Ursache und Neustart unten.

<!-- discord -->
Zweiter Wochenbericht als Entwurf, die Seite liegt als PR in pulsehawk-site bei Ben. Zcash zählt 78 verwaiste Blöcke neben 20.884 Kettenblöcken, 6 Bestätigungen üblich 2 min 22 s. Der Chipnet-Zuhörer hatte eine Lücke vom 25.11. 15:53 bis 27.11. 05:36 UTC, weil der Folgelauf nicht starten konnte, er läuft wieder. Bericht berichte/2026-11-27-wochenbericht-2-entwurf.md
<!-- /discord -->

## Bens Vorgaben (22. bis 25.11.), umgesetzt

- **BCH Mainnet:** Die ganze Tabelle (1, 3 und 6 Bestätigungen, üblich, 9 von 10, 99 von 100, gezählt neben gerechnet) steht nur auf der Seite. Forum und X nennen nur die Zeile für 6 Bestätigungen.
- **Difficulty 1:** Jede Chipnet-Spanne trägt den Hinweis, auch im Forumstext. Der X-Text nennt keine Chipnet-Spanne.
- **Zebra ab 7.1.0:** Ohne neuen Bau aus den Lauf-Metadaten gezählt. Es sind Verbindungen eines Zuhörers, keine eindeutigen Knoten, und eine Alpha zählt nicht als 7.1.0.
- **Fenster:** Jede Zahl nennt ihr Fenster in UTC. Die Woche beginnt an den Stichzeiten von Wochenbericht 1.
- **12 oder 120 Blöcke:** Beide stehen auf der Seite. Für das Forum gibt es zwei Fassungen, Entscheidung am Entwurf (Frage 1).

## a) Zahlentabelle

Den Zcash-Lauf habe ich am 27.11. um 05:30 UTC von Hand gestartet (workflow_dispatch, keine Workflow-Änderung). Die Chipnet-Köpfe kamen über den Anstoß auf dem Datenbranch. Die Wartezeit für k Bestätigungen ist die Zeit von einem Block, bis k weitere Blöcke gefolgt sind.

| Zahl | Wert | Art | Datei | Commit | Stichzeit oder Fenster (UTC) |
| --- | --- | --- | --- | --- | --- |
| Zcash, Kettenblöcke beim Zuhörer | 20.884 | counted | `data/zcash-mainnet/lauscher-dauer/` Läufe s38 bis s64, ausgewertet mit `scripts/zcash/lauscher_auswertung.py` | `c8d3db9a` | 2026-11-21 04:20:03 bis 2026-11-27 05:28:40 |
| Zcash, verwaiste Blöcke (untere Grenze) | 78 (0,37 %), davon 6 ohne Kopf, Tiefe höchstens 1 | counted | wie oben | `c8d3db9a` | wie oben, Kette `904fd71b` |
| Zcash, Blockabstände | 20.569, Median 17 s, Mittel 25,02 s | counted | `data/zcash-mainnet/koepfe.csv.gz` | `904fd71b` | 2026-11-21 06:34:04 bis 2026-11-27 05:31:38, Abruf 2026-11-27T05:31:38Z |
| Zcash, Anteil über 75 s | 4,73 % | counted | wie oben | `904fd71b` | wie oben |
| Zcash, 1 Bestätigung, üblich / 9 von 10 / 99 von 100 | 17 s / 57 s / 1 min 54 s | counted | wie oben | `904fd71b` | wie oben |
| Zcash, ideale 25-s-Kette, 1 Bestätigung | 17 s / 58 s / 1 min 55 s | computed | Erlang, Mittel 25 s | - | - |
| Zcash, 3 Bestätigungen, üblich / 9 von 10 / 99 von 100 | 1 min 7 s / 2 min 13 s / 3 min 28 s | counted | wie oben | `904fd71b` | wie oben |
| Zcash, ideale 25-s-Kette, 3 Bestätigungen | 1 min 7 s / 2 min 13 s / 3 min 30 s | computed | Erlang, Mittel 25 s | - | - |
| Zcash, 6 Bestätigungen, üblich / 9 von 10 / 99 von 100 | 2 min 22 s / 3 min 51 s / 5 min 28 s | counted | wie oben | `904fd71b` | wie oben |
| Zcash, ideale 25-s-Kette, 6 Bestätigungen | 2 min 22 s / 3 min 52 s / 5 min 28 s | computed | Erlang, Mittel 25 s | - | - |
| Zcash, Zebra-Verbindungen ab 7.1.0 | 492 von 604 (81,5 %), je Lauf 50,0 bis 96,0 % | counted | `data/zcash-mainnet/lauscher-dauer/s*-meta.json` (`peers[].software`) | `c8d3db9a` | Läufe s38 bis s64 |
| BCH Chipnet, Abstände der Woche | 8.379, Blöcke 340.761 bis 349.139, Median 45 s, Mittel 61,44 s | counted | `data/bch-chipnet/koepfe.csv.gz` | `fb089387` | 2026-11-21 06:31:50 bis 2026-11-27 05:31:27, Abruf 2026-11-27T05:32:00Z |
| BCH Chipnet, Anteil Difficulty 1 in der Woche | 26,6 % (2.226 Blöcke) | counted | wie oben | `fb089387` | wie oben |
| BCH Chipnet, 1 Blöcke nach Ankunft, üblich / 9 von 10 / 99 von 100 | 1 min 1 s / 2 min 4 s / 4 min 6 s (Kopfzeit 45 s / 2 min 3 s / 3 min 40 s; 60-s-Ziel 42 s / 2 min 18 s / 4 min 36 s computed) | counted | `data/bch-chipnet/lauscher/bloecke.csv`, Kopfzeit aus `koepfe.csv.gz` | `0af3d937`, `fb089387` | 2026-11-21 04:25:41 bis 2026-11-25 15:51:53, Blöcke 340.629 bis 346.134 |
| BCH Chipnet, 3 Blöcke nach Ankunft, üblich / 9 von 10 / 99 von 100 | 3 min 8 s / 6 min 5 s / 10 min 28 s (Kopfzeit 2 min 49 s / 6 min 3 s / 9 min 50 s; 60-s-Ziel 2 min 40 s / 5 min 19 s / 8 min 24 s computed) | counted | `data/bch-chipnet/lauscher/bloecke.csv`, Kopfzeit aus `koepfe.csv.gz` | `0af3d937`, `fb089387` | 2026-11-21 04:25:41 bis 2026-11-25 15:51:53, Blöcke 340.629 bis 346.134 |
| BCH Chipnet, 6 Blöcke nach Ankunft, üblich / 9 von 10 / 99 von 100 | 6 min 20 s / 12 min 7 s / 19 min 58 s (Kopfzeit 5 min 48 s / 11 min 5 s / 18 min 59 s; 60-s-Ziel 5 min 40 s / 9 min 16 s / 13 min 6 s computed) | counted | `data/bch-chipnet/lauscher/bloecke.csv`, Kopfzeit aus `koepfe.csv.gz` | `0af3d937`, `fb089387` | 2026-11-21 04:25:41 bis 2026-11-25 15:51:53, Blöcke 340.629 bis 346.134 |
| BCH Chipnet, 12 Blöcke nach Ankunft, üblich / 9 von 10 / 99 von 100 | 12 min 40 s / 23 min 49 s / 37 min 37 s (Kopfzeit 11 min 52 s / 20 min 55 s / 36 min 45 s; 60-s-Ziel 11 min 40 s / 16 min 36 s / 21 min 29 s computed) | counted | `data/bch-chipnet/lauscher/bloecke.csv`, Kopfzeit aus `koepfe.csv.gz` | `0af3d937`, `fb089387` | 2026-11-21 04:25:41 bis 2026-11-25 15:51:53, Blöcke 340.629 bis 346.134 |
| BCH Chipnet, 120 Blöcke nach Ankunft, üblich / 9 von 10 / 99 von 100 | 2 h 5 min 19 s / 3 h 54 min 42 s / 5 h 45 min 18 s (Kopfzeit 2 h 0 min 25 s / 3 h 10 min 5 s / 5 h 38 min 23 s; 60-s-Ziel 1 h 59 min 40 s / 2 h 14 min 14 s / 2 h 26 min 57 s computed) | counted | `data/bch-chipnet/lauscher/bloecke.csv`, Kopfzeit aus `koepfe.csv.gz` | `0af3d937`, `fb089387` | 2026-11-21 04:25:41 bis 2026-11-25 15:51:53, Blöcke 340.629 bis 346.134 |
| BCH Mainnet, 1 Bestätigung, üblich / 9 von 10 / 99 von 100 | gezählt 6 min 48 s / 23 min 31 s / 48 min 27 s, gerechnet 6 min 56 s / 23 min 2 s / 46 min 3 s | counted und computed | `data/bch-mainnet/wartezeit.json` auf `messung/bch-mainnet-probe` | `b7be3b44` | 2026-05-15 12:55:32 bis 2026-11-22 09:49:02, 27.314 Abstände |
| BCH Mainnet, 3 Bestätigungen, üblich / 9 von 10 / 99 von 100 | gezählt 26 min 38 s / 54 min 45 s / 1 h 28 min 5 s, gerechnet 26 min 44 s / 53 min 13 s / 1 h 24 min 4 s | counted und computed | `data/bch-mainnet/wartezeit.json` auf `messung/bch-mainnet-probe` | `b7be3b44` | 2026-05-15 12:55:32 bis 2026-11-22 09:49:02, 27.314 Abstände |
| BCH Mainnet, 6 Bestätigungen, üblich / 9 von 10 / 99 von 100 | gezählt 56 min 41 s / 1 h 35 min 31 s / 2 h 17 min 29 s, gerechnet 56 min 42 s / 1 h 32 min 45 s / 2 h 11 min 5 s | counted und computed | `data/bch-mainnet/wartezeit.json` auf `messung/bch-mainnet-probe` | `b7be3b44` | 2026-05-15 12:55:32 bis 2026-11-22 09:49:02, 27.314 Abstände |

**Zcash, Zuhörer:** Ausgewertet sind nur die Läufe s38 bis s64 (27 Läufe), gegen die Kette vom 27.11. 05:31 UTC, die nach den Läufen abgerufen wurde. Lauf s38 begann 7 min 40 s vor dem Ende von s37, dem letzten Lauf in Wochenbericht 1. Einzelne Blöcke dieser Minuten können in beiden Berichten stehen.

**BCH Chipnet:** Die Kopfzahlen laufen über die ganze Woche. Die Ankunftszeiten enden am 25.11. 15:51:53 UTC, wegen der Lücke unten.

## Lücken der Zuhörer (UTC)

- **Zcash, Serie „dauer“ (27 Läufe dieser Woche):** keine, die Läufe überlappen.
- **BCH Chipnet:** eine Lücke von 2026-11-25 15:53:16 bis 2026-11-27 05:36:39, 37 h 43 min 23 s.
  - **Ursache:** Der Lauf vom 25.11. ab 10:22 UTC wollte um 15:45 UTC den Folgelauf starten. Die GitHub-API antwortete zweimal mit HTTP 503 und 504. Der Workflow gibt dann nur eine Warnung aus, und die Kette endete mit dem Lauf um 15:53:16 UTC.
  - **Behebung:** Ich habe den Zuhörer am 27.11. um 05:36:39 UTC von Hand neu gestartet (workflow_dispatch mit denselben Eingaben, keine Workflow-Änderung).
  - **Vorschlag:** Der Workflow sollte den Start des Folgelaufs nach einem Fehler einige Male wiederholen. Das wäre eine Workflow-Änderung, also ein PR an Ben (Frage 2).

## b) Seite auf pulsehawk.io

pulsehawk-site#107:
- `/weekly/2026-11-29`, gebaut aus `data/weekly/2026-11-29.json`, das der Rechenlauf schreibt.
- `b2b_pages.py` baut jetzt eine Seite je Datei in `data/weekly/`. Woche 1 bleibt bytegleich.
- Textprüfung 0 von 27 Seiten mit Funden. Ben merged.

## c) Forum Zcash 59124 (116 Wörter)

> Our second weekly count, 21 Nov 06:34 utc to 27 Nov 05:31 utc from our own headers. The median block interval was 17 s, and 4.73 % of intervals ran longer than 75 s. Six confirmations usually took 2 min 22 s, 9 of 10 times within 3 min 51 s and 99 of 100 times within 5 min 28 s. Our listener counted 78 orphaned blocks next to 20,884 chain blocks, one vantage point, so read it as a lower bound. Of the Zebra connections our listener made, 81.5 % reported 7.1.0 or newer, connections and not distinct nodes. @dismad does the 99 of 100 line help you more than the 9 of 10 one?

## d) Forum BCH 2173, Fassung mit 12 Blöcken (115 Wörter)

> Week two on chipnet with one minute blocks. By our own headers from 21 Nov 06:31 utc to 27 Nov 05:31 utc, 26.6 % of the blocks carry difficulty 1, a testnet rule absent on mainnet, and they are part of every wait. By first sighting at our listener, 21 Nov 04:25 utc to 25 Nov 15:51 utc, twelve blocks usually took 12 min 40 s and 9 of 10 times came within 23 min 49 s. Our listener has a gap from 25 Nov 15:53 utc to 27 Nov 05:36 utc. On mainnet, counted since 15 May, six blocks usually took 56 min 41 s against 56 min 42 s computed for 600 s.

## d') Forum BCH 2173, Fassung mit 120 Blöcken (119 Wörter)

> Week two on chipnet with one minute blocks. By our own headers from 21 Nov 06:31 utc to 27 Nov 05:31 utc, 26.6 % of the blocks carry difficulty 1, a testnet rule absent on mainnet, and they are part of every wait. By first sighting at our listener, 21 Nov 04:25 utc to 25 Nov 15:51 utc, 120 blocks usually took 2 h 5 min 19 s and 9 of 10 times came within 3 h 54 min 42 s. Our listener has a gap from 25 Nov 15:53 utc to 27 Nov 05:36 utc. On mainnet, counted since 15 May, six blocks usually took 56 min 41 s against 56 min 42 s computed for 600 s.

## e) X-Post @pulsehawkio (71 Wörter)

> Bitcoin Cash mainnet, counted from our own headers, 27,314 block intervals from 15 May to 22 Nov. Six confirmations usually took 56 min 41 s, and the 600 s rule gives 56 min 42 s. The slow end runs longer than computed, 9 of 10 waits came within 1 h 35 min 31 s against 1 h 32 min 45 s. Exchanges and payment processors, which wait do you plan for?

## PR-Nummern

- pulsehawk-site#107, Wochenseite 2, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. Im Forum 2173 die Fassung mit 12 Blöcken (heutiges Fenster) oder mit 120 Blöcken (Fenster nach dem Upgrade)? Auf der Seite stehen beide.
2. Soll der Chipnet-Zuhörer den Start des Folgelaufs bei einem Fehler der GitHub-API wiederholen? Das wäre eine kleine Änderung in `bch-chipnet-lauscher.yml`, also ein PR an dich. Die Zcash-Kette hat dieselbe Stelle.
3. Miner je Fenster (Auftrag vom 25.11.): Deine Wahl zwischen eigenem Knoten (Befehl auf c2) und fremder Quelle (Freigabe des Hosts) steht noch aus.

## Was Ben tun muss

- pulsehawk-site#107 mergen, am besten am So 29.11. vor dem Posten.
- Die Texte c, d oder d' und e posten.
- Die drei Fragen beantworten.
