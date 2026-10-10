# Taktgeber auf c2

> **Die vollständige Schrittliste zum Einrichten steht in [../EINRICHTUNG.md](../EINRICHTUNG.md)** — in der Reihenfolge, in der sie
> abgearbeitet wird, mit `setup.sh`, Deploy Key, `server-secrets.yml` und dem
> Token von Hand. Die Abschnitte hier erklären das Warum.

**Der Server gibt den Takt, der Code bleibt auf GitHub.** c2 löst die
Workflows per `workflow_dispatch` zur festen Uhrzeit aus; gerechnet,
gebaut und gepostet wird weiter in den Actions-Läufen.

## Warum

GitHubs geplante Läufe kommen in diesem Konto **durchgehend sechs bis
sieben Stunden zu spät**. Gemessen am 09.10.2026 über vier Workflows:

| Workflow | cron (UTC) | tatsächlich | Verzug |
| --- | --- | --- | --- |
| tagesgrafik | 05:30 / 06:30 | 12:06 / 13:27 | +6:36 / +6:57 |
| kas-candles | 03:10 | 10:24 | +7:14 |
| number-of-day | 08:12 / 09:42 | 15:33 / 16:57 | +7:21 / +7:15 |
| richlist-log | So 03:15 | So 09:17 | +6:02 |

Alles mit einem Zeitfenster läuft damit ins Leere: die Tagesgrafik
liefert nur zwischen 07:00 und 12:00 Berlin, der Instagram-Job nur
zwischen 09:25 und 11:30, der Reel nur ±20 Minuten um die Short-Zeit.
Die Grafiken der letzten Woche kamen deshalb alle aus Handläufen, und im
Log steht es am 01.10. wörtlich: *„kein cron im fenster"*.

## Der Zeitplan

| Takt | wann (Berlin) | löst aus |
| --- | --- | --- |
| `takt-tagesgrafik` | täglich 07:30 | `tagesgrafik.yml` in kaspa-pulse |
| `takt-instagram-bild` | täglich 09:30 | `tagesgrafik.yml`, Eingabe `instagram=trocken` |
| `takt-reel` | Di–So 12:00, Mo 17:00 | `instagram-reel.yml` in pulse-studio |
| `takt-weeklynumbers` | Mo 18:40 | `weeklynumbers.yml` in kaspa-pulse |
| `takt-number-of-day` | täglich 10:12 und 11:42 | `number-of-day.yml` in kaspa-pulse |

Die Uhrzeiten stehen in Ortszeit, als Anhang an der Kalenderzeile:

```
OnCalendar=*-*-* 07:30:00 Europe/Berlin
```

systemd rechnet die Zeitumstellung selbst. Kein zweiter Termin je
Jahreszeit mehr.

> **Nicht `Timezone=`.** Die erste Fassung hatte eine eigene Zeile
> `Timezone=Europe/Berlin` im Abschnitt `[Timer]`. **Diesen Schlüssel gibt
> es nicht.** systemd überliest ihn mit „Unknown key name 'Timezone' in
> section 'Timer', ignoring" und rechnet weiter in UTC — alle fünf Takte
> liefen am 09.10.2026 auf c2 zwei Stunden zu spät. Die Zeitzone gehört an
> die Kalenderzeile (`systemd-analyze calendar` zeigt, was gilt).

## Eingaben: ein Takt ohne Eingaben ist nicht derselbe Lauf

**Ein `workflow_dispatch` ohne Eingaben nimmt die Vorbelegungen aus der
Workflow-Datei — und die sind absichtlich zurückhaltend.** Am 10.10.2026
hat Lauf 37 die Tagesgrafik gebaut und das Artefakt hochgeladen, aber
nichts nach #moderator-only geschickt und nichts ins Log geschrieben:
`senden` steht in `tagesgrafik.yml` auf `false`, damit ein versehentlicher
Handstart nicht sendet.

Was jeder Takt deshalb ausdrücklich mitschickt:

| Takt | Eingaben |
| --- | --- |
| `tagesgrafik` | `senden=true`, `form=` (leer = Rotation), `instagram=aus` |
| `instagram-bild` | `instagram=trocken` |
| `reel` | `live=` aus `REEL_LIVE` in `takt.conf` |
| `weeklynumbers` | `dry_run=` aus `WN_DRY_RUN` in `takt.conf` |
| `number-of-day` | keine, der Workflow hat keine, die zählt |

Wer einen Takt dazunimmt, liest zuerst den `workflow_dispatch`-Abschnitt
des Zielworkflows und schickt jede Eingabe mit, die der Lauf braucht.
`ausloesen.sh` ist die eine Stelle dafür.

**`Persistent=true`** holt einen verpassten Takt nach — außer beim Reel:
ein Reel zwei Stunden nach dem Short ist kein Reel zur Short-Zeit, und
das Fälligkeitsfenster im Skript würde es ohnehin abweisen.

**Die cron-Einträge auf GitHub bleiben stehen.** Sie sind der Rückfall,
und ihre Verspätung ist harmlos: jeder der vier Läufe prüft sein eigenes
Zeitfenster und endet grün ohne Lieferung, wenn er zu spät kommt. Es muss
dafür **keine Workflow-Datei geändert werden**.

## Zwei Schalter, die scharf stellen

Beide stehen bewusst auf der sicheren Seite und werden einzeln umgelegt:

| Schalter | wo | Wirkung |
| --- | --- | --- |
| `REEL_LIVE` | `takt.conf` auf c2 | `false` schickt den Reel-Lauf trocken los. Zusätzlich muss die Repository-Variable `REELS_LIVE` auf `ja` stehen — zwei Schalter, wie abgesprochen |
| `WN_DRY_RUN` | `takt.conf` auf c2 | `true` lässt Weekly Numbers nur rechnen. Auf GitHub ist `dry_run` ebenfalls auf `true` vorbelegt, ein Takt ohne dieses Feld postet also nie |

## Einrichtung

### 1. Repo und Nutzer

Wie beim Entity-X-Alarm: Repo nach `/opt/kaspa-pulse`, Besitzer `kpbot`.
Steht der Alarm schon, ist dieser Schritt erledigt.

### 2. Secrets — die Schrittliste

**In diesem Ordner steht kein Wert.** Übertragen wird wie beim
Entity-X-Alarm, mit `systemd-creds` an den Rechner gebunden verschlüsselt
und über `LoadCredentialEncrypted` gelesen.

| Name | Art | Umfang | liegt danach |
| --- | --- | --- | --- |
| `gh_dispatch_token` | fine-grained PAT | **nur** `neoalphavault-png/kaspa-pulse` und `neoalphavault-png/pulse-studio`, **nur** Permission *Actions: Read and write* | `/etc/credstore.encrypted/gh_dispatch_token` |

Mehr braucht der Taktgeber nicht. Er liest keine Inhalte, schreibt nichts
ins Repo und postet nirgends — er drückt einen Knopf.

Schritt für Schritt:

1. Auf GitHub unter *Settings → Developer settings → Fine-grained tokens*
   ein Token anlegen. **Resource owner** `neoalphavault-png`, **Repository
   access** nur die beiden genannten Repos, **Repository permissions**
   ausschließlich *Actions: Read and write*. Ablaufdatum notieren.
2. Den Wert **einmal** auf c2 eingeben, nie in eine Datei, nie in einen
   Chat, nie in eine Umgebungsvariable einer Shell-History:
   ```
   sudo systemd-ask-password "gh_dispatch_token:" \
     | sudo systemd-creds encrypt --name=gh_dispatch_token - \
       /etc/credstore.encrypted/gh_dispatch_token
   sudo chmod 600 /etc/credstore.encrypted/gh_dispatch_token
   ```
3. Gegenprobe, ohne den Wert zu zeigen:
   ```
   sudo systemd-creds decrypt --name=gh_dispatch_token \
     /etc/credstore.encrypted/gh_dispatch_token - | wc -c
   ```
   Die Zeichenzahl muss zur Länge des Tokens passen. Mehr wird nicht
   ausgegeben.
4. **Ablaufdatum in den Kalender.** Läuft das Token ab, steht jeder Takt
   still, und zwar leise: `takt.sh` meldet `http 401` ins Journal.

### 3. Units verlinken und starten

```
cd /opt/kaspa-pulse/deploy/c2/taktgeber
sudo systemctl link "$PWD/takt@.service"
for t in tagesgrafik instagram-bild reel weeklynumbers number-of-day; do
  sudo systemctl link "$PWD/takt-$t.timer"
done
sudo systemctl enable --now takt-tagesgrafik.timer takt-instagram-bild.timer \
  takt-reel.timer takt-weeklynumbers.timer takt-number-of-day.timer
```

### 4. Erste Probe, von Hand

```
sudo systemctl start takt@tagesgrafik.service
journalctl -u takt@tagesgrafik.service -n 20 --no-pager
```
Erwartet: `takt: neoalphavault-png/kaspa-pulse tagesgrafik.yml ausgeloest (main)`.
Auf GitHub muss binnen Sekunden ein Lauf vom Typ `workflow_dispatch`
erscheinen — nicht in sieben Stunden.

```
systemctl list-timers 'takt-*' --no-pager
```
zeigt die nächsten Zeitpunkte. `systemctl list-timers` schreibt sie in der
Zeitzone des Servers (hier UTC) — das ist richtig, solange die Differenz
stimmt: 07:30 Berlin steht dort im Sommer als 05:30 UTC, im Winter als
06:30 UTC. Wer die Ortszeit sehen will:

```
systemd-analyze calendar '*-*-* 07:30:00 Europe/Berlin'
```

## Wenn etwas nicht geht

| Bild | Ursache |
| --- | --- |
| `http 401` | Token abgelaufen oder falscher Umfang |
| `http 403` | Token hat *Actions: Read and write* nicht, oder das Repo ist nicht in seiner Liste |
| `http 404` | Workflow-Datei heißt anders, oder sie liegt nicht auf `main`. GitHub kennt `workflow_dispatch` nur vom Default-Branch |
| `http 422` | Eine Eingabe, die der Workflow nicht hat |

## Zurück auf GitHub

Die cron-Einträge stehen die ganze Zeit. Es reicht,
`sudo systemctl disable --now 'takt-*.timer'` zu setzen — dann läuft
wieder alles über GitHub, nur eben sechs bis sieben Stunden zu spät. Für
alles mit Zeitfenster heißt das: wieder von Hand.
