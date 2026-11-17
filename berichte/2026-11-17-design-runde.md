# Design-Runde 17.11.: Zahl 5, Datenschutz, Karussell vom 14.11.

- **Auftrag:** Gesamtauftrag von Ben vom 17.11.2026. Er ersetzt die offenen Punkte vom 13.11. und 16.11.
- **Stand:** 17.11.2026, Commit `fe71ccc` auf `main`. Der Selbst-Merge lief über `automerge-claude.yml` nach der Regel vom 26.10.
- **Berührt:** nur `scripts/`, `data/`, Seiten und das PDF, keine Workflow-Datei.
- **Prüfungen:** Selbsttests, `seo_pruefung` und Secret-Scan sind grün.
- **Offen:** Punkt 2 ist nicht erledigt, siehe unten.

## 1. Zahl 5 auf /whales und im Cheat Sheet

**Code**

`scripts/cheat_sheet.py` holt beide Formen jetzt aus `scripts/stufe_schaetzung.py`:

| Stelle | vorher | jetzt |
| --- | --- | --- |
| Karte 5 (früher Zeile 838) | „4 nov“, „next block reward cut, 13:45 utc“ | „around 5 dec“, „next block reward cut, estimate“ |
| Satz auf Karte 5 | „the next one is on 4 november.“ | „the next one is around 5 December 2026, an estimate, because the step is set by DAA score.“ |
| Hinweis auf Karte 5 | „the cut lands on a block score, so the exact minute drifts a little.“ | „the cut lands on a DAA score, not on a clock time, so the day is an estimate.“ |
| Datumszeile | „… · 3 days from 1 nov“ | „… · about 18 days from 17 nov“, gezählt ab dem Stichtag der Senkung |
| Deckblatt (früher Zeile 914) | „13:45 utc“ | „estimate · set by DAA score“ |
| Grafik | „2.06 until 4 nov“, „1.94 on 4 nov“ | „1.94 until around 5 dec“, „1.84 around 5 dec“ |
| Teaser-Datum | „4 November 2026, 13:45 utc“ | „around 5 dec, estimate“ |

- `scripts/whales_seite.py` nimmt die Form aus dem Cheat Sheet und setzt kein zweites „around“ davor.

**Korrigierte Ausgabe 2**

- **Neuer Aufruf:** `--korrektur-senkung --aus <probe der ausgabe> --edition N` baut die korrigierte Fassung einer schon veröffentlichten Ausgabe.
  - Er rechnet nur Zahl 5 für heute neu. Die sieben anderen Zahlen und ihre Stichtage bleiben unverändert, ebenso Stand und Nummer.
  - Er ersetzt `kaspa-pulse-cheat-sheet.pdf` und baut /whales neu.
  - Im Log bekommt die Ausgabe einen Eintrag unter `korrekturen`.
  - Die 10-Tage-Frist gilt dabei nicht für die sieben alten Zahlen, weil genau sie stehen bleiben sollen.
- **Gebaut am 17.11.** mit
  `python3 scripts/cheat_sheet.py --korrektur-senkung --aus data/cheat-sheet-edition-2-probe.json --edition 2 --stand 2026-11-17`
- **Grundlage** war der veröffentlichte Stand vom 1.11. um 12:07 UTC (`data/whales-stand.json`). Er passt Zahl für Zahl zum PDF auf der Website. `data/cheat-sheet-edition-2-probe.json` war eine frühere Probe vom 1.11. um 08:00 und ist durch diesen Stand ersetzt. Danach trägt sie die Korrektur.
- **Log** `data/cheat-sheet-log.json`, Ausgabe 2:
  - Die Nummer bleibt 2.
  - Der Stichtag `senkung` ist jetzt 2026-11-17.
  - Unter `korrekturen` steht ein Eintrag mit Zahl 5, Grund, Stichtag und Zeitpunkt vorher und nachher (4 nov 13:45 UTC, dann 5 dec).
- **Workflow:** Ein Lauf von `cheat-sheet.yml` war nicht nötig, der Neubau lief im Skript.
- **Text-Vergleich alt gegen neu** (`pdftotext`):
  - Geändert ist nur Seite 5 und die Zeile 05 auf dem Deckblatt.
  - Auf Seite 2 und 4 bricht je ein Satz ein Wort früher oder später um („about one / in seven“ statt „about one in / seven“). Der Grund ist die andere Chromium-Version beim Bau. Text und Zahlen sind gleich.
  - Die Quellzeile auf Seite 5 lautet jetzt „computed from the emission schedule“, wie seit #316 im Quelltext.
- **Selbsttest `cheat_sheet.py`:** 0 Fehler. Neu sind:
  - Karte 5 ohne Uhrzeit und ohne Verstoß gegen `stufe_schaetzung`
  - Teaser-Datum als Schätzung
  - Korrektur: Zahl 5 „around 5 dec“, Datumszeile „1.94 to 1.84 KAS per block · about 18 days from 17 nov“
  - die sieben anderen Zahlen zeichengleich
  - Log mit Nummer 2 und einem Korrektur-Eintrag

**Abnahme auf kaspapulse.com**

- **`kaspapulse.com/kaspa-pulse-cheat-sheet.pdf`:**
  - Die Datei ist byte-gleich zum Commit (md5 `604f18cd…`), 10 Seiten im Format 810 × 1013 pt.
  - Deckblatt: „05 next block reward cut, around 5 dec, estimate · set by DAA score“.
  - Seite 5 hat den Satz mit DAA score.
  - „13:45“ kommt nicht mehr vor.
  - `stufe_schaetzung.verstoesse` über den ganzen Text, Stand 17.11.: 0.
- **`kaspapulse.com/whales/` bei 390 px:**
  - Die Seitenbreite ist 390 und es gibt keinen waagerechten Scroll.
  - Karte 2 zeigt „around 5 dec“, darunter „next block reward cut, estimate“ und „1.94 to 1.84 KAS per block · about 18 days from 17 nov“.
  - „around 4 nov“ kommt nicht mehr vor.

## 2. Etikett DAA score

**Nicht erledigt.** Den Auftrag vom 13.11. finde ich weder in `berichte/` noch in den Commits noch in den PRs. Was genau das Etikett sein soll (Wortlaut, Stelle, Schreibweise „DAA score“ oder „daa score“), weiß ich deshalb nicht. Bitte den Text vom 13.11. noch einmal schicken.

## 3. datenschutz.html

- Die Zeile „Datenschutzerklärung · Last updated: …“ steht von Hand in `datenschutz.html`, außerhalb der AUTO-Bereiche. Die Datei selbst ist also die Quelle.
- Sie lautet jetzt „Last updated: November 2026“.
- Die Seite ist `noindex`, `seo_seiten.py` führt für sie keinen Stand.
- Live geprüft: `kaspapulse.com/datenschutz.html` zeigt „Last updated: November 2026“.

## 4. Karussell vom 14.11.

**Ursache**

1. **Mo 9.11., 18:40 Berlin:** Der Wochenpost ging auf Discord und Telegram raus ([Lauf 42666853629](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42666853629)). Der Push der `weekly-history.json` wurde mit „cannot lock ref“ abgelehnt. In derselben Sekunde hatte das Uhrwerk gepusht (`74619b3`, 17:40:20 UTC): `takt-uhrwerk` läuft täglich um 18:40 Berlin, `takt-weeklynumbers` am Montag ebenfalls um 18:40. Der Push-Schritt im Workflow hat nur einen Versuch.
2. **Sa 14.11., 11:00 Berlin:** Der Entwurf brach ab mit „keine montagsausgabe 2026-11-09 in weekly-history.json (letzte 2026-11-02)“ ([Lauf 43583149951](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43583149951)). Der Posten-Lauf um 13:00 fand keinen Entwurf. Er postete nichts und schrieb nur die Community-Zeile „log“.
3. **Mo 16.11.:** Dasselbe noch einmal, diesmal mit „fetch first“ ([Lauf 43920758686](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43920758686), Uhrwerk `f7f7740`, 17:40:20 UTC).
4. **Die Meldung in #ops-log war in beiden Fällen falsch.** Dort stand „ABBRUCH sprungbremse. tvl_total springt“. Diese Zeile stammt aus dem Selbsttest. Er schreibt ins selbe `weekly.log`, und `--ops-meldung` nimmt die letzte ABBRUCH-Zeile.

**Behoben** (nur `scripts/` und `data/`)

- **History sofort sichern:** `weekly_numbers.py` committet und pusht die history jetzt selbst, wenn es in GitHub Actions läuft.
  - Es versucht es bis zu fünfmal, mit `pull --rebase` und Pausen von 5, 10, 20 und 40 s.
  - Der Schritt „history zurückschreiben“ im Workflow findet danach nichts mehr und endet grün. Eine Workflow-Änderung ist nicht nötig.
  - Scheitert auch der fünfte Versuch, kommt eine klare ABBRUCH-Zeile: „history nach 5 versuchen nicht gepusht, der post ist raus …“.
- **Falsche ABBRUCH-Zeile:** Die Ausgabe der Ops-Tests im Selbsttest bleibt im Puffer und landet nicht mehr im Log.
- **7-Tage-Prüfung im Karussell:** `karussell.ausgaben_fuer()` verlangt die Ausgabe genau 7 Tage vor der Montagsausgabe. Sonst gibt es keinen Entwurf. Ohne diese Prüfung hätte das Karussell am 21.11. „16.11. gegen 2.11.“ als „a week before“ gepostet.
- **Wochen nachgetragen:** 2026-11-09 (Ausgabe 18) und 2026-11-16 (Ausgabe 19) stehen jetzt in `weekly-history.json`.
  - Die Werte stammen aus dem Job-Log des gesendeten Posts und sind gerundet wie gepostet. Block reward und Emission sind gerechnet.
  - `holders` (meaningful-balance) stand nicht im Post und fehlt.
  - Jeder Eintrag trägt ein Feld `nachtrag` mit dem Lauf.
  - Damit kennt auch die Dublettenbremse beide Wochen wieder.
  - Nichts wurde nachträglich gepostet.

**Selbsttests mit dem Fall**

| Skript | neue Fälle | Ergebnis |
| --- | --- | --- |
| `weekly_numbers.py --selftest` | Push abgelehnt wie am 9.11. und zweiter Versuch klappt; fünfmal abgelehnt mit klarer Meldung; die ABBRUCH-Zeile des Pushs geht an ops; die ABBRUCH-Zeile des Ops-Tests bleibt im Puffer | alle bestanden |
| `karussell.py --selbsttest` | 14.11. ohne Ausgabe 9.11.: kein Entwurf; 21.11. mit Lücke davor: kein Zwei-Wochen-Vergleich; 21.11. mit beiden Ausgaben: 16.11. gegen 9.11. | 0 Fehler |

**Gegenprobe für Sa 21.11.:** `karussell.vorbereiten("woche", "2026-11-21")` baut die Seiten mit „week to 14 nov 2026“. Die Hashrate lautet „-3.3% against the week to 7 nov“, die Halter „-1,491 in a week“. Nichts wurde gesendet.

## Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| Selbsttests `cheat_sheet`, `karussell`, `karussell_post`, `seo_pruefung`, `seo_seiten`, `preis_wache` | 0 Fehler |
| Selbsttests `whales_seite`, `stufe_schaetzung`, `startseite`, `weekly_numbers` | alle bestanden |
| `seo_pruefung.py --gegen origin/main` | 0 Fehler, 0 Warnungen |
| `preis_wache.py` | 55 Seiten, 0 Verstöße |
| `stufe_schaetzung.py` auf `whales/index.html` und `datenschutz.html` | 0 |
| Secret-Scan auf die vorgemerkten Änderungen | nichts gefunden |

## Offen und Vorschläge

- **Punkt 2:** fehlt, siehe oben.
- **Takte entzerren**, nur Ben, weil es `deploy/` betrifft: `takt-uhrwerk` 18:40 und `takt-weeklynumbers` Mo 18:40 sollten nicht mehr in derselben Minute laufen, zum Beispiel das Uhrwerk auf :41. Der Fix im Skript fängt den Zusammenstoß ab. Die Entzerrung nimmt ihn ganz weg.
- **Gleiche Regel, anderer Ort:** Der Wochenpost auf Discord und Telegram schreibt in der Reward-Zeile weiter „cut to 1.835 on december 5, 00.15 utc“ (`weekly_numbers.cut_phrase`). Das widerspricht der Regel vom 12.11. (keine Uhrzeit, nur „around …, estimate“). Ich habe es hier nicht geändert, weil es nicht im Auftrag stand.
- **`seo_seiten.py --pruefen`** meldet auf `main` eine Abweichung bei `kaspa-tvl.html` und `data/seiten-stand.json`. Das ist ein Altbefund aus den Bot-Läufen, ich habe ihn nicht angefasst.
