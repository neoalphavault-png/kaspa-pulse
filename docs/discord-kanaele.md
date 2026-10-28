# Discord, zwei Kanäle für den Betrieb (Ben, 28.10.2026)

Alles läuft über `scripts/ops_melden.py`, eine Stelle, zwei Arten.

| Art | Kanal | Secret | Was |
| --- | --- | --- | --- |
| `hand` | #moderator-only | `DISCORD_WEBHOOK_OPS` | nur Nachrichten, bei denen Ben etwas tun muss. Jede beginnt mit „📤 VON HAND“ und nennt Uhrzeit, Plattform, direkten Link und alles zum Kopieren |
| `log` | #ops-log | `DISCORD_WEBHOOK_LOG` | Trockenläufe, Proben, Kontrollmeldungen, Entwürfe zur Info, rote Läufe, die eine Sitzung behebt, Berichte an Claude |

- Fehlt `DISCORD_WEBHOOK_LOG`, geht eine Log-Nachricht **nicht** nach #moderator-only. Sie steht dann nur im Job-Log.
- Fehlt `DISCORD_WEBHOOK_OPS`, steht auch eine Hand-Nachricht nur im Job-Log. Der Bericht-Versand wird dann rot, weil Ben sonst nichts erfährt.
- Öffentliche Kanäle (#daily-graphic, Entity-X-Alarm, Zahl des Tages, Wochenzahlen) laufen nicht über `ops_melden` und bleiben, wie sie sind.
- Kein Webhook erscheint in einer Nachricht oder Ausgabe, `sauber()` ersetzt ihn durch `[webhook]`.

```
python3 scripts/ops_melden.py --art log  --text "probe, http 200"
python3 scripts/ops_melden.py --art hand --text-datei - --datei bild.png
```

Im Code: `ops_melden.hand(text, dateien)`, `ops_melden.log(text, dateien)`, für den Kopf einer Hand-Nachricht `ops_melden.hand_text(zeit, plattform, was, link, rest)`.

## Alle Sender und ihre Art

| Sender | Datei | Art |
| --- | --- | --- |
| Tagesgrafik, X-Post 17:00 mit Text und Bild | `scripts/tagesgrafik.py` | hand |
| Tagesgrafik, Kontrolle mit 5 Bildern, Instagram-Caption, Status, Gebührenbruch | `scripts/tagesgrafik.py` | log |
| Story-Vorlage, Bilder und Anleitung zum Posten | `scripts/story_vorlage.py` | hand |
| Story-Auto, Probe, Entwurf, gepostet | `scripts/ig_story_auto.py` | log |
| Instagram, Antwort-Entwurf zu einem Kommentar | `scripts/instagram.py` | hand |
| Instagram, Status, Container, Pflege | `scripts/instagram.py` | log |
| Karussell und Meme, Entwurf 2 h vorher, Probe | `scripts/karussell.py`, `karussell_post.py`, `meme_wahr.py` | log |
| Cheat Sheet, nicht scharf, Freigabe über `CHEAT_SHEET_LIVE` | `scripts/cheat_sheet.py` | hand |
| Cheat Sheet, scharf, Datei ersetzt | `scripts/cheat_sheet.py` | log |
| Entity-X-Alarm, Testlauf der Ping-Regel | `scripts/entity_x_alert.py` | log |
| Zahl des Tages, Trockenlauf | `scripts/post_number_of_day.py` | log |
| Wochenzahlen, Vorschau und Abbruch | `scripts/weekly_numbers.py` | log |
| Berichte, Kopf und Überblick | `scripts/bericht_discord.py` | log |
| Berichte, jeder Teil mit „📤 VON HAND“ vorn | `scripts/bericht_discord.py` | hand |
| Rote Läufe aller Workflows („rot nach ops-log“) | `.github/workflows/*.yml` | log |
| Entity-X-Alarm auf c2 im Parallelbetrieb (`server-secrets`, `ziel=ops-log`) | `deploy/c2` | log |
| Uhrwerk, Messungen, Brevo-Trichter, Rohtabelle, Proben | `scripts/insights_sammler.py`, `uhrwerk_proben.py` | log, über `uhrwerk.yml` |
