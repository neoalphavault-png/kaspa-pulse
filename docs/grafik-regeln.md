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

## Looks (Ben, 28.10.2026, Wahl nach dem Musterblatt)
Gewählt sind **A Editorial, B Foto-Objekt und D Neutral und Grün**. Rotiert wird nur zwischen diesen drei. Umgesetzt in `scripts/look_motor.py`.

| Look | Grund | Schrift | Teal |
| --- | --- | --- | --- |
| A-papier | warmes Papier #F4F1EA | Tinte #0B1A17 | nur als Strich |
| A-teal | #49EACB | Dunkelgrün #062B24 | ist der Grund |
| B-foto | ein Foto als Vollbild aus `graphics/fotos/`, Herkunft im Register `docs/look-v2/README.md` | Tinte auf einem Papierschleier über der ruhigen Fläche, das Motiv bleibt frei | – |
| D-dunkel | warmer dunkler Stein #1F1D1A | Stein hell #D6D0C6 | die große Zahl in #49EACB |
| D-hell | heller Stein #ECE7DE oder warmes Weiß | Tinte | als Strich unter der schwarzen Zahl |

- **D hell:** Die große Zahl steht nur in #49EACB, wenn sie gegen den Grund 7:1 erreicht. Auf warmem Weiß und hellem Stein sind es 1,3:1, dort ist die Zahl schwarz und #49EACB steht als Zeile in Form eines Strichs darunter.
- **Akzent zum Anlass:** Ein Foto-Look darf einen Anlass tragen, etwa Halloween mit Kürbis-Orange #E2711D. Das Orange kommt nur als kurzer Strich und als Farbkorrektur am vorhandenen Foto, höchstens rund 5 % der Fläche. Die Zahl bleibt schwarz.

## Verboten (Ben, 28.10.2026)
- **Keine gezeichneten Gegenstände:** keine selbst gezeichneten Piktogramme oder Gegenstände aus SVG-Formen, zum Beispiel Tasse, Sanduhr, Kürbis oder Stoppuhr.
- **Keine Gegenstände aus Punkten:** Die frühere Richtung C (ein Kürbis aus 999 Punkten, eine Tasse aus 2,975 Punkten) fällt raus.
- **Ausnahme:** Das Suchbild „Find the 1“ ist ein eigenes Format und bleibt.
- **Weiter erlaubt:** Diagramme aus echten Daten (Linie, Balken, Raster je Einheit).
- **Seit 29.10.2026 verboten:** die generativen Hintergründe aus `scripts/hintergrund.py` und die Pulslinie neben der Wortmarke, siehe „Hintergrund“.
- **Nicht mehr verwenden:** das alte Halloween-Bild `ig/vergleich/halloween-2026-10-31-01.jpg` und das Karussell „how fast is kaspa, really?“ (`ig/vergleich/`). Beide sind aus dem Repo entfernt, `scripts/vergleichs_karussell.py` baut sie nicht mehr.

## Hintergrund (Ben, 29.10.2026, feste Regel)
Gilt für jeden Generator: Tagesgrafik, Zahl des Tages, Karussell, Story, Cheat Sheet und die PulseHawk-Grafiken.

1. **Nur ruhig:** einfarbig, ein sanfter Verlauf oder ein stark weichgezeichnetes Foto (Look B). Keine Punkte, Partikel, Linien, Herzschlag- oder Kurvenornamente.
2. **Deko sieht nie wie Daten aus:** Nichts Dekoratives kreuzt, überlagert oder berührt Balken, Zahlen oder Achsen. Der Datenbereich hat einen freien Rand von 24 px.
3. **Selbsttest:** Blendet man die Deko-Ebene aus, bleibt die Aussage gleich, und die Deko-Ebene hat kein Pixel im Datenbereich. Fällt der Test durch, wird nichts gesendet und #ops-log bekommt die Meldung.

Umsetzung:
- `scripts/hintergrund.py`: Die acht Motive (Knotennetz und andere) sind abgeschaltet, `MOTIVE_AKTIV = False`. `setzen()` lässt jede Seite unverändert, `aktiv()` ist an keinem Tag wahr.
- **Pulslinie:** Die Herzschlag-Linie neben der Wortmarke ist aus Tagesgrafik, Karussell, Meme, Story und KCC-20 entfernt.
- `scripts/content_wache.py`, `deko_verstoesse()`: Jede Deko trägt die Klasse `hg-ebene` oder das Attribut `data-deko`. Die Wache rendert die Seite mit und ohne Deko. Ändert sich der Text oder ein Pixel im Datenbereich (Elemente mit `data-rolle`, `.zahl`, Diagramm-Formen, Tabellen, je plus 24 px), stoppt sie. `pruefe_seite()` ruft sie für jedes Bild auf. Ein Stopp der Wache sendet nichts, der rote Lauf meldet sich in #ops-log.
- **Look B:** Das Foto ist ein Motiv und kein Muster. Als reiner Hintergrund wird es stark weichgezeichnet, Zahl und Text kommen immer vom Generator, nie aus dem Bild.
- **Erlaubt bleiben:** der sanfte Verlauf im Cheat Sheet und das Gitter in Diagrammen. Das Gitter gehört zu den Daten und ist keine Deko.

## Wortmarke (Ben, 28.10.2026)
- **Varianten:** Die Wortmarke KASPA PULSE wechselt nach dem Grund.
  - schwarz
  - weiß
  - normal, also KASPA weiß und PULSE #49EACB
- **Welche Variante:**
  - Heller Grund und Teal-Grund: schwarz.
  - Dunkler Grund: weiß oder normal.
  - Foto: je nach Helligkeit im Bereich der Marke.
- **Messung:** im fertigen Bild unter der Marke, bei ausgeblendeter Marke, unteres 5-%-Quantil, mindestens **4,5:1** (`look_motor.logo_kontraste`).
- **Abwechslung:** Passen mehrere Varianten, nie zweimal hintereinander dieselbe (`look_takt.logo_waehlen`, gemerkt je Kanal unter `logo/<kanal>`).

## Rotation (Ben, 28.10.2026)
- **Keine Wiederholung:** Nie zweimal derselbe Look hintereinander je Kanal. Feed, Story, Karussell und Tagesgrafik werden getrennt geführt.
- **Zustand:** in `data/look-takt.json` unter `richtung/<kanal>`. Die gewählten Looks stehen in `look_takt.GEWAEHLT` = A, B, D.
- **Innerhalb eines Karussells** wechseln die inneren Folien zwischen A und D, nie zwei gleiche Looks hintereinander.
- **Ein gewünschter Look** (zum Beispiel B für ein Foto-Motiv) gilt nur, wenn er nicht derselbe wie zuletzt auf dem Kanal ist.

## Karussell (Ben, 28.10.2026)
- **Schlussfolie:** Die letzte Folie jedes Karussells ist die Newsletter-Folie mit dem Kurzlink `kaspapulse.com/nl` (utm_source instagram, utm_medium post, utm_campaign karussell), ohne Engagement-Köder.
- **Zahlen:** Sie werden beim Bau frisch geholt. Dieselbe Zahl höchstens einmal pro Tag auf Instagram.
