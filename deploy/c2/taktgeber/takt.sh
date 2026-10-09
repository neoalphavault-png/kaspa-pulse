#!/bin/sh
# takt.sh - einen GitHub-Workflow zur festen Uhrzeit ausloesen.
#
# WOFUER ES DAS GIBT. GitHubs geplante Laeufe kommen in diesem Konto
# durchgehend sechs bis sieben Stunden zu spaet (gemessen am 09.10.2026
# ueber tagesgrafik, kas-candles, number-of-day und richlist-log). Alles,
# was eine feste Uhrzeit braucht, laeuft damit ins Leere: die Tagesgrafik
# liefert nur zwischen 07:00 und 12:00 Berlin, der Instagram-Job nur
# zwischen 09:25 und 11:30, der Reel nur im Fenster um die Short-Zeit.
# Der Takt kommt deshalb von c2, der Code bleibt auf GitHub.
#
# DAS TOKEN STEHT IN KEINER DATEI UND IN KEINER AUSGABE. Es kommt aus den
# systemd-Credentials, wird nur in den Authorization-Header geschrieben
# und nie gedruckt. Siehe README.md, Schritt 2.
#
#   takt.sh <repo> <workflow-datei> [feld=wert ...]
#   takt.sh neoalphavault-png/kaspa-pulse tagesgrafik.yml
#   takt.sh neoalphavault-png/pulse-studio instagram-reel.yml live=false
set -eu

REPO="${1:?repo fehlt, z. B. neoalphavault-png/kaspa-pulse}"
WF="${2:?workflow-datei fehlt, z. B. tagesgrafik.yml}"
shift 2

REF="${TAKT_REF:-main}"
TOKEN="$(cat "$CREDENTIALS_DIRECTORY/gh_dispatch_token")"

# inputs als json zusammensetzen, ohne jq - der server soll nichts
# nachinstallieren muessen
INPUTS=""
for kv in "$@"; do
  k="${kv%%=*}"
  v="${kv#*=}"
  INPUTS="$INPUTS,\"$k\":\"$v\""
done
[ -n "$INPUTS" ] && INPUTS="{${INPUTS#,}}" || INPUTS="{}"

CODE="$(curl -sS -o /tmp/takt.out -w '%{http_code}' \
  -X POST "https://api.github.com/repos/$REPO/actions/workflows/$WF/dispatches" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "User-Agent: kaspa-pulse-takt" \
  -d "{\"ref\":\"$REF\",\"inputs\":$INPUTS}")"
unset TOKEN

if [ "$CODE" = "204" ]; then
  echo "takt: $REPO $WF ausgeloest ($REF)"
  exit 0
fi
# Die Antwort kann die Anfrage zurueckgeben, aber nie das Token - das
# steht nur im Header, und den gibt GitHub nicht zurueck.
echo "takt: $REPO $WF NICHT ausgeloest, http $CODE" >&2
sed -e 's/[A-Za-z0-9_]\{30,\}/<token>/g' /tmp/takt.out >&2 || true
rm -f /tmp/takt.out
exit 1
