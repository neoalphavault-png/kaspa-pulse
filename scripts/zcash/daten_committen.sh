#!/usr/bin/env bash
# daten_committen.sh - committet data/zcash-mainnet im Checkout daten/ auf
# messung/zcash-mainnet. Vorher der Secret-Scan ueber diesen Datenbranch
# (eine Kopie von secret_scan.py prueft das Repo, in dem sie liegt). Mehrere
# Laeufe schreiben gleichzeitig (Zuhoerer-Kette, taeglicher Lauf): bis zu drei
# Versuche mit rebase.
#   scripts/zcash/daten_committen.sh "<commit-nachricht>"
set -eu
cd daten
git config user.name "zcash mainnet bot"
git config user.email "bot@users.noreply.github.com"
git add data/zcash-mainnet
mkdir -p .scan && cp ../scripts/secret_scan.py ../scripts/bip39_english.txt .scan/
python3 .scan/secret_scan.py --baum
rm -rf .scan
if git diff --cached --quiet; then echo "nichts neu"; exit 0; fi
git commit -q -m "$1"
for versuch in 1 2 3; do
  git pull -q --rebase -X theirs origin messung/zcash-mainnet && git push -q origin HEAD:messung/zcash-mainnet && exit 0
  echo "push versuch $versuch gescheitert, neu"
  sleep $((versuch * 10))
done
exit 1
