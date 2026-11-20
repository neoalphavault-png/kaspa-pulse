# Bericht zum Auftrag vom 19.11.2026, fünf Punkte

Auftrag von Ben vom Do 19.11.2026. Die Punkte kommen nach Vorrang, jeder Punkt in einem eigenen PR. Dieser Bericht wächst mit jedem PR.

## 1. Wochenpost, die Reward-Zeile nur als Schätzung
- **Vorher:** `scripts/weekly_numbers.py`, `cut_phrase`, schrieb für Discord und Telegram „cut to 1.835 on december 5, 00.15 utc“. Bis 8 Tage vor der Stufe stand statt des Datums der Wochentag.
- **Jetzt:** „cut to 1.835 around 5 dec, estimate“. Ohne Uhrzeit und ohne Wochentag, in jeder Entfernung zur Stufe dieselbe Form. Die Form kommt aus `stufe_schaetzung.kurz`, wie im Cheat Sheet und auf /whales.
- **Wache vor dem Post:** `main()` ruft nach `assert_punctuation` jetzt `stufe_pruefen(msg, msg_tg)` auf. Nennt der fertige Post für Discord oder Telegram die nächste Stufe ohne „around“ und „estimate“ oder mit Uhrzeit, hält der Lauf an, bevor etwas gesendet wird.
- **`stufe_schaetzung.py`:** Die Wache erkennt jetzt auch „00.15 utc“ mit Punkt, so schrieb der Wochenpost die Uhrzeit. Ein Betrag wie „1.94 KAS“ zählt nicht als Uhrzeit.
- **Selbsttest `weekly_numbers.py`:**
  - Der Fall vom 16.11.2026 ergibt „cut to 1.835 around 5 dec, estimate“.
  - `stufe_schaetzung.verstoesse` findet in der Reward-Zeile nichts.
  - Der alte Satz ist rot und hält den Post an.
  - Der nahe und der ferne Fall (3.8. und 6.7.) haben dieselbe Form.
  - Der Goldpost vom 3.8. ist bis auf die Reward-Zeile zeichengleich geblieben.
- **Prüfung:**
  - Selbsttests mit 0 Fehlern: weekly_numbers, stufe_schaetzung, preis_wache, x_post und karussell.
  - `stufe_schaetzung` über 45 Seiten und `preis_wache` über 55 Seiten melden je 0 Verstöße.
  - Secret-Scan ohne Fund.
- **Kopf:** Die Änderung steht in `fcbfff57`. Dieser Abschnitt liegt als eigener Commit darauf.

## 2. Zahl des Tages, warum der Planlauf nicht von selbst kam
- **Befund aus den Läufen von `number-of-day.yml`, 16. bis 19.11.:**
  - Jeden Tag kam der erste Lauf als `workflow_dispatch` um 08:41/08:42 UTC. Das war die Automatik-Prüfung (Läufe 343, 348, 353, 358).
  - Danach kamen zwei weitere Läufe um 09:12 und 10:42 UTC. Sie blieben leer, weil die Sperre nach dem ersten Lauf greift.
  - Die eigenen Cron-Termine von GitHub (08:12 und 09:42 UTC) kamen 8 bis 10 Stunden zu spät, zum Beispiel am 18.11. um 17:13 und 18:23 UTC.
- **Ursache:**
  - `deploy/c2/taktgeber/takt-number-of-day.timer` stand auf 10:12 und 11:42 **Europe/Berlin**. Laut Kommentar sollte das 08:12 und 09:42 UTC sein, das stimmt aber nur in der Sommerzeit.
  - Seit dem Wechsel auf Winterzeit am 25.10. löst c2 um 09:12 und 10:42 UTC aus. Die Automatik-Prüfung erwartet den Lauf aber bis 08:41 UTC.
  - Der Takt kam also, aber eine Stunde nach der Prüfung.
- **Änderung als PR an Ben (#336):**
  - Der Timer steht auf `08:12:00 UTC` und `09:42:00 UTC`, dazu sind README und der Kontrollblock in `setup.sh` angepasst.
  - Nach dem Merge auf c2: `sudo ./setup.sh units`.
  - Keine Workflow-Datei ist geändert.

## 3. Karussell
### a) Warum seit dem 7.11. kein Wochen-Karussell und kein Meme im Log stehen
- **Wochen-Karussell, 7.11.:** gepostet und im Log, als letzter Eintrag.
- **Wochen-Karussell, 14.11.:** rot.
  - Entwurf 11:00 (Lauf 42) und Post 13:00 (Lauf 44) brachen ab mit „keine montagsausgabe 2026-11-09 in weekly-history.json (letzte 2026-11-02)“.
  - Am 9.11. war der Wochenpost rausgegangen, aber der Push der History scheiterte.
  - Seit dem 17.11. (`fe71ccc0`) sichert `weekly_numbers.py` die History selbst, mit bis zu fünf Versuchen. Die Wochen 9.11. und 16.11. sind nachgetragen.
  - Geprüft: `karussell.ausgaben_fuer` findet für Sa 21.11. die Ausgaben 16.11. und 9.11. Das Wochen-Karussell am 21.11. hat damit seine Zahlen.
- **Meme:** Es gibt genau ein Motiv, `meme_wahr.MOTIV = "kaspa-chemie"`, gepostet am 31.10.
  - Danach endet der Meme-Schritt nach der Regel richtig mit „nicht dran, das motiv … ging am 2026-10-31 raus, ein neues fehlt“. Lauf 45 am 14.11. war grün, ohne Post.
  - Am 7.11. war der Lauf noch rot, wegen der falschen Reihenfolge der except-Zweige. Behoben mit #284.
  - Solange kein neues Motiv kommt, gibt es kein Meme. Ob eine Motiv-Bank gebaut werden soll, ist weiter offen.
- **Daneben:** Die Story vom Mi 18.11. (Läufe 46 und 47) war rot, weil `data/karussell-story.json` fehlte.

### b) Neues Karussell „Kaspa is ___“
- **Neu ist `scripts/kaspa_ist.py`.**
  - Folie 1 zeigt die Lücke als Frage: „kaspa is“, ein leerer Strich und „?“. Darunter steht „how would you finish it?“, ohne Zahl und ohne Diagramm. Die Lücke ist gezeichnet und kein Strich im Text.
  - Danach kommen 5 Fortsetzungen mit je einer datierten Zahl und genau einem Methoden-Wort. Am Ende steht die Newsletter-Folie.
- **Kandidaten in fester Reihenfolge, jede Zahl wird beim Bau frisch geholt:**
  - „fast“: Blöcke je Sekunde, counted by kaspa pulse über 10 Minuten.
  - „capped“: Anteil am Maximum, source kaspa rest api.
  - „on a schedule“: nächster Reward, computed from the emission schedule, „around 5 dec, estimate“.
  - „widely held“: Adressen ab 100 KAS, source kaspalytics address thresholds.
  - „secured by work“: Hashrate als Mittel aus 7 Tagen, source kaspa rest api.
  - „a blockdag“: DAA score, source kaspa rest api.
- **Was rausfällt:**
  - Was die Tagesgrafik am selben Tag zeigt, fällt raus (dieselbe Zahl höchstens einmal am Tag).
  - Ein Stichtag älter als 10 Tage fällt ebenfalls raus.
  - Bleiben weniger als 4 Fortsetzungen, stoppt der Bau.
- **Kein Kurs, keine Personen.** Vom Vorbild ist nur die Satzform übernommen.
- **Look v2:** Die Folien wechseln zwischen A-papier und D-dunkel, die Wortmarke steht unten mittig. Die Wachen sind dieselben wie im Wochen-Karussell: Passform, Überlappung, Wortmarke mit 4.5:1 und `content_wache` mit Kontrast 7:1.
- **Variante zweifarbig:**
  - Die Fortsetzung steht in Teal, auf Papier in dunklem Teal mit 8.4:1. Unten links steht `@kaspapulse`.
  - Diese Position widerspricht der Feed-Regel „Fußzeile mittig“ (`content_wache`, `fuss_mitte`). Im Entwurf ist nur dieser eine Befund hingenommen.
  - Gepostet wird die Variante erst mit `"zweifarbig_frei": true` in der Story-Datei. Ben entscheidet.
- **Takt ohne Änderung an Workflow oder Timer:**
  - `data/karussell-story.json` sagt jetzt `{"mittwoch": "2026-11-25", "vorlage": "kaspa-is", "variante": "v2"}`.
  - Der bestehende Mittwochs-Takt (`art=story`, Entwurf Mi 16:00, Post Mi 18:00) baut damit dieses Karussell.
  - `karussell.vorbereiten` und `karussell.rendern` leiten die Vorlage an `kaspa_ist.py` weiter.
- **Entwurf nach #ops-log:** Nach dem Merge löse ich `karussell.yml` mit `art=story schritt=probe fuer=2026-11-25` von Hand aus. Das ist ein Probe-Entwurf („PROBE, geht nicht raus“), der nichts merkt. Der Entwurf am Mi 16:00 misst neu.
- **Vorschau mit Testwerten, beide Varianten:**
  - `berichte/bilder/2026-11-19-kaspa-is-v2.png`
  - `berichte/bilder/2026-11-19-kaspa-is-zweifarbig.png`
- **Mit echten Zahlen vom 19.11. 15:45 UTC gebaut,** Blockrate hier über 1 Minute statt 10:
  - 9.3 blocks a second
  - 96.9% of the 28.7 billion KAS maximum is mined
  - 1.84 KAS per block from around 5 dec, estimate, down from 1.94
  - 295,043 addresses (15 nov 2026)
  - 324.8 PH/s (12. bis 18.11.)
  - Caption mit Bauplan zahl_zuerst: „9.3 blocks a second, Kaspa is fast.“, dann „Counted by Kaspa Pulse over 1 minutes, 19 Nov 2026, 15:45 UTC.“, die Newsletter-Zeile und drei Hashtags. Seither heißt es richtig „minute“.
- **Selbsttest `kaspa_ist.py`:** 17 Fälle, mit `--bild` 19, dann gehen auch beide Varianten durch alle Wachen.
  - Lücke ohne Zahl, 5 Fortsetzungen und Newsletter-Folie.
  - Ein Methoden-Wort je Folie, counted nur bei der eigenen Zählung.
  - Die Stufe als Schätzung, Textwachen und Caption ohne Fund.
  - Wegfall nach Tagesgrafik und nach Alter, Stopp unter 4 Fortsetzungen und bei falschem Mittwoch.
  - Freigabe der Variante.
- **Für Ben:**
  - Pinnen auf Platz 2 nach dem Post.
  - Die Routine „Donnerstags-Erklärer vorbereiten“ schreibt laut `karussell.py` ebenfalls `data/karussell-story.json`. Läuft sie vor dem 25.11. für diesen Mittwoch, ersetzt sie die Vorlage.

## 5. Zwei Entscheidungen von Ben
### a) Newsletter, Preis- und Echtzeit-Wache vor dem Versand
- **Neu in `scripts/brevo_send.py`:** `text_wachen(html)`. `html_lesen_und_pruefen` ruft sie vor jeder Übergabe an Brevo auf, für Test, Update, Fix und Planung.
  - Preis-Wache: `preis_wache.seite_pruefen`. Sie findet Preise, kursnahe Sätze (auch im Skript) und eine Reward-Stufe ohne Schätzung.
  - Echtzeit-Wache: `content_wache.echtzeit_ausdruck` auf dem sichtbaren Text.
- **Bei einem Fund** wird nichts gesendet. Der Grund mit den Funden geht über `ops_melden.hand` als „📤 VON HAND“ nach #moderator-only, und der Lauf endet rot mit „Nichts an Brevo geschickt“.
- **Gegenprobe:** Über die Ausgaben vom 12.10. bis 16.11. finden beide Wachen nichts.
- **Selbsttest `brevo_send.py`:** Ein Preis, ein Wenn-dann-Satz mit Dollar und „right now“ halten je den Versand an, und je eine Meldung geht raus. Die Ausgabe vom 16.11. ist grün.

### b) Karussell, VON-HAND-Meldung bei rotem posten
- **Neu in `scripts/karussell_post.py`:** `von_hand_melden`. Endet der Schritt posten rot, mit Stopp oder Ausnahme und außer bei einer Probe, geht nach #moderator-only:
  - „📤 VON HAND“ mit Datum, Uhrzeit und Plattform,
  - der Grund, zum Beispiel „bild nicht oeffentlich, http 404“,
  - die Seiten als Bilder in der Reihenfolge des Entwurfs,
  - die Caption als Codeblock.
- **Sonderfälle:**
  - Ist die Caption zu lang für eine Nachricht, hängt sie als `caption.txt` an.
  - Ist kein Entwurf lesbar, kommt die Meldung ohne Bilder und sagt das.
  - Scheitert die Meldung selbst, bleibt der Lauf trotzdem rot.
- **Nur `scripts/`:** `karussell.yml` ist nicht geändert. Der Schritt „rot nach ops-log“ dort bleibt.
- **Selbsttest mit einem roten Fall:**
  - posten endet mit „bild nicht oeffentlich, http 404“, Exit 1 und genau eine Meldung.
  - Die Meldung beginnt mit VON HAND, nennt den Grund und 13:00 Berlin und trägt die Caption als Codeblock und die drei Seiten als JPEG.
  - Ohne Entwurf kommt die Meldung ohne Bilder. Eine Probe meldet nichts. Eine lange Caption hängt als Datei an.

### Nachtrag 20.11.2026, Selbsttest ohne Spuren (Wache 20.11.)
- **Fund der Wache:** Der neue Selbsttest in `karussell_post.py` rief `main(["posten", "--art", "woche", "--fuer", "2026-11-21", ...])` mit einem roten posten auf. `community_melden` war dabei nicht ersetzt. So stand in der echten `data/karussell-log.json` der Community-Eintrag `{"woche": "2026-11-21", "art": "log"}`.
  - Er war schon im PR, mit zeit_utc 2026-11-19T15:49:45+00:00, und wäre bei jedem Lauf von `karussell.yml` im Schritt selbsttest neu entstanden.
  - Fiele das Wochen-Karussell am Sa 21.11. aus, hätte `community_eintrag` die Meldung „kein Beitrag fuer Kaspa Community“ unterdrückt.
- **a)** Der Eintrag ist raus. `data/karussell-log.json` ist in diesem PR wieder der Stand von main, ohne Änderung.
- **b)** Im Selbsttest zeigt `LOG` auf eine Datei im tmp-Ordner, und `community_melden` ist ersetzt. Das Datum ist Sa 2.1.1999, einen solchen Samstag gibt es im Betrieb nie.
- **c) Byte-Gleichheit:**
  - `karussell_post.py --selbsttest` läuft jetzt über `selbsttest_ohne_spuren`. Danach muss `data/karussell-log.json` byte-gleich sein, sonst ist der Test rot und die Datei kommt zurück. Ein Fall im Selbsttest prüft das mit einem Test, der absichtlich schreibt.
  - `brevo_send.py --selftest` hat bisher nichts unter `data/` oder `newsletter/` geschrieben, geprüft mit sha256 über alle Dateien vor und nach dem Lauf. Er läuft jetzt trotzdem über `selftest_ohne_spuren`, das jede Datei unter beiden Ordnern vergleicht, auch neue und fehlende, und bei einer Abweichung rot wird und zurücksetzt. Gegenprobe mit einem schreibenden Test: rot, Datei zurück, neue Datei weg.

### Prüfung
- **Selbsttests mit 0 Fehlern:** brevo_send und karussell_post, je mit der Prüfung auf byte-gleiche Daten, dazu karussell, ops_melden und preis_wache.
- **Secret-Scan:** ohne Fund.
- **Kopf:** Die Änderung steht nach dem Neuaufsetzen auf main in den Commits dieses PRs, der Nachtrag vom 20.11. in `aaf4d986`. Dieser Abschnitt liegt als eigener Commit darauf.
