# Bericht 27.10.2026: Suchbild-Reel „find the 1 white dot“

Auftrag von Ben vom 26.10.2026, neue Frist Do 29.10.2026 18:00 Berlin (SEO-Auftrag v2 vom 27.10.2026).

## Stand
**Die gezählte Rohzahl vom 06.10.2026 gibt es nicht mehr.** Wie im Auftrag verlangt, melde ich das und rate nicht.
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

## Prüfung mit einer Probezahl
- **Probebild:** Zum Testen des Layouts habe ich mit 5,978 Punkten gerendert. Das Bild bleibt im Arbeitsordner und wird nicht veröffentlicht.
  - Raster 85 x 71, Abstand 9.7 px, Punkt 6 px.
  - Video 12.0 s, h264 und aac.
- **Bei 390 px Bildschirmbreite:** Ein Handy mit 3-facher Pixeldichte zeigt das Bild fast in voller Auflösung. Dort ist der weiße Punkt zu finden, aber gut versteckt. Auf einem Bildschirm mit einfacher Dichte wäre er kaum zu sehen.
- Selbsttest grün mit 17 Fällen.

## PR-Nummern
- #168, Rohzahl ins Log
- Generator und dieser Bericht, PR folgt

## Offene Fragen an Ben
1. **Welche Zahl?** Vorschlag: eine neue gezählte Rohzahl aus einem Handlauf der Tagesgrafik mit Form 4 und `senden=false`. Der Lauf misst 600 s und verschickt nichts. Text und Dateiname tragen dann dessen Datum statt 6 oct 2026. Wenn du zustimmst, starte ich den Lauf, baue Reel und Karussell und liefere bis Do 29.10. 18:00. Der Posttermin wäre frühestens Do 29.10.
2. Oder hast du die Rohzahl vom 06.10. noch irgendwo, zum Beispiel aus dem Artefakt oder einem Screenshot des Laufs? Dann reicht `--rohzahl N --fenster 600.3 --datum 2026-10-06`.

## Was Ben tun muss
Eine der zwei Fragen oben beantworten.
