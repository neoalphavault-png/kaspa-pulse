# Bericht 6.11.2026: Dataset-Lizenz, Newsletter-Archiv ohne Wenn-dann-Sätze, Textkorrekturen (Nachtrag 7.11.)

Auftrag von Ben vom 6.11.2026, Frist So 8.11. 12:00, vor dem Newsletter am Sonntag. Claude prüft, Ben merged.

## Nachtrag 7.11.2026, Bens Entscheidungen
1. **Alert-Satz 14.9. und 21.9.:** ersetzt wie am 28.9. Dort steht jetzt „reward cuts and the chain's largest wallet moving get checked several times a day, not once a week, and posted when a check finds one.“
2. **Description kaspa-hashrate:** vorher 176 Zeichen, also zu lang. Zwei Vorschläge, beide mit dem Suchbegriff vorne:
   - **A, genommen, 148 Zeichen:** „Kaspa hashrate in PH per second, dated and sourced, with weekly averages of the last two months and the highest daily average in the source history.“
   - **B, 144 Zeichen:** „Kaspa hashrate in PH/s, read once a day from the Kaspa REST API, with dated weekly averages and the highest daily average in the source history.“
   - **Warum A:** A nimmt „PH per second“ aus dem Titel auf und sagt in drei Worten, wofür die Seite steht, „dated and sourced“. B nennt die Quelle, ist aber technischer und für einen Suchtreffer weniger klar.
   - `seo_seiten.py` hat og:description, twitter:description und das Schema nachgezogen. `seo_pruefung.py` meldet für kaspa-hashrate keinen Fehler mehr.
3. **Rebase auf main:** Der Branch ist auf main `a095c11` neu aufgesetzt, der frühere Merge-Commit fällt dabei weg.
   - Konflikte gab es nur in den von `seo_seiten` erzeugten Dateien `data/seiten-stand.json` und `kaspa-tvl.html`. Dort habe ich den Stand von main genommen und `seo_seiten.py` neu laufen lassen.
   - **Prüfungen:**
     - `seo_seiten --pruefen` meldet „alles auf stand“.
     - `seo_pruefung` meldet 0 Fehler. Die beiden Warnungen zu kaspa-tvl (132 Zeichen) und kaspa-wallets (137 Zeichen) stammen aus Bens freigegebenen Texten vom 2.11.
     - `preis_wache` meldet 51 Seiten mit 0 Verstößen.
     - Die Selbsttests von seo_seiten, seo_pruefung, preis_wache, plausible und rahmen sind grün.
     - Secret-Scan ohne Fund.
   - **Merge:** Selbst-Merge nach der Regel vom 26.10., es sind keine Workflow-, Deploy- oder c2-Dateien betroffen.

**URLs für den Rich-Results-Test und die Validierung in Search Console:**
- https://kaspapulse.com/kaspa-covenants.html
- https://kaspapulse.com/kaspa-hashrate.html
- https://kaspapulse.com/kaspa-supply.html
- https://kaspapulse.com/kaspa-weekly.html
- https://kaspapulse.com/kcc-20.html

---

## 1. Dataset-Markup mit license und creator
- **Was fehlte:** Search Console meldete im Dataset-Schema das Feld `license`.
- **Änderung:** `scripts/seo_seiten.py` setzt in jedes Dataset `"license": "https://creativecommons.org/licenses/by/4.0/"`, aus der neuen Konstante `LIZENZ`.
- **creator:** Das Feld war schon gesetzt, als Organization Kaspa Pulse mit `url` https://kaspapulse.com/. Es bleibt so und wird jetzt im Selbsttest geprüft.
- **Betroffene Seiten:** Der Kopf ist neu geschrieben für kaspa-covenants, kaspa-hashrate, kaspa-supply, kaspa-weekly und kcc-20. In jedem Kopf kommt genau die Zeile `license` dazu.
- **Prüfung im Rich-Results-Format:** Ich habe den JSON-LD jeder der 5 Seiten nach den Vorgaben von Google für Dataset geprüft. Das Skript liegt nicht im Repo.
  - Pflicht: `name` und `description` mit 50 bis 5000 Zeichen.
  - Empfohlen: `license`, `creator` mit Typ, Name und url, `url`, `distribution` als DataDownload mit `contentUrl` und `encodingFormat` sowie `temporalCoverage` im ISO-Format.
  - Alle 5 Seiten sind ohne Befund, je genau ein Dataset.
- **Online-Prüfung:** Der Rich-Results-Test von Google und der Validator von schema.org sind aus meiner Umgebung gesperrt. Nach dem Merge bitte die 5 URLs im Rich-Results-Test laufen lassen und in Search Console „Validierung starten“.
- **Selbsttest:** `seo_seiten.py --selbsttest` hat 0 Fehler. Neu ist der Fall „dataset mit license cc by 4.0 und creator als organization mit url“.
- **kaspa-tvl.html:** Der Kopf ist mit neu geschrieben. Auf main wich die Seite schon vom Seitenstand ab, `seo_seiten.py --pruefen` meldete sie. Ohne diesen Schritt wäre der CI-Check „kopf, stand, navigation und sitemap auf stand“ rot.

## 2. Newsletter-Archiv ohne kursnahe Wenn-dann-Sätze (A4)
**Tabellenzeile in allen 8 Ausgaben vom 14.9. bis 2.11.**
- Vorher: „threshold to hold … next week“ mit „a close above $…“.
- Jetzt: „50 and 21 week lines, week to <Samstag>“ mit „$<50-Wochen-Linie> and $<21-Wochen-Linie>, source kraken“.

**Fließtext in 3 Ausgaben (19.10., 26.10., 2.11.)**
- Vorher: „a close above $… (next week) would …“.
- Jetzt: „the 50 week line sits at $… and the 21 week line at $…, source kraken, week to <Datum>.“

**Gerechnete Linienwerte**
Gerechnet mit `weekly_facts.linie`, also derselben Rechnung wie der Generator: 50 Wochen als einfaches Mittel, 21 Wochen exponentiell, Wochenschlüsse von Kraken. Stand ist jeweils die Woche, die die Ausgabe beschreibt. Die Abstände in der letzten Spalte stimmen mit denen überein, die schon im Text der Ausgaben standen.

| Ausgabe | Woche bis | 50 Wochen | 21 Wochen | Abstand zur 50-Wochen-Linie |
| --- | --- | --- | --- | --- |
| 14.9. | 12 sep | 0.037659 | 0.031219 | −6.45% |
| 21.9. | 19 sep | 0.036914 | 0.031937 | +5.98% |
| 28.9. | 26 sep | 0.036729 | 0.033388 | +30.41% |
| 5.10. | 3 oct | 0.036581 | 0.034273 | +17.88% |
| 12.10. | 10 oct | 0.036221 | 0.034865 | +12.59%, wie im Text |
| 19.10. | 17 oct | 0.035863 | 0.034908 | −1.46%, wie im Text |
| 26.10. | 24 oct | 0.035548 | 0.035012 | +1.41%, wie im Text |
| 2.11. | 31 oct | 0.035296 | 0.034790 | −7.72%, wie im Text |

**Prüfung**
- Danach steht „a close above“ in keiner Ausgabe mehr. `kurs_wenn_dann` und `preis_wache.verstoesse` finden im sichtbaren Text aller 8 Ausgaben nichts.
- **Generator für die Ausgabe 8.11.:**
  - `weekly_numbers.py` stoppt seit Commit `4583770` vom 5.11. jeden „the read“ mit einem Wenn-dann-Satz ab der Woche 2026-11-08 (`KURS_REGEL_AB`) und nennt in der Meldung den Ersatz mit Linienwert.
  - Der Selbsttest ist grün, 155 Fälle. Darin sind Fall 1 (der Wenn-dann-Satz stoppt) und Fall 2 (ein reiner Linienwert geht durch).
- **preis_wache:**
  - Die Wache prüft jetzt das ganze Archiv ab 14.9. statt erst ab 8.11. Das alte Archiv ist sauber, also darf kein solcher Satz zurückkommen.
  - Probe: Eine Ausgabe `newsletter/2026-11-08.html` mit der alten Tabellenzeile wird rot („kursnaher satz“). Die neue Zeile mit den Linienwerten bleibt grün.
  - `preis_wache.py` meldet 51 Seiten mit 0 Verstößen, der Selbsttest hat 0 Fehler. Neu ist der Fall „linienwert als daten ist nicht rot“.
- **Was nicht geändert wird:** Die Mails sind verschickt, Brevo und die Postfächer bleiben unverändert. Geändert ist nur das Archiv auf kaspapulse.com.

## 3. entity-x.html
Die Kachel „Average entry price“ heißt jetzt „Average price on deposit days“, passend zur Überschrift darüber. Sonst ist nichts an der Seite geändert.

## 4. Newsletter 14.9., 21.9. und 28.9.
- „live alerts“ heißt jetzt „wallet alerts“, am 14.9. und am 21.9. Am 28.9. stand dort schon „wallet alerts“. Das Wort im Kommentar der Datei bleibt, es beschreibt die Korrektur von damals.
- „the daily updates live at“ heißt jetzt „the daily updates are at“, in allen drei Ausgaben.
- **Bitte entscheiden:** Der Alert-Block vom 14.9. und 21.9. sagt noch „get posted the moment we count them“. Das ist derselbe Satz, den Ben am 28.9. korrigiert hat, weil der Alarm nur mehrmals am Tag prüft. Soll ich ihn wie am 28.9. ersetzen, also „get checked several times a day … and posted when a check finds one“?

## 5. datenschutz.html
- Die Überschrift „3. Live data from third-party APIs“ heißt jetzt „3. Data from third-party APIs“.
- „legitimate interest in displaying live data“ heißt jetzt „legitimate interest in displaying data from public APIs“.

## 6. utm-test.html
- **Entfernt.** Keine Seite, kein Menü und keine Sitemap verlinkt darauf.
- **Wer sie noch nennt:** Die Seite steht nur noch in Ausschlusslisten von Skripten (`seo_seiten.AUSGENOMMEN`, `seo_pruefung.NICHT_OEFFENTLICH`, `rahmen.AUSGENOMMEN`, `plausible.py`) und in alten Berichten. Die Listen bleiben, sie schaden ohne die Datei nicht. Die Selbsttests von plausible, rahmen, seo_pruefung und seo_seiten sind grün.
- **Folge:** kaspapulse.com/utm-test.html liefert nach dem Deploy 404. Die Anleitung für den UTM-Test steht weiter in `utm-regel.md` in pulse-studio.

## Prüfung gesamt
- `seo_seiten.py --pruefen` meldet „alles auf stand“. Dafür sind der Seitenstand und `dateModified` für entity-x neu geschrieben, dazu die Sitemap.
- `seo_pruefung.py --gegen origin/main` meldet 0 Fehler und 0 Warnungen.
- **Schon auf main:** `seo_pruefung.py` ohne Basis meldet die Description von kaspa-hashrate mit 176 statt höchstens 155 Zeichen. Das stammt aus #173 vom 27.10. und gehört nicht zu diesem Auftrag. Soll ich zwei kürzere Vorschläge machen?
- **Textregeln:** Kein now, live oder today in den neuen Texten. Keine Doppelpunkte, Striche oder Wenn-dann-Sätze. Jeder Linienwert trägt seine Woche und die Quelle.
- Secret-Scan ohne Fund. Keine Workflow-, Deploy- oder c2-Dateien.
