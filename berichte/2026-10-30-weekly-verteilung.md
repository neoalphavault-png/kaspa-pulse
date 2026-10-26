# Weekly-Verteilung automatisch

Bericht für Ben zum Auftrag vom 26.10.2026. Frist Fr 30.10. 18:00 Berlin, erster echter Lauf Mo 02.11.2026. Branch `feature/weekly-verteilung`.

## Was gebaut wurde

| Teil | Datei |
|---|---|
| Ablauf, Texte, Sperren, Selbsttest | `scripts/weekly_verteilung.py` |
| Workflow | `.github/workflows/weekly-verteilung.yml` |
| Takt auf c2, Mo 16:00 Europe/Berlin | `deploy/c2/taktgeber/takt-weekly-verteilung.timer`, Eintrag in `ausloesen.sh`, `takt.conf` (`WV_MODUS=scharf`), `setup.sh` (`TAKTE`), `README.md` |
| Merkdatei | `data/weekly-verteilung.json` |
| Liste fremder Gruppen (leer) | `data/weekly-verteilung-gruppen.json` |

### Ablauf am Montag

1. **16:00 Berlin** startet der Takt den Workflow. Die zwei cron-Zeilen im Workflow sind nur Rückfall, GitHubs Zeitplan kommt in diesem Konto oft Stunden zu spät. Ein Lauf nach 18:30 Berlin endet ohne etwas zu tun.
2. **Alle 5 Minuten bis 18:00** liest er den öffentlichen RSS-Feed des Kanals über `scripts/yt_live_check.py` (Kanal-ID dort, kein Schlüssel). Ein Video gilt nur, wenn alles zutrifft:
   - es erschien heute (Berliner Kalendertag),
   - es ist kein Short (Feed-Link ohne `/shorts/`),
   - sein Titel passt zum Titel im Uploadpaket, gleich oder mit gleichem Teil vor dem "|", zum Beispiel "Kaspa Analysis".
3. **Fund plus 5 Minuten:** Discord #weekly-numbers über `DISCORD_WEBHOOK_WEEKLY`.
4. **Fund plus 10 Minuten:** unser Telegram-Kanal über `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID`.
5. **18:00 Berlin:** #moderator-only über `DISCORD_WEBHOOK_OPS`. Die erste Nachricht beginnt mit "📤 VON HAND" und nennt die Regel "höchstens einmal pro Woche und Gruppe, nur wo Teilen erlaubt ist". Danach folgt je Gruppe eine Nachricht zum Kopieren, englisch, die deutsche Gruppe deutsch. Dazu kommt der Status: wann gefunden, was gepostet wurde, was nicht und warum. Fremde Gruppen und fremde Discords bekommen nie etwas automatisch.

Es werden nur vorhandene Secrets genutzt, dazu `STUDIO_READ_TOKEN` zum Lesen des Pakets aus pulse-studio. Kein neues Secret. Die Secrets stehen nur in der Umgebung des einen Schritts, der sendet.

### Texte

- **Quelle:** das Uploadpaket der Sonntagsaufgabe "KASPA WEEKLY vorbereiten", `pulse-studio/kw/<montag>/uploadpaket.md`, Abschnitte "Telegram (englisch, offizieller Kanal)" und "Discord (englisch)" (Abschnitt 6a der Aufgabe). Gelesen wird nur main von pulse-studio.
- **VIDEO_URL** wird der Link der Folge.
- **Wochenseite mit UTM je Kanal:** `kaspa-weekly.html?utm_source=discord|tg&utm_medium=chat&utm_campaign=weekly<nummer>`. Fremde Gruppen tragen `weekly<nummer>-gruppe`, die deutsche Gruppe `weekly<nummer>-gruppe-de`. Quellen und Gattung kommen aus `scripts/utm.py`.
- **Deutsche Gruppe:** ein kurzer deutscher Text ohne eigene Zahlen (Video und Wochenseite), damit keine Zahl beim Übersetzen falsch wird.
- **Textregeln vor jedem Senden:** kein Gedankenstrich, kein Doppelpunkt außer in Uhrzeiten und Links, kein Pfeil, keine Echtzeitwörter (live, now, jetzt und weitere), kein übriger Platzhalter. Ein Verstoß heißt: dieser Kanal wird nicht gepostet, der Grund steht um 18:00 in #moderator-only.

### Sperren

- **Merkdatei** `data/weekly-verteilung.json`: je Woche Video, Discord, Telegram und Moderator mit Zeit. Jeder Post wird sofort nach main geschrieben. Ein zweiter Lauf derselben Woche postet nichts mehr.
- **Veto, zwei Wege:**
  - Variable `WEEKLY_VERTEILUNG_STOPP` (JJJJ-MM-TT oder `immer`), gilt ab dem Start eines Laufs.
  - Datei `data/weekly-verteilung-stopp` auf main mit demselben Inhalt. Sie wird vor jedem einzelnen Post frisch gelesen und stoppt damit auch einen laufenden Lauf.
- **Probe:** Handstart in Actions mit `modus=probe` (Vorbelegung). Alles geht nur nach #moderator-only, ohne Warten und ohne Merkdatei. Bis zum Merge startet auch ein Push von `data/weekly-verteilung-probe.txt` auf diesem Branch eine Probe, nie den scharfen Lauf.

## Prüfung

- **Selbsttest grün.** Er spielt einen ganzen Montag mit falscher Uhr durch:
  - Fund um 16:00, Discord um 16:05, Telegram um 16:10, Moderator um 18:00 mit "📤 VON HAND".
  - Ein zweiter Lauf schickt nichts.
  - Ein Short und ein fremder Titel werden nicht genommen.
  - 16:00 Berlin liegt im Winter auf 15:00 UTC und im Sommer auf 14:00 UTC.
  - Die Textregeln fangen Doppelpunkt, Strich, Echtzeitwort und Platzhalter.
- **Vorschau mit dem echten Paket vom 26.10.** (Weekly 9): Texte regelkonform, UTM richtig, VIDEO_URL ersetzt.
- **Probe im Runner am 26.10.** ([Lauf 40356830393](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40356830393)): pulse-studio gelesen, 6 Nachrichten nach #moderator-only, alle mit HTTP 204. Weekly-Kanal und Telegram wurden nicht angefasst.
- Secret-Scan ohne Fund.

## Offene Fragen an Ben

1. **Paket auf main:** Der Automat liest nur das gemergte Sonntagspaket. Auf main von pulse-studio liegt es bis `kw/2026-10-19`, das Paket vom 26.10. steht noch auf `review/weekly-2026-10-26`. Ist das Paket am Montag um 16:00 nicht gemergt, wird nichts gepostet und #moderator-only sagt es um 18:00. Soll er in dem Fall den Branch `review/weekly-<datum>` lesen? Ich rate ab, denn dann ginge ungeprüfter Text raus.
2. **Preise im Text:** Die Blöcke aus 6a nennen den Wochenschluss und eine Schwelle in USD, zum Beispiel "0.03605 usd". Deine Textregel vom 23.10. sagte "keine Preise" für Entwürfe, die Regel in diesem Auftrag nennt sie nicht. Der Automat übernimmt den Text so, wie die Sonntagsaufgabe ihn baut. Soll er Preise blockieren?
3. **Fremde Gruppen:** `data/weekly-verteilung-gruppen.json` ist leer. Dann kommt eine englische und eine deutsche Fassung ohne Gruppennamen. Mit Namen kommt je Gruppe eine eigene Nachricht. Willst du die Liste füllen (Name, Sprache en oder de, Art telegram oder discord)?

## Was Ben tun muss

Die Schritte stehen unten auch als Nachrichten zum Kopieren.

<!-- discord -->
📤 VON HAND, Weekly-Verteilung einrichten (erster echter Lauf Mo 02.11. 16:00 Berlin)
Bitte in dieser Reihenfolge. Jeder Schritt steht in einer eigenen Nachricht darunter.
<!-- teil -->
1. PR mit dem Branch feature/weekly-verteilung prüfen lassen und mergen.
<!-- teil -->
2. Auf dem Server c2 den neuen Takt einrichten. Diesen Befehl kopieren und ausführen
sudo /opt/kaspa-pulse/deploy/c2/setup.sh nachziehen
Danach muss in der Kontrolle takt-weekly-verteilung.timer stehen.
<!-- teil -->
3. Probe nach dem Merge. GitHub, Actions, weekly verteilung, Run workflow, modus probe, datum leer. In #moderator-only kommen dann die Texte als PROBE, sonst nirgends hin.
<!-- teil -->
4. Am Sonntag das Paket in pulse-studio mergen (review/weekly-<datum>). Ohne gemergtes Paket postet der Montag nichts.
<!-- teil -->
5. Veto, falls nötig. GitHub, Settings, Secrets and variables, Actions, Variables, WEEKLY_VERTEILUNG_STOPP anlegen mit dem Montagsdatum (JJJJ-MM-TT) oder immer. Während eines laufenden Laufs stattdessen die Datei data/weekly-verteilung-stopp auf main mit demselben Inhalt anlegen, sie wird vor jedem Post gelesen.
<!-- teil -->
6. Montag 18:00 in #moderator-only die Nachrichten unter "📤 VON HAND" in die fremden Gruppen kopieren, höchstens einmal pro Woche und Gruppe, nur wo Teilen erlaubt ist.
<!-- /discord -->

Zustellung: Dieser Bericht liegt zusätzlich auf dem Branch `bericht/weekly-verteilung-2026-10-30`. Dort schickt der Bericht-Workflow aus PR #151 den markierten Abschnitt nach #moderator-only.
