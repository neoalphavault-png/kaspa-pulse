# Stand Donnerstags-Erklärer

**Lauf vom 11.11.2026, 18:47 Berliner Zeit.** Diese Datei wird bei jedem Lauf
vollständig ersetzt. Sie trägt nur den Kopfteil der Meldung an Ben, keine
Skripte, keine Titel, keine Uploadfelder, weil dieses Repo öffentlich ist.

## Thema

Niemand zählt die Maschinen, die Kaspa minen. Der Erklärer für Do 12.11.2026
zeigt, dass die Hashrate keine Zählung ist, sondern eine Schätzung aus
Schwierigkeit und Blocktakt, und was unser eigenes Tagesprotokoll aus 88
Lesungen über ihre Schwankung sagt. Der Reward-Schnitt vom 04.11.2026 ist der
Testfall: die Woche danach liegt niedriger als die Woche davor, und eine
einzelne Nacht im selben Fenster bewegt sich stärker als der ganze
Wochenabstand.

**Warum dieses Thema.** `vidiq_outliers` für „kaspa", letzte 30 Tage, Kanäle
unter 5.000 Abos, liefert von 25 Treffern nur drei echte Kaspa-Videos, und
alle drei sind Meinungs- oder Nachrichtenstücke, die sich mit unserer
Textregel nicht bauen lassen. Zuschauerfragen gibt es laut Uhrwerk-Bericht vom
09.11.2026 keine (null Zuschauerkommentare auf beiden letzten Langvideos). Die
drei Kaspa-Punkte in `format-radar.md` sind erschöpft: einer ist als Short
beschrieben und bis zum 14.12.2026 gesperrt, einer war der Erklärer vom
05.11., einer braucht die leere Rechner-Seite. Damit greift die gleichrangige
Stufe aus Schritt 0, die Ausreißer-Form 1 des Uhrwerk-Berichts: der Irrtum in
Sekunde 0, dann die Mechanik.

**Experiment dieser Folge:** genau diese Form. Block 1 nennt zuerst, was die
Zahl nicht ist, erst Block 2 sagt, wie sie entsteht. Bisher stand in Sekunde 0
immer eine Zahl. Messgröße: Aufrufe nach 48 h gegen die Kanal-Messlatte 174
(Stand 12.10.2026) und Kommentare je Video.

## Prüfzeilen

- Short-Skripte enthalten: **4 von 4, Manifest: ja**
- Telegram-Grafik: **ja, bei 390 px geprüft**, jede Zeile lesbar
- **Differenzen gegengerechnet: ok** (14 Rechnungen, beide Endpunkte je Zeile)
- **Quellen geprüft: ok**, drei Angaben im Lauf ergänzt
- `pruefung.py`: **BESTANDEN** für die sechs Blöcke, die vier Shorts, die
  geposteten Texte und alle Rechnungen gegen die Rohdaten
- Grafiknorm: **sauber**, gemessen mit der node-Fassung der Prüfung, weil
  `scripts/grafik_check.py` in diesem Container kein python-playwright findet
- `secret_scan.py --staged`: sauber

## Zahlen, die auf „offen" stehen

| Zahl | letzte echte Messung |
| --- | --- |
| Tagesgebühren der Kette | nie gefüllt, `fees_day` steht in allen **18** Wochenzeilen auf `null` |
| `holder_baselines` m3 und y1, `entityx_baselines` y1 | nie gefüllt |
| die drei Thumbnail-Scores | **nicht messbar**, nicht wegen Guthaben (vidIQ hat 1.334 Credits und alle Titel sind frisch gemessen), sondern weil diese Sitzung keine Bilder zu vidIQ hochladen darf: die Netzrichtlinie lehnt die Verbindung ab |

Alle Zahlen, die im Erklärer oder in einem der vier Shorts gesprochen werden,
sind geprüft und tragen Stand und Quelle. Die jüngste Lesung ist vom
11.11.2026 und am Erscheinungstag einen Tag alt; alle älteren Punkte derselben
Reihe stehen mit ihrem Datum im Satz.

## Datenausfall

- **Gebührenreihe, weiter leer.** `fees_day` und `fees_7d` in `data/weekly.json`
  stehen in allen 18 Wochenzeilen auf `null`. Keine Gebührenzahl in dieser
  Lieferung.
- **Drei fehlende Tage in der Hashrate-Reihe**, 29. bis 31.08.2026. Alte Lücke
  am Anfang der Reihe, seit dem 01.09.2026 lückenlos. Steht im Skript und in
  der Beschreibung.
- **`kp/shorts/hashrate-lesungen.json` steht auf dem 07.11.2026**, das Tageslog
  auf dem 11.11. Kein Ausfall, sondern ein Nachtrag, der seit dem 08.11. nicht
  gelaufen ist. Diese Lieferung liest beide Dateien zusammen und ändert keine
  von beiden.

## Ausreißer

- **Die Hashrate-Reihe hat keinen Ausreißer nach unserer Regel.** Die Regel
  verlangt einen Einzeltag auf mehr als das Doppelte mit Rückfall; die größte
  Nachtbewegung der Reihe liegt weit darunter. Genau das ist der Inhalt der
  Folge: die Reihe ist nicht sprunghaft im Sinne der Regel, sie ist
  durchgehend unruhig.
- **`tvl_total` am 21.09.2026** und **`dex_vol` am 19.10.2026** bleiben die
  bekannten Ausreißer der Wochenreihe. Keiner von beiden wird verwendet.
- **`active_addr` am 31.08. und 07.09.2026** bleibt der bekannte Ausreißer
  dieser Reihe. Nicht verwendet.

## Eine Unstimmigkeit, gemeldet, nicht repariert

`data/weekly.json` trägt für die Zeile 09.11.2026 eine Hashrate, die im
Tageslog unter dem 10.11.2026 steht. Dieser Lauf nimmt durchgehend das
Tageslog mit dessen eigenen Datumsangaben, damit Zähler und Nenner jeder
Aussage aus demselben Lauf stammen. In keinem Satz der Lieferung steht ein
Wert aus `weekly.json`.

## Offener Punkt für Ben, Mittwochs-Short der Folgewoche

Alle vier Kennzahlen, die `kennzahl_heute()` in
`scripts/number_of_day_data.py` kennt, liegen innerhalb der 60-Tage-Sperre für
Kernzahlen. Genommen ist die mit dem größten Abstand (42 Tage) und einem
anderen Stand; der gesprochene Text nennt ohnehin keinen Wert. Die
Alternativen wären ein Mittwoch ohne Short oder eine fünfte Zeile in
`KENNZAHLEN`. Beides ist Bens Entscheidung, nicht die dieses Laufs.

## Branch und Head

- Lieferung: `pulse-studio`, Branch **`review/erklaerer-2026-11-12`**, Head
  **`319f01b`**, ein Commit, bereit zum Merge.
- Diese Datei: `kaspa-pulse`, Branch `claude/ablage-erklaerer`.
