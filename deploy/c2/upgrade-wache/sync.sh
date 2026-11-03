#!/bin/sh
# Stuendlich: das Log der Upgrade-Wache auf den Datenbranch der Konfiguration.
# Nach dem Fenster (Zeile "fenster_zu" im Log) zusaetzlich die Rohdaten
# (scripts/wache/roh_export.py: Ankuendigungen, Koepfe, Software der Peers,
# Zustand, SHA256SUMS; nur aus dem Fenster, ohne Adressen) in den Ordner
# roh neben dem Log (Ben, 02.11.2026, fuer den PulseHawk Upgrade Report v1).
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
ROH=""
EXPORT_FEHLER=0
# wache_kern.log schreibt mit csv.writer, also mit \r\n am Zeilenende:
# vor dem Vergleich die \r entfernen.
if tr -d '\r' < "$LOG" | grep -q ',fenster_zu$'; then
  if python3 /opt/kaspa-pulse/scripts/wache/roh_export.py --kette "$KONFIG" --ablage "$ABLAGE" \
       --aus "$ABLAGE/export.neu"; then
    rm -rf "$ABLAGE/export" && mv "$ABLAGE/export.neu" "$ABLAGE/export"
    ROH="$(dirname "$ZIEL")/roh"
  else
    rm -rf "$ABLAGE/export.neu"
    EXPORT_FEHLER=1
    echo "rohdaten nicht exportiert, nur das log" >&2
  fi
fi

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
  if [ -n "$ROH" ]; then
    rm -rf "${KLON:?}/$ROH"
    cp -r "$ABLAGE/export" "$KLON/$ROH"
    git -C "$KLON" add -A "$ROH"
  fi
  if git -C "$KLON" diff --cached --quiet; then
    echo "log unveraendert"
    [ "$EXPORT_FEHLER" -eq 0 ] || echo "fehler: rohdaten nicht exportiert" >&2
    exit "$EXPORT_FEHLER"
  fi
  # Wie scripts/zcash/daten_committen.sh: eine Kopie von secret_scan.py
  # prueft das Repo, in dem sie liegt, hier also den Datenbranch.
  mkdir -p "$KLON/.scan"
  cp /opt/kaspa-pulse/scripts/secret_scan.py /opt/kaspa-pulse/scripts/bip39_english.txt "$KLON/.scan/"
  (cd "$KLON" && python3 .scan/secret_scan.py --baum)
  rm -rf "$KLON/.scan"
  git -C "$KLON" commit --quiet -m "upgrade-wache $KETTE: log${ROH:+ und rohdaten} [bot]"
  if git -C "$KLON" push --quiet origin "HEAD:$BRANCH"; then
    echo "log gepusht, $(wc -l < "$LOG") zeilen${ROH:+, rohdaten in $ROH}"
    # Fehler beim Export erst nach dem Log-Push melden, damit
    # systemctl status und journalctl ihn zeigen
    [ "$EXPORT_FEHLER" -eq 0 ] || echo "fehler: rohdaten nicht exportiert" >&2
    exit "$EXPORT_FEHLER"
  fi
  sleep 10
done
echo "push dreimal abgelehnt" >&2
exit 1
