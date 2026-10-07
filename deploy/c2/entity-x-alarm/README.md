# Entity-X-Alarm auf c2

Ben, 07.10.2026. Umzug am Freitag, Einrichtung gemeinsam mit Ben. Ab dann prüft der Alarm auf c2 an jeder vollen Minute. GitHub bleibt als Rückfall.

In diesem Ordner steht kein Wert, keine IP und kein Hostname. Die Secrets kommen so, wie es der Server-Vorschlag beschreibt: Sie werden aus GitHub übertragen, mit `systemd-creds` an den Rechner gebunden verschlüsselt und über `LoadCredentialEncrypted` gelesen.

## Dateien

| Datei | Zweck |
|---|---|
| `entity-x-alarm.service` | Dauerdienst, Nutzer `kpbot`, prüft an jeder vollen Minute. `LOOP_SECONDS=86400` beendet den Lauf nach einem Tag. `Restart=always` startet ihn neu und holt vorher main (`git pull --ff-only`). Nach einem Absturz startet er nach 5 s neu. |
| `start.sh` | Setzt die drei Secrets aus den Credentials als Umgebungsvariablen. Beim ersten Start übernimmt es Stand und Abdeckung aus dem Repo. |
| `entity-x-sync.service`, `.timer` | Läuft stündlich zur Minute 7. Schreibt die Tagesabdeckung ins Journal und bringt Stand und Abdeckung ins Repo, nur bei Änderung, als `kaspa-pulse-bot` mit dem Deploy Key. |
| `sync.sh` | Der Ablauf dazu. |

Stand und Abdeckung liegen auf c2 unter `/var/lib/kaspa-pulse/`, nicht im Arbeitsverzeichnis des Repos. Die Pfade setzen `ENTITY_X_STATE_FILE` und `ABDECKUNG_FILE`.

## Einrichtung am Freitag

1. Das Repo nach `/opt/kaspa-pulse` klonen, Besitzer `kpbot`. Den Deploy Key auf c2 erzeugen und den öffentlichen Teil unter Settings, Deploy keys mit Schreibrecht eintragen.
2. Die Secrets mit `server-secrets.yml` übertragen. Danach liegen `discord_webhook`, `telegram_bot_token` und `telegram_chat_id` in `/etc/credstore.encrypted/`.
3. Die Units verlinken und starten:
   ```
   sudo systemctl link /opt/kaspa-pulse/deploy/c2/entity-x-alarm/entity-x-alarm.service
   sudo systemctl link /opt/kaspa-pulse/deploy/c2/entity-x-alarm/entity-x-sync.service
   sudo systemctl link /opt/kaspa-pulse/deploy/c2/entity-x-alarm/entity-x-sync.timer
   sudo systemctl enable --now entity-x-alarm.service entity-x-sync.timer
   ```
4. Zehn Minuten zusehen: `journalctl -u entity-x-alarm -f` muss jede Minute eine Zeile „no alert, balance …“ zeigen.
5. **Parallelbetrieb.** GitHub läuft weiter, bis die Abdeckung auf c2 einen vollen Tag belegt ist (`journalctl -u entity-x-sync`). Doppelte Meldungen in dieser Zeit sind erwartet.
6. **Umschalten:** Die Repository-Variable `SERVER_AKTIV` auf `true` setzen. Der GitHub-Job überspringt sich dann selbst, meldet keinen Nachfolger mehr an, und die Kette dort endet.

## Zurück auf GitHub

Erst `SERVER_AKTIV` auf `false` setzen, dann einen Lauf von `entity-x-alert` von Hand starten. Er meldet seine Nachfolger wieder selbst an. Der Zeitplan alle 15 Minuten fängt auf, falls das vergessen wird.

## Ziel

Mindestens 95 % beobachtete Minuten je UTC-Tag und eine größte Lücke unter 30 Minuten. `python3 scripts/entity_x_alert.py --abdeckung` zeigt beides für heute und gestern.
