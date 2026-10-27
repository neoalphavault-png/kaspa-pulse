# Bericht-Versand in den Ops-Kanal, nur einmal je Inhalt

Bericht für Ben zum Auftrag vom 26.10.2026. Branch `fix/bericht-discord-einmal`, PR [#156](https://github.com/neoalphavault-png/kaspa-pulse/pull/156).

## Anlass

Der Rat an STP kam am 26.10. zweimal in #moderator-only. Der Branch `bericht/weekly-verteilung-2026-10-30` baute auf dem STP-Branch auf statt auf main. Der Workflow verglich bei einem neuen Branch mit dem Stand davor und schickte den STP-Abschnitt erneut.

## Was gemacht wurde

1. **Rebase:** `bericht/weekly-verteilung-2026-10-30` liegt jetzt auf main (d899ea8). Im Diff steht nur noch `berichte/2026-10-30-weekly-verteilung.md`. Gepusht mit `--force-with-lease`, nur auf meinem eigenen Branch.
2. **Nur Berichte dieses Pushes:** Der Workflow liest jetzt das Push-Ereignis. Es zählen nur Berichte, die in Commits dieses Pushes hinzukamen oder geändert wurden, und nur Commits, die mit diesem Push zum ersten Mal ins Repo kamen. Berichte aus einem Eltern-Branch fallen damit heraus.
3. **Prüfsumme merken:** Je Bericht wird die sha256-Prüfsumme des Discord-Abschnitts in `gesendet.json` auf dem Branch `ops/bericht-gesendet` gemerkt. Derselbe Abschnitt desselben Berichts geht nie ein zweites Mal raus. Das gilt auch nach Rebase oder Force-Push und auf jedem anderen Branch, also strenger als "je Branch". Gemerkt wird erst nach erfolgreichem Versand. Alle Läufe stehen in einer Warteschlange, damit zwei Läufe nicht gleichzeitig schreiben.
4. **Kopfzeile:** Die Zahl in "Bitte die folgenden N Nachrichten" wird aus der fertigen Liste der folgenden Nachrichten gezählt, bei einer Nachricht heißt es "die folgende Nachricht". Die 7 vom 26.10. war schon gezählt und stimmte, beide Berichte hatten 7 Teile nach der Kopfzeile. Neu ist, dass ein Selbsttest die Zahl gegen die wirklich folgenden Nachrichten prüft.
5. **Merkdatei vorbelegt:** `ops/bericht-gesendet` trägt schon die drei Abschnitte, die am 26.10. rausgingen: STP-Rat (zweimal, von beiden Branches) und Weekly-Verteilung. Die Uhrzeit steht dort nicht, ich habe sie nicht gemerkt. In der Datei stehen nur Branch, Pfad, Prüfsumme und Datum.

## Nachtrag 27.10., vor dem Merge

Bens Vorgaben vom 27.10. sind umgesetzt. Neuer Kopf des Codes: Commit eb9e453 auf `fix/bericht-discord-einmal`. Danach folgt nur noch dieser Bericht.

- **Rebase:** Der Branch liegt auf main 641fcdc und enthält den Fix von gestern aus #157: `kaspapulse.com` ist erlaubt, Unterdomains bleiben gesperrt. Der Rebase lief ohne Konflikt.
- **Job `senden`:** `contents: read`, der Webhook steht nur im Sendeschritt. Hat der Lauf etwas gesendet, geht die Merkdatei als Artefakt `bericht-gesendet-<lauf>` weiter, 3 Tage aufbewahrt.
- **Job `merken`:** `contents: write`, ohne Secret. Er läuft nur, wenn der Sendejob neue Einträge gemeldet hat. Er prüft die Merkdatei mit `--merk-pruefen`: erlaubt sind nur Branch, Pfad unter `berichte/`, sha256, Zeit und ein kurzer Hinweis. Danach pusht er nur auf `ops/bericht-gesendet`.
- **Abgleich mit main:** Vor dem Versand holt der Sendejob `origin/main`. Weichen `.github/workflows/bericht-discord.yml` oder `scripts/bericht_discord.py` davon ab, bricht er ab und sendet nichts. Ein Branch mit geändertem Sendecode kann also nie senden.

Geprüft:
- Selbsttest grün, darunter neue Fälle für ungültige Merkdateien: fremde Felder, Pfad außerhalb `berichte/`, falsche Prüfsumme, IP im Hinweis.
- `--merk-pruefen` auf die echte Merkdatei von `ops/bericht-gesendet`: gültig.
- Lokal gegen ein Test-Repo ausprobiert:
  - Bei gleichem Stand wie main läuft der Versand weiter.
  - Bei abweichendem Skript bricht der Sendejob ab.
  - Der Job `merken` legt die Merkdatei zweimal hintereinander richtig ab.
  - Eine Merkdatei mit einem Pfad unter `scripts/` lehnt er ab.
- Secret-Scan des Diffs ohne Fund.

Ein Push läuft immer mit der Workflow-Datei aus seinem eigenen Commit. Bis zum Merge würde der neue Workflow deshalb nur auf einem `bericht/`-Branch abbrechen, der schon auf diesem Stand aufbaut, weil main noch den alten Code trägt. Branches auf main laufen bis dahin mit dem alten Workflow. Nach dem Merge sind beide gleich.

## Eigener Fehler beim Rebase

Der Force-Push hat den Weekly-Bericht noch einmal nach #moderator-only geschickt, am 26.10. um 19:36 UTC, 8 Nachrichten ([Lauf 40388259035](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40388259035)). Vorher hatte ich den Workflow von main durchgespielt, aber in meiner lokalen Kopie. Dort gab es den alten Stand des Branches noch. Im Runner war er nach dem Force-Push nicht mehr erreichbar. Deshalb nahm der alte Workflow den Weg für einen neuen Branch, verglich mit dem letzten Commit und sendete ohne Vergleich mit dem alten Stand. Mit diesem PR wäre das nicht passiert: Der Abschnitt steht mit seiner Prüfsumme in der Merkdatei, ein Rebase sendet ihn nicht erneut. Bis zum Merge pushe ich nichts mehr auf `bericht/`-Branches.

## Prüfung

- Selbsttest grün: Kopfzahl bei 1, 3 und 7 Teilen, nur neue Commits, gleicher Inhalt nie zweimal, auch auf anderem Branch, neuer Inhalt einmal, fehlgeschlagener Versand wird nicht gemerkt.
- Sicherungsschritt gegen ein lokales Test-Repo: Merkdatei anlegen und fortschreiben, beides gelungen.
- Durchgespielt mit dem echten Ereignis eines Rebase-Pushes und der vorbelegten Merkdatei: Weekly-Bericht "schon gesendet, nichts gesendet".
- Ein Push auf `ops/bericht-gesendet` startet nur den Secret-Scan.

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

- Den PR prüfen lassen und mergen. Er ändert `.github/workflows/bericht-discord.yml`, deshalb kein Selbst-Merge. Der Workflow braucht jetzt `contents: write`, nur um die Merkdatei auf `ops/bericht-gesendet` zu schreiben.
- `ops/bericht-gesendet` nie löschen und nie nach main mergen. Ohne die Datei würde ein neuer Push mit einem schon gesendeten Abschnitt wieder senden.
