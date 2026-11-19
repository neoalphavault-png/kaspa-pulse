# Ringversuch: eine Wochenzahl ohne eigenen Knoten nachzählen (Auftrag Ben 19.11.2026, Frist Mo 30.11.)

**Kopf:** Vorschlag, eine Seite, nichts ausgeführt außer dem Nachrechnen der Sollzahl aus unseren Köpfen.

**Zahl:** Zcash Mainnet, Woche Mo 9.11.2026 00:00 bis Mo 16.11.2026 00:00 UTC, Blockabstände nach Kopfzeit (PH-M-001).

**Ergebnis, das herauskommen muss** (aus unseren Köpfen, counted):
- Blöcke mit Kopfzeit in der Woche: 24.200, Höhe 3.553.224 bis 3.577.423
- Abstand = Kopfzeit des Blocks minus Kopfzeit seines Vorgängers, also 24.200 Abstände
- Median 17 s, Mittel 24,99 s, Anteil über 75 s 4,77 %

**Öffentliche Daten, ohne eigenen Knoten** (eine der beiden Quellen genügt):
1. **Header-Client aus `pulsehawk/methods`:** `headers/ph_headers.py`, nur Standardbibliothek, holt Köpfe über das P2P-Protokoll von fremden Knoten und prüft Verkettung und Arbeit. Die Seeds stehen in Zebras Quellcode. Die Checkpoint-Datei kommt aus Zebras Repo.
2. **Ein öffentlicher Block-Explorer**, der zu jeder Höhe Hash und Kopfzeit zeigt. Dann prüft man selbst nur Höhe und Hash gegen die Checkpoints.

**Schritte:**
1. `git clone` von `pulsehawk/methods`, dann `python3 headers/ph_headers.py --selftest`. Er muss mit „all tests passed“ enden.
2. Köpfe holen, mit Seeds und Checkpoint-Datei von Zebra:
   `python3 headers/ph_headers.py --network zcash-mainnet --seed SEED --checkpoints main-checkpoints.txt --from 3553000 --to 3577500 --out heads.csv.gz --meta heads-meta.json`
3. Die Blöcke wählen, deren Kopfzeit in [9.11. 00:00, 16.11. 00:00) UTC liegt. Für jeden den Abstand zum Vorgänger bilden. Median, Mittel und Anteil über 75 s rechnen. Es sind zehn Zeilen Python, kommt bei uns als `tools/week_check.py` dazu, wenn Ben will.
4. Mit dem Ergebnis oben vergleichen. Stimmen Median und Anzahl nicht genau, ist die Kette oder das Fenster verschieden. Dann die Höhen am Rand und die `tip_hash` vergleichen.

**Warum das ein Ringversuch ist:** Zwei voneinander unabhängige Wege kommen an dieselbe Kette, entweder über fremde P2P-Knoten oder über einen Explorer. Weil die Rechenregel feststeht, muss jeder Weg dieselbe Zahl liefern.

## Fragen

1. Soll `tools/week_check.py` (Schritt 3) ins Methoden-Repo, als PR an dich?
