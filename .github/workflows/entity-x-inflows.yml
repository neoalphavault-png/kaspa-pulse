name: entity x inflow trace

# manueller lauf. beantwortet die frage, woher die zufluesse von entity x
# kommen. ergebnis liegt danach als data/entity-x-inflows.json im repo und
# als artifact zum download, die zusammenfassung steht im log.

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  trace:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: trace inflows
        run: python scripts/entity_x_inflows.py

      - name: commit result
        run: |
          git config user.name "kaspa-pulse-bot"
          git config user.email "bot@kaspapulse.com"
          git add data/entity-x-inflows.json
          if git diff --staged --quiet; then
            echo "nothing changed"
          else
            git commit -m "entity x inflow trace $(date -u +%Y-%m-%d)"
            git push
          fi

      - name: upload for download
        uses: actions/upload-artifact@v4
        with:
          name: entity-x-inflows
          path: data/entity-x-inflows.json
