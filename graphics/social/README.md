# graphics/social, die vier Kanal-Icons für die Newsletter-Leiste

Die Kanal-Leiste im Newsletter (ab Ausgabe 14, `newsletter/2026-10-12.html`)
lädt vier PNG von `https://kaspapulse.com/graphics/social/`. **Sie liegen hier
noch nicht**, und sie können nicht aus einer Claude-Sitzung geholt werden: der
Container erreicht youtube.com, discord.com, x.com und instagram.com nicht
(Egress-Sperre, geprüft am 05.10.2026, alle vier antworten mit 000).

Bens Regel dazu, und sie ist der Grund für diese Datei: **nur die offiziellen
Brand-Assets der Plattformen, und nur als Link auf unsere eigenen Kanäle.**
Nachgezeichnete oder nachgebaute Logos kommen nicht in den Newsletter.

## Was gebraucht wird

| Datei | Marke | Offizielle Quelle | Welches Asset |
| --- | --- | --- | --- |
| `youtube.png` | YouTube | youtube.com/about/brand-resources | das Icon, nicht das Wortmarken-Logo |
| `discord.png` | Discord | discord.com/branding | das Clyde-Icon (Mark), einfarbig |
| `x.png` | X | about.x.com Brand Toolkit | das X-Icon |
| `instagram.png` | Instagram | about.meta.com/brand/resources/instagram | das Glyph-Icon |

**Maße: 40 x 40 Pixel**, PNG mit Transparenz. Dargestellt werden sie mit
`width="20" height="20"`, die doppelte Auflösung ist für Retina-Displays. Auf
dem dunklen Grund des Newsletters (#0B0E12) brauchen sie eine helle oder
einfarbig weiße Fassung; die farbigen Originale auf dunklem Grund wirken
schmutzig, aber die Entscheidung gehört zur Marke und nicht ins Skript.

## Bis sie liegen

Die Leiste bleibt vollständig lesbar: jeder Eintrag trägt den Namen als Text
neben dem Icon, und das Icon trägt einen alt-Text. Fehlt die Datei, zeigt das
Mailprogramm den alt-Text oder ein kleines leeres Kästchen, der Name steht so
oder so da. `scripts/brevo_send.py` warnt vor jedem Versand, welche der im
HTML verlinkten Bilder im Repo fehlen, damit es nicht vergessen wird.

Nebenwirkung, falls jemand den alt-Text ändern will: er ist absichtlich der
Kanalname, weil Ben ihn so bestellt hat. Mit abgeschalteten Bildern liest man
den Namen dann zweimal ("youtube youtube"). Wer das nicht mag, setzt `alt=""`,
dann bleibt nur der Name als Text, und die Zeile liest sich einmal.
