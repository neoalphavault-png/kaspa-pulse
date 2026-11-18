# Stand Donnerstags-Erklärer

**Lauf vom 18.11.2026, 18:45 Berliner Zeit.** Diese Datei wird bei jedem Lauf
vollständig ersetzt. Sie trägt nur den Kopfteil der Meldung an Ben, keine
Skripte, keine Titel, keine Uploadfelder, weil dieses Repo öffentlich ist.

## Thema

Zwei Jahre unserer eigenen Kursreihe, und zwei Messungen darauf, die sich zu
widersprechen scheinen. Fast jeder zweite Abend schloss höher, und der Kurs
steht trotzdem um 83 Prozent tiefer. Der Erklärer für Do 19.11.2026 erklärt
den Unterschied zwischen einer Zählung und einer Veränderung an einer Reihe,
die jeder Zuschauer zu kennen glaubt, und endet bei der Arithmetik, nicht bei
einer Meinung über den Kurs. Es fällt kein Kursziel, in keine Richtung.

**Warum dieses Thema.** `vidiq_outliers` für „kaspa", letzte 30 Tage, Kanäle
unter 5.000 Abos, liefert von 25 Treffern wieder nur drei echte Kaspa-Videos,
und alle drei sind Meinungs- oder Nachrichtenstücke, die sich mit unserer
Textregel nicht bauen lassen. Zuschauerfragen gibt es keine: der
Uhrwerk-Bericht vom 16.11.2026 findet keine, und die beiden jüngsten
Langvideos tragen am 18.11.2026 je null Kommentare. Die drei Kaspa-Punkte in
`format-radar.md` sind weiter erschöpft. Damit greift die gleichrangige Stufe
aus Schritt 0, die Ausreißer-Form 2 des Uhrwerk-Berichts vom 16.11.2026:
Ereignis-Aufhänger statt Metrik. Das Ereignis ist ein Datum, nämlich der
zweite Geburtstag unserer eigenen Tagesreihe am 19.11.2026.

**Experiment dieser Folge:** die ersten dreißig Sekunden tragen eine Spannung
statt einer Zahl. Block 1 stellt zwei wahre Sätze gegeneinander und nennt als
Anlass ein Datum. Bisher stand in Sekunde 0 entweder eine Zahl (bis 05.11.)
oder ein Irrtum (12.11.). Messgröße: der gesehene Anteil nach 30 Sekunden,
der beim Erklärer vom 12.11.2026 von 94,7 auf 67,0 Prozent fällt, dazu
Aufrufe nach 48 h gegen die Kanal-Messlatte 174 (Stand 12.10.2026).

## Prüfzeilen

- Short-Skripte enthalten: **4 von 4, Manifest: ja**
- Telegram-Grafik: **ja, bei 390 px geprüft**, jede Zeile lesbar
- **Differenzen gegengerechnet: ok** (13 Rechnungen, beide Endpunkte je
  Zeile, dazu 9 weitere Werte maschinell nachgerechnet)
- **Quellen geprüft: ok**, fünf Angaben im Lauf ergänzt
- `pruefung.py`: **BESTANDEN** für die sechs Blöcke, die vier Shorts, die
  geposteten Texte und alle Rechnungen gegen die Rohdaten
- `uploadpaket_wache.py`: **sauber**
- Grafiknorm: **sauber**, gemessen mit der node-Fassung der Prüfung, weil
  `scripts/grafik_check.py` in diesem Container kein python-playwright findet
- `secret_scan.py --staged`: sauber

## Was die Prüfung gefunden hat

Zwei echte Befunde, beide behoben, beide hätten die Echtzeit-Wache ausgelöst:
im angehefteten Kommentar des Freitags-Shorts stand „live" als Verb, und der
beste Freitags-Titel trug es ebenfalls. In beiden Fällen heißt es „lebend"
und nicht „in Echtzeit", aber die Wache sucht das Wort, nicht die Bedeutung.
Der genommene Titel ist ein gleichwertiger Kandidat ohne das Wort.

## Zahlen, die auf „offen" stehen

| Zahl | letzte echte Messung |
| --- | --- |
| Tagesgebühren der Kette | nie gefüllt, `fees_day` steht in allen **19** Wochenzeilen auf `null` |
| `holder_baselines` m3 und y1, `entityx_baselines` y1 | nie gefüllt |
| die drei Thumbnail-Scores | **nicht messbar**, nicht wegen Guthaben (vidIQ hat 579 Credits und alle 16 Titelkandidaten sind frisch gemessen), sondern weil diese Sitzung keine Bilder zu vidIQ hochladen darf. In diesem Lauf erneut versucht, der Upload scheitert an der Netzrichtlinie |

Alle Zahlen, die im Erklärer oder in einem der vier Shorts gesprochen werden,
sind geprüft und tragen Stand und Quelle. Die jüngste Lesung der Kursreihe ist
vom 17.11.2026 und am Erscheinungstag zwei Tage alt; sie ist der letzte volle
utc-Tag, den die Datei führt. Alle älteren Punkte derselben Reihe stehen mit
ihrem Datum im Satz.

## Datenausfall

- **Gebührenreihe, weiter leer.** `fees_day` und `fees_7d` in
  `data/weekly.json` stehen in allen 19 Wochenzeilen auf `null`. Keine
  Gebührenzahl in dieser Lieferung.
- **`data/covenants-log.json` steht auf dem 25.10.2026**, seit 24 Tagen ohne
  neuen Eintrag. Keine Covenant-Zahl in dieser Lieferung.
- **`kp/shorts/hashrate-lesungen.json` steht weiter auf dem 07.11.2026.** Der
  Nachtrag ist seit dem 08.11. nicht gelaufen. Diese Lieferung liest die Datei
  nicht und ändert sie nicht.
- **Die Kursreihe selbst hat keine Lücke.** Maschinell geprüft, 729
  aufeinanderfolgende Kalendertage, bei Bitcoin im selben Fenster ebenso.

## Ausreißer

- **Die Kursreihe hat keinen Ausreißer nach unserer Regel.** Die Regel
  verlangt einen Einzeltag auf mehr als das Doppelte mit Rückfall; die größte
  Tagesbewegung der Reihe liegt weit darunter. Die beiden Extremtage stehen im
  Skript mit Stichtag.
- **`tvl_total` am 21.09.2026** und **`dex_vol` am 19.10.2026** bleiben die
  bekannten Ausreißer der Wochenreihe. Keiner von beiden wird verwendet.
- **`active_addr` und `covenant_tx` am 31.08. und 07.09.2026** bleiben die
  bekannten Ausreißer dieser Reihen. Nicht verwendet.
- **Ein Reihenbruch, kein Ausreißer:** `tps` in `data/weekly.json` enthielt
  bis zum 14.09.2026 auch Coinbase-Transaktionen, seit dem 16.09.2026 nur
  Standardtransaktionen. Der Dienstags-Short vergleicht deshalb keinen
  tps-Wert vor dem 16.09.2026.

## Drei Dinge, die Ben nachsehen sollte

1. **Der Mittwochs-Short der Woche 47 vom 18.11.2026.** Sein Manifest nagelt
   die Kennzahl `mined_left` fest, die Automatik hat an dem Tag aber
   `hashrate_move` gezogen (`data/number-of-day-log.json`, Zeile 2026-11-18).
   Der Nachtrag bricht in genau diesem Fall ab. Steht im Bild eine Zahl?
2. **Die Mittwochs-Kennzahl der Folgewoche ist eine Entscheidung.** Von den
   vier Kennzahlen, die `scripts/number_of_day_data.py` kennt, ist eine seit
   dem 01.11.2026 preisgesperrt und kommt gar nicht mehr dran; die drei
   übrigen liegen in der 60-Tage-Sperre. Genommen ist die mit dem größten
   Abstand (42 Tage) und einem anderen Stand. Die Alternativen wären ein
   Mittwoch ohne Short oder eine fünfte Zeile in `KENNZAHLEN`.
3. **Der Shorts-Test aus dem Uhrwerk-Bericht ist weiter nicht freigegeben.**
   Fünfte Woche in Folge „Test läuft, 0 von 7". `test` steht bei allen vier
   Shorts auf `keiner`.

## Eine Korrektur im Bestand

Eine Video-ID in `pulse-studio/docs/kanal-links.md` war falsch: der Erklärer
vom 22.10.2026 stand dort mit einem kleinen L am Ende statt mit einem großen
i. Korrigiert, dazu acht IDs nachgetragen, alle aus einem Abruf des eigenen
Kanals. Drei davon wurden in früheren Paketen als „offen" geführt. Das
Manifest der Woche 47 trägt die falsche Fassung weiter und wird nicht
angefasst, es liegt in einem eigenen PR.

## Branch und Head

- Lieferung: `pulse-studio`, Branch **`review/erklaerer-2026-11-19`**, Head
  **`8aa439e`**, ein Commit, bereit zum Merge.
- Diese Datei: `kaspa-pulse`, Branch `claude/ablage-erklaerer`.
