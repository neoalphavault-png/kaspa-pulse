# Stand Donnerstags-Erklärer

**Lauf vom 04.11.2026, 18:36 Berliner Zeit.** Diese Datei wird bei jedem Lauf
vollständig ersetzt. Sie trägt nur den Kopfteil der Meldung an Ben, keine
Skripte, keine Titel, keine Uploadfelder, weil dieses Repo öffentlich ist.

## Thema

Wie viel von Kaspa in den tausend größten Adressen liegt. Der Erklärer für
Do 05.11.2026 zählt die Rangliste vom 01.11.2026 selbst und zeigt, dass die
übliche Schlagzeile und die ehrliche Zahl zwei verschiedene Zahlen sind.
Gewählt als oberster offener Kaspa-Punkt aus `format-radar.md`, weil
`vidiq_outliers` ohne Guthaben nicht messbar ist und es laut Uhrwerk-Bericht
vom 02.11.2026 **keine Zuschauerfragen** gibt (null Zuschauerkommentare auf
beiden letzten Langvideos).

## Prüfzeilen

- Short-Skripte enthalten: **4 von 4, Manifest: ja**
- Telegram-Grafik: **ja, bei 390 px geprüft**, jede Zeile lesbar
- **Differenzen gegengerechnet: ok** (11 Rechnungen, beide Endpunkte je Zeile)
- **Quellen geprüft: ok**, zwei Angaben im Lauf ergänzt
- `pruefung.py`: **BESTANDEN** für die sechs Blöcke, die vier Shorts, die
  geposteten Texte und alle Rechnungen gegen die Rohdaten
- Grafiknorm: **sauber**, gemessen mit derselben node-Fassung der Prüfungen wie
  am 29.10., weil `scripts/grafik_check.py` in diesem Container kein
  python-playwright findet
- `secret_scan.py --staged`: sauber, in beiden Repos

## Zahlen, die auf „offen" stehen

| Zahl | letzte echte Messung |
| --- | --- |
| Tagesgebühren der Kette | nie gefüllt, `fees_day` steht in allen **17** Wochenzeilen auf `null` |
| `holder_baselines` m3 und y1, `entityx_baselines` y1 | nie gefüllt |
| alle vidIQ-Werte dieses Laufs (Titel-Scores, Thumbnail-Scores, Suchvolumen, Ausreißer) | **nicht messbar**, Guthaben 0, Auffüllung erst 24.11.2026 |

Alle Zahlen, die im Erklärer oder in einem der vier Shorts gesprochen werden,
sind geprüft und tragen Stand und Quelle. Der Hauptstichtag ist der
01.11.2026, die beiden fremden Zahlen stehen auf dem 02.11.2026.

## Datenausfall

- **Gebührenreihe.** Unverändert leer, siehe oben. Keine Gebührenzahl steht in
  dieser Lieferung.
- **`data/kohorte.json` ist kein Datenausfall mehr.** Die Datei war bis zum
  04.10.2026 gefüllt und damit 28 Tage alt, **die Rohdaten für den 11.10.,
  18.10., 25.10. und 01.11.2026 liegen aber vollständig im Repo**.
  `python3 scripts/kohorte.py` schreibt alle vier Wochen in einem Lauf nach,
  lokal geprüft. Die Datei ist in dieser Lieferung bewusst **nicht geändert**,
  weil ein Push auf `claude/**` sofort nach `main` geht.
- **vidIQ.** Kein Zugriff in diesem Lauf, Guthaben 0. Das ist der zweite Lauf
  in Folge ohne Messungen; die für den 03.11.2026 angekündigte Auffüllung ist
  nicht eingetroffen, der Dienst nennt jetzt den 24.11.2026.

## Ausreißer

- **`tvl_total` am 21.09.2026** und **`dex_vol` am 21.09. und 19.10.2026**
  sind Ausreißer nach unserer Regel (mehr als das Doppelte, danach Rückfall).
  Keiner wird verwendet.
- **`active_addr` 31.08. und 07.09.2026** bleibt der bekannte Ausreißer der
  Reihe. Nicht verwendet.
- **Der `covenant_tx`-Sprung vom 26.10.2026 ist keiner mehr.** 141 auf 747 auf
  **426**: der Rückfall liegt über der Hälfte des Spitzenwerts, die Regel
  greift nicht. Der Vorbericht hatte ihn als offenen Ausreißer gemeldet.

## Was Ben entscheiden muss

1. **Der CTA-Satz hat drei Fassungen im Umlauf**, und Ben spricht ihn am
   Donnerstag. Genommen ist die wörtliche Fassung aus dem Auftrag mit
   17 Wörtern. Im Repo stehen zwei andere, eine mit einem zusätzlichen Wort
   und eine mit einem anderen zweiten Satz. Vor der Aufnahme entscheiden.
2. **Kein von Ben freigegebener Test.** Der Uhrwerk-Bericht vom 02.11. schlägt
   zwei vor, für die langen Videos die Länge 9 bis 12 Minuten und für die
   Shorts den Einstieg in Sekunde 0. Eine Freigabe steht in keiner Datei
   beider Repos. `test` steht deshalb bei allen vier Shorts auf `keiner`, und
   Punkt 13b des Auftrags greift nicht.
3. **Das vidIQ-Guthaben ist leer bis zum 24.11.2026.** Kein Titel und kein
   Thumbnail dieses Laufs ist gemessen, weder beim Erklärer noch bei den vier
   Shorts. Es wurde keine Zahl geraten.
4. **Eine Video-ID bleibt zweideutig.** Zwei Dateien im Repo schreiben sie
   unterschiedlich, und aus diesem Container ist die Videoplattform nicht
   erreichbar, die Probe konnte also nicht laufen. Vor dem Setzen der Endcard
   einmal aufrufen.
5. **Der angeheftete Kommentar des Erklärers ist länger als 180 Zeichen**,
   weil die Datumszeile für zwei Stichtage dazugehört. Soll er kürzer werden,
   fällt die Zeile weg.
6. **`scripts/kohorte.py` einmal laufen lassen**, dann ist die Wochenreihe
   wieder aktuell und der nächste Lauf meldet sie nicht erneut als alt.
7. **Ob die Telegram-Grafik gepostet wird**, entscheidet Ben.

## Branch

**Branch `review/erklaerer-2026-11-05` in `pulse-studio`, Head `5dfc11e`,
bereit zum Merge.**

Diese Ablage liegt auf `claude/ablage-erklaerer` in `kaspa-pulse`.
