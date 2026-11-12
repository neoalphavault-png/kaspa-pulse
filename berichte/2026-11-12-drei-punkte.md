# Bericht 12.11.2026: Linienwerte statt Wenn-dann, „by kaspa pulse“, Reward-Stufe nur als Schätzung

Auftrag von Ben vom 12.11.2026, Frist So 15.11. 18:00 Berlin. Begonnen nach dem Merge von #314 (Cloudflare), wie verlangt. Keine Workflow-, Deploy- oder c2-Datei ist geändert, deshalb gilt der Selbst-Merge nach der Regel vom 26.10.

## a) kaspa-weekly.html, Linienwerte statt Wenn-dann-Satz
- **Weg ist** der Satz, den der Browser baute, je nach Seite des Schlusses:
  - „A weekly close above $x. That would be the first close above the 21 week average in … weeks, and it would end the longest stretch below the line in our window.“
  - „A weekly close back below $x. That would end the run above the 21 week average after … weeks …“
- **Neu ist** der reine Linienwert mit Quelle, wie `linienwert_satz` in `weekly_numbers.py`. Mit den Kerzen im Repo baut die Seite heute diesen Satz:
  > The 21 week line sits at $0.03432, source kraken. The 50 week line sits at $0.03513, source kraken. Week ending 7 november 2026.
  - Die Werte kommen aus `fmtP`, also mit 5 Stellen wie in den beiden Karten oben auf derselben Seite. `linienwert_satz` im Newsletter nutzt 6 Stellen. So stehen auf der Seite nicht zwei verschiedene Schreibweisen derselben Linie.
- **Rahmen des Satzes:** Die Überschrift „What would change our read“, das Label „the one number“ und der Absatz darunter kündigten eine Bedingung an. Ohne den Satz stimmten sie nicht mehr. Deshalb geändert:
  - Überschrift „Where the two lines sit“, Label „the line values“.
  - Absatz: „Both lines come from the same weekly closes as the chart. The 21 week line is an exponential average, the 50 week line a plain average. We report the values, never a level the close has to reach.“
  - Im Einleitungsabsatz oben steht statt „Then one sentence on what would change our read“ jetzt „Then where both lines sit, as plain values with their source.“
- **`preis_wache.py` liest jetzt auch Inline-JavaScript (Regel 2):**
  - Die Textstücke eines Skripts werden über `+` zu Sätzen verbunden, Kommentare fallen weg. JSON-LD und externe Skripte sind ausgenommen.
  - Ein eingesetzter Wert wird zum Platzhalter. Baut eine Funktion, die „$“ voranstellt, den Wert (wie `fmtP`), zählt er als Dollarbetrag.
  - Rot ist „a close above“, „weekly close above“ (auch „back above“ und „back below“) und „would“ im selben Satz wie ein Dollarbetrag.
  - `seite_pruefen` ruft die Prüfung auf. Damit läuft sie über `seo_pruefung` in jedem PR mit.
- **Gegenprobe:** Die alte Fassung der Seite von `origin/main` ist rot, mit zwei Treffern („A weekly close above $‹wert›.“ und „A weekly close back below $‹wert›.“). Die neue Fassung ist grün.
- **Selbsttest `preis_wache`:**
  - Der alte Satz der Wochenseite ist rot, der sichtbare Text allein sieht ihn nicht, `seite_pruefen` findet ihn.
  - Die Linienwerte sind grün.
  - „would“ mit literalem Dollarbetrag ist rot, ebenso mit „$“ vor einem eingesetzten Wert.
  - Ein Template-String ist rot.
  - „would“ ohne Dollar ist grün, ein Kommentar zählt nicht, JSON-LD und externe Skripte zählen nicht.
- **Prüfung im Browser:** `weekly_pruefung.py --selbsttest` und `--live` sind grün, Karte und Absatz sagen dasselbe.
- **Abnahme auf kaspapulse.com/kaspa-weekly.html:** am 12.11.2026 nach dem Merge (`95edfb3`), im Browser mit den ausgelieferten Daten.
  - Überschrift „Where the two lines sit“.
  - Satz: „The 21 week line sits at $0.03432, source kraken. The 50 week line sits at $0.03513, source kraken. Week ending 7 november 2026.“
  - Der Wenn-dann-Satz kommt im ausgelieferten HTML nicht mehr vor. „weekly close above“ steht dort nur noch im Rückblick „The last weekly close above it was …“, das ist ein vergangener Schluss mit Datum und keine Bedingung.
- **Live mitgeprüft:**
  - kaspa-halving.html: Kurzfakt „Next reward step around 5 December 2026, an estimate, because the step is set by DAA score. …“. Der Browser baut „next step around 5 December 2026, an estimate, because the step is set by DAA score.“ und „around 5 dec, estimate“.
  - Startseite: „daily emission steps down to 1,585,790 KAS around 5 dec, estimate“.
  - /whales: „around 4 nov / next block reward cut, estimate“.

## b) „by kaspa pulse“ ohne „computed“
- `scripts/whales_seite.py:97` lautet jetzt „source kaspa rest api, 7 day mean by kaspa pulse“.
- `scripts/archiv.py:62` lautet jetzt „source kraken daily candles, the average by kaspa pulse“. Daraus neu gebaut ist `method/index.html:336`.
- **Suche nach „computed by kaspa pulse“ im ganzen Repo**, ohne Groß- und Kleinschreibung, außer `berichte/`. Danach gibt es keinen weiteren Treffer außer der erlaubten Ausnahme „computed by kaspa pulse from the emission schedule“:
  - `scripts/archiv.py:70` und `:75`
  - `scripts/tagesgrafik.py:383` (`RECHNUNG`)
- **Verwandte Treffer**, gemeldet und nicht geändert:
  - `scripts/archiv.py:63`, die Kurzform derselben Kennzahl: „source kraken, average computed“.
  - `newsletter/2026-10-19.html:182`, `2026-10-26.html:178`, `2026-11-02.html:178` und `2026-11-09.html:169`: „the two averages are computed by us“.
  - `data/covenants/abgleich-2026-10-09/METHOD.md:54`: „Nothing else is computed by us.“

## c) Die nächste Reward-Stufe nur als Schätzung
- **Eine Stelle für beide Formen:** `scripts/stufe_schaetzung.py`.
  - Kurz: `kurz(d)` ergibt „around 5 dec, estimate“.
  - Im Fließtext: `lang(d)` ergibt „around 5 December 2026, an estimate, because the step is set by DAA score“.
  - Keine Uhrzeit. Alle Textskripte holen die Form dort ab.
- **Die Wache `verstoesse(text, heute)`:**
  - Ein Satz fällt auf, wenn er von einer Stufe spricht (reward, step, cut, halving, emission, minted, KAS a day) und ein Datum nach heute nennt, aber nicht „around“ und „estimate“ trägt.
  - Er fällt auch auf, wenn er eine Uhrzeit auf die Minute nennt.
  - `seite_verstoesse` prüft eine fertige Seite Block für Block, dazu JSON-LD und Meta-Beschreibungen.
  - `preis_wache.seite_pruefen` ruft sie als Regel 3 auf, damit läuft sie in jedem PR über `seo_pruefung` mit.
- **Geänderte Quellen und Seiten:**

| Stelle | vorher | jetzt |
| --- | --- | --- |
| `index.html`, h2 (aus `startseite.py`) | daily emission steps down to 1,585,790 KAS on 5 dec | … around 5 dec, estimate |
| `index.html`, Grafiktitel | 1,585,790 KAS a day on 5 dec, after 1,680,086 on 4 nov | 1,585,790 KAS a day from around 5 dec, estimate, after 1,680,086 on 4 nov |
| `index.html`, Teilen-Text für X | … on 5 dec. | … around 5 dec, estimate. |
| Wochenseiten `week/…` (18 Stück, aus `startseite.py` über `archiv.py`) | on 5 aug, on 4 sep … | around 5 aug, estimate … |
| `kaspa-halving.html`, Kurzfakt (aus `seiten_zahlen.py`) | Next reward step on 5 December 2026 around 00:15 UTC, … | Next reward step around 5 December 2026, an estimate, because the step is set by DAA score. Block reward from … |
| `kaspa-halving.html`, zwei FAQ-Antworten, sichtbar und im JSON-LD | … is on 5 December 2026 around 00:15 UTC … / … is on 5 December 2026 … | … is around 5 December 2026, an estimate, because the step is set by DAA score … |
| `kaspa-halving.html`, im Browser gebaut (`cdCap`, `nxDate`) | expected around dec 5, 2026, 01:15 gmt+1, shown in your local time … / ≈ dec 5, 2026 | next step around 5 December 2026, an estimate, because the step is set by DAA score. / around 5 dec, estimate |
| `kaspa-mining.html`, Tabelle und FAQ (aus `seiten_zahlen.py`) | until 5 December 2026 around 00:15 UTC / computed, on 5 December … / the next step is on 5 December 2026 | until around 5 dec, estimate / computed, around 5 dec, estimate / the next step is around 5 December 2026, an estimate, … |
| Threads und Discord, Tagesgrafik Form 3 (`tagesgrafik.py`) | Next step 5 Oct 2026, 03:15 UTC, computed by Kaspa Pulse … | Next step around 5 Oct, estimate, computed by Kaspa Pulse from the emission schedule. |
| Tagesgrafik Form 3, Bild und X-Entwurf | the next step, 5 oct 2026, 03:15 utc / on 5 oct it goes from … | the next step around 5 oct, estimate / the next step, around 5 oct, estimate, takes it from … |
| Zahl des Tages am Tag der Stufe, Discord und Telegram (`number_of_day_data.py`) | kaspa block reward, falls on 5 dec / … stop being minted from 5 dec on. | kaspa block reward, falls around 5 dec, estimate / … stop being minted from this step on. |
| Reward-Cut-Alarm, Discord (`reward_cut_alert.py`) | the next step is estimated for 5 december 2026. / the estimate right now is … the day can still shift a little … | the next step is around 5 December 2026, an estimate, because the step is set by DAA score. / the step is around …, an estimate, … |
| /whales, Karte 5 (`whales_seite.py`) | 4 nov / next block reward cut | around 4 nov / next block reward cut, estimate |
| Newsletter-Zeile „next cut“ | saturday 5 dec, reward to 1.8354 kas; … | around 5 dec, estimate, reward to 1.8354 kas; … |

- **Newsletter:** Ein Skript, das die Zeile baut, gibt es nicht. Die Montagsroutine schreibt die Ausgabe nach der letzten Ausgabe. Deshalb ist die Zeile in `newsletter/2026-11-09.html` geändert, das ist die Vorlage für den 16.11. `preis_wache` prüft jede Ausgabe ab dem 14.9. und meldet eine neue Ausgabe ohne Schätzung rot.
- **Zeilennummern aus dem Auftrag:** `index.html` 340 und 343 stehen nach dem Bot-Lauf jetzt auf 332 und 335. Die Zeilen in `kaspa-halving.html` heißen Kurzfakt, die beiden FAQ-Antworten und ihr JSON-LD. Alle sind erfasst.
- **Selbsttests:**
  - `stufe_schaetzung` prüft beide Formen. Alle alten Sätze sind rot, darunter auch „the next cut lands december 24“.
  - Grün sind die neuen Sätze, vergangene Stufen („stepped down on 4 nov“), ein Messtag mit Uhrzeit, eine Wochenseite vom Juli ohne Jahr und ein Countdown in Tagen. „5 jan“ im Dezember zählt als künftig.
  - Seite mit Tabelle und JSON-LD: Die Stufenzeile ist rot, die Hashrate-Zeile mit Uhrzeit nicht.
  - Neue Fälle in `startseite`, `seiten_zahlen`, `tagesgrafik` (Form 3 über Bild, X, Threads, Discord, Instagram und Antwort), `number_of_day_data`, `reward_cut_alert` und `whales_seite`.
- **Seiten:** `stufe_schaetzung.py` über alle 44 öffentlichen Seiten ergibt 0 Verstöße, vorher waren es 13.

## Prüfung
- **Selbsttests ohne Fehler:**
  - stufe_schaetzung, preis_wache, seiten_zahlen, startseite, archiv, whales_seite, reward_cut_alert, number_of_day_data, tagesgrafik, stimme, web_analytics, weekly_numbers, seo_seiten, seo_pruefung, content_wache, karussell, cheat_sheet und instagram
  - threads mit 96 Fällen, 0 falsch
- **Browser:** `weekly_pruefung --selbsttest` und `--live` grün.
- **Seitenprüfungen:**
  - `preis_wache` meldet 53 Seiten mit 0 Verstößen.
  - `seo_pruefung --gegen origin/main` meldet 0 Fehler und 0 Warnungen.
  - `seo_seiten --pruefen` meldet „alles auf stand“.
  - `startseite --pruefen` meldet „index.html passt“ und „archiv passt“.
  - `whales_seite --pruefen` meldet „passt“.
  - `web_analytics --pruefen` ist grün.
- **Syntax:** node-Prüfung aller Inline-Skripte von `kaspa-halving.html` ohne Fehler.
- **Daten:** `kaspa-mining.html` ist mit derselben Messung neu gesetzt, die schon auf der Seite stand (342.1 PH/s, 12 November 2026 15:16 UTC). Es kam also keine neue Zahl dazu. `kaspa-tvl.html` ist nicht angefasst.
- **Secret-Scan:** ohne Fund.

## Offen für Ben
- **Halving-Countdown:** Die Seite zählt weiter Tage, Stunden, Minuten und Sekunden bis zur geschätzten Stufe. Eine Uhrzeit steht nicht mehr da, der Zähler wirkt aber genauer, als die Stufe ist. Soll er nur noch Tage zeigen?
- **Cheat Sheet (PDF):** `cheat_sheet.py:838` und `:914` schreiben „next block reward cut, 13:45 utc“ und das Datum ohne „around“. Nicht geändert, weil das PDF nicht im Auftrag stand und das Layout feste Breiten hat. Die Seite /whales zeigt die Karte schon als Schätzung. Soll das PDF nachziehen?
- **Reward-Cut-Alarm:** Der Titel sagt „the reward gets cut tomorrow“ und „it happened. the reward just got cut“, der Text sagt „percent“. Das sind Treffer gegen die Textregeln (Echtzeitwörter, % statt percent). Nicht geändert, außerhalb des Auftrags.
- **Zahl des Tages, Countdown:** Die Antwort sagt „the kaspa date is arithmetic“. Ein Datum nennt sie nicht, sie passt aber nicht mehr zur Schätzung. Ändern?
- **Newsletter-Versand:** `brevo_send.py` ruft `preis_wache` nicht auf. Soll der Versand anhalten, wenn eine Ausgabe gegen die Regeln verstößt?

## Kopf
Die Änderung steht in `1f9fdaf`. Dieser Bericht und der Live-Nachtrag zu Cloudflare liegen als eigener Commit darauf (`2ce9b4c`), beides gemergt als `95edfb3`. Die Abnahme auf kaspapulse.com ist ein eigener Nachtrag auf `95edfb3`.
