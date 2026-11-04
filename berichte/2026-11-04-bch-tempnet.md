# BCH Tempnet 2027, Woche 3, Bericht 4.11.2026

Grundlage sind der Wochenlauf von Ben (Auftrag 21.10.), der Nachtrag zum Build-Wechsel (30.10.) und der Forumsbeitrag für Woche 3 (3.11.).

## Was gemacht ist

- **Wochenlauf:**
  - Stichtag 2026-11-04T10:00:00Z gesetzt (`1a8c1c5`). Lauf [41812080818](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41812080818) war grün, der Bot-Commit ist `fd7cb84`.
  - Abruf 10:07:51 UTC, Spitze 356.042.
  - Die Zielhöhe kam nur aus Peers mit bestätigtem Abzweig 327.989. Zwei Gegenproben ergaben je 500 von 500 gleiche Hashes, verworfene Abzweige gab es keine.
  - Der Stand liegt in `data/bch/tempnet-2026-11-04.json` und `docs/bch-tempnet-2026-11-04.md`. Zwischenstand-Dateien gab es keine.
- **Gegenprobe gegen chaingraph:** Sie gab diesmal HTTP 503, letzte Woche HTTP 403. Ich habe das nicht umgangen.
- **PH-Entwurf:** `ph-entwurf-bch.yml` lief grün ([41812196507](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41812196507)). Die Aufforderung an #moderator-only kam mit HTTP 204 an.
- **Adressen:** In `data/bch` und `docs` stehen keine IPs und keine Hostnamen.
- **Forumsbeitrag Woche 3:**
  - Er steht in `berichte/2026-11-04-bch-tempnet-woche3-forum.md` auf `main`, [PR #251](https://github.com/neoalphavault-png/kaspa-pulse/pull/251), Squash-Merge `ed0ae2b` am 4.11. um 10:13 UTC. Der Text kann direkt kopiert werden, Ben postet ihn.
  - Die Zahlen kommen aus `scripts/bch/forum_woche3.py` und `data/bch/tempnet-woche3-forum-2026-11-04.json` (`e6f219c`).
  - Den Branch `bericht/bch-tempnet-woche3-forum` konnte ich nicht löschen, GitHub antwortete mit 403.
- **Build-Wechsel:** `data/bch/build-wechsel.json` und `.md` sind neu gerechnet, Stand 4.11. (`bfe7c0f`).
- **Zuhörer:**
  - Der Lauf 43 vom 3.11. brach nach 2 h 25 min ab, ohne Log und ohne Daten. Vermutlich ist der Runner weggefallen. Dadurch startete kein Folgelauf.
  - Die Daten des Zuhörers enden deshalb am 3.11. um 13:59 UTC.
  - Ich habe den Zuhörer am 4.11. um 10:08 UTC von Hand neu gestartet (Run 41812164707).

## Woche 3, getrennt vor und nach 29.10. 21:00 UTC

Das Fenster reicht vom 28.10. 10:00 bis 4.11. 10:00 UTC. Den Schnitt hat Ben auf 21:00 UTC gelegt, nicht auf den Neustart um 22:35 UTC. Alle Werte sind counted, die Spalte für 60 s ist computed.

| Köpfe | vorher | nachher | computed für 60 s |
|---|---:|---:|---:|
| Abstände | 2.113 | 8.314 | |
| Mittel | 59,62 s | 57,59 s | 60 s |
| Median | 43,0 s | 30,0 s | 41,6 s |
| p90 | 132,0 s | 129,0 s | 138,2 s |
| p99 | 207,0 s | 382,9 s | 276,3 s |
| über 5 min | 0 | 130 (1,56 %) | 0,67 % |
| längste Lücke | 276 s | 1.159 s | etwa 576 s |
| Mindestschwierigkeit | 282 | 1.513 | |
| Abstand genau 120 s | 46 | 57 | |

| Zuhörer | vorher | nachher (bis 3.11. 13:59) |
|---|---:|---:|
| Kettenblöcke | 2.113 | 7.449 |
| timestamp_deviation Median / p90 / p99, alle | 0,80 / 3,34 / 36,3 s | 3,19 / 5,29 / 14,1 s |
| dto. ohne genau 120 s | 0,78 / 3,20 / 5,1 s (46 ausgelassen) | 3,18 / 5,25 / 12,2 s (55 ausgelassen) |
| propagation_spread Median / p90 | 7,8 / 11,0 s | 7,2 / 10,3 s |
| stale nach 6 Bestätigungen | 4 von 2.117 (0,19 %) | 398 von 7.847 (5,07 %) |

**Was die Tabellen zeigen:**
- **Stale-Blöcke:** Von den 398 stale-Blöcken nachher fallen 356 in drei kurze Abschnitte:

  | Abschnitt UTC | stale | Kettenblöcke je Stunde |
  |---|---:|---:|
  | 29.10. 21 bis 23 Uhr | 216 | 488 |
  | 2.11. 22 bis 3.11. 0 Uhr | 112 | 369 |
  | 3.11. 8 bis 9 Uhr | 28 | 254 |

  Der Median liegt bei 58 Kettenblöcken je Stunde.
- **propagation_spread:** Vorher kamen am 29.10. zwischen 00:21 und 00:55 UTC 38 Blöcke bei einem einzelnen Peer mehr als 10 min nach der ersten Ankündigung an. Deshalb nennt der Forumstext kein p99 des propagation_spread.
- **Abstände:** Nachher wechseln sich Schübe und lange Lücken ab. Der Median fällt auf 30 s, 130 Abstände liegen über 5 min, und 1.513 Blöcke tragen Mindestschwierigkeit.

**Vergleich mit dem Wochenlauf vom 28.10.** (gesamt ab 327.989):

| | 28.10. | 4.11. |
|---|---:|---:|
| Blöcke | 17.625 | 28.052 |
| Mittel / Median | 63,13 / 44,0 s | 61,22 / 40,0 s |
| p90 / p99 | 128,0 / 216,0 s | 129,0 / 244,0 s |
| über 5 min | 31 (0,18 %) | 161 (0,57 %) |
| Mindestschwierigkeit | 4.819 | 6.614 |
| Abstand 0 | 56 | 181 |
| Sprünge der Schwierigkeit | 1 | 15 (3 eingeholt, 10 abgelöst, 1 offen, 1 nicht in 2.000 Blöcken) |

## Welche älteren Zahlen betroffen sein können

- **Woche 2:** bleibt gültig. Der p99 der timestamp_deviation von 31,1 s gilt nur mit den 107 Blöcken mit genau 120 s, ohne sie sind es 5,2 s. Der Forumsbeitrag für Woche 3 sagt das.
- **Zwischenstand vom 30.10. 13:18:** bitte nicht verwenden.

## Offene Fragen an Ben

1. Die 101 Blöcke von einem Miner stammen aus deinem Auftrag, als Angabe von rufitnes. Das Forum ist für mich gesperrt, und in rufitnes' öffentlichen Daten steht keine Zuordnung zu Minern. Bitte vor dem Posten prüfen.
2. Der Forumstext begründet den Schnitt mit „shortly before the node restart discussed in this thread“. Passt das so?
3. Hat der neue Build von 9500 einen eigenen User-Agent? Bisher bleibt die Kennung gleich.

## Was Ben tun muss

- Den Forumsbeitrag aus `berichte/2026-11-04-bch-tempnet-woche3-forum.md` heute Nachmittag selbst posten, alles unter der Zeile „Everything below this line is the post.“
- Den Branch `bericht/bch-tempnet-woche3-forum` löschen, wenn du willst. Mir hat GitHub das verweigert.
