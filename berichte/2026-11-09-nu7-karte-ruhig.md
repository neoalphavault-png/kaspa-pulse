# NU7-Karte ruhig, Aufräumrunde vor dem Post (9.11.2026)

Ben am 9.11. morgens: Die Karte wirkt überladen. Ziel ist eine Botschaft mit viel Luft, auf dem Handy in 3 Sekunden lesbar. Frist 10:30, Post um 11:00.

<!-- discord -->
NU7-Karte ruhig liegt mit der Vorschau mit 390 px in #ph-entwuerfe, vor der Frist. Nur noch Kicker, 4 of 4, eine Unterzeile, vier Zeilen mit Streifen, eine Achse und eine Fußnote. Der Streifen steht unter jeder Zeile statt in einer dritten Spalte, sonst passt die Achse nicht auf eine Höhe. Der Track Record verlinkt auf die Methode. Bericht berichte/2026-11-09-nu7-karte-ruhig.md
<!-- teil -->
📤 VON HAND 11:00, fällig 11:00 Berlin: Post der NU7-Karte „4 of 4“ (ruhige Fassung aus #ph-entwuerfe von heute), Text schreibst du selbst. Vorher kurz prüfen, ob der Track Record den 23.10. führt. Bericht berichte/2026-11-09-nu7-karte-ruhig.md
<!-- /discord -->

## Was gemacht wurde

- **Geblieben** sind der Kicker „zcash nu7 upgrade, 6 nov 2026“, der Falke, die große Zahl „4 of 4“ und eine Unterzeile: „forecasts landed inside their 90% band*, published 14 to 2 days ahead“.
- **Tabelle:** je Prognose „forecast made“ und „the block came“ in 40 px, darunter der Streifen ohne Kopfzeile.
  - Die Spalte „we said (utc)“ ist weg.
  - Die Pfeile an den Enden sind weg. Strich in der Mitte und Punkt sind geblieben, der Punkt hat jetzt 30 px.
  - Darunter steht eine Achsenzeile auf einer Höhe: „15 min earlier“, „our forecast“, „15 min later“.
- **Weg** sind die zwei Einleitungszeilen, die Zeile mit Blockhöhe und Header-Client, der Hinweis auf 7 Tage und PH-M-006 und die zweite Link-Zeile.
- **Fuß:** „* 90% bands were 2 h 53 min to 8 h 38 min wide. method and every result at pulsehawk.io/track-record“, dann „Data from PulseHawk · pulsehawk.io“. Die Bandbreiten kommen aus der Rechentabelle.
- **Größen:** Die große Zahl ist wieder 160 px. Kein Text ist kleiner als 30 px, also nicht kleiner als die Fußzeile. Die Stil-Prüfung ist bestanden.
- **Versand:** 1080x1350 und Vorschau mit 390 px in #ph-entwuerfe über `ph/stil-muster`. Nicht gepostet.

## Abweichungen, bitte prüfen

1. **Streifen unter der Zeile statt in einer dritten Spalte.** Nachgemessen bei 30 px: „15 min earlier“ 196 px, „our forecast“ 172 px, „15 min later“ 169 px. Damit die drei auf einer Höhe stehen und sich nicht überdecken, braucht der Streifen rund 540 px. Neben „forecast made“ und „6 min 56 s earlier“ bleiben in einer dritten Spalte nur etwa 450 px. Unter der Zeile hat der Streifen die volle Breite von 888 px, und der Punkt ist im Handy-Bild besser zu sehen.
2. **Die Fußnote braucht zwei Zeilen.** Bei 30 px passt der Satz nicht in eine Zeile. Mit „Data from PulseHawk“ sind es unten also drei Zeilen.

## Track Record

- pulsehawk.io/track-record verlinkt auf die Methode, auf /method und /method#ph-m-006. Die Fußnote stimmt damit.
- Stand 9.11. um 08:10 UTC führt die Seite TR-001 bis TR-004. Der 23.10. fehlt noch, und dort steht noch „estimate“. „every result“ in der Fußnote stimmt erst, wenn der 23.10. und der 4.11. als Einträge drin sind.

## Offene Fragen an Ben

1. Ist der Streifen unter der Zeile statt in einer dritten Spalte in Ordnung?
2. Soll die Karte um 11:00 raus, obwohl der Track Record den 23.10. noch nicht führt?

## Was Ben tun muss

- **Heute 11:00 Berlin:** Karte aus #ph-entwuerfe freigeben und selbst posten. Diese Aufgabe geht auch als „📤 VON HAND 11:00“ raus.

## Selbst-Merge

- PR #295, Merge-Commit `46c8ad9`, squash. Live ist das Skript `scripts/ph/nu7_karte.py` in der ruhigen Fassung und dieser Bericht. Die Karte selbst geht nicht automatisch raus, Ben postet.
