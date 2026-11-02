Stand: 2026-11-02 07:40 Berlin

# Montagsroutine 2026-11-02, Meldung an Ben

1. UNSICHERHEIT: Sonntagsdatei fehlte auf main (liegt nur auf review/weekly-2026-11-02). Kernzahlen selbst aus data/kas-candles.json gerechnet und gegen die Datei gelegt, keine Abweichung.
2. VIDEO-LINK FEHLT: Der Newsletter trägt VIDEO_URL. Testmail NICHT gestartet, weil brevo_send.py bei offenem Platzhalter abbricht. Ben muss den Link nachliefern.
3. In der Sonntagsdatei geprüft: der tiefste Wochenschluss seit Sa 29.08.2026 (0,03057 $), nicht seit "Woche zum 05.09." (dort 0,03523 $). Wallet-Start: Sonntagsdatei 24.10. 17:22 UTC, Newsletter der Vorwoche 25.10. 17:36 UTC, derselbe Wert 1.539.942.949, ich nahm die Sonntagsdatei. Im Uploadpaket (Beschreibung) steht "pings the second the biggest wallet moves", das ist ein Echtzeit-Wort, bitte ändern.
4. Zahl der Woche: 7,72 % unter der 50-Wochen-Linie, Schluss Sa 31.10.2026 (0,03257 $), und in den 52 Wochen seit 02.11.2025 die einzige Woche, die beide Linien in einem Schritt verlor.
5. Dashboard: heute lief kein Lauf, einmal gestartet (Lauf 46, grün, index.html mit 7,72 % liegt auf main). Kein eigener Branch nötig.
6. Echtzeit-Wörter: keine Treffer, keine ersetzt (nur "the first/second" als Zählwort durch die Liniennamen ersetzt). Ergänzte Quellen: keine. Der Newsletter trägt keine Kaspalytics-Zahl und keinen Gebührenanteil (letzte Monatszählung 25.09.).
7. Newsletter Ausgabe 17: wartet auf deine Freigabe, auto steht auf false, nichts geplant, keine Kampagnen-ID. Eingaben für brevo-send.yml: html_path newsletter/2026-11-02.html, subject "7.72% below the 50 week line", mode schedule, send_at 2026-11-02T18:00. Vorher mode test mit demselben html_path und subject, sobald der Link eingetragen ist.
8. X main: kaspa closed the week 7.72% below its 50 week average on 31 oct 2026, after 1.41% above a week earlier. in the 52 weeks our series carries that line, no other week lost both averages in one step. week 53, above or below?
9. X reply_video: the whole close in one sitting, both lines, and the numbers behind them. the new episode is up {video_url}
10. X reply_newsletter: all the weekly numbers in one mail, every monday. https://kaspapulse.com/x
11. Differenzen gegengerechnet: ok (Wallet 1.542.974.287 minus 1.539.942.949 = 3.031.338, Emission 1.779.989 minus 1.680.086 = 99.903, Abstände -7,72 und -6,38 gegen +1,41 und +2,97, Schwelle 0,035239 liegt 8,19 % über dem Schluss).
12. Video 16:00, Short 17:00. Schick mir den Video-Link, dann trage ich ihn ein und schicke eine neue Testmail. Danach brevo-send.yml mit den Eingaben oben starten, Newsletter geht 18:00. X-Faden 18:15. Discord und Telegram 18:40 automatisch; kommt bis 19:15 kein Post, weekly numbers einmal von Hand starten, Haken 'nur rechnen und drucken' abwählen. Veto bis 17:55: weekly-cancel.yml.

Commit der Inhalte: af7cd7c (main), Branch claude/focused-planck-op275t.
