Stand: 2026-11-09 07:35 Berlin

# Montagsroutine 2026-11-09, Meldung an Ben

1. UNSICHERHEIT: VIDEO_URL fehlt (nicht in der Sonntagsdatei). Newsletter trägt den Platzhalter, Testmail NICHT gestartet, weil brevo_send.py bei offenem Platzhalter abbricht. Ben muss den Link nachliefern.
2. Sonntagsdatei: Rang "45. weitester von 53" nicht übernommen, weekly_facts.py rechnet den Rang anders (9. von 53, enthält Wochen über der Linie). Gezählt und im Text: "weitester Abstand unter der 50-Wochen-Linie seit der Woche zum 05.09.2026 (−20,56 %)", neun Wochen. Bitte Rangzeile in der Sonntagsdatei prüfen.
3. Dashboard: heute lief kein Lauf, einmal gestartet (Lauf 49, grün). Die Startseite enthält keine "the read"-Lesetexte mehr (seit startseite.py), daher kein Branch claude/dashboard-<datum>.
4. Zahl der Woche: 15,54 % unter der 50-Wochen-Linie, Wochenschluss Sa 07.11.2026 (0,02967 $), nach 7,72 % unter der Linie in der Vorwoche. Weitester Abstand unter der Linie seit der Woche zum 05.09.2026 (neun Wochen).
5. Testmail: nein (siehe 1). Echtzeit-Wörter: keine Treffer. Wenn-dann-Sätze: keine, preis_wache 0 Verstöße. Ergänzte Quellen: keine. Keine Kaspalytics-Zahl in dieser Ausgabe (Netz gesperrt, Zeile vom 02.11. nicht nachrechenbar), kein Gebührenanteil (keine eigene Monatszählung). Ersetzt: "one kas buys" durch "one kas was worth".
6. Newsletter Ausgabe 18 (newsletter_issue.py ok): wartet auf deine Freigabe, auto steht auf false, nichts geplant, keine Kampagnen-ID. Eingaben für brevo-send.yml: html_path newsletter/2026-11-09.html, subject "15.54% below the 50 week line", mode schedule, send_at 2026-11-09T18:00. Vorher mode test mit demselben html_path und subject, sobald der Link eingetragen ist.
7. X main: kaspa closed the week 15.54% below its 50 week average on 7 nov 2026, after 7.72% below a week earlier. the widest gap under that line in nine weeks, since the week to 5 sep 2026. week 54, above or below?
8. X reply_video: the whole close in one sitting, both lines, and the numbers behind them. the new episode is up {video_url}
9. X reply_newsletter: all the weekly numbers in one mail, every monday. https://kaspapulse.com/x
10. Differenzen gegengerechnet: ok (Wallet 1.547.368.323 minus 1.542.974.288 = 4.394.035, exakt 4.394.035,62; Emission 1.779.989 minus 1.680.086 = 99.903, nächster Schritt 1.680.086 minus 1.585.790 = 94.296; Abstände −15,54 und −13,56 gegen −7,72 und −6,38; Hashrate-Wochenmittel 356,11 gegen 356,32 neu gerechnet; Sats 39,17 gegen 42,06).
11. Video 16:00, Short 17:00. Schick mir den Video-Link, dann trage ich ihn ein und schicke eine neue Testmail. Danach brevo-send.yml mit den Eingaben oben starten, Newsletter geht 18:00. X-Faden 18:15. Discord und Telegram 18:40 automatisch; kommt bis 19:15 kein Post, weekly numbers einmal von Hand starten, Haken 'nur rechnen und drucken' abwählen. Veto bis 17:55: weekly-cancel.yml.

Inhalte: Commit auf claude/wonderful-rubin-ow0q7b und claude/week-input-2026-11-09 (Newsletter, Wochengrafik 1800x1200, week-input.json, weekly-x-queue.json).
