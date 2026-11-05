# Schalter-Karussell: Quellzeile Bild 2 ohne „computed“

Auftrag von Ben vom 5.11.2026, erledigt am 5.11.2026 um 15:20 Berlin, vor dem Entwurf Fr 6.11. 09:00. Nur `scripts/`, Selbst-Merge nach der Regel vom 26.10.

## Was geändert ist

- In `scripts/look_motor.py`, `schalter_seiten()`, hat die Quellzeile der Hashrate-Seite (Bild 2) jetzt den neuen Wortlaut:

  | | Quellzeile |
  | --- | --- |
  | vorher | „source kaspa rest api, daily means computed by kaspa pulse, %s“ |
  | jetzt | „source kaspa rest api, daily means by kaspa pulse, %s“ |

- Grund: „computed“ ist nur für Werte aus festen Protokollregeln erlaubt. Ein Tagesmittel aus Fremddaten gehört nicht dazu.
- Die Caption bleibt unverändert. Dort steht „computed“ nur bei der Belohnung („the reward computed from the emission schedule“), und das ist eine Protokollregel.
- Commit `d6fbd06`, per `automerge-claude.yml` auf `main` (Lauf [42042074696](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42042074696)).

## Selbsttest

- `python3 scripts/look_motor.py --selbsttest`: 0 Fehler. Neu ist die Prüfung „schalter, quelle bild 2 ohne computed“. Sie verlangt den neuen Wortlaut genau, mit „5 nov 2026“, und kein „computed“.
- `python3 scripts/karussell_post.py --selbsttest`: 0 Fehler.

## Probe

`karussell.yml` lief mit art=schalter, schritt=probe, fuer=2026-11-06, start=hand. Lauf [42042118959](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42042118959) auf `d6fbd06`, grün.

- Er ist trocken geblieben, nichts wurde veröffentlicht.
- Die drei Seiten liegen als Bot-Commits unter `ig/karussell/`:
  - `9c98ed4`, Bild 1, A-papier
  - `a5fdf3c`, Bild 2, D-dunkel
  - `c22ae84`, Bild 3, A-papier
- **Bild 2** (`ig/karussell/karussell-schalter-2026-11-06-2-D-dunkel-8bdbbad0.jpg`) zeigt unter den Balken: **„source kaspa rest api, daily means by kaspa pulse, 5 nov 2026“**. Ich habe es neben das Bild 2 der Probe davor gelegt (`dbcec72`, „…daily means computed by kaspa pulse, 5 nov 2026“). Sonst ist nichts anders, auch die Zahlen sind gleich (348 PH/s, 356 gegen 348).
- Das Artefakt `karussell-entwurf-schalter-2026-11-06-probe` ließ sich aus der Arbeitsumgebung nicht herunterladen, der Proxy sperrt den Speicher von GitHub. Geprüft habe ich deshalb das abgelegte JPEG aus demselben Lauf.

## Am Rand

Dieselbe Art Formulierung steht noch an zwei anderen Stellen. Sie sind nicht geändert, weil sie nicht zum Auftrag gehören:

- `scripts/whales_seite.py:95`: „7 day mean computed by kaspa pulse“
- `scripts/archiv.py:62`: „the average computed by kaspa pulse“ aus Kraken-Kerzen

Soll ich die beiden genauso umstellen?
