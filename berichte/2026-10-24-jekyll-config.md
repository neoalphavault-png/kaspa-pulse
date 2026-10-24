# Bericht 24.10.2026: Markdown und Server-Dateien raus aus kaspapulse.com

Branch `fix/jekyll-config`, eigener kleiner PR von main. Er wird vor #134, #135 und #136 gemergt (Ben, 24.10.2026).

## Befund vorher
- **Pages baut mit Jekyll:** GitHub Pages baut das Repo klassisch mit Jekyll, ohne eigenen Deploy-Workflow. Es gab weder `_config.yml` noch `.nojekyll`.
- **Was öffentlich war:** Am 24.10. lieferte kaspapulse.com mit Status 200 aus:
  - den Zcash-Bericht unter `/berichte/2026-10-23-zcash-mainnet.html`, `.md` und ohne Endung
  - `/docs/cheat-sheet.html`
  - `/data/weekly-notes.html`
  - die Server-Skripte unter `/deploy/c2/`, zum Beispiel `setup.sh` und die credstore-Hilfen
- **Keine Verweise:** Keine öffentliche Seite verlinkt in `berichte/`, `docs/` oder `deploy/`. Die einzige Erwähnung von `data/weekly-notes.md` steht in einem Code-Kommentar in `index.html`.

## Was gemacht wurde
- **`_config.yml`:**
  - mit `exclude` für `berichte/`, `docs/`, `deploy/`, `CLAUDE.md` und `data/weekly-notes.md`
  - dazu die eingebaute Ausnahmeliste von Jekyll 3; `exclude` ersetzt diese Liste, deshalb steht sie mit drin
  - sonst keine Einstellung, nichts an der Verarbeitung der Seiten geändert
- **Probebau:** Mit `github-pages` 232 (dem Stack von GitHub Pages) habe ich lokal zweimal gebaut, ohne und mit der neuen Datei, und die Ausgaben verglichen:
  - vorher 329 Dateien, nachher 287
  - es fallen genau die 42 Dateien in `berichte/`, `docs/`, `deploy/` und `data/weekly-notes.md` weg
  - keine Datei kommt hinzu
  - jede verbleibende Datei ist Byte für Byte gleich
  - Startseite, `/archive/`, `/method/`, die Wochenseiten, entity-x, Impressum, Datenschutz, `CNAME`, `robots.txt`, `sitemap.xml`, `capture.js`, die JSON-Dateien unter `data/`, die Schriften und die Kurzlinks entsprechen dem Repo

## PR-Nummern
- dieser PR: #137
- danach: #134 (Rahmen), #135, #136

## Abnahme nach dem Deploy
- `https://kaspapulse.com/berichte/2026-10-23-zcash-mainnet.html` (auch `.md` und ohne Endung) gibt 404.
- Ebenso `/docs/cheat-sheet.html`, `/data/weekly-notes.html` und `/deploy/c2/setup.sh`.
- Startseite, `/archive/`, `/method/`, eine Wochenseite, `/entity-x.html`, `/impressum.html` und `/datenschutz.html` geben 200 und sehen aus wie vorher.

Ich prüfe das nach dem Merge selbst und trage das Ergebnis hier nach.

## Offene Fragen an Ben
1. **Weitere Markdown-Dateien:** Drei Markdown-Dateien liegen außerhalb der genannten Pfade und bleiben damit öffentlich: `data/covenants/abgleich-2026-10-09/METHOD.md`, `graphics/fonts/README.md` und `reports/uhrwerk-roh-2026-10-19.md`. Sollen sie auch in `exclude`? `reports/` enthält Rohdaten des Uhrwerks.

## Was Ben tun muss
- Diesen PR prüfen und vor #134, #135 und #136 mergen.
- Die Frage oben beantworten.
