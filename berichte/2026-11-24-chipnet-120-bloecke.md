# Chipnet, Dauer von 120 Blöcken in Folge seit der Aktivierung (Auftrag Ben 24.11.2026, Frist Mi 25.11. 08:30 Berlin)

**Kopf:** Kleiner Test ohne neuen Bau und ohne Workflow, gerechnet aus vorhandenen Daten. Nach Kopfzeit dauern 120 Blöcke üblich 2 h 0 min 5 s, gerechnet für ein 60-s-Ziel 1 h 59 min 40 s. Bei 9 von 10 liegen gezählt und gerechnet gleichauf. Bei 99 von 100 ist die gezählte Dauer 12 min 36 s länger als gerechnet. Die Ankunft beim Zuhörer liegt lückenlos vor und gibt im selben Zeitraum dieselben Werte. Bedarf laut Ben: Mathieu Geukens (General Protocols, ParyonUSD), Fenster zum Anfechten künftig 120 Blöcke. Zahlungsbereitschaft unbelegt.

<!-- discord -->
Chipnet seit der Aktivierung, 8.191 gleitende Fenster von 120 Blöcken nach Kopfzeit. Üblich dauern 120 Blöcke 2 h 0 min 5 s, gerechnet 1 h 59 min 40 s. Bei 99 von 100 sind es gezählt 2 h 39 min 32 s, gerechnet 2 h 26 min 57 s. Das längste Fenster dauert 2 h 48 min 27 s, das kürzeste 1 h 5 min 34 s. Im Zeitraum tragen 25,9 % der Blöcke Difficulty 1. Bericht berichte/2026-11-24-chipnet-120-bloecke.md
<!-- /discord -->

## Verfahren

- **Fenster:** Für jeden Block h ab 332.451 die Zeit vom Block h−1 bis zum Block h+119, also 120 Abstände in Folge, gleitend um je einen Block. Ein Fenster zählt nur, wenn sein letzter Block in der Datei liegt.
- **Kopfzeit:** aus `data/bch-chipnet/koepfe.csv.gz`. Die Köpfe hat unser Header-Client über P2P geholt, mit Verkettung, Arbeitsnachweis und BCHN-Checkpoints geprüft und mit einer Gegenprobe abgesichert.
- **Gerechnet:** ideale Kette mit exponentiellen Abständen bei 60 s Mittel, die Summe von 120 Abständen folgt der Erlang-Verteilung mit 120 Stufen.
- **Ankunft:** erste Sichtung jedes Blocks beim Zuhörer (`first_seen_utc`). Ein Fenster zählt nur, wenn alle 121 Blöcke darin gesehen wurden.
- **Werte:** Üblich ist der Median, 9 von 10 das 90. Perzentil, 99 von 100 das 99. Perzentil.

## Zahlen

| Zahl | Wert | Art | Datei | Commit | Stichzeit oder Zeitraum (UTC) |
|---|---|---|---|---|---|
| Fenster nach Kopfzeit | 8.191 | counted | `data/bch-chipnet/koepfe.csv.gz` | `4c1981ff` | 2026-11-15 12:33:16 bis 2026-11-21 06:31:50, Blöcke 332.450 bis 340.760, Abruf 2026-11-21T06:33:45Z |
| 120 Blöcke üblich | 2 h 0 min 5 s | counted | wie oben | `4c1981ff` | wie oben |
| 120 Blöcke, 9 von 10 innerhalb | 2 h 13 min 49 s | counted | wie oben | `4c1981ff` | wie oben |
| 120 Blöcke, 99 von 100 innerhalb | 2 h 39 min 32 s | counted | wie oben | `4c1981ff` | wie oben |
| kürzestes Fenster | 1 h 5 min 34 s, Blöcke 337.227 bis 337.347, ab 2026-11-18 20:50:57, davon 6 mit Difficulty 1 | counted | wie oben | `4c1981ff` | wie oben |
| längstes Fenster | 2 h 48 min 27 s, Blöcke 337.546 bis 337.666, ab 2026-11-19 00:53:56, davon 50 mit Difficulty 1 | counted | wie oben | `4c1981ff` | wie oben |
| Anteil Difficulty 1 im Zeitraum | 25,9 % (2.152 von 8.310 Blöcken) | counted | wie oben | `4c1981ff` | wie oben |
| 120 Blöcke üblich, 60-s-Ziel | 1 h 59 min 40 s | computed | Erlang, 120 Stufen, Mittel 60 s | - | - |
| 120 Blöcke, 9 von 10, 60-s-Ziel | 2 h 14 min 14 s | computed | wie oben | - | - |
| 120 Blöcke, 99 von 100, 60-s-Ziel | 2 h 26 min 57 s | computed | wie oben | - | - |
| Ankunft, lückenlose Fenster | 9.184 | counted | `data/bch-chipnet/lauscher/bloecke.csv` | `15e8b0ac` | 2026-11-17 19:46:11 bis 2026-11-24 12:59:27, Blöcke 335.748 bis 345.234, 30 Läufe ohne Lücke, 2 Höhen ohne Sichtung |
| Ankunft, 120 Blöcke üblich / 9 von 10 / 99 von 100 | 2 h 0 min 41 s / 2 h 25 min 23 s / 3 h 34 min 16 s | counted | wie oben | `15e8b0ac` | wie oben |
| Ankunft, kürzestes / längstes Fenster | 15 min 31 s (ab 2026-11-21 20:00:23) / 5 h 39 min 22 s (ab 2026-11-24 07:19:16) | counted | wie oben | `15e8b0ac` | wie oben |
| Ankunft im Zeitraum der Köpfe, 4.893 Fenster, üblich / 9 von 10 / 99 von 100 | 1 h 58 min 54 s / 2 h 18 min 53 s / 2 h 43 min 38 s (Kopfzeit derselben Fenster 1 h 58 min 50 s / 2 h 18 min 20 s / 2 h 43 min 41 s) | counted | `bloecke.csv` und `koepfe.csv.gz` | `15e8b0ac`, `4c1981ff` | 2026-11-17 19:46:11 bis 2026-11-21 06:31:50 |

## Einordnung

- **Üblich:** Gezählt und gerechnet liegen 25 s auseinander. Bei 9 von 10 liegt die gezählte Dauer 25 s unter dem gerechneten Wert.
- **Lange Fenster:** Bei 99 von 100 dauert es gezählt 12 min 36 s länger als gerechnet. Das längste Fenster trägt 50 Blöcke mit Difficulty 1, also viele lange Pausen.
- **Difficulty 1 und die Fenster:** Difficulty 1 ist eine Testnet-Regel, die nach einer langen Pause einen Block durchlässt. Sie gilt auf dem Mainnet nicht. Die Fenster auf Chipnet sind daher kein Maß für das Mainnet.
- **Ankunft gegen Kopfzeit:** Im selben Zeitraum stimmen beide auf wenige Sekunden überein, denn die Kopfzeit verzerrt hier nichts.
- **Die Zeit nach dem Abruf der Köpfe:** Die breiteren Werte der Ankunft kommen aus den Tagen 21. bis 24.11. Nach der Stichzeit der Köpfe gab es eine sehr schnelle Folge (120 Blöcke in 15 min 31 s am 21.11. ab 20:00 UTC) und eine sehr langsame (5 h 39 min 22 s am 24.11. ab 07:19 UTC). Der größte Einzelabstand dort war 688 s, es ist also keine Lücke des Zuhörers. Für diese Tage liegen keine geprüften Köpfe vor und damit auch kein Anteil Difficulty 1.

## Bestätigung #348

Der Zeitraum der 27.314 Mainnet-Abstände ist richtig, 15.5.2026 12:55:32 bis 22.11.2026 09:49:02 UTC. Der erste Abstand beginnt mit der Kopfzeit von Block 951.146 und endet bei 951.147. Der letzte endet bei Block 978.460. Datei `data/bch-mainnet/koepfe.csv.gz` auf `messung/bch-mainnet-probe`, Commit `b7be3b44`.

## PR-Nummern

- dieser Bericht

## Offene Fragen an Ben

1. Sollen die Chipnet-Köpfe vor Freitag bis zum 24.11. aufgefrischt werden? Das ginge über den vorhandenen Ablauf (Anstoß auf dem Datenbranch), ohne neuen Bau. Dann hätten auch die schnelle und die langsame Folge geprüfte Kopfzeiten und einen Anteil Difficulty 1.

## Was Ben tun muss

- Frage 1 beantworten.
- Am Fr 27.11. am Entwurf entscheiden, ob die 120 Blöcke im Wochenbericht 2 die 12 ersetzen.
