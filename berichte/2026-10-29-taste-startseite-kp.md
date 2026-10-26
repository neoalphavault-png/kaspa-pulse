# Bericht 26.10.2026: Startseite kaspapulse.com mit dem Taste Skill

Auftrag vom 26.10.2026, Frist Do 29.10.2026 18:00 Berlin.

Ablauf nach `docs/werkzeuge.md`:
1. Gestaltung nach dem Taste Skill, fest auf Commit 12af471
2. Prüfung gegen die Web Interface Guidelines
3. Befunde als Datei:Zeile, Fixes im selben PR

Die Marke geht vor:
- **Schriften:** Archivo 900, IBM Plex Sans, IBM Plex Mono
- **Farben:** #080B0F, #F2F5F4, #49EACB
- kein Falke

Claude prüft, Ben merged.

## Was gemacht wurde
- **Audit:** `inspect.mjs` in 390, 768 und 1440 px für:
  - die Startseite
  - `/kaspa-weekly.html`
  - drei Unterseiten

  Den Plausible-Screenshot hatte ich nicht. Deshalb die Ersatzliste aus dem Auftrag: kaspa-covenants, kaspa-mining, kaspa-supply.
- **PR 1, nur die Startseite.** Branch `design/startseite-spitze`, PR #147. Er baut auf #146 auf und enthält dessen zwei Commits.
- **Erstes Bild neu.** Es ist in beiden Looks dunkel wie der Kopf.
  - **Links:** das Versprechen als h1, darunter die Anmeldung.
    - h1: „kaspa in 6 numbers, every monday“
    - darunter: „block rate, miner fees, emission, holders and addresses, each with its date and source. one free mail every monday, the next on 2 nov.“
  - **Rechts:** die Zahl der Woche in #49EACB. Auf dem Telefon steht sie unter der Anmeldung.
  - **5-Sekunden-Test:** Wer ankommt, liest zuerst, was er bekommt. Der Anmeldeknopf steht ohne Scrollen im ersten Bild, auch bei 390 x 844.
- **Anmeldung:** dasselbe Brevo-Formular wie bisher.
  - Das erste Formular mit den UTM-Feldern (`id="utmSource"` usw.) ist vom Platz nach Schritt 3 ins erste Bild gezogen.
  - Das zweite am Ende ist unverändert. Es holt sich die UTM-Werte beim Absenden wie bisher.
  - `utm.js` und das Absende-Skript sind nicht angefasst.
- **Ruhiger:**
  - keine Trennlinien zwischen den Schritten, keine Umrandungen um Grafiken, Knöpfe und Kanäle. Flächen und Abstand trennen jetzt.
  - Kopfzeilen nicht mehr in Großbuchstaben
  - die Zeile „1 / 5 · the chain“ über jeder Überschrift fällt weg. Die Stelle zeigt die Leiste, für Screenreader trägt jeder Schritt „1 of 5, the chain“ als Name.
  - „share on x“ steht jetzt unter der Grafik statt über der Überschrift.
- **Hintergrund hell** jetzt #F2F5F4 statt #EEF3F1, also die Markenfarbe.
- **Schriftgrößen:** von 10 auf 9.
- **Generator:** Die Startseite kommt aus `scripts/startseite.py`, also steht die Änderung dort.
  - Neu ist `intro_html()`.
  - Die Wochenseiten behalten ihr bisheriges erstes Bild mit eigenem h1. Den gemeinsamen Rahmen (Farben, keine Linien) übernehmen sie über `archiv.py`.
  - `seo_seiten.py` hat dadurch das Datum „page last updated“ der Wochenseiten, des Archivs und von method auf 26 October 2026 gesetzt, weil sich ihr sichtbarer Text geändert hat.
- **Main eingezogen:** Die Lesung vom 26.10.2026 ist drin, alle generierten Seiten sind neu gebaut.

## Audit, Befunde (390, 768, 1440 px)

| Seite | FAIL | WARN | Was zuerst auffällt |
| --- | --- | --- | --- |
| Startseite, Stand main | 8 | 6 | erstes Bild ohne Satz, was die Seite ist, Anmeldung erst nach Schritt 3, kein h1, Kopfzeilen über jeder Überschrift, Linien und Kästen, Text unter 13 px, Kontrast der Chips 2.9:1 |
| Startseite, nachher | 3 | 4 | Rest siehe unten |
| /kaspa-weekly.html | 12 | 10 | 39 Textblöcke unter 13 px, 11 Kleinlabels in Großbuchstaben, 14 umrandete Kästen, 3 Reihen gleicher Karten, Terrakotta #C2553A, Fließtext 15 px und 99 Zeichen je Zeile, Kontrast 3.5:1 bei „what this format is“, eine Zeile scrollt bei 390 seitlich |
| /kaspa-covenants.html | 10 | 8 | 29 Textblöcke unter 13 px, 10 Kleinlabels, 10 Kästen, Verlauf-Flächen, Fließtext 15 px, Kontrast 3.5:1, seitliches Scrollen bei 390 |
| /kaspa-mining.html | 12 | 9 | h1 mit 14 Wörtern, bei 390 vier Zeilen, 38 Textblöcke unter 13 px, Kontrast 3.5:1 bei „The short answer“, Großbuchstaben im Titel, Gedankenstrich im h1 |
| /kaspa-supply.html | 11 | 11 | h1 mit 12 Wörtern, bei 390 drei Zeilen, 35 Textblöcke unter 13 px, Kontrast 3.5:1, leere Mitte im Anmeldekasten bei 768 |

**Allen vier Unterseiten gemeinsam:**
- **Kopf:**
  - Kein dominantes Element im ersten Bild, die größte Schrift ist 52 px.
  - Die Anmeldung steht erst weit unten.
  - Kein Bild.
- **Text:**
  - Text unter 13 px.
  - Kleinlabels in Großbuchstaben mit Sperrung.
- **Flächen:**
  - Kästen mit 1px-Rand.
  - Knöpfe mit Schatten.
  - Verläufe.
- **Textregel:** Kopfzeilen mit „live“ auf mining und supply, also Echtzeitwörter. Die behebt #141 schon.
- **Zahl im ersten Bild:** Bei mining und supply steht dort ein Strich, bis die Daten im Browser geladen sind. Ohne Netz zur Datenquelle bleibt der Strich stehen.

**Startseite nachher, was bleibt und warum:**
- **IBM Plex Mono und drei Schriften** (mono, font-count): bleibt, gehört zur Marke.
- **Keine Bilder, kein Video** (few-pictures, no-footage): bleibt in diesem PR.
  - Ein Bild im ersten Bild wäre der größte Inhalt und würde LCP verschlechtern, das schließt der Auftrag aus.
  - Vorschlag als Folge-PR, siehe unten.
- **Wenig Bewegung** (still-page): bleibt.
  - Die Schritte blenden schon beim Scrollen ein.
  - Eine Einblendung im ersten Bild würde den größten Inhalt später zeigen.
- **Wortmarke im Fuß 3.2:1** (contrast): bleibt, ein Logo ist von der Kontrastregel ausgenommen.
- **Ränder 196 und 238 px bei 1440** (off-centre, nur WARN): Fehlmeldung.
  - Der Skill misst die Textzeilen, nicht die Flächen.
  - Die Karte der Zahl der Woche reicht rechts genau bis 1244 px wie der Anmeldeknopf im Kopf, links beginnt alles bei 196 px.

## Messungen, Startseite vorher (main) gegen nachher
**LCP:**
- **Aufbau:**
  - lokal, gzip wie bei GitHub Pages
  - Netz gedrosselt: 150 ms Latenz, 1.6 Mbit/s
  - CPU vierfach gedrosselt
  - 15 Läufe, vorher und nachher abwechselnd
- **Ergebnis:**

| Breite | vorher Median | nachher Median | vorher p75 | nachher p75 |
| --- | --- | --- | --- | --- |
| 390 | 500 ms | 484 ms | 532 ms | 500 ms |
| 1440 | 504 ms | 500 ms | 516 ms | 512 ms |

- LCP ist nicht schlechter. Der größte Inhalt ist jetzt Text in Archivo 900 bzw. IBM Plex Sans. Archivo wird wie bisher vorgeladen.
- Ein zusätzliches Vorladen von IBM Plex Sans habe ich getestet. Es machte 1440 langsamer und ist nicht drin.
- Das HTML ist ungepackt 3 KB größer, gepackt 1 KB.

**Kontrast WCAG AA:**
- Geprüft wurden alle sichtbaren Textelemente, hell und dunkel, bei 390 und 1440 (86 bzw. 93 Texte).
- Alle erreichen AA, außer der Wortmarke im Fuß (Logo).
- **Im ersten Bild:**
  - #F2F5F4 auf #080B0F
  - #A9B7B4 auf #0F1519
  - #49EACB auf #0F1519
  - Knopf #04211C auf #49EACB
  - Platzhalter #4F625D auf #F2F5F4

  Alle Werte liegen über 4.5:1.

**Formular:**
- **Test:** im Browser mit `?utm_source=youtube&utm_medium=shorts&utm_campaign=w44`. Brevo war abgefangen, es ging keine echte Anmeldung raus.
- **Gesendet:** Beide Formulare senden vorher und nachher genau dieselben Felder.
  - EMAIL
  - UTM_SOURCE youtube, UTM_MEDIUM shorts, UTM_CAMPAIGN w44, UTM_MEDIUM_RAW shorts
  - locale, html_type
  - leeres Honigtopf-Feld
- **Rückmeldung:** Die Bestätigung erscheint im jeweiligen Kasten.
- **Erstes Bild:** Der Knopf steht bei 390 x 844 im ersten Bild, vorher nicht.

**Externe Skripte:** keine neuen. Es bleiben `capture.js` und `utm.js` aus dem eigenen Repo.

**Prüfungen im Repo, alle grün:**
- `startseite.py --selbsttest` mit neuen Fällen:
  - Anmeldung vor dem ersten Schritt
  - genau ein h1
  - Versprechen nennt jede Zahl und den nächsten Montag
  - keine Kopfzeile über den Schritten
  - Wochenseite behält ihr h1
- `startseite.py --pruefen`, `archiv.py --selbsttest`
- `utm.py --selftest`, `utm_fields.py --selftest`
- `check_reads.py index.html`
- `weekly_pruefung.py --selbsttest`
- `seo_pruefung.py --gegen origin/main` (0 Fehler), `seo_pruefung.py --selbsttest`
- `seo_seiten.py --pruefen` und `--selbsttest`
- `kurzlinks.py --pruefen`, `wortmarke.py pruefen`
- Secret-Scan

**Textregeln:** Die Wache in `startseite.py` liest jetzt auch das h1 und die neue Zeile. Kein Echtzeitwort, „%“, jede Zahl mit Datum, keine Striche, Doppelpunkte oder Pfeile.

**Vorher und Nachher:** `docs/startseite/`
- `spitze-erstes-bild-390.png`, `-768.png`, `-1440.png`: vorher, nachher hell, nachher dunkel
- `spitze-ganze-seite-390.png`, `-768.png`, `-1440.png`: vorher und nachher

## Web Interface Guidelines, Befunde
Geprüft wurde der neue Code. Die Zeilen beziehen sich auf den Stand im PR.

| Datei:Zeile | Befund | Status |
| --- | --- | --- |
| scripts/startseite.py:653 | Datum „2 nov“ im Versprechen konnte zwischen Zahl und Monat umbrechen | behoben, geschütztes Leerzeichen |
| index.html:189 | Platzhalter im ersten Bild in Grau des Browsers, unter 4.5:1 | behoben, #4F625D (5.9:1) |
| index.html:188 | Anmeldeknopf im ersten Bild ohne Hover-Zustand | behoben |
| index.html:201 | „5 numbers, 2 minutes“ im ersten Bild ohne Hover-Zustand | behoben |
| index.html:290 | E-Mail-Feld ohne sichtbares Label | bleibt, `aria-label="email"`, Platzhalter mit Muster und das h1 direkt darüber sagen, wofür es ist |
| index.html:316 | Schritte als `section` mit `aria-label` werden zu Regionen | in Ordnung, der Name sagt Stelle und Thema, die Kopfzeile dafür ist weg |
| index.html:320 | „share on x“ öffnet ein neues Fenster | in Ordnung, `rel="noopener"` wie bisher |
| index.html:130 | Ränder mit `vw` zählen die Bildlaufleiste mit | behoben, Prozent statt `vw`, kein seitliches Scrollen bei 390, 768 und 1440 |
| index.html:183 | h1 mit `text-wrap: balance` | in Ordnung |
| index.html:180 | Fokusrahmen im dunklen ersten Bild | in Ordnung, #49EACB auf #080B0F ist gut sichtbar |
| index.html:143 | Bewegung bei reduzierter Bewegung | in Ordnung, keine neue Bewegung |
| index.html (Überschriften) | kein Title Case | bleibt, Hausstil klein |

## Folge-PRs (Vorschlag, jeweils mit Vorher und Nachher)
1. **Unterseiten-Rahmen** für weekly, covenants, mining und supply, gemeinsam über `rahmen.css`:
   - kleinste Schrift 13 px, Fließtext 16 px mit höchstens 70 Zeichen je Zeile
   - Kleinlabels in normaler Schreibung
   - Kästen ohne Rand, Knöpfe ohne Schatten, keine Verläufe
   - Kontrast der grauen Labels von 3.5:1 auf mindestens 4.5:1
   - Terrakotta #C2553A raus
2. **Erstes Bild der Unterseiten** wie auf der Startseite:
   - kurzes h1, höchstens zwei Zeilen bei 390
   - die Kennzahl groß
   - die Anmeldung im ersten Bild
   - Erst mining und supply, dann covenants und weekly.
3. **Zahl ohne Strich** bei mining und supply. Die Seite bringt den letzten gemessenen Wert mit Datum schon im HTML mit, das Skript ersetzt ihn nur noch. Kein Strich im ersten Bild, auch ohne Netz zur Datenquelle.
4. **Seitliches Scrollen bei 390** auf weekly, covenants, mining und supply: die Tabellen. Prüfen, ob das gewollt ist, sonst umbrechen.
5. **Hintergrund #F2F5F4 auf allen Seiten.** Die Startseite hat ihn jetzt, die Unterseiten noch #EEF3F1.
6. **Bild im ersten Bild der Startseite,** sobald #144 gemergt ist. Eines der generativen Motive als SVG-Fläche hinter dem Versprechen, aus `graphics/hintergruende/`. Vor dem Umbau messe ich LCP; wird es schlechter, kommt es nicht.
7. **Textregeln der Unterseiten:** ist #141, schon offen.

## PR-Nummern
- PR 1, Startseite: #147
- baut auf #146 auf. Wird #146 zuerst gemergt, schrumpft #147 auf die Änderungen von heute.

## Offene Fragen an Ben
1. **Plausible-Liste:** Welche drei Unterseiten haben laut Plausible die meisten Besuche? Ich habe die Ersatzliste genommen (covenants, mining, supply). Mit dem Screenshot passe ich die Folge-PRs an.
2. **Versprechen:** Ist „kaspa in 6 numbers, every monday“ so richtig? Die Zahl folgt den Schritten mit Daten plus der Zahl der Woche, heute 6. Fehlt eine Quelle, steht dort 5.
3. **Reihenfolge der Folge-PRs:** Soll ich mit Punkt 1 beginnen?
4. **#146:** Erst #146 mergen und dann #147, oder #146 schließen und nur #147 nehmen? Beides geht, #147 enthält #146.

## Was Ben tun muss
- PR #147 ansehen, vor allem die Bilder in `docs/startseite/`, und mergen. Workflow-Dateien sind nicht betroffen, also Sammelfenster 16:00.
- Den Plausible-Screenshot schicken, falls die Ersatzliste nicht stimmt.
- Die vier Fragen beantworten.
