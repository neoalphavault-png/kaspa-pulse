# BCH Tempnet, Ergänzung zum Abschluss: Gegenrechnung und Stücke von 120 Blöcken (11.11.2026)

Ben am 11.11.: bitcoincashautist hat im Forum 2173, Beitrag 44, direkt gefragt. Wir haben eine Tabelle vor dem 15.11. zugesagt. Frist Fr 13.11. 09:00, Nachtrag Sa 14.11.

<!-- discord -->
BCH Tempnet, Ergänzung zum Abschluss: Deine Forumszahlen zu den sechs Fenstern stimmen genau. Eine Abweichung gibt es bei außerhalb: 68,71 s und 50 s kommen von den Köpfen vom 11.11., mit dem Stand vom 10.11. sind es 68,44 s und 49 s. Die Tabelle in Stücken von 120 Blöcken ist fertig: 314 Stücke, 194 voll abgedeckt. Die Ausbreitung c2 minus GitHub hat den Median −39 ms bei n 2.402. Forumstext im Bericht. Bericht berichte/2026-11-11-bch-tempnet-stuecke.md
<!-- /discord -->

## 1. Gegenrechnung deiner Forumszahlen

Grundlage wie in deinem Auftrag: `tempnet-fenster-2026-11-10.json`, dazu die Köpfe und die `zusammenfassung.json` dieses Stands. Die Köpfe reichen bis 364.603, der Zuhörer bis 10.11. 05:55 UTC. Ein Abstand innerhalb eines Fensters ist der Abstand zwischen zwei aufeinanderfolgenden Blöcken im Fenster, also Blöcke minus 1 je Fenster.

| Zahl | im Forum | nachgerechnet | |
|---|---|---|---|
| Abstände in den sechs Fenstern | 5.609 | 5.609 | gleich |
| Mittel / Median in den Fenstern | 20,19 s / 5 s | 20,19 s / 5 s | gleich |
| Mittel je Fenster | 33,00 / 12,88 / 19,74 / 21,41 / 7,01 / 7,86 s | 33,00 / 12,88 / 19,74 / 21,41 / 7,01 / 7,86 s | gleich |
| Median je Fenster | 10 / 5 / 10 / 7 / 2 / 1 s | 10 / 5 / 10 / 7 / 2 / 1 s | gleich |
| außerhalb, Mittel / Median | 68,71 s / 50 s | 68,44 s / 49 s bei 30.999 Abständen | **abweichend** |
| Stale in den Fenstern | 1.327 auf 1.071 Höhen, höchstens 5 je Höhe | 1.327 auf 1.071 Höhen, höchstens 5 je Höhe | gleich |

**Die Abweichung bei „außerhalb“:** 68,71 s und 50 s ergeben sich genau, wenn man die Köpfe vom 11.11. nimmt (bis 365.759, 32.155 Abstände außerhalb der sechs Fenster). Mit den Köpfen vom 10.11. (bis 364.603), auf denen die Fenster-Datei beruht, sind es 30.999 Abstände, Mittel 68,44 s, Median 49 s.

Beide Werte gelten für alle Abstände, deren Block nicht in einem Fenster liegt, vom ersten Tempnet-Block an. Für das Forum schlage ich vor, die Zahl mit ihrem Stand zu nennen.

## 2. Tabelle in Stücken von 120 Blöcken

- **CSV:** `data/bch/tempnet-stuecke-120-2026-11-11.csv` auf `messung/bch-tempnet` (Commit `63ab522a`), dazu die JSON mit Eingängen und Gegenrechnung.
- **Skript:** `scripts/bch/tempnet_stuecke.py` (PR #309).
- **Eingänge:**
  - Köpfe bis 365.759 (Abruf 11.11. 10:07 UTC)
  - Zuhörer auf GitHub mit 77 Läufen bis 11.11. 19:31 UTC
- **Regeln:**
  - Die Stücke beginnen beim ersten Tempnet-Block 327.989. Das letzte unvollständige Stück fällt weg, das letzte volle endet bei 365.668.
  - Die Blockzeit ist die Kopfzeit minus die Kopfzeit des Vorgängers, je Block des Stücks. Im ersten Stück fehlt der Vorgänger des ersten Blocks.
  - Stale-Blöcke zählen nach Höhe. Ein Stale-Ereignis ist eine Höhe mit einem oder mehr Kandidaten.
  - Die Abdeckung ist der Anteil der Zeit vom ersten bis zum letzten Block des Stücks, in der ein Zuhörer lief. Unter 99,9 % ist das Stück als nicht voll markiert, Stale-Werte bleiben leer.
- **Ergebnis:**
  - 314 Stücke, davon 194 voll abgedeckt.
  - Nicht voll sind:
    - 1 bis 110, vor dem Start des Zuhörers am 25.10.
    - 111 mit 36,1 %
    - 125 mit 98,7 %, die Lücke von 1,6 min am 26.10.
    - 227 bis 234, die Lücke vom 3.11. 13:59 bis 4.11. 10:08 UTC
- **Stale in den vollen Stücken:** 1.452 Blöcke in 1.195 Ereignissen. In 96 der 194 vollen Stücke gibt es kein Stale-Ereignis, der Median liegt bei 1.

**Die 12 vollen Stücke mit den meisten Stale-Ereignissen:**

| Stück | Höhen | Beginn (UTC) | mittlere Difficulty | Blockzeit Mittel / Median | stale Blöcke | stale Ereignisse |
|---:|---|---|---:|---|---:|---:|
| 166 | 347.789 bis 347.908 | 29.10. 21:34 | 5,6 | 2,44 / 2 s | 35 | 35 |
| 167 | 347.909 bis 348.028 | 29.10. 21:39 | 21,1 | 2,40 / 2 s | 40 | 40 |
| 168 | 348.029 bis 348.148 | 29.10. 21:44 | 80,1 | 2,52 / 2 s | 36 | 36 |
| 169 | 348.149 bis 348.268 | 29.10. 21:49 | 302,2 | 2,41 / 2 s | 33 | 33 |
| 249 | 357.749 bis 357.868 | 5.11. 16:54 | 33,4 | 4,58 / 1 s | 113 | 71 |
| 250 | 357.869 bis 357.988 | 5.11. 17:03 | 131,0 | 0,94 / 1 s | 151 | 94 |
| 251 | 357.989 bis 358.108 | 5.11. 17:05 | 510,7 | 1,43 / 1 s | 97 | 68 |
| 296 | 363.389 bis 363.508 | 9.11. 17:06 | 5,8 | 15,35 / 1 s | 90 | 68 |
| 297 | 363.509 bis 363.628 | 9.11. 17:36 | 22,5 | 0,80 / 1 s | 112 | 88 |
| 298 | 363.629 bis 363.748 | 9.11. 17:37 | 88,3 | 0,84 / 1 s | 114 | 84 |
| 299 | 363.749 bis 363.868 | 9.11. 17:39 | 346,2 | 0,85 / 1 s | 111 | 79 |
| 300 | 363.869 bis 363.988 | 9.11. 17:41 | 1.348,8 | 1,55 / 1 s | 75 | 59 |

Alle zwölf liegen am Anfang eines Hash-Einstiegs oder in den Minuten davor, während die Difficulty noch steigt. Die Stücke 249 und 296 beginnen kurz vor dem Einstieg aus der Fenster-Datei.

## 3. Was wir nicht liefern, und Ausbreitung

- **Blockgröße und Zahl der Transaktionen** liefern wir nicht. Unser Header-Client hält nur Köpfe. Der Zuhörer hat keinen Mempool und kann daraus keine volle Zählung machen.
- **Ausbreitung:** Beide Zuhörer, GitHub und c2, liefen vom 9.11. 16:30 bis 11.11. 18:01 UTC zugleich. c2 sah 2.402 Kettenblöcke, alle auch auf GitHub.
  - Erste Ankündigung c2 minus GitHub: Median −0,039 s, p10 −0,051 s, p90 0,042 s, kleinster −0,101 s, größter 0,217 s, n 2.402.
  - c2 war 1.574 mal zuerst, GitHub 822 mal.
- **Uhren:** GitHub nach `chronyc tracking` im Bereich von Mikrosekunden, c2 nach `timedatectl` zwischen −1,8 ms und −0,02 ms. Die Differenzen liegen also deutlich über dem Versatz der Uhren. Das Fenster enthält das Hash-Fenster vom 9.11.
- **Reicht das?** Für eine Aussage über den Weg zwischen zwei Messpunkten ja. Für eine Ausbreitung im Netz nein, denn es sind nur zwei Orte.

## 4. Forumsentwurf (Ben postet)

---

@bitcoincashautist thanks for the idea to cut the whole tempnet into chunks of 120 blocks, it shows where the stale blocks sit better than our window tables did. Here is the table, together with a check of the window numbers we posted.

**Check of the window numbers.** Recounted from our headers and our listener as of 10 Nov, the six hash windows have 5,609 intervals with a mean of 20.19 s and a median of 5 s, and the 1,327 stale blocks inside them sit on 1,071 heights with at most 5 at one height. The mean and median outside the windows were taken from headers up to block 365,759 of 11 Nov. With the headers of 10 Nov, up to block 364,603, they are 68.44 s and 49 s over 30,999 intervals.

**Chunks of 120 blocks.** We start at block 327,989 and end with the last full chunk at block 365,668, which gives 314 chunks. Block time is header time minus the header time of the parent. A stale event is one height with one or more stale candidates. A chunk counts as covered when our listener ran for the whole time from its first to its last block. Of the 314 chunks, 194 are covered. Chunks 1 to 110 lie before our listener started on 25 Oct, and chunks 227 to 234 fall into our gap from 3 Nov 13:59 utc to 4 Nov 10:08 utc. Those chunks stay in the csv with empty stale columns.

Across the 194 covered chunks we counted 1,452 stale blocks in 1,195 stale events. In 96 of them there is no stale event at all. These are the twelve with the most stale events.

| chunk | heights | start utc | mean difficulty | mean / median block time | stale blocks | stale events |
|---:|---|---|---:|---|---:|---:|
| 166 | 347,789 to 347,908 | 29 Oct 21:34 | 5.6 | 2.44 / 2 s | 35 | 35 |
| 167 | 347,909 to 348,028 | 29 Oct 21:39 | 21.1 | 2.40 / 2 s | 40 | 40 |
| 168 | 348,029 to 348,148 | 29 Oct 21:44 | 80.1 | 2.52 / 2 s | 36 | 36 |
| 169 | 348,149 to 348,268 | 29 Oct 21:49 | 302.2 | 2.41 / 2 s | 33 | 33 |
| 249 | 357,749 to 357,868 | 5 Nov 16:54 | 33.4 | 4.58 / 1 s | 113 | 71 |
| 250 | 357,869 to 357,988 | 5 Nov 17:03 | 131.0 | 0.94 / 1 s | 151 | 94 |
| 251 | 357,989 to 358,108 | 5 Nov 17:05 | 510.7 | 1.43 / 1 s | 97 | 68 |
| 296 | 363,389 to 363,508 | 9 Nov 17:06 | 5.8 | 15.35 / 1 s | 90 | 68 |
| 297 | 363,509 to 363,628 | 9 Nov 17:36 | 22.5 | 0.80 / 1 s | 112 | 88 |
| 298 | 363,629 to 363,748 | 9 Nov 17:37 | 88.3 | 0.84 / 1 s | 114 | 84 |
| 299 | 363,749 to 363,868 | 9 Nov 17:39 | 346.2 | 0.85 / 1 s | 111 | 79 |
| 300 | 363,869 to 363,988 | 9 Nov 17:41 | 1,348.8 | 1.55 / 1 s | 75 | 59 |

All twelve sit at the start of a hash entry or in the minutes just before it, while difficulty is still climbing.

**What the table does not have.** Block size and transaction count are not in it. Our header client keeps headers only, and our listener has no mempool, so it cannot give a full count.

**Two listeners.** Since 9 Nov 16:30 utc a second copy of our listener runs on another network path. Up to 11 Nov 18:01 utc both saw the same 2,402 chain blocks. The first announcement reached the second listener a median of 0.039 s earlier than the first one, with a p10 of 0.051 s earlier and a p90 of 0.042 s later. Two places are not a measure of propagation across the network, so we give this as the difference between our two points only.

The csv is data/bch/tempnet-stuecke-120-2026-11-11.csv on messung/bch-tempnet in github.com/neoalphavault-png/kaspa-pulse, made with scripts/bch/tempnet_stuecke.py. We will update it on 14 Nov with the data up to then.

---

## PR-Nummern

- PR #309, `tempnet_stuecke.py`
- PR #305, Abschlussbericht, wird am Fr 13.11. aufgefrischt
- dieser Bericht

## Offene Fragen an Ben

1. Bleibt im Forum die Zahl außerhalb mit Stand 11.11. stehen, oder korrigierst du sie auf 68,44 s und 49 s vom 10.11.? Der Entwurf nennt beide mit Stand.
2. Der Zuhörer sieht für die meisten Blöcke die Kurz-IDs der Compact Blocks, also eine Zahl, die der Zahl der Transaktionen nahe kommt. Soll das als source „our listener, estimate“ dazu, oder bleibt es beim Satz, dass wir keine Transaktionen zählen? Mein Vorschlag ist, beim Satz zu bleiben.

## Was Ben tun muss

- Den Forumsentwurf posten, nach dem Update am Fr 13.11. oder wie er ist.
