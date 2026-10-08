# TN10-Zähler, intern

Nur auf diesem Branch. Nicht nach main. Die Methode bleibt intern, nach außen gehen nur Ergebnisse, Quelle und Grenzen.

| Datei | Wirkung |
|---|---|
| `dauer.txt` | Fenster in Sekunden, höchstens 39600 (11 h). Eine Änderung startet einen Lauf. |
| `segment.txt` | Länge eines Teil-Laufs in Sekunden, 600 bis 11400. Standard 10800. Das Fenster darf höchstens drei Segmente lang sein. |
| `start.txt` | Beginn des Fensters in UTC, etwa `2026-10-09T21:25:00Z`. Leer heißt sofort. Bis 4 min vorher schlafen Wartejobs ohne jede Abfrage, höchstens 34 h. Eine Änderung startet einen Lauf. |
| `ids.txt` | Tx-IDs für den Prüfmodus. Eine Änderung startet die Prüfung. |

Ein Lauf hat zwei Spuren. Spur a endet nach einem, zwei und drei Segmenten, Spur b nach einem halben, anderthalb, zweieinhalb und drei. Jede Übergabe der einen Spur liegt mitten in einem Teil der anderen. Der Job `zusammen` baut daraus `tn10-gesamt-minuten.csv`. Je Minute steht dort, aus welchem Teil die Zeile stammt (`quelle`) und wie viele Teile sie voll hatten (`teile_voll`). Doppelt gezählte Minuten stehen verglichen in `tn10-gesamt-abgleich.csv`.

Jeder Teil hält zwei Knoten, k1 und k2. Dass es zwei verschiedene sind, belegt die p2p-Kennung, gespeichert nur als Hash (`k1_id`, `k2_id`). Knotenadressen werden nicht gespeichert, IPs werden maskiert.
