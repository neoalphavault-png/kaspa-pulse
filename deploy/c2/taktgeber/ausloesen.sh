#!/bin/sh
# ausloesen.sh - die Zuordnung Takt -> Workflow. Eine Stelle, an der
# steht, was wann ausgeloest wird. Keine Werte, nur Namen.
set -eu
HIER="$(dirname "$0")"
case "$1" in
  tagesgrafik)
    # ACHTUNG, hier lag der Fehler am 10.10.2026: ein Takt OHNE Eingaben
    # nimmt die Vorbelegungen von tagesgrafik.yml - und senden steht dort
    # absichtlich auf false. Lauf 37 hat die Grafik gebaut und das Artefakt
    # hochgeladen, aber nichts nach #moderator-only geschickt und nichts ins
    # Log geschrieben. Darum stehen alle drei Eingaben ausdruecklich da,
    # genau wie bei Bens Handstart:
    #   senden=true     Grafik, Texte und Selbstpruefung nach #moderator-only
    #   form=           leer heisst Rotation, keine Form von Hand
    #   instagram=aus   der Instagram-Job laeuft zu seiner eigenen Zeit
    #
    # senden geht als Text "true" raus, nicht als JSON-Wahrheitswert. Beide
    # Wege waeren richtig, aber den Text prueft der Workflow ohnehin genau
    # so ([ "$SENDEN" = "true" ]), und diese Form hat der Dispatch schon
    # verschickt. Ein 422 morgen um 07:30 waere teurer als die Eleganz.
    "$HIER/takt.sh" "$REPO_PULSE" tagesgrafik.yml senden=true form= instagram=aus
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
