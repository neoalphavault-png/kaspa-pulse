# Kaspa in Zahlen, zum Anfassen

Generator `scripts/vergleichs_karussell.py`, Format nach Ben vom 27.10.2026.

## Bildregister

Alle Objekte sind gezeichnet, als SVG in Graustufen im Skript (`OBJEKTE`), ohne fremde Vorlage. Es gibt also keine Lizenzfrage.

| Objekt | Herkunft | Lizenz |
| --- | --- | --- |
| stoppuhr, sanduhr, tasse, bett, brief | gezeichnet von kaspa pulse, 27.10.2026 | eigene |
| bloecke (10 blöcke in einer reihe) | gezeichnet von kaspa pulse, 27.10.2026 | eigene |
| kuerbis, netz (halloween) | gezeichnet von kaspa pulse, 27.10.2026 | eigene |

Die offenen Bildarchive (Openverse, Wikimedia Commons, Art Institute of Chicago, Met) waren am 27.10.2026 aus der Arbeitsumgebung nicht erreichbar. Deshalb ist kein Foto dabei. Für freigestellte Fotos statt Zeichnungen: `skills/taste-skill/scripts/assets.mjs --license cc0,pd`, und jede Datei mit Quelle und Lizenz hier eintragen.

## Neu bauen

```
python3 scripts/vergleichs_karussell.py bauen --lauf 2026-10-21 --ziel out/vergleich
python3 scripts/vergleichs_karussell.py halloween --ziel out/vergleich
python3 scripts/vergleichs_karussell.py --selbsttest
```

`--lauf` nimmt einen Tag aus `data/tagesgrafik-log.json`, an dem die Blockrate gezählt wurde.
