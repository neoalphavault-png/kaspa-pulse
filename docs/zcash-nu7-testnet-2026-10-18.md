# Zcash NU7 Testnet: unabhängige Zählung, Stand 2026-10-18

**Stichtag:** 2026-10-18 06:00:00 UTC · **Blockbereich:** 4.465.026 bis 4.514.228 (49.203 Blöcke, 2026-10-04 18:21:45 bis 2026-10-18 05:59:48 UTC) · **Abruf:** 2026-10-18T06:13:38Z

Nur Zahlen. Kein Kurs, keine Bewertung.

## Methode und Quelle

- Blockköpfe direkt aus dem P2P-Netz des Zcash-Testnets (`getheaders`), Peers über die DNS-Seeds, kein Explorer, keine API, kein Konto. Skript: `scripts/zcash/testnet_koepfe.py`.
- Startpunkt: Checkpoint 4.414.585 aus Zebras `test-checkpoints.txt`. Geprüft: Verkettung über den Vorgänger-Hash, Hash ≤ Ziel aus nBits, 0 spätere Checkpoints. Die Equihash-Lösung prüfen wir nicht.
- Gegenprobe mit weiteren Peers: /Zebra:7.0.0-rc.0/: 500/500 Hashes gleich, /Zebra:7.0.0-rc.0/: 500/500 Hashes gleich
- Gegenprobe ohne verwertbare Antwort: /Zakura:1.6.0/: 2 Versuche, /Zakura:1.7.0-rc1/: 1 Versuche. Handschlag jeweils erfolgreich, auf `getheaders` kam innerhalb von 20 s keine Antwort. Das kann auch an unserem Client liegen; wir haben es nicht weiter eingegrenzt.
- Software der Peers: /Zebra:7.0.0-rc.0/, /Zakura:1.6.0/, /Zakura:1.7.0-rc1/
- Abstand = Zeitstempel minus Zeitstempel des Vorgängers, erster Abstand bei 4.465.027. Zeitstempel setzt der Miner; null und negative Abstände bleiben drin.
- Schwierigkeit wie in der RPC: Ziel(powLimit 0x2007ffff) / Ziel(nBits). Tage in UTC.
- Auswertung: `scripts/zcash/nu7_auswertung.py`, Rohdaten: `data/zcash/testnet-koepfe.csv.gz`.

## A. Abstände zwischen Blöcken

|  | gemessen | Erwartung exponentiell, 25 s |
| --- | --- | --- |
| Abstände | 49.202 |  |
| Mittel | 23,68 s | 25,0 s |
| Median | 17,0 s | 17,3 s |
| p90 | 52,0 s | 57,6 s |
| p99 | 109,0 s | 115,1 s |
| längste Lücke | 451 s (Höhe 4.495.487) | ≈ 284 s (Erwartungswert des Maximums) |
| über 75 s | 3,59 % (1.767) | 4,98 % |
| über 150 s | 0,203 % (100) | 0,248 % |
| Abstand 0 s / negativ | 531 / 0 |  |

Vor der Aktivierung (50.439 Abstände, Höhe 4.414.586 bis 4.465.025): Mittel 9,0 s, Median 2,0 s, 517 Blöcke mit Mindestschwierigkeit. Das Testnet lief dort weit schneller als das 75-s-Ziel; als Vergleich für das alte Ziel taugt dieser Abschnitt nicht.

**Blöcke mit Mindestschwierigkeit seit der Aktivierung:** 1, kleinste Lücke davor 451 s; größte Lücke ohne Mindestschwierigkeit 434 s; Lücken über 150 s (6 × 25 s) insgesamt: 100.

## B. Je Tag (UTC)

| Tag | Blöcke | Höhen | mittl. Abstand | Schwierigkeit Mittel | min | max | Mindest-Schw. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-04 | 685 | 4.465.026–4.465.710 | 29,2 s | 1.779,0 | 1.263,7 | 2.114,3 | 0 |
| 2026-10-05 | 3.334 | 4.465.711–4.469.044 | 26,0 s | 918,0 | 604,7 | 1.334,8 | 0 |
| 2026-10-06 | 4.047 | 4.469.045–4.473.091 | 21,3 s | 7.362,2 | 611,5 | 11.878,0 | 0 |
| 2026-10-07 | 3.444 | 4.473.092–4.476.535 | 25,1 s | 11.609,4 | 10.452,9 | 13.566,8 | 0 |
| 2026-10-08 | 3.445 | 4.476.536–4.479.980 | 25,1 s | 12.614,2 | 10.598,0 | 19.457,1 | 0 |
| 2026-10-09 | 3.453 | 4.479.981–4.483.433 | 25,0 s | 11.780,3 | 9.927,2 | 16.143,1 | 0 |
| 2026-10-10 | 3.467 | 4.483.434–4.486.900 | 24,9 s | 11.502,7 | 10.554,1 | 12.604,1 | 0 |
| 2026-10-11 | 3.463 | 4.486.901–4.490.363 | 25,0 s | 12.081,6 | 10.061,7 | 21.531,1 | 0 |
| 2026-10-12 | 3.457 | 4.490.364–4.493.820 | 25,0 s | 11.346,0 | 10.273,6 | 12.431,2 | 0 |
| 2026-10-13 | 5.714 | 4.493.821–4.499.534 | 15,1 s | 50.070,8 | 1,0 | 720.736,5 | 1 |
| 2026-10-14 | 3.485 | 4.499.535–4.503.019 | 24,8 s | 10.655,9 | 9.020,4 | 12.573,0 | 0 |
| 2026-10-15 | 3.447 | 4.503.020–4.506.466 | 25,1 s | 11.461,4 | 10.201,2 | 12.756,3 | 0 |
| 2026-10-16 | 3.459 | 4.506.467–4.509.925 | 25,0 s | 11.395,7 | 10.329,8 | 12.745,4 | 0 |
| 2026-10-17 | 3.442 | 4.509.926–4.513.367 | 25,1 s | 11.590,0 | 10.255,9 | 12.739,8 | 0 |
| 2026-10-18 | 861 | 4.513.368–4.514.228 | 25,1 s | 11.247,7 | 10.472,8 | 12.318,5 | 0 |

Erster und letzter Tag sind angeschnitten (Aktivierung 18:21:45 UTC, Stichtag).

**Wie schnell folgt die Schwierigkeit?** Fenster 100 Bloecke, Sprung ab Faktor 2.0 (vom folgenden Fenster bestaetigt); eingeholt, wenn die Schwierigkeit innerhalb +-15 % der Hashrate der folgenden 100 Bloecke mal 25 s liegt. Sprünge: 6; eingeholt im Median nach 960 Blöcken bzw. 159,7 min, längstens 1.839 Blöcke; vom nächsten Sprung abgelöst, bevor eingeholt: 1; nicht eingeholt in 2.000 Blöcken: 0.

| Höhe | Zeit UTC | Faktor Hashrate | Schwierigkeit an der Grenze | eingeholt nach Blöcken | min | Schwierigkeit dann |
| --- | --- | --- | --- | --- | --- | --- |
| 4.469.626 | 2026-10-06 04:00:07 | 2,45 | 625,0 | 960 | 182,2 | 8.116,7 |
| 4.480.926 | 2026-10-09 06:01:32 | 0,28 | 15.396,4 | 169 | 96,2 | 12.549,9 |
| 4.488.026 | 2026-10-11 07:51:35 | 5,27 | 11.592,7 | abgelöst | – | – |
| 4.488.226 | 2026-10-11 08:11:57 | 0,17 | 20.911,8 | 249 | 159,7 | 12.032,7 |
| 4.494.176 | 2026-10-13 02:28:02 | 9,20 | 12.008,4 | 1.239 | 91,1 | 628.067,2 |
| 4.495.476 | 2026-10-13 04:15:27 | 0,23 | 717.246,1 | 1.839 | 257,9 | 10.138,5 |

## C. Zeitstempel

- Rückwärts (Zeitstempel kleiner als der des Vorgängers): **0**, größter Schritt 0 s.
- Auffällig weit voraus (Zeitstempel mehr als 600 s nach dem Median der 11 folgenden Bloecke): **0**.
- Zeitstempel nach unserer Abrufzeit: 0. Verstöße gegen die Median-Regel der 11 Vorgänger: 0 (Konsensregel, Gegenprobe).

## D. Ersatzmessung: ein Zuhörer, kein eigener Knoten

**Ein Zuhörer** an einem Ort (GitHub-Runner). Tatsächliches Zeitfenster: 17.10.2026 14:51 bis 20:21 UTC (Ankündigungen von 14:51 bis 20:21 UTC, 329,8 min). Er hielt Verbindungen zu Testnet-Knoten und schrieb jede Block-Ankündigung mit Ankunftszeit mit. Er sieht nur, was ihm angekündigt wird; die Ankunftszeit enthält den Weg vom Knoten zu ihm. Das ersetzt keinen eigenen Knoten und gilt nur für dieses Fenster, nicht seit der Aktivierung. Skripte: `scripts/zcash/testnet_lauscher.py`, `scripts/zcash/lauscher_auswertung.py`.

- Verbindungen je Software: zakura: 55, zebra: 8; Ankündigungen je Software: zakura: 3.659, zebra: 2.025. Software: /Zakura:1.6.0/, /Zakura:1.7.0-rc0/, /Zakura:1.7.0-rc1/, /Zebra:7.0.0-rc.0/
- Kettenblöcke mit Zeitstempel im Fenster: 776, davon angekündigt gesehen: 775
- **Abgehängte Blöcke** (angekündigt, aber nicht in der später abgerufenen Kette): **5**, in 5 Zweigen; größte Zweigtiefe 1
- **Ankunft Zakura minus Zebra** (erste Ankündigung je Software, 730 Blöcke): Median 36,0 ms, p10 -2.871,1 ms, p90 417,6 ms; Zakura zuerst bei 299 Blöcken
- Streuung über alle Peers (letzte minus erste Ankündigung, 773 Blöcke): Median 6.910,0 ms, p90 15.920,0 ms, max 79.908 ms
- Erste Ankunft minus Zeitstempel des Blocks: Median 16,4 s, p90 53,1 s (Zeitstempel setzt der Miner)

Beobachtung mit Vorbehalt: 4 der 5 abgehängten Blöcke hat nur ein Zakura-Peer angekündigt. Das ist ein Zuhörer an einem Ort mit 5 Blöcken; daraus folgt kein Schluss auf einen Client. Zakura-Verbindungen wechselten öfter als Zebra-Verbindungen, das kann die Zahl mitbestimmen. Für den nächsten Lauf vorgemerkt: ein zweiter Zuhörer an einem anderen Ort.

| Höhe | erste Ankündigung UTC | angekündigt von | Peers |
| --- | --- | --- | --- |
| 4.512.089 | 2026-10-17 14:59:22 | zakura | 3 |
| 4.512.307 | 2026-10-17 16:32:09 | zakura | 1 |
| 4.512.513 | 2026-10-17 18:06:03 | zakura, zebra | 6 |
| 4.512.703 | 2026-10-17 19:21:47 | zakura | 1 |
| 4.512.758 | 2026-10-17 19:45:32 | zakura | 2 |

## Was wir nicht messen konnten

- **Verwaiste Blöcke und Reorg-Tiefe seit der Aktivierung:** nur im Fenster des Zuhörers, siehe D.
- **Equihash-Lösungen und Blockinhalt:** nicht geprüft, nur Kopf, Verkettung, Arbeitsnachweis gegen nBits und Checkpoints.
- **Echte Hashrate:** nur relativ über Schwierigkeit und Abstände; Zeitstempel kommen vom Miner.
