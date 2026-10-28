# BCH Tempnet 2027, Woche 2, Bericht 28.10.2026

Auftrag (Ben, 21.10. und 25.10.2026): Wochenlauf am Mittwoch 10:00 UTC, dazu Woche 2 mit dem Mitschnitt vom eigenen Netzwerkpfad (inv, headers, cmpctblock, Stale-Blöcke) und dem Vergleich mit rufitnes/tempnet-data.

## Was gemacht ist

- **Wochenlauf:** Stichtag 2026-10-28T10:00:00Z auf `messung/bch-tempnet` gesetzt (`727387d`).
  - Lauf [40669667890](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40669667890) war grün, der Bot-Commit ist `da72b3e`.
  - Der Stand liegt in `data/bch/tempnet-2026-10-28.json` und `docs/bch-tempnet-2026-10-28.md`. Zwischenstand-Dateien gab es keine.
- **PH-Entwurf:** `ph-entwurf-bch.yml` lief grün ([40669948358](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40669948358)) und hat den Entwurf an #ph-entwuerfe geschickt (HTTP 200).
- **Auswertung des Zuhörers:** über alle 14 Läufe, mit der frischen Kette aus dem Wochenlauf. Die Daten liegen auf `messung/bch-tempnet` (`3d64ddc`), nicht auf main:
  - [`data/bch/tempnet-woche2-bloecke-2026-10-28.csv`](https://github.com/neoalphavault-png/kaspa-pulse/blob/messung/bch-tempnet/data/bch/tempnet-woche2-bloecke-2026-10-28.csv): eine Zeile je Block, 4.207 Blöcke
  - [`data/bch/tempnet-woche2-zusammenfassung-2026-10-28.json`](https://github.com/neoalphavault-png/kaspa-pulse/blob/messung/bch-tempnet/data/bch/tempnet-woche2-zusammenfassung-2026-10-28.json)
  - [`data/bch/tempnet-woche2-vergleich-rufitnes-2026-10-28.json`](https://github.com/neoalphavault-png/kaspa-pulse/blob/messung/bch-tempnet/data/bch/tempnet-woche2-vergleich-rufitnes-2026-10-28.json)
- **PR:** [kaspa-pulse#142](https://github.com/neoalphavault-png/kaspa-pulse/pull/142) ist am 26.10. gemergt. Deshalb ist der Branch `messung/bch-tempnet-woche2` frisch von main angelegt, mit neuem PR nur für diesen Bericht und den Forum-Entwurf.

## Methode

Ein Zuhörer ohne eigenen Knoten hält Verbindungen nur zu Tempnet-Peers, die den Abzweig 327.989 bestätigen, und schreibt jede Block-Ankündigung mit Nachrichtentyp (inv, headers, cmpctblock), Peer-Label `peer_N` und Millisekunden mit. Danach legen wir die Ankündigungen über den Hash auf die eigene, per P2P geholte und auf Verkettung und PoW geprüfte Kette und zählen je Block die erste Ankündigung, den Abstand zum Header-Zeitstempel und die Streuung über die Peers. Für jeden Block holen wir beim ersten Ankündiger einen cmpctblock und schätzen die fehlenden TX über die BIP152-Kurz-IDs gegen die bei uns per inv angekündigten TX.

## Zuhörer: Läufe und Lücken

14 Läufe von 25.10. 09:15:47 bis 28.10. 07:36:11 UTC, zusammen 71,7 h. Zwei Lücken zwischen Läufen (aus `data/bch/lauscher/*/meta.json`, start und ende):

| von (UTC) | bis (UTC) | Dauer | Grund |
|---|---|---:|---|
| 25.10. 09:27:47 | 25.10. 09:34:44 | 6 min 57 s | Testlauf zu Ende, Dauerlauf von Hand gestartet |
| 26.10. 12:37:49 | 26.10. 12:39:24 | 1 min 35 s | Anstoß von Hand kam zu spät (vor dem Merge von #142) |

- Alle übrigen Wechsel überlappen um 5,7 bis 16,5 min.
- Seit Lauf 9 (26.10. 23:15 UTC) reicht sich die Kette auf main selbst weiter.
- Lauf 15 läuft seit 28.10. 07:28 UTC. Seine Daten kommen erst mit dem Laufende gegen 12:58 UTC auf den Datenbranch. Der Zeitraum 07:36 bis 10:00 UTC fehlt deshalb noch in der Auswertung.
- Vor dem Start am 25.10. 09:15 UTC gibt es keinen Mitschnitt. Die Woche ab 21.10. 10:00 ist für den Zuhörer also nur zu gut 3 Tagen abgedeckt.
- Je Lauf sind 31 bis 47 Peers mit bestätigtem Abzweig verbunden. Abgelehnt werden je Lauf 90 bis 101 Peers, weil sie den Abzweig nicht bestätigen.

## Wochenzahlen aus den Köpfen

Blockabstände gegen eine ideale 60-s-Kette. Die Spalte "nur Woche" umfasst die Abstände mit Blockzeit von 21.10. 10:00 bis 28.10. 10:00 UTC, also 10.053 Abstände (Blöcke 335.561 bis 345.613). "Gesamt" ist der Stand des Wochenlaufs ab 327.989, wie am 21.10.

| Kennzahl | nur Woche (counted) | gesamt 28.10. (counted) | gesamt 21.10. (counted) | berechnet für 60 s |
|---|---:|---:|---:|---:|
| Abstände | 10.053 | 17.624 | 7.571 | |
| Mittel | 60,16 s | 63,13 s | 67,07 s | 60 s |
| Median | 45,0 s | 44,0 s | 43,0 s | 41,6 s |
| p90 | 132,0 s | 128,0 s | 125,0 s | 138,2 s |
| p99 | 212,5 s | 216,0 s | 232,0 s | 276,3 s |
| Anteil über 5 min | 0,02 % (2) | 0,18 % (31) | 0,38 % (29) | 0,67 % |
| Längste Lücke | 334 s, vor 335.881 am 21.10. 15:45:56 UTC | 20.863 s, Höhe 328.223 (16.10.) | dieselbe | ≈ 588 s (Woche), ≈ 621 s (gesamt) |
| Abstand 0 | 49 | 56 | 7 | |
| Zeitstempel minus MTP davor, Median / p90 / p99 | 355 / 518 / 658 s | 348 / 520 / 695 s | 335 / 524 / 765 s | 340 / 557 / 786 s |
| dto. kleinster Wert | 57 s | 49 s | 49 s | Konsens verlangt mehr als 0 |
| Abrufzeit minus MTP der Spitze | | 255 s | 530 s | Median 340 s, p90 556 s |
| Abrufzeit minus Zeitstempel der Spitze | | 22 s | 137 s | Median 42 s, p90 138 s |
| 10 Blöcke, Median / p90 / p99 | | 585 / 808 / 1.051 s | 568 / 823 / 1.229 s | 10 × 60 s: 580 / 852 / 1.127 s; 1 × 600 s: 416 / 1.382 / 2.763 s |
| Blöcke mit Mindestschwierigkeit | 1.364 | 4.819 von 17.625 | 3.455 von 7.572 | |

Die berechneten Werte kommen aus der Exponentialverteilung bei 60 s. Für die 10er-Fenster gilt Erlang, für die MTP-Werte die Simulation mit 200.000 Ziehungen.

**Beobachtung zur Woche:** Mittel und Median liegen nah an 60 s, das Ende der Verteilung ist aber deutlich kürzer als berechnet. Nur 2 Abstände liegen über 5 min statt der berechneten 0,67 %, p99 liegt bei 212 s statt 276 s. In derselben Woche tragen 1.364 Blöcke Mindestschwierigkeit. Die Regel dahinter prüfen wir nicht.

**Prüfung des Wochenlaufs**
- **Zielhöhe:** 345.620, nur aus 4 Peers mit bestätigtem Abzweig. 8 Proben ohne Abzweig zählten nicht mit.
- **Spitze:** 345.623 beim Abruf am 28.10. um 10:09:45 UTC.
- **Gegenprobe:** /Vcash:0.1/ und /Bitcoin Cash Node:29.2.1(tempnet-20261015)/, je 500 von 500 Hashes gleich. Es wurden keine Abzweige verworfen.
- **chaingraph:** wieder HTTP 403. Nicht umgangen.
- **Datenschutz:** In `data/bch`, `docs` und im Job-Log stehen keine IPs und keine Hostnamen. Der Secret-Scan ist sauber.

## Neue Größen aus dem Zuhörer

Blöcke 341.252 bis 345.470, Header-Zeit 25.10. 09:16:30 bis 28.10. 07:36:03 UTC. Alle 4.207 Kettenblöcke im Fenster haben wir angekündigt gesehen, im Median von 22 Peers (p90 39, höchstens 51).

**first_seen je Typ** (welche Nachricht zuerst kam)

| Typ | Blöcke |
|---|---:|
| inv | 4.205 |
| headers | 2 |
| cmpctblock | 0 |

**timestamp_deviation** (first_seen minus Header-Zeitstempel), 4.207 Blöcke:
- Median 0,78 s, Mittel 2,06 s, p90 3,40 s, p99 31,1 s.
- Kleinster Wert 0,08 s, größter 196,0 s. Kein Block kam bei uns vor seinem Zeitstempel an.
- 41 der 42 Blöcke über p99 tragen einen Header-Zeitstempel genau 120 s nach dem Vorgänger, keiner davon trägt Mindestschwierigkeit. Im Fenster haben 107 Blöcke einen Abstand von genau 120 s.
- Der Zeitstempel ist hier offenbar nicht die Zeit des Funds. Das ist eine Beobachtung aus den Köpfen, keine Deutung.

**propagation_spread** (letzte minus erste Ankündigung über die Peers, nur Blöcke mit mindestens zwei Peers), 4.200 Blöcke:
- Median 7,6 s, p90 10,8 s, p99 16,7 s, größter Wert 252,9 s.
- Das ist die Streuung an unserem einen Zuhörer über 20 bis 50 Verbindungen. Es ist keine Ausbreitungszeit im Netz.

**Stale-Blöcke** (angekündigt, aber 6 Blöcke später nicht in der Kette): 16, das sind 0,38 % von 4.223 angekündigten Blöcken. Kein Fall ist offen unter 6 Bestätigungen, und jeder hat einen Kopf.

| Höhe | Hash | Header-Zeit UTC | first_seen UTC | Peers |
|---|---|---|---|---:|
| 341.286 | 000000002337390b548d8a3cd3ae0780b4f75c05a52d40e1f2755b26f473e326 | 25.10. 09:50:33 | 09:50:36,002 | 2 |
| 341.300 | 000000005b8613bd5b6d0fbc1069ec441fc7e9e440fd15dc1bacafe5892efccc | 25.10. 09:58:35 | 09:58:38,086 | 2 |
| 341.321 | 0000000047685e219871a10692e3fb5869d66509677f741257f07e80fe1b791f | 25.10. 10:20:02 | 10:20:02,637 | 1 |
| 342.114 | 00000000850e0daa8861651cc0f983ce56c7e2cf774e00976ecd60fc412da69b | 25.10. 23:44:19 | 23:44:20,029 | 5 |
| 342.389 | 000000005d86178fa783984b758c3b64dbb097eb9a68e7c14af5c449cb2f167d | 26.10. 04:15:38 | 04:15:41,927 | 15 |
| 342.614 | 000000004b2a70758ada9a4c991c327d54d5f23c9911366668669d5951143a03 | 26.10. 07:47:05 | 07:47:07,100 | 8 |
| 342.742 | 000000005e3cd08d5611b6aba0cf583f06e3a36461674093e1eb147db948a73b | 26.10. 10:03:26 | 10:03:26,741 | 5 |
| 342.853 | 000000004050ac63cc48d25c10cac1c29de82ae8407dad52852ef4dc10d93305 | 26.10. 11:59:08 | 11:59:10,472 | 23 |
| 343.235 | 0000000040e817e29e53f1bac8af6f108835d053a72bc9f548e0aed1af17420d | 26.10. 18:23:55 | 18:23:55,252 | 7 |
| 343.460 | 0000000095bdaf46473050ca83604b350ed1be19dbac5f4387e86cb9911eb3cf | 26.10. 22:08:25 | 22:08:28,819 | 27 |
| 343.694 | 000000001528521a5cc514bbf7cd7c97bdb5462a7ba6a31b28dfc75afdd9553e | 27.10. 01:48:54 | 01:48:54,569 | 20 |
| 344.444 | 0000000071e1554decf3d9f52706fb918ea7c0476cbf15a52aa2e9322e9336f8 | 27.10. 14:30:18 | 14:30:18,216 | 24 |
| 344.473 | 000000005794037f020b418c81079f7bcc3b9703f3e1686a318c1d4baf0459ce | 27.10. 15:06:08 | 15:06:08,314 | 25 |
| 345.229 | 000000007865433dced5c20c3995fa04737dcd044c7608200fe79f4453e0112b | 28.10. 03:37:16 | 03:37:19,044 | 12 |
| 345.431 | 00000000fdca79ad4a1bc5a7214fb5ca032c9277a9afc657a2af56083e91223a | 28.10. 06:59:40 | 06:59:43,810 | 28 |
| 345.466 | 000000009f9b028264967854e99e0da21dc2fa32d673e48142f59c6a988e25c4 | 28.10. 07:34:04 | 07:34:07,231 | 22 |

Alle 16 kamen zuerst per inv. Die Spalte Peers zählt, wie viele unserer Verbindungen den Block angekündigt haben.

**Compact-Weg**
- **cmpctblock bekommen:** für 4.204 von 4.207 Blöcken, alle auf unsere Anfrage. Von selbst kam keiner.
- **Kurz-IDs je Block:** Median 5, p90 25, höchstens 78.
- **Geschätzt fehlende TX:** Median 0, p99 1, höchstens 10. In 4.137 Blöcken fehlte keine, in 67 Blöcken zusammen 83.
- **Warum nur eine Schätzung:** Wir haben keinen Mempool. Wir zählen, wie viele Kurz-IDs zu keiner Transaktion passen, die uns ein Peer per inv angekündigt hat. Ein echter Knoten kennt auch TX, die er selbst geprüft oder abgelehnt hat, und kann TX kennen, deren inv wir nie bekommen haben. Die Zahl ist deshalb eine Näherung an das, was ein Knoten nachfordern müsste.
- **Warum cmpctblock als Ankündigung praktisch nicht vorkommt:** Nach BIP152 schickt ein Knoten neue Blöcke nur an höchstens drei Peers sofort als cmpctblock, die er selbst als High-Bandwidth-Peers wählt (`sendcmpct` mit Modus 1). Er wählt dafür Peers, die ihm zuletzt Blöcke als Erste geliefert haben. Ein Zuhörer, der selbst nie Blöcke weitergibt, wird nie gewählt. Alle anderen Peers kündigen per inv oder headers an, den cmpctblock gibt es nur auf Anfrage.

## Vergleich mit rufitnes/tempnet-data

Stand-Commit `787f5613593493ba0933360303a5b3d18465211a` (Snapshot 345.617, 28.10. 10:04:31 UTC). Gelesen wurden nur `data/events.csv` und `data/compact.csv` als Daten, kein Code daraus ausgeführt. Join über den Hash: Alle 4.207 Blöcke stehen in beiden Datensätzen.

| Größe | counted | source rufitnes/tempnet-data |
|---|---:|---:|
| timestamp_deviation, Median | 0,78 s | 1 s |
| dto. p90 / p99 | 3,4 / 31,1 s | 4 / 33 s |
| dto. größter Wert | 196,0 s | 196 s |
| Blöcke über cmpctblock | 4.204 (auf Anfrage) | 4.189 (via compact) |
| fehlende TX, Median / p99 / größter (4.187 Blöcke in beiden) | 0 / 1 / 10 (geschätzt) | 0 / 1 / 10 (requested) |
| Reorg-Ereignisse bzw. Stale-Blöcke | 16 Stale-Blöcke | 0 Reorg-Ereignisse |

- **Zeiten:** Unsere erste Ankündigung minus seine Empfangszeit beträgt im Median minus 0,01 s, p90 0,03 s. Er misst in ganzen Sekunden über die Lesezeit der Logzeile, wir in Millisekunden. Beide Uhren sind nicht gegeneinander abgeglichen.
- **Fehlende TX:** Unsere Schätzung ohne Mempool trifft in der Verteilung seine nachgeforderten TX.
- **Stale gegen Reorg:** Kein Widerspruch. Ein Knoten meldet nur dann einen Reorg, wenn er seine Spitze schon auf den später verdrängten Block gesetzt hatte. Kommt der Konkurrenzblock zuerst an, bleibt der Knoten auf seiner Spitze und loggt keinen Reorg. Wir zählen jeden angekündigten Block, der nicht in die Kette kam.

## Offene Fragen an Ben

1. Lauf 15 deckt 07:36 bis 10:00 UTC ab. Seine Daten kommen gegen 12:58 UTC. Soll ich die Wochen-CSV dann einmal nachziehen, oder bleibt der Stand 07:36 UTC und die Stunden gehen in Woche 3?
2. Die 120-s-Zeitstempel (41 von 42 Blöcken über p99) sind im Forum-Entwurf als reine Beobachtung genannt. Passt das so, oder lieber weglassen?
3. Die Software der Peers nenne ich im Forum nicht, weil Kennungen wie `my-tempnet-node` auf einzelne Betreiber zeigen können. Einverstanden?

## Was Ben tun muss

- **Forum-Entwurf prüfen und selbst posten:** `berichte/2026-10-28-bch-tempnet-woche2-forum.md`. Ich poste nichts.
- **Für den neuen PR nichts:** Er enthält nur diese beiden Berichtsdateien, keine Workflows und keine Rohdaten. Ich merge ihn selbst, sobald die Checks grün sind und der Forum-Text die Regelprüfung besteht. Danach folgt die Zeile zum Merge unten.
- **Sonst nichts.** Die Zuhörer-Kette läuft auf main selbst weiter bis 15.11. 12:00 UTC.

Der Secret-Scan ist sauber, in den Branches `messung/bch-tempnet` und `messung/bch-tempnet-woche2` stehen weder Schlüssel noch Tokens. Peer-Adressen und Hostnamen stehen in keiner Datei und keinem Log.
