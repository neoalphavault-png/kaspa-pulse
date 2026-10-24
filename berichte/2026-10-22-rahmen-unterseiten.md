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

## Zweiter Merge mit main (24.10.2026)
Nach den Merges von #137, #138 und #135 hatte #134 Konflikte in `kaspa-hashrate.html`, `kaspa-covenants.html` und `kaspa-smart-contracts.html`.

- **Was main geändert hatte:** nur AUTO-Blöcke und Datenwerte, durch die Bots vom 24.10. (`seiten zahlen 2026-10-24`, `covenants log 2026-10-24`):
  - hashrate: `hashrate-satz`, `hashrate-wochen`, `seitenstand`
  - covenants: `kacheln`, `skala`, `stand`, `summe`, `tabelle`, `txchart`, `utxochart`, `seitenstand`
  - smart-contracts: `covenant-zahl`, `seitenstand`
- **Wie gelöst:** Die drei Seiten kommen aus main, `scripts/rahmen.py` hat den Rahmen darauf neu gesetzt. Der Rahmen (Kopf, Menü, Fuß, Farben hell und dunkel, Schrift) stammt aus diesem Branch, alle AUTO-Blöcke und Datenwerte aus main.
- **Nachgeprüft:**
  - Jeder AUTO-Block der drei Seiten ist zeichengleich mit main.
  - Kein Seitendatum weicht von main ab.
  - `_config.yml` aus #137 ist unverändert (kein Unterschied zu main).
- **Probebau:** mit `github-pages` 232. `berichte/`, `docs/` und `deploy/` sind nicht in der Ausgabe, `rahmen.css` ist dabei.
- **Angesehen:** hashrate, covenants und smart-contracts aus dem gebauten Stand, bei 390 px und 1280 px, hell und dunkel.
  - Keine Seite scrollt quer, `rahmen.css` ist überall geladen.
  - Die Zahlen von main stehen da: 386.9 PH/s am 24. Oktober, 17,479 Covenant-UTXOs am 23. Oktober, die Wochentabelle bis 12. Oktober.
- **Selbsttests, alle grün:**
  - `rahmen.py --selbsttest` und `--pruefen`
  - `seo_seiten.py --selbsttest` und `--pruefen`
  - `seo_pruefung.py --gegen origin/main` (0 Fehler)
  - `wortmarke.py pruefen` und `--selbsttest`
  - `startseite.py --selbsttest` und `--pruefen`
  - `archiv.py --selbsttest`
  - `weekly_pruefung.py --selbsttest`
  - `seiten_zahlen.py --selbsttest`
  - `covenants_page.py --selftest` und `--check` (20 Zahlen stimmen mit dem Log)
  - `entity_x_page.py --selftest`
  - `check_reads.py index.html`
  - `number_of_day_data.py --selftest`, seit #138 grün

## PR-Nummern
- PR 1 Startseite: #127, Nachbesserung #128, beide gemergt
- PR 2 Archiv und method: #131, gemergt
- PR 3 Rahmen: #134, offen
- dazwischen gemergt: #137 (Jekyll), #138 (Zahl des Tages), #135; offen: #139 (Jekyll-Folge)

## Offene Fragen an Ben
1. **Textregeln auf den Unterseiten:** beantwortet (Ben, 24.10.). Ein eigener Text-PR folgt nach dem Merge von #134, eine Seite pro Commit.
2. **Roter Selbsttest auf main:** erledigt mit #138 (Ben, 24.10.).

## Offen aus diesem Gespräch
3. **Jekyll und Markdown:** erledigt mit #137, Folge-PR #139.

## Was Ben tun muss
- #134 von Hand mergen. Workflow-Dateien sind nicht betroffen.
- Keine offenen Fragen mehr zu diesem PR.
