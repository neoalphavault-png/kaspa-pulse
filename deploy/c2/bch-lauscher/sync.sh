#!/bin/sh
# Stuendlich: fertige Laeufe des zweiten BCH-Tempnet-Zuhoerers (start.sh) auf
# messung/bch-tempnet unter data/bch/lauscher-c2/<lauf>/, im selben Format wie
# die Laeufe von GitHub (gzip ohne Zeitstempel, meta.json mit "uhr" und
# "messpunkt": "c2"). Eigener flacher Klon unter /var/lib wie bei der
# Upgrade-Wache, Secret-Scan vor dem Push, hoechstens dreimal.
set -eu
ABLAGE="${ABLAGE:-/var/lib/kaspa-pulse/bch-lauscher}"
KP="${KP:-/opt/kaspa-pulse}"
KLON="$ABLAGE/repo"
BRANCH=messung/bch-tempnet
ZIEL=data/bch/lauscher-c2
GESENDET="$ABLAGE/gesendet.txt"
QUELLE="$(git -C "$KP" remote get-url origin)"
touch "$GESENDET"
NEU=""
for d in "$ABLAGE"/laeufe/*/; do
  [ -f "$d/fertig" ] || continue
  L=$(basename "$d")
  grep -qx "$L" "$GESENDET" || NEU="$NEU $L"
done
[ -n "$NEU" ] || { echo "kein neuer fertiger lauf"; exit 0; }

if [ ! -d "$KLON/.git" ]; then
  git clone --quiet --depth 1 --single-branch --branch "$BRANCH" "$QUELLE" "$KLON"
fi
git -C "$KLON" config user.name "bch-lauscher c2"
git -C "$KLON" config user.email "bot@users.noreply.github.com"

for v in 1 2 3; do
  git -C "$KLON" fetch --quiet --depth 1 origin "$BRANCH"
  git -C "$KLON" reset --quiet --hard "origin/$BRANCH"
  for L in $NEU; do
    Q="$ABLAGE/laeufe/$L"
    O="$KLON/$ZIEL/$L"
    mkdir -p "$O"
    for n in ereignisse koepfe compact; do gzip -n -c "$Q/roh/$n.jsonl" > "$O/$n.jsonl.gz"; done
    python3 - "$Q/roh/meta.json" "$Q/uhr-anfang.json" "$Q/uhr-ende.json" "$O/meta.json" <<'PY'
import json, sys
quelle, anfang, ende, ziel = sys.argv[1:]
def lesen(p):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {"versatz": "nicht verfügbar"}
meta = json.load(open(quelle))
meta["messpunkt"] = "c2"
meta["uhr"] = {"anfang": lesen(anfang), "ende": lesen(ende)}
if not any("quelle" in v for v in meta["uhr"].values()):
    meta["versatz"] = "nicht verfügbar"
json.dump(meta, open(ziel, "w"), indent=2, ensure_ascii=False)
PY
    git -C "$KLON" add "$ZIEL/$L"
  done
  if git -C "$KLON" diff --cached --quiet; then echo "nichts neu"; exit 0; fi
  mkdir -p "$KLON/.scan"
  cp "$KP/scripts/secret_scan.py" "$KP/scripts/bip39_english.txt" "$KLON/.scan/"
  (cd "$KLON" && python3 .scan/secret_scan.py --baum)
  rm -rf "$KLON/.scan"
  git -C "$KLON" commit --quiet -m "bch tempnet: zuhoerer c2,$NEU [bot]"
  if git -C "$KLON" push --quiet origin "HEAD:$BRANCH"; then
    for L in $NEU; do echo "$L" >> "$GESENDET"; done
    echo "gepusht:$NEU"
    exit 0
  fi
  sleep 10
done
echo "push dreimal abgelehnt" >&2
exit 1
