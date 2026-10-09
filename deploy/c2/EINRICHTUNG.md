# c2 einrichten, Schritt für Schritt

Ben, 09.10.2026. Hetzner CX23, Nürnberg, Ubuntu 24.04. Cloud-Firewall
eingehend nur SSH und ICMP.

**In dieser Datei steht kein Wert.** Keine IP, kein Token, kein Webhook.
Nur Namen und Befehle. Was auf dem Bildschirm des Servers erscheint,
bleibt dort: nichts davon in einen Chat kopieren.

Alles, was einen Wert zeigt, ist so gebaut, dass es nur die **Länge**
oder die **Größe** nennt.

---

## Vorab: drei Dinge, die vorher stimmen müssen

| was | wie geprüft |
| --- | --- |
| SSH vom Mac klappt | steht |
| `SERVER_HOST` als Secret in `kaspa-pulse` | steht |
| Die Cloud-Firewall lässt SSH von GitHubs Runnern durch | Port 22 ist eingehend offen, also ja. Nach Schritt 1.6 nur noch mit Schlüssel, kein Passwort |

---

## Schritt 1 — setup.sh

### 1.0 Einmal auf dem Mac: `~/.ssh/config`

Damit unten überall `ssh c2` steht und weder Hostname noch Schlüsselname in
einem Befehl auftauchen, der im Repo oder im Chat landet:

```
Host c2
  HostName <die IPv4 von c2>
  User root
  IdentityFile ~/.ssh/hetzner_c2
  IdentitiesOnly yes
```

`IdentitiesOnly yes`, damit ssh nicht erst die anderen Schlüssel im Agenten
durchprobiert — sonst greift nach Schritt 1.6 `MaxAuthTries 3`. Gegenprobe:
`ssh c2 true` läuft stumm durch.

### 1.1 Anmelden und die Grundlage legen

`setup.sh` liegt im Repo, das Repo liegt noch nicht auf dem Server. Also
zuerst diese Zeilen von Hand, dann holt sich alles Weitere das Skript
selbst:

```sh
ssh c2
apt-get update -qq && apt-get install -y -qq git
useradd --system --create-home --shell /bin/bash kpbot
install -d -o kpbot -g kpbot -m 0700 /home/kpbot/.ssh
ssh-keyscan -t ed25519 github.com > /home/kpbot/.ssh/known_hosts 2>/dev/null
ssh-keygen -lf /home/kpbot/.ssh/known_hosts
```

Die letzte Zeile muss genau diesen Fingerabdruck zeigen:

```
SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
```

Das ist GitHubs veröffentlichter ed25519-Fingerabdruck (docs.github.com,
„GitHub's SSH key fingerprints"). Stimmt er nicht, **nicht
weitermachen** — dann sitzt etwas zwischen c2 und GitHub. Danach:

```sh
chown kpbot:kpbot /home/kpbot/.ssh/known_hosts
sudo -u kpbot ssh-keygen -q -t ed25519 -N "" -C "c2 deploy key kaspa-pulse" -f /home/kpbot/.ssh/id_ed25519
cat /home/kpbot/.ssh/id_ed25519.pub
```

Die letzte Zeile zeigt den **öffentlichen** Teil des Deploy Keys. Der
private Teil verlässt c2 nie.

### 1.2 Deploy Key auf GitHub eintragen

`github.com/neoalphavault-png/kaspa-pulse` → **Settings → Deploy keys →
Add deploy key**. Titel z. B. `c2`, Schlüssel einsetzen, **„Allow write
access" anhaken** (der stündliche Sync pusht Stand und Abdeckung).

### 1.3 Repo holen

```sh
sudo -u kpbot ssh -T git@github.com
install -d -o kpbot -g kpbot -m 0755 /opt/kaspa-pulse
sudo -u kpbot git clone git@github.com:neoalphavault-png/kaspa-pulse.git /opt/kaspa-pulse
```

Die zweite Zeile muss sein: `/opt` gehört `root`, `kpbot` darf dort sonst
nichts anlegen. `git clone` in ein leeres Verzeichnis ist in Ordnung.

Die erste Zeile muss `successfully authenticated` sagen. Tut sie es
nicht, ist der Deploy Key noch nicht drin.

### 1.4 setup.sh, der Rest der Grundlage

```sh
cd /opt/kaspa-pulse/deploy/c2
sudo ./setup.sh grundlage
```

Das Skript ist wiederholbar und tut nur, was noch fehlt: Pakete
(`git curl python3 ca-certificates openssh-client`, mehr braucht c2
nicht), den Nutzer `kpdeploy`, `/etc/credstore.encrypted` mit Modus 700,
`/var/lib/kaspa-pulse`, die beiden Schreibhilfen unter `/usr/local/sbin/`
und die sudoers-Regel. Den Deploy Key aus 1.1 lässt es stehen.

Es prüft außerdem den Fingerabdruck von `github.com` gegen den
veröffentlichten Wert und bricht ab, wenn er nicht stimmt.

### 1.5 Später: Stand nachholen

Der Klon in 1.3 lief schon als `kpbot`, Besitzer und Rechte stimmen
also. Für jedes spätere Update reicht

```sh
sudo /opt/kaspa-pulse/deploy/c2/setup.sh klonen
```

Es holt den neuesten `main` und setzt den Besitzer gerade, falls doch
einmal etwas als `root` angelegt wurde.

### 1.6 sshd härten

**Vorher eine zweite SSH-Sitzung offen lassen.** Dann:

```sh
sudo ./setup.sh haerten
```

Setzt `PasswordAuthentication no`, `PermitRootLogin prohibit-password`,
kein X11- und kein Agent-Forwarding, `MaxAuthTries 3`. Prüft die
Einstellung mit `sshd -t`, bevor es neu lädt.

---

## Schritt 2 — der Schlüssel für die Actions

Der Deploy Key aus Schritt 1 geht **von c2 zu GitHub**. Jetzt kommt der
Schlüssel für die andere Richtung: **von GitHub zu c2**, nur um Secrets
abzulegen.

### 2.1 Auf dem Mac erzeugen

```sh
ssh-keygen -t ed25519 -N "" -C "github actions server-secrets" -f ~/.ssh/kp-c2-actions
```

Der private Teil geht später in das Secret, der öffentliche auf c2. Er
wird **auf dem Mac** erzeugt, damit der private Teil nie auf dem Server
liegt.

### 2.2 Öffentlichen Teil auf c2 eintragen

```sh
scp ~/.ssh/kp-c2-actions.pub c2:/tmp/actions.pub
ssh c2 'cd /opt/kaspa-pulse/deploy/c2 && ./setup.sh runner /tmp/actions.pub && rm /tmp/actions.pub'
```

Damit steht in der `authorized_keys` von `kpdeploy`:

```
restrict,command="/usr/local/sbin/kp-credstore-ssh" ssh-ed25519 AAAA…
```

**Dieser Schlüssel kann keine Shell bekommen.** `restrict` nimmt
Terminal, Port- und Agent-Forwarding weg, der erzwungene Befehl lässt
genau zwei Dinge zu:

| Befehl | Wirkung |
| --- | --- |
| `put discord_webhook` ⎪ `put telegram_bot_token` ⎪ `put telegram_chat_id` | nimmt einen Wert von stdin, legt ihn verschlüsselt ab |
| `liste` | zeigt Namen, Größen und Datum der Credentials, keine Werte |

`put gh_dispatch_token` weist der Server ausdrücklich ab.

---

## Schritt 3 — SERVER_SSH_KEY und SERVER_HOST_KEY

### 3.1 SERVER_SSH_KEY

Auf dem Mac, kopiert den privaten Teil in die Zwischenablage, ohne ihn
auf den Bildschirm zu schreiben:

```sh
pbcopy < ~/.ssh/kp-c2-actions
```

Dann auf GitHub, `kaspa-pulse` → **Settings → Secrets and variables →
Actions → New repository secret**, Name **`SERVER_SSH_KEY`**, einsetzen.
Der ganze Inhalt der Datei, von der `BEGIN`-Zeile bis zur `END`-Zeile; die
Zeilenumbrüche müssen mit.

Kopf- und Fußzeile stehen hier bewusst nicht wörtlich: unser eigener
`secret-scan` erkennt diese Zeile als privaten Schlüssel, und das soll er
auch — auch in einer Anleitung.

### 3.2 SERVER_HOST_KEY

Auf c2:

```sh
cd /opt/kaspa-pulse/deploy/c2 && sudo ./setup.sh hostkey
```

Gibt genau **eine Zeile** aus: die IP, dann `ssh-ed25519`, dann der
Schlüssel. Diese Zeile wird der Wert des Secrets **`SERVER_HOST_KEY`**.
Darunter steht der Fingerabdruck — der muss zu dem passen, den der Mac
beim ersten `ssh` gezeigt hat (`ssh-keygen -lf ~/.ssh/known_hosts`
filtert ihn heraus).

Damit prüft der Lauf die Gegenstelle, statt `StrictHostKeyChecking=no`
zu setzen.

---

## Schritt 4 — server-secrets.yml

Die Datei liegt nach dem Merge unter
`.github/workflows/server-secrets.yml`.

**Lauf starten:** Actions → `server-secrets` → **Run workflow**

| Eingabe | für die 48 h |
| --- | --- |
| `ziel` | **`moderator`** |
| `was` | `alle` |

`ziel=moderator` nimmt `DISCORD_WEBHOOK_OPS` — der schreibt nach
**#moderator-only**, genau dorthin sollen die 48 h. `ziel=normal` nimmt
`DISCORD_WEBHOOK` und setzt dazu eine gelbe Warnung, weil der Alarm von c2
dann öffentlich postet. Das ist der Schalter nach den 48 h, kein anderer.

Der Lauf überträgt drei Werte über stdin durch die SSH-Verbindung, nie
über eine Kommandozeile. Am Ende zeigt er die Liste der Credentials mit
Namen und Größen und löscht den Schlüssel vom Runner (`shred`).

Erwartet im Log:

```
kp-credstore-put: discord_webhook abgelegt, 187 byte verschluesselt
kp-credstore-put: telegram_bot_token abgelegt, … byte verschluesselt
kp-credstore-put: telegram_chat_id abgelegt, … byte verschluesselt
```

---

## Schritt 5 — gh_dispatch_token, von Hand

Das Token für den Taktgeber kommt **nicht** durch eine Leitung. Es wird
einmal auf dem Server eingetippt.

### 5.1 Token anlegen

GitHub → **Settings → Developer settings → Fine-grained tokens → Generate
new token**

| Feld | Wert |
| --- | --- |
| Resource owner | `neoalphavault-png` |
| Repository access | **Only select repositories**: `kaspa-pulse`, `pulse-studio` |
| Repository permissions | **ausschließlich** `Actions: Read and write` |
| Expiration | setzen und ins Kalender eintragen |

Sonst nichts. Der Taktgeber liest keine Inhalte und schreibt nichts ins
Repo, er drückt einen Knopf.

### 5.2 Auf c2 eingeben

```sh
sudo systemd-ask-password "gh_dispatch_token:" \
  | sudo systemd-creds encrypt --name=gh_dispatch_token - \
    /etc/credstore.encrypted/gh_dispatch_token
sudo chmod 600 /etc/credstore.encrypted/gh_dispatch_token
```

Die Eingabe wird nicht angezeigt und landet in keiner Shell-History.

`systemd-creds` meldet dabei *„Credential secret file … is not located on
encrypted media, using anyway"*. Das ist richtig so: die Hetzner-VM hat
kein TPM, der Hostschlüssel liegt auf der Platte. Das Credential ist
trotzdem an **diesen** Rechner gebunden — auf einem anderen ist die
Datei nutzlos.

### 5.3 Gegenprobe, ohne den Wert zu zeigen

```sh
sudo systemd-creds decrypt --name=gh_dispatch_token \
  /etc/credstore.encrypted/gh_dispatch_token - | wc -c
```

Die Zahl muss zur Länge des Tokens passen. Mehr kommt nicht.

---

## Schritt 6 — Units starten

```sh
cd /opt/kaspa-pulse/deploy/c2 && sudo ./setup.sh units
```

Das Skript bricht ab und sagt, welches Credential fehlt, falls Schritt 4
oder 5 noch offen ist. Sonst verlinkt es beide Gruppen und startet sie:
den Entity-X-Alarm samt stündlichem Sync und die fünf Takt-Timer.

Dann zehn Minuten zusehen:

```sh
journalctl -u entity-x-alarm -f
```

Jede Minute eine Zeile `no alert, balance …`.

Und einmal von Hand takten:

```sh
sudo systemctl start takt@tagesgrafik.service
journalctl -u takt@tagesgrafik.service -n 20 --no-pager
```

Erwartet: `takt: neoalphavault-png/kaspa-pulse tagesgrafik.yml ausgeloest
(main)`, und auf GitHub binnen Sekunden ein Lauf vom Typ
`workflow_dispatch`.

```sh
sudo ./setup.sh pruefen
```

zeigt alles auf einmal: Credentials (Namen, Größen, Länge im Klartext —
nie der Wert), Dienste, die nächsten Takte in Ortszeit, den Repo-Stand
und die Abdeckung.

---

## Schritt 7 — 48 h Parallelbetrieb

**Was läuft:** GitHub und c2 prüfen beide. Doppelte Meldungen sind in
dieser Zeit erwartet — die von c2 landen in **#moderator-only**, nur die
von GitHub im öffentlichen Kanal.

**Was auf der sicheren Seite bleibt:**

| Schalter | Stand | wo |
| --- | --- | --- |
| `REEL_LIVE` | `false` | `takt.conf` auf c2 |
| `REELS_LIVE` | nicht `ja` | Repository-Variable in `pulse-studio` |
| `WN_DRY_RUN` | `true` | `takt.conf` auf c2 |
| `dry_run` | `true` | Vorbelegung in `weeklynumbers.yml` |
| `SERVER_AKTIV` | `false` | Repository-Variable in `kaspa-pulse` |
| `IG_MODUS` | `trocken` | Repository-Variable in `kaspa-pulse` |

Der Taktgeber darf dabei schon takten: er löst nur Läufe aus, die selbst
trocken sind.

**Das Ziel für die 48 h:** mindestens 95 % beobachtete Minuten je
UTC-Tag, größte Lücke unter 30 Minuten.

```sh
journalctl -u entity-x-sync --since "48 hours ago" | tail -40
```

**Danach, und erst dann, einzeln:**

1. `server-secrets.yml` noch einmal, `ziel=normal` — der Alarm von c2
   postet ab jetzt öffentlich.
2. `SERVER_AKTIV` auf `true` — der GitHub-Job überspringt sich selbst
   und die Kette dort endet.
3. `REEL_LIVE`, `WN_DRY_RUN` und `IG_MODUS` jeder für sich, nach
   eigenem Okay.

---

## Zurück, wenn etwas nicht stimmt

| Lage | Handgriff |
| --- | --- |
| Alarm auf c2 macht Unsinn | `sudo systemctl stop entity-x-alarm`, `SERVER_AKTIV` auf `false`, einen Lauf von `entity-x-alert` von Hand starten |
| Takte stören | `sudo systemctl disable --now 'takt-*.timer'` — dann läuft alles wieder über GitHubs cron, nur sechs bis sieben Stunden zu spät |
| Token abgelaufen | `journalctl -u 'takt@*'` zeigt `http 401`. Schritt 5 wiederholen |
| Webhook getauscht | `server-secrets.yml` neu starten, `was=nur-discord` |
