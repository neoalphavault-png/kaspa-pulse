# Bericht 8.11.2026: X-Post von @gokugalax pausiert, 8.11. bis 14.11.

Auftrag von Ben vom 7.11.2026. Die Workflow-Datei ist geändert, deshalb merged Ben, bis So 8.11. 08:00 Berlin.

## Welcher Post
- Der tägliche automatische X-Post ist der Post zur Zahl des Tages aus `.github/workflows/number-of-day.yml`, Schritt „post to x“ (`scripts/x_post.py --from-nod`).
- Laut `data/x-post-log.json` geht er jeden Tag gegen 08:42 UTC raus, das sind 09:42 Berlin (Schlüssel `nod-<datum>`).
- Einen zweiten täglichen X-Post gibt es auf main nicht.

## Schalter
- In `number-of-day.yml` steht oben `env: X_GOKU_AN: "false"`, mit Kommentar und Datum.
- „post to x“ läuft nur bei `X_GOKU_AN == 'true'`. Steht der Schalter auf `"false"`, schreibt ein Schritt „x pausiert“ eine Zeile ins Job-Log.
- Am So 15.11. genügt eine Zeile, `X_GOKU_AN: "true"`, dann postet der Lauf wieder wie vorher.
- Kein Code ist gelöscht. `x_post.py` und der Schritt bleiben unverändert.

## Was weiterläuft
- Zahl des Tages: Discord und Telegram (`post_number_of_day.py`), Archivbild, Log und Seitenstempel.
- Instagram, Threads, Tagesgrafik auf Discord, Karussell und alle PulseHawk-Posts sind nicht betroffen.
- Die Sperre gegen Doppelposts hängt am Archivbild des Tages (`graphics/archive/<tag>.png`), nicht am X-Log. Der zweite Termin am Tag postet also auch während der Pause nicht doppelt nach Discord.
- Die Selbstantwort unter dem X-Post entfällt mit, sie gehört zum selben Schritt.

## Prüfung
- YAML lädt, `env.X_GOKU_AN` ist `"false"`.
- Secret-Scan ohne Fund.

## Offen für Ben
- **Weekly-X-Post am Montag:** `weekly-afternoon.yml` postet montags die Weekly Numbers über dieselben X-Zugangsdaten. Der Auftrag nennt nur den Tagespost. Darum läuft der Weekly-Post am Mo 9.11. weiter. Soll er auch pausieren?
