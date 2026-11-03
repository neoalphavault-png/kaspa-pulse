# KCC-20-Zählung, Stichzeit Di 3.11.2026 12:00 UTC

Bericht für Ben zum Auftrag vom 2.11.2026, Frist Di 3.11. 19:30 Berlin. Zugesagt an Kastle am 28.10. als "next KCC-20 count on Nov 2". Unsere Zahlen tragen counted, fremde Zahlen ihre Quelle.

## Ergebnis

| | 26.10. 12:00 UTC | 3.11. 12:00 UTC | Veränderung |
|---|---|---|---|
| KCC-20-Tokens, counted | 240 | 313 | +73 |
| Eindeutige Halter-Adressen, counted | 857 | 1,406 | +549 |
| Halter-Outputs, counted | 2,646 | 4,021 | +1,375 |
| Tokens mit gleichem Ticker wie bei KRC-20, source kasplex | 62 | 75 | +13 |
| Transfers, counted | 4,560 seit 22.10. 05:53 UTC | 737 seit 1.11. 06:23 UTC | nicht vergleichbar, siehe unten |

- **Neue Tokens seit 26.10.:** 73, alle mit Genesis zwischen 26.10. 12:24 und 3.11. 09:33 UTC. 62 davon tragen einen Ticker, 13 einen Ticker, den es auch bei KRC-20 gibt (source kasplex). Zusammen haben die neuen Tokens 738 Halter je Token gezählt.
- **Kein Token ist verschwunden:** Alle 240 Tokens vom 26.10. haben am 3.11. noch mindestens einen lebenden Output.
- **Gleicher Ticker heißt nicht derselbe Token.** Wie am 26.10. ist das nur ein Abgleich der Namen.

## Transfers seit 26.10. 12:00 UTC

Diese Zahl lässt sich nicht ganz aus dem eigenen Knoten zählen. Unser Knoten hält nur rund 30 bis 42 Stunden. Das eigene Fenster vom 26.10. endete um 12:17 UTC, die neuen Läufe reichen bis 1.11. 06:23 UTC zurück. Dazwischen liegt eine Lücke, die kein eigener Knoten mehr lesen kann.

| | KCC-20-Transfers | Quelle |
|---|---|---|
| Im lückenlosen eigenen Fenster 1.11. 06:23 bis 3.11. 12:00 UTC | 737 | counted |
| Aus eigenen Knotenfenstern seit 26.10. 12:00 UTC, bis zur Kettenspitze 3.11. 12:17 UTC | 741 | counted, enthält die 737, dazu 4 vom 26.10. zwischen 12:00 und 12:17 UTC oder nach der Stichzeit |
| In der Lücke, nur von api.kaspa.org | 2,631 | source api.kaspa.org, unvollständig |

Die 2,631 sind nur die Transfers, die wir als Vorfahren lebender Outputs von api.kaspa.org geholt haben, um ihren Zustand zu beweisen. Transfers in der Lücke, deren Outputs schon wieder ausgegeben sind und die kein lebender Output braucht, fehlen darin. Eine Summe "seit 26.10." ist deshalb keine gezählte Zahl. Auf der Seite steht nur die 737 mit ihrem Fenster.

## Tokens mit den meisten Haltern

| # | Ticker | Covenant-ID | Halter | Halter-Outputs | Transfers counted | Halter am 26.10. |
|---|---|---|---|---|---|---|
| 1 | NACHO | `41d44970ba` | 330 | 523 | 252 | neu |
| 2 | THEN | `d8c4356d20` | 259 | 445 | 21 | 234 |
| 3 | GUZA | `3cb7bd371e` | 245 | 490 | 21 | 200 |
| 4 | TEK | `cecb547d3a` | 120 | 204 | 68 | 88 |
| 5 | DAGAS | `244cd20dac` | 95 | 128 | 19 | 65 |
| 6 | BTE | `efcf006e57` | 86 | 146 | 21 | 80 |
| 7 | KB | `b75a6e90f5` | 74 | 154 | 13 | 46 |
| 8 | ROCKET | `7cf4b45ebf` | 64 | 115 | 2 | 64 |
| 9 | POKEMONKAS | `592404037e` | 58 | 64 | 5 | neu |
| 10 | BYE | `c4556dc2ee` | 47 | 67 | 34 | neu |

Transfers counted je Token seit 1.11. 06:23 UTC. Eine Tx, die zwei Tokens berührt, zählt bei beiden, deshalb ergibt die Summe je Token 743 statt 737.

## Hinweis zu NACHO und zur Migration

- Der neue KCC-20-Token mit Ticker NACHO (Covenant-ID `41d44970ba…`) hat seine Genesis am 27.10.2026 17:57 UTC. Er ist mit 330 Haltern jetzt der größte KCC-20-Token. Den Ticker NACHO gibt es auch bei KRC-20 (source kasplex).
- Seine Metadaten (KCC-23-Vorbereitung) nennen Name, Ticker, Symbol, Bild und 6 Dezimalstellen, aber keinen Migrationsweg, keinen Snapshot und keinen KRC-20-Bezug. Damit ist er nach der Regel vom 28.10. keine zählbare Migration. Ob er zum geplanten "turnstile" gehört, belegt nichts auf der Kette.
- Korrektur zum Migrationsbericht (#217): Der Satz "Ein NACHO- oder KAT-Token gibt es unter den 240 nicht" stimmte für die Stichzeit 26.10. Am Tag der Prüfung (29.10.) gab es den NACHO-Token schon. Das Ergebnis ROT bleibt, weil kein Kennzeichen auf der Kette eine Migration ausweist. Ein KAT-Token ist auch am 3.11. nicht dabei.

## Wie gezählt wurde

- **Wie am 26.10.:** eigener Mainnet-Knoten (rusty-kaspa v2.1.0) im Runner, frisch synchronisiert und gestoppt. `kcc20/werkzeug` liest den UTXO-Bestand zur Stichzeit mit Zweitprüfung. Jeder Halter-Output zählt nur, wenn sein Zustand per Blake2b-Hash gegen die KCC-20-Konformitätsvektoren bewiesen ist.
- **Hauptlauf** [41595802303](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41595802303):
  - Stichzeit 3.11. 12:00:00 UTC
  - Pruning-Punkt 1.11. 18:25 UTC, Kettenspitze 12:17 UTC
  - Zweitprüfung identisch, 0 Fehler
  - 209,790 Kettenblöcke, keiner ohne Daten
- **Vorlauf** [41506728241](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41506728241): Stichzeit 2.11. 12:00 UTC. Er verlängert das eigene Fenster bis 1.11. 06:23 UTC zurück.
  - Stand am 2.11.: 307 Tokens, 1,309 Halter.
- **Frühere Läufe:** Ihre Tx-Listen sind mit eingelesen: 39967185904, 40087545641, 40186478752, 40308051997.
- **Nicht bewiesen:** 124 Outputs unter 124 Tokens, zusammen 1,071 KAS, ohne bewiesenen Zustand. Vermutlich ist das je Token der Mint-Ausgang, wie schon am 26.10. Diese zählen nicht als Halter.
- **Andere Covenants:** 15,768 lebende Covenant-Outputs gehören nicht zum finalen KCC-20, sie gehören zu 1,640 anderen Covenant-IDs. Sie sind nicht gezählt.

## Dateien

- `kcc20/ergebnis/kcc20-tokens-2026-11-03.csv`: 313 Tokens im Format vom 26.10. Keine Adressen.
- `data/kcc20-stand.json` auf den neuen Stand, `kcc-20.html` daraus neu gebaut: Kurz-Fakt, Zahlenblock, Tabelle, Migrationsabsatz, FAQ und Dataset-Link auf die neue CSV.
- **Zwei Skripte geändert, keine Workflows:**
  - `scripts/seo_seiten.py` nimmt den CSV-Pfad jetzt aus `data/kcc20-stand.json`.
  - Der Selbsttest in `scripts/seiten_zahlen.py` prüft gegen die Werte im Stand statt gegen die festen Zahlen vom 26.10.
- **Rohsummen** der Läufe liegen auf `fix/kcc20-zaehlung` unter `kcc20/laeufe/`.

## Auf dem Lauf-Branch, nicht in diesem PR

- `fix/kcc20-zaehlung` war nach dem letzten Merge gelöscht. Ich habe ihn am 2.11. aus main neu angelegt.
- **Neuer Job `sichern` im Workflow `kcc20-zaehlung.yml`, nur auf diesem Branch:** Er legt Summen und CSV ohne Adressen und ohne Tx-IDs auf den Branch. Grund: Die Artefakte lassen sich aus meiner Umgebung nicht laden.
  - Workflow-Änderungen prüft Claude, Ben merged. Ob der Job nach main soll, entscheidest du.
- Im Vorlauf stand in `kcc20-namen.csv` noch die Spalte mit den Genesis-Tx-IDs der Tokens. Sie ist seit a7241f2 entfernt, in der Historie von `fix/kcc20-zaehlung` (f33ff93) aber noch enthalten.

## Offene Fragen an Ben

1. Soll Kastle die Zahlen direkt bekommen (Tokens, Halter, Transfers mit Fenster)? Ein Satz ginge so: "313 KCC-20 tokens with 1,406 unique holders at 3 November 2026, 12:00 UTC, counted on our own node."
2. Soll der Job `sichern` nach main?
3. Sollen wir die Zählung künftig regelmäßig laufen lassen? Dann gibt es keine Lücke bei den Transfers mehr. Täglich wäre lückenlos, mindestens alle 30 Stunden.

## Was Ben tun muss

- Nichts mergen: Ich merge diesen PR selbst, wenn die Checks grün sind. Er enthält keinen Workflow, kein deploy und keine c2-Datei.
- Die drei Fragen oben beantworten.
