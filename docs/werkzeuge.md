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

## web-design-guidelines (Web Interface Guidelines)

| | |
| --- | --- |
| Skill | github.com/vercel-labs/agent-skills, Ordner `skills/web-design-guidelines`, **Commit `063bee94c3f4df8453406c830b0a7df0f2860278`** (kurz 063bee9, 28.08.2026) |
| Lizenz Skill | MIT laut README von agent-skills; das Repo hat an diesem Commit keine eigene LICENSE-Datei |
| Ordner | `skills/web-design-guidelines/`: `SKILL.upstream.md` unverändert, `SKILL.md` von uns angepasst |
| Regeln | `docs/web-interface-guidelines.md`, Kopie von `command.md` aus github.com/vercel-labs/web-interface-guidelines, **Commit `434b7f91364665f2f733b310ec54809bf8f37937`** (Stand von main am 25.10.2026), geholt am 25.10.2026 |
| Lizenz Regeln | MIT, Copyright (c) 2025 Vercel Labs, Text am Ende der Kopie |
| Prüfsummen | `docs/web-design-guidelines.sha256` für den Skill-Ordner, `docs/web-interface-guidelines.sha256` für die Regeln |
| Wache | `python3 scripts/werkzeuge_pruefen.py` deckt beides mit ab |

### Was wir angepasst haben
- Der Skill lud seine Regeln sonst bei jedem Lauf frisch von `raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`, also immer den aktuellen Stand von main. Dieser Stand ist ungeprüft.
- Unser `SKILL.md` liest nur die Kopie `docs/web-interface-guidelines.md` und verbietet das Nachladen. Sonst ist nichts geändert, das Original liegt als `SKILL.upstream.md` daneben.
- Die Kopie ist byte-gleich mit `command.md` an Commit 434b7f9 (SHA-256 im Kopf der Datei). Davor steht ein Kopf mit Quelle, Datum, Commit und Lizenz, danach der Lizenztext. Ein neuer Stand kommt nur nach Prüfung durch Claude.

### Was geprüft wurde (25.10.2026)
- `command.md` enthält nur Prüfkriterien für UI-Code und ein Ausgabeformat (`datei:zeile`). Es fordert nichts, was über das Prüfen von Code hinausgeht: kein Netzwerk, keine Installation, keine Änderung an Dateien, kein Posten. Nichts davon war zu melden.
- **Regeln, die mit unserer Marke kollidieren.** Hier gehen Marke und Textregeln vor; der Bericht nennt sie als „bleibt“:
  - „Title Case for headings/buttons“: unser Hausstil ist klein geschrieben
  - „Second person; avoid first person“: wir schreiben „we count“, „our series“
  - „Curly quotes“: in unseren Texten stehen keine Anführungszeichen im Fließtext
  - „Intl.DateTimeFormat statt fester Formate“: unsere Seiten sind fertig gebaut, das Datumsformat „19 oct 2026“ ist Hausstil
  - Das Beispiel im Ausgabeformat nutzt Pfeile („→“); in unseren Berichten stehen keine

## Ablauf bei jedem Seiten-PR (Ben, 25.10.2026)
1. Gestaltung nach dem Taste Skill: `inspect.mjs` bei 360, 768 und 1440 px, ansehen, beheben, wieder ansehen. Die Marke geht vor.
2. Dann Prüfung gegen die Web Interface Guidelines (`skills/web-design-guidelines`, Regeln aus `docs/web-interface-guidelines.md`).
3. Befunde als Liste `datei:zeile` im Bericht, je mit „behoben“, „bleibt“ (mit Grund) oder „Vorschlag“.
4. Die Fixes kommen im selben PR. Textregeln gelten weiter.
