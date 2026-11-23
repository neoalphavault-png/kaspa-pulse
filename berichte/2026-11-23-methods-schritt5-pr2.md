# Methoden-Repo Schritt 5, PR 2: BCH-Tempnet-Auswertung in pulsehawk/methods (23.11.2026)

Plan `berichte/2026-11-12-methods-schritt5.md`, Frist PR 2 Mo 23.11., gesamt Mo 30.11. Die Tempnet-Auswertung liegt als pulsehawk/methods#10 bei dir. Das Ergebnis: Auf denselben Daten wie die Originale gibt sie dieselben Zahlen.

<!-- discord -->
Methoden-Repo Schritt 5, PR 2 liegt bei dir, die BCH-Tempnet-Auswertung in pulsehawk/methods#10. Vier Skripte für Wochenzählung, Hash-Fenster, Stücke von 120 Blöcken und Build-Wechsel. Auf unseren vollen Tempnet-Daten geben sie dieselben Zahlen wie die Originale, die vier Stücke-CSV sind bytegleich. Die Selbsttests laufen offline, dazu ein Beispiel mit 19 sha256, alle gleich. Frist Mo 23.11. ist eingehalten. Bericht berichte/2026-11-23-methods-schritt5-pr2.md
<!-- /discord -->

## Was gemacht wurde

- **`bch_tempnet/weekly.py`** aus `tempnet_auswertung.py`, neue Kennung PH-M-007. Abstände, MTP-Verzug, 10 gegen 1 Block, Nachführung, Mindestschwierigkeit, je Tag. Der Bericht ist jetzt englisch.
- **`bch_tempnet/windows.py`** aus `tempnet_fenster.py`, neue Kennung PH-M-008. Die Stunden aus dem Forenbeitrag und der Difficulty-Abgleich kommen jetzt als Eingabedateien. Im Code steht kein Forenname.
- **`bch_tempnet/chunks.py`** aus `tempnet_stuecke.py` (PH-M-008), mit Zweigregel und Slot-Zählung.
  - Die Ausbreitung zwischen zwei Messpunkten fehlt hier. Sie kommt mit dem Zuhörer in PR 3.
- **`bch_tempnet/build_switch.py`** aus `build_wechsel.py` (nutzt PH-M-004 und PH-M-005).
  - Ohne Standardwert für den alten Build.
  - Überspringt Blöcke ohne erste Sichtung. Das Original bricht auf den heutigen Daten an genau diesen 83 Blöcken ab.
- **`forum_woche3.py`** ist nicht dabei, wie entschieden.
- **Gleiche Zahlen:** Jedes Original und sein Port liefen auf denselben vollen Daten, Köpfe 327.989 bis 371.652 und alle 96 Zuhörer-Läufe.
  - weekly 505 von 505 Zahlen gleich
  - windows 90 von 90 gleich, die 6 Fenster wie im Stand vom 15.11.
  - chunks: vier CSV bytegleich, JSON 31 von 31 gleich
  - build_switch 3.777 von 3.777 gleich
- **Selbsttests offline:** weekly 11, windows 12, chunks 22, build_switch 9 Prüfungen, alle bestanden. Die alten Selbsttests sind ebenfalls bestanden.
- **Beispiel:** `bch_tempnet/example.py` rechnet einen Auszug unserer Daten neu und vergleicht 19 sha256, alle gleich.
  - Wochenzählung: die ersten 1.440 Tempnet-Köpfe.
  - Fenster und Stücke: die Köpfe 354.400 bis 355.599 mit drei Zuhörer-Läufen vom 2. und 3.11.
  - Die Lauf-Meta enthalten nur Start und Ende, keine Peers und keine Software-Kennung.
- **Doku:** METHODS.md bekommt PH-M-007 und PH-M-008. FORMATS.md erklärt die gelesenen Zuhörer-Dateien mit ihren deutschen Feldnamen, README.md und CONTRIBUTING.md nennen die neuen Selbsttests.
- **Prüfungen vor dem Push:**
  - Secret-Scan staged und Baum sauber.
  - Der Datenfilter aus CONTRIBUTING.md ist leer, auch über die gezippten Beispieldateien.
  - Keine internen Namen im neuen Code. Keine Workflow-Datei.

| Datei im Beispiel | sha256 |
|---|---|
| `weekly-heads.csv.gz` | `70681da775ea56c75b7a41819479c51a15c3e0290045d10826f4a0dc713a6001` |
| `heads.csv.gz` | `1363475bf0fde9e89f804145098e7a42a515ae08a79a8df5662861c663b665b7` |
| `listener/zusammenfassung.json` | `9c88afc193aad42c210c0330a060c391a7c6791189197d32cb4b681bea0c8cdc` |
| Ausgabe `weekly.json` | `b0edee52f3b6402742a3beac61316577d71b56a9fdedb8530e4139fd965c1d88` |
| Ausgabe `windows.json` | `4eab2b07eba2385bf9ff076fb7e273886772cac0957cffe129cd442318aed037` |
| Ausgabe `chunks.csv` | `d0f8a1ed6d95cb56be72aec69a95e4a545745631c0357af613274b05dc3e25f7` |
| Ausgabe `chunks-slot-nomin.csv` | `1ac59ad9aa41ddce79c249ae6773b7ef38887f0af1faafbbf182c5aab463808d` |

Die volle Liste steht in `bch_tempnet/examples/SHA256SUMS`.

## Stand PR 3

PR 3 (Zuhörer für Zcash und BCH als ein Programm, mit Auswertung, PH-M-002 und PH-M-004) bleibt für Fr 27.11. geplant. Dazu kommt die Ausbreitung zwischen zwei Messpunkten aus `tempnet_stuecke.py`.

## PR-Nummern

- pulsehawk/methods#10, BCH-Tempnet-Auswertung, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. **Neue Kennungen:** Sind PH-M-007 (Wochenzählung) und PH-M-008 (Hash-Fenster und Stücke) so recht?
2. **Zwei Zählregeln eines Lesers:** METHODS.md nennt die Regeln aus dem Forum nur als „von einem Leser vorgeschlagen“, ohne Namen. Soll er dort namentlich genannt werden, wenn er zustimmt?

## Was Ben tun muss

- pulsehawk/methods#10 prüfen und mergen.
- Die zwei Fragen beantworten.
