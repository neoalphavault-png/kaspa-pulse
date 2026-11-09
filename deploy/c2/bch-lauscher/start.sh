#!/bin/sh
# Zweiter Messpunkt fuer das BCH Tempnet (Ben, 09.11.2026, Teil C Punkt 10):
# derselbe Zuhoerer wie auf GitHub (scripts/bch/tempnet_lauscher.py), aber
# von c2 aus, also ueber einen anderen Netzwerkpfad. Laeufe zu hoechstens
# 330 min nacheinander bis BIS (Tempnet-Ende). Vor und nach jedem Lauf die Uhr
# (scripts/bch/uhr_versatz.py, wie im Workflow). Ein fertiger Lauf bekommt die
# Datei "fertig"; nur solche Laeufe bringt sync.sh ins Repo. Keine Werte und
# keine Adressen in dieser Datei, im Log oder in den Daten.
set -eu
BIS="${BIS:-2026-11-15T12:00:00Z}"
ABLAGE="${ABLAGE:-/var/lib/kaspa-pulse/bch-lauscher}"
KP="${KP:-/opt/kaspa-pulse}"
cd "$KP"
ENDE=$(date -d "$BIS" +%s)
while :; do
  REST=$(( ($ENDE - $(date +%s)) / 60 ))
  if [ "$REST" -lt 10 ]; then echo "bis $BIS erreicht, keine weiteren laeufe"; exit 0; fi
  DAUER=$REST; [ "$DAUER" -le 330 ] || DAUER=330
  LAUF=$(date -u +%Y%m%dT%H%M)
  O="$ABLAGE/laeufe/$LAUF"
  mkdir -p "$O/roh"
  echo "lauf $LAUF, $DAUER min"
  python3 scripts/bch/uhr_versatz.py > "$O/uhr-anfang.json" 2>/dev/null \
    || echo '{"versatz": "nicht verfügbar"}' > "$O/uhr-anfang.json"
  if python3 -u scripts/bch/tempnet_lauscher.py --dauer "$DAUER" --aus "$O/roh"; then
    python3 scripts/bch/uhr_versatz.py > "$O/uhr-ende.json" 2>/dev/null \
      || echo '{"versatz": "nicht verfügbar"}' > "$O/uhr-ende.json"
    touch "$O/fertig"
  else
    echo "lauf $LAUF endete mit fehler, er bleibt als luecke liegen" >&2
    sleep 30
  fi
done
