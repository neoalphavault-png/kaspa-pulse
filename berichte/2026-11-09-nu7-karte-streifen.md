# NU7-Karte mit Streifen, letzte Runde vor dem Post (9.11.2026)

Ben am 8.11. abends: Die Spalte „90% band“ wird durch einen Streifen je Zeile ersetzt. Dazu ein neuer Untertitel, eine Fußnote mit Sternchen und die Breite der Bänder im Fuß. Frist Mo 9.11. 10:30, Post um 11:00.

<!-- discord -->
NU7-Karte mit Streifen liegt mit der Vorschau mit 390 px in #ph-entwuerfe, fertig am So 8.11. abends, also vor der Frist. Je Zeile ein Streifen von 15 min vor bis 15 min nach unserer Prognose, der Block als türkiser Punkt, rechts heißt später. pulsehawk.io/method liefert 200 und erklärt PH-M-006. Achtung: Der Track Record führt den 23.10. und den 4.11. noch nicht und sagt noch „estimate“. Bericht berichte/2026-11-09-nu7-karte-streifen.md
<!-- /discord -->

## Was gemacht wurde

1. **Untertitel** „published 14 to 2 days ahead, scored against the block“.
2. **Streifen** statt der Spalte „90% band“, Kopfzeile „forecast and block“. Die Spalte „the block came“ ist unverändert.
   - Alle vier Streifen haben denselben Maßstab, 15 min vor bis 15 min nach unserer Prognose.
   - Ein dünner heller Strich in der Mitte ist unsere Prognose, der türkise Punkt ist der Block. Rechts heißt, der Block kam später.
   - 23 oct und 28 oct liegen rechts, 2 nov und 4 nov links. Das passt zur Textspalte.
   - Der Hintergrund ist blass türkis, wo das 90-%-Band liegt. Alle vier Bänder reichen auf beiden Seiten über das Fenster hinaus, deshalb zeigen in jeder Zeile an beiden Enden kleine Pfeile, dass es weitergeht. Eine Bandkante, die ins Fenster fällt, zeichnet das Skript an der genauen Stelle. Das habe ich mit einem erfundenen schmalen Band geprüft, auf der Karte kommt der Fall nicht vor.
   - Unter der letzten Zeile steht eine Achse mit „15 min earlier“, „our forecast“ und „15 min later“. „our forecast“ steht in einer zweiten Zeile unter dem Mittelstrich, weil die drei Wörter nebeneinander bei 30 px nicht in die Spalte passen.
3. **Fußnote.** Hinter „90% band“ steht ein *. Unten steht „* how we forecast, step by step, pulsehawk.io/method“.
   - pulsehawk.io/method liefert 200 (geprüft am 8.11. um 19:50 UTC). Die Seite erklärt PH-M-006 („Forecast of an activation time“) mit Ziehungen, Median, 90-%-Band und Link zum Code.
   - Mit Schrägstrich am Ende (pulsehawk.io/method/) liefert die Adresse 404. Auf der Karte steht sie ohne.
4. **Bandbreite im Fuß.** „the 90% bands spanned 2 h 53 min to 8 h 38 min.“ Gerundet auf ganze Minuten, aus der Rechentabelle.
5. **Lesbarkeit bei 390 px.** Der Punkt hat 22 px bei 1080 Breite, in der Vorschau etwa 8 px, und ist klar zu sehen. Der Streifen ist 36 px hoch. Keine Dezimalminuten, keine Doppelpunkte oder Gedankenstriche im Fließtext. Die Stil-Prüfung ist bestanden.

Damit alles auf 1350 px passt, steht die große Zahl jetzt mit 140 statt 160 px. Die Abstände in der Tabelle sind etwas enger. Die Kopfzeilen der ersten, zweiten und vierten Spalte gehen über zwei Zeilen.

## Rechentabelle

Block 3.543.405, Kopfzeit 6.11. 02:34:02 UTC. Positiv heißt, der Block kam nach der Prognose, der Punkt liegt rechts.

| Prognose | Median (UTC) | Block minus Prognose | Punkt | 90-%-Band (UTC) | Bandbreite |
|---|---|---:|---|---|---|
| 23.10. | 02:21:52 | +730 s | rechts, 12 min 10 s | 5.11. 22:02:16 bis 6.11. 06:40:25 | 31.089 s, 8 h 38 min |
| 28.10. | 02:26:16 | +466 s | rechts, 7 min 46 s | 5.11. 23:01:22 bis 6.11. 05:51:31 | 24.609 s, 6 h 50 min |
| 2.11. | 02:39:52 | −350 s | links, 5 min 50 s | 6.11. 00:28:23 bis 05:00:17 | 16.314 s, 4 h 32 min |
| 4.11. | 02:40:58 | −416 s | links, 6 min 56 s | 6.11. 01:14:45 bis 04:07:28 | 10.363 s, 2 h 53 min |

`nu7_karte.py` schreibt die Werte zusätzlich in `rechnung.json` (Felder `block_minus_prognose_s` und `bandbreite_s`).

## Stil-Modul

`ph_stil.py` lässt jetzt einen blass türkisen Hintergrund für ein 90-%-Band zu, mit höchstens 10 % Deckkraft. Kräftiges Türkis bleibt dem einen gezählten Element vorbehalten, hier der großen Zahl und den Punkten der Blöcke. Der Selbsttest hat dafür einen eigenen Fall. Die gleiche Datei kommt in pulsehawk-site als eigener PR.

## Versand

Karte und Vorschau liegen in #ph-entwuerfe über `ph/stil-muster`. Nicht gepostet.

## Offene Fragen an Ben

1. Der Track Record (pulsehawk.io/track-record) führt am 8.11. um 20:15 UTC nur TR-003 (28.10.) und TR-004 (2.11.). Der 23.10. und der 4.11. fehlen noch, und dort steht noch „estimate“. Die Fußzeile „every forecast, hits and misses“ stimmt erst, wenn beide Einträge drin sind. Soll die Karte trotzdem um 11:00 raus, oder vorher die Fußzeile weg?
2. Die große Zahl ist jetzt 140 px statt 160 px, sonst passt der Fuß nicht. Ist das in Ordnung?

## Was Ben tun muss

- Karte in #ph-entwuerfe ansehen und bis Mo 11:00 freigeben.
- Vor dem Post prüfen, ob der Track Record den 23.10. und den 4.11. zeigt.
