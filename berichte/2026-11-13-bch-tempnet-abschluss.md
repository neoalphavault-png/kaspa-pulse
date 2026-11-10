# BCH Tempnet, Abschlussbericht für das Forum (Ben 10.11.2026, Frist Fr 13.11. 09:00)

Zusage im Forum #40: Stale-Blöcke getrennt nach den Ein- und Ausstiegen der ASIC-Hashrate, die Fenster aus der Difficulty. Gerechnet aus unseren eigenen Tempnet-Köpfen, dazu rufitnes' fünf Fenster aus #37 und die Gegenprobe gegen die CSV von bitcoincashautist aus #41.

<!-- discord -->
BCH Tempnet, Entwurf des Abschlussberichts fertig (Stand 10.11. 09:47 UTC), Ben postet. Sechs Hash-Fenster aus unseren eigenen Köpfen. In diesen Fenstern sind 21,0 % der angekündigten Blöcke stale, außerhalb 0,70 %. Die Difficulty stimmt in allen 35.101 gemeinsamen Höhen mit der CSV von bitcoincashautist überein. Die Zahlen frische ich am Fr 13.11. vor 09:00 Berlin auf. Bericht berichte/2026-11-13-bch-tempnet-abschluss.md
<!-- /discord -->

## Grundlage

- **Köpfe:** `data/bch/tempnet-koepfe.csv.gz` auf `messung/bch-tempnet`, Abruf 10.11. 09:47 UTC, Höhe 327.989 bis 364.603. Auf Verkettung und Arbeit geprüft, Gegenprobe 500 von 500 bei zwei Peers.
- **Difficulty je Kopf aus nBits.** Kein fremdes Skript, nur `scripts/bch/tempnet_fenster.py` (PR #304).
- **Zuhörer:** 70 Läufe, 25.10. 09:15 bis 10.11. 05:55 UTC, abgedeckt 368,9 h. 22.318 von 22.381 Kettenblöcken angekündigt, 1.449 stale nach 6 Bestätigungen.
- **Lücke im Zuhörer:** 3.11. 13:59:44 bis 4.11. 10:08:30 UTC, rund 20 h. Ein Lauf hat seine Daten nicht gesichert. Das ASIC-Fenster vom 3.11. 17:26 bis 21:10 UTC liegt ganz in dieser Lücke. Dort zählen wir nichts.
- **Vergleich, source bitcoincashautist:** `tempnet_d.csv` aus dem Gist in #41, Spalten `height,difficulty`, Höhe 327.900 bis 363.089, sha256 `e7ce24e0…94e`. Nur als Daten aus der HTML-Seite des Gists gelesen, denn die Raw-Adresse ist aus der Sitzung gesperrt. Das mitgelieferte Skript habe ich nicht ausgeführt.
- **Zahlen als JSON:** `data/bch/tempnet-fenster-2026-11-10.json` auf `messung/bch-tempnet` (Commit `ed765147`).
- **Forum:** Den Thread konnte ich erst lesen, nachdem `bitcoincashresearch.org` in die Netzwerkfreigabe der Umgebung kam. Das hast du am 10.11. bestätigt.

## Regel für die Fenster

Ein Block gehört zu einem Hash-Fenster, wenn über 10 Blöcke eine von zwei Bedingungen gilt:
- Die Arbeitsrate liegt bei mindestens 5 Difficulty je Sekunde. Das ist das Zehnfache der höchsten Stundenrate außerhalb der Fenster.
- Die 10 Blöcke kamen in höchstens 60 s, also mit der zehnfachen Zielrate. Diese Bedingung fängt die Rampe am Anfang, wenn die Blöcke schon schnell kommen, die Difficulty aber noch niedrig ist.

Die Ränder liegen auf dem ersten und letzten Block, der allein schnell ist. Läufe mit weniger als 30 min Abstand werden zusammengelegt. Einstieg und Ausstieg sind Kopfzeiten.

**Kontrolle gegen rufitnes' Spitzenstunden aus #37**, Kettenblöcke je Stunde nach Kopfzeit:

| Stunde (UTC) | rufitnes | wir |
|---|---:|---:|
| 29.10. 21:00 | 688 | 689 |
| 2.11. 23:00 | 562 | 561 |
| 3.11. 08:00 | 254 | 254 |
| 3.11. 17:00 | 351 | 351 |
| 5.11. 17:00 | 641 | 641 |

Die Abweichung um je einen Block erklärt eine Kopfzeit an der Stundengrenze.

## Ergebnis (Stand 10.11.)

| Fenster | Einstieg (UTC) | Ausstieg (UTC) | Höhen | Blöcke | größte Difficulty | Zuhörer | Kettenblöcke angekündigt | stale | Anteil |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 29.10. 21:33:24 | 30.10. 16:28:35 | 347.756 bis 349.820 | 2.065 | 101.573 | 100 % | 2.065 | 236 | 10,3 % |
| 2 | 2.11. 22:51:45 | 3.11. 01:59:58 | 353.742 bis 354.619 | 878 | 29.643 | 100 % | 878 | 118 | 11,8 % |
| 3 | 3.11. 08:22:35 | 3.11. 10:39:07 | 354.727 bis 355.142 | 416 | 31.214 | 100 % | 416 | 32 | 7,1 % |
| 4 | 3.11. 17:26:41 | 3.11. 21:10:47 | 355.214 bis 355.842 | 629 | 69.678 | 0 % (Lücke) | | | |
| 5 | 5.11. 17:00:15 | 5.11. 18:20:12 | 357.758 bis 358.442 | 685 | 19.273 | 100 % | 685 | 405 | 37,2 % |
| 6 | 9.11. 17:35:01 | 9.11. 19:38:15 | 363.417 bis 364.358 | 942 | 46.966 | 100 % | 942 | 536 | 36,3 % |

| | Kettenblöcke angekündigt | stale | Anteil |
|---|---:|---:|---:|
| in den Hash-Fenstern | 4.986 | 1.327 | 21,0 % |
| außerhalb | 17.332 | 122 | 0,70 % |

**rufitnes' fünf Fenster aus #37**, nach erster Ankündigung bei uns:

| Fenster (UTC) | Zuhörer | Kettenblöcke | stale | Anteil |
|---|---:|---:|---:|---:|
| 29.10. 21:00 bis 23:00 | 100 % | 976 | 216 | 18,1 % |
| 2.11. 22:00 bis 3.11. 00:00 | 100 % | 738 | 112 | 13,2 % |
| 3.11. 08:00 bis 09:00 | 100 % | 254 | 28 | 9,9 % |
| 3.11. 17:00 bis 18:00 | 0 % (Lücke) | | | |
| 5.11. 17:00 bis 18:00 | 100 % | 641 | 405 | 38,7 % |
| zusammen | | 2.609 | 761 | 22,6 % |
| übrige Zeit | | 19.709 | 688 | 3,4 % |

**Gegenprobe, source bitcoincashautist:**
- In allen 35.101 Höhen, die beide Dateien haben (327.989 bis 363.089), stimmt die Difficulty aus unseren nBits mit seiner CSV überein: 0 Abweichungen.
- Abweichungen gibt es nur im Umfang. Seine Datei beginnt 89 Höhen früher (327.900 bis 327.988, vor dem Abzweig des Tempnet) und endet bei 363.089. Fenster 6 liegt danach und ist bei ihm noch nicht enthalten.
- Seine CSV hat keine Zeiten. Die Zeiten der Fenster kommen nur aus unseren Köpfen.

**Fenster 6 am 9.11.** ist neu, also nach rufitnes' Beitrag. rufitnes schrieb am 8.11., die letzten 72 h seien ruhig gewesen. Das gilt bei uns bis zum 9.11. um 17:35 UTC.

## Forumsentwurf (Ben postet)

Textregeln eingehalten: kein Doppelpunkt im Fließtext außer in Uhrzeiten, kein Gedankenstrich, kein Pfeil, kein Satz beginnt mit einer Ziffer. Die Tabellen enthalten nur Zahlen.

---

@bitcoincashautist @Rufitnes Here is the split we promised, with the hash windows taken from our own tempnet headers.

**How we found the windows.** We computed the difficulty of every header from its nBits. Our headers are checked for linkage and proof of work when we fetch them. A block belongs to a hash window when 10 consecutive blocks either carried at least 5 difficulty per second of work, ten times the highest hourly rate outside the windows, or came within 60 s, ten times the 60 s target rate. The second rule catches the start of an entry, when blocks already come fast but difficulty has not caught up. Entry and exit are header times of the first and last fast block. Headers up to block 364,603, fetched 10 Nov 09:47 utc.

**Cross check against bitcoincashautist's csv** (source bitcoincashautist, the gist in #41). For all 35,101 heights both files share, from 327,989 to 363,089, the difficulty from our nBits matches his to the last digit. His file starts 89 blocks earlier, before the fork, and ends before our sixth window. The times come from our headers only, because his file has heights and difficulty.

**Six hash windows**

| window | entry utc | exit utc | blocks | max difficulty | chain blocks announced to our listener | stale | share |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 29 Oct 21:33 | 30 Oct 16:28 | 2,065 | 101,573 | 2,065 | 236 | 10.3 % |
| 2 | 2 Nov 22:51 | 3 Nov 01:59 | 878 | 29,643 | 878 | 118 | 11.8 % |
| 3 | 3 Nov 08:22 | 3 Nov 10:39 | 416 | 31,214 | 416 | 32 | 7.1 % |
| 4 | 3 Nov 17:26 | 3 Nov 21:10 | 629 | 69,678 | not covered | | |
| 5 | 5 Nov 17:00 | 5 Nov 18:20 | 685 | 19,273 | 685 | 405 | 37.2 % |
| 6 | 9 Nov 17:35 | 9 Nov 19:38 | 942 | 46,966 | 942 | 536 | 36.3 % |

| | chain blocks announced | stale | share |
|---|---:|---:|---:|
| inside the six windows | 4,986 | 1,327 | 21.0 % |
| outside | 17,332 | 122 | 0.70 % |

**Rufitnes' five windows from #37**, by our first announcement

| window utc | chain blocks | stale | share |
|---|---:|---:|---:|
| 29 Oct 21:00 to 23:00 | 976 | 216 | 18.1 % |
| 2 Nov 22:00 to 3 Nov 00:00 | 738 | 112 | 13.2 % |
| 3 Nov 08:00 to 09:00 | 254 | 28 | 9.9 % |
| 3 Nov 17:00 to 18:00 | not covered | | |
| 5 Nov 17:00 to 18:00 | 641 | 405 | 38.7 % |
| together | 2,609 | 761 | 22.6 % |
| all other hours | 19,709 | 688 | 3.4 % |

Our hourly header counts agree with rufitnes' peak hours within one block (689, 561, 254, 351 and 641 against his 688, 562, 254, 351 and 641).

**A gap we have to name.** Our listener has no data from 3 Nov 13:59 utc to 4 Nov 10:08 utc, because one run did not save its data. Window 4 lies fully inside that gap, so we count no stale blocks there. Rufitnes' 70 replaced tips, 63 of them in the 3 Nov 17:00 hour, stay source rufitnes and are not part of our numbers.

**Definitions as before.** A block counts as stale when it was announced to us and is not in the chain 6 blocks later. The share is stale blocks over chain blocks announced to us plus stale blocks. One listener on one network path, coverage 368.9 h from 25 Oct 09:15 utc to 10 Nov 05:55 utc. Stale blocks go to a window by height, and to rufitnes' hours by the time we first saw them. Numbers are counted by us except where marked as source.

The script is scripts/bch/tempnet_fenster.py and the numbers are in data/bch/tempnet-fenster-2026-11-10.json on messung/bch-tempnet in github.com/neoalphavault-png/kaspa-pulse. We will update them on 13 Nov with the data up to then.

---

## Offene Fragen an Ben

1. Soll der Beitrag die Zahlen vom 10.11. tragen, oder wartest du auf das Update am Fr 13.11. vor 09:00 Berlin? Ich schlage das Update vor, denn dann sind gut drei Tage mehr drin.
2. Der zweite Messpunkt auf c2 läuft seit dem 9.11. Soll er schon in diesen Beitrag oder erst in den Nachtrag am Sa 14.11.? Mein Vorschlag ist der Nachtrag, denn bis Freitag sind es erst rund 3,5 Tage.

## Was Ben tun muss

- Den Entwurf posten, sobald das Update vom Freitag drin ist.
