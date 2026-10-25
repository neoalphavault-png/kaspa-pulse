# Bericht 25.10.2026: Bildhintergründe für Tagesgrafik, Zahl des Tages, Karussell und Story

Branch `design/hintergruende`. **Der PR baut auf #140 (Story-Vorlagen) und #143 (Karussell-Automatik) auf**, beide sind in den Branch gemergt. Er gehört nach diesen beiden gemergt. Bis dahin zeigt sein Diff deren Änderungen mit. Im Einsatz ab Mi 28.10.2026.

## Was gemacht wurde
- **Acht generative Motive** in `scripts/hintergrund.py`:
  - blockstrom, knotennetz, punktraster, höhenlinien (`hoehenlinien`), partikel-puls, abstrakte zahnräder (`zahnraeder`), sternenfeld mit Hashrate-Wellen, glitch-raster
  - je eine dunkle und eine helle Fassung; der Teal-Look zeichnet die Formen der hellen Fassung in seinen Farben
  - nur Farben aus `look_takt`, kein Falke, keine fremden Bilder
  - jedes Motiv kommt aus einem festen Startwert und ist immer dasselbe Bild
- **Standbilder:** 32 SVG in `graphics/hintergruende/`, 8 Motive × 2 Fassungen × Feed 1080x1350 und Story 1080x1920.
- **Register:** `docs/hintergruende.md` mit Herkunft „generativ“, Startwert und Dateien je Motiv. Standbilder und Register baut das Skript (`--bauen`), `--pruefen` fällt auf jede Abweichung.
- **Takt:**
  - Look und Motiv wechseln gemeinsam. `look_takt.raster_motiv` gibt jedem Post im Instagram-Raster das Motiv nach dem seines Vorgängers, mit derselben Vorgänger-Regel wie beim Look (auch wenn der Karussell-Entwurf vor der Tagesgrafik des Tages läuft). Nie dasselbe Motiv zweimal hintereinander; bei acht Motiven auch nie zweimal übereinander im Dreier-Raster.
  - Das Motiv steht beim Raster-Eintrag in `data/look-takt.json`.
  - threads, x und discord rücken mit dem Datum weiter, ebenso die Zahl des Tages.
  - Die Story rückt mit dem Datum weiter, nie im Motiv des Feed-Posts vom selben Tag.
- **Lesbarkeit:**
  - **Schleier:** `setzen()` legt das Motiv als Ebene ganz nach hinten und nach dem Layout hinter jeden Text einen Schleier im Grundton (95 % Deckung). Das Layout der Seiten bleibt unberührt.
  - **Rand:** Im Feed bleibt der 60-px-Rand Grund; das ist die bestehende Rand-Wache, das Motiv blendet bis 140 px ein. Die Story läuft randlos.
- **Kontrast-Wache 7:1:** neu in `content_wache.pruefe_seite`, also für alle Bild-Generatoren.
  - Gemessen wird im fertigen Bild: ein Screenshot ohne Text, dann je Text die Pixel seines Grundes gegen seine Farbe, unteres 5-%-Quantil.
  - Ausgenommen ist nur die Wortmarke (ein Logo). Ein Verstoß stoppt den Lauf.
- **Eingebaut in:**
  - Tagesgrafik (alle vier Kanäle)
  - Zahl des Tages (alle Kanäle)
  - Karussell woche und story und das Meme (auch über `karussell_post.py`; das Manifest trägt das Motiv als `hintergrund`)
  - Story-Vorlagen
  - Ab 28.10. (`hintergrund.AB`) tragen die Bilder ein Motiv. Farben und Kontrast-Wache gelten sofort nach dem Merge.

## Was sich an den Farben ändert (bitte ansehen)
Die 7:1-Regel trifft schon die bestehenden Looks, unabhängig vom Motiv. Ohne Änderung wäre jede helle Grafik an der Wache gescheitert.

| Look | Farbe | vorher | Kontrast | nachher | Kontrast |
| --- | --- | --- | --- | --- | --- |
| hell | akzent | #0F9A80 | 3.1:1 | #085042 | 8.4:1, auf der Fläche 7.4:1 |
| hell | text2 | #4F625D | 5.8:1 | #3B4A46 | 8.3:1, auf der Fläche 7.3:1 |
| teal | text2 | #0F4A40 | 6.7:1 | #0A332C | 9.1:1, auf der Fläche 7.3:1 |

- Gleicher Farbton, nur dunkler.
- Im hellen Look werden damit auch die Balken dunkler, weil sie den Akzent tragen.
- Die **Wortmarke** bleibt `#0F9A80` (neuer Schlüssel `marke`). Das gilt für die Grafiken und für die Website, auf kaspapulse.com ändert sich nichts (`wortmarke.py pruefen`: 0 Abweichungen).
- **Zahl des Tages** hat eine eigene Farbtabelle. Dort sind im hellen Look teal, dim und red dunkler, im Teal-Look dim und red; die Wortmarke steht auf `--marke`.

## Kontaktbogen
- `docs/hintergruende/raster-ab-2026-10-28.png`: das Instagram-Profil als 9er-Raster, so wie Instagram es zeigt.
  - drei Spalten, neuestes oben links, jedes Bild als 3:4-Ausschnitt der 4:5-Grafik
  - die neun Posts von Mi 28.10. bis Mo 02.11.: Tagesgrafik täglich, Story-Karussell Mi, Woche und Meme Sa
  - Look und Motiv kommen aus einer Kopie des Look-Takts; die Inhalte sind Beispiele aus den Selbsttests
- `docs/hintergruende/story-ab-2026-10-28.png`: die Story-Vorlagen Mi bis Sa mit ihren Motiven.
- `docs/hintergruende/matrix-alle-motive.png`: jedes Motiv in jedem Look auf Tagesgrafik, Zahl des Tages und Karussell.
- Alle Bilder sind mit den echten Generatoren gebaut und durch alle Wachen gelaufen: Größen, Rand, Text, Kontrast 7:1. Neu bauen: `python3 scripts/hintergrund_bogen.py --out docs/hintergruende`.
- **Funde der Kontrast-Wache unterwegs, alle behoben:**
  - die hellen Farben oben
  - der Akzent auf den Meme-Kacheln, 6.5:1 auf der Fläche
  - eine Datumszeile auf dem Punktraster, 6.8:1, vor dem dichteren Schleier

## Tests
- **Selbsttests grün:**
  - `hintergrund.py`, unter anderem jedes Motiv in jedem Look mit Text in text2 gemessen und ein Gegenbeispiel, bei dem die Wache anschlagen muss
  - `look_takt.py` (Motivfolge im Raster), `content_wache.py`, `wortmarke.py`, `karussell.py`, `meme_wahr.py`, `karussell_post.py`
  - `story_vorlage.py` (jetzt mit Motiv in jedem Bild), `number_of_day.py --selbsttest`, `tagesgrafik.py --selftest`
- **Weitere Prüfungen:** `hintergrund.py --pruefen` und `wortmarke.py pruefen` ohne Abweichung, Secret-Scan sauber.
- **Kanal-Renderer:** Tagesgrafik und Zahl des Tages für den 28.10. über `kanaele_rendern` gebaut, alle Kanäle mit Motiv und Wache grün.

## PR-Nummern
- dieser PR: folgt
- baut auf: #140, #143

## Offene Fragen an Ben
1. **Farben:** Sind die dunkleren Töne für hell und teal in Ordnung (Tabelle oben)? Die 7:1-Regel lässt den alten hellen Akzent `#0F9A80` für Text nicht zu. Wenn die Balken im hellen Look hell bleiben sollen, trenne ich Füllfarbe und Textfarbe; das wären mehr Stellen in den Generatoren.
2. **Diagramme:** Der Schleier liegt nur hinter Text. Durch die Diagramme selbst (Punkte, Waffeln) scheint das Motiv durch, zu sehen in der Tagesgrafik f2 und f5 im Raster. Soll das Motiv auch hinter den Diagrammen zurücktreten?

## Was Ben tun muss
1. #140 und #143 mergen, dann diesen PR. Workflow-Dateien ändert er nicht, neue Pakete braucht er nicht.
2. Den Kontaktbogen ansehen und die zwei Fragen beantworten.
