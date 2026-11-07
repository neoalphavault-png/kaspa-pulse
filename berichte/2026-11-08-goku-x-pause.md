# Bericht 8.11.2026: Goku-X aus, dauerhaft

Auftrag von Ben vom 7.11.2026, mit Nachtrag von ~21:00: Auf @gokugalax erscheint kein Post mehr, den ein Workflow oder Skript per API absetzt. Das gilt ohne Enddatum. Workflow-Dateien sind geändert, deshalb merged Ben, bis So 8.11. 08:00 Berlin.

## Schalter
- **`scripts/x_post.py`:** Ein Aufruf mit POST an X geht nur raus, wenn die Umgebungsvariable `X_GOKU_AN` auf `"true"` steht.
  - Fehlt sie oder steht sie auf etwas anderem, ist X aus.
  - `main()` beendet jeden Post-Lauf grün mit „x ist aus (X_GOKU_AN ist nicht true), auf @gokugalax geht nichts raus“ und ohne Eintrag im Log.
  - `call()` sperrt zusätzlich jeden POST, damit auch ein anderer Aufrufer nichts absetzen kann.
  - Lesen (GET, Uhrwerk-Metriken), Löschen, `--dry-run` und `--selftest` bleiben erlaubt.
- **`.github/workflows/number-of-day.yml`:** oben `env: X_GOKU_AN: "false"`. „post to x“ läuft nur bei `"true"`, sonst schreibt „x pausiert“ eine Zeile ins Job-Log.
- **`.github/workflows/weekly-afternoon.yml`:** oben `env: X_GOKU_AN: "false"`. Der Montagsfaden endet damit grün ohne Post.
- **Wieder einschalten:** in beiden Workflows die Zeile auf `"true"` stellen. Kein Code ist gelöscht.

## Alle Stellen, die bis zu diesem PR auf @gokugalax posten konnten
Alle laufen über `scripts/x_post.py` und die Secrets `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN` und `X_ACCESS_SECRET`. Diese vier Secrets kommen in drei Workflows vor: `number-of-day.yml`, `weekly-afternoon.yml` und `uhrwerk.yml`.

| Stelle | wann | was | jetzt |
| --- | --- | --- | --- |
| `number-of-day.yml`, Job render, Schritt „post to x“ | täglich, laut `data/x-post-log.json` gegen 08:42 UTC, das sind 09:42 Berlin | Post zur Zahl des Tages mit Bild, dazu die Selbstantwort (`x_post.py --from-nod`) | aus |
| `number-of-day.yml`, Job x-test | nur von Hand, mit der Eingabe `x_test` | Testpost, sofort gelöscht | aus |
| `weekly-afternoon.yml`, Schritt „x faden posten“ | montags 15:20 Berlin | Weekly-Faden mit Grafik und zwei Selbstantworten (`x_post.py --weekly`) | aus |
| `weekly-afternoon.yml`, Job Trockenlauf | nur von Hand | ein Post mit der 4:5-Grafik, sofort gelöscht | aus |
| `x_post.py` von Hand | jederzeit mit den Secrets in der Umgebung | jeder Post | aus, solange `X_GOKU_AN` nicht `true` ist |
| `uhrwerk.yml`, Schritte „schnappschuesse“ und „was liefert x“ | Uhrwerk-Takt | liest nur Metriken per GET (`uhrwerk_proben.py`, `insights_sammler.py`) und postet nicht | unverändert, die Datei ist nicht angefasst |

Die Tagesgrafik postet nicht selbst auf X. Sie schickt nur einen X-Text und die Antwort als Entwurf nach #moderator-only, für einen Post von Hand.

## Was weiterläuft
- Zahl des Tages auf Discord und Telegram, das Archivbild und das Log.
- Instagram, Threads, Tagesgrafik auf Discord, Karussell, Meme, Newsletter und PulseHawk.
- **Keine Doppelposts:** Die Sperre der Zahl des Tages hängt am Archivbild des Tages, nicht am X-Log. Discord bekommt also nur einen Post am Tag.

## Prüfung
- `x_post.py --selftest` ok. Neu geprüft wird: Ohne Variable oder mit `false` ist X aus, ein POST über `call()` wird abgelehnt, und nur `true` schaltet an.
- Probe ohne Netz: `x_post.py --text probe` mit Platzhalter-Secrets endet mit Exit 0 und „x ist aus“, gesendet wird nichts.
- Beide Workflows laden als YAML, `env.X_GOKU_AN` ist `"false"`.
- Secret-Scan ohne Fund.

## Offen für Ben
- **Satz im Discord-Text:** Der Discord-Text der Tagesgrafik sagt noch „it goes on x at 17:00“. Das meint den Post von Hand. Soll der Satz raus? Er gehört zum Stimm-Auftrag für Discord.
- **Entwurf nach #moderator-only:** Die Tagesgrafik schickt weiter den X-Entwurf nach #moderator-only. Soll das bleiben?
