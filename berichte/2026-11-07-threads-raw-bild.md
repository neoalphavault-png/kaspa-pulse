# Bericht 7.11.2026: Threads ohne Pages, Bild über die raw-Adresse des Commits

Auftrag von Ben vom 6.11.2026, Frist Sa 7.11. 15:00. Die Workflow-Datei ist geändert, deshalb merged Ben. Die Probe mit `--hand` folgt am Sa vor 17:10, das Ergebnis kommt als Nachtrag in diesen Bericht.

## Anlass, Lauf threads #21 am 6.11. (42249808757)
- **17:10:** Der Commit `5ac323a` „threads bild [bot]“ war um 17:10:27 Berlin auf main.
- **Danach:** Der Schritt „jpeg auf kaspapulse.com“ wartete die vollen 1500 s. kaspapulse.com lieferte bis 17:35:33 nur 404, weil das Pages-Deploy hing.
- **Folge:** Es gab keinen Container und keinen Post. Die Meldung „threads ist rot, heute kein post“ war richtig.
- **Was dabei funktioniert hat:** Der neue Schritt „log nachholen“ hat den Eintrag vom 5.11. mit dem Text über die Threads-API ergänzt („nachgeholt, 2026-11-05 media 17975335962157821“). „log sichern“ hat ihn im ersten Versuch gepusht (`5d58be5`).

## 1. Threads holt das Bild über die raw-Adresse
- **Adresse:** `https://raw.githubusercontent.com/neoalphavault-png/kaspa-pulse/<commit-sha>/ig/<datei>`. Der SHA ist der Commit, der das JPEG geschrieben hat (`git log -1 -- ig/<datei>`). Der Repo-Name kommt aus `GITHUB_REPOSITORY`.
- **Warum das hilft:** Die Adresse gilt sofort nach dem Push und ändert sich nie. Pages spielt dafür keine Rolle.
- **Neu in `scripts/instagram.py`:** `bild_bereit(pfad, raw, raw_frist, pages_frist)`. Die Funktion wartet zuerst auf die raw-Adresse, höchstens `RAW_FRIST` = 120 s. Danach greift kaspapulse.com als Rückfall. Beide Adressen müssen `image/jpeg` mit genau der Länge der Datei liefern (`url_warten`, wie bisher).
- **Neu in `scripts/threads.py`:** `bild --jpeg ig/<datei>` nutzt `bild_bereit`, mit raw zuerst und Pages als Rückfall mit `BILD_FRIST` = 1500 s. Die Funktion schreibt `bild` und `quelle` (raw oder pages) als Schritt-Ausgaben.
- **threads.yml:**
  - Der Schritt heißt jetzt „jpeg committen, bild bereitstellen“ (`id: b`). Er pusht das JPEG wie bisher und ruft danach `threads.py bild` auf.
  - Der Container nimmt `steps.b.outputs.bild` statt der festen kaspapulse.com-Adresse.
  - `timeout-minutes` bleibt 45, weil der Pages-Rückfall bis zu 1500 s braucht.
- **Geprüft an echten Adressen**, mit dem Bild vom 6.11., Commit `5ac323a`:
  - raw.githubusercontent.com liefert HTTP 200, `content-type: image/jpeg`, `content-length: 131018`. Die Datei hat genau 131018 Bytes.
  - `threads.py bild` liefert die raw-Adresse nach 0.4 s.
  - Ob Threads die Adresse annimmt, zeigt erst die Probe (Punkt 4). Die Threads-API ist aus meiner Umgebung gesperrt.

## 2. Instagram
- **Stand:** Instagram bleibt vorerst bei Pages. `instagram.py posten` nutzt jetzt auch `bild_bereit`, aber mit `raw=IG_RAW` und `IG_RAW = False`. Damit gilt dieselbe Adresse wie bisher, kaspapulse.com mit 600 s. Im Log steht neu das Feld `quelle`.
- **Warum nicht gleich umgestellt:** Ob Meta die raw-Adresse für Instagram annimmt, lässt sich nur mit einem echten Container prüfen. Dafür gibt es den neuen Befehl `instagram.py quelle-probe --bild URL`.
  - Er legt einen Container mit dem Bild an, ohne Caption, und veröffentlicht nie.
  - threads.yml ruft ihn nur im Handlauf auf (`modus=trocken`) und nur, wenn die Quelle raw ist (`continue-on-error`). Der Instagram-Token steht nur in diesem einen Schritt.
- **Wenn die Probe FINISHED zeigt:** Die Umstellung ist eine Zeile in `scripts/instagram.py`, `IG_RAW = True`. Die Workflow-Datei bleibt dabei unberührt. Das Instagram-JPEG wird in `tagesgrafik.yml` schon vor dem Posten gepusht, also hat es einen Commit.

## 3. Selbsttest
- **`threads.py --selbsttest`:** 83 Fälle, 0 falsch. Neu sind:
  - raw-Frist 120 s.
  - Der Workflow holt das Bild mit `threads.py bild`, und der Container nimmt `steps.b.outputs.bild`.
  - Threads nimmt die raw-Adresse des Commits.
  - Rückfall auf kaspapulse.com mit 1500 s, wenn raw nicht bereit ist.
- **`instagram.py --selbsttest`:** 0 Fehler. Neu sind:
  - raw-Adresse des Commits.
  - `bild_commit` nimmt nur einen SHA.
  - raw zuerst, mit 120 s und der Länge der Datei.
  - Ist raw nicht bereit, greift Pages mit eigener Frist.
  - Ohne Commit geht es gleich zu Pages.
  - Instagram ohne `IG_RAW` bleibt bei Pages mit 600 s.
  - Ein absoluter Pfad im Repo wird zu `ig/<datei>`.
  - `IG_RAW` ist bis zur Probe aus.
- **Weitere Selbsttests:** `look_takt.py` und `karussell_post.py` mit 0 Fehlern.

## 4. Probe Sa 7.11. vor 17:10
**Ablauf nach Bens Merge**
- `threads.yml` von main mit `modus=trocken`, also als Handlauf. Er ist nie scharf, es gibt kein Zeitfenster und keine Tagessperre.
- **Threads:** Der Container wird angelegt und bleibt unveröffentlicht. FINISHED heißt, Threads nimmt die raw-Adresse an.
- **Instagram:** `quelle-probe` mit derselben Adresse. FINISHED heißt, Instagram nimmt sie auch an.
- Das Ergebnis kommt als Nachtrag hier herein.

## Am Rand
- Das Karussell (`karussell_post.seiten_ablage`) wartet weiter auf kaspapulse.com. Dasselbe Risiko hat es am 5.11. getroffen. Mit `bild_bereit` ließe es sich genauso umstellen, wenn die Instagram-Probe grün ist.
- Hostnamen im Code sind nur öffentliche Adressen, raw.githubusercontent.com und kaspapulse.com. Es gibt keine Schlüssel, Tokens oder IPs. Secret-Scan ohne Fund.
