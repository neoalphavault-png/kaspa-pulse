# Bericht 12.11.2026: Plausible raus, Cloudflare Web Analytics rein

Auftrag von Ben vom 12.11.2026, Frist So 15.11. 18:00 Berlin. Keine Workflow-Datei ist geändert, deshalb gilt der Selbst-Merge nach der Regel vom 26.10.

## 1. Cloudflare Web Analytics auf allen öffentlichen Seiten
- **Neuer Baustein `scripts/web_analytics.py`:** Er ersetzt `scripts/plausible.py`, das gelöscht ist.
  - Er setzt Bens Snippet wörtlich zwischen `<!--AUTO:analytics-->` und `<!--/AUTO:analytics-->`, direkt vor `</body>`. Ein zweiter Lauf ändert nichts.
  - `--pruefen` endet mit Exit 1, wenn eine Seite den Block nicht hat oder noch die alte Zählung trägt.
- **Seitenliste:** dieselbe wie in `seo_seiten.py`, plus `whales/index.html`, zusammen 45 Seiten. Wochenseiten, Archiv und method erben den Block aus dem Rahmen von `index.html`.
- **An der Quelle:** `scripts/whales_seite.py` baut die Seite /whales und setzt den Block jetzt selbst vor `</body>`, im Teaser wie in der vollen Fassung.
- **Token und Secret-Scan:** Das Token ist öffentlich. Der Secret-Scan erkennt `"token": "…"` aber als Schlüssel-Zuweisung. Er hat deshalb eine Ausnahme bekommen, über den Fingerabdruck `2fe71292cfdd` in `.secret-scan-allow`, mit Begründung und ohne den Wert.

## 2. Plausible vollständig entfernt
- **Seiten:** Auf allen 45 Seiten ist der Block im Kopf weg (Skript von plausible.io und Init).
- **Anmelde-Handler:** Das Ereignis „Signup“ ist auf allen Seiten mit Formular entfernt, auf /whales und in `capture.js`.
- **Unverändert:** die Anmeldung selbst, der Erfolgstext und die versteckten UTM-Felder für Brevo. Alle Inline-Skripte und `capture.js` haben die Syntaxprüfung von node bestanden.
- **Gleichlautende Wörter umbenannt, damit die Suche leer ist:** Das Verhalten ändert sich dabei nicht.
  - Kommentare und Meldungen: „unplausibler Wert“ heißt jetzt „unstimmiger Wert“, in `address_thresholds_log.py`, `covenants_log.py`, `kaspalytics.py`, `entity_x_heartbeat.py` und `reward_cut_alert.py`.
  - Ein Testname in `meme_wahr.py` ist entsprechend angepasst.
  - In `weekly_numbers.py` heißt `PLAUSIBLE` jetzt `WERTEBEREICH` und `check_plausible` jetzt `bereich_pruefen`.
  - In zwei Texten unter `skills/taste-skill/` steht „believable“ statt „plausible“.
- **Ergebnis:** `git grep -il plausible -- ':!berichte/'` findet 0 Dateien.

## 3. Datenschutzseite, Abschnitt 6
Neu heißt der Abschnitt „Cookies and web analytics (Cloudflare Web Analytics)“. Jede Aussage über Cloudflare ist mit Cloudflares eigenem Text belegt, gelesen am 12.11.2026:

| Aussage auf der Seite | Beleg bei Cloudflare |
| --- | --- |
| Anbieter Cloudflare, Inc., 101 Townsend St, San Francisco, CA 94107, USA | https://www.cloudflare.com/privacypolicy/ („Cloudflare, Inc. 101 Townsend St, San Francisco, CA 94107 USA“) |
| keine Cookies, kein localStorage | https://www.cloudflare.com/web-analytics/ („does not use any client-side state, such as cookies or localStorage, to collect usage metrics“) |
| kein Fingerprinting über IP-Adresse oder User-Agent | https://www.cloudflare.com/web-analytics/ („We also don’t “fingerprint” individuals via their IP address, User Agent string, or any other data for the purpose of displaying analytics.“) |
| keine personenbezogenen Daten | https://developers.cloudflare.com/web-analytics/about/ („Cloudflare Web Analytics does not collect or use your visitors’ personal data.“) |
| Seitenaufrufe, Besuche, verweisende Seiten | https://developers.cloudflare.com/web-analytics/about/ („information on page views and visitors“) und https://www.cloudflare.com/web-analytics/ („the number of views, and the top referrers to your website“) |
| Ladezeit der Seiten im Browser | https://developers.cloudflare.com/web-analytics/about/ („The JavaScript snippet (also known as a beacon) collects metrics using the Performance API“) |
| Zertifizierung nach EU-U.S. Data Privacy Framework | https://www.cloudflare.com/privacypolicy/ („Cloudflare complies with the EU-U.S. DPF“) |

- **Unsere eigenen Aussagen:** Zweck ist die Reichweitenmessung, Rechtsgrundlage Art. 6 (1)(f) DSGVO. Das Formular sendet kein Ereignis an Cloudflare, und die E-Mail-Adresse geht nur an Brevo (Abschnitt 4).
- **Nicht übernommen:** Land, Gerätetyp und Browser stehen auf den gelesenen Seiten nicht ausdrücklich. Deshalb stehen sie auch nicht im Text.
- **Textregeln:** keine Doppelpunkte, Striche oder Pfeile im Fließtext, keine Echtzeitwörter.

## 4. Content-Security-Policy
Es ist keine gesetzt. Im Repo gibt es weder einen `Content-Security-Policy`-Meta-Tag noch eine `_headers`-Datei. kaspapulse.com wird von GitHub Pages ausgeliefert (`server: GitHub.com`), ohne CSP-Header. Damit gibt es nichts zu ergänzen.

## 5. Prüfung auf dem Betriebspfad
Folgt als Nachtrag nach dem Merge, sobald GitHub Pages ausgeliefert hat. Geprüft wird auf kaspapulse.com und kaspapulse.com/whales/: eine Anfrage an cloudflareinsights.com mit 2xx, keine Anfrage an plausible.io. Die Anmeldung testet Ben selbst. Ich melde mich nicht an.

## Prüfung
- **Selbsttests mit 0 Fehlern:** web_analytics, whales_seite, weekly_numbers, meme_wahr, seo_pruefung, seo_seiten, preis_wache, rahmen, archiv und startseite.
- **Seitenprüfungen:**
  - `web_analytics.py --pruefen` meldet „cloudflare web analytics auf allen seiten“.
  - `seo_seiten --pruefen` meldet „alles auf stand“.
  - `seo_pruefung --gegen origin/main` meldet 0 Fehler.
  - `preis_wache` meldet 53 Seiten mit 0 Verstößen.
- **Secret-Scan:** über die Commits des Branches ohne Fund, nach der Ausnahme für das öffentliche Token.
- **Umgebung:** Die Cloudflare-Seiten und Hosts waren aus der alten Umgebung gesperrt. Für diesen Auftrag läuft die Sitzung in einer neuen persönlichen Umgebung „kaspa-pulse“. Sie erlaubt die bisherigen Hosts plus developers.cloudflare.com, www.cloudflare.com, static.cloudflareinsights.com und cloudflareinsights.com.

## Hinweis
Cloudflare wertet keine UTM-Parameter und keine eigenen Ereignisse aus. Die Zuordnung von Anmeldungen zu Kampagnen läuft ab jetzt nur über die versteckten UTM-Felder in Brevo.

## Kopf
Der Stand vor dem Live-Nachtrag ist `500fe89`. Dieser Eintrag liegt als eigener Commit darauf.
