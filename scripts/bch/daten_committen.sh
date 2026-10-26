#!/usr/bin/env bash
# daten_committen.sh - committet data/bch/lauscher im Checkout daten/ auf
# messung/bch-tempnet. Vorher der Secret-Scan ueber diesen Datenbranch
# (eine Kopie von secret_scan.py prueft das Repo, in dem sie liegt). Mehrere
# Laeufe schreiben gleichzeitig (Zuhoerer-Laeufe ueberlappen, dazu der
# Wochenlauf): bis zu drei
# Versuche mit rebase.
#   scripts/bch/daten_committen.sh "<commit-nachricht>"
set -eu
cd daten
git config user.name "bch tempnet bot"
git config user.email "bot@users.noreply.github.com"
git add data/bch/lauscher
mkdir -p .scan && cp ../scripts/secret_scan.py ../scripts/bip39_english.txt .scan/
python3 .scan/secret_scan.py --baum
rm -rf .scan
if git diff --cached --quiet; then echo "nichts neu"; exit 0; fi
git commit -q -m "$1"
for versuch in 1 2 3; do
  git pull -q --rebase -X theirs origin messung/bch-tempnet && git push -q origin HEAD:messung/bch-tempnet && exit 0
  echo "push versuch $versuch gescheitert, neu"
  sleep $((versuch * 10))
done
exit 1
