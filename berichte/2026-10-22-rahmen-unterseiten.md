# Bericht 22.10.2026: Rahmen der Startseite für alle Unterseiten (PR 3)

Branch `design/rahmen-unterseiten`, PR #134, geöffnet im Sammelfenster am Fr 23.10.2026 um 16:00 Berlin. Vorher habe ich main gemergt: Die drei Seiten, die die Generatoren seit dem 22.10. neu geschrieben hatten (covenants, hashrate, smart-contracts), kommen aus main, der Rahmen ist darauf neu gesetzt. Kein Seitendatum weicht von main ab.

## Was gemacht wurde
- **Rahmen:** Alle 22 Unterseiten tragen jetzt den Rahmen der Startseite.
  - Kopf: der dunkle Balken mit der Wortmarke, dem Menü aus `MENUE` in `capture.js` und dem Knopf subscribe.
  - Fuß: neu die Kanal-Knöpfe und die Wortmarke.
  - Farben hell und dunkel, Schrift IBM Plex Sans und Archivo.
- **Inhalte bleiben gleich:** Kein Satz, keine Zahl und keine id, in die ein Generator schreibt, hat sich geändert. Die Blöcke der Generatoren zwischen AUTO-Marken sind von der Farbumstellung ausgenommen.
- **Gemeinsame Dateien:** `rahmen.css` (Farben, Schrift, Kopf, Fuß, Diagrammfarben über Attribut-Selektoren) und `rahmen.js` (Menü).
- **Neues Skript `scripts/rahmen.py`:** setzt den Rahmen und stellt die festen Farbwerte der Seiten auf Variablen um. Es lässt sich beliebig oft laufen und ändert beim zweiten Mal nichts. Dazu gibt es `--pruefen` und `--selbsttest`.
- **Anpassungen an bestehenden Skripten:**
  - `seo_seiten.py` hält das Menü im Kopf täglich auf dem Stand von `MENUE`. Der Rahmen zählt nicht zum Seitenstand, kein Seitendatum ist gesprungen.
  - `wortmarke.py`: Seiten mit `rahmen.css` gelten als hell-fähig, die Marke im Fuß folgt dem Look.
  - `weekly_pruefung.py` prüft das neue Menü.
  - `startseite.py`: `menue_html` markiert die eigene Seite.
- **Geprüft:**
  - Alle Selbsttests und Prüfungen sind grün, ebenso die Generatoren-Selbsttests.
  - Im Browser alle 22 Seiten, Handy 360 x 640 und Desktop, hell und dunkel: Keine Seite scrollt quer, und das Handy-Menü passt überall.
  - Der Secret-Scan ist sauber.
- **Bilder:** `docs/startseite/rahmen-handy-hell.png`, `rahmen-handy-dunkel.png`, `rahmen-diagramme-hell.png`.

## PR-Nummern
- PR 1 Startseite: #127, Nachbesserung #128, beide gemergt
- PR 2 Archiv und method: #131, gemergt
- PR 3 Rahmen: #134, offen

## Offene Fragen an Ben
1. **Textregeln auf den Unterseiten:** Mehrere Unterseiten verletzen die heutigen Textregeln, mit „right now“ und „live“ auf hashrate, mining, supply und entity x und mit Gedankenstrichen. Nach deiner Vorgabe bleiben die Inhalte in PR 3 unverändert. Soll ein eigener Text-PR je Seite folgen?
2. **Roter Selbsttest auf main:** `number_of_day_data.py --selbsttest` ist auf main rot, auch ohne PR 3. Die „now“-Wache aus #124 trifft eine feste Vorlage („the network now mints …“). Soll ich prüfen, ob das den täglichen Lauf von number-of-day betrifft, und einen Fix vorschlagen?

## Offen aus diesem Gespräch
3. **Jekyll und Markdown:** Das Repo hat weder `.nojekyll` noch `_config.yml`. GitHub Pages macht deshalb aus jeder Markdown-Datei eine öffentliche Seite, auch aus diesen Berichten und aus `docs/`, `deploy/` und `data/weekly-notes.md`. Ein `_config.yml` mit `exclude` würde sie aus der Website nehmen, auf GitHub blieben sie lesbar. Soll ich das als kleinen PR bauen?

## Was Ben tun muss
- #134 prüfen und mergen. Workflow-Dateien sind diesmal nicht betroffen.
- Die beiden Fragen oben beantworten.
