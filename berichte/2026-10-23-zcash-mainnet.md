# Zcash Mainnet rund um NU7, Bericht 23.10.2026

Auftrag (Ben, 23.10.2026): Zcash NU7 auf dem Mainnet, erwartet gegen gezählt. NU7 aktiviert bei Höhe 3.543.405. Zuerst Machbarkeit prüfen, dann Baseline, Vorhersage, Zählung ab Aktivierung, Entwürfe nach #ph-entwuerfe.

## 1. Machbarkeit: ja

Der eigene Header-Client kommt sauber an Mainnet-Peers. Lauf 2 auf `zcash/mainnet`:

- 38.125 Köpfe ab dem Zebra-Checkpoint 3.489.716 bis zur Spitze 3.527.841
- Verkettung, Arbeitsnachweis aus nBits und 89 Zebra-Checkpoints geprüft
- kein Peer-Fehler, kein verworfener Abzweig
- Hauptpeer /Zebra:7.0.0/, der Abruf der Köpfe dauerte unter einer Minute
- Gegenprobe mit zwei Peers /Zebra:7.0.0/, je 500 von 500 Hashes gleich
- Software der Peers: /Zebra:7.0.0/, /Zakura:1.7.0/, /Zakura:1.7.0-modified/, /Zakura:1.5.1/, /Zakura:1.5.0/

Zwei Befunde aus dem ersten Lauf, beide behoben:

- Die Mainnet-Knoten melden Protokoll 170190; wir hatten 170180 aus dem Testnet. Nach der Aktivierung trennen NU7-Knoten ältere Versionen wahrscheinlich. Der Client meldet auf dem Mainnet jetzt 170190.
- Die Gegenprobe schickte nur einen Hash im Locator. Sie nutzt jetzt einen vollen Locator wie der Hauptabruf.

Zakura-Peers beantworten `getheaders` in unserem Lauf weiterhin nicht. Sechs Versuche mit vollem Locator liefen nach 45 s in eine Zeitüberschreitung. Der Handschlag gelingt, dieselbe Beobachtung gab es im Testnet. Wir zählen deshalb über Zebra-Peers und halten Zakura als "ohne Antwort" fest, ohne Wertung.

## 2. Baseline vor NU7, gegen eine ideale 75-s-Kette

Blöcke 3.489.718 bis 3.527.841, 20.09.2026 07:01 bis 23.10.2026 12:49 UTC, 38.124 Abstände.

| Kennzahl | gezählt | berechnet (75 s) |
|---|---:|---:|
| Mittel | 75,34 s | 75 s |
| Median | 53,0 s | 52,0 s |
| p90 | 172,0 s | 172,7 s |
| p99 | 349,0 s | 345,4 s |
| Anteil über 225 s | 5,11 % | 4,98 % |
| Anteil über 518 s | 0,113 % | 0,1 % |
| Längste Lücke | 930 s, vor Block 3.524.451 am 20.10. 14:01 UTC | 834 s |
| Negative Abstände | 0 | 0 |

Die Wochen W39 bis W43 liegen alle zwischen 75,26 und 75,41 s im Mittel. Die Kette läuft vor NU7 sehr nah an der idealen 75-s-Kette.

## 3. Vorhersage für Höhe 3.543.405 (erster Stand)

Noch 15.564 Blöcke ab der Spitze. Das Tempo der letzten 14 vollen Tage liegt bei 75,29 s, die Tagesmittel zwischen 74,7 und 76,1 s.

| Rechnung | Zeitpunkt UTC |
|---|---|
| Gezähltes Tempo, Median | 06.11.2026 02:21 |
| Band 5 % bis 95 % | 05.11.2026 22:02 bis 06.11.2026 06:40 (8,6 h) |
| Berechnet mit genau 75 s | 06.11.2026 01:04 |
| Zakura (laut Ben) | 06.11.2026 00:50 |

Das Band entsteht in zwei Schritten:

- 20.000 Ziehungen mit Seed 2027. Für jede Ziehung wird das Tempo aus 14 zufällig gezogenen Tagesmitteln bestimmt (Bootstrap).
- Die Zeit für die fehlenden Blöcke folgt dann einer Gamma-Verteilung, also der Summe exponentieller Abstände.

Die Breite des Bands kommt fast ganz aus dem Zufall der Abstände selbst. Die Schwankung des Tempos trägt wenig bei. Die Zakura-Schätzung liegt im Band, 1,5 h vor unserem Median.

## 4. Was gebaut ist

Alles auf `zcash/mainnet` (PR kaspa-pulse#133), Daten auf `messung/zcash-mainnet`.

- `scripts/zcash/zcash_koepfe.py`: Der Header-Client aus der Testnet-Zählung, jetzt mit `--netz testnet|mainnet`.
- `scripts/zcash/mainnet_auswertung.py`:
  - Kennzahlen gegen 75 s, Werte je Woche und die Vorhersage mit Band
  - ab NU7 die Kennzahlen gegen 25 s: Median gegen 17,3 s, Anteil über 75 s gegen 5,0 %, über 173 s gegen 0,1 %, p90, p99, längste Lücke
  - ab NU7 das Einpendeln: ab welchem Block das gleitende Mittel über 100 Abstände dauerhaft in 25 s ± 20 % liegt, und die Schwierigkeit relativ zu den 1.000 Blöcken vor NU7
  - ab NU7 eine CSV im Format der Testnet-CSV. Mit den Testnet-Köpfen erzeugt sie die auf pulsehawk.io veröffentlichte Testnet-CSV byte-gleich.
- `.github/workflows/zcash-mainnet.yml`:
  - läuft täglich um 05:23 UTC, sobald die Datei auf main liegt, und von Hand mit `stand=true`
  - täglich wird `aktuell.json` überschrieben
  - ein datierter Stand entsteht mittwochs, von Hand und einmal als Kurznotiz, sobald 100 NU7-Blöcke da sind
  - Roh-Header kommen nie nach main
- `.github/workflows/ph-entwurf-zcash-mainnet.yml`:
  - nach jedem neuen Stand ein Entwurf nach #ph-entwuerfe
  - gleiches Skript und gleiches Secret wie der BCH-Entwurf, nur ein eigener Auslöser
- `scripts/ph/ph_entwurf.py`:
  - neuer Modus `zcash-mainnet`. Vor NU7 enthält der Entwurf eine Zeile mit der Vorhersage, ab NU7 eine Zeile zum Einpendeln.
  - Werte aus der Zielzeit heißen jetzt "computed", die Regelprüfung bricht bei "expected" ab
  - der Zeitverlauf ist für lange Fenster lesbar (34 Tage)
  - dieselbe Datei geht mit PR pulsehawk-site#35 ins andere Repo

Erster Entwurf, in #ph-entwuerfe, Layout Verlauf. Er wurde zweimal geschickt: zuerst mit überlappenden Datumsangaben, dann mit der korrigierten Grafik. Bitte den ersten ignorieren.

```
zcash mainnet ahead of nu7 with 75 s blocks.
we counted a median block interval of 53.0 s over 38,124 blocks, against 52.0 s computed for an ideal 75 s chain.
the longest gap was 16 min, before block 3,524,451 on 20 oct at 14:01 utc.
at the pace of the last 14 days block 3,543,405 arrives around 6 nov 2026, 02:21 utc, in a 90 % band from 5 nov 2026, 22:02 to 6 nov 2026, 06:40.
window 20 sep 2026, 07:01 to 23 oct 2026, 12:49 utc, blocks 3,489,718 to 3,527,841.
method on pulsehawk.io
```

Die Zahlen für den X-Post am Sa 24.10. stimmen mit unserer Rechnung für die ideale 25-s-Kette überein:

- Median 25 · ln 2 = 17,3 s
- Anteil über 75 s e⁻³ = 4,98 %
- 1 von 1.000 Abständen über 25 · ln 1000 = 173 s

## 5. Geplante Folgeläufe

| Termin (UTC) | Was |
|---|---|
| Mi 28.10. 15:00 | Prüfung, ob der Mittwochsstand da ist, sonst anstoßen. Tabelle an Ben, Bericht. |
| Mi 04.11. 15:00 | Dasselbe, letzter Stand vor der Aktivierung |
| Fr 06.11. 09:00 | Kurznotiz nach der Aktivierung, notfalls alle 2 h neu prüfen |
| Mi 11.11. 15:00 | Stand und CSV, Woche 1 nach NU7 |
| Mi 18.11. 15:00 | Stand und CSV, Woche 2 nach NU7 |

## 6. Offene Fragen an Ben

1. **CSV ab NU7:** Wo soll sie veröffentlicht werden? Mein Vorschlag ist pulsehawk-site unter `data/zcash-mainnet/`, nicht unter `data/zcash-nu7/`. Dort würde `ph-entwurf-zcash.yml` sonst einen zweiten Entwurf mit Testnet-Text schicken. Die Entwürfe zum Mainnet kommen schon aus kaspa-pulse.
2. **Zakura in der Gegenprobe:** Zakura-Peers antworten nicht auf `getheaders`. Reicht dir die Gegenprobe mit zwei Zebra-Peers, oder soll ich nach der Aktivierung einen Zuhörer wie im Testnet am 17.10. mitlaufen lassen? Der sieht Zakura-Ankündigungen ohne `getheaders`.
3. **Eigener Entwurfs-Workflow:** Die Mainnet-Entwürfe laufen über eine eigene Workflow-Datei mit gleichem Skript und gleichem Secret, nicht über `ph-entwurf-bch.yml`. Passt das?

## 7. Was Ben tun muss

- **kaspa-pulse#133 prüfen und mergen, möglichst vor Mi 28.10.** Erst dann laufen der tägliche Lauf und `workflow_dispatch`. Ohne Merge stoße ich den Mittwochsstand über einen Push auf den PR-Branch an.
- **pulsehawk-site#35 prüfen und mergen:** Damit ist `ph_entwurf.py` in beiden Repos gleich. Der PR schickt nichts nach Discord.
- **Den ersten Mainnet-Entwurf in #ph-entwuerfe ignorieren.** Der zweite hat die richtige Grafik.

Der Secret-Scan hat in `zcash/mainnet`, `messung/zcash-mainnet` und `ph/computed` keine Schlüssel und keine Tokens gefunden. Peer-Adressen und Hostnamen stehen in keiner Datei und keinem Log.
