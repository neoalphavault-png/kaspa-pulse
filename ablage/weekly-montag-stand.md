# Montagsroutine, Stand 16.11.2026 07:38 Berlin

Sonntagsdatei fehlte, selbst gerechnet (review/weekly-2026-11-16 ungemergt; meine Werte decken sich mit dem Entwurf dort). Video-Link fehlt, VIDEO_URL steht als Platzhalter, du musst ihn nachliefern. Testmail deshalb NICHT gestartet: brevo_send.py weist jede Ausgabe mit VIDEO_URL ab, keine Kampagnen-ID.

Dashboard: die fünf Lesetexte gibt es seit dem Startseiten-Umbau (23.10.) nicht mehr, index.html mit startseite.py gerendert.

Zahl der Woche: KAS schloss Sa 14.11.2026 23.63% unter der 50-Wochen-Linie (Vorwoche 15.54%), weitester Abstand seit der Woche zum 29.08.2026, elf Wochen.

Dashboard weekly: heute kein Lauf, einmal gestartet (durchgelaufen, Commit 63b6c882).

Testmail raus: nein. Fundliste: 0 Echtzeit-Wörter, 0 Wenn-dann-Sätze, 0 ergänzte Quellen (keine Kaspalytics- oder Fremdzahl im Text).

Newsletter Ausgabe 19 wartet auf deine Freigabe. Eingaben brevo-send.yml: html_path newsletter/2026-11-16.html, subject "23.63% below the 50 week line", mode schedule, send_at 2026-11-16T18:00 (vorher mode test mit Link).

X main: kaspa closed the week 23.63% below its 50 week average on 14 nov 2026, after 15.54% below a week earlier. the widest gap under that line in eleven weeks, since the week to 29 aug 2026. week 55, above or below?

X reply_video: the whole close in one sitting, both lines, and the numbers behind them. the new episode is up {video_url}

X reply_newsletter: all the weekly numbers in one mail, every monday. https://kaspapulse.com/x

Differenzen gegengerechnet: ok (Wallet 1,561,274,881 − 1,547,368,323 = 13,906,558; Abstand 50: 23.63 − 15.54 = 8.09; Abstand 21: 21.52 − 13.56 = 7.96; Emission 1,680,086 − 1,585,790 = 94,296).

Commit 8d3d56a2 auf claude/dashboard-2026-11-16 und claude/week-input-2026-11-16 (Newsletter, Grafik 1800x1200, week-input, X-Queue, Startseite).

Video 16:00, Short 17:00. Schick mir den Video-Link, dann trage ich ihn ein und schicke eine neue Testmail. Danach brevo-send.yml mit den Eingaben oben starten, Newsletter geht 18:00. X-Faden 18:15. Discord und Telegram 18:40 automatisch; kommt bis 19:15 kein Post, weekly numbers einmal von Hand starten, Haken 'nur rechnen und drucken' abwählen. Veto bis 17:55: weekly-cancel.yml.

