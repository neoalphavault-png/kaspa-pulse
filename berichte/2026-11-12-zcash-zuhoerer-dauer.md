# Zcash-Zuhörer als Dauerlauf „dauer“ (12.11.2026)

Ben am 12.11.: Kette wieder starten, Name „dauer“, Ende So 6.12.2026 00:00 UTC. Auswertung je Kalenderwoche, Meldung nach #ops-log bei Abriss. Bedarf: Zcash-Wochenbericht ab 22.11. und eine gemessene Vorher-Linie für die NU8-Debatte im Forum (Thread 59124).

<!-- discord -->
Zcash-Zuhörer läuft wieder als Kette „dauer“, gestartet am 12.11. um 21:36 UTC, Ende 6.12. 00:00 UTC. Wochenauswertung und Abriss-Wache als PR, du merged. Die erste volle Woche (16. bis 23.11.) ist am 22.11. noch nicht fertig. Am 22.11. trägt die Wochenzahl den Teil vom 12.11. 21:4x bis 16.11. 00:00 UTC. Bericht berichte/2026-11-12-zcash-zuhoerer-dauer.md
<!-- /discord -->

## Was gemacht ist

- **Kette gestartet:** am 12.11. um 21:36 UTC von hier aus, `zcash-mainnet-lauscher.yml` auf `main`, Lauf 43311949085. Eingaben `name=dauer`, `segment=1`, `dauer_min=330`, `ende_utc=2026-12-06T00:00:00Z`.
  - Die Endzeit steuert seit #303 allein die Kette. Der letzte Lauf wird so gekürzt, dass er um 00:00 UTC am 6.12. endet.
  - Rohdaten kommen nach `data/zcash-mainnet/lauscher-dauer/` auf `messung/zcash-mainnet`.
- **Wochenauswertung**, neu `scripts/zcash/lauscher_woche.py`, Selbsttest 7 von 7:
  - Je Kalenderwoche von Mo 00:00 bis Mo 00:00 UTC: Kettenblöcke, davon angekündigt, abgehängt, ohne Kopf, Tiefe 1, 2 und 3+, Abdeckung, vollständig ja oder nein.
  - Ankündigungen in den letzten 10 min vor der Kettenspitze zählen als „offen“, nicht als abgehängt.
  - Gegenprobe an den NU7-Läufen: 9.062 Kettenblöcke, 9.055 angekündigt, 52 abgehängt, 12 ohne Kopf, 40 mit Tiefe 1. Das ist genau der Endstand vom 10.11.
- **Workflow, PR (du merged):**
  - `zcash-mainnet-lauscher.yml` schreibt nach jeder Auswertung `wochen.csv` und `wochen.json` in den Ordner der Messreihe.
  - Neu `zuhoerer-kette-wache.yml`, stündlich zur Minute 41. Läuft kein Lauf, obwohl die Endzeit noch fern ist, und endete der letzte in der letzten Stunde, geht eine Meldung nach #ops-log. Sie nennt den Lauf, das Ergebnis und die Eingaben für den Start von Hand mit der nächsten Laufnummer. Einen Abriss meldet sie einmal.
  - Ohne Merge läuft die Kette trotzdem, nur Wochen-CSV und Meldung fehlen dann.

## Welches Fenster die erste Wochenzahl am 22.11. trägt

- Die Kette begann am 12.11. um 21:36 UTC. Die erste Woche, Mo 9.11. bis Mo 16.11., ist deshalb nur ab dem 12.11. abgedeckt (etwa 44 %, als nicht vollständig markiert).
- Die erste volle Woche ist Mo 16.11. 00:00 bis Mo 23.11. 00:00 UTC. Sie ist am So 22.11. noch nicht fertig.
- **Vorschlag für den Bericht am 22.11.:**
  - Die Wochenzahl trägt das Fenster 12.11. 21:4x bis 16.11. 00:00 UTC, genannt mit Abdeckung und als nicht volle Woche.
  - Die laufende Woche ab 16.11. kommt als Zwischenstand bis zum Zeitpunkt des Berichts dazu.
  - Die erste volle Woche (16. bis 23.11.) steht im Bericht am 29.11.

## Start von Hand, falls die Kette abreißt

Actions, „zcash mainnet lauscher“, Run workflow auf `main`:
- `name` = dauer
- `segment` = Zahl der Dateien `s*-meta.json` in `data/zcash-mainnet/lauscher-dauer/` plus 1
- `dauer_min` = 330
- `ende_utc` = 2026-12-06T00:00:00Z

Die Wache nennt die Laufnummer in ihrer Meldung.

## PR-Nummern

- dieser PR (Workflow, Skript, Bericht)
- #303, feste Endzeit, gemergt am 11.11.

## Offene Fragen an Ben

1. Passt der Vorschlag für die Wochenzahl am 22.11. (Teilwoche ab 12.11. plus Zwischenstand)?

## Was Ben tun muss

- Diesen PR prüfen und mergen, damit die Wochen-CSV und die Abriss-Meldung laufen.
