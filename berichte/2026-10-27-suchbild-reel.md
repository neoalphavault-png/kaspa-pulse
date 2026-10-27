# Bericht 27.10.2026: Suchbild-Reel „find the 1 white dot“

Auftrag von Ben vom 26.10.2026, neue Frist Do 29.10.2026 18:00 Berlin (SEO-Auftrag v2 vom 27.10.2026).

## Stand
**Geliefert am 27.10.2026, vor der Frist Do 29.10.2026 18:00 Berlin, mit einer neuen gezählten Zahl.** Die gezählte Rohzahl vom 06.10.2026 gibt es nicht mehr. Wie im Auftrag verlangt, melde ich das, und geraten ist nichts.
- **Im Repo:** In kaspa-pulse und pulse-studio steht nur die Rate 10.093 je Sekunde über 600.3 s. Eine gezählte Anzahl steht nirgends, `ep/2026-10-08/skript.md` rechnet selbst „10,093 × 600,3 = 6.058,8“.
- **Bei GitHub:** Die Quelle war der Bericht von Workflow-Lauf 37455223503 (maschinenzahlungen, Job `messung`). Den Lauf gibt es nicht mehr, die API antwortet mit 404. Im Workflow sind nur noch zwei Läufe vom 03.10.2026 gelistet.
- **Aus der Tagesgrafik zurückrechnen geht nicht:** Sie loggte bis heute nur die Rate und den End-Score. Das echte Fenster ist 600 s plus die Dauer eines Abrufs. Für den 21.10.2026 passt deshalb jede ganze Zahl von 5,978 bis 5,981.

## Was gemacht wurde
- **#168, selbst gemergt als 103e040:**
  - Die Tagesgrafik schreibt ab ihrem nächsten Lauf die gezählte Rohzahl ins Log, als `daa_zuwachs`, dazu `daa_start` und das echte Fenster `fenster_sek`.
  - Gemessen wird die Blockrate aber nur, wenn Form 4 läuft, das war zweimal in 30 Tagen. Deshalb druckt `m_blockrate` die Rohzahl zusätzlich ins Job-Log, das kam mit diesem PR.
  - Ein Handlauf der Tagesgrafik mit Form 4 und `senden=false` misst damit 600 s lang, verschickt nichts und schreibt die gezählte Zahl ins Job-Log.
- **`scripts/suchbild_reel.py`, Generator mit Selbsttest:**
  - **Zahl:**
    - `--lauf JJJJ-MM-TT` liest die Rohzahl aus dem Log. Fehlt sie, bricht er ab, ohne zu rechnen.
    - `--rohzahl --fenster --datum` nimmt eine Zahl, die Ben nennt.
  - **Raster:** genau so viele türkise Punkte (#49EACB auf #080B0F) wie gezählt, darin 1 weißer Punkt (#F2F5F4).
    - Die Stelle ist fest aus dem Datum bestimmt.
    - Sie liegt nicht im mittleren Drittel und mindestens 12 % vom Rand entfernt.
    - Reel und Karussell zeigen den Punkt an derselben Stelle.
  - **Reel:** 1080x1920, 12 s, Standbild mit Musik, Ein- und Ausblenden, Lautheit −16 LUFS. Die Texte stehen oben in der sicheren Fläche wie im Auftrag, unten die Wortmarke KASPA PULSE ohne Falke.
  - **Karussell:** 2 Folien 1080x1350.
    - Folie 1 wie das Reel.
    - Folie 2 mit Ring um den weißen Punkt, „‹Rate› blocks a second, counted, ‹Datum›“, „1 block per 10 minutes, bitcoin protocol target“ und „the weekly kaspa numbers by email, link in bio“.
  - **Prüfung:** Textregeln, kein Werturteil, Bitcoin nur als Maßstab, Zahl mit Datum und counted. Dazu `content_wache` im Profil story für das Reel und feed für die Folien. Kein Text liegt auf dem Raster.
  - **Musik:** „Cinematic 80s Synthwave Mystery“ von Sonican. Quelle Pixabay, Pixabay Content License. Im Register von pulse-studio (`docs/musik-lizenzen.md`) als ruhig und für Shorts freigegeben geführt, ohne Gesang.

## Die neue Zahl
- **Messung:** Handlauf der Tagesgrafik mit Form 4 und `senden=false` am 27.10.2026 (Lauf 40571555116). Es wurde nichts verschickt und kein Log geschrieben.
- **Ergebnis:** gezählt **5,953** Blöcke in **600.243 s**, Start 19:43:23 UTC, DAA-Score von 577,099,780 auf 577,105,733. Daraus ergeben sich 9.918 je Sekunde.
- **Festgehalten** in `docs/suchbild/README.md`, weil GitHub Job-Logs nach einiger Zeit löscht.
- **Texte im Bild:**
  - Reel und Folie 1: „5,953 kaspa blocks in 600.2 s, counted, 27 oct 2026“ und „1 white dot, bitcoin protocol target, 1 block per 600 s“.
  - Folie 2: „9.918 blocks a second, counted, 27 oct 2026“.

## Lieferung
- **#174, selbst gemergt als dcef086.** Live unter kaspapulse.com/ig/suchbild/, alle vier Dateien mit HTTP 200 abgerufen:
  - das Reel als mp4, 1080x1920, 12.0 s, h264 und aac mit 48 kHz
  - das Titelbild
  - die 2 Karussell-Folien als JPEG, 1080x1350
- **Nachgezählt:** Im fertigen Reel-Bild sind es 5,952 türkise und 1 weißer Punkt. Der weiße Punkt bleibt im JPEG und im Video weiß.
- **Caption:** `docs/suchbild/caption.txt`. Sie endet mit einer Frage und hat keinen Link. Die Textwache ist grün. Die Karussell-Wache meldet nur „bitcoin“, das hier wie im Auftrag nur als Maßstab steht.
- **Dateinamen:** Sie tragen Do 29.10.2026 18:00 als Vorschlag für den Posttermin, weil der Mittwoch mit einer Zahl vom 27.10. knapp ist. Den Termin legst du fest.

## Prüfung mit einer Probezahl
- **Probebild:** Zum Testen des Layouts habe ich mit 5,978 Punkten gerendert. Das Bild bleibt im Arbeitsordner und wird nicht veröffentlicht.
  - Raster 85 x 71, Abstand 9.7 px, Punkt 6 px.
  - Video 12.0 s, h264 und aac.
- **Bei 390 px Bildschirmbreite:** Ein Handy mit 3-facher Pixeldichte zeigt das Bild fast in voller Auflösung. Dort ist der weiße Punkt zu finden, aber gut versteckt. Auf einem Bildschirm mit einfacher Dichte wäre er kaum zu sehen.
- Selbsttest grün mit 17 Fällen.

## PR-Nummern
- #168, Rohzahl ins Log, selbst gemergt (103e040)
- #169, Generator, Rohzahl ins Job-Log, Bericht, selbst gemergt (df91fb6)
- #174, Reel, Karussell, Register, selbst gemergt (dcef086)

## Offene Fragen an Ben
1. Passt die neue Zahl vom 27.10. statt der vom 06.10.? Alles ist damit gebaut. Für eine andere Zahl reicht ein Aufruf von `suchbild_reel.py`.
2. Posttermin: Do 29.10.2026 18:00 Berlin, oder ein anderer?

## Was Ben tun muss
Reel und Karussell bei Instagram posten, siehe die Teile „📤 VON HAND“ unten.

<!-- discord -->
**Suchbild „find the 1 white dot“, Lieferung 27.10.2026**
- **Zahl:** gezählt 5,953 Kaspa-Blöcke in 600.2 s am 27 oct 2026, ab 19:43 UTC (Handlauf der Tagesgrafik, nichts verschickt). Die Zahl vom 06.10. gab es nicht mehr, geraten ist nichts.
- **Bild:** genau 5,953 Punkte, 1 davon weiß für den 1 Block, den Bitcoin laut Protokoll in 600 s anpeilt. Nachgezählt im fertigen Bild.
- **Musik:** Cinematic 80s Synthwave Mystery von Sonican, Pixabay Content License, im Musikregister für Reels freigegeben.
- **PRs:** #168, #169 und #174, alle selbst gemergt.
- **Bericht:** berichte/2026-10-27-suchbild-reel.md
- **Termin:** Vorschlag Do 29.10.2026 18:00 Berlin
<!-- teil -->
📤 VON HAND, 1 von 2: **Reel bei Instagram**
Plattform Instagram, Reel, Termin Do 29.10.2026 18:00 Berlin.
Datei:
```
https://kaspapulse.com/ig/suchbild/2026-10-29_1800_IG-REEL_find-the-dot.mp4
```
Titelbild:
```
https://kaspapulse.com/ig/suchbild/2026-10-29_1800_IG-REEL_find-the-dot-titelbild.jpg
```
Die Musik ist im Video eingebaut, in der App keine zweite dazu.
Caption, mit den Hashtags:
```
find the 1 white dot.

5,953 dots, one for each kaspa block we counted in 600.2 seconds on 27 oct 2026. the 1 white dot stands for the 1 block bitcoin's protocol targets in 600 seconds.

counted by kaspa pulse from the kaspa network, window from 19:43 utc on 27 oct 2026.

the weekly kaspa numbers by email, link in bio.

#kaspa #kas #blockdag #proofofwork #crypto

where is the white dot?
```
<!-- teil -->
📤 VON HAND, 2 von 2: **Karussell bei Instagram**, 2 Folien in dieser Reihenfolge, gleiche Caption wie beim Reel.
Folie 1:
```
https://kaspapulse.com/ig/suchbild/2026-10-29_1800_IG-KARUSSELL_find-the-dot-01.jpg
```
Folie 2, mit dem markierten Punkt:
```
https://kaspapulse.com/ig/suchbild/2026-10-29_1800_IG-KARUSSELL_find-the-dot-02.jpg
```
Vorschlag: das Karussell einen Tag nach dem Reel posten, dann ist Folie 2 die Auflösung.
<!-- /discord -->
