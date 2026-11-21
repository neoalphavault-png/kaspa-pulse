# Bericht 21.11.2026: Zahl des Tages, Themengruppen

Nachtrag von Ben vom 21.11.2026, Frist Mi 25.11. 16:00 Berlin. Geändert sind nur `scripts/number_of_day_data.py` und dieser Bericht. Keine Workflow-Änderung, deshalb Selbst-Merge nach der Regel vom 26.10. Den Vorschlag für den Workflow des Adress-Logs macht ein eigener PR an Ben (Punkt 3).

## 1. Themengruppen
- **`GRUPPEN` in `number_of_day_data.py`:**
  - hashrate: hashrate_move, hashrate_year, hashrate_consequence
  - angebot: mined_left, emission_year
  - adressen: whale_weight, top_share, holders_1kas
  - bloecke: blocks_per_day, blocks_since_cut
  - schritt: cut_today, cut_countdown
  - tokens: kcc20_count
- **Regeln in `choose()`**, zusätzlich zu denen vom 20.11.:
  - Keine Gruppe an zwei Folgetagen.
  - „hashrate“ höchstens einmal in sieben Tagen, jede andere Gruppe höchstens zweimal. Die Zählung steht in `gruppen_in_tagen`.
  - Die Gruppe „schritt“ ist in den 12 Tagen vor einem Schritt ausgenommen.
  - **Meine Ergänzung:** Die Gruppe „schritt“ ist auch am Tag des Schritts selbst ausgenommen. Sonst hätte am 5.12. die Gruppenregel `cut_today` gesperrt, weil am 4.12. der Countdown lief. Das ist der eine Tag, an dem die Meldung des Schritts dran sein muss.
- **Selbsttest:**
  - hashrate_year nach hashrate_move am Vortag ist gesperrt.
  - Ein zweites Hashrate-Thema in sieben Tagen ist gesperrt, nach sieben Tagen ist es wieder frei.
  - Adressen zweimal in sieben Tagen geht, ein drittes Mal nicht.
  - Der Countdown in den 12 Tagen vor dem Schritt ist frei, weiter vorn gilt die Grenze.
  - cut_today kommt am Tag des Schritts.
  - Jeder Kandidat hat eine Gruppe.

## 2. Simulation und Plan, neu gerechnet
- **Simulation 21.10. bis 20.11.** mit den Tageswerten aus dem Log, wie am 20.11.:

| Tag | Kandidat | Gruppe |
| --- | --- | --- |
| 21.10. | emission_year | angebot |
| 22.10. | whale_weight | adressen |
| 23.10. | mined_left | angebot |
| 24.10. | cut_countdown | schritt |
| 25.10. | hashrate_move | hashrate |
| 26.10. | holders_1kas | adressen |
| 27.10. | blocks_since_cut | bloecke |
| 28.10. | cut_countdown | schritt |
| 29.10. | top_share | adressen |
| 30.10. | blocks_per_day | bloecke |
| 31.10. | mined_left | angebot |
| 1.11. | cut_countdown | schritt |
| 2.11. | whale_weight | adressen |
| 3.11. | emission_year | angebot |
| 4.11. | cut_today | schritt |
| 5.11. | holders_1kas | adressen |
| 6.11. | kcc20_count | tokens |
| 7.11. | blocks_since_cut | bloecke |
| 8.11. | mined_left | angebot |
| 9.11. | hashrate_move | hashrate |
| 10.11. | whale_weight | adressen |
| 11.11. | none |  |
| 12.11. | top_share | adressen |
| 13.11. | none |  |
| 14.11. | emission_year | angebot |
| 15.11. | blocks_since_cut | bloecke |
| 16.11. | mined_left | angebot |
| 17.11. | hashrate_move | hashrate |
| 18.11. | whale_weight | adressen |
| 19.11. | none |  |
| 20.11. | holders_1kas | adressen |

  - Kein Kandidat und keine Gruppe stehen an zwei Folgetagen. Hashrate kommt höchstens einmal in sieben Tagen.
  - **3 Ausfälle:** 11.11., 13.11. und 19.11. Bens Grenze vom 20.11. war zwei. Nach Punkt 5 gilt jetzt „lieber ein Ausfall als ein drittes Hashrate-Thema“, und der Selbsttest lässt drei zu.
  - Mit anderen Sperrfristen für emission_year und kcc20_count verschieben sich die Lücken nur, also habe ich sie nicht angefasst. Die zwei vorgeschlagenen Kandidaten unten würden sie schließen.
- **Plan 22.11. bis 5.12.** mit dem echten Log bis 21.11. (am 21.11. lief hashrate_year) und den Werten vom 21.11. Die Hashrate vor einem Jahr ist mit 180 PH/s angenommen. „wählbar“ heißt, der Kandidat liefert eine Zahl und ist an diesem Tag nicht gesperrt.

| Tag | gewählt | Gruppe | wählbar |
| --- | --- | --- | --- |
| So 22.11. | emission_year | angebot | blocks_since_cut, emission_year, holders_1kas, kcc20_count, top_share |
| Mo 23.11. | cut_countdown | schritt | blocks_since_cut, cut_countdown, holders_1kas, kcc20_count, top_share, whale_weight |
| Di 24.11. | whale_weight | adressen | blocks_per_day, blocks_since_cut, holders_1kas, kcc20_count, mined_left, top_share, whale_weight |
| Mi 25.11. | mined_left | angebot | blocks_per_day, blocks_since_cut, cut_countdown, kcc20_count, mined_left |
| Do 26.11. | holders_1kas | adressen | blocks_per_day, blocks_since_cut, cut_countdown, holders_1kas, kcc20_count |
| Fr 27.11. | kcc20_count | tokens | blocks_per_day, blocks_since_cut, cut_countdown, kcc20_count |
| Sa 28.11. | hashrate_move | hashrate | blocks_per_day, blocks_since_cut, cut_countdown, hashrate_move |
| So 29.11. | blocks_since_cut | bloecke | blocks_per_day, blocks_since_cut, cut_countdown |
| Mo 30.11. | cut_countdown | schritt | cut_countdown |
| Di 1.12. | blocks_per_day | bloecke | blocks_per_day |
| Mi 2.12. | whale_weight | adressen | cut_countdown, whale_weight |
| Do 3.12. | mined_left | angebot | cut_countdown, emission_year, mined_left |
| Fr 4.12. | cut_countdown | schritt | cut_countdown |
| Sa 5.12. | cut_today | schritt | cut_today, emission_year, hashrate_move, hashrate_year |

  - Kein Ausfall in den 14 Tagen.
  - Hashrate kommt am 28.11. (hashrate_move, sieben Tage nach dem 21.11.) und am 5.12. nicht mehr, weil cut_today den Tag hat.
  - Die Folge hashrate_move am 28.11. und hashrate_year am 29.11. aus dem Plan vom 20.11. kommt nicht mehr vor.
  - Das Adress-Log reicht jetzt bis 20.11. (Punkt 3). Deshalb bleiben holders_1kas und top_share länger wählbar als im Plan vom 20.11.

## 3. data/address-thresholds-log.json endete am 15.11.
- **Ursache:** Kein Fehler, sondern der Takt.
  - `.github/workflows/address-thresholds.yml`, Zeile 20: `cron: "0 6 * * 1"`. Der Lauf ist wöchentlich, montags.
  - Der letzte Lauf war am Mo 16.11., verspätet um 15:07 UTC, und holte die Reihe bis zum 15.11. Kaspalytics liefert einen Tag hinterher.
  - Alle 9 Läufe seit dem 22.9. waren grün.
  - Die Zahl des Tages und /whales lesen die Reihe täglich, für sie ist eine Woche zu alt.
- **Nachgetragen:** Ein Lauf von Hand (`workflow_dispatch`, Lauf 10, 21.11. 10:00 UTC, grün) hat den 16. bis 20.11. geholt. Die Quelle lieferte alle fünf Tage. Auf main steht die Reihe jetzt bis 20.11.
- **Meldung in #ops-log:** Nein. Der Workflow hat keinen Schritt „rot nach ops-log“ wie seit #341 das covenants log, und ein leerer Lauf („nichts geaendert“) meldet sich auch nicht.
- **Was dafür nötig ist:** eine Workflow-Änderung, also ein eigener PR an Ben (#345). Er bringt
  - einen täglichen Lauf,
  - einen Schritt „rot nach ops-log“ wie in #341,
  - eine Meldung nach #ops-log, wenn ein Lauf keinen neuen Tag bringt.

## 4. Eine Schreibweise, PH/s
- **Quelle der Schreibweise „295 PH“ vom 20.11.:** `number_of_day_data.py`, `KENNZAHLEN["hashrate_move"]["fmt"]`, vorher Zeile 389. Daraus lesen hashrate_move, die Vergleichszeilen und der Short über `kennzahl_heute`. Dazu kam `cand_hashrate_consequence`, vorher Zeile 1051.
- **Jetzt:** Beide schreiben „PH/s“, wie hashrate_year. Die Tests von `kennzahl_heute` erwarten „338 PH/s“.
- **Neuer Fall im Selbsttest:** Keine Karte eines Kandidaten enthält eine Zahl mit „PH“ ohne „/s“.
- **Nicht angefasst:** „PH“ ohne „/s“ steht noch in Teststrings von `content_wache.py`, `number_of_day.py`, `weekly_numbers.py` und `x_post.py` sowie in `post_manifest.py` (Beispiel und Test). Das sind keine Ausgaben, und `post_manifest.py` fasse ich nicht an.

## 5. Vorrat ohne Hashrate
Der Plan der nächsten 14 Tage kommt ohne Ausfall aus. In der Simulation über den Herbst gab es drei. Damit es dort weniger werden, schlage ich zwei Kandidaten aus eigenen Daten vor, beide als eigene Gruppe. Gebaut sind sie nicht.
- **covenant_tx, Gruppe „covenants“:**
  - Covenant-Transaktionen je Tag gegen sieben Tage davor, aus `data/covenants-log.json`. Das Log läuft täglich, letzter Tag 19.11., zuletzt 1,208 Transaktionen.
  - source kaspalytics, Datum der Tag der Zählung.
- **exchange_kas, Gruppe „boersen“:**
  - KAS auf Börsen-Adressen gegen vier Wochen davor, aus der Wochenreihe `data/weekly-history.json` (`exchange_kas`).
  - source kaspalytics, Datum die Woche.
- Beide ohne Kurs und ohne USD. Für die drei Ausfalltage liegen Werte vor: covenants 714 (11.11.), 442 (13.11.) und 1,208 (19.11.), dazu die Börsen-Reihe bis zur Woche vom 16.11. Ob sie die Lücken ganz schließen, rechne ich nach, wenn Ben sie freigibt.

## Prüfung
- **Selbsttests mit 0 Fehlern:** number_of_day_data, mit den neuen Fällen und der Simulation, dazu content_wache und stufe_schaetzung.
- **Keine Workflow-Änderung** in diesem PR.
- **Secret-Scan:** ohne Fund.

## Kopf
Die Änderung steht in `2489cdec` und `af3900b1` auf main `bfed8228`. Dieser Bericht liegt als eigener Commit darauf.
