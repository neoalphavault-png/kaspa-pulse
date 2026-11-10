# Zcash-Zuhörer nach NU7, Endstand und Endkriterium (10.11.2026)

Ben hat am 10.11. drei Punkte beauftragt: prüfen, warum nach Lauf 13 kein Lauf 14 kam, den Endstand berichten und einen englischen Satz für den Forumsbeitrag am Mi 11.11. um 10:00 liefern. Frist Mi 11.11. 09:30. Grundlage ist `data/zcash-mainnet/lauscher-nu7/` auf `messung/zcash-mainnet`, Auswertung `zusammenfassung.json` aus Commit `3ba17a6` vom 8.11. 15:35 UTC. Ein Zuhörer an einem Ort, kein eigener Knoten. Keine Peer-Adressen.

<!-- discord -->
Zcash-Zuhörer nach NU7, Endstand: Ab NU7 sind 52 von 8.609 Kettenblöcken abgehängt (0,60 %). 40 davon haben einen geholten Kopf, alle mit Tiefe 1. 12 sind ohne Kopf, sie zählen mit, Begründung im Bericht. Lauf 13 hat die Kette absichtlich beendet, sobald der Kopfabruf gelang. Neu steuert eine feste Endzeit die Kette (PR, du merged). Satz für das Forum steht im Bericht. Bericht berichte/2026-11-10-zuhoerer-endstand.md
<!-- /discord -->

## 1. Warum nach Lauf 13 kein Lauf 14 kam

**Kein Fehler im Lauf 13.** Das Log von Lauf 13 (Actions-Lauf 42469506766) zeigt um 15:24:19 UTC die Zeile „naechster lauf: nein, 48 h nach nu7 erreicht“. Das Endkriterium war nie eine Laufzahl, sondern „48 h nach dem NU7-Block“. Um die Zeit des NU7-Blocks zu kennen, rief jeder Lauf kurz vor seinem Ende die Köpfe ab Höhe 3.543.355 ab.

| Lauf | Prüfung (UTC) | Kopfabruf | Entscheidung |
|---|---|---|---|
| 11 | 8.11. etwa 04:26 | ohne den NU7-Block | „ja, nu7 noch nicht erreicht“, Lauf 12 startet |
| 12 | 8.11. etwa 09:55 | ohne den NU7-Block | Lauf 13 startet |
| 13 | 8.11. 15:24:19 | mit dem NU7-Block | „nein, 48 h nach nu7 erreicht“, Ende |

**Der eigentliche Fehler** lag darin, dass das Ende am Netz hing. Nach Plan wäre um 48 h Schluss gewesen (8.11. 02:34 UTC). Weil der Kopfabruf zweimal scheiterte, lief die Kette bis 61 h. Hätte er auch in Lauf 13 versagt, wäre sie bis zur harten Grenze am 10.11. 00:00 UTC gelaufen. Genau das hatte ich am 8.11. in `berichte/2026-11-08-zcash-lauscher.md` (PR #289) angenommen. **Diese Annahme war falsch,** denn ich habe nicht damit gerechnet, dass ein späterer Abruf gelingt.

**Umstellung, PR #303 (`zcash/lauscher-endzeit`)** (Workflow, du merged nach deiner Prüfung):
- **Ein Eingang:** Statt `stunden_nach_nu7` und `spaetestens_utc` gibt es nur `ende_utc`, die feste Endzeit der Kette. Er ist Pflicht beim Start von Hand.
- **Kein Kopfabruf mehr:** Die Entscheidung trifft `scripts/zcash/lauscher_weiter.py` allein aus der Uhrzeit.
  - Der nächste Lauf startet 8 min vor dem Ende des laufenden.
  - Er wird so gekürzt, dass er genau bei `ende_utc` endet.
  - Bleiben weniger als 10 min, startet keiner mehr.
- **Selbsttest** `lauscher_weiter.py --selbsttest`, 6 von 6 bestanden. Er läuft im Workflow bei jedem Start im Schritt „eingaben“. Die Fälle:
  - Endzeit noch nicht erreicht, voller Lauf von 330 min
  - Endzeit noch nicht erreicht, letzter Lauf auf 100 min gekürzt
  - weniger als 10 min übrig, kein Lauf
  - Endzeit vorbei
  - Testlauf mit Endzeit im Jahr 2000
  - falsches Format bricht ab
- **Fehlerfall:** Scheitert die Entscheidung trotzdem, startet kein weiterer Lauf. Die Rohdaten des laufenden werden wie bisher gesichert.

Für die NU7-Messreihe ändert das nichts mehr, sie ist abgeschlossen. Es gilt für die nächste Messreihe mit diesem Workflow.

## 2. Endstand

**Fenster:**
- **Gesamt:** 5.11. 17:02:19 bis 8.11. 15:30:05 UTC, 13 Läufe ohne Lücke (jeder Lauf begann 4 bis 7 min vor dem Ende des vorigen). Von der ersten bis zur letzten Ankündigung sind es 4.217,2 min.
- **Ab NU7:** von der Kopfzeit des NU7-Blocks (Höhe 3.543.405) am 6.11. um 02:34:02 UTC bis 8.11. 15:30:05 UTC, also 60 h 56 min.

| | Kettenblöcke im Fenster | davon bei uns angekündigt | abgehängt | Anteil |
|---|---:|---:|---:|---:|
| vor NU7 | 453 | 453 | 0 | 0 % |
| ab NU7, Endstand | 8.609 | 8.602 | 52 | 0,601 % |
| ab NU7, nur Abgehängte mit Kopf | 8.609 | 8.602 | 40 | 0,463 % |

Anteil wie bisher: abgehängt / (angekündigte Kettenblöcke + abgehängt), also 52 / 8.654.

**Ab NU7 je 6 h** (die letzten 12 h 56 min ab Stunde 48 fallen in keine der Spalten, darin liegen 4 Abgehängte):

| Stunden nach NU7 | 0 bis 6 | 6 bis 12 | 12 bis 18 | 18 bis 24 | 24 bis 30 | 30 bis 36 | 36 bis 42 | 42 bis 48 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kettenblöcke | 706 | 855 | 861 | 847 | 885 | 855 | 878 | 847 |
| abgehängt | 8 | 7 | 9 | 3 | 6 | 6 | 6 | 3 |

**Tiefe:** Die 40 Abgehängten mit Kopf hängen alle direkt an einem Kettenblock, also Tiefe 1 (40 Zweige, größte Tiefe 1).

**Nachgerechnet:** Ich habe `lauscher_auswertung.py` heute mit denselben 13 Läufen gegen unsere eigene Kopfkette (`data/zcash-mainnet/koepfe.csv.gz`) neu laufen lassen. Ergebnis: 52 abgehängt, 12 ohne Kopf, 8.602 von 8.609. Das stimmt mit `3ba17a6` überein.

### Die 12 Abgehängten ohne Kopf

„Ohne Kopf“ heißt: Der Hash wurde uns angekündigt, er steht nicht in der Kette, und der Zuhörer hat den Kopf nicht bekommen. Höhe, Vorgänger und Tiefe sind deshalb unbekannt.

| erste Ankündigung (UTC) | Hash, Anfang | führende Null-Hexziffern | Peers | Software |
|---|---|---:|---:|---|
| 6.11. 04:47:16 | `0000000000f119a4` | 10 | 5 | Zebra 7.0.0, Zakura 1.7.0, Zakura 1.8.0-modified |
| 6.11. 05:30:49 | `0000000000d1e586` | 10 | 1 | Zebra 7.0.0 |
| 6.11. 15:12:49 | `0000000000a9e5d5` | 10 | 1 | Zebra 7.0.0 |
| 6.11. 15:38:51 | `0000000001241b4e` | 9 | 1 | Zebra 7.0.0 |
| 6.11. 17:59:43 | `0000000000cb0ef3` | 10 | 6 | Zebra 7.0.0, Zakura 1.8.3 |
| 6.11. 18:41:42 | `00000000013eccfd` | 9 | 2 | Zebra 7.0.0 |
| 6.11. 21:13:47 | `000000000011011f` | 10 | 2 | Zebra 7.0.0 |
| 7.11. 03:11:28 | `0000000000f9e874` | 10 | 2 | Zebra 7.0.0, Zebra 7.0.0-modified |
| 7.11. 04:22:10 | `00000000009a5a97` | 10 | 1 | Zebra 7.0.0 |
| 7.11. 10:33:59 | `0000000000450d58` | 10 | 4 | Zebra 7.0.0 |
| 7.11. 12:07:58 | `00000000010d44e6` | 9 | 2 | Zebra 7.0.0 |
| 7.11. 14:46:37 | `0000000000db9b2f` | 10 | 2 | Zebra 7.0.0 |

**Sie zählen als verwaist, also in den 52.** Begründung:
1. **Sie stehen nicht in der Kette.** Unsere Kopfkette reicht weit über ihre Ankündigungszeit hinaus.
2. **Gemeldet hat sie NU7-fähige Software.** Bei allen 12 war mindestens ein Peer mit Zebra 7.0.0 dabei. Ein Rest der alten Kette vor NU7 ist damit unwahrscheinlich.
3. **Die Hashes sehen aus wie Blöcke.** Alle haben 9 bis 10 führende Null-Hexziffern wie jeder Kettenblock im Fenster (mindestens 9). Ein beliebiger Hash hätte das mit einer Wahrscheinlichkeit von etwa 1 zu 2³⁶.

**Was wir nicht wissen:** Ohne Kopf können wir weder die Arbeit noch die Höhe prüfen. Deshalb nennen wir beide Zahlen:
- 52 als Endstand
- 40 als untere Grenze, nur mit geprüftem Kopf

Ihre Tiefe ist unbekannt, die Aussage „Tiefe 1“ gilt nur für die 40.

### Zwischenstand vom 8.11.

**49 von 7.047 (0,69 %) war ein Zwischenstand.** Er galt nach Lauf 11, Auswertung `0e9a7e05` vom 8.11. 04:43 UTC, Fenster ab NU7 bis etwa 50 h. Er steht in `berichte/2026-11-08-zcash-lauscher.md` und ist durch den Endstand oben ersetzt. Die Läufe 12 und 13 kamen danach hinzu.

## 3. Satz für den Forumsbeitrag am Mi 11.11. um 10:00

> From 6 Nov 02:34 utc, the header time of the NU7 activation block, to 8 Nov 15:30 utc, our listener counted 52 announced blocks that did not end up in the chain, against 8,602 chain blocks announced to it, a share of 0.60 %, and each of the 40 for which we fetched the header was a single block replacing the tip.

Alle Zahlen sind counted und kommen je einmal vor. Kein Doppelpunkt im Fließtext, kein Gedankenstrich. Kürzer, falls nötig:

> From 6 Nov 02:34 utc to 8 Nov 15:30 utc our listener counted 52 orphaned blocks against 8,602 chain blocks, a share of 0.60 %.

## Offene Fragen an Ben

1. Willst du im Forum die 52 nennen, die 40 oder beide? Mein Vorschlag ist der erste Satz, denn er nennt beide.

## Was Ben tun muss

1. PR #303 (`zcash/lauscher-endzeit`) prüfen und mergen. Er ändert eine Workflow-Datei, deshalb mergst du.
2. Am Mi 11.11. um 10:00 den Forumsbeitrag mit dem Satz oben posten.
