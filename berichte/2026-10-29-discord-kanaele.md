# Bericht 29.10.2026: Discord nur noch Handlungen in #moderator-only

Auftrag von Ben vom 28.10.2026. Frist Do 29.10.2026 18:00 Berlin, gebaut am 28.10.2026.

## Was gebaut ist
- **Eine Stelle für alle Meldungen:** `scripts/ops_melden.py` mit zwei Arten.
  - `hand` geht nach #moderator-only über `DISCORD_WEBHOOK_OPS`. Jede Nachricht beginnt mit „📤 VON HAND“, dann Zeit, Plattform, was zu tun ist, der direkte Link und alles zum Kopieren.
  - `log` geht nach #ops-log über `DISCORD_WEBHOOK_LOG`. Dazu gehören Trockenläufe, Proben, Kontrollmeldungen, Entwürfe zur Info, rote Läufe und Berichte an Claude.
- **Fehlt `DISCORD_WEBHOOK_LOG`,** steht eine Log-Nachricht nur im Job-Log. Sie geht nie nach #moderator-only.
- **Öffentliche Kanäle** laufen nicht darüber und bleiben unverändert: #daily-graphic, Entity-X-Alarm, Zahl des Tages, Wochenzahlen, Telegram.
- **Webhooks** kommen nur aus der Umgebung. `sauber()` ersetzt jede Webhook-Adresse in Text und Ausgabe durch `[webhook]`. In keiner Datei steht eine, auch die Testadressen werden erst zur Laufzeit zusammengesetzt.
- **Berichte:** Der Kopf und alle Teile ohne „📤 VON HAND“ gehen nach #ops-log. Jeder Teil mit „📤 VON HAND“ vorn geht einzeln nach #moderator-only, mit Link zum Bericht. Der Kopf zählt beide Mengen aus der fertigen Liste. Fehlt der Ops-Webhook, wird der Lauf rot, weil du sonst nichts erfährst.

## Alle Sender und ihre Art
Stand 28.10.2026, auch in `docs/discord-kanaele.md`.

| Sender | Art |
| --- | --- |
| Tagesgrafik, X-Post 17:00 mit Text und Bild | hand |
| Tagesgrafik, Kontrolle mit 5 Bildern, Instagram-Caption, Status, Gebührenbruch | log |
| Story-Vorlage, Bilder und Anleitung | hand |
| Story-Auto, Probe, Entwurf, gepostet | log |
| Instagram, Antwort-Entwurf zu einem Kommentar | hand |
| Instagram, Status und Container | log |
| Karussell und Meme, Entwurf 2 h vorher und Probe | log |
| Cheat Sheet, solange `CHEAT_SHEET_LIVE` nicht scharf ist | hand |
| Cheat Sheet, scharf | log |
| Entity-X-Alarm, Testlauf der Ping-Regel | log |
| Entity-X-Alarm auf c2 im Parallelbetrieb (`server-secrets`, `ziel=ops-log`) | log |
| Zahl des Tages, Trockenlauf | log |
| Wochenzahlen, Vorschau und Abbruch | log |
| Rote Läufe aller Workflows („rot nach ops-log“) | log |
| Berichte, Kopf und Überblick | log |
| Berichte, Teile mit „📤 VON HAND“ | hand |
| Uhrwerk, Messungen, Brevo-Trichter, Rohtabelle, Proben (#185) | log |
| Uhrwerk, scharfer Ausreißer-Alarm „Kommentare jetzt beantworten“ (#185) | hand |

## c2
- Auf c2 braucht es **keinen neuen Credential-Namen**. Der Alarm liest weiter `discord_webhook`.
- `server-secrets.yml` (#184) bietet statt `ziel=moderator` jetzt `ziel=ops-log` an. Diese Wahl nimmt `DISCORD_WEBHOOK_LOG`. Ein Parallelbetrieb landet damit in #ops-log.
- **Nur falls der Alarm auf c2 noch nach #moderator-only schreibt,** also seit dem 48-h-Parallelbetrieb nicht auf `normal` umgestellt wurde, steht unten ein Schritt.

## Probe
Lauf auf dem Branch bericht/2026-10-29-discord-kanaele, Ergebnis folgt unten.

## PR-Nummern
- #183, Skripte und `ops_melden`, selbst gemergt (a918e7f)
- #186, Bericht-Versand fand keine Berichte im Push-Ereignis, Rückfall über den Vergleich, selbst gemergt (18f873d)
- #184, Workflows und c2, wartet auf Ben
- #185, Uhrwerk mit den geschützten Dateien `uhrwerk.yml` und `insights_sammler.py`, wartet auf deine Freigabe

## Offene Fragen an Ben
1. #185: Darf ich das Uhrwerk anfassen? Ohne Freigabe meldet es weiter alles nach #moderator-only.
2. Schreibt der Entity-X-Alarm auf c2 öffentlich (`normal`) oder noch nach #moderator-only?

## Was Ben tun muss
Siehe „📤 VON HAND“ im Discord-Abschnitt.

<!-- discord -->
**Discord-Kanäle, 28.10.2026**
- **Gebaut:** Eine Stelle `ops_melden` mit zwei Arten. **hand** geht nach #moderator-only und beginnt immer mit 📤 VON HAND. **log** geht nach #ops-log.
- **Umgestellt:** Tagesgrafik, Story-Vorlage, Story-Auto, Instagram, Karussell, Meme, Cheat Sheet, Entity-X-Test, Zahl des Tages, Wochenzahlen, Berichte (#183, live).
- **Hier landen ab jetzt nur noch:** X-Post 17:00, Story-Vorlage, Kommentar-Antworten, Cheat-Sheet-Freigabe und die VON-HAND-Teile der Berichte.
- **Ohne das neue Secret** stehen Log-Meldungen nur im Job-Log. Sie kommen nie hierher.
- **Probe:** Diese Nachrichten sind die Probe. Die Handlungen kommen hier an, Kopf und Überblick gehen nach #ops-log, solange das Secret fehlt nur ins Job-Log.
- **Bericht:** berichte/2026-10-29-discord-kanaele.md
<!-- teil -->
📤 VON HAND, heute, Discord und GitHub. **Kanal #ops-log anlegen und den Webhook als Secret speichern**
1. In Discord den Kanal #ops-log anlegen, nur für dich und die Mods. Kanal bearbeiten, Integrationen, Webhooks, Neuer Webhook, Webhook-URL kopieren.
2. Auf GitHub ein neues Repository-Secret anlegen:
https://github.com/neoalphavault-png/kaspa-pulse/settings/secrets/actions/new
Name:
```
DISCORD_WEBHOOK_LOG
```
Wert: die kopierte Webhook-URL. Bitte nirgends sonst einfügen, auch nicht im Chat.
<!-- teil -->
📤 VON HAND, nach dem Secret, GitHub. **#184 mergen, Workflows und c2**
https://github.com/neoalphavault-png/kaspa-pulse/pull/184
Damit gehen rote Läufe, Karussell-Entwürfe, Story-Auto und Kontrollen nach #ops-log. Danach schicke ich je eine Probe hand und log.
<!-- teil -->
📤 VON HAND, wenn du willst, GitHub. **#185 Uhrwerk freigeben oder ablehnen**
https://github.com/neoalphavault-png/kaspa-pulse/pull/185
Er ändert die geschützten Dateien uhrwerk.yml und insights_sammler.py. Danach gehen Messungen nach #ops-log, nur der scharfe Ausreißer-Alarm kommt hierher. Antwort genügt, ja oder nein.
<!-- teil -->
📤 VON HAND, nur falls der Entity-X-Alarm auf c2 noch hier schreibt, GitHub. **server-secrets auf ops-log stellen**
Erst nach #184. Actions, server-secrets, Run workflow:
https://github.com/neoalphavault-png/kaspa-pulse/actions/workflows/server-secrets.yml
ziel:
```
ops-log
```
was:
```
nur-discord
```
Schreibt der Alarm schon öffentlich, nichts tun.
<!-- /discord -->
