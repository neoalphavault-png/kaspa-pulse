# Miner nach dem Reward Cut am 4.11., Auswertung

Bericht für Ben zum Auftrag vom 2.11. mit den Fenstern vom 3.11., Frist Mi 11.11. 12:00 Berlin. Die Antwort in #data-requests geht am 11.11. um 17:00 raus. Die Frage aus #data-requests lautet „after the reward cut on 4 nov, does anything change in how fast miners move their coins?“ Alle Zahlen sind counted, aus unserem eigenen Mainnet-Knoten.

## Ergebnis in drei Sätzen

Innerhalb von 24 h wird vor und nach dem Cut derselbe Anteil der Coinbase-Ausgänge weiterbewegt, 90.80 % gegen 90.79 %. Innerhalb von 72 h sind es nach dem Cut 0.9 Prozentpunkte weniger, 94.63 % gegen 93.69 %. Der Median bis zur ersten Ausgabe steigt von 45 auf 50 Minuten.

## Fenster

| Fenster | Von (UTC) | Bis (UTC) | Länge |
|---|---|---|---|
| vor dem Cut | 2.11. 06:30 | 4.11. 13:45 | 55 h 15 min |
| nach dem Cut | 4.11. 13:45 | 6.11. 21:00 | 55 h 15 min |
| Tag vor dem Cut | 3.11. 13:45 | 4.11. 13:45 | 24 h |
| Tag nach dem Cut | 4.11. 13:45 | 5.11. 13:45 | 24 h |

- **Zwei gleich lange Fenster direkt vor und nach dem Cut,** wie am 3.11. festgelegt, statt der ersten Fenster vom 2.11.
- **Anfang am 2.11. um 06:30:** Unser Knoten konnte zu Beginn der Aufzeichnung nur bis zu seinem Pruning-Punkt am 2.11. um 06:28:56 UTC zurücklesen. Länger als 55 h 15 min kann das Fenster vor dem Cut also nicht sein, und das Fenster danach ist genauso lang.
- **Beobachtet bis 10.11. 02:47:02 UTC.** Jede Coinbase aus beiden Fenstern ist damit mindestens 72 h lang beobachtet.
- **Lückenlos:** 24 Läufe nacheinander, jeder liest ab dem letzten Kettenblock des Laufs davor. In allen 6,630 Minuten der beiden Fenster gibt es Kettenblöcke und neue Coinbase-Ausgänge.

## Je Fenster

| Fenster | Coinbase-Ausgänge | KAS aus Coinbase | in 24 h weiterbewegt | in 72 h weiterbewegt | Median bis zur ersten Ausgabe |
|---|---:|---:|---:|---:|---:|
| vor dem Cut | 1,986,596 | 4,103,035 | 90.80 % (KAS 90.79 %) | 94.63 % (KAS 94.63 %) | 45 min |
| nach dem Cut | 1,967,197 | 3,874,706 | 90.79 % (KAS 90.70 %) | 93.69 % (KAS 93.62 %) | 50 min |
| Tag vor dem Cut | 863,018 | 1,782,153 | 90.95 % (KAS 90.95 %) | 95.13 % (KAS 95.14 %) | 37 min |
| Tag nach dem Cut | 855,665 | 1,678,793 | 91.00 % (KAS 91.06 %) | 93.64 % (KAS 93.71 %) | 43 min |

- **Anteil:** Coinbase-Ausgänge, die innerhalb der Frist nach ihrer Entstehung zum ersten Mal ausgegeben wurden, geteilt durch alle Coinbase-Ausgänge des Fensters. In Klammern derselbe Anteil nach KAS.
- **Median:** die Zeit von der Coinbase bis zur ersten Ausgabe, auf die Minute. Ausgänge, die bis zum Ende der Beobachtung nicht ausgegeben sind, zählen als länger als jeder gemessene Verzug.
- **KAS aus Coinbase:** nach dem Cut 5.56 % weniger als davor, bei 0.98 % weniger Ausgängen.

## Was die Zahl misst und was nicht

Die Zahl misst, wie schnell eine Coinbase-Ausgabe nach ihrer Entstehung zum ersten Mal ausgegeben wird, aber nicht, wohin die Coins gehen, wer sie bewegt oder ob sie verkauft werden.

## Was wir weglassen

- **7 Tage:** Für das Fenster nach dem Cut wären 7 Tage erst am 13.11. um 21:00 UTC beobachtet, nach der Frist. Statt 7 Tagen zeigen wir 72 h für beide Fenster.
- **Frage 3, KAS an Adressen mit Börsen-Label:** weggelassen. Wir haben keine Labels mit source kaspalytics, und ohne eine solche Quelle führen wir keine Börsen.
- **Keine Adressen, keine Pool-Namen, kein Kurs.** Die Daten tragen nur Summen je Minute und je Entstehungsstunde.

## Wie gezählt wurde

- **Werkzeug:** `kp-coinbase` (Rust, rusty-kaspa v2.1.0) liest die UTXO-Änderungen der Kettenblöcke aus einem angehaltenen Mainnet-Knoten im Runner. Eine entfernte Coinbase-Ausgabe trägt den DAA-Score ihrer Entstehung. Daraus ergeben sich Entstehung und erste Ausgabe, ohne dass wir Bestände mitführen.
- **Läufe:** 24 Läufe von [Lauf 41698334356](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41698334356) auf dem Messbranch `messung/miner-nach-cut`, von 2.11. 06:28:56 bis 10.11. 02:47:02 UTC.
- **Daten:** `miner/daten/` auf diesem Branch, mit `stand.json`, `daa-zeit.csv`, `rein.csv` (je Minute neue Coinbase-Ausgaben) und `raus-<tag>.json` (je Entstehungsstunde der Verzug bis zur ersten Ausgabe, in Eimern). Die Eimer sind bis 6 h je Minute breit, bis 72 h je 5 Minuten und bis 8 Tage je 30 Minuten.
- **Auswertung:** `python3 scripts/miner_cut.py --auswerten --daten miner/daten --fenster vor 2026-11-02T06:30:00Z 2026-11-04T13:45:00Z --fenster nach 2026-11-04T13:45:00Z 2026-11-06T21:00:00Z`, dazu die beiden Tagesfenster. Der Selbsttest läuft ohne Fehler.

## Was Ben tun muss

- Den Antwort-Entwurf prüfen und am 11.11. um 17:00 in #data-requests posten.

<!-- discord -->
Miner nach dem Cut, Auswertung fertig. Zwei Fenster zu je 55 h 15 min direkt vor und nach dem Cut am 4.11. 13:45 UTC, lückenlos aus dem eigenen Knoten (counted). In 24 h weiterbewegt 90.80 % gegen 90.79 %, in 72 h 94.63 % gegen 93.69 %, Median bis zur ersten Ausgabe 45 gegen 50 min. Frage 3 weggelassen, keine Labels mit source kaspalytics. Bericht berichte/2026-11-10-miner-nach-cut.md
<!-- teil -->
📤 VON HAND, Antwort für #data-requests am Mi 11.11. um 17:00

we counted it on our own node. two windows of 55 h 15 min each, 2 nov 06:30 to 4 nov 13:45 utc before the cut and 4 nov 13:45 to 6 nov 21:00 utc after it.

within 24 h, 90.8 % of coinbase outputs were spent before the cut and 90.8 % after it. within 72 h it was 94.6 % before and 93.7 % after. the median time from coinbase to first spend went from 45 to 50 min.

this measures how soon a coinbase output is spent for the first time, not where the coins go, who moves them or whether they are sold. counted by kaspa pulse
<!-- /discord -->
