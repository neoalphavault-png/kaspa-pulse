# Look v2, Musterblatt vom 28.10.2026, Fassung 2

Gebaut mit `scripts/look_v2.py`. Die Bilder liegen unter `ig/look-v2/`, das Musterblatt ist `ig/look-v2/musterblatt.png`.

| Code | Richtung | Inhalt | Grund |
| --- | --- | --- | --- |
| A1 | Editorial | Halloween, Stufe am 4 nov 2026 | Papier #F4F1EA |
| A2 | Editorial | Kaspa in real life, Espresso | Teal #49EACB |
| B1 | Foto-Objekt | Halloween | Foto Kürbis |
| B2 | Foto-Objekt | Espresso | Foto Espresso |
| C1 | Daten-Kunst | Halloween, 999 Punkte, je Punkt 100 KAS der täglichen Senkung | #080B0F |
| C2 | Daten-Kunst | Espresso, 2,975 Punkte, ein Punkt je Block | Papier #F4F1EA |
| D1 | Neutral und Grün | Halloween, nur die Zahl in #49EACB | warmer dunkler Stein #1F1D1A |
| D2 | Neutral und Grün | Espresso, eine Zeile in #49EACB | Stein #3A3733 |

## Zahlen
- **Halloween, computed aus dem Emissionsplan:** Am 4 nov 2026 fällt die Emission von 1,779,989 auf 1,680,086 KAS je Tag, das sind 99,903 KAS weniger.
- **Espresso:** computed aus unserer Zählung vom 27 oct 2026, 5,953 Blöcke in 600.243 s, siehe `docs/suchbild/README.md`. Auf 300 s gerechnet sind das 2,975 Blöcke.

## Fotos
| Datei | Herkunft | Rechte |
| --- | --- | --- |
| `graphics/fotos/kuerbis-grok.jpg` | von Ben am 28.10.2026 geliefert, mit Grok erzeugt | Ben, nach den Nutzungsbedingungen des Dienstes |
| `graphics/fotos/espresso-grok-2.jpg` | von Ben am 28.10.2026 mit Fassung 2 geliefert, mit Grok erzeugt, 768 x 1152 | Ben, nach den Nutzungsbedingungen des Dienstes |

Beide sind 2:3 und werden auf 1080 x 1350 zugeschnitten und hochskaliert. Für den Einsatz wären Fassungen mit mindestens 1080 px Breite schärfer.

## Prüfung
Jede Seite läuft durch `content_wache` im Profil feed: Mindestgrößen, Textregeln, Kontrast 7:1 und bei A und C der freie Rand von 60 px. Bei B entfällt nur der Rand, weil das Foto bis an die Kante geht. Hinter den Texten liegt dort ein Schleier aus Papierfarbe, damit sie 7:1 erreichen.

## Warum D auf dunklem Stein
Teal #49EACB als Schrift erreicht auf warmem Weiß (#F4F1EA) nur etwa 1,3:1 Kontrast, auf Hellgrau noch weniger. Das ist unlesbar und liegt weit unter der 7:1-Regel. Auf warmem dunklem Stein erreicht dasselbe Teal über 7:1, der Grund bleibt neutral und das Bild ruhig. Auf hellem Grund ist Teal nur als Linie oder Fläche möglich, so wie in A1 und C2.
