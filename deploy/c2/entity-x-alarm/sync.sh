#!/bin/sh
# Stuendlich: Stand und Abdeckung vom Server ins Repo, nur bei Aenderung.
# Committet als kaspa-pulse-bot mit dem Deploy Key, wie die Bots heute.
# Schreibt die Tagesabdeckung ins Journal.
set -eu
cd /opt/kaspa-pulse
/usr/bin/python3 scripts/entity_x_alert.py --abdeckung
git pull --ff-only --quiet
cp /var/lib/kaspa-pulse/entity_x_state.json scripts/entity_x_state.json
cp /var/lib/kaspa-pulse/entity-x-abdeckung.json data/entity-x-abdeckung.json
git add scripts/entity_x_state.json data/entity-x-abdeckung.json
if git diff --staged --quiet; then
  echo "unveraendert, kein commit"
  exit 0
fi
git -c user.name="kaspa-pulse-bot" -c user.email="bot@kaspapulse.com" commit -q -m "entity x state update [c2]"
git pull --rebase --quiet origin main
git push --quiet origin HEAD:main
