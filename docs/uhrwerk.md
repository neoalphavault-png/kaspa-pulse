# Reichweiten-Uhrwerk, Teil 1: Manifest und Sammler

Ben, 15.10.2026. Teil 1 von drei: hier stehen das Manifest und der Sammler.
Zeitplan, Varianten und Auswertung kommen nach dem Design-Start am 20.10.

## Warum zuerst das Manifest

Eine Reichweite ohne Beschreibung des Posts ist eine Zahl ohne Frage. Erst
wenn Format, Look, Variante und Haken daneben stehen, laesst sich etwas
vergleichen. Das Manifest wird im Moment des Postens geschrieben, aus der
Automatik heraus - nicht spaeter aus der Erinnerung.

## Was hier liegt

| Datei | was sie tut |
| --- | --- |
| `scripts/post_manifest.py` | schreibt und liest `data/insights/manifest.jsonl` |
| `scripts/insights_sammler.py` | Schnappschuesse 24 h und 7 d, Follower, Ausreisser-Alarm, Anmeldungen |
| `scripts/uhrwerk_proben.py` | die zwei Fragen: was liefert X, kennt Graph Trial Reels |
| `scripts/x_analytics_csv.py` | liest den CSV-Export der X-Analyse ein |
| `data/insights/manifest.jsonl` | eine Zeile je Post |
| `data/insights/<kanal>.jsonl` | ein Schnappschuss je Zeile |
| `data/insights/follower.jsonl` | Followerzahl je Kanal, bei jedem Lauf |
| `data/insights/trichter.jsonl` | Anmeldungen je Kanal, woechentlich |

Jedes Skript hat `--selbsttest`. Stand 15.10.2026: 40 + 36 + 24 + 17
Pruefungen, alle gruen.

## Das Manifest

Zehn Felder, von Ben gesetzt: `post_id`, `kanal`, `zeit_berlin`, `format`,
`look`, `variante`, `hook`, `laenge_s`, `hashtags`, `quelle`. Dazu
`permalink` und `eingetragen`.

Geprueft wird vor dem Schreiben: fremder Kanal, fremdes Format, fremde
Variante, leerer Haken, ein Reel ohne Laenge, ein Bild mit Laenge, eine
Zeit ohne Zeitzone - alles bricht ab, statt eine unbrauchbare Zeile zu
hinterlassen. Derselbe Post wird nie zweimal eingetragen.

Beim Posten darf das Manifest nichts kaputt machen: `eintragen_still()`
meldet den Fehler und laesst den Post leben. Eine fehlende Zeile holt die
Montagsroutine nach, ein verlorener Post nicht.

Angeschlossen ist bisher der Instagram-Tagespost
(`scripts/instagram.py posten`, `look` = `tagesgrafik-formNN`). Die Reels
kommen aus `pulse-studio/scripts/instagram_reel.py` und werden dort
angeschlossen; Threads postet noch nicht, nur Container.

### Zwei Dateien, ein Manifest

Geschrieben wird immer nur in die eigene Datei, gelesen aus allen. Der
Tagespost schreibt nach `kaspa-pulse/data/insights/manifest.jsonl`, das
Reel nach `pulse-studio/data/insights/manifest.jsonl`. Ein Lauf auf GitHub
kann nicht in das andere Repo schreiben, und ein zweiter Schreibweg waere
ein zweiter Weg, auf dem etwas schiefgeht.

Der Sammler liest beide. `UHRWERK_MANIFEST` nennt die Dateien, getrennt wie
ein Suchpfad:

    UHRWERK_MANIFEST=data/insights/manifest.jsonl:studio/data/insights/manifest.jsonl

Dafuer holt `uhrwerk.yml` pulse-studio als zweite, nur lesende Auscheckung
nach `studio/` (siehe den Workflow unten). Steht die Variable nicht, liest
der Sammler nur die eigene Datei - dann fehlen die Reels in der
Auswertung, und nichts geht kaputt.

Bens Handposts traegt die Montagsroutine nach:

    python3 scripts/post_manifest.py --eintragen --kanal x --post-id 18... \
      --format text --look - --hook "..." --hashtags 0 --quelle hand
    python3 scripts/post_manifest.py --nachtragen   # aus den alten logs

## Der Sammler

Zwei Zeitpunkte je Post, 24 Stunden und 7 Tage. Ein Fenster wird beim
ersten Lauf genommen, bei dem der Post alt genug ist, und danach nie
wieder. Wird ein Fenster mehr als um die Haelfte verpasst (Nachtrag alter
Posts, ausgefallener Timer), steht `nachtrag: true` in der Zeile - eine
spaet gemessene 24-Stunden-Zahl ist keine 24-Stunden-Zahl.

Eine Story hat nur das Fenster 24 h; nach 24 Stunden ist sie samt Zahlen
weg. Bei einem Takt von 6 Stunden kann das knapp werden, was dann fehlt,
steht als `fehlt` in der Zeile.

Ein Kanal, der nicht laeuft, nimmt die anderen nicht mit: jeder Fehler ist
eine Zeile im Bericht, nicht das Ende des Laufs. Eine Metrik, die ein
Medium nicht kennt, wird einzeln nachgefragt (Graph laesst sonst den ganzen
Aufruf scheitern) und sonst als fehlend vermerkt.

Metriken:

* Instagram: `reach`, `views`, `likes`, `comments`, `shares`, `saved`,
  `total_interactions`, `follows`, `profile_visits`; Story stattdessen
  `reach`, `views`, `replies`, `navigation`, `total_interactions`.
* Threads: `views`, `likes`, `replies`, `reposts`, `quotes`, `shares`.
* X: siehe unten.

Die Followerzahl geben alle drei APIs nur fuer jetzt her, nie fuer damals.
Darum schreibt jeder Lauf die aktuelle Zahl in `follower.jsonl`, und die
Schnappschuesse tragen die letzte Zahl **vor** dem Post als
`follower_bei_post`. Bis die Reihe laeuft, fehlt das Feld. Geraten wird
nicht.

## Tokens

Nur aus der Umgebung, aus den GitHub Secrets. Sie stehen in keiner Datei,
in keiner Ausgabe und in keiner Discord-Nachricht. Bei Instagram und
Threads geht das Token in den `Authorization`-Kopf, nie in die Adresse -
eine Adresse landet in Protokollen, ein Kopf nicht. Fehlermeldungen tragen
nur Wirt und Pfad, nie die Parameter. Jede geschriebene Zeile laeuft durch
`sauber()`; findet sich darin etwas, das wie ein Token aussieht, wird nicht
geschrieben. Ein fehlendes Token ist kein Abbruch, sondern eine Zeile im
Bericht.

## Was X liefert

X kennt drei Gruppen: `public_metrics` (Likes, Antworten, Reposts, Quotes,
Bookmarks, `impression_count`), `non_public_metrics` (`impression_count`,
`user_profile_clicks`, `url_link_clicks`) und `organic_metrics` (dasselbe
plus Likes und Reposts). Die beiden letzten gelten nur fuer eigene Posts,
nur 30 Tage zurueck, und erst ab einer bestimmten Zugangsstufe.

**ERGEBNIS DER PROBE (Ben, 16.10.2026): unser Zugang liefert alle drei
Gruppen.** Damit kommen Reichweite, Profilklicks und Linkklicks direkt aus
der API, und der CSV-Export wird nicht gebraucht. Der Leser dafuer bleibt
trotzdem liegen: die Zugangsstufe kann sich aendern, und `non_public` und
`organic` reichen nur 30 Tage zurueck. Faellt eine Gruppe weg, setzt die
Probe `csv_noetig` wieder auf `true`.

Die Probe fragt alle drei Gruppen einzeln, weil kein Handbuch verlaesslich
sagt, was ein Zugang hergibt:

    python3 scripts/uhrwerk_proben.py --x-metriken

Sie meldet je Gruppe, was ankommt oder mit welcher Begruendung abgelehnt
wird, und setzt `csv_noetig`. Steht dort `true`, kommen Reichweite und
Klicks aus dem CSV-Export der X-Analyse, den Ben montags hochlaedt:

    python3 scripts/x_analytics_csv.py --datei ~/Downloads/account_overview.csv

Er haengt nicht an einer festen Kopfzeile (X hat "Tweet id" zu "Post id"
und "Retweets" zu "Reposts" umbenannt), liest Punkt, Komma und Leerzeichen
als Tausendertrennung, nimmt unbekannte Spalten unter `weitere` mit und
meldet jeden Post, der nicht im Manifest steht. Der Stand gehoert zum
Schluessel: derselbe Export zweimal eingelesen schreibt nichts, der Export
der naechsten Woche schreibt neue Zeilen.

## Kennt Graph Trial Reels

Ein Trial Reel geht nur an Menschen, die uns nicht folgen - fuer einen
Variantentest das saubere Besteck.

**ERGEBNIS DER PROBE (Ben, 16.10.2026): das Feld `is_trial` gibt es an
unseren Medien.** Das heisst: diese API-Version kennt Trial Reels. Es
heisst noch nicht, dass das Anlegen das Feld auch annimmt - Graph
verschluckt unbekannte Felder beim Anlegen still. Der Beweis ist ein Lauf
mit `--container`, bei dem `is_trial` zurueckgelesen wird. Der gehoert vor
den ersten Variantentest, nicht davor in die Planung.

Die Probe:

    python3 scripts/uhrwerk_proben.py --ig-trial-reels
    python3 scripts/uhrwerk_proben.py --ig-trial-reels --container --video-url https://...

Erst lesen (gibt es `is_trial` an unseren Medien), dann auf Wunsch einen
Container anlegen. **Veroeffentlicht wird nie.** Und eine Warnung zum
Lesen des Ergebnisses: Graph ignoriert unbekannte Felder beim Anlegen oft
still. "Container angelegt" ist kein Beweis. Beweis ist, dass `is_trial`
beim Lesen zurueckkommt - das steht in der Ausgabe getrennt als `beweis`.

## Klicks je Kurzlink: dafuer gibt es keine Quelle

Die Kurzlinks (`kaspapulse.com/ig`, `/x`, `/threads`, `/yt`, `/discord`)
sind statische Seiten auf GitHub Pages. GitHub Pages fuehrt kein
Protokoll, das wir lesen koennen, und eine Zaehlung im Browser hat die
Weiterleitung mit `meta refresh` absichtlich nicht - sie wuerde genau die
Besucher verlieren, fuer die der Kurzlink gemacht ist (App-Browser,
abgeschaltetes Skript).

Gemessen wird deshalb erst die Anmeldung, nicht der Klick:
`UTM_SOURCE` steht als Kontaktattribut in Brevo, der Sammler zaehlt die
Anmeldungen der letzten sieben Tage je Kanal nach
`data/insights/trichter.jsonl`. Das ist die Zahl, die zaehlt, aber es ist
nicht die Klickzahl.

Drei Wege zu echten Klicks, Bens Entscheidung, nichts davon ist gebaut:

1. **Cloudflare vor kaspapulse.com.** Web Analytics ist kostenlos und
   zaehlt Aufrufe je Pfad, also `/ig` gegen `/x`. Aufwand: DNS umziehen,
   etwa 1 h, danach nichts mehr.
2. **Ein eigener Zaehler** als kleine Funktion (Cloudflare Worker o. ae.)
   vor der Weiterleitung. Volle Kontrolle, eine Stelle mehr, die ausfallen
   kann. Etwa 3 h.
3. **So lassen.** Anmeldungen je Kanal reichen fuer die Frage, welcher
   Kanal traegt. Kostet nichts.

Empfehlung: 1, und erst wenn die Anmeldungszahlen zu duenn sind, um einen
Unterschied zu zeigen.

## Der Ausreisser-Alarm

Reichweite ab dem Dreifachen des Kanal-Medians der letzten 30 Posts
(Fenster 24 h) - eine Zeile nach #moderator-only, mit Link und "Kommentare
jetzt beantworten".

Median, nicht Mittel: ein einzelner Treffer zieht ein Mittel mit und hebt
die Schwelle genau dann, wenn sie greifen soll. Unter sieben Posts je
Kanal gibt es keinen Alarm; ein Median aus drei Zahlen ist eine Meinung.
Beides steht im Selbsttest.

## Wo der Sammler laeuft

Der Takt kommt von c2, der Code laeuft auf GitHub - wie bei allem anderen
hier, und aus zwei Gruenden: GitHubs eigene geplante Laeufe kommen in
diesem Konto sechs bis sieben Stunden zu spaet, und die Tokens liegen in
den GitHub Secrets. Der Sammler auf c2 selbst wuerde eine zweite Stelle
mit Tokens schaffen, ohne etwas zu gewinnen.

In `takt.conf` steht `UHRWERK_LIVE=trocken`, in `ausloesen.sh` die beiden
Faelle `uhrwerk` und `uhrwerk-trichter`. **Beides ist untaetig, solange der
Timer fehlt.**

### Timer, von Hand (`deploy/c2/taktgeber/takt-uhrwerk.timer`)

```ini
[Unit]
Description=Kaspa Pulse Takt, Reichweiten-Uhrwerk alle 6 Stunden

[Timer]
Unit=takt@uhrwerk.service
# 06:40, 12:40, 18:40, 00:40 Berlin. Bewusst nicht zur vollen Stunde und
# nicht um 09:30: der Tagespost soll zuerst draussen sein.
OnCalendar=*-*-* 00,06,12,18:40:00 Europe/Berlin
# Persistent: ein verpasster Lauf wird nachgeholt. Ein Fenster, das dabei
# zu spaet kommt, erkennt der Sammler selbst und schreibt nachtrag: true.
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
```

### Montags, Anmeldungen (`deploy/c2/taktgeber/takt-uhrwerk-trichter.timer`)

```ini
[Unit]
Description=Kaspa Pulse Takt, Uhrwerk Montagszahlen

[Timer]
Unit=takt@uhrwerk-trichter.service
# Montags 07:26, vor der Montagsroutine.
OnCalendar=Mon *-*-* 07:26:00 Europe/Berlin
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
```

Einschalten:

    sudo cp takt-uhrwerk.timer takt-uhrwerk-trichter.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now takt-uhrwerk.timer takt-uhrwerk-trichter.timer
    systemctl list-timers 'takt-*'

### Workflow, von Hand (`.github/workflows/uhrwerk.yml`)

```yaml
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
          python3 scripts/insights_sammler.py --sammeln --modus "${{ inputs.modus || 'trocken' }}"

      - name: anmeldungen je kanal
        if: inputs.trichter == 'true'
        env:
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
        run: |
          python3 scripts/insights_sammler.py --trichter --modus "${{ inputs.modus || 'trocken' }}"

      # IMMER committen, auch nach einem roten Schritt: ein Fenster, das
      # gemessen und nicht gesichert wurde, wird nie wieder gemessen.
      # [skip ci] ist Guertel und Hosentraeger - ein Push mit GITHUB_TOKEN
      # loest ohnehin keine Action aus.
      - name: schnappschuesse sichern
        if: always()
        run: |
          git config user.name "kaspa-pulse-bot"
          git config user.email "bot@kaspapulse.com"
          git add -- data/insights/
          if git diff --staged --quiet -- data/insights/; then
            echo "nichts gemessen, nichts zu committen"
            exit 0
          fi
          git commit -q -m "uhrwerk schnappschuesse $(date -u +%Y-%m-%dT%H:%M) [skip ci]"
          # Die gemessenen Dateien ZUERST beiseitelegen, aus dem sauberen
          # Stand nach dem Commit. Nach einem gescheiterten Rebase stehen
          # Konfliktmarken in der Datei - eine Kopie von dann waere Muell.
          rm -rf /tmp/ins-eigen && cp -r data/insights /tmp/ins-eigen
          OK=nein
          for N in 1 2 3; do
            if git pull --rebase --autostash -q origin main; then
              :
            else
              # Dateien, die nur wachsen: beide Seiten behalten, Zeilen
              # ohne Dopplung vereinen. Ein Rebase kann das nicht wissen.
              echo "rebase-konflikt, zeilen werden vereint"
              git rebase --abort 2>/dev/null || true
              git reset --hard -q origin/main 2>/dev/null || true
              python3 - <<'EOF'
          import pathlib
          eigen, ziel = pathlib.Path("/tmp/ins-eigen"), pathlib.Path("data/insights")
          ziel.mkdir(parents=True, exist_ok=True)
          for q in sorted(eigen.glob("*.jsonl")):
              z = ziel / q.name
              kennt = set(z.read_text(encoding="utf-8").splitlines() if z.exists() else [])
              neu = [l for l in q.read_text(encoding="utf-8").splitlines()
                     if l.strip() and l not in kennt]
              if neu:
                  with open(z, "a", encoding="utf-8") as fh:
                      fh.write("\n".join(neu) + "\n")
              print("%s: %d zeilen dazu" % (q.name, len(neu)))
          EOF
              git add -- data/insights/
              git diff --staged --quiet -- data/insights/ || \
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
            mkdir -p artefakt && cp -r /tmp/ins-eigen artefakt/insights || true
          fi

      - name: nicht gesicherte zeilen als artefakt
        if: always() && hashFiles('artefakt/insights/*') != ''
        uses: actions/upload-artifact@v4
        with:
          name: uhrwerk-nicht-gesichert
          path: artefakt/insights
          retention-days: 30

  proben:
    # Laeuft nur, wenn Ben sie ausdruecklich anstoesst. Eine leere Eingabe
    # ist hier kein "beide": der Vergleich mit dem Namen ist absichtlich
    # ausgeschrieben, contains() waere bei einer leeren Eingabe wahr.
    if: inputs.proben == 'x-metriken' || inputs.proben == 'trial-reels' || inputs.proben == 'beide'
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
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
      # Aufruf ohne ihn mit http 403 ab (gemessen an der ersten Probe,
      # 16.10.2026). Im Skript geht er durch insights_sammler.hole, und
      # dort prueft der Selbsttest den Kopf an der Anfrage selbst.
      - name: ergebnis nach ops
        if: always()
        env:
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
          LAUF: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          python3 scripts/uhrwerk_proben.py --melden --ordner proben \
            --modus "${{ inputs.modus || 'trocken' }}"

      - name: proben als artefakt
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: uhrwerk-proben
          path: proben
          if-no-files-found: ignore
          retention-days: 30
```

Die Proben startet Ben nach dem Einsetzen einmal von Hand: Actions,
reichweiten-uhrwerk, Run workflow, `proben: beide`, `sammeln: nein`.

### Reel-Workflow, drei Schritte mehr (`pulse-studio/.github/workflows/instagram-reel.yml`)

`instagram-reel.yml` committet bisher nichts. Der Reel-Lauf schreibt seine
Manifest-Zeile also auf den Laeufer, und mit dem Laeufer ist sie weg.
Zuerst oben im Workflow `permissions: contents: write` statt `read`, dann
diese drei Schritte ans Ende des Jobs `reel`:

```yaml
      # ------------------------------------------------------------------
      # Reichweiten-Uhrwerk: die Manifest-Zeile des Reels sichern.
      # always(): ein veroeffentlichtes Reel ohne Zeile im Manifest taucht
      # in keiner Auswertung auf, auch wenn der Lauf danach rot wurde.
      # Committet wird AUSSCHLIESSLICH data/insights/manifest.jsonl - nichts
      # aus dem Bau, keine mp4, kein Cover.
      - name: manifest sichern
        id: manifest
        if: always() && steps.faellig.outputs.los == 'ja'
        run: |
          DATEI=data/insights/manifest.jsonl
          ZEILE=/tmp/manifest-zeile.jsonl
          NACHRICHT="uhrwerk manifest, reel $(date -u +%Y-%m-%d) [skip ci]"
          git config user.name "pulse-studio-bot"
          git config user.email "bot@kaspapulse.com"
          git add -- "$DATEI"
          if git diff --staged --quiet -- "$DATEI"; then
            echo "keine neue manifest-zeile, nichts zu tun"
            echo "gesichert=leer" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          # Die neue Zeile ZUERST beiseitelegen. Sie ist das, was zaehlt;
          # alles darunter darf scheitern. Nach einem gescheiterten Rebase
          # stehen Konfliktmarken in der Datei, eine Kopie von dann waere
          # Muell.
          git diff --staged -U0 -- "$DATEI" | sed -n 's/^+\({.*\)$/\1/p' > "$ZEILE"
          echo "zeile gesichert: $(wc -l < "$ZEILE")"
          git commit -q -m "$NACHRICHT"
          OK=nein
          for N in 1 2 3; do
            if git pull --rebase --autostash -q origin main; then
              :
            else
              # Eine Datei, die nur waechst: beide Seiten behalten. Statt
              # einen Konflikt zu loesen, wird vom frischen Stand aus neu
              # angehaengt - dasselbe gilt, wenn schon das Holen scheitert.
              echo "rebase-konflikt oder kein netz, zeile wird neu angehaengt"
              git rebase --abort 2>/dev/null || true
              git reset --hard -q origin/main 2>/dev/null || true
              mkdir -p "$(dirname "$DATEI")"
              cat "$ZEILE" >> "$DATEI"
              git add -- "$DATEI"
              git commit -q -m "$NACHRICHT" || true
            fi
            if git push -q origin HEAD:main; then OK=ja; break; fi
            echo "push $N fehlgeschlagen"
            sleep "$N"
          done
          if [ "$OK" = "ja" ]; then
            echo "manifest-zeile ist auf main"
            echo "gesichert=ja" >> "$GITHUB_OUTPUT"
          else
            echo "::warning::manifest-zeile nicht auf main, sie geht als artefakt mit"
            cp "$ZEILE" manifest-zeile.jsonl
            echo "gesichert=nein" >> "$GITHUB_OUTPUT"
          fi
          exit 0

      - name: manifest-zeile als artefakt
        if: always() && steps.manifest.outputs.gesichert == 'nein'
        uses: actions/upload-artifact@v4
        with:
          name: uhrwerk-manifest-zeile
          path: manifest-zeile.jsonl
          retention-days: 90

      # ops_sagen.py statt eingebautem Python: es setzt den User-Agent,
      # ohne den Discord mit http 403 ablehnt, blendet den Webhook aus
      # jeder Ausgabe aus und haengt LAUF als zweite Zeile an. Der
      # Reel-Lauf bleibt gruen - das Reel ist draussen, nur die Zeile
      # fehlt, und die laesst sich von Hand eintragen.
      - name: ops, wenn die zeile nicht auf main kam
        if: always() && steps.manifest.outputs.gesichert == 'nein'
        env:
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
          LAUF: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          ZEILE=$(head -c 600 manifest-zeile.jsonl 2>/dev/null || true)
          python3 scripts/ops_sagen.py "uhrwerk, das reel ist raus, die manifest-zeile kam nicht auf main. sie liegt als artefakt uhrwerk-manifest-zeile am lauf. $ZEILE"
```

Geprueft, nicht nur gelesen: beide Commit-Schritte sind aus dem YAML
herausgeloest und gegen echte Repos gelaufen. Ein fremder Push dazwischen
(Rebase-Konflikt in einer Datei, die nur waechst), ein sauberer Push,
nichts zu committen und dreimal kein Netz - in allen vier Faellen bleibt
der Lauf gruen, und keine Zeile geht verloren oder steht doppelt.

## Trockenlauf, zwei Tage

`UHRWERK_LIVE=trocken` schreibt die Schnappschuesse und schickt die Meldung
nach #moderator-only, mit `[trockenlauf]` davor. Mehr passiert nicht: das
Uhrwerk schreibt ohnehin in keinen anderen Kanal.

**Auch der Ausreisser-Alarm geht im Trockenlauf raus**, gekennzeichnet.
Das ist der Sinn der zwei Tage - ein Alarm, der zwei Tage lang nur im
Lauf-Log steht, hat nichts gezeigt. Auf `scharf` faellt nur das
Kennzeichen weg.

Der erste Schnappschuss ist 24 Stunden nach dem ersten Post im Manifest
moeglich, nicht frueher: vorher ist kein Fenster faellig.

**Der User-Agent.** Discord lehnt einen urllib-Aufruf ohne User-Agent mit
http 403 ab (gemessen an der ersten Probe, 16.10.2026). Er steht deshalb
an genau einer Stelle, in `insights_sammler.hole`, und jede Meldung geht
durch `insights_sammler.melden`. Die Workflows bauen keine eigene
Discord-Anfrage mehr; der Selbsttest prueft den Kopf an der Anfrage
selbst und dass dieses Skript sich nicht wieder eine eigene baut.

## Was nach dem 20.10. kommt

* `config/zeitplan.json`: Slots, Varianten A/B und Anteil (80/20) je Kanal,
  statt im Code. Generatoren und Timer lesen daraus, Looks verteilen sich
  gleichmaessig ueber die Varianten. Plananderungen nur per PR.
* `data/experimente.jsonl`: Test, Start, Ende, Varianten, Ergebnis,
  Entscheidung.
* Auswertung im Code: Median, mindestens 7 Posts je Variante, Sieger erst
  ab 20 % Vorsprung, sonst bleibt der alte Wert.
* Montags 07:30 Berlin eine Rohtabelle je Kanal nach
  `reports/uhrwerk-roh-<datum>.md`. Den Bericht schreibt die Routine, nicht
  dieses Skript.

Telegram und Discord bleiben auf festen Zeiten und sind nicht dabei.
