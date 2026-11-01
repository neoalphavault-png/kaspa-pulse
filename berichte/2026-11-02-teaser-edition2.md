# Bericht 2.11.2026: Teaser Cheat Sheet Edition 2

Auftrag von Ben vom 1.11.2026, Frist Mo 2.11. 14:00 Berlin. Gebaut am 1.11.2026 und gemergt mit #224.

## Warum
Das volle Karussell und das Deckblatt zeigten alle 8 Zahlen. Damit war der Inhalt verschenkt, für den man sich anmelden soll. Die Anzeige ad1-whales-v3 brachte 0 Anmeldungen. Der Teaser folgt deshalb derselben Logik wie kaspapulse.com/whales: 2 Zahlen offen, 6 gesperrt.

## Teaser-Karussell, 4 Seiten 1080x1350
1. **Titel:** „the 8 kaspa numbers whales watch“, edition 2 · november 2026, mit allen 8 Fragen.
   - **Offen, Zahl 1:** 5.6%, as of 1 nov 2026, counted by kaspa pulse.
   - **Offen, Zahl 5:** 4 nov, Zeitpunkt 4 nov 2026, 13:45 utc, computed from the emission schedule.
   - **Gesperrt:** Die Werte 2, 3, 4, 6, 7 und 8 sind ein unscharfer Block wie auf /whales, darunter „in the cheat sheet“. Im HTML steht weder Zahl noch Datum, und der Generator prüft das.
2. **Zahl 1 voll:** die Seite „how much does the biggest wallet hold?“ wie im PDF, 5.6%, 1,542,974,288 KAS, 1 nov 2026.
3. **Zahl 5 voll:** die Seite „when do miners get paid less again?“ wie im PDF, 4 nov, 2.06 auf 1.94 KAS je Block.
4. **Schluss:** „6 more numbers, dated and sourced, in the cheat sheet.“, darunter die 6 Fragen mit gesperrtem Wert, unten „free by email, link in bio.“

## Anzeigenbilder
- Das Titelmotiv gibt es einzeln in 1080x1350 (Feed) und 1080x1920 (Story und Reels).
- Unten bleibt der Bereich frei, den Instagram mit dem Button überdeckt: 230 px bei 1350, 380 px bei 1920. Bei 1920 bleiben zusätzlich oben 250 px für die Profilzeile frei.
- Der Generator misst im fertigen Bild, dass dort kein Text steht.

## Zahlen und Stichtage
Alle Werte kommen aus dem Lauf vom 1.11.2026, 09:00 Berlin (Lauf 41286982337, Edition 2). Die Messung liegt als `data/cheat-sheet-edition-2-probe.json` im Repo.

| Zahl | Wert | Stichtag | Im Teaser |
| --- | --- | --- | --- |
| 1 biggest wallet | 5.6% | 1 nov 2026 | offen |
| 2 exchanges | gesperrt | 25 oct 2026 | gesperrt |
| 3 not moved in a year | gesperrt | 31 oct 2026 | gesperrt |
| 4 wallets with 100 KAS | gesperrt | 25 oct 2026 | gesperrt |
| 5 next reward cut | 4 nov, 13:45 utc | 1 nov 2026 | offen |
| 6 what pays the miners | gesperrt | 1 nov 2026 | gesperrt |
| 7 hashrate | gesperrt | 31 oct 2026 | gesperrt |
| 8 covenants | gesperrt | 25 oct 2026 | gesperrt |

## Prüfung
- **Look und Kontrast:** Der Look ist der des Cheat Sheets mit denselben Schriften und Farben. Jedes Bild erreicht mindestens 7:1, gemessen im fertigen Bild.
- **Textregeln:** Kein now, live oder today, keine Doppelpunkte oder Striche im Fließtext. Jede offene Zahl hat ein Datum.
- **Selbsttest:** 11 neue Fälle. Ein Wert im Sperrblock und ein gesperrter Wert im HTML werden beide erkannt. Dazu prüft er Caption, Seitenzahl, Größen und die Fußzeile von Seite 6.
- Secret-Scan ohne Fund, keine Workflow-Dateien.

## Fußzeile Seite 6 im PDF
Auf Seite 6 (Zahl 5) stand „from the emission schedule, counted by kaspa pulse“. Der Generator schreibt jetzt „computed from the emission schedule“. Das gilt ab dem nächsten Bau, also auch, wenn du Edition 2 mit `veroeffentlichen=true` neu baust, und sicher für Edition 3.

## Caption-Vorschlag
```
the 8 kaspa numbers whales watch, edition 2, november 2026. 2 of them in this post, the biggest wallet and the next block reward cut, each with its date and source. the other 6 are in the cheat sheet, free by email, link in bio.

#kaspa #kas #blockdag
```
Ohne Engagement-Köder, mit Edition und Monat.

## Künftig für jede Edition
Der monatliche Lauf baut den Teaser automatisch mit, aus derselben Messung wie das PDF. An #moderator-only geht als „📤 VON HAND“ nur noch der Teaser mit seinen 4 Seiten, den 2 Anzeigen und der Caption. Das volle Karussell wird weiter gebaut, aber nicht mehr zum Posten geschickt.

## Hinweis zum 4.11.
Seite 3 und der Titel nennen den Reward Cut am 4 nov. Wird der Teaser nach dem 4.11. gepostet, ist die Zahl 5 Vergangenheit. Die Seite bleibt richtig, weil sie datiert ist, wirkt dann aber alt. Ein Post bis Di 3.11. passt am besten.

## Was Ben tun muss
Siehe „📤 VON HAND“ im Discord-Abschnitt.

<!-- discord -->
**Teaser Cheat Sheet Edition 2, 1.11.2026**
- **4 Seiten 1080x1350:** Titel mit allen 8 Fragen, offen nur Zahl 1 (5.6%, 1 nov 2026) und Zahl 5 (4 nov), die anderen 6 unscharf ohne Zahl im HTML. Dann Zahl 1 voll, Zahl 5 voll, Schluss „6 more numbers…“.
- **Anzeigen:** 1080x1350 und 1080x1920, unten frei für den Button.
- **Prüfung:** Kontrast 7:1, Textregeln, Selbsttest grün. Gemergt mit #224.
- **Künftig** baut jeder Lauf den Teaser mit, das volle Karussell geht nicht mehr raus.
- **Fußzeile Seite 6** jetzt „computed from the emission schedule“.
- **Bericht:** berichte/2026-11-02-teaser-edition2.md
<!-- teil -->
📤 VON HAND
Instagram, Teaser Cheat Sheet Edition 2, am besten bis Di 3.11. (der Cut ist am 4.11.).
- **Karussell:** Bild 1 bis 4 in dieser Reihenfolge, 1080x1350, ohne Musik.
- **Anzeige:** Bild 5 im Feed, Bild 6 für Story und Reels, nicht ins Karussell.
Caption kopieren
```
the 8 kaspa numbers whales watch, edition 2, november 2026. 2 of them in this post, the biggest wallet and the next block reward cut, each with its date and source. the other 6 are in the cheat sheet, free by email, link in bio.

#kaspa #kas #blockdag
```
<!-- bild ig/cheat-sheet/teaser-edition-2/teaser-1-titel.png -->
<!-- bild ig/cheat-sheet/teaser-edition-2/teaser-2-zahl-1.png -->
<!-- bild ig/cheat-sheet/teaser-edition-2/teaser-3-zahl-5.png -->
<!-- bild ig/cheat-sheet/teaser-edition-2/teaser-4-schluss.png -->
<!-- bild ig/cheat-sheet/teaser-edition-2/anzeige-1080x1350.png -->
<!-- bild ig/cheat-sheet/teaser-edition-2/anzeige-1080x1920.png -->
<!-- /discord -->
