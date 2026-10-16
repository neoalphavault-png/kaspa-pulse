name: reichweiten-uhrwerk

# WER IHN STARTET. Der Takt auf c2 (takt-uhrwerk.timer, alle 6 Stunden,
# und takt-uhrwerk-trichter.timer montags). Hier steht absichtlich KEIN
# schedule: GitHubs geplante Laeufe kommen in diesem Konto sechs bis sieben
# Stunden zu spaet, und ein schedule-Lauf hat keine Eingaben - modus waere
# dort leer.
#
# DIE TOKENS KOMMEN AUS DEN GITHUB SECRETS UND GEHEN NUR ALS env: IN DEN
# LAUF. Sie stehen in keiner Datei im Repo, und die Skripte blenden alles
# aus, was wie ein Token aussieht - auch aus Fehlermeldungen und aus jeder
# Zeile, die geschrieben wird.
#
# DIE EINGABEN GEHEN UEBER env:, NICHT DIREKT IN run: (Ben, 16.10.2026).
# Ein ${{ ... }} mitten im Shell-Befehl wird vor der Shell ersetzt; wer
# eine Eingabe schickt, schreibt damit Shell-Code. Ueber env: ist sie
# eine Variable, und der erste Schritt jedes Jobs prueft ihren Wert.

on:
  workflow_dispatch:
    inputs:
      modus:
        description: "trocken = schreiben und melden, scharf = auch der Ausreisser-Alarm"
        required: false
        default: "trocken"
        type: string
      trichter:
        description: "true = Anmeldungen je Kanal aus Brevo (montags)"
        required: false
        default: "false"
        type: string
      sammeln:
        description: "nein = nur die Proben laufen lassen"
        required: false
        default: "ja"
        type: string
      proben:
        description: "einmalige Proben: was liefert X, kennt Graph Trial Reels"
        required: false
        default: "aus"
        type: choice
        options:
          - aus
          - x-metriken
          - trial-reels
          - beide

permissions:
  contents: write

env:
  MODUS: ${{ inputs.modus || 'trocken' }}
  TRICHTER: ${{ inputs.trichter || 'false' }}

concurrency:
  group: uhrwerk
  cancel-in-progress: false

jobs:
  sammeln:
    # Leere Eingabe heisst sammeln. Nur ein ausdrueckliches "nein" laesst
    # den Job aus - sonst waere ein Takt ohne Felder ein stiller Leerlauf.
    if: inputs.sammeln != 'nein'
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      # Erst die Eingaben, dann alles andere. Ein falscher Wert bricht hier
      # ab und nicht erst mitten im Lauf, wo schon gemessen wurde.
      - name: eingaben pruefen
        run: |
          case "$MODUS" in
            trocken|scharf) echo "modus $MODUS" ;;
            *) echo "::error::modus muss trocken oder scharf sein, nicht '$MODUS'"; exit 1 ;;
          esac
          case "$TRICHTER" in
            true|false) echo "trichter $TRICHTER" ;;
            *) echo "::error::trichter muss true oder false sein, nicht '$TRICHTER'"; exit 1 ;;
          esac

      - uses: actions/checkout@v4

      # Das Reel postet aus pulse-studio und traegt seine Manifest-Zeile
      # dort ein. Hier wird sie nur GELESEN. pulse-studio ist privat, der
      # mitgelieferte Token reicht dafuer nicht - STUDIO_READ_TOKEN ist ein
      # fein eingestellter Token mit Contents: Read, nur auf dieses eine
      # Repo. Fehlt oder verfaellt er, bleibt der Schritt rot und der Lauf
      # geht weiter: der Sammler liest dann nur das eigene Manifest, die
      # Reels fehlen in der Auswertung, nichts geht kaputt.
      - name: manifest aus pulse-studio, nur lesen
        continue-on-error: true
        uses: actions/checkout@v4
        with:
          repository: neoalphavault-png/pulse-studio
          token: ${{ secrets.STUDIO_READ_TOKEN }}
          path: studio
          sparse-checkout: data/insights

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      # Erst die Selbsttests, dann an die Daten. Ein Sammler, der sich
      # selbst nicht traut, soll nichts in die Dateien schreiben.
      - name: selbsttests
        run: |
          python3 scripts/post_manifest.py --selbsttest
          python3 scripts/insights_sammler.py --selbsttest
          python3 scripts/x_analytics_csv.py --selbsttest
          python3 scripts/uhrwerk_proben.py --selbsttest

      - name: schnappschuesse
        env:
          UHRWERK_MANIFEST: "data/insights/manifest.jsonl:studio/data/insights/manifest.jsonl"
          INSTAGRAM_PAGE_TOKEN: ${{ secrets.INSTAGRAM_PAGE_TOKEN }}
          IG_USER_ID: ${{ vars.IG_USER_ID }}
          IG_GRAPH_VERSION: ${{ vars.IG_GRAPH_VERSION }}
          THREADS_TOKEN: ${{ secrets.THREADS_TOKEN }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
        run: |
          python3 scripts/insights_sammler.py --sammeln --modus "$MODUS"

      # Montags. Die Zahlen aus Brevo gehen NUR nach #moderator-only, sie
      # werden in kein Repo geschrieben - kaspa-pulse ist oeffentlich.
      - name: anmeldungen je kanal
        if: env.TRICHTER == 'true'
        env:
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
        run: |
          python3 scripts/insights_sammler.py --trichter --modus "$MODUS"

      # Montags. Die Rohtabelle fuer die Claude-Routine um 10:40 Berlin.
      # Sie traegt nur, was ohnehin oeffentlich ist, und wird committet.
      - name: rohtabelle
        if: env.TRICHTER == 'true'
        env:
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
        run: |
          python3 scripts/insights_sammler.py --rohtabelle --modus "$MODUS"

      # IMMER committen, auch nach einem roten Schritt: ein Fenster, das
      # gemessen und nicht gesichert wurde, wird nie wieder gemessen.
      # [skip ci] ist Guertel und Hosentraeger - ein Push mit GITHUB_TOKEN
      # loest ohnehin keine Action aus.
      - name: schnappschuesse sichern
        if: always()
        run: |
          git config user.name "kaspa-pulse-bot"
          git config user.email "bot@kaspapulse.com"
          # reports/ gibt es erst nach dem ersten Montagslauf. Ein
          # "git add -- reports/" auf einen Pfad, den es nicht gibt, bricht
          # das ganze add ab - dann waere nichts vorgemerkt und der Lauf
          # haette still nichts committet.
          git add -- data/insights/
          if [ -d reports ]; then git add -- reports/; fi
          if git diff --staged --quiet; then
            echo "nichts gemessen, nichts zu committen"
            exit 0
          fi
          git commit -q -m "uhrwerk schnappschuesse $(date -u +%Y-%m-%dT%H:%M) [skip ci]"
          # Die gemessenen Dateien ZUERST beiseitelegen, aus dem sauberen
          # Stand nach dem Commit. Nach einem gescheiterten Rebase stehen
          # Konfliktmarken in der Datei - eine Kopie von dann waere Muell.
          rm -rf /tmp/uhrwerk-eigen && mkdir -p /tmp/uhrwerk-eigen
          cp -r data/insights /tmp/uhrwerk-eigen/insights
          if [ -d reports ]; then cp -r reports /tmp/uhrwerk-eigen/reports; fi
          OK=nein
          for N in 1 2 3; do
            if git pull --rebase --autostash -q origin main; then
              :
            else
              # Dateien, die nur wachsen: beide Seiten behalten, Zeilen
              # ohne Dopplung vereinen. Ein Rebase kann das nicht wissen.
              # Die Rohtabelle traegt das Datum im Namen und kollidiert
              # darum nicht; sie wird einfach wieder hingelegt.
              echo "rebase-konflikt, zeilen werden vereint"
              git rebase --abort 2>/dev/null || true
              git reset --hard -q origin/main 2>/dev/null || true
              python3 - <<'EOF'
          import pathlib, shutil
          eigen = pathlib.Path("/tmp/uhrwerk-eigen")
          ziel = pathlib.Path("data/insights")
          ziel.mkdir(parents=True, exist_ok=True)
          for q in sorted((eigen / "insights").glob("*.jsonl")):
              z = ziel / q.name
              kennt = set(z.read_text(encoding="utf-8").splitlines() if z.exists() else [])
              neu = [l for l in q.read_text(encoding="utf-8").splitlines()
                     if l.strip() and l not in kennt]
              if neu:
                  with open(z, "a", encoding="utf-8") as fh:
                      fh.write("\n".join(neu) + "\n")
              print("%s: %d zeilen dazu" % (q.name, len(neu)))
          eigene_berichte = (eigen / "reports")
          for q in sorted(eigene_berichte.glob("*.md")) if eigene_berichte.exists() else []:
              pathlib.Path("reports").mkdir(exist_ok=True)
              shutil.copy2(q, pathlib.Path("reports") / q.name)
              print("%s wieder hingelegt" % q.name)
          EOF
              git add -- data/insights/
              if [ -d reports ]; then git add -- reports/; fi
              git diff --staged --quiet || \
                git commit -q -m "uhrwerk schnappschuesse $(date -u +%Y-%m-%dT%H:%M) [skip ci]"
            fi
            if git push -q origin HEAD:main; then OK=ja; break; fi
            echo "push $N fehlgeschlagen"
            sleep "$N"
          done
          if [ "$OK" = "ja" ]; then
            echo "schnappschuesse sind auf main"
          else
            echo "::warning::schnappschuesse nicht auf main, sie liegen als artefakt bereit"
            mkdir -p artefakt && cp -r /tmp/uhrwerk-eigen artefakt/uhrwerk || true
          fi

      - name: nicht gesicherte zeilen als artefakt
        if: always() && hashFiles('artefakt/uhrwerk/**') != ''
        uses: actions/upload-artifact@v4
        with:
          name: uhrwerk-nicht-gesichert
          path: artefakt/uhrwerk
          retention-days: 30

  proben:
    # Laeuft nur, wenn Ben sie ausdruecklich anstoesst. Eine leere Eingabe
    # ist hier kein "beide": der Vergleich mit dem Namen ist absichtlich
    # ausgeschrieben, contains() waere bei einer leeren Eingabe wahr.
    if: inputs.proben == 'x-metriken' || inputs.proben == 'trial-reels' || inputs.proben == 'beide'
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    # Dieser Job liest nur. Er schreibt nichts ins Repo, also bekommt er
    # auch kein Schreibrecht.
    permissions:
      contents: read
    steps:
      - name: eingaben pruefen
        run: |
          case "$MODUS" in
            trocken|scharf) echo "modus $MODUS" ;;
            *) echo "::error::modus muss trocken oder scharf sein, nicht '$MODUS'"; exit 1 ;;
          esac

      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: mkdir -p proben

      # continue-on-error: eine Probe, die "kein Zugang" meldet, hat
      # geantwortet. Das Ergebnis soll ankommen, auch wenn der Aufruf
      # abbricht.
      - name: was liefert x
        if: inputs.proben == 'x-metriken' || inputs.proben == 'beide'
        continue-on-error: true
        env:
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
        run: |
          python3 scripts/uhrwerk_proben.py --x-metriken | tee proben/x-metriken.json

      # OHNE --container: es wird nur gelesen. Nichts wird angelegt und
      # nichts veroeffentlicht.
      - name: kennt graph trial reels
        if: inputs.proben == 'trial-reels' || inputs.proben == 'beide'
        continue-on-error: true
        env:
          INSTAGRAM_PAGE_TOKEN: ${{ secrets.INSTAGRAM_PAGE_TOKEN }}
          IG_USER_ID: ${{ vars.IG_USER_ID }}
          IG_GRAPH_VERSION: ${{ vars.IG_GRAPH_VERSION }}
        run: |
          python3 scripts/uhrwerk_proben.py --ig-trial-reels | tee proben/trial-reels.json

      # Der Bericht steht in uhrwerk_proben.py und nicht mehr hier. Genau
      # an dieser Stelle fehlte der User-Agent, und Discord lehnt einen
      # Aufruf ohne ihn mit http 403 ab (gemessen am 16.10.2026, Lauf #2).
      # Im Skript geht er durch insights_sammler.hole, und dort prueft der
      # Selbsttest den Kopf an der Anfrage selbst.
      - name: ergebnis nach ops
        if: always()
        env:
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
          LAUF: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          python3 scripts/uhrwerk_proben.py --melden --ordner proben --modus "$MODUS"

      - name: proben als artefakt
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: uhrwerk-proben
          path: proben
          if-no-files-found: ignore
          retention-days: 30
