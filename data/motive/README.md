# Motiv-Bank

Angelegt am 29.10.2026 (Ben, Nachtrag zu Look v2 Teil 2). Hier liegen die Fotos für den Hintergrund von Look B in der Tagesgrafik, der Zahl des Tages und im Karussell. Die ersten Motive liefert Ben aus Grok bis Sa 31.10.2026.

## Ablage
```
data/motive/
  1080x1350/   hochkant, Instagram, Threads, Story-Ausschnitt
  1600x900/    quer, X (Zahl des Tages) und Discord
  register.csv
```

- **Name:** `thema-nr.jpg`, alles klein, die Nummer zweistellig, zum Beispiel `energie-01.jpg` oder `stadt-03.jpg`.
- **Zwei Größen:** Jedes Motiv liegt in beiden Ordnern unter demselben Namen. Fehlt eine der beiden Größen, nutzt der Generator das Motiv nicht.
- **Format:** JPG, sRGB, genau 1080x1350 oder 1600x900 Pixel, höchstens 1,5 MB je Datei.
- **Neue Nummer:** die nächste freie je Thema. Ein ersetztes Motiv bekommt eine neue Nummer, alte Nummern werden nicht neu vergeben.

## Themen je Kennzahl
| Thema | Kennzahl | Bildidee |
| --- | --- | --- |
| `energie` | Hashrate | Energie, Licht |
| `zeit` | Emission, neue KAS, Countdown | Zeit, Sanduhr als Foto |
| `tresor` | Entity X, große Halter, schlafende Coins | Tresor, Stein |
| `stadt` | Blöcke, Blockrate, Transaktionen | Stadt bei Nacht |

Weitere Themen kommen als neue Zeile hier dazu, bevor ihr erstes Motiv abgelegt wird.

## Regeln für jedes Motiv
- **Kein Text, keine Zahl, kein Logo im Bild.** Zahl und Text setzt immer unser Generator darüber, nie das Bild.
- **Ruhig** nach der Hintergrund-Regel vom 29.10.2026 (`docs/grafik-regeln.md`, Abschnitt „Hintergrund“). Keine Linien, Kurven oder Punkte, die wie ein Diagramm aussehen. Der Generator zeichnet das Foto stark weich, bevor Text darüber kommt.
- **Kein Falke, keine Kurse, keine Kerzen-Charts, kein Bitcoin als Motiv.**
- **Jedes Motiv höchstens einmal in 30 Tagen** (Teil 3, Motiv-Bank).
- **Fehlt ein passendes Motiv** zum Thema der Kennzahl, nimmt der Generator Look A oder D statt B.

## register.csv
Eine Zeile je Motiv, damit die Herkunft belegt ist:

```
datei,thema,quelle,erzeugt_am,abgelegt_von,hinweis
energie-01.jpg,energie,grok,2026-10-31,Ben,
```

Keine Zugangsdaten, Links mit Tokens oder Prompts mit persönlichen Daten in die Datei.
