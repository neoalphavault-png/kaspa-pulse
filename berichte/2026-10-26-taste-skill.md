# Bericht 26.10.2026: Taste Skill eingebunden (gepinnt), Startseite geprüft

Zwei PRs, beide von main:
- **Werkzeug**, Branch `tools/taste-skill`: der Skill, die Pin-Wache und dieser Bericht.
- **Startseite**, Branch `design/startseite-taste`: die Änderungen an der Startseite mit Vorher-Nachher-Bildern.

## Was gemacht wurde
- **Skill gepinnt:**
  - `skills/taste-skill/` steht auf genau Commit `12af471f627f866411b4bd785b19646d3672784c` von github.com/leonxlnx/taste-skill, unverändert, dazu der MIT-Lizenztext.
  - Der Commit-Hash steht in `docs/werkzeuge.md`.
  - `docs/taste-skill.sha256` hält jede Datei fest, `scripts/werkzeuge_pruefen.py` fällt bei jeder Abweichung durch. Ein Update geht also nur mit neuer Prüfung.
- **Vorher geprüft:** alle Skripte und Anweisungen gelesen. Der Skill startet nur einen lokalen Headless-Chrome und sucht Bilder in offenen Archiven ohne Schlüssel. Er sendet nichts und liest keine Zugangsdaten. Details in `docs/werkzeuge.md`.
- **Nicht auf der Website:** `skills/` und `.taste-skill/` stehen in `exclude` in `_config.yml`, sonst hätte Jekyll SKILL.md und die Skripte auf kaspapulse.com ausgeliefert. `.taste-skill/` steht zusätzlich in `.gitignore`.
- **Marke vor Skill:** in `docs/werkzeuge.md` festgehalten. Wir übernehmen nur Komposition, Typo-Größen, Abstände, Bildideen und die Prüfschleife, nie fremde Paletten oder Schriften. Unsere Textregeln schlagen `references/copy.md`, das Gedankenstriche empfiehlt.
- **Bilder:** In diesem Durchgang ist kein Bild dazugekommen. Der Weg für später steht fest: `assets.mjs --license cc0,pd`, jede Datei mit Quelle und Lizenz in `docs/hintergruende.md`.

## Startseite, Befunde von `inspect.mjs` (360, 768, 1440 px)
Geprüft wurde `index.html` aus main, derselbe Stand wie auf kaspapulse.com. Die Datei kam über den lokalen Server des Skills: Die Live-Seite über den Proxy der Cloud hätte nur mit abgeschalteter TLS-Prüfung geladen.

**Vorher:** 10 FAIL, 6 WARN. **Nachher:** 9 FAIL, 6 WARN. Behoben sind alle Befunde, die echte Mängel innerhalb unserer Marke waren.

| Befund | Was der Skill meldet | Entscheidung |
| --- | --- | --- |
| contrast | Akzent #0F9A80 auf hellem Grund 2.9 bis 3.1:1 („40.68% below“, „next“, Chips), Anmeldeknopf 3.1:1 | **behoben**, Akzent als Textfarbe #0B6B59 (5.7:1), Knopf ebenso |
| palette-terracotta | Text #C2553A | **behoben**, keine Markenfarbe; negative Werte stehen im Grauton der Seite |
| small-text | 24 Textblöcke unter 13 px | **behoben**, kleinste Schrift jetzt 13 px |
| no-title | kein sichtbares h1 | **behoben**, die Zeile der Zahl der Woche ist jetzt das h1, gleiche Größe |
| size-count | 10 Schriftgrößen | nebenbei besser, 12 px fällt weg |
| contrast „PULSE“ | Wortmarke im Fuß 3.1:1 | **bleibt**, ein Logo ist von der Kontrastregel ausgenommen |
| mono, font-count, micro-label | IBM Plex Mono außerhalb von Code, drei Schriften | **bleibt**, IBM Plex Mono gehört zur Marke |
| off-centre | Ränder 356 und 325 px bei 1440 | **Fehlmeldung**: der Inhalt sitzt mittig (340 und 340 px); gemessen wurde die Navigation im eigenen Container |
| no-title @360 | h1 nicht im ersten Bild | **Fehlmeldung**: der Skill misst bei 360 px einen nur 225 px hohen Ausschnitt; auf einem Telefon steht das h1 im ersten Bild |
| headline-lines | „fees paid 0.13% of miner revenue …“ drei Zeilen bei 360 px, h1 drei Zeilen bei 768 | Vorschlag 1 |
| eyebrow | „1 / 5 · the chain“ und „share on x“ über den Überschriften | Vorschlag 2 |
| hairline, outlined-box | 8 Trennlinien, 5 umrandete Kästen | Vorschlag 3 |
| few-pictures, no-footage | keine Bilder, kein Video | Vorschlag 4 |
| still-page | wenig Bewegung | Vorschlag 5 |
| small-title | h1 nur 26 px | Vorschlag 1 |

**Vorschläge an Ben** (nicht umgesetzt, weil sie die Gestaltung verändern):
1. **Überschriften kürzer:** Überschriften der Schritte auf höchstens zwei Zeilen bei 360 px, den Rest in den Satz darunter. Das h1 größer setzen (32 bis 40 px) und dafür kürzer fassen. Das betrifft die Satzvorlagen in `startseite.py`.
2. **Schrittnummer und „share on x“:** Die Nummer „1 / 5 · the chain“ in die Fortschrittsleiste ziehen und „share on x“ unter den Absatz stellen statt über die Überschrift.
3. **Linien und Kästen:** Linien zwischen den Schritten durch Abstand oder Tonwechsel ersetzen, die Kästen der Diagramme ohne Rand, nur mit Fläche.
4. **Bilder:** Bilder aus offenen Archiven (cc0 oder public domain), etwa Mining-Hardware oder historische Rechenmaschinen, je eins pro Schritt, mit Credit. Vor dem Laden schlage ich Motive vor und frage, weil das den Charakter der Seite ändert.
5. **Bewegung:** eine dezente Einblendung pro Schritt, nur transform und opacity, mit Rückfall für reduzierte Bewegung. Das gibt es zum Teil schon (`.rv`).

**Vorher-Nachher:** `docs/startseite/taste-vergleich-360.png`, `-768.png` und `-1440.png` im Startseiten-PR.

**Geprüft im Startseiten-PR, alles grün:**
- `startseite.py --selbsttest` und `--pruefen`
- `archiv.py --selbsttest`, `check_reads.py index.html`
- `seo_pruefung.py --gegen origin/main` (0 Fehler)
- `weekly_pruefung.py --selbsttest`, `wortmarke.py pruefen`
- Secret-Scan

Dieselbe Kopfzeile tragen Archiv, `/method/` und die Wochenseiten. Sie haben dieselben Änderungen bekommen; jede Seite hat genau ein h1.

## pulsehawk.io, Vorschlag (nicht umgebaut)
Die Seite habe ich als einzelne HTML-Datei geladen und mit demselben Inspektor geprüft. Schriften und das Falken-Bild lagen dabei nicht vor; „font-fallback“ und „broken-image“ kommen nur davon.

Ergebnis: 11 FAIL, 9 WARN. Die wichtigsten Befunde für die eigene Marke mit Falke:
- **Hero-Überschrift:** „Independent blockchain measurement under load“ bricht bei 360, 768 und 1440 px auf vier Zeilen. Der erste Bildschirm hat kein dominantes Element, die größte Schrift ist 46 px.
- **Kein Knopf im ersten Telefon-Bildschirm.**
- **Fließtext 14.5 px**, zwei Textblöcke unter 13 px.
- **9 umrandete Kästen**, zwei Reihen gleicher Karten.
- **Ränder ungleich** bei 768 px (20 und 42 px), dazu eine leere Strecke von 120 px bei 360 px.
- **IBM Plex Mono** für Labels. Ob das zur PulseHawk-Marke gehört, entscheidest du.

**Vorschlag:** derselbe Durchgang wie hier, im Repo pulsehawk-site, mit eigener Prüfung der PulseHawk-Marke (Falke, Farben, Schriften): erst die Befundliste, dann ein PR mit Vorher-Nachher. **Ich warte auf deine Freigabe.**

## Ergänzung 25.10.2026: Web Interface Guidelines

### Was eingebunden wurde (Werkzeug-PR #145)
- **Skill:** `skills/web-design-guidelines/` aus github.com/vercel-labs/agent-skills, Commit `063bee94c3f4df8453406c830b0a7df0f2860278` (063bee9). Das Original liegt als `SKILL.upstream.md` daneben.
- **Regeln, einmal geholt:** `docs/web-interface-guidelines.md` ist `command.md` aus github.com/vercel-labs/web-interface-guidelines, Commit `434b7f91364665f2f733b310ec54809bf8f37937`, geholt am 25.10.2026. Quelle, Datum, Commit, Lizenz und SHA-256 stehen im Kopf der Datei.
- **Skill angepasst:** Das Original lädt die Regeln bei jedem Lauf frisch von main. Unser `SKILL.md` liest nur die Kopie im Repo und darf nichts nachladen.
- **Gepinnt:** `docs/web-design-guidelines.sha256` und `docs/web-interface-guidelines.sha256`. `scripts/werkzeuge_pruefen.py` prüft beide und fällt bei jeder Änderung durch, also auch dann, wenn jemand die Regeln ohne Prüfung austauscht.
- **Nicht auf der Website:** liegt unter `skills/` bzw. als Doku, `skills/` steht schon in `exclude`.
- Der Eintrag steht in `docs/werkzeuge.md`, dazu der neue Ablauf für Seiten-PRs.

### Prüfung der Regeln
- **Nichts über das Prüfen von Code hinaus.** `command.md` enthält nur Prüfkriterien für UI-Code und ein Ausgabeformat. Es fordert kein Netzwerk, keine Installation, kein Schreiben, kein Posten; zu melden war nichts davon. Das einzige Nachladen stand im Skill selbst (frisch von main) und ist abgestellt.
- **Regeln gegen unsere Marke.** Hier gehen Marke und Textregeln vor:
  - Title Case für Überschriften und Knöpfe: unser Hausstil ist klein
  - „second person, avoid first person“: wir schreiben „we count“
  - typografische Anführungszeichen
  - `Intl.DateTimeFormat` statt fester Datumsformate: unsere Seiten sind fertig gebaut, „19 oct 2026“ ist Hausstil
  - Pfeile im Ausgabeformat: in unseren Berichten stehen keine
- **Lizenz:** agent-skills hat an Commit 063bee9 keine LICENSE-Datei, MIT steht nur in der README. web-interface-guidelines hat eine LICENSE (MIT, Vercel Labs), der Text steht am Ende der Kopie.

### Erster Lauf an der Startseite (zusammen mit dem Taste-Test)
Reihenfolge wie künftig bei jedem Seiten-PR: erst die Gestaltung nach dem Taste Skill (oben), dann die Prüfung gegen die Guidelines. Die Fixes stehen im Startseiten-PR #146 als zweiter Commit (2c1fa8d). Zeilen beziehen sich auf den Stand vor den Fixes. `startseite.py` baut auch Archiv, `/method/` und die Wochenseiten, die Fixes gelten dort ebenso.

| Datei:Zeile | Befund | Status |
| --- | --- | --- |
| index.html:222 | kein Link zum Überspringen der Navigation | behoben, „skip to content“ als erstes Element |
| index.html:245 | `<main>` ohne Sprungziel | behoben, `id="main"` |
| index.html:282 | E-Mail-Feld ohne `autocomplete="email"` und `spellcheck="false"`, Platzhalter ohne Beispiel | behoben, mit `aria-label`, Platzhalter „you@example.com“ |
| index.html:314 | dasselbe Feld im zweiten Formular | behoben |
| scripts/startseite.py:661 | Vorlage des Felds | behoben, daher in allen Seiten gleich |
| index.html:5 | kein `theme-color` | behoben, #080B0F |
| index.html:83 | kein `color-scheme`, kein `touch-action: manipulation`, keine Tap-Farbe | behoben, `color-scheme` folgt dem Umschalter hell und dunkel, Tap-Farbe in #49EACB |
| index.html:109 | Menü auf dem Telefon ohne `overscroll-behavior: contain` | behoben |
| index.html:127 | `.next` ohne Hover-Zustand | behoben |
| index.html:155 | `.bridge a` ohne Hover-Zustand | behoben |
| index.html:200 | `footer a` ohne Hover-Zustand | behoben |
| index.html:225 | Wortmarke im Kopf ohne `translate="no"` | behoben |
| index.html:342 | Wortmarke im Fuß ohne `translate="no"` | behoben |
| index.html (alle Überschriften) | kein Title Case | bleibt, Hausstil klein |
| index.html (Fließtext) | erste Person „our“ | bleibt, Markenstimme |
| index.html (Datumsangaben) | feste Datumsformate | bleibt, fertig gebaute Seite, Hausstil |
| index.html:83 | kein `overscroll-behavior: none` für die ganze Seite | bleibt, das Federn der Seite ist gewollt |
| index.html (Fokus) | Fokusrahmen | in Ordnung, der Rahmen des Browsers bleibt; `scroll-padding-top` hält Ziele unter dem festen Kopf frei |
| index.html (Anmeldeknopf) | Knopf nur während der Anfrage gesperrt | in Ordnung |
| index.html (`.msg`) | Rückmeldung mit `role="status"` | in Ordnung, wird vorgelesen |

Danach habe ich wieder geprüft:
- `inspect.mjs` meldet weiter 9 FAIL und 6 WARN, dieselben Befunde wie nach den Taste-Fixes
- `startseite.py --selbsttest` und `--pruefen`, `archiv.py --selbsttest`, `seo_pruefung.py --gegen origin/main` (0 Fehler), `wortmarke.py pruefen` und der Secret-Scan sind grün

### Ablauf ab jetzt bei jedem Seiten-PR
1. Gestaltung nach dem Taste Skill bei 360, 768 und 1440 px.
2. Prüfung gegen die Guidelines.
3. Befunde als Liste Datei:Zeile im Bericht.
4. Fixes im selben PR.

Festgehalten in `docs/werkzeuge.md`.

## PR-Nummern
- Werkzeug: #145 (Taste Skill, Web Interface Guidelines, Pin-Wache, dieser Bericht)
- Startseite: #146 (Taste-Fixes 8a3ba80, Guidelines-Fixes 2c1fa8d)

## Offene Fragen an Ben
1. Welche der fünf Vorschläge für die Startseite soll ich umsetzen?
2. Darf ich pulsehawk.io im Repo pulsehawk-site so prüfen und einen PR vorbereiten?
3. Der helle Akzent als Textfarbe ist auf der Website jetzt #0B6B59, in den Grafiken aus #144 #085042. Beide sind dunkler als #0F9A80, gleicher Farbton. Soll ich beide auf einen Wert bringen?

## Was Ben tun muss
- Beide PRs prüfen und mergen; Workflow-Dateien sind nicht betroffen.
- Ein neuer Stand der Guidelines kommt nur über einen PR, den Claude geprüft hat; `werkzeuge_pruefen.py` hält sonst jede Änderung auf.
- Die drei Fragen beantworten.
