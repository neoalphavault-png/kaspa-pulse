# Bericht-Versand in den Ops-Kanal, nur einmal je Inhalt

Bericht für Ben zum Auftrag vom 26.10.2026. Branch `fix/bericht-discord-einmal`, PR [#156](https://github.com/neoalphavault-png/kaspa-pulse/pull/156).

## Anlass

Der Rat an STP kam am 26.10. zweimal in #moderator-only. Der Branch `bericht/weekly-verteilung-2026-10-30` baute auf dem STP-Branch auf statt auf main. Der Workflow verglich bei einem neuen Branch mit dem Stand davor und schickte den STP-Abschnitt erneut.

## Was gemacht wurde

1. **Rebase:** `bericht/weekly-verteilung-2026-10-30` liegt jetzt auf main (d899ea8). Im Diff steht nur noch `berichte/2026-10-30-weekly-verteilung.md`. Vor dem Force-Push habe ich durchgespielt, was der Workflow auf main dabei tut: kein Abschnitt wäre gesendet worden. Gepusht mit `--force-with-lease`, nur auf meinem eigenen Branch.
2. **Nur Berichte dieses Pushes:** Der Workflow liest jetzt das Push-Ereignis. Es zählen nur Berichte, die in Commits dieses Pushes hinzukamen oder geändert wurden, und nur Commits, die mit diesem Push zum ersten Mal ins Repo kamen. Berichte aus einem Eltern-Branch fallen damit heraus.
3. **Prüfsumme merken:** Je Bericht wird die sha256-Prüfsumme des Discord-Abschnitts in `gesendet.json` auf dem Branch `ops/bericht-gesendet` gemerkt. Derselbe Abschnitt desselben Berichts geht nie ein zweites Mal raus. Das gilt auch nach Rebase oder Force-Push und auf jedem anderen Branch, also strenger als "je Branch". Gemerkt wird erst nach erfolgreichem Versand. Alle Läufe stehen in einer Warteschlange, damit zwei Läufe nicht gleichzeitig schreiben.
4. **Kopfzeile:** Die Zahl in "Bitte die folgenden N Nachrichten" wird aus der fertigen Liste der folgenden Nachrichten gezählt, bei einer Nachricht heißt es "die folgende Nachricht". Die 7 vom 26.10. war schon gezählt und stimmte, beide Berichte hatten 7 Teile nach der Kopfzeile. Neu ist, dass ein Selbsttest die Zahl gegen die wirklich folgenden Nachrichten prüft.
5. **Merkdatei vorbelegt:** `ops/bericht-gesendet` trägt schon die drei Abschnitte, die am 26.10. rausgingen: STP-Rat (zweimal, von beiden Branches) und Weekly-Verteilung. Die Uhrzeit steht dort nicht, ich habe sie nicht gemerkt. In der Datei stehen nur Branch, Pfad, Prüfsumme und Datum.

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
