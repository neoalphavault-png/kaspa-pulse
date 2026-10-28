# STP-Lauf Do 29.10.2026 um eine Stunde verschoben

Bestätigung für Ben zum Auftrag vom 27.10.2026. Frist Mi 28.10. 18:00 Berlin. Alle Zeiten in UTC.

## Was gilt

| | UTC | Berlin |
|---|---|---|
| T0, Start | Do 29.10. 19:00 | 20:00 |
| END | Do 29.10. 20:00 | 21:00 |
| Gezählte Minuten | 19:03 bis 19:14, 19:23 bis 19:34, 19:43 bis 19:59 | 20:03 bis 20:14, 20:23 bis 20:34, 20:43 bis 20:59 |
| Covenant-IDs an Ben | bis 18:55 | bis 19:55 |

Unverändert:
- Familie 0 (KNS) zählt nie.
- `ntp.csv` kommt von desk, mini und box. Die Messpunkte sind wie das Zählfenster um eine Stunde verschoben (Ben, 28.10.): 17:00, 18:55 und 20:01 UTC. Sie stehen ausdrücklich in der Laufdatei (`ntp=17:00,18:55,20:01`).
- Jede MINER-Zeile in `phase.log` markiert ihre Minute.

Neu laut STP, über Ben:
- Die öffentlichen Spuren sind muon und boson. vector kommt nur dazu, wenn er die Prüfung eine Stunde vor START besteht.
- KNS sendet über muon, STP vermerkt das als Abweichung.

Für den Parser ändert keiner der beiden Punkte etwas. Er zählt die Covenant-Familien nur über den Hash der Covenant-ID. Sender und Knoten nimmt er aus `phase.log` und `sec.csv`, egal wie sie heißen.

## Was gemacht wurde

Auf `messung/tn10-zaehler`, Commits 2f5043c und a089a32. Dieser Branch wird nie gemergt.

- **Laufdatei `messung/tn10/lauf-2026-10-29.txt`:** Dort stehen `t0=2026-10-29T19:00:00Z`, `ende=2026-10-29T20:00:00Z` und `gezaehlt=19:03-19:14,19:23-19:34,19:43-19:59`. Der Parser liest sie mit `--lauf`. Schickt STP andere Minuten, gilt seine Liste. Dann ändere ich nur diese eine Zeile und melde mich. Die Zusammenfassung des Parsers vermerkt, ob die Liste vom Plan abweicht.
- **Parser:** Schritte, Pausen und NTP-Punkte rechnet er ab T0. Der Selbsttest prüft die Laufdatei: T0 19:00, END 20:00 und genau die 41 Minuten oben. Er prüft auch, dass eine abweichende Liste von STP gilt und dass eine Minute außerhalb des Fensters abbricht. Die NTP-Zeiten können dort mit `ntp=` stehen, falls STP sie nicht verschiebt. 70 Prüfungen grün.

## Historie bereinigt (28.10.)

Im Selbsttest stand in einem Commit ein echter TN10-Knotenname, aus Teilstrings zusammengesetzt. Ben hat dafür am 28.10. einen Force-Push auf `messung/tn10-zaehler` freigegeben.

- Die beiden Commits 890cd87 und ece9c41 sind zu 3a0e1de zusammengelegt. Darauf liegen neu: d0808f5 (vorher b416861), bb7494f (5430e5b), bdd5ee5 (2f5043c) und 89c312b (a089a32).
- Danach kommt 11ec36b mit den NTP-Zeiten in der Laufdatei. **Neuer Kopf: 11ec36b.**
- Der Code ist bis auf die Laufdatei derselbe wie vorher, der alte Kopf und der neue Zwischenstand 89c312b haben denselben Inhalt.
- `git log -p` über den ganzen Branch habe ich mit einem Prüfer durchsucht, auch nach zusammengesetzten Teilstrings und in den Commit-Nachrichten: kein Fund. Werte wurden dabei nicht ausgegeben.
- Selbsttests grün: Parser mit 71 Prüfungen, Nachzählung, Zähler.
- Secret-Scan des Pushes grün. Der Force-Push hat keinen Zähllauf ausgelöst.
- Die geplanten Pushes gehen auf den Branch, nicht auf einen Commit. Sie setzen also auf 11ec36b auf.

Was bleibt:
- Der alte Commit ist auf keinem Branch mehr. GitHub kann ihn aber über seine Kennung noch eine Weile zeigen, bis er aufgeräumt wird. Ganz sofort entfernen kann ihn nur der GitHub-Support.
- Derselbe Prüfer findet den Namen auch auf `bericht/stp-rat-2026-10-27`, in c099d95 und in dessen Bereinigung efc8d0e. Das ist der bekannte Prüfwert aus PR #151, siehe dort. PR #151 ist als Squash gemergt, auf main steht der Name nicht. Der Branch existiert aber noch, und PR #151 hält die Commits fest.
- Ein Treffer in einem SVG unter `graphics/hintergruende/` auf main ist falsch-positiv: Dort steht das Wort "vector" als SVG-Attribut, kein Knotenname.

## Startzeiten der Zählläufe (UTC)

Einen Cron gibt es für TN10 nicht, weder auf main noch auf dem Messbranch noch in den Takten auf c2. Die Zählläufe starten mit dem Push einer Zeitdatei auf `messung/tn10-zaehler` und schlafen dann ohne Abfrage bis kurz vor ihrer Zeit. Die Pushes habe ich als geplante Aufgaben angelegt:

| Push (UTC) | Datei | Wirkung |
|---|---|---|
| Mi 28.10. 11:00 | `messung/tn10/start.txt` = 2026-10-29T18:30:00Z, `dauer.txt` = 7200 | Live-Zähler auf zwei Knoten von 18:30 bis 20:30 UTC, je 30 Minuten Grundlast vor und nach dem Lauf. Er läuft ab 18:26 an. Früher als Mi 08:26 UTC geht der Push nicht, die Wartejobs schlafen höchstens 34 h. |
| Do 29.10. 18:58 | `messung/tn10/nach/covenant.sha256` (nur Hashes), `messung/tn10/nach/mempool.txt` = 2026-10-29T20:15:00Z | Mempool samt Orphans 15 Minuten nach END, je Familie. Fehlen die IDs, kommt `mempool.txt` spätestens 19:50 ohne Familien. |
| Do 29.10. 20:35 | `messung/tn10/nach/stuecke.txt`, sechs Stücke zu 20 Minuten von 18:30 bis 20:30, mit Kette | Nachzählung je Minute und Covenant-Familie auf zwei Knoten. Daraus und aus STPs Logs rechnet der Parser die Minutentabelle. |

Keine dieser Dateien enthält einen Schlüssel, ein Token, eine IP oder einen Hostnamen. Die Covenant-IDs gehen nur als sha256 in `covenant.sha256`, nie in ein Repo, einen Commit oder ein Log.

## Offene Fragen an Ben

1. **NTP-Messpunkte:** beantwortet am 28.10., 17:00, 18:55 und 20:01 UTC.
2. **STPs Logs nach END:** beantwortet am 28.10., sie kommen über Ben. STPs Repo lese ich nicht, bis Ben es freigibt.
3. **`bericht/stp-rat-2026-10-27`:** Soll ich den gemergten Branch löschen, damit c099d95 nicht mehr in der Branch-Liste steht? Über PR #151 bleibt der Commit trotzdem erreichbar. Ganz weg bekommt ihn nur der GitHub-Support, wenn du das willst.

## Was Ben tun muss

- STPs Covenant-IDs bis Do 18:55 UTC an mich, je Familie eine Zeile `f<n> <id>`.
- Schickt STP andere Zählminuten, gib sie mir. Dann gilt seine Liste.
- Nach END STPs Logs an mich.
- Entscheiden, was mit `bericht/stp-rat-2026-10-27` passiert (Frage 3).

Workflow-Änderungen prüft Claude, Ben merged. Dieser Auftrag ändert keinen Workflow.
