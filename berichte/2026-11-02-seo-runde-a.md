# Bericht SEO-Runde v2, Priorität A (Frist Mo 2.11.2026 18:00 Berlin)

Auftrag von Ben vom 27.10.2026 abends, auf Grundlage der Search Console. Er ersetzt den SEO-Auftrag vom Nachmittag. Dessen Stand ist mit #164 schon live und steckt in den Punkten unten.

## Was gemacht wurde
1. **kaspa-halving.html**
   - **Kurz-Fakt unter der H1:** „Next reward step on 4 November 2026 around 13:45 UTC, block reward from 2.0602 to 1.9445 KAS per block, computed from the emission schedule“.
     - Das Datum steht fest im Text, ohne Countdown.
     - Die Zahlen kommen aus dem Emissionsplan in `weekly_facts`, Stufe 4 nach dem Anker.
   - **FAQ „When is the next Kaspa halving?“:** ersetzt die alte Frage mit „Is there a countdown?“.
   - **FAQ „Does Kaspa have a halving?“:** beantwortet jetzt mit Datum und KAS je Block, computed.
   - **Nach dem 4.11.:** `seiten_zahlen.py` rechnet die nächste Stufe jeden Tag neu. Ab der Stufe steht dort der 5 December 2026 mit 1.9445 auf 1.8354 KAS, das prüft der Selbsttest. Ändert sich der Text, zieht `seo_seiten.py` dateModified und lastmod nach.
   - **Keine eigene Reward-Cut-Seite.**
2. **Drei Zielseiten**
   - **kaspa-hashrate.html:** Title und H1 schon seit #164.
     - Neu ist der Abschnitt „Kaspa hashrate, the last 30 days“, je Tag das Tagesmittel und das 7-Tage-Mittel.
     - Der Link von der Startseite heißt jetzt „hashrate“ statt „network“.
   - **kaspa-supply.html:** Die Frage heißt jetzt wortgleich „How many Kaspa coins are there?“. Die Antwort nennt den Umlauf mit Quelle und Datum und die maximale Menge, computed, und erneuert sich täglich. Halter und Adressen stehen seit #164.
   - **kaspa-smart-contracts.html:** H1 und erste FAQ beantworten „Does Kaspa have smart contracts?“ wörtlich. Covenants, KCC-20 und Toccata stehen seit #164 mit Zahlen und Datum.
3. **Klickrate, nur Title und Description**

   | Seite | Title | Description |
   | --- | --- | --- |
   | kron.html | Kron Kaspa DEX and Launchpad, How It Works and What to Check | DEX und Launchpad auf Layer 1, Bonding Curve, 3 Prüfungen vor dem Handel |
   | kaspa-data-sources.html | Kaspalytics and Other Kaspa Data Sources Side by Side | „We read Kaspalytics daily and show it next to …“, ohne fremde Marken herabzusetzen |
   | kaspa-tvl.html | Kaspa TVL on DefiLlama, Kasplex and Igra Explained | TVL wie DefiLlama sie führt, getrennt nach Kasplex und Igra |
   | kaspa-staking.html | Can You Stake Kaspa? No, Kaspa Is Proof of Work | beginnt mit „No.“, die Antwort steht schon im Title |

## Abweichungen
- **source statt counted bei der Hashrate:** Die Tageswerte kommen aus der Hashrate-Historie der Kaspa-REST-API. Wir zählen die Hashrate nicht selbst, also steht dort „source“, wie in #164 begründet.
- **30-Tage-Tabelle:** Die Kaspa-REST-API ist aus der Arbeitsumgebung nicht erreichbar. Die Tabelle füllt deshalb der Lauf `seiten-zahlen`, den ich nach dem Merge von Hand starte.
- **Halving auf Dauer aktuell:** `seiten-zahlen.yml` committet bisher nur drei Seiten. Damit die Halving-Seite nach dem 4.11. von selbst nachzieht, muss `kaspa-halving.html` in die Commit-Liste. Das ist eine Workflow-Datei und kommt als eigener PR an Ben. Bis zum Merge ziehe ich die Zahlen nach der Stufe von Hand nach.

## Prüfung
- `seiten_zahlen.py --selbsttest` grün, darunter die Halving-Stufe vor und nach dem 4.11., die 30-Tage-Tabelle und die Supply-FAQ.
- `startseite.py --selbsttest` grün.
- Textwache über alle geänderten sichtbaren Texte, kein Verstoß. Die Treffer sind nur JSON-Schlüssel.
- 390 und 1440 px für Halving, Hashrate, Supply und Startseite, ohne seitliches Scrollen.
- JSON-LD gültig.

## PR-Nummern
- #164, Nachmittag, live
- #170, Priorität A, selbst gemergt
- #172, KCC-20 final, selbst gemergt
- #171, Workflow `seiten-zahlen.yml`, wartet auf Ben

## Selbst-Merge und Abnahme
- **#170 als 43a8221, 27.10.2026:**
  - Live sind Halving mit Kurz-Fakt und FAQ, Hashrate mit 30-Tage-Tabelle, Supply mit „How many Kaspa coins are there?“ und die neuen Titles von kron, kaspa-data-sources, kaspa-tvl und kaspa-staking.
  - Die 30-Tage-Tabelle hat der Handlauf von `seiten-zahlen` am 27.10.2026 gefüllt, mit Tageswerten bis zum 26.10.
  - Abnahme auf der echten URL: Alle Titles und Kurz-Fakt-Zeilen werden ausgeliefert.
- **#172 als 9e8c7c1, 27.10.2026:** KCC-20 ist seit dem 21.10.2026 final. Smart Contracts, Token-Standard und Toccata nennen das jetzt, live geprüft.
- **Lighthouse mobil live nach allen Merges, 27.10.2026:**

  | Seite | Punkte | LCP | CLS |
  | --- | --- | --- | --- |
  | Startseite | 97 | 2.2 s | 0.021 |
  | kaspa-halving | 100 | 1.3 s | 0.001 |
  | merged-mining | 99 | 2.0 s | 0 |
  | entity-x | 98 | 1.7 s | 0.085 |
  | kaspa-data-sources | 98 | 2.2 s | 0 |

## Offene Fragen an Ben
1. **Neu-Indexierung:** Die Search Console kann ich von hier aus nicht bedienen, es gibt keinen Zugang dafür. Ich liefere nach jedem Merge die Liste der geänderten URLs zum Einreichen.
2. **Rich Results Test:** Der Test von Google ist von hier nicht erreichbar. Ich prüfe das Schema lokal. Der Test auf der echten URL steht als „📤 VON HAND“ in der Lieferung.

## Was Ben tun muss
Den Workflow-PR für `seiten-zahlen.yml` mergen, damit die Halving-Seite nach dem 4.11. von selbst nachzieht. Die geänderten URLs in der Search Console zur Indexierung einreichen.

<!-- discord -->
**SEO-Runde v2, Lieferung 27.10.2026**
- **Priorität A (#170) und B (#173):** beide fertig, selbst gemergt und live, lange vor den Fristen 2.11. und 8.11.
- **A, Halving:** Kurz-Fakt mit der Stufe am 4 nov 2026 um 13:45 UTC, 2.0602 auf 1.9445 KAS je Block, computed. Dazu die zwei FAQ.
- **A, Hashrate:** 30-Tage-Tabelle mit 7-Tage-Mittel.
- **A, Supply:** FAQ „How many Kaspa coins are there?“.
- **A, Klickrate:** neue Titles für kron, data-sources, tvl und staking.
- **B, Wallets:** Vergleichstabelle mit KCC-20-Spalte. Bei keiner Wallet steht KCC-20 in den Release-Notes, Stand 27 oct 2026.
- **B, Schema:** Article und Breadcrumb auf allen Unterseiten, Dataset auf 4 Zahlenseiten.
- **B, Aufräumen:** /balance leitet auf die Wallet-Seite, kaspa-mining trägt feste Zahlen.
- **B, Tempo:** Lighthouse mobil live, alle 5 Seiten mit LCP unter 2.5 s und CLS unter 0.1, Halving vorher 0.17, nachher 0.001.
- **Nebenbefund #172:** KCC-1, KCC-2 und KCC-20 sind seit dem 21 oct 2026 final, drei Seiten sind korrigiert.
- **/whales:** live, die Weiterleitung behält die UTM-Parameter.
- **Berichte:** berichte/2026-11-02-seo-runde-a.md und berichte/2026-11-08-seo-runde-b.md
<!-- teil -->
📤 VON HAND, 1 von 2: **mergen**
1. PR #171 (Workflow seiten-zahlen, Halving und Mining ziehen täglich nach). Ohne ihn ziehe ich die Halving-Zahlen nach dem 4.11. von Hand nach.
2. PR #144, falls noch offen, danach auf c2:
```
sudo bash deploy/c2/setup.sh nachziehen
```
<!-- teil -->
📤 VON HAND, 2 von 2: **Search Console**, Neu-Indexierung beantragen, je URL einzeln in die URL-Prüfung:
```
https://kaspapulse.com/kaspa-halving.html
https://kaspapulse.com/kaspa-hashrate.html
https://kaspapulse.com/kaspa-supply.html
https://kaspapulse.com/kaspa-smart-contracts.html
https://kaspapulse.com/kron.html
https://kaspapulse.com/kaspa-data-sources.html
https://kaspapulse.com/kaspa-tvl.html
https://kaspapulse.com/kaspa-staking.html
https://kaspapulse.com/kaspa-wallets.html
https://kaspapulse.com/kaspa-mining.html
https://kaspapulse.com/kaspa-token-standard.html
https://kaspapulse.com/kaspa-toccata.html
https://kaspapulse.com/
```
Rich Results Test, je einen Seitentyp:
```
https://kaspapulse.com/kaspa-supply.html
https://kaspapulse.com/kaspa-wallets.html
```
<!-- /discord -->
