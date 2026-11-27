# Zuhörer, Start des Folgelaufs bei API-Fehler wiederholen (Entscheidung Ben 27.11.2026, Frage 2 aus #359)

**Kopf:** Zwei PRs an Ben, je nur eine Workflow-Datei. #360 für den Chipnet-Zuhörer, #361 für die Zcash-Kette. Die Stelle bei Zcash ist anders gebaut und darum ein eigener PR. Die neue Funktion ist in beiden wortgleich. Getestet offline mit einem Ersatz für gh, Secret-Scan ohne Fund. Miner je Fenster ruht bis So 29.11., dort ist nichts gebaut.

<!-- discord -->
Zwei PRs bei Ben, je nur eine Workflow-Datei. Der Chipnet-Zuhörer (#360) und die Zcash-Kette (#361) wiederholen den Start des Folgelaufs bei Fehler 5xx oder Zeitüberschreitung bis zu fünfmal und enden sonst rot, nachdem die Daten des Laufs gesichert sind. Getestet offline in 14 Fällen, keine Adresse im Log. Bericht berichte/2026-11-27-folgelauf-wiederholen.md
<!-- /discord -->

## Was gemacht wurde

- **Funktion `api()` im Schritt „zuhoeren und naechsten lauf starten“**
  - Sie führt einen gh-Aufruf mit `timeout 30` aus.
  - Bei HTTP 5xx oder Zeitüberschreitung wiederholt sie bis zu fünfmal, mit 15, 30, 60 und 120 s Abstand. Im schlimmsten Fall sind das 375 s, weniger als die 8 min vor Laufende.
  - Bei 4xx und anderen Fehlern wiederholt sie nicht.
- **Log:** Je Versuch eine Zeile, zum Beispiel `naechster lauf: start auf main, versuch 2 von 5, HTTP 503`. Die Ausgabe von gh kommt nicht ins Log, weil sie die URL der API enthält. Kein Token im Log.
- **Scheitern:** Scheitern alle Versuche, schreibt der Schritt eine Marke. Der laufende Lauf wird trotzdem zu Ende gehört, Rohdaten und Auswertung werden committet.
- **Rotes Ende:** Der neue letzte Schritt „naechster lauf gestartet“ (`if: always()`) endet dann rot mit dem Satz „Der naechste Lauf liess sich nicht starten, auch nicht mit Wiederholung (Zeilen naechster lauf im Schritt zuhoeren). Die Kette endet mit diesem Lauf, neu starten per workflow_dispatch.“

## Geänderte Zeilen

| PR | Datei | Zeilen |
|---|---|---|
| #360 | `.github/workflows/bch-chipnet-lauscher.yml` | 108 bis 132 neu (Kommentar und `api()`), 138 bis 148 geändert (Prüfung auf aktive Läufe und Start über `api()`), 210 bis 218 neu (Schritt „naechster lauf gestartet“). 41 Zeilen dazu, 5 entfernt. |
| #361 | `.github/workflows/zcash-mainnet-lauscher.yml` | 126 bis 150 neu (Kommentar und `api()`), 157 bis 163 geändert (Start über `api()`), 231 bis 239 neu (Schritt „naechster lauf gestartet“). 41 Zeilen dazu, 3 entfernt. |

- **Chipnet:** Neben dem Start läuft auch die Prüfung auf einen anderen aktiven Lauf (`gh run list`) über `api()`. Ein Fehler dort hätte bisher stillschweigend als „anderer Lauf aktiv“ gegolten, und die Kette wäre ohne Warnung zu Ende gewesen. Der Rückfall auf main bleibt, er wird bei `main` als eigenem Branch nicht doppelt versucht.
- **Zcash:** Die Entscheidung über `lauscher_weiter.py` bleibt, es gibt weiter weder eine Prüfung auf aktive Läufe noch einen Rückfall auf main. Bisher brach ein gescheiterter Start den Schritt wegen `set -eu` sofort ab. Damit wäre auch „rohdaten committen“ ausgefallen, also gingen die Daten des Laufs verloren. Das ist mit dem PR behoben.

## Wie getestet

- YAML beider Dateien geladen, `bash -n` für jeden run-Block.
- Der geänderte Block jeder Datei lief lokal mit einem Ersatz-`gh`, der vorgegebene Antworten liefert (ok, HTTP 503, 504, 404, 422, Zeitüberschreitung). Seine Fehlertexte enthalten die API-URL wie die echten. Der Zuhörer selbst und `sleep` waren dabei ersetzt.
- **Chipnet, 8 Fälle:**
  - Sofort ok: gestartet, grün.
  - Zweimal 503, dann ok: 3 Versuche, grün.
  - Fünfmal 503: 5 Versuche, rot.
  - 404 auf dem eigenen Branch, dann main: auf main gestartet, grün.
  - 404 auf main: rot.
  - Prüfung der Läufe fünfmal 504: rot.
  - Zeitüberschreitung, dann ok: grün.
  - Anderer Lauf aktiv: kein Start, grün.
- **Zcash, 6 Fälle:**
  - Sofort ok: grün.
  - Zweimal 503, dann ok: 3 Versuche, grün.
  - Fünfmal 504: rot.
  - 422: rot ohne Wiederholung.
  - Zeitüberschreitung, dann ok: grün.
  - Kein Folgelauf: kein Aufruf, grün.
- In keinem Fall stand die URL der API im Log.
- **Nicht getestet:** ein Lauf auf GitHub. Die Push-Trigger der beiden Workflows gelten nur für `bch/chipnet-lauscher` und `zcash/mainnet-lauscher`, meine Branches starten keinen Lauf. Die erste echte Probe ist der nächste Folgelauf nach dem Merge.

## Ergebnis des Secret-Scans

- `python3 scripts/secret_scan.py --staged` und `--baum` vor jedem Push, auf beiden Branches: nichts gefunden.
- Der Secret-Scan des Push-Ereignisses läuft auf GitHub, der des pull_request-Ereignisses mit dem PR.

## PR-Nummern

- #360, Chipnet-Zuhörer, Ben merged
- #361, Zcash-Kette, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. Keine neue. Miner je Fenster ruht wie entschieden bis So 29.11.

## Was Ben tun muss

- #360 und #361 prüfen und mergen. Nach dem Merge gilt die Änderung ab dem nächsten Lauf, der vom main startet. Der laufende Chipnet-Lauf vom 27.11. 05:36 UTC startet seinen Nachfolger noch mit dem alten Code.
