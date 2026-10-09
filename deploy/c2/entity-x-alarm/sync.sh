#!/bin/sh
# Stuendlich: Stand und Abdeckung vom Server ins Repo. Schreibt die
# Tagesabdeckung ins Journal.
#
# WARUM NICHT MEHR "cp UND COMMIT" (Ben, 09.10.2026). Im Parallelbetrieb
# schreiben GitHub und c2 dieselbe Abdeckungsdatei. Ein cp haette die
# Minuten des anderen geloescht - und die 95 % je Tag wollen wir ja
# messen. Dazu kam der Konflikt: "git pull --rebase" bricht ab, wenn
# beide Seiten dieselbe Datei geaendert haben, und liess das Repo mitten
# im Rebase stehen.
#
# Jetzt in zwei Schritten, beide verlustfrei:
#   1. Die Serverdatei wird in die Repo-Datei VEREINIGT (eine Minute gilt
#      als beobachtet, wenn eine der beiden sie beobachtet hat).
#   2. entity_x_alert.py --festschreiben erledigt den Rest: fetch, reset
#      auf origin/main, noch einmal vereinigen, committen, pushen, bei
#      Ablehnung von vorn. Denselben Weg geht der GitHub-Job seit dem
#      08.10.2026.
#
# Fuer Schritt 2 muessen die Pfade ins Repo zeigen, nicht nach
# /var/lib - darum "env -u".
set -eu
cd /opt/kaspa-pulse

SERVER_ABDECKUNG="${ABDECKUNG_FILE:-/var/lib/kaspa-pulse/entity-x-abdeckung.json}"
SERVER_STAND="${ENTITY_X_STATE_FILE:-/var/lib/kaspa-pulse/entity_x_state.json}"

# Bericht aus der Sicht des Servers, fuer das Journal.
/usr/bin/python3 -u scripts/entity_x_alert.py --abdeckung

git fetch --quiet origin main
git reset --hard --quiet origin/main

/usr/bin/python3 -u scripts/abdeckung_vereinen.py \
  "$SERVER_ABDECKUNG" data/entity-x-abdeckung.json
cp "$SERVER_STAND" scripts/entity_x_state.json

env -u ABDECKUNG_FILE -u ENTITY_X_STATE_FILE \
  /usr/bin/python3 -u scripts/entity_x_alert.py --festschreiben
