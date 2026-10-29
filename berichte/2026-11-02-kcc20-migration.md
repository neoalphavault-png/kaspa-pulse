# KRC-20 zu KCC-20, Migrationszählung je Token, Schritt 0

Bericht für Ben zum Auftrag vom 28.10.2026, Frist Mo 2.11. 18:00 Berlin. Schritt 0 (Machbarkeit) am Do 29.10.2026, 21:00 bis 22:00 UTC, nach dem STP-Lauf.

## Ergebnis: ROT

Am 29.10.2026 lässt sich keine Migration von KRC-20 zu KCC-20 zählen. Es gibt keinen Migrationsweg, der auf dem Mainnet läuft und in einer offiziellen Quelle beschrieben ist. Auf der Kette gibt es nichts, was ein KCC-20-Token als Migration eines KRC-20-Tokens ausweist. Nach dem Auftrag ist hier Schluss: keine Zählung, keine Schätzung, keine CSV, kein Post-Entwurf.

## 1. Scope-Regel

Gezählt würde je Token die KCC-20-Menge, die nachweislich aus einer Migration eines bestimmten KRC-20-Tokens entstanden ist, und nur dann, wenn ein offizieller Migrationsweg und ein Kennzeichen auf der Kette diese Zuordnung belegen.

## 2. Wie die Migration technisch abläuft, laut Quellen

| Projekt | Was die Quelle sagt | Quelle, Datum |
|---|---|---|
| KaspaCom | Werkzeug für "snapshot" und "claim": Bestände werden aus einem Indexer übernommen, auf der KCC-20-Seite entstehen Reserven und Controller, die Halter holen sich ihren Teil per Claim. Von Burn oder Sperre auf der KRC-20-Seite steht dort nichts. Stand ist Entwurf und ausdrücklich abgeschaltet: "KCC20_MIGRATIONS_SIGNERLESS_START_ENABLED remains false by default", "No transaction was signed or broadcast. The feature remains disabled." | [KASPACOM/kcc20-tx-builder](https://github.com/KASPACOM/kcc20-tx-builder), [PR #4](https://github.com/KASPACOM/kcc20-tx-builder/pull/4) vom 9. und 10.10.2026, [docs/snapshot-start.md](https://github.com/KASPACOM/kcc20-tx-builder/blob/main/docs/snapshot-start.md). Gelesen am 29.10.2026. |
| Nacho the Kat | Geplant ist laut einem Beteiligten ein "turnstile": NACHO aus KRC-20, Kasplex EVM und Igra EVM geht in ein Migrationswerkzeug, heraus kommt KCC-20. Kein Snapshot mit Airdrop. Ein Datum, ein Start oder ein Kennzeichen auf der Kette ist nicht genannt. Der Schreiber sagt selbst, niemand "owns decisions". Das ist ein Kommentar, keine Ankündigung des Projekts. | [kasplex/go-krc20d Issue #1](https://github.com/kasplex/go-krc20d/issues/1), Kommentar vom 23.10.2026. Gelesen am 29.10.2026. |
| KAT | Keine Quelle zu einer KRC-20-Migration gefunden. | |
| Igra | Keine Quelle zu einer KRC-20-Migration gefunden. Im KaspaCom-PR erscheint Igra nur als Datenquelle für Bestände. | |
| Standard | Die KCC-Spezifikationen (KCC-1, KCC-2, KCC-20, KCC-23) enthalten keine Regel für eine Migration von KRC-20. | Repo kaspanet/kccs, Stand 1ed87ae vom 21.10.2026. |

Weitere Treffer kamen nur aus Nachrichtenseiten und Posts auf X: eine einseitige Brücke von KaspaCom, eine Discord-Abstimmung von NACHO über ein Migrationsfenster, ein Versuch auf Testnet-10 mit einem einzigen erfundenen Halter. Diese Seiten waren entweder nicht lesbar oder sind keine offizielle Quelle. Ich nehme sie deshalb nicht als Beleg.

## 3. Sind beide Seiten je Token erkennbar?

- **KCC-20-Seite, aus unserem Knoten:** Unsere Zählung vom 26.10. 12:00 UTC hat 240 Tokens. Bei keinem nennen Genesis-Payload oder KCC-23-Metadaten ein KRC-20-Token als Herkunft, einen Snapshot oder eine Migration. Nur ein Token nennt überhaupt einen Weg, `bridge_covenant_id` und `eth_vault`. Das ist eine Brücke von Ethereum, keine KRC-20-Migration. Ein NACHO- oder KAT-Token gibt es unter den 240 nicht.
- **Gleicher Ticker:** 62 KCC-20-Tokens tragen einen Ticker, den es auch bei KRC-20 gibt (source kasplex). Ein gleicher Ticker heißt nicht derselbe Token, das belegt keine Migration.
- **KRC-20-Seite:** Gesamtmengen gibt es aus dem Indexer (source kasplex). Weil der Weg kein Burn und keine Sperre an einer bekannten Stelle ist, lässt sich aber keine "migrierte Menge" auf der KRC-20-Seite messen.

Damit ist keine Seite je Token zählbar: GELB scheidet auch aus.

## 4. Was GRÜN möglich machen würde

1. Ein Projekt startet seine Migration auf dem Mainnet, mit offizieller Beschreibung.
2. Der Weg hinterlässt ein Kennzeichen auf der Kette, das wir auf unserem Knoten lesen können. Zum Beispiel ein Feld in den KCC-23-Metadaten oder im Genesis-Payload, das den KRC-20-Ticker und den Snapshot oder das Werkzeug nennt. Oder eine bekannte Sperradresse beziehungsweise ein Burn auf der KRC-20-Seite.

Für die Zählung ist schon alles da: Unsere KCC-20-Zählung liest Genesis-Payload und KCC-23-Metadaten (`scripts/kcc20_namen.py`, Feld `weg_hinweis`), und die Stichzeit mit DAA-Score ist erprobt.

## Offene Fragen an Ben

1. Soll ich am Mo 2.11. um 07:00 UTC Schritt 0 noch einmal kurz prüfen, ob bis dahin eine Migration live gegangen ist? Dann bliebe bis zur Stichzeit 12:00 UTC Zeit für eine Zählung.
2. Hat Kastle (Leo) einen Datenwunsch genannt?

## Was Ben tun muss

- Frage 1 beantworten.
- Falls ein Projekt dir einen Migrationsweg nennt, mir die offizielle Quelle geben.
