# Prüfung Form 11 und Form 12

Stand 30.09.2026. Nur Befund, nichts gebaut. Ben entscheidet danach, ob die Formen gebaut werden.

Alle Zahlen stammen aus Runner-Läufen oder aus Dateien im Repo. Jede Zahl steht unten mit Stichtag und Quelle.

| Lauf | Inhalt |
|---|---|
| [36699899262](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36699899262) | Kaspalytics-Reihen, Seitentexte, Explorer-Labels mit Kontostand |
| [36700199409](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36700199409) | Aufschlüsselung der Börsenbestände, ganze Erklärtexte, Reihenlängen |
| [36700694337](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36700694337), [36701042932](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36701042932), [36701176014](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36701176014) | Suche nach den Daten der Verteilungstabelle |
| [36701002510](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36701002510) | Entity-X-Ledger, Stand je Bewegung |

Die Prüf-Branches heißen `pruefung/formen-11-12-2026-09-30` und `pruefung/musterdateien-2026-09-30`. Sie werden nie gemergt.

## Form 11, Schlafende Coins

### Was `dormant_pct` ist

- **Quelle:** Kaspalytics, `https://www.kaspalytics.com/api/charts/supply/inactive?minAge=1year`, Reihe `CSPERCENT`.
- **Definition laut Seite:** „share of circulating Kaspa supply that has not moved in at least one year“. Die Variante „sums every age bucket from 1–2 years upward“.
- **Zählweise laut Seite:** Das Alter jedes UTXO im UTXO-Set wird über den DAA-Score geschätzt, „accurate to within minutes“. Die Seite verweist auf einen offenen Python-Ansatz auf GitHub.
- **Fenster:** mindestens 1 Jahr seit der letzten Bewegung, gemessen als Anteil am Umlauf.
- **Stichtag:** Kaspalytics misst einmal am Tag, als Momentaufnahme. Der letzte Punkt trägt die Marke `2026-09-29T00:00:02.584Z`. Nach der Mitternachtsregel in `scripts/kaspalytics.py` ist das der Stand vom Ende des **28.09.2026**.
- **Reihe bei Kaspalytics:** täglich seit 27.08.2023, 1,125 Punkte.
- **Reihe bei uns:** wöchentlich in `data/weekly.json`, erster Wert in der Woche vom 27.07.2026 (50.47).
  - Bis 21.09. von Hand abgelesen, seit 28.09. vom Bot gelesen.
  - `data/weekly-history.json` führt die Zahl ab der Woche vom 03.08.2026.
- **Namensfalle:** In `data/weekly.json` und in `scripts/kaspalytics.py` heißt der Wert `holders`, in `scripts/weekly_numbers.py` heißt er `dormant_pct`. Das Umbenennen steht seit dem 28.09. an, siehe `data/weekly-notes.md`.

### 1 Jahr und 2 Jahre getrennt: ja

Kaspalytics liefert beide getrennt, Stichtag 28.09.2026:

| minAge | Anteil am Umlauf |
|---|---|
| `6months` | 70.72% |
| `1year` | **50.58%** |
| `2years` | **25.75%** |
| `3years` | 11.98% |

`3months` und `4years` stehen als Links auf der Seite, abgerufen habe ich sie nicht. Falsch geschriebene Werte wie `2year`, `1y` oder `730days` antworten mit http 400 „Unknown minAge“.

**Gegenprobe gegen die Hodl-Wave-Bänder** (`supply/hodl-waves`, derselbe Stichtag):
- Die Bänder 1–2 Jahre, 2–3 Jahre, 3–4 Jahre und 4–5 Jahre ergeben zusammen 50.578060496 %, genau wie `minAge=1year`.
- Ab 2 Jahren ergeben sie 25.751732531 %, genau wie `minAge=2years`, und ab 3 Jahren 11.978532000 %.
- Beide Zahlen stammen aus denselben Grunddaten. Die Gegenprobe zeigt, dass wir die Reihen richtig lesen, nicht, dass Kaspalytics richtig zählt.

### Selbst zählen

Nicht nötig, weil es die Zahl gibt.

Wollten wir sie trotzdem selbst zählen, bräuchten wir das ganze UTXO-Set mit dem DAA-Score jedes Eintrags. Das geht nur über einen eigenen Knoten mit UTXO-Index. `api.kaspa.org` hat keinen Endpunkt für das ganze Set, und auf einem GitHub-Runner ist kein eigener Knoten möglich.

Wie lange ein Lauf dauern würde, habe ich nicht gemessen. Eine Zahl dazu steht hier deshalb nicht.

### Täglich reproduzierbar

Ja. Kaspalytics schreibt jeden Tag einen Punkt, und der Abruf braucht keine Anmeldung. Es bleibt eine einzige Quelle ohne unabhängige Gegenzählung.

## Form 12, Eine Wallet gegen alle Börsen

### `exchange_kas` gegen Entity X, gleicher Stichtag 27.09.2026

| Größe | Wert | Stichtag | Quelle |
|---|---|---|---|
| `exchange_kas` | 3,783,300,501 KAS | Ende 27.09.2026 (Marke `2026-09-28T00:00:02.953Z`) | Kaspalytics `supply/exchange-holdings`, Reihe `Balance` |
| Entity X | 1,525,975,596.46 KAS | Ende 27.09.2026 | eigener Ledger aus der Kette (Lauf 36701002510). Die letzte Bewegung davor war am 25.09. um 10:09 UTC, die nächste am 28.09. um 12:26 UTC. |
| **Verhältnis** | **Entity X hält 40.3% dessen, was alle bekannten Börsenadressen zusammen halten** | | |

Die Richlist vom 27.09. 08:31 UTC (`data/richlist-log.json`) nennt für Entity X 1,525,975,596 KAS, also dieselbe Zahl.

### Welche Adressen in `exchange_kas` stecken

Das lässt sich nicht feststellen.
- Die Seite sagt: „A list of known exchange addresses is maintained by kas.fyi and kaspa.stream. The total balance of all addresses on this list is summed.“
- Die API liefert nur die Summe. `?breakdown=true` gibt dieselbe eine Reihe zurück, `/addresses` und `/exchanges` antworten mit 404, und `__data.json` der Seite ist leer.

### Gegen unsere eigenen Börsen-Labels: keine grobe Übereinstimmung

Als eigene Labels zähle ich das Label-Verzeichnis von `api.kaspa.org/addresses/names`, 138 Einträge. Davon tragen 44 Adressen einen Börsennamen:

> Biconomy, Bitget, Bitvavo, Bybit, Bybit EU, ChangeNOW, CoinEx, Gate.io, Kraken, KuCoin, MEXC, Pionex, PionexUS, Unknown exchange, Uphold, XT

Pools, Fonds, Bridges, Spendenadressen und die Burn-Adresse zähle ich nicht mit.

| Messung | Summe Börsen-Labels | gegen `exchange_kas` |
|---|---|---|
| Richlist 27.09.2026 08:31 UTC, 25 gelabelte Börsenadressen in den Top 10,000 | 6,077,912,913 KAS | +2.29B, das 1.61-fache |
| live, 30.09.2026 10:02 UTC, alle 44 Adressen mit `/balance` | 6,135,560,066 KAS | gegen den 28.09. (3,781,519,097): das 1.62-fache |

Unsere Labels finden rund 60 % mehr Börsenbestand als Kaspalytics.

Die größten Posten in der Richlist vom 27.09.:

| Börse | KAS |
|---|---|
| Kraken (3 Adressen) | 1.54B |
| KuCoin | 0.86B |
| MEXC | 0.82B |
| Bybit | 0.76B |
| Gate.io | 0.71B |
| Uphold | 0.61B |
| Bitvavo | 0.51B |
| Bitget | 0.20B |

Kaspalytics führt also entweder weniger Adressen oder andere. Welche fehlen, lässt sich ohne die Liste von Kaspalytics nicht sagen. Ich vermute hier keine Ursache.

Gemessen an unseren Labels hält Entity X am 27.09. **25.1%** des gelabelten Börsenbestands, gemessen an Kaspalytics 40.3%. Die Aussage hängt also davon ab, wessen Börsenliste gilt.

### Zweite Rechnung: Entity X gegen alle anderen Adressen über 100 KAS

Aus der Richlist allein ist sie nicht zu bilden.
- Die Rangliste von `api.kaspa.org/addresses/top` hat 10,000 Einträge und reicht nur bis 284,576 KAS hinunter.
- Adressen zwischen 100 und 284,576 KAS fehlen darin.

Was belegt ist, Stichtag 27.09.2026 08:31 UTC:

| Vergleich | Summe der anderen | Anteil Entity X |
|---|---|---|
| die 9,999 anderen Adressen der Rangliste (ab 284,576 KAS) | 21,092,252,516 KAS | 7.2% |
| Obergrenze: Umlauf minus Entity X, alle Adressen bis hinunter zu Staub (Umlauf 27,724,105,701 laut `data/richlist-log.json`) | 26,198,130,105 KAS | 5.8% |

Der gesuchte Wert liegt also zwischen **5.8% und 7.2%**.

**Eine Quelle für das genaue Aggregat gibt es.** Kaspalytics hat die Seite „Address Distribution by KAS Bucket“ (`/app/supply/distribution-table/KAS`). Sie zeigt je Guthabenstufe die Zahl der Adressen und den gesamten KAS-Bestand. Gezählt wird laut Seite aus dem UTXO-Index eines Knotens.

Die Daten lädt die Seite im Browser nach. Den Pfad dahin habe ich in drei Läufen nicht gefunden:
- Seitenquelltext und `__data.json` enthalten keine Daten;
- in den 120 Skriptmodulen der Seite steht kein `/api/`-Pfad.

Ein Browserlauf auf dem Runner (Playwright, Netzwerkmitschnitt) würde den Pfad zeigen. Das wäre der nächste Schritt, falls Form 12 gebaut wird.

### Täglich reproduzierbar

| Größe | täglich? | Grund |
|---|---|---|
| Entity X | ja | `/balance`, stabiler Endpunkt |
| `exchange_kas` | ja | ein Punkt je Tag, als Momentaufnahme mit der Mitternachtsregel |
| eigene Börsen-Labels | ja | 44 Abrufe von `/balance` plus das Verzeichnis. Das Verzeichnis ist als experimentell markiert und kann sich ändern. |
| Richlist | technisch ja | Der Endpunkt ist experimentell („EXPECT BREAKING CHANGES“) und kann mit 503 abgeschaltet sein. Bisher läuft er einmal pro Woche als Archiv (`scripts/richlist_log.py`). |
| Aggregat über 100 KAS | noch nicht | erst, wenn der Datenpfad der Verteilungstabelle belegt ist |

## Offen für die Entscheidung

1. **Form 11** ist täglich baubar, mit 1 Jahr und 2 Jahren getrennt. Es gibt nur eine Quelle, Kaspalytics.
2. **Form 12:** Das Verhältnis hängt an der Börsenliste.
   - Kaspalytics ergibt 40.3%, unsere Labels 25.1%.
   - Die Liste von Kaspalytics ist nicht einsehbar, unsere liegt offen.
   - Ohne Entscheidung, welche Liste gilt, ist die Zahl nicht eindeutig.
3. **Das Aggregat „alle anderen über 100 KAS“** braucht noch einen Browserlauf, um den Datenpfad der Verteilungstabelle zu finden. Bis dahin sind nur die Grenzen 5.8% bis 7.2% belegt.
