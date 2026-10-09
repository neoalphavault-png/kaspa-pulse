#!/bin/sh
# setup.sh - c2 einrichten: Entity-X-Alarm und Taktgeber.
#
# IN DIESER DATEI STEHT KEIN WERT. Kein Token, kein Webhook, keine IP,
# kein Hostname. Namen ja, Werte nein.
#
# Jeder Schritt ist wiederholbar. Ein zweiter Lauf aendert nichts, was
# schon richtig steht, und bricht ab, statt etwas zu ueberschreiben.
#
#   sudo ./setup.sh grundlage         Pakete, Nutzer, Ordner, Deploy-Key erzeugen
#   sudo ./setup.sh klonen            Repo nach /opt/kaspa-pulse holen
#   sudo ./setup.sh runner DATEI      oeffentlichen Actions-Schluessel eintragen
#   sudo ./setup.sh hostkey           die Zeile fuer SERVER_HOST_KEY zeigen
#   sudo ./setup.sh haerten           sshd: keine Passwoerter, kein root-Login
#   sudo ./setup.sh units             Units verlinken und starten
#   sudo ./setup.sh pruefen           Gegenprobe, zeigt keine Werte
#
# Reihenfolge: grundlage, Deploy Key auf GitHub eintragen, klonen,
# runner, hostkey, haerten, dann die Secrets (server-secrets.yml und
# systemd-ask-password), zuletzt units. Die ganze Liste steht in
# deploy/c2/EINRICHTUNG.md.
set -eu

ZIEL=/opt/kaspa-pulse
REPO_SSH="git@github.com:neoalphavault-png/kaspa-pulse.git"
DIENSTNUTZER=kpbot          # laesst die Dienste laufen, haelt den Deploy Key
UEBERTRAGER=kpdeploy        # nimmt die Secrets von den Actions an, nichts sonst
CRED=/etc/credstore.encrypted
# Veroeffentlicht von GitHub, docs.github.com -> "GitHub's SSH key
# fingerprints". Stimmt die Gegenprobe nicht, ist etwas zwischen uns und
# GitHub - dann nicht weitermachen.
GITHUB_ED25519="SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU"

meldung() { printf '\n== %s\n' "$*"; }
hinweis() { printf '   %s\n' "$*"; }

root_sein() {
  [ "$(id -u)" = "0" ] || { echo "setup.sh braucht sudo" >&2; exit 1; }
}

hier() { CDPATH='' cd -- "$(dirname -- "$0")" && pwd; }

# ---------------------------------------------------------------- grundlage
grundlage() {
  root_sein

  meldung "Pakete"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  # Mehr braucht c2 nicht: entity_x_alert.py und takt.sh kommen mit der
  # Standardbibliothek und curl aus, nichts wird nachinstalliert.
  apt-get install -y -qq git curl python3 ca-certificates openssh-client
  hinweis "python3 $(python3 -V 2>&1 | cut -d' ' -f2), git $(git --version | cut -d' ' -f3)"

  meldung "Nutzer"
  if id "$DIENSTNUTZER" >/dev/null 2>&1; then
    hinweis "$DIENSTNUTZER gibt es schon"
  else
    useradd --system --create-home --shell /bin/bash "$DIENSTNUTZER"
    hinweis "$DIENSTNUTZER angelegt, kein Passwort, kein Fernzugang"
  fi
  if id "$UEBERTRAGER" >/dev/null 2>&1; then
    hinweis "$UEBERTRAGER gibt es schon"
  else
    # /bin/sh, weil der erzwungene Befehl in authorized_keys eine Shell
    # braucht. Ein Terminal bekommt dieser Nutzer trotzdem nie, dafuer
    # sorgt restrict in der authorized_keys.
    useradd --system --create-home --shell /bin/sh "$UEBERTRAGER"
    hinweis "$UEBERTRAGER angelegt, nimmt nur Credentials an"
  fi
  passwd -l "$DIENSTNUTZER" >/dev/null 2>&1 || true
  passwd -l "$UEBERTRAGER" >/dev/null 2>&1 || true

  meldung "Ordner"
  install -d -o root -g root -m 0700 "$CRED"
  install -d -o "$DIENSTNUTZER" -g "$DIENSTNUTZER" -m 0755 /var/lib/kaspa-pulse
  hinweis "$CRED (700, root) und /var/lib/kaspa-pulse ($DIENSTNUTZER)"

  meldung "Schreibhilfen fuer die Credentials"
  QUELLE="$(hier)/credstore"
  install -o root -g root -m 0755 "$QUELLE/kp-credstore-put" /usr/local/sbin/kp-credstore-put
  install -o root -g root -m 0755 "$QUELLE/kp-credstore-ssh" /usr/local/sbin/kp-credstore-ssh
  TMP="$(mktemp)"
  {
    echo "# Kaspa Pulse: der Uebertrager darf genau zwei Befehle als root,"
    echo "# beide zeigen keinen Wert. Angelegt von deploy/c2/setup.sh."
    echo "$UEBERTRAGER ALL=(root) NOPASSWD: /usr/local/sbin/kp-credstore-put, /usr/bin/ls -l --time-style=long-iso $CRED"
  } > "$TMP"
  chmod 0440 "$TMP"
  visudo -c -f "$TMP" >/dev/null
  install -o root -g root -m 0440 "$TMP" /etc/sudoers.d/kaspa-pulse-credstore
  rm -f "$TMP"
  visudo -c >/dev/null
  hinweis "/etc/sudoers.d/kaspa-pulse-credstore geprueft"

  meldung "github.com als bekannter Host"
  SSHDIR="$(getent passwd "$DIENSTNUTZER" | cut -d: -f6)/.ssh"
  install -d -o "$DIENSTNUTZER" -g "$DIENSTNUTZER" -m 0700 "$SSHDIR"
  ssh-keyscan -t ed25519 github.com > "$SSHDIR/known_hosts.neu" 2>/dev/null
  FP="$(ssh-keygen -lf "$SSHDIR/known_hosts.neu" | awk '{print $2}')"
  if [ "$FP" != "$GITHUB_ED25519" ]; then
    rm -f "$SSHDIR/known_hosts.neu"
    echo "ABBRUCH: github.com zeigt $FP, erwartet $GITHUB_ED25519." >&2
    echo "Vergleichen mit docs.github.com, 'GitHub's SSH key fingerprints'." >&2
    exit 1
  fi
  mv "$SSHDIR/known_hosts.neu" "$SSHDIR/known_hosts"
  chown "$DIENSTNUTZER:$DIENSTNUTZER" "$SSHDIR/known_hosts"
  chmod 0600 "$SSHDIR/known_hosts"
  hinweis "Fingerabdruck stimmt: $FP"

  meldung "Deploy Key"
  if [ -f "$SSHDIR/id_ed25519" ]; then
    hinweis "gibt es schon, bleibt wie er ist"
  else
    sudo -u "$DIENSTNUTZER" ssh-keygen -q -t ed25519 -N "" \
      -C "c2 deploy key kaspa-pulse" -f "$SSHDIR/id_ed25519"
    hinweis "neu erzeugt, der private Teil verlaesst diesen Rechner nicht"
  fi
  echo
  echo "Diesen oeffentlichen Teil auf GitHub eintragen:"
  echo "  Settings -> Deploy keys -> Add deploy key, 'Allow write access' AN"
  echo
  cat "$SSHDIR/id_ed25519.pub"
  echo
  hinweis "Danach: sudo ./setup.sh klonen"
}

# ------------------------------------------------------------------- klonen
klonen() {
  root_sein
  if [ -d "$ZIEL/.git" ]; then
    meldung "Repo steht schon, hole den neuesten Stand"
    sudo -u "$DIENSTNUTZER" git -C "$ZIEL" pull --ff-only
  else
    meldung "Gegenprobe: erreicht der Deploy Key das Repo?"
    # GitHub antwortet auf ssh -T immer mit Code 1, der Text zaehlt.
    AUS="$(sudo -u "$DIENSTNUTZER" ssh -o BatchMode=yes -T git@github.com 2>&1 || true)"
    case "$AUS" in
      *"successfully authenticated"*) hinweis "$AUS" ;;
      *) echo "ABBRUCH: $AUS" >&2
         echo "Der Deploy Key ist noch nicht eingetragen, oder ohne Schreibrecht." >&2
         exit 1 ;;
    esac
    meldung "Klonen nach $ZIEL"
    install -d -o "$DIENSTNUTZER" -g "$DIENSTNUTZER" -m 0755 "$ZIEL"
    sudo -u "$DIENSTNUTZER" git clone --quiet "$REPO_SSH" "$ZIEL"
  fi
  chown -R "$DIENSTNUTZER:$DIENSTNUTZER" "$ZIEL"
  hinweis "Stand: $(sudo -u "$DIENSTNUTZER" git -C "$ZIEL" log --oneline -1)"
}

# ------------------------------------------------------------------- runner
runner() {
  root_sein
  DATEI="${1:?Datei mit dem oeffentlichen Actions-Schluessel fehlt}"
  [ -f "$DATEI" ] || { echo "$DATEI gibt es nicht" >&2; exit 1; }
  ssh-keygen -lf "$DATEI" >/dev/null || { echo "$DATEI ist kein Schluessel" >&2; exit 1; }
  case "$(cat "$DATEI")" in
    *PRIVATE*) echo "ABBRUCH: das ist der PRIVATE Teil. Nur .pub eintragen." >&2; exit 1 ;;
  esac
  SSHDIR="$(getent passwd "$UEBERTRAGER" | cut -d: -f6)/.ssh"
  install -d -o "$UEBERTRAGER" -g "$UEBERTRAGER" -m 0700 "$SSHDIR"
  [ "$(wc -l < "$DATEI")" -le 1 ] || { echo "ABBRUCH: $DATEI hat mehr als eine Zeile" >&2; exit 1; }
  # restrict: kein Terminal, kein Forwarding, kein Agent. command: nur
  # kp-credstore-ssh, also put und liste - nie eine Shell.
  #
  # Uebernommen werden NUR Art und Schluessel ($1 und $2), der Kommentar
  # wird selbst gesetzt. Sonst koennte ein Kommentar mit Zeilenumbruch
  # eine zweite, unbeschraenkte Zeile einschmuggeln.
  printf 'restrict,command="/usr/local/sbin/kp-credstore-ssh" %s %s github-actions-server-secrets\n' \
    "$(awk 'NR==1{print $1}' "$DATEI")" "$(awk 'NR==1{print $2}' "$DATEI")" \
    > "$SSHDIR/authorized_keys"
  chown "$UEBERTRAGER:$UEBERTRAGER" "$SSHDIR/authorized_keys"
  chmod 0600 "$SSHDIR/authorized_keys"
  meldung "Actions-Schluessel eingetragen"
  hinweis "$(ssh-keygen -lf "$DATEI")"
  hinweis "Dieser Schluessel kann nur 'put <name>' und 'liste', keine Shell."
}

# ------------------------------------------------------------------ hostkey
hostkey() {
  root_sein
  IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')"
  [ -n "$IP" ] || IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [ -n "$IP" ] || { echo "IPv4 nicht gefunden, bitte von Hand einsetzen" >&2; exit 1; }
  meldung "Diese eine Zeile ist der Wert fuer das Secret SERVER_HOST_KEY"
  hinweis "Sie enthaelt die IP. Nur ins Secret einsetzen, nicht in einen Chat."
  echo
  awk -v ip="$IP" '{print ip, $1, $2}' /etc/ssh/ssh_host_ed25519_key.pub
  echo
  hinweis "Fingerabdruck zum Vergleich mit dem Mac:"
  hinweis "$(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub)"
}

# ------------------------------------------------------------------ haerten
haerten() {
  root_sein
  install -d -m 0755 /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/10-kaspa-pulse.conf <<'KONF'
# Kaspa Pulse c2. Nur Schluessel, kein Passwort, kein root-Login.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
X11Forwarding no
AllowAgentForwarding no
MaxAuthTries 3
KONF
  chmod 0644 /etc/ssh/sshd_config.d/10-kaspa-pulse.conf
  sshd -t
  meldung "sshd-Einstellung geprueft, lade neu"
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
  hinweis "Die offene Sitzung bleibt. Vor dem Abmelden eine zweite Sitzung oeffnen."
}

# -------------------------------------------------------------------- units
units() {
  root_sein
  FEHLT=""
  for n in discord_webhook telegram_bot_token telegram_chat_id gh_dispatch_token; do
    [ -s "$CRED/$n" ] || FEHLT="$FEHLT $n"
  done
  if [ -n "$FEHLT" ]; then
    echo "ABBRUCH: diese Credentials fehlen noch:$FEHLT" >&2
    echo "discord_webhook, telegram_* kommen mit server-secrets.yml," >&2
    echo "gh_dispatch_token von Hand, siehe deploy/c2/taktgeber/README.md." >&2
    exit 1
  fi
  A="$ZIEL/deploy/c2/entity-x-alarm"
  T="$ZIEL/deploy/c2/taktgeber"
  meldung "Units verlinken"
  systemctl link "$A/entity-x-alarm.service" "$A/entity-x-sync.service" "$A/entity-x-sync.timer"
  systemctl link "$T/takt@.service"
  for t in tagesgrafik instagram-bild reel weeklynumbers number-of-day; do
    systemctl link "$T/takt-$t.timer"
  done
  systemctl daemon-reload
  meldung "Starten"
  systemctl enable --now entity-x-alarm.service entity-x-sync.timer
  systemctl enable --now takt-tagesgrafik.timer takt-instagram-bild.timer \
    takt-reel.timer takt-weeklynumbers.timer takt-number-of-day.timer
  hinweis "journalctl -u entity-x-alarm -f  zeigt jede Minute eine Zeile"
}

# ------------------------------------------------------------------ pruefen
pruefen() {
  root_sein
  meldung "Credentials, nur Namen und Groessen"
  ls -l --time-style=long-iso "$CRED" || true
  for n in discord_webhook telegram_bot_token telegram_chat_id gh_dispatch_token; do
    if [ -s "$CRED/$n" ]; then
      L="$(systemd-creds decrypt --name="$n" "$CRED/$n" - 2>/dev/null | wc -c || echo "?")"
      printf '   %-20s lesbar, %s zeichen\n' "$n" "$L"
    else
      printf '   %-20s FEHLT\n' "$n"
    fi
  done
  meldung "Dienste"
  systemctl is-active entity-x-alarm.service entity-x-sync.timer || true
  meldung "Naechste Takte, Ortszeit"
  systemctl list-timers 'takt-*' 'entity-x-*' --no-pager || true
  meldung "Repo"
  sudo -u "$DIENSTNUTZER" git -C "$ZIEL" log --oneline -1 2>/dev/null || echo "   kein Repo"
  meldung "Abdeckung heute und gestern"
  sudo -u "$DIENSTNUTZER" env ABDECKUNG_FILE=/var/lib/kaspa-pulse/entity-x-abdeckung.json \
    python3 "$ZIEL/scripts/entity_x_alert.py" --abdeckung 2>/dev/null || echo "   noch keine"
}

BEFEHL="${1:-}"
# shift ist ein special builtin: ohne Argumente beendet es die Shell
# sofort, auch mit "|| true". Darum die Abfrage.
if [ $# -gt 0 ]; then shift; fi
case "$BEFEHL" in
  grundlage) grundlage ;;
  klonen)    klonen ;;
  runner)    runner "${1:-}" ;;
  hostkey)   hostkey ;;
  haerten)   haerten ;;
  units)     units ;;
  pruefen)   pruefen ;;
  *) sed -n '2,20p' "$0"; exit 1 ;;
esac
