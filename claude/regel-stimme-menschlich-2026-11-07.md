# Regel: Stimme fuer alle automatischen Texte (Ben, 7.11.2026)

Stand 7.11.2026, abends angepasst: der automatische X-Post von @gokugalax ist
dauerhaft abgeschaltet. Die Regel gilt deshalb fuer:

- die Instagram-Caption der Tagesgrafik (`scripts/tagesgrafik.py`, `ig_caption`)
- den Threads-Text (eigener Text aus der Tagesgrafik, `-threads.json`, `scripts/threads.py`)
- den oeffentlichen Discord-Text der Tagesgrafik (#daily-graphic)
- die Karussell-Captions (`scripts/karussell.py`, `scripts/look_motor.py` Schalter)
- die Meme-Caption (`scripts/meme_wahr.py`)

Nicht dafuer: der X-Text der Tagesgrafik und die Antwort darunter, die Zahl
des Tages (eigenes Regelwerk, siehe Bericht), Ops-Meldungen nach #ops-log und
#moderator-only. Bildtexte (Kopf, Datumszeile, "counted by kaspa pulse" im
Bild) sind Bild, nicht Posttext.

## 1. Schreibung

Normale Gross- und Kleinschreibung: Satzanfang gross, Eigennamen richtig
(Kaspa, Kaspa Pulse, Bitcoin, KAS, PH/s, UTC, DAA, Kaspalytics, Kaspa REST
API, Monate wie "6 Nov 2026", Wochentage). Hashtags, Handles und Links bleiben
unveraendert.

## 2. Keine feste Schlussfrage

Eine Frage steht nur, wenn der Bauplan "frage" gewaehlt ist. Ganz gestrichen
sind diese drei Saetze:

- "what number would you put next to this one?"
- "how many KAS is that?"
- "what was that work paid?"

## 3. Hoechstens ein Methoden-Wort je Text

counted, computed, source: zusammen hoechstens eines pro Text.

## 4. Bauplaene, wechselnd

Mindestens fuenf Bauplaene, jeder Text folgt genau einem:

| Bauplan | Aufbau |
|---|---|
| beobachtung | der Satz mit der Zahl, dann Fenster und Quelle |
| vergleich | Bitcoin als Massstab: zwei Zahlen nebeneinander, kein "better", kein Werturteil. Nur mit einer echten, datierten Bitcoin-Zahl, sonst faellt er aus |
| einordnung | Zahl, Fenster und Quelle, dazu ein Satz, der die Zahl einordnet |
| pointe | Zahl, Fenster und Quelle, dazu eine kurze trockene Pointe |
| frage | Zahl, Fenster und Quelle, am Ende eine Frage. Nur gelegentlich |
| datum_voran | das Datum fuehrt ("On 6 Nov 2026, ..."), danach nur die Quelle |
| zahl_zuerst | die Zahl mit Einheit fuehrt, dann Fenster und Quelle |

Derselbe Bauplan nie zweimal am selben Tag ueber Instagram, Threads,
Discord, Karussell und Meme. Die Wahl ist deterministisch (Datum und Kanal)
und steht je Tag in `data/stimme-stand.json`.

## 5. Floskel-Sperre

Gesperrt, gross oder klein, in jedem Text und im Quelltext der Textskripte:

- "one thing we keep in mind"
- "useful view"
- "good work by"
- "the part worth watching"
- "method on pulsehawk.io"

## 6. Textregeln, die bleiben

Keine Gedankenstriche, Doppelpunkte oder Pfeile im Fliesstext, keine
Kursziele, keine Preise, keine Echtzeitwoerter (now, live, today, "for now",
"this morning"), "%" statt "percent", jede Zahl mit Datum, "Rekord" nur mit
Zeitraum, kein Engagement-Koeder, Bitcoin nur als Massstab, keine andere
Chain als Vergleich, kein "real KAS", kein "meaningful". Die bestehenden
Wachen (`tagesgrafik.pruefe_eine`, `content_wache.py`,
`karussell.caption_pruefen`, `threads.wache`, `preis_wache.py`) bleiben in
Kraft; angepasst sind sie nur dort, wo sie Kleinschreibung oder die
Pflichtfrage erzwungen haben.

Umsetzung: `scripts/stimme.py` (Bauplan-Wahl, Tagesstand, Schreibung,
Regelpruefung, Selbsttest).
