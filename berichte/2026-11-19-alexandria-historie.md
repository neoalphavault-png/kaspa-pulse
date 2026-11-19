# Historie von messung/alexandria-anker neu schreiben, Vorschlag (Auftrag Ben 19.11.2026)

**Kopf:** Nur Prüfung und Vorschlag, nichts ausgeführt. Ben entscheidet. In diesem Bericht steht kein Wert.

## Was ich gefunden habe

- **Branch:** `messung/alexandria-anker`, 65 Commits seit der Abzweigung von main (`93c49fb`). Kein PR hat diesen Branch als Kopf.
- **Spitze** (`cc556c8`): Mein Muster für Kaspa-Adressen und für IPv4 findet in keiner Datei unter `messung/alexandria/` etwas.
- **`f7fbf7c`** (2.11. 07:55 UTC, Rohdaten):
  - `roh/20261102T075543Z/k1.json` und `k2.json` enthalten je 2 Kaspa-Adressen. `2666fcd` hat sie später durch Länge und sha256 ersetzt.
  - `archiv/007.bin` (1 Stelle) und `archiv/034.bin` (2 Stellen) enthalten Zeichenfolgen in IPv4-Form. Ob das echte Adressen oder Versionsnummern sind, habe ich nicht geprüft. Beide Dateien fehlen an der Spitze.
- **`9284085`** (2.11. 08:26 UTC, Eingang, `stuecke/s1.json` bis `s6.json`): Meine Muster (Kaspa-Adresse, IPv4, Hostname, lange Hex-Folge) finden darin **nichts**. Wenn du dort etwas gesehen hast, brauche ich die Art des Funds, ohne Wert.

## Vorschlag, Schritte

1. **Sicherung** des alten Stands als Bundle, nur lokal und nicht im Repo:
   `git bundle create alexandria-alt.bundle origin/messung/alexandria-anker`
2. **Neuschreiben** in einem frischen Klon nur dieses Branches, mit `git filter-repo`:
   - k1.json und k2.json in jedem Commit durch die bereinigte Fassung aus `2666fcd` ersetzen (`--blob-callback`, an den beiden Pfaden).
   - `archiv/007.bin` und `archiv/034.bin` aus der Historie entfernen (`--path … --invert-paths`). An der Spitze fehlen sie ohnehin.
   - Gilt nur für `--refs messung/alexandria-anker`. main und andere Branches bleiben unberührt.
3. **Prüfen** vor dem Push:
   - Der Baum an der neuen Spitze ist byte-gleich mit `cc556c8`.
   - `git log -p` über den neuen Branch findet mit denselben Mustern nichts.
   - Die Zahl der Commits bleibt 65.
4. **Push** mit `--force-with-lease` auf `messung/alexandria-anker`. Das ist ein erzwungener Push auf einen Datenbranch, darum Ben.
5. **Nachlauf:**
   - **Alte Commits:** GitHub hält sie über die Commit-Adresse noch eine Weile erreichbar. Endgültig entfernt sie nur der GitHub Support, über eine Anfrage zum Entfernen sensibler Daten mit den beiden Commit-Kennungen.
   - **Logs:** Die Actions-Logs der Läufe vom 2.11., die diese Rohdaten geschrieben haben, auf dieselben Muster prüfen und gegebenenfalls löschen.
   - **Klone:** Wer den Branch lokal hat, etwa c2 oder ein Rechner von Ben, holt ihn neu.

## Fragen

1. Soll ich das so ausführen? Wenn ja: Gilt für die beiden `.bin`-Dateien „entfernen“, oder soll ich vorher prüfen, ob die Stellen wirklich Adressen sind?
2. Was hast du in `9284085` gefunden?
