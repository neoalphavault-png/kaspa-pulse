# Stimm-Regel fuer die automatischen Texte, 9.11.2026

Auftrag Ben vom 7.11.2026, Frist Di 10.11. 12:00. Regel im Repo:
`claude/regel-stimme-menschlich-2026-11-07.md`. Scope-Aenderung vom 7.11.
abends: der automatische X-Post von @gokugalax ist abgeschaltet, die Regel
gilt fuer Instagram, Threads, Discord, Karussell und Meme. Der X-Text der
Tagesgrafik und die Antwort darunter sind unveraendert (drei Zeilen,
klein, Zeile 3 eine Frage, auch die beiden alten Fragen bleiben dort).

## Was geaendert ist

**scripts/stimme.py (neu).** Gemeinsamer Baustein: Bauplaene, Tagesstand
(`data/stimme-stand.json`, haelt 30 Tage), deterministische Wahl
(`waehlen`), Satzbau je Bauplan (`saetze`), Schreibung (`schreibung`),
Regelpruefung (`regel_verstoesse`, `tag_verstoesse`, `klein_verstoesse`),
Floskel-Sperre mit Quelltext-Scan, Bitcoin-Massstab aus
`data/bitcoin-massstab.json` (`bitcoin_zahl`), eigener Selbsttest.

**scripts/tagesgrafik.py.** Jede Vorlage traegt zusaetzlich `einordnung`
und `pointe` (aus denselben Messwerten), Form 2 und 8 eine eigene `frage`
fuer die Stimm-Texte. `texte()` baut X und Antwort wie bisher und waehlt
fuer Instagram, Threads und Discord je einen Bauplan; Threads hat jetzt
einen eigenen Text (`s["threads"]`), nicht mehr den X-Text. `ig_caption`
baut Bloecke nach Bauplan, `IG_FRAGEN` ohne "what number would you put next
to this one?". `textpruefung` prueft die Stimm-Regel je Kanal und die
Tagesregel. `main` schreibt Text und Bauplan ins `-threads.json`, den
Bauplan ins `-instagram.json`, und mit `--log-schreiben` den Tagesstand.
Form 7: die Antwort hat nur noch ein Methoden-Wort.

**scripts/threads.py.** `wache(text, heute, bauplan)`: die Pflichtfrage ist
weg. Mit Bauplan (Text aus der Tagesgrafik) gilt die Stimm-Regel, ohne
Bauplan (Text von Hand aus der Warteschlange) nur die Hauswache. `posten`
reicht den Bauplan aus dem `-threads.json` durch.

**scripts/instagram.py.** `posten` prueft mit dem Bauplan aus dem
`-instagram.json` (Frage, Schreibung, Methoden-Wort).

**scripts/karussell.py.** `caption()` mit optionalem dritten Block und
Schreibung; `caption_nach_bauplan()` waehlt den Bauplan gegen den
Tagesstand; Bausteine fuer Woche und Story. `caption_pruefen` nimmt 4 oder 5
Bloecke, keine Pflichtfrage mehr, hoechstens ein Methoden-Wort.
`vorbereiten` merkt Bauplan und Stand, der Entwurf schreibt den Stand.

**scripts/look_motor.py.** Schalter-Caption mit einem Methoden-Wort (vorher
"source" und "computed"), Bauplaene, Selbsttest dazu.

**scripts/meme_wahr.py.** Caption nach Bauplan; traegt der Satz schon
"counted" (gemessene Blockrate), nennt der Haken das Periodensystem ohne
"source". "KAsPa" bleibt in der Schreibung erhalten.

**scripts/karussell_post.py.** Der Entwurf (nicht die Probe) schreibt den
Tagesstand; das Manifest traegt den Bauplan.

**.github/workflows/tagesgrafik.yml, karussell.yml.** `git add
data/stimme-stand.json` im vorhandenen Commit-Schritt, im Karussell-Lauf
zusaetzlich `stimme.py --selbsttest`. Workflow-Aenderung, also merged Ben.

Nicht angefasst: X-Text der Tagesgrafik, `x_post.py`,
`number-of-day.yml`, `weekly-afternoon.yml`, pulse-studio, Shorts,
`data/insights/`, `insights_sammler.py`, `post_manifest.py`, `uhrwerk.yml`.

## Die Bauplaene

| Bauplan | Aufbau | wann |
|---|---|---|
| beobachtung | Satz mit Zahl, dann Fenster und Quelle | immer (nicht auf Instagram, die Caption fuehrt mit der Zahl) |
| vergleich | dazu ein datierter Bitcoin-Satz als Massstab, ohne Urteil | nur mit Eintrag in `data/bitcoin-massstab.json`, heute nie |
| einordnung | dazu ein Satz Einordnung aus denselben Messwerten | immer |
| pointe | dazu eine kurze trockene Pointe | immer |
| frage | dazu eine Frage | an jedem 4. Tag fuer einen Kanal reihum, sonst nur als Reserve |
| datum_voran | "On 6 Nov 2026, ...", danach nur die Quelle | immer |
| zahl_zuerst | Zahl mit Einheit vorn, dann Fenster und Quelle | immer |

## Tagesregel ueber die Kanaele

Jeder Kanal hat je Tag eine Reihenfolge der Bauplaene: die Liste ohne
"frage", gedreht um (Tagesnummer + Kanalnummer). "frage" steht vorn nur beim
Fragekanal des Tages (jeder 4. Tag, reihum), sonst ganz hinten. Genommen
wird der erste Bauplan, der an diesem Tag noch frei ist, dessen Text gebaut
werden kann und alle Wachen haelt. Die Tagesgrafik waehlt Instagram,
Threads, Discord in einem Lauf (fuenf immer verfuegbare Bauplaene reichen
fuer drei), schreibt den Stand mit `--log-schreiben`; Karussell und Meme
lesen ihn spaeter am Tag und ergaenzen ihn beim Entwurf. Ein zweiter Lauf am
selben Tag bekommt denselben Bauplan. Ist nichts frei, stoppt der Lauf mit
`StimmeStopp` (bei fuenf Kanaelen und fuenf festen Bauplaenen plus Reserve
kommt das im Regelbetrieb nicht vor; der Selbsttest der Tagesgrafik spielt
14 Tage mit Karussell und Meme durch).

## Floskel-Sperre

`stimme.FLOSKELN` (case-insensitive) faellt in jedem Text auf
(`regel_verstoesse`), dazu prueft der Selbsttest den Quelltext der
Textskripte (tagesgrafik, karussell, look_motor, meme_wahr, threads,
instagram, karussell_post). Treffer heute: keiner. Hinweis:
"method on pulsehawk.io" ist in `scripts/ph/` (PulseHawk-Entwuerfe) Pflicht,
das ist ein anderes Projekt und hier nicht angefasst.

## Gelockerte Wachen und warum

- `tagesgrafik.DATUM` jetzt case-insensitive ("6 Nov 2026").
- `ig_pruefung`: keine Pflichtfrage an Platz 2 mehr, mindestens 4 Bloecke,
  hoechstens eine Frage; Quellen-Zaehlung und x-Termin ohne Gross/Klein.
- `textpruefung`: Mail-Satz und 17:00-Satz im Discord-Text ohne Gross/Klein
  verglichen.
- `threads.wache`: keine Pflichtfrage; Frage nur beim Bauplan frage.
- `karussell.caption_pruefen`: 4 oder 5 Bloecke statt genau 5, block 3 keine
  Pflichtfrage; `text_pruefen` erkennt "Source" auch gross.
- `pruefe_eine(..., massstab=True)` laesst "bitcoin"/"btc" nur beim Bauplan
  vergleich durch; Werturteile ("better", "faster", "than bitcoin" ...)
  faengt `stimme.regel_verstoesse` immer.

Verschaerft: hoechstens ein Methoden-Wort (auch Karussell), Kleinschreibung
faellt auf, "today", "this morning", "for now" faellt auf, Floskeln, alte
Schlussfragen, doppelter Bauplan am Tag.

## Selbsttests

Vorher auf main (Branch-Basis): alle gruen ausser `wortmarke.py` (4 Fehler,
bekannt). Nachher:

| Selbsttest | Faelle ok | Fehler |
|---|---|---|
| tagesgrafik.py --selftest | 369 | 0 |
| stimme.py --selbsttest | 56 | 0 |
| karussell.py --selbsttest | 39 | 0 |
| karussell_post.py --selbsttest | 60 | 0 |
| look_motor.py --selbsttest | 45 | 0 |
| meme_wahr.py --selbsttest | 22 | 0 |
| threads.py --selbsttest | 90 | 0 |
| instagram.py --selbsttest | 72 | 0 |
| content_wache.py --selbsttest | 62 | 0 |
| look_takt.py --selbsttest | 55 | 0 |
| x_post.py --selftest | gruen | 0 |
| number_of_day.py --selbsttest | 42 | 0 |
| preis_wache.py --selbsttest | 29 | 0 |
| wortmarke.py --selbsttest | 31 | 4 (wie auf main) |

## Beispiele aus echten Daten der Woche

Erzeugt offline mit dem neuen Code, Tagesstand in der Reihenfolge der Woche
simuliert (Tagesgrafik zuerst, dann Karussell, dann Meme). Quellen der
Werte: Form 3 aus dem Emissionsplan (`reward_plan`, Messzeit 2.11. 06:30
UTC), Form 5 aus `tagesgrafik-log.json` (gebuehren vom 3.11.), Form 10 und
Form 2 aus `number-of-day-log.json` (Umlauf, Anteil, Wallet; dessen Messung
08:12 UTC, die Tagesgrafik misst 06:30, die gezeigten Zahlen stimmen mit den
geposteten 96.82% und 5.57% ueberein), die Bewegung vom 4.11. 12:05 UTC aus
dem Threads-Text und der Differenz im Log, Form 8 aus `instagram-log.json`
(350.2 PH/s am 6.11.; die 90-Tage-Reihe fuer das Bild liegt nicht im Repo,
sie geht in keinen Text ein), neue KAS am 6.11. aus dem Emissionsplan.
Karussell aus `weekly-history.json` (Ausgabe 2.11., week to 31 Oct), Meme
mit der Crescendo-Blockrate (kein Netz fuer die Messung). Die Tagesgrafik
vom 6.11. (Form 11) laesst sich nicht nachbauen: der Anteil "2 Jahre" (p2)
steht nirgends im Repo. Das Schalter-Karussell vom 6.11. ebenso wenig: die
Tagesmittel der Hashrate vom 2., 3. und 5.11. fehlen im Repo. Karussell und
Meme liefen in dieser Woche nur am 7.11. (Meme gar nicht, Motiv verbraucht);
ihre Beispiele 2 und 3 sind deshalb Szenarien desselben Tages mit mehr
belegten Bauplaenen, so gekennzeichnet. Jedes Beispiel unten haelt die
genannte Kanalwache, `stimme.regel_verstoesse`, dazu
`content_wache.text_verstoesse`, `preis_wache.verstoesse` und
`pruefe_eine` (gegengeprueft: 21 Texte, alle gruen, jeder mit hoechstens
einem Methoden-Wort). Ein Bauplan vergleich kommt nicht vor: es gibt keine
datierte Bitcoin-Zahl im Repo.

### Instagram (Caption der Tagesgrafik)

**2026-11-02, Form 3 (Countdown), Bauplan einordnung.** textpruefung: gruen; ig_pruefung: gruen

    3 days to the next block reward cut.
    
    The reward steps down once a month, and 12 steps halve it.
    
    As of 2 Nov 2026, counted by Kaspa Pulse.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-04, Form 10 (Herkunft), Bauplan datum_voran.** textpruefung: gruen; ig_pruefung: gruen

    On 4 Nov 2026, 96.82% of all KAS that will ever exist is already mined.
    
    Counted by Kaspa Pulse.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-07, Form 8 (Sicherheit), Bauplan pointe.** textpruefung: gruen; ig_pruefung: gruen

    350.2 PH/s of hashrate.
    
    That is the work behind every block.
    
    As of 6 Nov 2026, source Kaspa REST API hashrate.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag #proofofwork

### Threads

**2026-11-03, Form 5 (Miner-Oekonomie), Bauplan datum_voran.** textpruefung: gruen; threads.wache mit Bauplan: gruen

    On 2 Nov 2026, Kaspa miners earned 643 times more in new coins than in fees.
    Source Kaspalytics fees, Kaspa emission schedule.

**2026-11-04, Form 10 (Herkunft), Bauplan frage.** textpruefung: gruen; threads.wache mit Bauplan: gruen

    97% of all KAS that will ever exist is already mined, with 0 premine.
    4 Nov 2026, coin supply against max supply.
    How much is left?

**2026-11-07, Form 8 (Sicherheit), Bauplan einordnung.** textpruefung: gruen; threads.wache mit Bauplan: gruen

    Kaspa miners ran 350 quadrillion hashes every second.
    Daily average 6 Nov 2026, source Kaspa REST API.
    1.68M new KAS were issued on 6 Nov, from the emission schedule.

### Discord (#daily-graphic)

**2026-11-02, Form 3 (Countdown), Bauplan datum_voran.** textpruefung: gruen; pruefe_eine (in textpruefung): gruen

    On 2 Nov 2026, Kaspa cuts its block reward again in 3 days.
    Counted by Kaspa Pulse.
    
    Share it first, it goes on X at 17:00.
    All the weekly numbers in one mail, every Monday.

**2026-11-03, Form 5 (Miner-Oekonomie), Bauplan zahl_zuerst.** textpruefung: gruen; pruefe_eine (in textpruefung): gruen

    643x more KAS for miners from new coins than from fees.
    30 days to 2 Nov 2026, source Kaspalytics fees and the emission schedule.
    
    Share it first, it goes on X at 17:00.
    All the weekly numbers in one mail, every Monday.

**2026-11-05, Form 2 (Entity X), Bauplan einordnung.** textpruefung: gruen; pruefe_eine (in textpruefung): gruen

    One wallet holds about 1 in 18 of all KAS in circulation.
    1.23M KAS came into it on 4 Nov 2026, 12:05 UTC, counted on chain.
    The address is public, so anyone can check its balance on the chain.
    
    Share it first, it goes on X at 17:00.
    All the weekly numbers in one mail, every Monday.

### Karussell (Woche, Sa 7.11.)

**2026-11-07, Bauplan zahl_zuerst, tagesstand nach der tagesgrafik vom 7.11. (instagram, threads, discord).** caption_pruefen: gruen; stimme.regel_verstoesse: gruen

    52.2% of all KAS has not moved in a year.
    
    The week in numbers, with addresses inside, week to 31 Oct 2026, source Kaspalytics.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-07, Bauplan beobachtung, szenario, am selben tag zusaetzlich belegt zahl_zuerst.** caption_pruefen: gruen; stimme.regel_verstoesse: gruen

    Half of all KAS has not moved in a year, 52.2%.
    
    The week in numbers, with addresses inside, week to 31 Oct 2026, source Kaspalytics.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-07, Bauplan frage, szenario, am selben tag zusaetzlich belegt zahl_zuerst, beobachtung.** caption_pruefen: gruen; stimme.regel_verstoesse: gruen

    52.2% of all KAS has not moved in a year.
    
    The week in numbers, with addresses inside, week to 31 Oct 2026, source Kaspalytics.
    
    Which of these numbers would you have guessed?
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

### Meme, but true (Sa 7.11.)

**2026-11-07, Bauplan beobachtung, tagesstand nach tagesgrafik und karussell vom 7.11..** meme_wahr.pruefen: gruen; stimme.regel_verstoesse: gruen

    K is potassium 19, As is arsenic 33, Pa is protactinium 91, together they spell KAsPa, source IUPAC periodic table.
    
    The chemistry checks out, and so does the speed, 10 blocks a second, the block rate since the Crescendo upgrade on 5 May 2025.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-07, Bauplan zahl_zuerst, szenario, am selben tag zusaetzlich belegt beobachtung.** meme_wahr.pruefen: gruen; stimme.regel_verstoesse: gruen

    19, 33 and 91 are the atomic numbers of K, As and Pa, together they spell KAsPa, source IUPAC periodic table.
    
    The chemistry checks out, and so does the speed, 10 blocks a second, the block rate since the Crescendo upgrade on 5 May 2025.
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

**2026-11-07, Bauplan frage, szenario, am selben tag zusaetzlich belegt beobachtung, zahl_zuerst.** meme_wahr.pruefen: gruen; stimme.regel_verstoesse: gruen

    K is potassium 19, As is arsenic 33, Pa is protactinium 91, together they spell KAsPa, source IUPAC periodic table.
    
    The chemistry checks out, and so does the speed, 10 blocks a second, the block rate since the Crescendo upgrade on 5 May 2025.
    
    What other word can you build from the table?
    
    Weekly Kaspa numbers in our newsletter, link in bio.
    
    #kaspa #kas #blockdag

### Tagesstand der Woche (simuliert, data/stimme-stand.json)

- 2026-11-02: instagram einordnung, threads pointe, discord datum_voran
- 2026-11-03: instagram pointe, threads datum_voran, discord zahl_zuerst
- 2026-11-04: instagram datum_voran, threads frage, discord beobachtung
- 2026-11-05: instagram zahl_zuerst, threads beobachtung, discord einordnung
- 2026-11-07: instagram pointe, threads einordnung, discord datum_voran, karussell zahl_zuerst

## Pruefung durch Claude (7.11.2026)
- Alle Selbsttests aus der Tabelle oben laufen auf dem Kopf des PR bei mir gruen.
- Korrigiert: Form 10 hiess "... that will ever exist already mined", der Satz hatte kein Verb. Jetzt steht dort "... is already mined" (`ig_zahl`), das Beispiel oben ist angepasst. Der Fehler stand schon auf main, mit dem Bauplan datum_voran faellt er mehr auf.
- Schon auf main, nicht geaendert: Form 3 (Countdown zum Reward Cut) nennt "counted by Kaspa Pulse". Der Termin kommt aber aus dem Emissionsplan, nach den Textregeln waere "computed" richtig. Das betrifft die Datumszeile im Bild und die Caption, also mehr als diesen PR.
- Discord: Der Satz "Share it first, it goes on X at 17:00." steht noch drin, weil die Wache ihn verlangt. Seit dem 7.11. postet niemand mehr per API auf @gokugalax (#285), und "Share it first" grenzt an Engagement-Koeder. Empfehlung: Satz und Pflicht in der Wache streichen.

## Offen fuer Ben

1. **Bitcoin-Vergleichszahl.** Annahme umgesetzt: eine Datei
   `data/bitcoin-massstab.json` mit `{"zahlen": [{"kennzahl", "datum",
   "satz"}]}`, Kennzahlen je Form in `tagesgrafik.BITCOIN_KENNZAHL`
   (reward_cut, blocks_8h, fee_share, hashrate, mined_pct). Genommen wird
   nur ein Eintrag, hoechstens 7 Tage alt, mit Datum im Satz, ohne
   Werturteil. Vorschlag: ein kleiner taeglicher Sammler (z. B. Bitcoin-
   Gebuehrenanteil und geschuerfter Anteil von einer oeffentlichen
   Bitcoin-API, oder Protokollwerte wie 144 Bloecke am Tag mit Stand-Datum).
   Welche Quelle und welche Kennzahlen, entscheidest du. Bis dahin faellt
   der Bauplan aus.
2. **Zahl des Tages.** `post_number_of_day.py` postet automatisch und
   oeffentlich nach Discord (und Telegram, X). Der Text kommt aus
   `number_of_day_data.py`, hat ein eigenes Regelwerk (u. a. Dollarwerte und
   Link in der Antwort) und ist identisch mit dem X-Text. Nicht umgebaut:
   das widerspricht in Teilen der Stimm-Regel ("keine Preise"), und der
   Koordinator arbeitet gerade an `x_post.py` und `number-of-day.yml`. Soll
   die Regel dort gelten?
3. **Weitere automatische oeffentliche Discord-Posts** gefunden:
   `entity_x_alert` und `reward_cut_alert` (Webhook DISCORD_WEBHOOK),
   `monday_briefing` und `weeklynumbers` (DISCORD_WEBHOOK_WEEKLY /
   _BRIEFING). Das sind Alarme und Wochentexte, nicht umgebaut. Gilt die
   Regel auch dort?
4. **"share it first, it goes on X at 17:00."** steht weiter im Discord-Text
   (die Wache verlangt ihn). Ob er nach dem Abschalten des X-Posts noch
   stimmt, kann ich nicht pruefen; "share it first" grenzt ausserdem an
   Engagement-Koeder. Streichen oder anpassen?
5. **Fragetakt.** "gelegentlich" ist als jeder 4. Tag fuer einen Kanal
   reihum umgesetzt, dazu Frage als Reserve, wenn sonst nichts frei ist.
