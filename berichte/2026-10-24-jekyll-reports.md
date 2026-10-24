# Bericht 24.10.2026: Folge-PR zu #137, reports/ und die Schrift-README raus aus kaspapulse.com

Branch `fix/jekyll-reports`, kleiner Folge-PR von main nach #137 (Ben, 24.10.2026).

## Was gemacht wurde
- **Ausgenommen:** `_config.yml` nimmt zusätzlich `reports/` und `graphics/fonts/README.md` aus.
- **Bleibt öffentlich:**
  - `data/covenants/abgleich-2026-10-09/METHOD.md`, wie Ben entschieden hat: Die Methode gehört zu unserer Transparenz.
  - `graphics/fonts/LICENSE-OFL-1.1.txt`, denn die Lizenz gehört zu den Schriftdateien.
- **Vorher geprüft:** Keine öffentliche Seite verweist auf `reports/` oder auf die Schrift-README.
- **Probebau** mit `github-pages` 232, vorher und nachher:
  - Es fallen genau zwei Dateien weg: `reports/uhrwerk-roh-2026-10-19.md` und `graphics/fonts/README.md`.
  - Keine Datei kommt hinzu.
  - Alle übrigen Dateien bleiben Byte für Byte gleich.

## Abnahme von #137 nach dem Deploy
Trage ich unten nach, sobald Pages den Stand mit `_config.yml` ausgeliefert hat.

## Abnahme dieses PR nach dem Deploy
Trage ich nach dem Merge nach: 404 für `deploy/c2/`, `berichte/` und `reports/`.

## PR-Nummern
- #137 (Jekyll, gemergt), #138 (Zahl des Tages, gemergt)
- dieser PR: die Nummer trage ich beim Öffnen nach

## Offene Fragen an Ben
Keine.

## Was Ben tun muss
- Diesen PR prüfen und mergen.
