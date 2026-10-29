# STP-Lauf Do 29.10.2026, Auswertung

Bericht für Ben zum Auftrag vom 29.10.2026, Frist Fr 30.10. 18:00 Berlin. Lauf auf Testnet-10, 19:00 bis 20:00 UTC, gezählte Minuten 19:03 bis 19:14, 19:23 bis 19:34 und 19:43 bis 19:59 UTC. Zahlen aus unseren zwei Knoten heißen counted, Zahlen aus STPs Logs heißen source STP.

## Ergebnis in drei Sätzen

Unsere Nachzählung auf zwei Knoten bestätigt STPs Kernaussage: Mit mehr Covenant-Familien steigt die Zahl der angenommenen Covenant-Ausgaben fast im gleichen Verhältnis. Gezählt sind es 0.81 je Sekunde mit einer Familie, 1.98 mit zwei und 3.27 mit vier. STP kommt auf 0.81, 1.95 und 3.24. Je Familie bleibt es bei etwa 0.8 bis 1.0 je Sekunde. Gültig nach unserer Regel sind aber nur 8 der 41 gezählten Minuten. In allen anderen liefen weniger Sender als geplant, deshalb sagt der Lauf nichts über Grenzen der Knoten oder über Contention unter voller Last.

## Was gezählt wurde

- **Nachzählung mit Covenant:** [Lauf 40970671061](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40970671061) auf `messung/tn10-zaehler`, Commit 58b5212. Sechs Stücke zu 20 Minuten von 18:30 bis 20:30 UTC, je zwei verschiedene öffentliche Knoten, Blöcke und Kette. Alle 120 Minuten sind auf beiden Knoten vollständig, und beide Knoten stimmen in allen 120 Minuten überein, auch in jeder Covenant-Spalte.
- **Covenant-IDs:** Ben hat sie am 29.10. nach dem Lauf weitergegeben. Im Repo steht je Familie nur der sha256 (`messung/tn10/nach/covenant.sha256`, geschrieben mit `scripts/tn10_contention.py --hash`). Alle vier Hashes sind gleich wie in STPs Datei `covenant-id-sha256.csv`.
- **Nachträglich zuordnen ging nicht:** Die erste Nachzählung (5cac0fe) lief ohne Hash-Datei. Dann speichert das Skript keine Covenant-Daten, nur Summen je Minute. Deshalb liefen die sechs Stücke mit den Hashes ein zweites Mal. Der Pruning-Punkt der Knoten lag dabei bei 28.10. 14:56 UTC, das Fenster war also noch ganz lesbar.
- **Gesamtverkehr 18:30 bis 20:30 UTC:** 403,826 angenommene Tx und 70,438 Blöcke (counted, beide Knoten gleich). Der Live-Zähler hatte 403,828, der Unterschied von 2 Tx liegt in zwei Minuten, in denen live nur ein Knoten sicher war.
- **STPs Logs:** nur `logs/storm-2026-10-29` aus STPs Repo, nur lesend, Stand fff69ac. Eine `REVIEW.md` im Hauptordner des Repos gibt es nicht, die Review liegt in diesem Logordner und ist mitgelesen. Nichts davon wurde ausgeführt, kein anderer Link geöffnet.
- **Parser:** `scripts/tn10_contention.py --lauf messung/tn10/lauf-2026-10-29.txt` mit STPs Logs und der Nachzählung. STP hat `phase.log`, `ntp.csv` und `post-end-mempool.csv` je Maschine geliefert (`phase-mini.log` und so weiter). Der Parser liest jetzt beide Formen (Commit 8aa4102, Selbsttest ohne Fehler).

Die Ergebnisdateien der Nachzählung tragen Tx-IDs und lassen sich von meiner Umgebung aus nicht laden. Deshalb gibt es auf `messung/tn10-zaehler` einen kleinen Workflow `tn10-auswertung.yml` (657a733), der nur die Spalten mit reinen Zahlen ins Log schreibt ([Lauf 40974624108](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40974624108)). Er bleibt auf dem Messbranch und wird nicht gemergt.

## Je Schritt

| Schritt | gezählte Minuten | Familien | angenommen je s, counted | je Familie, counted | Hops je s, source STP | nie angenommen, counted |
|---|---|---|---|---|---|---|
| 1 | 19:03 bis 19:14, 12 | 1 | 0.806 | f1 0.806 | 0.806 | 0 |
| 2 | 19:23 bis 19:34, 12 | 2 | 1.983 | f1 0.989, f2 0.994 | 1.950 | 171, also 12.0 % der angenommenen |
| 3 | 19:43 bis 19:59, 17 | 4 | 3.275 | f1 0.814, f2 0.825, f3 0.823, f4 0.813 | 3.242 | 214, also 6.4 % |
| nur gültige Minuten | 19:25 bis 19:32, 8 | 2 | 2.054 | f1 1.019, f2 1.035 | 2.021 | 131 |

- **angenommen:** Ausgaben eines Covenants, die die Kette angenommen hat, zur Blockzeit des annehmenden Kettenblocks. Eine Tx zählt zu einer Familie, wenn ein Ausgang an deren Covenant-ID gebunden ist oder ein Eingang einen solchen Ausgang ausgibt.
- **nie angenommen:** konkurrierende Ausgaben, die in einem Block stehen, aber nie angenommen wurden. Das ist Contention, die wir selbst auf der Kette sehen.
- Gegenüber Schritt 1 ist die Rate in Schritt 2 das 2.46-fache, in Schritt 3 das 4.06-fache (counted).

## Minutentabelle

Je gezählter Minute die Summe und die Familien. Die volle Tabelle je Minute und Familie, mit STPs sent, ok und Ablehnungen, steht in `tn10/ergebnis/stp-lauf-2026-10-29-minuten.csv` (104 Zeilen, keine Tx-ID, keine Adresse, kein Hostname). Ein Punkt heißt: Familie in diesem Schritt nicht aktiv.

| Minute (UTC) | Schritt | angenommen, counted | je Familie f1 / f2 / f3 / f4, counted | nie angenommen, counted | Hops, source STP | Sekunden mit allen Sendern, source STP | gültig |
|---|---|---|---|---|---|---|---|
| 19:03 | 1 | 50 | 50 / · / · / · | 0 | 50 | 0 | nein |
| 19:04 | 1 | 45 | 45 / · / · / · | 0 | 45 | 0 | nein |
| 19:05 | 1 | 47 | 47 / · / · / · | 0 | 47 | 0 | nein |
| 19:06 | 1 | 51 | 51 / · / · / · | 0 | 51 | 0 | nein |
| 19:07 | 1 | 49 | 49 / · / · / · | 0 | 49 | 0 | nein |
| 19:08 | 1 | 51 | 51 / · / · / · | 0 | 51 | 0 | nein |
| 19:09 | 1 | 44 | 44 / · / · / · | 0 | 45 | 0 | nein |
| 19:10 | 1 | 51 | 51 / · / · / · | 0 | 50 | 0 | nein |
| 19:11 | 1 | 50 | 50 / · / · / · | 0 | 50 | 0 | nein |
| 19:12 | 1 | 47 | 47 / · / · / · | 0 | 47 | 0 | nein |
| 19:13 | 1 | 46 | 46 / · / · / · | 0 | 46 | 0 | nein |
| 19:14 | 1 | 49 | 49 / · / · / · | 0 | 49 | 0 | nein |
| 19:23 | 2 | 94 | 47 / 47 / · / · | 0 | 94 | 0 | nein |
| 19:24 | 2 | 105 | 52 / 53 / · / · | 11 | 102 | 18 | nein |
| 19:25 | 2 | 120 | 56 / 64 / · / · | 18 | 120 | 60 | ja |
| 19:26 | 2 | 123 | 57 / 66 / · / · | 17 | 120 | 60 | ja |
| 19:27 | 2 | 117 | 60 / 57 / · / · | 12 | 114 | 60 | ja |
| 19:28 | 2 | 134 | 66 / 68 / · / · | 21 | 132 | 60 | ja |
| 19:29 | 2 | 126 | 62 / 64 / · / · | 18 | 124 | 60 | ja |
| 19:30 | 2 | 118 | 61 / 57 / · / · | 12 | 114 | 60 | ja |
| 19:31 | 2 | 126 | 63 / 63 / · / · | 16 | 124 | 60 | ja |
| 19:32 | 2 | 122 | 64 / 58 / · / · | 17 | 122 | 60 | ja |
| 19:33 | 2 | 124 | 63 / 61 / · / · | 19 | 123 | 27 | nein |
| 19:34 | 2 | 119 | 61 / 58 / · / · | 10 | 115 | 0 | nein |
| 19:43 | 3a | 194 | 47 / 48 / 50 / 49 | 23 | 190 | 0 | nein |
| 19:44 | 3a | 175 | 44 / 44 / 43 / 44 | 16 | 170 | 0 | nein |
| 19:45 | 3a | 188 | 44 / 46 / 50 / 48 | 9 | 186 | 0 | nein |
| 19:46 | 3a | 193 | 47 / 50 / 51 / 45 | 16 | 192 | 0 | nein |
| 19:47 | 3a | 196 | 49 / 51 / 48 / 48 | 17 | 193 | 0 | nein |
| 19:48 | 3a | 214 | 54 / 53 / 53 / 54 | 11 | 214 | 0 | nein |
| 19:49 | 3a | 210 | 53 / 53 / 51 / 53 | 11 | 210 | 0 | nein |
| 19:50 | 3a | 197 | 49 / 49 / 50 / 49 | 15 | 193 | 0 | nein |
| 19:51 | 3a | 215 | 53 / 54 / 55 / 53 | 12 | 215 | 0 | nein |
| 19:52 | 3a | 216 | 56 / 53 / 54 / 53 | 23 | 214 | 0 | nein |
| 19:53 | 3a | 200 | 50 / 52 / 50 / 48 | 12 | 197 | 0 | nein |
| 19:54 | 3a | 205 | 50 / 55 / 48 / 52 | 15 | 202 | 0 | nein |
| 19:55 | 3b | 190 | 47 / 48 / 48 / 47 | 14 | 189 | 0 | nein |
| 19:56 | 3b | 190 | 48 / 47 / 48 / 47 | 8 | 188 | 0 | nein |
| 19:57 | 3b | 170 | 43 / 39 / 45 / 43 | 4 | 170 | 0 | nein |
| 19:58 | 3b | 188 | 46 / 50 / 45 / 47 | 5 | 187 | 0 | nein |
| 19:59 | 3b | 199 | 50 / 50 / 50 / 49 | 3 | 197 | 0 | nein |

Gültig heißt nach der Regel vom 21.10.: beide Knoten vollständig und gleich, keine Sender-Lücke, kein Miner-Wechsel. Beide Knoten waren in allen 41 Minuten vollständig und gleich. Ungültig sind die Minuten nur wegen der Sender: In 31 Minuten lief in keiner Sekunde die geplante Zahl von 4 Sendern, in 19:24 und 19:33 nur in 18 und 27 Sekunden (sec.csv, source STP).

Außerhalb der gezählten Minuten: um 18:59 UTC 4 angenommene Ausgaben, je Familie eine, das sind die Genesis-Tx (STP 18:59:36 bis 18:59:38). Um 20:00 UTC noch 4 angenommene und 2 nie angenommene. In den Pausen 19:15 bis 19:19 nichts, 19:35 noch 2.

## Vergleich mit STP

- **Schritt 1 stimmt genau:** 580 gezählt, 580 Hops bei STP, Minute für Minute bis auf eine Verschiebung von 1 zwischen 19:09 und 19:10 (Minutengrenze).
- **Schritt 2 und 3 liegen wir höher:** Im ganzen Fenster 19:00 bis 20:00 sind es 6,382 counted gegen 6,321 source STP, 61 mehr, also 0.97 %. Je Minute sind es 0 bis 5 mehr, weniger nur um 19:09 mit 1.
- **Vermutete Ursache:** STP zählt Hops aus dem Protokoll des Koordinators auf mini ("inclusions come from the mini coordinator's hop record", README). In Schritt 1 sendete nur mini, und dort stimmt es genau. Der Unterschied kommt erst, sobald andere Sender dazukommen. Gewinnt die Ausgabe eines anderen Senders, steht sie vermutlich nicht immer in mini's Protokoll. Belegen kann ich das ohne STPs Tx-Liste nicht. Frage an STP unten.
- **Contention erst mit mehreren Sendern:** Mit einem Sender (Schritt 1 und 19:23) gibt es 0 nie angenommene Ausgaben. Ab 19:24, als die Spuren auf box dazukamen, stehen in jeder Minute 3 bis 23 konkurrierende Ausgaben in Blöcken.

## Abweichungen

Laut Ben, von STP:

1. **box kam erst im zweiten gezählten Fenster dazu**, weil die Handoff-Kopie fehlgeschlagen ist. phase-mini.log: "handoff_copy no_route_to_desk_or_box" um 19:01:20, phase-box.log: Import um 19:24:20. Schritt 1 lief nur mit dem Sender auf mini. In sec.csv laufen alle 4 Sender nur in 525 Sekunden zwischen 19:24:42 und 19:33:50.
2. **Die Covenant-IDs kamen erst um 19:25 UTC**, Frist war 18:55. Für die Zählung war das kein Schaden, weil die Nachzählung nachträglich liest und die Genesis um 18:59:36 bis 18:59:38 lag.
3. **Die tkas-Miner auf dem Cloud-Host hatten seit 11:30 CET 25 kurze Freezes**, der letzte um 16:15 CET (15:15 UTC) mit etwa 10 s, also vor dem Fenster. In phase.log steht keine MINER-Zeile ("miner_line note=config_miners_empty"). Im Parser steht das als Aussage nach Plan, nicht als Messung. Unsere Blockzählung zeigt in allen 120 Minuten zwei Knoten mit gleichen Blöcken.
4. **Die KNS-Spur lief über muon** und wird nicht gezählt. Sie startete erst gegen 19:25 UTC. In STPs minute.csv gibt es keine Zeile für Familie 0, unsere Covenant-Zählung kennt nur f1 bis f4.

Dazu aus STPs Logs:

5. **Spuren auf box:** muon und boson hatten node_dead-Aussetzer um 19:15, 19:35, 19:53 und 19:54 UTC und haben laut README nach 19:33:50 nichts mehr gesendet. boson brachte 55 von 5,314 Versuchen durch (source STP).
6. **Uhren:** box lag bei 18:55 um -888 ms und bei 20:01 um -929 ms daneben, desk bei -85 und -87 ms. mini hat nur eine Messung um 18:08 mit +50 ms, die Punkte 18:55 und 20:01 fehlen. Den Punkt 17:00 hat keine Maschine, gemessen wurde gegen 18:04. Für unsere Zahlen spielt das keine Rolle, sie hängen nur an der Blockzeit. STPs Zeiten auf box sind um fast eine Sekunde verschoben.
7. **STPs Review widerspricht ihrem eigenen sec.csv:** Die Review sagt "No second in the counted minutes had all four senders on at once". In sec.csv sind es aber 525 Sekunden in den gezählten Minuten von 19:24 bis 19:33 mit 4 von 4 Sendern. Unsere 8 gültigen Minuten beruhen auf sec.csv.
8. **phase-box.log meldet die Spuren um 19:51:15 wieder an**, sec.csv zeigt in Schritt 3 aber nur 1 bis 2 Sender. Wir zählen die Minuten deshalb als Sender-Lücke.
9. Keine Submit-Zeiten von STP, deshalb gibt es keine Zeit von Submit bis Block. Die Spalten dafür bleiben leer.

## Was die Zahlen tragen

- **Ja:** Die Zahl der angenommenen Covenant-Ausgaben je Familie und Minute, auf zwei Knoten gleich gezählt, und dass sie mit der Zahl der Familien fast gleich mitwächst. Bei einer Familie etwa 0.8 je Sekunde, bei zwei und vier je Familie 0.8 bis 1.0.
- **Ja:** STPs Headline (0.81, 1.96, 3.24 Hops je s) passt zu unserer Kette, wir liegen 0 bis 1.7 % darüber.
- **Ja:** Konkurrierende Ausgaben erscheinen auf der Kette erst mit mehreren Sendern, und keine davon wurde angenommen.
- **Nein:** Ein Vergleich der Schritte unter gleichen Bedingungen. Schritt 1 lief mit 1 Sender, Schritt 2 mit 1 bis 4, Schritt 3 mit 1 bis 2. Die Senderzahl ändert sich also mit dem Schritt.
- **Nein:** Grenzen der Knoten. STP schreibt selbst, die Last war leicht (Mempool höchstens 61, RPC unter 17 ms, source STP).
- **Nein:** Latenz von Submit bis Block, weil keine Submit-Zeiten kamen.
- **Nein:** Etwas über KNS oder über die Miner im Fenster.

Für eine öffentliche Zahl taugt am ehesten "angenommene Covenant-Ausgaben je Sekunde bei 1, 2 und 4 Familien, counted auf zwei Knoten". Mit dem Hinweis, dass es eine leichte Last auf Testnet-10 war.

## Ist ein Wiederholungslauf nötig?

Für die Kernaussage nicht: Mehr Familien bringen fast gleich mehr angenommene Ausgaben, das steht auf der Kette. Für alles, was STP eigentlich zeigen wollte, ja: Contention mit allen Sendern von der ersten Sekunde an, höhere Rate, 8 Familien und die Grenzen der Knoten. STPs eigene Liste (Handoff automatisch, Sender ohne Handoff starten nicht, öffentliche Spuren vom desk, Uhren richten, 4 Familien mit höherer Rate, dann 8) deckt das. Von unserer Seite dazu:

1. Covenant-IDs vor START, damit der Live-Zähler die Familien gleich mitzählt.
2. Eine Datei mit Submit-Zeiten je Tx (tx_id, submit_ms), dann gibt es die Zeit bis zum Block. Sie bleibt privat bei Ben, ins Repo kommt nur die Auswertung.
3. MINER-Zeilen oder eine klare Aussage zu den Minern im Fenster.
4. NTP auf allen drei Maschinen zu allen drei Punkten.
5. sec.csv mit senders_on je Spur, nicht nur die Summe, damit eine Lücke einem Sender zugeordnet werden kann.

## Offene Fragen an Ben

1. Soll STP gefragt werden, ob "hops" nur die Aufnahmen aus mini's Protokoll zählt? Das würde die 61 Ausgaben mehr bei uns erklären.
2. Soll STP den Satz in der Review zu "no second with all four senders" prüfen? sec.csv zeigt 525 Sekunden mit 4 von 4.
3. Gibt es einen Termin für den Wiederholungslauf? Unser Zähler und die Nachzählung sind bereit. Die Nachzählung braucht nur die Covenant-IDs vor START.

## Was Ben tun muss

- Nichts mergen: Ich merge diesen PR selbst, wenn die Checks grün sind (nur Bericht und CSV, kein Workflow).
- Die Fragen oben beantworten oder an STP weitergeben.
- Der Workflow `tn10-auswertung.yml` und die Parser-Änderung liegen nur auf `messung/tn10-zaehler`, der Branch wird nicht gemergt.
