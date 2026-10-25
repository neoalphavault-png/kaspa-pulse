# Bildhintergründe

Register der Hintergrundmotive für Tagesgrafik, Zahl des Tages, Karussell und Story-Vorlagen (Ben, 25.10.2026). Gebaut von `scripts/hintergrund.py`, nicht von Hand ändern: `python3 scripts/hintergrund.py --bauen` schreibt Standbilder und Register neu, `--pruefen` fällt auf jede Abweichung.

- **Herkunft:** generativ. Jedes Motiv entsteht im Skript aus einem festen Startwert. Keine fremden Bilder, keine Fotos, keine Lizenz Dritter, kein Falke.
- **Farben:** nur die Töne aus `scripts/look_takt.py`. Der Teal-Look zeichnet die Formen der hellen Fassung in seinen eigenen Farben.
- **Takt:** Look und Motiv wechseln gemeinsam. Im Instagram-Raster nimmt jeder Post das Motiv nach dem seines Vorgängers (`look_takt.raster_motiv`), es steht also nie dasselbe Motiv zweimal hintereinander. Andere Kanäle und die Story rücken mit dem Datum weiter, die Story nie im Motiv des Feed-Posts vom selben Tag.
- **Lesbarkeit:** hinter jedem Text liegt ein Schleier im Grundton (Deckung 95 %). Die Kontrast-Wache misst im fertigen Bild jeden Text gegen seinen Grund, mindestens 7:1. Ausgenommen ist nur die Wortmarke.

| Motiv | Herkunft | Fassung | Feed 1080x1350 | Story 1080x1920 | Startwert |
| --- | --- | --- | --- | --- | --- |
| blockstrom | generativ | dunkel | `graphics/hintergruende/blockstrom-dunkel-feed.svg` | `graphics/hintergruende/blockstrom-dunkel-story.svg` | 14952 |
| blockstrom | generativ | hell | `graphics/hintergruende/blockstrom-hell-feed.svg` | `graphics/hintergruende/blockstrom-hell-story.svg` | 14952 |
| knotennetz | generativ | dunkel | `graphics/hintergruende/knotennetz-dunkel-feed.svg` | `graphics/hintergruende/knotennetz-dunkel-story.svg` | 15002 |
| knotennetz | generativ | hell | `graphics/hintergruende/knotennetz-hell-feed.svg` | `graphics/hintergruende/knotennetz-hell-story.svg` | 15002 |
| punktraster | generativ | dunkel | `graphics/hintergruende/punktraster-dunkel-feed.svg` | `graphics/hintergruende/punktraster-dunkel-story.svg` | 16715 |
| punktraster | generativ | hell | `graphics/hintergruende/punktraster-hell-feed.svg` | `graphics/hintergruende/punktraster-hell-story.svg` | 16715 |
| hoehenlinien | generativ | dunkel | `graphics/hintergruende/hoehenlinien-dunkel-feed.svg` | `graphics/hintergruende/hoehenlinien-dunkel-story.svg` | 18286 |
| hoehenlinien | generativ | hell | `graphics/hintergruende/hoehenlinien-hell-feed.svg` | `graphics/hintergruende/hoehenlinien-hell-story.svg` | 18286 |
| partikel-puls | generativ | dunkel | `graphics/hintergruende/partikel-puls-dunkel-feed.svg` | `graphics/hintergruende/partikel-puls-dunkel-story.svg` | 20031 |
| partikel-puls | generativ | hell | `graphics/hintergruende/partikel-puls-hell-feed.svg` | `graphics/hintergruende/partikel-puls-hell-story.svg` | 20031 |
| zahnraeder | generativ | dunkel | `graphics/hintergruende/zahnraeder-dunkel-feed.svg` | `graphics/hintergruende/zahnraeder-dunkel-story.svg` | 14647 |
| zahnraeder | generativ | hell | `graphics/hintergruende/zahnraeder-hell-feed.svg` | `graphics/hintergruende/zahnraeder-hell-story.svg` | 14647 |
| sternenfeld | generativ | dunkel | `graphics/hintergruende/sternenfeld-dunkel-feed.svg` | `graphics/hintergruende/sternenfeld-dunkel-story.svg` | 16377 |
| sternenfeld | generativ | hell | `graphics/hintergruende/sternenfeld-hell-feed.svg` | `graphics/hintergruende/sternenfeld-hell-story.svg` | 16377 |
| glitch-raster | generativ | dunkel | `graphics/hintergruende/glitch-raster-dunkel-feed.svg` | `graphics/hintergruende/glitch-raster-dunkel-story.svg` | 20015 |
| glitch-raster | generativ | hell | `graphics/hintergruende/glitch-raster-hell-feed.svg` | `graphics/hintergruende/glitch-raster-hell-story.svg` | 20015 |
