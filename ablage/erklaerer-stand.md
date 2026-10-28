# Stand Donnerstags-Erklärer

**Lauf vom 28.10.2026, 18:45 Berliner Zeit.** Diese Datei wird bei jedem Lauf
vollständig ersetzt. Sie trägt nur den Kopfteil der Meldung an Ben, keine
Skripte, keine Titel, keine Uploadfelder, weil dieses Repo öffentlich ist.

## Thema

Wann ist eine Münze wirklich verloren. Der Erklärer für Do 29.10.2026
beantwortet die häufigste Zuschauerfrage aus dem Uhrwerk-Bericht vom
26.10.2026 und zeigt an unserer eigenen Wochenreihe, dass der ruhende Haufen
in beide Richtungen wandert.

## Prüfzeilen

- Short-Skripte enthalten: **4 von 4, Manifest: ja**
- Telegram-Grafik: **ja, bei 390 px geprüft**
- **Differenzen gegengerechnet: ok** (12 Rechnungen, beide Endpunkte je Zeile)
- **Quellen geprüft: ok**, vier Angaben im Lauf ergänzt
- `pruefung.py`: **BESTANDEN** für die sechs Blöcke und für die vier Shorts
- `text_wache.py`: Erklärer 73 Stellen, 2 zum Ansehen, 3 Hinweise, alle
  angesehen und richtig. Shorts 70 Stellen, **0 zum Ansehen**, 3 Hinweise,
  alle drei die eigene Zählung des Freitags. Echtzeit-, Demut- und
  Kursziel-Wache leer
- Grafiknorm: **sauber**, gemessen mit einer node-Fassung derselben Prüfungen,
  weil `scripts/grafik_check.py` in diesem Container kein python-playwright
  findet und sein fest verdrahteter Browserpfad auf eine ältere
  Container-Generation zeigt
- `secret_scan.py --staged`: sauber

## Zahlen, die auf „offen" stehen

| Zahl | letzte echte Messung |
| --- | --- |
| Tagesgebühren der Kette | **26.10.2026**, und zwei Dateien widersprechen sich: `weekly-history.json` trägt für diese Woche einen Wert, `weekly.json` hat das Feld in allen 16 Wochenzeilen leer |
| Anteil der 100 größten Adressen (`kohorte.json`) | **04.10.2026**, also 24 Tage alt |
| `holder_baselines` m3 und y1, `entityx_baselines` y1 in `weekly.json` | nie gefüllt |

Alle Zahlen, die im Erklärer oder in einem der vier Shorts gesprochen werden,
sind geprüft und tragen Stand und Quelle.

## Datenausfall

- **Gebührenreihe.** In `weekly.json` steht `fees_day` in allen 16
  Wochenzeilen auf `null`, `fees_7d` ebenfalls. In `weekly-history.json` stehen
  die Wochen vom 24.08., 28.09., 05.10., 12.10. und 19.10.2026 auf `null`.
  Keine Gebührenzahl steht in dieser Lieferung.
- **`data/kohorte.json`** hat nur zwei Messpunkte, der jüngste vom 04.10.2026.
  Die Reihe steht über sieben Tage still und ist nicht verwendet.

## Ausreißer

- **`covenant_tx` springt am 26.10.2026 von 141 auf 747**, also auf mehr als
  das Fünffache der Vorwoche. Ein Rückfall ist noch nicht messbar, die Reihe
  endet mit dieser Lesung. Die Zahl steht in keinem Satz des Erklärers und in
  keinem der vier Shorts.
- **`active_addr` 22.125 (31.08.) und 21.170 (07.09.2026)** bleiben der
  bekannte Ausreißer der Reihe, drei- bis viermal über dem Rest, danach
  Rückfall auf 6.394. Bereits in Woche 44 vermerkt, nicht verwendet.
- Der Sprung von `active_addr` 5.672 (19.10.) auf 7.150 (26.10.2026) ist mit
  plus 26 Prozent **kein** Ausreißer nach unserer Regel.

## Was Ben entscheiden muss

1. **Kein von dir freigegebener Test.** Der Uhrwerk-Bericht vom 26.10.
   schlägt zwei vor, für die langen Videos den Einstieg in Sekunde 0 und für
   die Shorts Zahl gegen Frage. Eine Freigabe steht in keiner Datei des Repos.
   `test` steht deshalb bei allen vier Shorts auf `keiner`, und Punkt 13b des
   Auftrags greift nicht.
2. **Zwei Video-IDs sind zu prüfen**, bevor ein Link gesetzt wird. Eine steht
   in zwei Dateien unterschiedlich, die andere fehlt in der
   Veröffentlichungsliste.
3. **Das vidIQ-Guthaben ist aufgebraucht.** Nach elf Messungen stand es auf 4,
   ein Aufruf kostet 5, Nachfüllung laut Dienst am 03.11.2026. Deshalb fehlen
   die drei Thumbnail-Bewertungen und ein Titel-Score.
4. **Der angeheftete Kommentar des Erklärers ist länger als 180 Zeichen**,
   weil die Datumszeile für zwei ältere Endpunkte dazugehört. Soll er kürzer
   werden, fällt das Datum weg.
5. **Ob die Telegram-Grafik gepostet wird**, entscheidest du.

## Branch

**Branch `review/erklaerer-2026-10-29` in `pulse-studio`, Head `0dd9ef6`,
bereit zum Merge.**

Diese Ablage liegt auf `claude/ablage-erklaerer` in `kaspa-pulse`.
