# Covenants-Log, rot vom 27.10. bis 19.11., behoben und nachgetragen

Bericht für Ben zum Auftrag vom Fr 20.11., Frist Mo 23.11. 16:00 Berlin. Alle Zahlen sind source kaspalytics, mitgeschrieben von Kaspa Pulse.

## 1. Wo und warum der Lauf abbrach

- **Schritt:** „seite rendern“ in `.github/workflows/covenants-log.yml`, also `python3 scripts/covenants_page.py`. Davor liefen „selbsttest“ und „zahlen holen“ grün. Am 19.11. holte der Abruf 24 neue Tage, bis 18.11.
- **Meldung:** `FEHL bloecke ohne inhalt: ['analytics']`, ausgegeben in `scripts/covenants_page.py` Zeile 507. Danach endet der Lauf mit Exit 1, deshalb dauerte jeder Lauf nur 10 bis 15 Sekunden.
- **Ursache:** Commit 6320f3ea vom 26.10. um 11:08 UTC setzte auf allen öffentlichen Seiten den Block `<!--AUTO:analytics-->`, in `kaspa-covenants.html` Zeile 476 bis 478. Erst stand dort Plausible, seit #314 Cloudflare Web Analytics, gepflegt von `scripts/web_analytics.py`. `scripts/covenants_page.py` führte in Zeile 293 als fremde Blöcke nur `faq` und `seitenstand`. Jeden anderen Block ohne eigenen Inhalt hielt es für einen Fehler. Der erste Lauf nach dem Commit war #36 am 27.10.
- **Kein Secret beteiligt:** Selbsttest und Abruf bei der Quelle waren nicht die Ursache.

## 2. Behoben und nachgetragen

- **Fix:** [PR #340](https://github.com/neoalphavault-png/kaspa-pulse/pull/340), Merge-Commit 52d6b4d3. `analytics` steht jetzt in `FREMDE`, und der Selbsttest prüft den Block mit.
- **Nachgetragen:** Am 20.11. habe ich den Lauf von Hand gestartet, Commit 5640c8f8 „covenants log 2026-11-20“. Die Quelle lieferte alle fehlenden Tage. `data/covenants-log.json` hält jetzt 147 Tage vom 26.06. bis 19.11.
- **Keine Lücke:** Vom 26.10. bis 19.11. fehlt kein Tag, in keiner der vier Reihen. Deshalb gibt es auf der Seite keine Lücke auszuweisen.
- **Alter Leerwert:** Leer ist nur ein Wert von früher. utxo_count am 29.09. bleibt leer, weil der Messpunkt der Quelle 11 h 57 min neben Mitternacht liegt. Das meldet das Log selbst, und mit diesem Ausfall hat es nichts zu tun.
- **Live:** Auf `kaspa-covenants.html` stehen jetzt 23,513 Covenant-UTXOs zum 19.11. und 1,208 Covenant-Transaktionen am 19.11. Die Seite trägt den Stand „page last updated 20 November 2026“. Die drei Sätze auf `kaspa-smart-contracts.html` nennen ebenfalls 23,513 zum 19.11.

## 3. Zahlen ohne Datum, die bei einem Stillstand falsch wirken

Geprüft habe ich `kaspa-covenants.html` und alle Stellen, an denen `seiten_zahlen.py` Werte aus dem Log einsetzt. Seit dem Lauf vom 20.11. stimmen alle Zahlen wieder. Die Liste zeigt, welche Zahlen bei einem erneuten Stillstand aktuell aussehen würden, obwohl sie alt sind.

| Seite und Block | Text | Datum dabei |
|---|---|---|
| `kaspa-covenants.html`, kacheln | „729 average per day over the last seven full days“ | nein, die sieben Tage sind nicht genannt |
| `kaspa-covenants.html`, kacheln | „the busiest single day so far, 7 sep 2026“ und „the quietest single day so far, 22 jul 2026“ | nur der Tag des Höchst- und Tiefstwerts, nicht bis wann „so far“ reicht |
| `kaspa-covenants.html`, skala | „On the median day the count is 454“ | nein, der Zeitraum fehlt |
| `kaspa-covenants.html`, summe | „the log holds 143 days … 267,691 covenant transactions“ | ja, am Satzende steht 19 nov 2026 |

Mit Datum stehen der Kopf (UTXOs „as of“), die Kachel der letzten Transaktionen, die Stand-Zeile, die Tabelle, beide Diagramme (Endmarke) und die drei Sätze auf `kaspa-smart-contracts.html` („at the end of 19 November 2026“). Mein Vorschlag, nicht umgesetzt: bei den drei Stellen ohne Datum „through 19 nov 2026“ mit dem letzten Tag des Logs anhängen. Das ist eine Änderung am Seitentext, deshalb entscheidest du.

Außerhalb von `seiten_zahlen.py` lesen auch `scripts/cheat_sheet.py` und `scripts/maschinenzahlungen.py` das Log. Beide geben das Datum des letzten Tages mit aus.

## 4. Meldung in #ops-log

- **Nicht gemeldet:** Die roten Läufe kamen in #ops-log nie an. `covenants-log.yml` hat keinen Meldeschritt, anders als zum Beispiel `karussell.yml` und `cheat-sheet.yml`.
- **Ergänzt als PR an dich:** [PR #341](https://github.com/neoalphavault-png/kaspa-pulse/pull/341) fügt den Schritt „rot nach ops-log“ hinzu. Er läuft nur bei `failure()` und ruft `ops_melden.log(text, was="rot")` auf, mit dem Link zum Lauf. Der Webhook kommt nur aus `secrets.DISCORD_WEBHOOK_LOG`. Das ändert den Workflow, deshalb mergst du.

## Selbsttests und Secret-Scan

- **Selbsttests:** `covenants_page.py --selftest` mit 13 Fällen ok, `covenants_log.py --selftest` mit 44 Fällen ok, `seiten_zahlen.py --selbsttest`, `seo_seiten.py --selbsttest` und `ops_melden.py --selbsttest` je 0 Fehler.
- **Prüfung:** `covenants_page.py --check` zeigt alle Zahlen der Seite gleich dem Log.
- **Secret-Scan:** grün auf #340 und #341. In diesem Bericht steht kein Wert aus einem Secret und kein Token.

## Was Ben tun muss

- PR #341 prüfen und mergen.
- Entscheiden, ob die drei Stellen ohne Datum ein „through“ mit Datum bekommen.

<!-- discord -->
Covenants-Log wieder grün. Der Lauf brach seit 27.10. in „seite rendern“ ab, weil covenants_page.py den neuen analytics-Block nicht als fremden Block kannte (Zeile 293). Fix #340, nachgetragen bis 19.11. ohne Lücke, Seite zeigt 23,513 Covenant-UTXOs zum 19.11. Meldung roter Läufe in #ops-log als PR #341 an Ben. Bericht berichte/2026-11-23-covenants-log.md
<!-- /discord -->
