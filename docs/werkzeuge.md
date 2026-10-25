# Fremde Werkzeuge

Werkzeuge von außen kommen nur auf einem geprüften, festen Stand ins Repo. Sie folgen nie einem Branch von selbst. Ein neuer Stand braucht eine neue Prüfung durch Claude und einen neuen Eintrag hier.

## taste-skill

| | |
| --- | --- |
| Quelle | github.com/leonxlnx/taste-skill |
| Stand | **Commit `12af471f627f866411b4bd785b19646d3672784c`**, eingebunden am 25.10.2026 |
| Ordner | `skills/taste-skill/`, nur der Skill-Ordner aus dem Repo, unverändert, dazu der Lizenztext |
| Lizenz | MIT, Copyright (c) 2026 Leonxlnx, Text in `skills/taste-skill/LICENSE` |
| Prüfsummen | `docs/taste-skill.sha256`, eine SHA-256 je Datei |
| Wache | `python3 scripts/werkzeuge_pruefen.py` fällt durch, sobald eine Datei abweicht, fehlt oder dazukommt |
| Nicht auf der Website | `skills/` und `.taste-skill/` stehen in `exclude` in `_config.yml` |

### Was geprüft wurde (25.10.2026)
- **Skripte** (`scripts/*.mjs`, `scripts/lib/*.mjs`):
  - `cdp.mjs` startet nur einen lokalen Headless-Chrome mit einem Wegwerf-Profil, das danach gelöscht wird.
  - `inspect.mjs` stellt eine lokale Datei über einen Server auf 127.0.0.1 bereit, misst die Seite im Browser und schreibt Screenshots und `report.json` nach `.taste-skill/`.
  - `assets.mjs` sucht ohne API-Schlüssel bei Openverse, Wikimedia Commons, dem Art Institute of Chicago, dem Met, dem Internet Archive und der NASA und lädt nur auf `--get` herunter.
  - `draw.mjs` schreibt eine Verlaufsdatei nach `~/.taste-skill/history.json`.
  - Keine weiteren Prozesse, keine Telemetrie, keine Zugangsdaten, kein Zugriff auf Umgebungsvariablen außer Pfaden (`CHROME_PATH`, `HOME`, `TASTE_SKILL_TMP`, `TASTE_SKILL_HISTORY`).
- **Anweisungen** (`SKILL.md`, `references/*.md`): Gestaltungsregeln und Arbeitsablauf. Keine Anweisung, etwas zu installieren, zu senden oder Regeln zu umgehen.
- **Im Repo nicht übernommen:** Sponsor-Logos, Beispielbilder, Plugin-Manifeste, `install.sh` und die Workflow-Datei des Fremd-Repos.

### Wie wir ihn nutzen
1. **Unsere Marke geht vor:**
   - Schriften: Archivo 900, IBM Plex Sans 500/600, IBM Plex Mono.
   - Farben: #080B0F, #F2F5F4, #49EACB und ihre Abstufungen.
   - Kein Falke bei Kaspa Pulse.
2. **Was wir übernehmen:** Vom Skill nehmen wir nur Komposition, Typo-Größen, Abstände, Bildideen und die Prüfschleife (`inspect.mjs`, ansehen, beheben, wieder ansehen). Nie fremde Paletten oder Schriften aus `library/palettes.json` oder `library/type.json`.
3. **Unsere Regeln schlagen den Skill:**
   - Textregeln: kein Gedankenstrich, kein Doppelpunkt, kein Pfeil, kein Echtzeitwort. `references/copy.md` empfiehlt den Halbgeviertstrich für Bereiche, das gilt bei uns nicht.
   - Befunde des Inspektors, die der Marke widersprechen, sind keine Fehler, zum Beispiel „mono“ oder „font-count“ für IBM Plex Mono. Der Bericht nennt sie mit Begründung.
4. **Bilder** holen wir mit `skills/taste-skill/scripts/assets.mjs` nur mit `--license cc0,pd`. Jede Datei steht mit Quelle und Lizenz in `docs/hintergruende.md`.

### Aufruf
```
node skills/taste-skill/scripts/inspect.mjs index.html --out .taste-skill/inspect --widths 360,768,1440
node skills/taste-skill/scripts/assets.mjs "<suche>" --license cc0,pd
```
Braucht Node 22 und ein Chrome oder Chromium (`CHROME_PATH`). In der Cloud-Umgebung läuft Chromium als root und braucht `--no-sandbox`. Dafür genügt ein kleiner Starter außerhalb des Repos, der das Flag anhängt; der Skill selbst bleibt unverändert.
