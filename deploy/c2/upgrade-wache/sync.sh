#!/bin/sh
# Stuendlich: das Log der Upgrade-Wache auf den Datenbranch der Konfiguration.
# Eigener flacher Klon nur dieses Branches unter /var/lib, damit das
# Arbeitsverzeichnis /opt/kaspa-pulse (main) unberuehrt bleibt. Vor dem Push
# der Secret-Scan wie auf GitHub. Bei Ablehnung (jemand anders hat gepusht)
# holen und noch einmal, hoechstens dreimal.
set -eu
KETTE="${1:?kette fehlt}"
KONFIG="/opt/kaspa-pulse/scripts/wache/ketten/$KETTE.json"
ABLAGE="/var/lib/kaspa-pulse/wache/$KETTE"
KLON="$ABLAGE/repo"
LOG="$ABLAGE/wache-log.csv"
[ -f "$LOG" ] || { echo "noch kein log"; exit 0; }

BRANCH="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["ablage"]["branch"])' "$KONFIG")"
ZIEL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["ablage"]["log"])' "$KONFIG")"
QUELLE="$(git -C /opt/kaspa-pulse remote get-url origin)"

if [ ! -d "$KLON/.git" ]; then
  git clone --quiet --depth 1 --single-branch --branch "$BRANCH" "$QUELLE" "$KLON"
fi
git -C "$KLON" config user.name "upgrade-wache c2"
git -C "$KLON" config user.email "bot@users.noreply.github.com"

for v in 1 2 3; do
  git -C "$KLON" fetch --quiet --depth 1 origin "$BRANCH"
  git -C "$KLON" reset --quiet --hard "origin/$BRANCH"
  mkdir -p "$KLON/$(dirname "$ZIEL")"
  cp "$LOG" "$KLON/$ZIEL"
  git -C "$KLON" add "$ZIEL"
  if git -C "$KLON" diff --cached --quiet; then
    echo "log unveraendert"
    exit 0
  fi
  # Wie scripts/zcash/daten_committen.sh: eine Kopie von secret_scan.py
  # prueft das Repo, in dem sie liegt, hier also den Datenbranch.
  mkdir -p "$KLON/.scan"
  cp /opt/kaspa-pulse/scripts/secret_scan.py /opt/kaspa-pulse/scripts/bip39_english.txt "$KLON/.scan/"
  (cd "$KLON" && python3 .scan/secret_scan.py --baum)
  rm -rf "$KLON/.scan"
  git -C "$KLON" commit --quiet -m "upgrade-wache $KETTE: log [bot]"
  if git -C "$KLON" push --quiet origin "HEAD:$BRANCH"; then
    echo "log gepusht, $(wc -l < "$LOG") zeilen"
    exit 0
  fi
  sleep 10
done
echo "push dreimal abgelehnt" >&2
exit 1
