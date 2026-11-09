# Bericht 10.11.2026: Folge zu #286, X-Satz raus, Form 3 computed

Auftrag von Ben vom 9.11.2026, Frist Mi 11.11. 12:00 Berlin. Keine Workflow-Datei ist geändert, deshalb gilt der Selbst-Merge nach der Regel vom 26.10., wenn alles grün ist.

## 1. Der X-Satz ist aus dem Discord-Text gestrichen
- **`tagesgrafik.py`:** Der Discord-Text endet jetzt mit dem Mail-Satz. „share it first, it goes on x at 17:00.“ steht nicht mehr darin.
  - Grund eins: Engagement-Köder sind verboten.
  - Grund zwei: @gokugalax postet seit #285 nicht mehr automatisch.
- **Textprüfung:** Die Pflicht für den Satz ist weg. Ein Discord-Text, der den X-Termin nennt oder zum Teilen auffordert, fällt jetzt auf (`DISCORD_KOEDER`).
- **Selbsttest `tagesgrafik.py`:**
  - Der Fall „discord mit 17:00“ ist ersetzt durch „discord ohne x-termin und ohne aufforderung zum teilen, mail-satz am ende“, für jede Form.
  - Der Instagram-Fall mit „it goes on x at 17:00“ ist entfernt. Die Instagram-Wache sperrt den X-Termin weiter.
- **`stimme.py`:** Der Test „it goes on X at 17:00“ (vorher Zeile 380) ist ersetzt. „share it first“ steht jetzt in der Floskel-Sperre, im Text und im Quelltext der Textskripte. Der Selbsttest prüft das.

## 2. Form 3 heißt jetzt „computed“
- **Neue Herkunft:** `RECHNUNG = "computed by kaspa pulse from the emission schedule"`. Der Reward-Cut-Countdown kommt aus dem Emissionsplan, gezählt wird dort nichts.
- **Wo die Zeile steht:** in der Datumszeile im Bild, in der Instagram-Caption, im Threads-Text und im Discord-Text. Bei Threads und Discord steckt sie in der zweiten Zeile: „Next step <Datum>, <Uhrzeit> UTC, computed by Kaspa Pulse from the emission schedule.“
- **Wache:** Die Datumszeile darf auf „counted by kaspa pulse“, auf „computed by kaspa pulse from the emission schedule“ oder auf „source …“ enden. Form 3 muss auf „computed …“ enden, sonst fällt sie auf. Der Stichtag für Instagram ist bei beiden eigenen Herkünften der Tag der Messung.
- **Selbsttest:**
  - Datumszeile ohne Werte, höchstens zwei Zeilen, endet auf „computed …“.
  - „counted“ bei Form 3 fällt auf.
  - Caption, Threads und Discord nennen „computed …“ und kein „counted“.
- **Bild:** Die Datumszeile wird länger und bricht jetzt auf zwei Zeilen um. Vorher hielt der Selbsttest sie bei höchstens 70 Zeichen in einer Zeile. Gerendert mit den Testwerten überlappt nichts, und die Wache im Bild ist grün. Vorschau: `berichte/bilder/2026-11-10-form3-computed.png`.

Mit den Testwerten aus dem Selbsttest sehen die drei Texte so aus:

```
Instagram
On 29 Sep 2026, 6 days to the next block reward cut.

Computed by Kaspa Pulse from the emission schedule.

Weekly Kaspa numbers in our newsletter, link in bio.

#kaspa #kas #blockdag

Threads
6 days to the next block reward cut.
Next step 5 Oct 2026, 03:15 UTC, computed by Kaspa Pulse from the emission schedule.

Discord
Kaspa cuts its block reward again in 6 days.
Next step 5 Oct 2026, 03:15 UTC, computed by Kaspa Pulse from the emission schedule.
How often does that happen?

All the weekly numbers in one mail, every Monday.
```

## 3. Bauplan vergleich
Der Bauplan bleibt aus. `data/bitcoin-massstab.json` gibt es nicht, also wählt `stimme.py` „vergleich“ nie. Das ändert sich erst, wenn Ben die Bitcoin-Quelle festlegt.

## Prüfung
- **Selbsttests:**
  - tagesgrafik 0 Fehler
  - stimme 0 Fehler
  - threads 96 Fälle, 0 falsch
  - instagram, karussell, karussell_post, content_wache, preis_wache und look_takt je 0 Fehler
- **Secret-Scan:** ohne Fund.
- **Nicht geändert:** Der X-Entwurf für den Post von Hand geht weiter nach #moderator-only („x um 17:00 von hand“). Das ist eine Ops-Meldung und kein öffentlicher Text. Ob er bleibt, hat Ben noch nicht entschieden.

## Kopf
Die Änderung steht in `8f4db41`. Dieser Eintrag liegt als eigener Commit darauf.
