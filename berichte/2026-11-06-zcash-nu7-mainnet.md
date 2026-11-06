# Zcash NU7 Mainnet aktiviert, Kurznotiz (6.11.2026)

Ben hat am 23.10. eine Kurznotiz binnen 24 h nach der Aktivierung beauftragt. Maßgeblich ist die Schätzung vom 4.11. (computed, `stand-2026-11-04`, `scripts/wache/ketten/zcash-mainnet.json`, #254).

## Aktivierung gegen die Schätzung vom 4.11.

| | Wert |
|---|---|
| Block 3.543.405, Kopfzeit (counted, eigene Köpfe) | **6.11.2026 02:34:02 UTC** |
| erste Sicht bei unserem Zuhörer (counted) | 02:34:10,897 UTC, 8,9 s nach der Kopfzeit |
| Schätzung 4.11. (computed) | Median 02:40:58 UTC, 90-%-Band 01:14:45 bis 04:07:28 UTC |
| im 90-%-Band | **ja** |
| Abweichung zum Median | **−6,9 min**, also früher als der Median |

**Track Record, frühere Stände** (nicht maßgeblich):

| Stand | Median (computed) | 90-%-Band | Abweichung | im Band |
|---|---|---|---:|---|
| 23.10. | 02:21:52 | 5.11. 22:02:16 bis 6.11. 06:40:25 | +12,2 min | ja |
| 28.10. | 02:26:16 | 5.11. 23:01:22 bis 6.11. 05:51:31 | +7,8 min | ja |
| 2.11. (Prüfung, 7 Tage) | 02:39:52 | 00:28:23 bis 05:00:17 | −5,8 min | ja |
| Zakura (laut Ben, source) | 00:50:00 | kein Band | +104,0 min | entfällt |

Positiv heißt, der Block kam später als geschätzt.

## Erste Zahlen ab NU7

Quelle ist der Stand `stand-2026-11-06` auf `messung/zcash-mainnet`, Lauf von Hand mit `stand=true`, Bot-Commit `a3a1814`.
- Abruf 05:13:54 UTC, Spitze 3.543.655.
- Gegenprobe mit zwei Zebra-7.0.0-Peers, je 500 von 500 Hashes gleich.
- Keine IPs und keine Hostnamen im Stand.
- Discord-Entwurf: `ph-entwurf-zcash-mainnet.yml` lief grün (Run 42167772834).

**250 Abstände, Blöcke 3.543.406 bis 3.543.655:**

| Kennzahl | counted | computed für 25 s |
|---|---:|---:|
| Mittel | 38,21 s | 25 s |
| Median | 25,0 s | 17,3 s |
| p90 | 85,1 s | 57,6 s |
| p99 | 162,6 s | 115,1 s |
| Anteil über 75 s | 13,2 % | 4,98 % |
| Anteil über 173 s | 0,8 % | 0,1 % |
| längste Lücke | 249 s vor Block 3.543.445 (03:11:24 UTC) | 152 s |
| negative Abstände | 0 | 0 |

**Einpendeln:** Die Schwierigkeit liegt bei Block +1 bei 0,794 des Werts vor NU7, bei +10 bei 0,767 und bei +100 bei 0,504. An der Spitze sind es 0,417. Bei gleicher Hashrate wären 0,333 zu erwarten (computed). Die Blockzeit ist noch nicht eingependelt: Das Mittel liegt bei 38 s statt 25 s, weil die Schwierigkeit noch über dem Gleichgewicht steht. Die CSV mit den Abständen heißt `zcash-mainnet-nu7-intervals-2026-11-06.csv`.

**Header-Client:** Er verbindet sich auch nach NU7 mit Peers auf Protokoll 170190. Kein Peer hat sich wegen NU7 getrennt.

## Zuhörer (GitHub)

- **Die Kette läuft ohne Lücke:**
  - Lauf 1: 5.11. 17:02 bis 22:32 UTC
  - Lauf 2: 22:26 bis 6.11. 03:56 UTC
  - Lauf 3: seit 03:49 UTC
- **Abdeckung:** 643,9 min.
- **Verbindungen über alle Läufe:** 24 zu Zebra, 48 zu Zakura. Lauf 2 hielt auch nach NU7 Verbindungen zu beiden.
- **Stand bis 6.11. 03:56 UTC:**

  | | Kettenblöcke | angekündigt | abgehängt |
  |---|---:|---:|---:|
  | vor NU7 | 453 | 453 | 0 |
  | ab NU7 | 111 | 110 | 1 (0,90 %) |

- **Der abgehängte Block:** Höhe 3.543.512, Tiefe 1. Ein einzelner Zakura-Peer hat ihn um 03:56:03 UTC angekündigt. Die Kette hat auf dieser Höhe einen anderen Block mit demselben Vorgänger.

## Problem: Die Upgrade-Wache auf c2 hängt seit 02:54 UTC

- **Was das Log zeigt:**
  - Die Wache hat die Aktivierung um 02:34 UTC richtig gesehen.
  - Ihre Probe zur Aktivierung zählte 7,1 % der Peers unter Protokoll 170190.
  - Seit Block 3.543.431 (Kopfzeit 02:54:12 UTC) wächst ihre Spitze nicht mehr: um 03:29:52 und 04:29:52 UTC weiter Höhe 3.543.431, bei 16 Verbindungen.
- **Folge:** Der Alarm „blockpause“ von 03:04:52 UTC ist ein **Fehlalarm**. Die Kette lief in dieser Zeit weiter, die längste echte Lücke war 249 s. Eine Entwarnung kam nicht, weil die Wache selbst keinen neuen Block mehr sieht.
- **Vermutung, nicht belegt:** Ankündigungen kommen an, aber Köpfe ohne bekannten Vorgänger brauchen einen neuen Anker über den Header-Client, und dieser Abruf scheitert oder hängt. Die Ursache steht im Journal auf c2, das ich nicht sehe.
- **Auswirkung auf den Report am 9.11.:**
  - M3, M4 und die Probe bei +6 h (fällig 08:34 UTC) brauchen eine laufende Wache.
  - M1, M2 und M6 kommen aus den Köpfen und sind nicht betroffen.
  - M7 erste Sicht kann aus dem Zuhörer kommen.

## Offene Fragen an Ben

1. Ist ein Neustart der Wache für dich in Ordnung? Der Zustand mit Aktivierungszeit und Proben bleibt in `zustand.json` erhalten. Mit dem Neustart verankert die Wache neu.
2. Soll ich die Ursache nach dem Journal suchen und einen Fix vorbereiten? Der Fix wäre ein eigener PR, Code in `scripts/wache/`.

## Was Ben tun muss

1. **Auf c2, möglichst vor 08:34 UTC:**
   ```
   journalctl -u upgrade-wache@zcash-mainnet --since "2026-11-06 02:50" | grep -iE "anker|fehler|error" | tail -30
   sudo systemctl restart upgrade-wache@zcash-mainnet
   ```
   Die Ausgabe der ersten Zeile bitte schicken. Sie enthält keine Adressen, die Wache loggt nur Höhen und Fehlertypen.
2. pulsehawk-site PR #65 mit der CSV prüfen und mergen.
