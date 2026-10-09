#!/bin/sh
# ausloesen.sh - die Zuordnung Takt -> Workflow. Eine Stelle, an der
# steht, was wann ausgeloest wird. Keine Werte, nur Namen.
set -eu
HIER="$(dirname "$0")"
case "$1" in
  tagesgrafik)
    "$HIER/takt.sh" "$REPO_PULSE" tagesgrafik.yml
    ;;
  instagram-bild)
    # Der Job "instagram" in tagesgrafik.yml, von Hand immer trocken.
    "$HIER/takt.sh" "$REPO_PULSE" tagesgrafik.yml instagram=trocken
    ;;
  reel)
    # Leere Eingaben: der Lauf nimmt den Short, der jetzt faellig ist.
    # live steuert die Variable REELS_LIVE, nicht der Takt.
    "$HIER/takt.sh" "$REPO_STUDIO" instagram-reel.yml "live=${REEL_LIVE:-false}"
    ;;
  weeklynumbers)
    # ACHTUNG: dry_run steht auf GitHub auf true. Ein Takt ohne dieses
    # Feld rechnet nur und postet nicht. Scharf wird er ueber WN_DRY_RUN
    # in takt.conf, bewusst und an einer Stelle.
    "$HIER/takt.sh" "$REPO_PULSE" weeklynumbers.yml "dry_run=${WN_DRY_RUN:-true}"
    ;;
  number-of-day)
    "$HIER/takt.sh" "$REPO_PULSE" number-of-day.yml
    ;;
  *)
    echo "unbekannter takt: $1" >&2
    exit 1
    ;;
esac
