# KCC-20 Tageslauf, Ausfall am 11.11. und Nachholung

Bericht für Ben zum Auftrag vom 12.11. Die öffentliche Wochenzahl ist am Di 17.11. um 14:00 fällig. Bis dahin soll der Tageslauf wieder täglich in `claude/ablage-kcc20` ankommen. Nur Summen, keine Adressen.

## Grund in einem Satz

Der Planlauf vom 11.11. ([Lauf 43087815921](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43087815921)) hat vollständig gezählt, aber der Upload des Ergebnisses scheiterte, weil GitHubs Artefakt-Dienst fünfmal hintereinander eine HTML-Fehlerseite statt einer Antwort lieferte, und deshalb fand der Ablage-Job nichts zum Ablegen.

## Was sonst auffällt

- **7.11. fehlt auch:** Der Planlauf vom 7.11. ([Lauf 42397644495](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42397644495)) brach ab, weil der Knoten in 290 Minuten nicht synchron wurde. Am 11.11. brauchte er dafür 34 Minuten.
- **Der Plan startet spät:** Angesetzt ist 12:05 UTC. Die Läufe vom 7. bis 12.11. starteten aber zwischen 17:42 und 22:14 UTC. Startet ein Lauf erst nach Mitternacht UTC, nimmt der Workflow bisher den neuen Tag als Stichzeit. Er wartet dann auf eine Stichzeit in der Zukunft und scheitert.
- **Ablage seit dem 6.11.:** 6.11., 8.11., 9.11., 10.11. und 12.11. sind da. Der 11.11. ist nachgeholt (unten), der 7.11. fehlt weiter.

## Nachholung des 11.11.

- **Lauf:** [Lauf 43314446329](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43314446329), gestartet am 12.11. um 21:52 UTC.
- **Parameter:** Stichzeit 11.11. 12:00 UTC und Vergleich ab 10.11. 12:00 UTC. Als Vorläufe dienen die drei Saatläufe und die Ablageläufe bis zum 10.11., wie es der Plan täte.
- **Weg:** über `kcc20/start.txt` auf `fix/kcc20-zaehlung`. Vorher habe ich main in den Branch gemergt, damit der Lauf denselben Workflow wie der Plan nutzt.
- **Grenze:** Die Stichzeit lag beim Start 33.9 h zurück. Der Lauf konnte nur zählen, weil der Pruning-Punkt noch davor lag.

## Ergebnis der Nachholung

- **Angekommen:** Lauf 43314446329 ist grün und liegt in `claude/ablage-kcc20` unter `kcc20/laeufe/2026-11-11-43314446329`, abgelegt am 12.11. um 23:07 UTC. Der Pruning-Punkt des Knotens lag bei 11.11. 07:39:27 UTC, also noch vor der Stichzeit.
- **Summen zur Stichzeit 11.11. 12:00 UTC (counted):**
  - 425 Tokens mit lebenden Outputs.
  - 6,140 Halter-Outputs und 1,861 eindeutige Halter.
  - 13,697 Transfers seit 21.10. Davon sind 35 counted, die übrigen 13,662 stammen aus der Zeit vor unserem eigenen Fenster.
- **Bestand:** Zwischen dem 10.11. und dem 12.11. passt der Nachholauf in die Reihe. Am 10.11. waren es 422 Tokens und 1,829 Halter, am 12.11. 429 Tokens und 1,896 Halter.

## Was der Ausfall kostet

Der Bestand je Stichzeit wird in jedem Lauf neu bewiesen, er ist nicht betroffen. Betroffen ist die lückenlose eigene Kette der Transfers. Der Lauf vom 10.11. las die Tx bis 10.11. 20:19:44 UTC, der Nachholauf und der Lauf vom 12.11. lesen erst ab 11.11. 07:39:27 UTC. Die 11 h 20 min dazwischen hätte nur der verlorene Upload vom 11.11. gehabt, und kein Knoten hat sie noch. Unser counted Fenster für Transfers beginnt deshalb neu am 11.11. um 07:39:27 UTC. Am 10.11. begann es noch am 7.11. um 07:27:47 UTC. Transfers vor dem 11.11. 07:39 UTC stehen ab jetzt nur noch als Zahl von api.kaspa.org, also source api.kaspa.org, nicht counted. Für die Wochenzahl am 17.11. heißt das: Bei den Transfers ist nur das Fenster ab 11.11. 07:39 UTC counted.

## Änderung am Workflow, als PR für Ben

`kcc20-zaehlung.yml`, zwei kleine Änderungen.

1. **Zweiter Upload-Versuch:** Scheitert der Upload, folgt nach 5 Minuten ein zweiter Versuch mit denselben Dateien. Erst wenn auch der scheitert, ist der Lauf rot.
2. **Tag der Stichzeit:** Der Tag ist der des letzten 12:05 UTC, also `date -u -d '-12 hours -5 minutes'`. Ein Start am 13.11. um 02:00 UTC zählt damit noch zum 12.11.

Keine Änderung an Zählung, Ablage oder Rechten. Gegen den 7.11. hilft beides nicht, ein Knoten, der nicht synchron wird, bleibt ein Ausfall.

## Was Ben tun muss

- Den PR prüfen und mergen. Die Änderung greift ab dem nächsten Planlauf.
