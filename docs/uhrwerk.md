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

Eine Datei fuer beide Repos: auf c2 zeigt `UHRWERK_MANIFEST` (aus
`takt.conf`) auf die Datei in kaspa-pulse. Ohne die Variable schreibt jedes
Repo in sein eigenes `data/insights/`.

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

**Welche Stufe unser Zugang hat, sagt kein Handbuch, sondern nur ein
Aufruf.** Aus diesem Container geht keiner: `api.x.com` ist hier
gesperrt, und die vier Secrets liegen nicht hier. Darum die Probe, die auf
GitHub laeuft und alle drei Gruppen einzeln fragt:

    python3 scripts/uhrwerk_proben.py --x-metriken

Sie meldet je Gruppe, was ankommt oder mit welcher Begruendung abgelehnt
wird, und setzt `csv_noetig`. Steht dort `true`, kommen Reichweite und
Klicks aus dem CSV-Export der X-Analyse. Der Leser dafuer steht schon:

    python3 scripts/x_analytics_csv.py --datei ~/Downloads/account_overview.csv

Er haengt nicht an einer festen Kopfzeile (X hat "Tweet id" zu "Post id"
und "Retweets" zu "Reposts" umbenannt), liest Punkt, Komma und Leerzeichen
als Tausendertrennung, nimmt unbekannte Spalten unter `weitere` mit und
meldet jeden Post, der nicht im Manifest steht. Der Stand gehoert zum
Schluessel: derselbe Export zweimal eingelesen schreibt nichts, der Export
der naechsten Woche schreibt neue Zeilen.

## Kennt Graph Trial Reels

Ein Trial Reel geht nur an Menschen, die uns nicht folgen - fuer einen
Variantentest das saubere Besteck. Auch das ist von hier aus nicht
pruefbar: `graph.facebook.com` ist gesperrt. Die Probe:

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
on:
  workflow_dispatch:
    inputs:
      modus:
        description: "trocken = nur schreiben und melden, scharf = mit alarm"
        required: false
        default: "trocken"
        type: string
      trichter:
        description: "anmeldungen je kanal (montags)"
        required: false
        default: "false"
        type: string
permissions:
  contents: write
jobs:
  sammeln:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: selbsttests
        run: |
          python3 scripts/post_manifest.py --selbsttest
          python3 scripts/insights_sammler.py --selbsttest
          python3 scripts/x_analytics_csv.py --selbsttest
          python3 scripts/uhrwerk_proben.py --selbsttest
      - name: schnappschuesse
        env:
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
          python3 scripts/insights_sammler.py --sammeln --modus "${{ inputs.modus }}"
      - name: anmeldungen je kanal
        if: inputs.trichter == 'true'
        env:
          BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
          DISCORD_WEBHOOK_OPS: ${{ secrets.DISCORD_WEBHOOK_OPS }}
        run: |
          python3 scripts/insights_sammler.py --trichter --modus "${{ inputs.modus }}"
      # Immer committen, auch wenn ein Kanal rot war: was gemessen wurde,
      # soll nicht verloren gehen, sonst wird dasselbe Fenster nie wieder
      # gemessen.
      - name: commit
        if: always()
        run: |
          git config user.name "kaspa-pulse-bot"
          git config user.email "bot@kaspapulse.com"
          git add data/insights/
          if git diff --staged --quiet; then
            echo "nothing changed"
          else
            git commit -m "uhrwerk schnappschuesse $(date -u +%Y-%m-%dT%H:%M)"
            git pull --rebase origin main
            git push
          fi
```

## Trockenlauf, zwei Tage

`UHRWERK_LIVE=trocken` schreibt die Schnappschuesse und schickt die Meldung
nach #moderator-only, sonst nichts. Nach zwei stillen Tagen auf `scharf` -
dann kommt auch der Ausreisser-Alarm. Der erste Schnappschuss ist 24
Stunden nach dem ersten Post im Manifest moeglich, nicht frueher: vorher
ist kein Fenster faellig.

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
