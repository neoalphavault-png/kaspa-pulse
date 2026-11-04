# Zcash Mainnet, Wochenstand 4.11.2026 (letzter vor NU7)

Auftrag von Ben am 23.10.: jeden Mittwoch bis zur Aktivierung ein Wochenstand. Dazu kommt die Upgrade-Wache aus dem Auftrag vom 29.10.

## Was gemacht ist

- **Wochenstand:** `data/zcash-mainnet/stand-2026-11-04.json` und `.md` liegen auf `messung/zcash-mainnet`. Sie kommen aus dem geplanten Lauf [41835014270](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41835014270), der grün lief, Bot-Commit `26d9aa5`. Ein Lauf von Hand war nicht nötig.
- **Abruf:** 13:10:12 UTC, Spitze 3.541.609 um 13:05:01 UTC.
  - Peer-Software: Zakura 1.7.0, Zebra 7.0.0, Zakura 1.8.2.
  - Gegenprobe: diesmal nur ein Peer (Zebra 7.0.0, 500 von 500 Hashes gleich). Am 28.10. waren es zwei.
- **Adressen:** keine IPs und keine Hostnamen im Stand.
- **Entwurf:** `ph-entwurf-zcash-mainnet.yml` lief grün ([41836073993](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41836073993)), Schritt „entwurf bauen und senden“ erfolgreich.

## Kennzahlen gegen 75 s

51.892 Abstände, Blöcke 3.489.718 bis 3.541.609.

| Kennzahl | counted | computed |
|---|---:|---:|
| Mittel | 75,35 s | 75 s |
| Median | 53,0 s | 52,0 s |
| p90 | 172,0 s | 172,7 s |
| p99 | 349,0 s | 345,4 s |
| Anteil über 225 s | 5,03 % | 4,98 % |
| Anteil über 518 s | 0,129 % | 0,1 % |
| längste Lücke | 930 s vor Block 3.524.451 am 20.10. | 858 s |

## Vorhersage für Höhe 3.543.405

Noch 1.796 Blöcke. Tempo der letzten 14 vollen Tage 75,35 s, Tagesmittel 74,8 bis 75,7 s.

| Stand | Spitze | Median | 90-%-Band | Breite | mit genau 75 s |
|---|---:|---|---|---:|---|
| 23.10. | 3.527.841 | 6.11. 02:21:52 | 5.11. 22:02:16 bis 6.11. 06:40:25 | 8,6 h | 6.11. 01:04:15 |
| 28.10. | 3.533.510 | 6.11. 02:26:16 | 5.11. 23:01:22 bis 6.11. 05:51:31 | 6,8 h | 6.11. 01:37:27 |
| 4.11. | 3.541.609 | **6.11. 02:40:58** | **6.11. 01:14:45 bis 04:07:28** | 2,9 h | 6.11. 02:30:01 |

Der Median ist von Stand zu Stand um 19 min nach hinten gewandert, das Band ist von 8,6 h auf 2,9 h geschrumpft. Alle Zeiten sind computed. Zum Vergleich: Die Prüfung vom 2.11. aus 7 Tagen ergab 02:39:52 mit Band 00:28:23 bis 05:00:17 (`berichte/2026-11-02-nu7-hoehe-pruefung.md`).

## Upgrade-Wache

1. **erwartet_utc:** steht auf dem neuen Median 6.11. 02:40:58 UTC mit Band 01:14:45 bis 04:07:28 UTC. Erledigt mit [PR #254](https://github.com/neoalphavault-png/kaspa-pulse/pull/254), Squash-Merge `49a7734`, Quelle im Feld `_quelle`. Die untere Bandgrenze liegt 1,4 h vor dem Median, also nicht mehr als 20 h; die Regel „untere Grenze minus 4 h“ greift deshalb nicht.
2. **Läuft die Wache auf c2?** Ja.
   - `wache/wache-log.csv` auf `messung/zcash-mainnet` hat 48 stündliche Zeilen „ruht“ seit 2.11. 16:12 UTC.
   - Die letzte Zeile ist von 13:55:57 UTC, mit 12,7 h bis zum Fenster.
   - Der Sync zur Minute 23 läuft.
   - Die Wache auf c2 rechnet noch mit 02:39:52 vom 2.11. Ihr Fenster beginnt damit am 5.11. um 02:39:52 UTC, 66 s früher als nach dem Stand auf `main`. Für die Messung spielt das keine Rolle.

## Termine angepasst

- **Kurznotiz am 6.11.:** Die Prüfung beginnt um 05:10 UTC statt 09:00 UTC, also Obergrenze des Bands plus 1 h. Fehlen dann noch 100 NU7-Blöcke, prüft sie alle 2 h erneut.
- **Prüfung „Fenster offen?“ am 5.11. 03:40 UTC:** auf den Fensterbeginn 02:40 UTC angepasst.

## Offene Fragen an Ben

1. Die Gegenprobe lief diesmal nur mit einem Peer. Reicht das für den letzten Stand vor NU7, oder soll ich einen Lauf mit `stand=false` nachschieben, in der Hoffnung auf zwei Gegenproben?

## Was Ben tun muss

Nichts Dringendes. Wer will, startet die Wache vor dem 5.11. 02:39 UTC mit `sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet` neu, damit sie die Schätzung vom 4.11. lädt.
