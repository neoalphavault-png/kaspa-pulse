#!/bin/sh
# Setzt die Secrets aus den systemd-Credentials als Umgebungsvariablen,
# so wie die Skripte sie auf GitHub lesen. Kein Wert steht in einer Datei
# im Repo, keiner wird ausgegeben.
set -eu
DISCORD_WEBHOOK="$(cat "$CREDENTIALS_DIRECTORY/discord_webhook")"
TELEGRAM_BOT_TOKEN="$(cat "$CREDENTIALS_DIRECTORY/telegram_bot_token")"
TELEGRAM_CHAT_ID="$(cat "$CREDENTIALS_DIRECTORY/telegram_chat_id")"
export DISCORD_WEBHOOK TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID
# beim ersten start den letzten stand aus dem repo uebernehmen, damit der
# erste vergleich nicht bei null anfaengt
if [ ! -f "$ENTITY_X_STATE_FILE" ]; then
  cp /opt/kaspa-pulse/scripts/entity_x_state.json "$ENTITY_X_STATE_FILE"
fi
if [ ! -f "$ABDECKUNG_FILE" ] && [ -f /opt/kaspa-pulse/data/entity-x-abdeckung.json ]; then
  cp /opt/kaspa-pulse/data/entity-x-abdeckung.json "$ABDECKUNG_FILE"
fi
exec /usr/bin/python3 /opt/kaspa-pulse/scripts/entity_x_alert.py
