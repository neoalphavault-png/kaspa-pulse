# Grafik-Regeln

Angelegt am 28.10.2026. Hier stehen die Regeln für alle Grafiken von Kaspa Pulse: Instagram, Threads, X, Discord, Story und Karussell. Die Generatoren prüfen sie, soweit das maschinell geht.

## Marke
- **Schriften:** Archivo 900 für Zahlen und Titel, IBM Plex Sans für Text, IBM Plex Mono für Quelle und Datum.
- **Farben:** #080B0F, #F2F5F4 oder wärmeres Papier (#F4F1EA), Teal #49EACB als Akzent.
- **Wortmarke:** KASPA PULSE, kein Falke.
- **Kontrast:** Jeder Text erreicht gegen seinen Grund mindestens 7:1 (`content_wache`, `hintergrund.kontrast_verstoesse`). Auf hellem Grund ist Teal deshalb nie Schriftfarbe, nur Linie, Punkt oder Fläche.

## Zahlen und Text
- Jede Zahl hat ein Datum und eines der Wörter counted (eigene Zählung), source (fremde Zahl) oder computed (aus Protokollregeln gerechnet).
- Keine Gedankenstriche, Doppelpunkte oder Pfeile im Fließtext, keine Echtzeitwörter, keine Kursziele, keine Preise.
- Bitcoin nur als Maßstab, zwei Zahlen nebeneinander, ohne Werturteil.

## Motive (Ben, 28.10.2026)
- **Keine selbst gezeichneten Piktogramme oder Gegenstände aus SVG-Formen mehr.** Gemeint sind Tasse, Sanduhr, Kürbis, Stoppuhr und Ähnliches.
- **Erlaubt:**
  - Typografie allein (Richtung A)
  - echte Fotos mit belegter Herkunft im Register (Richtung B)
  - Formen, die aus echten Daten entstehen, zum Beispiel ein Punkt je Block (Richtung C)
  - ein neutraler Grund mit einer einzigen Zahl oder Zeile in #49EACB und kleiner Wortmarke (Richtung D). Der Grund ist dann dunkler Stein, weil Teal als Schrift auf hellem Grund nur 1,3:1 erreicht.
  - die generativen Hintergründe aus `scripts/hintergrund.py`, weil sie Muster sind und keine Gegenstände
- **Nicht immer dunkel:** helles Papier und Teal sind gleichwertige Gründe.
- **Welche Richtung wofür gilt,** entscheidet Ben nach dem Musterblatt vom 28.10.2026 (`docs/look-v2/`). Die Wahl wird hier eingetragen.

## Abwechslung (Ben, 28.10.2026)
- **Rotation:** Alle Generatoren (Karussell, Tagesgrafik, Story) rotieren zwischen den gewählten Richtungen.
- **Keine Wiederholung:** Nie zweimal dieselbe Richtung hintereinander auf derselben Plattform, auch nicht bei zwei Posts am selben Tag.
- **Umsetzung:** `look_takt.richtung_merken(speicher, plattform, datum, serie)`. Die gewählten Richtungen stehen in `look_takt.GEWAEHLT`, der Speicher in `data/look-takt.json` unter `richtung/<plattform>`.
