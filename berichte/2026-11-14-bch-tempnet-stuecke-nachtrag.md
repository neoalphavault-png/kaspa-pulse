# BCH Tempnet, Nachtrag zu den Stücken von 120 Blöcken, Stand 14.11.2026

Zusage im Forum #44/#47: die Tabelle in Stücken von 120 Blöcken aufgefrischt und, wie bitcoincashautist in #47 gefragt hat, eine zweite CSV ohne Blöcke mit Difficulty 1. Entscheidungen Ben 12.11. eingehalten: Top 12 plus alle Gleichstände an der Grenze, außerhalb beide Zahlen mit Stand, keine Transaktionen gezählt und nichts aus Kurz-IDs geschätzt.

<!-- discord -->
BCH Tempnet, Stücke von 120 Blöcken aufgefrischt (Stand 14.11. 14:02 UTC), dazu die zweite CSV ohne Difficulty 1. Es sind 353 Stücke, 231 voll abgedeckt. Ohne Difficulty 1 fallen je Stück im Median 18 Blöcke weg. Keinen Block verlieren 25 Stücke, gar keinen mehr haben 23. Die Top-Stücke (12 plus Gleichstand, 13 Zeilen) sind in beiden CSV dieselben. Die Ausbreitung c2 minus GitHub hat den Median −37 ms bei n 6.848. Forumsabsatz mit 112 Wörtern im Bericht. Bericht berichte/2026-11-14-bch-tempnet-stuecke-nachtrag.md
<!-- /discord -->

## Dateien und Eingänge

Auf `messung/bch-tempnet`, Commit `1b9359c2` ([skip ci]):
- `data/bch/tempnet-stuecke-120-2026-11-14.csv`, die erste CSV mit unveränderter Form. Die Stücke 1 bis 314 sind Zeile für Zeile gleich wie am 11.11.
- `data/bch/tempnet-stuecke-120-ohne-diff1-2026-11-14.csv`, die zweite CSV mit denselben Spalten plus `block_count`.
- `data/bch/tempnet-stuecke-120-2026-11-14.json` mit Eingängen, Ausbreitung und Kennzahlen der zweiten CSV.

Eingänge:
- **Köpfe:** Abruf 14.11. 14:02 UTC, bis 370.349.
- **Zuhörer GitHub:** 89 Läufe bis 14.11. 12:01 UTC.
- **Zuhörer c2:** 21 Läufe vom 9.11. 16:30 bis 14.11. 12:01 UTC. Mit `scripts/bch/lauscher_auswertung.py` gegen dieselben Köpfe ausgewertet.
- **Skript:** `scripts/bch/tempnet_stuecke.py` von main (#309, #312) mit `--ohne-diff1-csv`. Selbsttest bestanden.

## Erste CSV, Stand 14.11.

- 353 Stücke, das letzte volle endet bei 370.348. Davon sind 231 voll abgedeckt.
- Nicht voll sind:
  - 1 bis 110, vor dem Start des Zuhörers
  - 111 mit 36,1 %
  - 125 mit 98,7 %
  - 227 bis 234, die Lücke vom 3.11. 13:59 bis 4.11. 10:08 UTC
  - 352 mit 99,6 % und 353 mit 0 %, nach dem Ende des letzten Zuhörerlaufs um 14.11. 12:01 UTC
- **Stale in den vollen Stücken:** 1.492 Blöcke in 1.235 Ereignissen. 116 der 231 vollen Stücke haben kein Stale-Ereignis, der Median liegt bei 0.

## Zweite CSV ohne Difficulty 1

**Regel:**
- Gleiche `chunk_n` und gleiche Höhen wie in der ersten CSV.
- Blöcke mit nBits 1d00ffff zählen nicht. `block_count` ist die Zahl der übrigen Blöcke.
- Mittlere Difficulty, Blockzeiten und Stale gelten nur über die übrigen Blöcke. Stale zählt nur auf Höhen, deren Kettenblock bleibt.
- Die Blockzeit ist die Kopfzeit minus die Kopfzeit des Vorgängers, auch wenn der Vorgänger Difficulty 1 hat.
- In Stücken ohne übrige Blöcke bleiben Mittel und Blockzeiten leer.

**Wie viele Blöcke wegfallen:**
- Insgesamt fallen 9.273 Blöcke weg.
- Je Stück liegt der Median bei 18, das Maximum bei 120.
- 25 Stücke haben keinen Wegfall.
- 23 Stücke haben gar keine Blöcke mehr: 3 bis 23 vor dem Zuhörer, dazu 183 und 255, beide voll abgedeckt. Die beiden liegen kurz nach einem Ausstieg der Hashrate (30.10. und 5.11.).
- Nur über die 231 vollen Stücke gezählt: Median 17, 23 ohne Wegfall, 2 ganz leer.
- **Stale in den vollen Stücken:** 1.436 Blöcke in 1.179 Ereignissen, also 56 Blöcke und 56 Ereignisse weniger. 134 volle Stücke haben kein Stale-Ereignis.

**Was sich an den Top-Stücken ändert.** Es sind die 12 mit den meisten Stale-Ereignissen, plus alle Stücke mit Gleichstand an der Grenze. In beiden CSV sind es dieselben 13 Stücke mit denselben Stale-Zahlen, denn Stück 170 hat wie Stück 169 genau 33 Ereignisse. Die Reihenfolge bleibt gleich. Nur zwei Stücke verlieren Blöcke:

| Stück | Blöcke übrig | mittlere Difficulty | Blockzeit Mittel / Median | stale Blöcke / Ereignisse |
|---:|---:|---|---|---|
| 249 | 119 | 33,4 auf 33,7 | 4,58 auf 3,58 s / 1 s | 113 / 71, gleich |
| 296 | 118 | 5,8 auf 5,9 | 15,35 auf 12,79 s / 1 s | 90 / 68, gleich |

Die übrigen 11 Top-Stücke haben 120 Blöcke ohne Difficulty 1 und sind in beiden CSV gleich.

## Ausbreitung, Stand 14.11.

- **Zeitraum:** Beide Zuhörer liefen vom 9.11. 16:30 bis 14.11. 12:01 UTC zugleich. c2 sah 6.848 Kettenblöcke, alle auch auf GitHub.
- **Erste Ankündigung c2 minus GitHub:**
  - Median −0,037 s
  - p10 −0,053 s
  - p90 0,042 s
  - kleinster Wert −0,103 s, größter 0,217 s
- **Wer zuerst:** c2 war 4.215 mal zuerst, GitHub 2.627 mal.
- Am 11.11. waren es n 2.402 und ein Median von −0,039 s. Es sind weiter nur zwei Messpunkte.

## Forumsentwurf (Ben postet)

Ein Absatz mit 112 Wörtern, ohne Zwischenüberschriften. Die Tabelle steht nur als Verweis auf die CSV im Text. Textregeln eingehalten.

---

@bitcoincashautist thanks for the idea of chunks of 120 blocks. As you asked, a second csv leaves out every block with nBits 1d00ffff, keeps the same chunk_n and heights and adds block_count. Means, block times and stale count only the remaining blocks. A median of 18 blocks per chunk drops out, 25 chunks lose none and 23 have none left. The top twelve plus the tie at the boundary stay the same thirteen chunks. Both csv files are on messung/bch-tempnet in github.com/neoalphavault-png/kaspa-pulse, as of 14 Nov 14:02 utc. The hours up to 15 Nov 12:00 utc are missing, and our gap from 3 Nov 13:59 to 4 Nov 10:08 utc stays empty.

---

## PR-Nummern

- PR #309 und #312, `tempnet_stuecke.py` (gemergt)
- PR #310, Stücke-Bericht vom 11.11. (offen, roter Discord-Check)
- dieser Bericht

## Offene Fragen an Ben

- Weiter offen von #310: Soll der Hostnamen-Filter in `bericht_discord.py` unsere eigene Seite erlauben? Bis dahin stehen in Discord-Abschnitten keine Seitennamen.

## Was Ben tun muss

- Den Absatz vor dem Ende des Tempnet am So 15.11. posten, zusammen mit oder nach dem Nachtrag zum Abschluss.
- #310 mergen oder schließen. Die Zahlen darin sind auf dem Stand vom 11.11. und durch diesen Nachtrag ergänzt.
