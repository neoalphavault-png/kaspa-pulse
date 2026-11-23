# Montagsroutine, Stand 23.11.2026 07:38 Berlin

Video-Link fehlt, VIDEO_URL steht als Platzhalter (Newsletter-Button, reply_video), du musst ihn nachliefern. Testmail deshalb NICHT gestartet: brevo_send.py weist jede Ausgabe mit VIDEO_URL ab, keine Kampagnen-ID. Heldenzahl ist diese Woche die Zahl der Folge (37 kUSDT-Halter), nicht die 50-Wochen-Linie; "stablecoin" nur als Frage im Videotitel, sonst "dollar tickers".

Zahl der Woche: 37 Adressen hielten kUSDT am Sa 21.11.2026 12:00 UTC, 6 Tage nach der Genesis am 15.11.2026 (14 am 16.11.), eigene Zählung vom eigenen Knoten.

Dashboard weekly: heute kein Lauf, einmal gestartet (durchgelaufen, Commit cffbcaa auf main). index.html mit startseite.py geprüft, unverändert; check_reads: alle Zahlen decken sich mit dem Datenblock.

Testmail raus: nein (VIDEO_URL). Fundliste: 0 Echtzeit-Wörter, 0 Wenn-dann-Sätze, 0 ergänzte Quellen (keine Kaspalytics- oder Fremdzahl außer kraken). Text-Wachen brevo_send, preis_wache, weekly_facts pruefe, content_wache: grün. Ersetzt vor Abgabe: "12:00 utc" aus X-main und Read gestrichen (Doppelpunkt-Verbot).

Newsletter Ausgabe 20 wartet auf deine Freigabe. Eingaben brevo-send.yml: html_path newsletter/2026-11-23.html, subject "37 addresses held kUSDT, 6 days after its genesis", mode schedule, send_at 2026-11-23T18:00 (vorher mode test mit Link).

X main: 37 addresses held kUSDT on 21 nov 2026, 6 days after the token's genesis, up from 14 on 16 nov, in our own node count. how many kUSDT holders next saturday?

X reply_video: who holds the new dollar tickers on kaspa, how much sits on chain, and the week in numbers. the new episode is up {video_url}

X reply_newsletter: all the weekly numbers in one mail, every monday. https://kaspapulse.com/x

Differenzen gegengerechnet: ok (Halter 2,126 − 1,929 = 197; Wallet 1,566,279,326 − 1,561,274,881 = 5,004,445; Abstand 50: 25.21 − 23.63 = 1.58; Abstand 21: 22.58 − 21.52 = 1.06; Emission 1,680,086 − 1,585,790 = 94,296; Tokens 455 − 431 = 24).

Commit 50ca1a2 auf claude/dashboard-2026-11-23 und claude/week-input-2026-11-23 (Newsletter, Grafik 1800x1200, week-input, X-Queue).

Video 16:00, Short 17:00. Schick mir den Video-Link, dann trage ich ihn ein und schicke eine neue Testmail. Danach brevo-send.yml mit den Eingaben oben starten, Newsletter geht 18:00. X-Faden 18:15. Discord und Telegram 18:40 automatisch; kommt bis 19:15 kein Post, weekly numbers einmal von Hand starten, Haken 'nur rechnen und drucken' abwählen. Veto bis 17:55: weekly-cancel.yml.
