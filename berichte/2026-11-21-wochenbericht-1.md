# Erster Wochenbericht Zcash und Bitcoin Cash, Entwurf und Zahlen (Auftrag Ben 20.11.2026, Frist Sa 21.11. 16:00 Berlin)

**Kopf:** Zahlen aus unseren Datenbranches, Seite als PR in pulsehawk-site (pulsehawk-site#105, Ben merged), Forums- und X-Texte unten, Ben postet am So 22.11. Dazu die Antwort zum roten Secret-Scan (Punkt 2), zu c2 (Punkt 3) und der Plan für `tools/week_check.py` (Punkt 4).

<!-- discord -->
Erster Wochenbericht, Entwurf und Zahlen liegen bereit, die Seite liegt als PR in pulsehawk-site bei Ben. Zcash zählt 120 verwaiste Blöcke neben 28.665 Kettenblöcken, Zuhörer ohne Lücke. BCH Chipnet braucht für 6 Bestätigungen üblich 5 min 56 s, für 12 üblich 11 min 53 s, nach Ankunft beim Zuhörer. Der rote Secret-Scan vom 18.11. war kein Fund, der Bereich ließ sich nach dem Löschen des Branch nicht mehr auflösen. Bericht berichte/2026-11-21-wochenbericht-1.md
<!-- /discord -->

## Bens Antworten (20.11.), umgesetzt

- **BCH:** Wartezeit nach Ankunft beim Zuhörer, Kopfzeit als Zusatz.
- **B1 und B2** (Knoten je Client, Gebühren) werden nicht gebaut und gehen auf den Parkplatz. Der kleine Test zur Gebührenfrage ist beendet.
- **`methods/koepfe-roh`:** Ben löscht ihn in der Oberfläche.
- **Zcash:** Teilwoche mit genanntem Fenster, vom Start der Zuhörer-Serie bis zur Stichzeit des Samstagslaufs. Die Basis der Rate nach NU7 bleibt 52 von 8.609 (Serie NU7).
- **Verbindungen je Client:** Sie bleiben draußen.

## a) Zahlentabelle

Der Samstagslauf wurde von Hand gestartet (workflow_dispatch, keine Workflow-Änderung), weil der geplante Lauf in diesem Konto Stunden zu spät kommt. Die Wartezeit für k Bestätigungen ist die Zeit von einem Block, bis k weitere Blöcke gefolgt sind. Üblich ist der Median, 9 von 10 das 90. Perzentil, 99 von 100 das 99.

| Zahl | Wert | Art | Datei | Commit | Stichzeit oder Fenster (UTC) |
|---|---|---|---|---|---|
| Zcash, Kettenblöcke beim Zuhörer | 28.665 | counted | `data/zcash-mainnet/lauscher-dauer/zusammenfassung.json` | `135fbdac` | 2026-11-12T21:36:48Z bis 2026-11-21T04:27:43Z |
| Zcash, verwaiste Blöcke (untere Grenze) | 120 (0,42 %), davon 13 ohne Kopf, Tiefe höchstens 1 | counted | `data/zcash-mainnet/lauscher-dauer/zusammenfassung.json` | `135fbdac` | wie oben |
| Zcash, Blockabstände | 28.970, Median 17 s, Mittel 24,97 s | counted | `data/zcash-mainnet/koepfe.csv.gz` | `fe7e077d` | 2026-11-12 21:36:48 bis 2026-11-21 06:34:04 UTC, Abruf 2026-11-21T06:34:04Z |
| Zcash, Anteil über 75 s | 4,73 % | counted | `data/zcash-mainnet/koepfe.csv.gz` | `fe7e077d` | wie oben |
| Zcash, Wartezeit 1 Bestätigung, üblich / 9 von 10 | 17 s / 57 s | counted | `data/zcash-mainnet/koepfe.csv.gz` | `fe7e077d` | wie oben |
| Zcash, Wartezeit 3 Bestätigungen, üblich / 9 von 10 | 1 min 7 s / 2 min 12 s | counted | `data/zcash-mainnet/koepfe.csv.gz` | `fe7e077d` | wie oben |
| Zcash, Wartezeit 6 Bestätigungen, üblich / 9 von 10 | 2 min 21 s / 3 min 51 s | counted | `data/zcash-mainnet/koepfe.csv.gz` | `fe7e077d` | wie oben |
| Zcash, ideale 25-s-Kette, 1 Bestätigung | 17 s / 58 s | computed | `Erlang, Mittel 25 s` | `-` | - |
| Zcash, ideale 25-s-Kette, 3 Bestätigungen | 1 min 7 s / 2 min 13 s | computed | `Erlang, Mittel 25 s` | `-` | - |
| Zcash, ideale 25-s-Kette, 6 Bestätigungen | 2 min 22 s / 3 min 52 s | computed | `Erlang, Mittel 25 s` | `-` | - |
| BCH Chipnet, Aktivierungshöhe | 332.451 | counted | `data/bch-chipnet/koepfe.csv.gz` | `4c1981ff` | MTP-Regel, Abruf 2026-11-21T06:33:45Z |
| BCH Chipnet, Abstände seit Aktivierung | 8.310, Median 52 s, Mittel 59,77 s | counted | `data/bch-chipnet/koepfe.csv.gz` | `4c1981ff` | 2026-11-15 12:33:16 bis 2026-11-21 06:31:50 UTC |
| BCH Chipnet, Anteil Difficulty 1 | 25,9 % (2.152 Blöcke) | counted | `data/bch-chipnet/koepfe.csv.gz` | `4c1981ff` | wie oben |
| BCH Chipnet, Wartezeit 1 Bestätigung nach Ankunft, üblich / 9 von 10 / 99 von 100 | 52 s / 2 min 2 s / 2 min 8 s (Kopfzeit 52 s / 2 min 2 s) | counted | `data/bch-chipnet/lauscher/bloecke.csv` | `8418b292` | 2026-11-17 19:46:11 bis 2026-11-21 04:25:41 UTC |
| BCH Chipnet, Wartezeit 3 Bestätigungen nach Ankunft, üblich / 9 von 10 / 99 von 100 | 2 min 56 s / 4 min 38 s / 6 min 6 s (Kopfzeit 2 min 56 s / 4 min 44 s) | counted | `data/bch-chipnet/lauscher/bloecke.csv` | `8418b292` | 2026-11-17 19:46:11 bis 2026-11-21 04:25:41 UTC |
| BCH Chipnet, Wartezeit 6 Bestätigungen nach Ankunft, üblich / 9 von 10 / 99 von 100 | 5 min 56 s / 8 min 29 s / 10 min 34 s (Kopfzeit 5 min 58 s / 8 min 34 s) | counted | `data/bch-chipnet/lauscher/bloecke.csv` | `8418b292` | 2026-11-17 19:46:11 bis 2026-11-21 04:25:41 UTC |
| BCH Chipnet, Wartezeit 12 Bestätigungen nach Ankunft, üblich / 9 von 10 / 99 von 100 | 11 min 53 s / 15 min 44 s / 19 min 14 s (Kopfzeit 11 min 55 s / 15 min 50 s) | counted | `data/bch-chipnet/lauscher/bloecke.csv` | `8418b292` | 2026-11-17 19:46:11 bis 2026-11-21 04:25:41 UTC |
| BCH Mainnet, 1 Bestätigung, üblich / 9 von 10 / 99 von 100 | 6 min 56 s / 23 min 2 s / 46 min 3 s | computed | `Erlang, Mittel 600 s` | `-` | - |
| BCH Mainnet, 3 Bestätigungen, üblich / 9 von 10 / 99 von 100 | 26 min 44 s / 53 min 13 s / 1 h 24 min 4 s | computed | `Erlang, Mittel 600 s` | `-` | - |
| BCH Mainnet, 6 Bestätigungen, üblich / 9 von 10 / 99 von 100 | 56 min 42 s / 1 h 32 min 45 s / 2 h 11 min 5 s | computed | `Erlang, Mittel 600 s` | `-` | - |
| BCH Mainnet, 12 Bestätigungen, üblich / 9 von 10 / 99 von 100 | 1 h 56 min 41 s / 2 h 45 min 59 s / 3 h 34 min 54 s | computed | `Erlang, Mittel 600 s` | `-` | - |

**Zcash:** Die Blockabstände laufen bis zur Stichzeit 2026-11-21 06:34:04 UTC. Der Zuhörer ist bis zum Ende seines letzten fertigen Laufs ausgewertet, 2026-11-21T04:27:43Z.

**BCH Mainnet:** Mainnet-Köpfe gibt es ohne neuen Bau nicht. Unser Header-Client hat kein Profil für das BCH-Mainnet, und es läuft kein Mainnet-Zuhörer. Die Mainnet-Werte sind deshalb computed aus der 10-Minuten-Regel (Erlang mit Mittel 600 s).
**Vorschlag für KW48:** im Header-Client in pulsehawk/methods ein Profil `bch-mainnet` mit Fixpunkt und BCHN-Checkpoints anlegen, dann die Wartezeiten nach Kopfzeit zählen. Das ist ein kleiner PR, Ben merged.

## Lücken der Zuhörer (UTC)

- **Zcash, Serie „dauer“ (37 Läufe):** keine, die Läufe überlappen
- **BCH Chipnet (15 Läufe):** keine, die Läufe überlappen

## b) Seite auf pulsehawk.io

pulsehawk-site#105:
- `/weekly/2026-11-22`, gebaut aus `data/weekly/2026-11-22.json`. Diese Datei schreibt der Rechenlauf, keine getippten Zahlen.
- Auf `/reports/` ein neuer Abschnitt „Which weekly reports have we published?“.
- Die Textprüfung ist bestanden. Ben merged.

## c) Forum Zcash 59124 (zcash_59124, 112 woerter, 550 zeichen)

> Our weekly count, as promised. From the start of our current listener series at 12 Nov 21:36 utc to 21 Nov 04:27 utc our listener counted 120 orphaned blocks next to 28,665 chain blocks, one vantage point, so read it as a lower bound. Our headers to 21 Nov 06:34 utc give a median block interval of 17 s, and 4.73 % of intervals ran longer than 75 s. Three blocks usually took 1 min 7 s, six blocks 2 min 21 s, and 9 of 10 times six blocks came within 3 min 51 s. @dismad would a weekly line like this help you plan, or is another number more useful?

## d) Forum BCH 2173 (bch_2173, 112 woerter, 553 zeichen)

> Waiting times on chipnet with one minute blocks, from the first sighting of each block at our listener, 17 Nov 19:46 utc to 21 Nov 04:25 utc, blocks 335,748 to 340,629. One confirmation usually took 52 s, three 2 min 56 s, six 5 min 56 s, and twelve 11 min 53 s. Nine of ten times six blocks arrived within 8 min 29 s, and 99 of 100 times within 10 min 34 s. Of the blocks since the activation at 332,451, 25.9 % carry difficulty 1, and they are part of every wait. For mainnet at 600 s, six blocks would usually take 56 min 42 s, computed, not counted.

## e) X-Post @pulsehawkio (x, 48 woerter, 245 zeichen)

> Bitcoin Cash chipnet with one minute blocks. We counted the wait for six confirmations at our listener, usually 5 min 56 s, and 9 of 10 times within 8 min 29 s. Wallets and pools, which wait do you show your users before you call a payment done?

## Punkt 2, roter Secret-Scan vom 18.11.

- **Lauf:** „secret scan“ 44383308855, Ereignis pull_request, 18.11. 19:43:54 UTC. Grün waren „selbsttest“ und „alle dateien im stand“, rot war „neue commits“.
- **Gemeldet hat er keine Datei und keine Zeile.** Der Schritt brach mit „Invalid revision range“ ab, weil git den Bereich Basis..Spitze (`bd26cc2..7bf2d82`) im Checkout nicht auflösen konnte.
- **Ursache:** Ich hatte #331 um 19:42:27 UTC gemergt und den Branch gleich gelöscht. Der Lauf startete danach und fand die PR-Spitze nicht mehr.
- **Mein Fehler dabei:** Ich habe gemergt, bevor dieser Scan überhaupt angelaufen war. Bei meiner Prüfung standen nur die drei anderen Checks da, grün.
- **Nachgeprüft:** `secret_scan.py --bereich bd26cc2..7bf2d82` lokal, 1 Commit, nichts gefunden. Der Push-Lauf auf dem Branch (19:40:38 UTC) war grün. In der Historie steht keine Stelle.
- **Ab jetzt:** Ich warte vor einem Selbst-Merge, bis auch der Scan des pull_request-Ereignisses grün ist.

## Punkt 3, c2

- Keiner der beiden Zuhörer dieses Berichts läuft auf c2, beide laufen auf GitHub.
- Der c2-Zuhörer war ein Tempnet-Zuhörer. Sein letzter Lauf war am 15.11. um 06:37 UTC.
- Ein Neustart von c2 erzeugt deshalb keine Lücke in diesem Bericht. Kommt die Uhrzeit, prüfe ich trotzdem, ob ein Lauf in dem Fenster fehlt.

## Punkt 4

`tools/week_check.py` kommt bis Mo 30.11. als PR ins Methoden-Repo.

## PR-Nummern

- pulsehawk-site#105, Wochenseite, Ben merged
- dieser Bericht

## Fragen

1. Soll ich das Profil `bch-mainnet` für den Header-Client in KW48 bauen (Vorschlag oben)?

## Was Ben tun muss

- pulsehawk-site#105 mergen, am besten am So 22.11. vor dem Posten.
- Die Texte c, d und e posten.
- Frage 1 beantworten.
