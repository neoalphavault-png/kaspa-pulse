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
    # Der Job "instagram" in tagesgrafik.yml. scharf steuert IG_LIVE hier,
    # der zweite Schalter ist die Repository-Variable IG_MODUS. trocken
    # laeuft als Handstart (ohne Zeitfenster, ohne Tagessperre, nie
    # scharf), scharf als Takt (Fenster und Tagessperre gelten).
    "$HIER/takt.sh" "$REPO_PULSE" tagesgrafik.yml "instagram=${IG_LIVE:-trocken}"
    ;;
  threads)
    # threads.yml (Ben, 17.10.2026). scharf steuert THREADS_LIVE hier, der
    # zweite Schalter ist die Repository-Variable THREADS_LIVE. trocken legt
    # nur den Container an und veroeffentlicht nie.
    "$HIER/takt.sh" "$REPO_PULSE" threads.yml "modus=${THREADS_LIVE:-trocken}"
    ;;
  karussell-woche)
    # karussell.yml (Ben, 18.10.2026), nur entwurf nach #moderator-only
    "$HIER/takt.sh" "$REPO_PULSE" karussell.yml art=woche fuer= senden=true
    ;;
  karussell-story)
    "$HIER/takt.sh" "$REPO_PULSE" karussell.yml art=story fuer= senden=true
    ;;
  karussell-meme)
    # "Meme, but true", entwurf am posttag, misst die blockrate am posttag
    "$HIER/takt.sh" "$REPO_PULSE" karussell.yml art=meme fuer= senden=true
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
  cheat-sheet)
    # Einmal im Monat. Der Workflow baut und schickt PDF und Deckblatt nach
    # #moderator-only; die Datei der Webseite ersetzt er nur, wenn die
    # Variable CHEAT_SHEET_LIVE auf "scharf" steht. Der Takt gibt dazu
    # nichts mit, damit hier keine zweite Stelle entsteht, an der das
    # Veroeffentlichen haengt.
    "$HIER/takt.sh" "$REPO_PULSE" cheat-sheet.yml
    ;;
  number-of-day)
    "$HIER/takt.sh" "$REPO_PULSE" number-of-day.yml
    ;;
  shorts-nachtrag)
    # Mittwochs 10:30 und, falls noetig, 11:00. Der Workflow sucht sich
    # Woche und Schluessel selbst (die laufende Woche, Schluessel "mi")
    # und bricht ab, wenn number-of-day.json noch nicht von heute ist.
    # Keine Eingaben: shorts-nachtrag.yml hat keine, die zaehlt.
    "$HIER/takt.sh" "$REPO_STUDIO" shorts-nachtrag.yml
    ;;
  uhrwerk)
    # Reichweiten-Uhrwerk, alle 6 Stunden. Der Takt kommt von hier, die
    # Zahlen holt der Lauf auf GitHub, weil dort die Tokens liegen und
    # nirgends sonst. modus steuert UHRWERK_LIVE in takt.conf: trocken
    # schreibt die Schnappschuesse und meldet nur nach #moderator-only.
    "$HIER/takt.sh" "$REPO_PULSE" uhrwerk.yml "modus=${UHRWERK_LIVE:-trocken}"
    ;;
  uhrwerk-trichter)
    # Montags: Anmeldungen je Kanal aus Brevo, dazu die Rohtabelle.
    "$HIER/takt.sh" "$REPO_PULSE" uhrwerk.yml "modus=${UHRWERK_LIVE:-trocken}" trichter=true
    ;;
  *)
    echo "unbekannter takt: $1" >&2
    exit 1
    ;;
esac
