#!/bin/sh
# Setzt den Webhook fuer #ops-log aus dem systemd-Credential als
# Umgebungsvariable, unter dem Namen, den die Konfiguration nennt
# (meldung.webhook_env, hier DISCORD_WEBHOOK_LOG wie auf GitHub).
# Kein Wert steht in einer Datei im Repo, keiner wird ausgegeben.
set -eu
KETTE="${1:?kette fehlt, z. B. zcash-mainnet}"
DISCORD_WEBHOOK_LOG="$(cat "$CREDENTIALS_DIRECTORY/discord_webhook_log")"
export DISCORD_WEBHOOK_LOG
ABLAGE="/var/lib/kaspa-pulse/wache/$KETTE"
mkdir -p "$ABLAGE"
exec /usr/bin/python3 -u /opt/kaspa-pulse/scripts/wache/wache.py \
  --kette "/opt/kaspa-pulse/scripts/wache/ketten/$KETTE.json" --ablage "$ABLAGE"
