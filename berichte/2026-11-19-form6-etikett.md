# Bericht 19.11.2026: Vier Punkte vom 13.11., Form 6 mit Quelle statt „counted“

Auftrag von Ben vom 13.11.2026. Keine Workflow-, Deploy-, c2- oder Secret-Datei ist geändert, deshalb gilt der Selbst-Merge nach der Regel vom 26.10.

## 1. Zahl 5 auf /whales und im Cheat Sheet
- **Erledigt am 17.11.** in `fe71ccc0` von einer anderen Claude-Sitzung, Bericht `berichte/2026-11-17-design-runde.md`, also vor der Frist am 18.11.
  - Ausgabe 2 ist korrigiert. Nur Zahl 5 ist neu, „around 5 dec“ und „next block reward cut, estimate“, ohne Uhrzeit. Nummer und die anderen sieben Zahlen bleiben.
  - Das PDF unter kaspapulse.com, /whales und das Log sind neu gebaut.
  - Die Dezember-Ausgabe trägt dieselbe Form, weil `cheat_sheet.py` beide Formen aus `scripts/stufe_schaetzung.py` holt.
- **Heute geprüft:** `whales/index.html` zeigt „around 5 dec / next block reward cut, estimate / 1.94 to 1.84 KAS per block · about 18 days from 17 nov“. `whales_seite.py --pruefen` meldet „passt“.
- **Neu in diesem PR, der Selbsttest aus dem Auftrag:** Ein vergangener Schritt darf nicht als „next“ erscheinen.
  - `cheat_sheet.stufe_vorbei(p, heute)` meldet den Tag, wenn der Schritt aus der Probe heute schon erreicht ist.
  - Selbsttest `cheat_sheet.py`: Eine Probe mit „4 nov“ fällt am 13.11. auf, am 3.11. nicht. Die Korrektur vom 17.11. nennt mit 5 dec einen künftigen Schritt und kein „4 nov“.
  - `whales_seite.py --pruefen` endet jetzt mit Exit 1, wenn Zahl 5 einen vergangenen Schritt als nächsten nennt.

## 2. Form 6, das Etikett für den DAA score
- **Vorher:** In Datumszeile und Instagram-Caption stand „counted by kaspa pulse“, in Zeile 2 für X, Threads und Discord „counted by the network's daa score, …“.
- **Jetzt:** „source kaspa rest api“.
  - Datumszeile: „… · source kaspa rest api“.
  - Zeile 2: „The DAA score on 19 Nov 2026, 14:00 UTC, source Kaspa REST API.“
  - Caption: „Source Kaspa REST API.“
- **Warum „source“:**
  - Form 6 liest `virtualDaaScore` aus `api.kaspa.org/info/blockdag`, siehe `messen_6`.
  - „counted“ steht nur für unsere eigene Zählung. Den DAA score zählen nicht wir, ihn zählt jeder Knoten nach dem Protokoll.
  - „computed“ steht für Werte, die wir aus festen Protokollregeln ausrechnen, wie den Emissionsplan. Den DAA score rechnen wir nicht aus, wir lesen ihn ab.
  - Damit bleibt „source“ mit der API, aus der die Zahl kommt. So steht es auch bei den anderen Formen, die von der REST-API lesen (Form 1 und Form 8, Hashrate).
- **Stichtag für Instagram:** Er bleibt der Tag der Messung. Der Tag steht jetzt in Zeile 2, also findet `ig_stichtag` ihn dort.
- **Selbsttest `tagesgrafik.py`:**
  - Herkunft und Datumszeile enden auf „source kaspa rest api“.
  - Kein Kanal sagt „counted“, alle nennen die Quelle.
  - Der Stichtag ist der Tag der Messung.
  - Ein Testname, der Form 6 „eigene Zählung“ nannte, heißt jetzt „mit dem messtag“.
- **Keine weitere Stelle** im Code nennt den DAA score „counted“. Nur `data/threads-post-log.json` enthält die alten Texte vom 24.10. und 1.11. Das ist ein Log und bleibt so.
- **Seiten:** Keine Seite trägt Form 6, deshalb war nichts neu zu bauen.

## 3. Datenschutzseite
- **Erledigt am 17.11.** in `fe71ccc0`: „Last updated: November 2026“. Live geprüft im Bericht vom 17.11.

## 4. Merge bei Secrets
Ist notiert. Jeder PR mit Bezug zu Secrets, auch `.secret-scan-allow`, geht an Ben zum Mergen.

## Prüfung
- **Selbsttests mit 0 Fehlern:** tagesgrafik, cheat_sheet, whales_seite, stimme, instagram, content_wache und preis_wache. threads hat 96 Fälle, 0 falsch.
- **Seiten:** `whales_seite.py --pruefen` meldet „passt“, ohne vergangenen Schritt.
- **Secret-Scan:** ohne Fund.

## Offen für Ben
- **/whales veraltet jeden Monat:** Das Cheat Sheet erscheint am 1. eines Monats, der Schritt fällt um den 4. oder 5. Die Dezember-Ausgabe nennt also ab etwa 6.12. wieder einen vergangenen Schritt als „next“, bis zum 1.1. `--pruefen` meldet das, ändert es aber nicht. Es gibt drei Wege:
  - eine Korrektur nach jedem Schritt mit `cheat_sheet.py --korrektur-senkung`, das braucht eine Workflow-Änderung als PR an dich,
  - die Ausgabe erst nach dem Schritt bauen, etwa am 6.,
  - Zahl 5 auf /whales im Browser aus dem Emissionsplan rechnen.
- **Zwei Blockzahlen in Form 6:** Zeile 1 rundet ab („552 million“), die Zahl im Bild und auf Threads rundet („553 million“). Mit den Testwerten stehen im Discord-Text 552 und im Threads-Text 553. Nicht geändert, das ist ein anderer Punkt. Soll Zeile 1 auch runden?

## Kopf
Die Änderung steht in `147879ef`. Dieser Bericht liegt als eigener Commit darauf.
