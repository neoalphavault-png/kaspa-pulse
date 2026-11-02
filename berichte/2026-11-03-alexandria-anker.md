# Alexandria-Anker auf Testnet-10, unabhängige Prüfung

Bericht für Ben zum Auftrag vom 2.11.2026, Frist Di 3.11. 12:00 Berlin. Gelesen am Mo 2.11.2026 zwischen 07:31 und 08:26 UTC. Zahlen aus unseren eigenen Abfragen heißen counted, Angaben des Teams (Kas Knight, 1.11.) heißen source Team, Angaben der Archivseite source Archiv.

## Ergebnis in vier Sätzen

Die Tx ist auf Testnet-10 vorhanden und angenommen, genau in dem Block, den das Team nennt, mit der Blockzeit 1.11.2026 21:24:24.537 UTC (counted, zwei Knoten gleich). Der Payload ist byte-genau der erwartete Text, 85 Byte (counted). Die Ausgänge ergeben zusammen 99,779,400 sompi wie angegeben, den Eingang und damit die Gebühr konnten wir aber nicht nachrechnen, weil die vorherige Tx auf beiden Knoten nicht mehr lesbar war. Das Commitment im Payload lässt sich ohne veröffentlichte ALX-KASPA-1-Spezifikation nicht unabhängig nachrechnen.

## Wie geprüft wurde

- **Zwei Knoten:** Zwei verschiedene öffentliche Testnet-10-Knoten (rusty-kaspa 2.1.0), über denselben Weg wie bei der STP-Zählung gewählt. Der zweite meidet den ersten. Kennungen `813b7ce939` und `da0ae1241a`. Es sind keine Knoten, die wir selbst betreiben, die Abfragen und die Rechnung sind aber unsere eigenen. Nur lesend, höchstens eine Abfrage je Sekunde.
- **Pruning-Punkt beider Knoten:** 31.10.2026 15:16:55 UTC. Alles davor ist auf diesen Knoten nicht mehr lesbar.
- **Läufe** auf dem Messbranch `messung/alexandria-anker`:
  - [Lauf 41406868017](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41406868017): Tx, Block, Annahme, Payload, Suche nach dem Eingang 6 h zurück, Archivseite. k1 gelesen 07:53:53 UTC, k2 07:55:43 UTC.
  - [Lauf 41409677674](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41409677674): Suche nach dem Eingang vom Pruning-Punkt bis 1.11. 15:26 UTC, sechs Stücke, 07:58 bis 08:26 UTC.
- **Rohdaten:** `messung/alexandria/roh/20261102T075543Z/k1.json` und `k2.json` (die ganze Tx, wie die Knoten sie liefern, dazu der Kopf des annehmenden Blocks), `messung/alexandria/roh/eingang-20261102T082622Z/` (Suche) und `messung/alexandria/roh/20261102T075543Z/archiv/` (Archivseite byte-genau). Die Rohdaten enthalten die Scripts der Ausgänge, deshalb stehen sie nur dort und nicht in diesem Bericht.
- **Skript:** `scripts/alexandria_anker.py`, Workflows `alexandria-anker.yml` und `alexandria-eingang.yml`, nur auf dem Messbranch.

## 1. Tx vorhanden und angenommen

| | Wert | Quelle |
|---|---|---|
| Tx | `3db50bc618db869ebfdda76381d7d5beb491f61a97426faadd02d831dfd70269` | source Team, auf beiden Knoten gefunden (counted) |
| Annehmender Block | `9afd242166b4ddc2b900b30c6d6016014414c2dd199d7856804213bf0618a7d5`, gleich der Angabe | counted, k1 und k2 |
| Kettenblock | ja | counted, k1 und k2 |
| Blockzeit des annehmenden Blocks | 1.11.2026 21:24:24.537 UTC, gleich der Angabe | counted, k1 und k2 |
| DAA-Score des annehmenden Blocks | 612,333,727 | counted, k1 und k2 |
| Blue Score | 600,700,146 | counted, k1 und k2 |
| Mergeset | 2 blaue Blöcke, 0 rote | counted, k1 und k2 |
| Annahme | Ab dem Selected Parent ist der nächste Kettenblock genau der angegebene Block, und seine angenommenen Tx enthalten diese Tx. Kein anderer Block in der gelesenen Kette nimmt sie an. | counted, k1 und k2 |

Die Tx steht in zwei Blöcken, beide blau, beide im Mergeset des annehmenden Blocks:

| Block | Blockzeit (UTC) | DAA-Score |
|---|---|---|
| `9b2d0ffa87d0027fa2bc303e3ad6020266fd4024f95ecc08d1906fe787597683` (Selected Parent des annehmenden Blocks) | 1.11.2026 21:24:24.178 | 612,333,725 |
| `96d84e3d31662865522bec84e2301ba2c82529e36592d8fb4b45d0ac13d0cd52` | 1.11.2026 21:24:23.929 | 612,333,724 |

Beide Knoten liefern die Tx byte-gleich (Vergleich der ganzen JSON-Daten, counted).

## 2. Payload

| | Wert | Quelle |
|---|---|---|
| Länge | 85 Byte | counted, k1 und k2 |
| Text (UTF-8) | `ALX-KASPA-1\|study\|52\|4fdbb5b5344a7aa285b1426a3df7fff61e2d69396130ccffea2bab52cbeccc01` | counted, k1 und k2 |
| Gleich dem erwarteten Payload | ja, byte-genau | counted gegen source Team |
| sha256 des Payloads | `123746b14a7f787136cc54c0429cae5e0e4eab56fe6b1a5d3e1511bf53cd3e9c` | counted |

Weitere Felder der Tx (counted): Version 0, Lock-Time 0, normales Subnetz (alles Nullen), Gas 0, ein Eingang, zwei Ausgänge, beide vom Typ PubKey, keine Covenant-Bindung. Masse laut Knoten 2,121 (compute), das Feld mass der Tx steht auf 92,172 (gleich storageMass).

## 3. Eingang, Ausgänge, Gebühr

| | sompi | Quelle |
|---|---|---|
| Ausgang 1 | 11,000,000 | counted, k1 und k2 |
| Ausgang 2 | 88,779,400 | counted, k1 und k2 |
| Ausgänge zusammen | 99,779,400, gleich der Angabe | counted |
| Eingang | nicht lesbar | source Team: 100,000,000 (1 TKAS) |
| Gebühr | nicht nachrechenbar | source Team: 220,600 |

Warum der Eingang nicht lesbar war: Ein Kaspa-Knoten führt keinen Index über Tx-IDs. Die vorherige Tx lässt sich nur finden, indem man die Blöcke liest. Wir haben jeden Block vom Pruning-Punkt der Knoten (31.10. 15:16:55 UTC) bis eine Minute nach der Tx gelesen und nach der vorherigen Tx gesucht. Gefunden wurde sie nicht:

| Zeitraum (UTC) | Blöcke | Knoten | gefunden |
|---|---|---|---|
| 31.10. 15:16:55 bis 19:20 | 146,144 | `da0ae1241a` | nein |
| 31.10. 19:18 bis 23:20 | 145,153 | `813b7ce939` | nein |
| 31.10. 23:18 bis 1.11. 03:20 | 145,144 | `da0ae1241a` | nein |
| 1.11. 03:18 bis 07:20 | 145,689 | `da0ae1241a` | nein |
| 1.11. 07:18 bis 11:20 | 144,928 | `813b7ce939` | nein |
| 1.11. 11:18 bis 15:26 | 149,115 | `813b7ce939` | nein |
| 1.11. 15:24 bis 21:25 | 216,256 | beide | nein |

Jedes Stück ist lückenlos bis über sein Ende gelesen, die Stücke überlappen sich um 2 Minuten. Die vorherige Tx ist also älter als der Pruning-Punkt der Knoten, und ihr Betrag ist mit diesen Knoten nicht mehr lesbar. Die Angaben 1 TKAS Eingang und 220,600 sompi Gebühr bleiben source Team. Sie passen zu den Ausgängen (100,000,000 minus 99,779,400 gleich 220,600), sind von uns aber nicht belegt.

## 4. Commitment

Gelesen am 2.11.2026 von 07:31:49 bis 07:31:59 UTC vom GitHub-Runner, nur GET, ohne Anmeldung, byte-genau gespeichert.

| | Wert | Quelle |
|---|---|---|
| Eintrag 52 | Version 2, Vorgänger 51, gleiche Lineage wie 51 | source Archiv, `/api/studies/52` |
| Zeitleiste | AP-0052 Version 2 folgt AP-0051, AP-0051 ist die erste Ablage | source Archiv, `/api/timeline` |
| Datei zu 52 | PDF, 27,725 Byte, sha256 `a286f3ffe06f7c9699d9dac4d4bab47f677000d50c80de6f7a036f08c392161c` | counted aus `/api/studies/52/file` |
| fileHash laut Archiv | gleicher Wert | source Archiv, also stimmt die Datei mit dem Fingerabdruck des Archivs überein |
| Datei zu 51 | 27,738 Byte, sha256 gleich dem fileHash von 51 im Archiv | counted gegen source Archiv |
| manifestHash zu 52 | `6e4b69c745a8cb58f15c8a55bf41f0fe58826340df57f84d02b8dd6273287e5e` | source Archiv |
| documentHash zu 52 | `083bb17add43518291ad7c65f84e3005883289410aca9d2d5e4ceda54c42484b` | source Archiv |
| Commitment im Payload | `4fdbb5b5344a7aa285b1426a3df7fff61e2d69396130ccffea2bab52cbeccc01` | counted aus der Tx |

Was nicht geht:

- **Das Manifest ist nicht öffentlich herunterladbar.** Unter `/study/52/manifest` und `/manifest.json` liefert die Seite nur die App selbst aus, `/api/study/52/manifest` gibt 404. Den manifestHash können wir deshalb nicht nachrechnen.
- **Das Verfahren ist nicht festgelegt.** Die App beschreibt das Commitment nur so: "ALX-KASPA-1 fingerprints the manifest hash, record hash, record identity, protocol version, and network for inclusion in a transaction payload; this hash alone is not an anchor." Welche Bytes in welcher Reihenfolge, mit welchem Trenner und welchem Hash eingehen, steht nirgends. Das Commitment ist weder der fileHash noch der manifestHash noch der documentHash. Wir haben 824,256 naheliegende Kombinationen der genannten Teile mit sha256 durchgerechnet (Reihenfolge, Trenner, Schreibweisen von Kennung und Netz, JSON), keine ergibt das Commitment.

Ergebnis: **Das Commitment ist ohne veröffentlichte ALX-KASPA-1-Spezifikation nicht unabhängig nachrechenbar.** Bestätigt ist nur, dass genau dieser Wert in einer angenommenen Tx auf Testnet-10 steht und dass die öffentliche Datei zu study/52 zum fileHash des Archivs passt.

Hinweis: Der Abstract von Eintrag 52 sagt "This record is not yet anchored to Kaspa." Er stammt von der Ablage um 19:58:51 UTC am 1.11., also vor der Annahme um 21:24 UTC, und stand am 2.11. um 07:31 UTC noch unverändert dort (source Archiv).

## 5. Was wir NICHT geprüft haben

- **Sicherheit:** keine Prüfung von App, Server, Schlüsseln, Signaturverfahren, Zugriffsschutz oder Angriffsflächen.
- **Produktionsreife:** keine Aussage über Betrieb, Verfügbarkeit, Wiederherstellung, Skalierung oder Mainnet. Geprüft ist eine Tx auf Testnet-10.
- **Rechtliches:** keine Aussage zu Urheberschaft, Eigentum, Beweiskraft, Datenschutz oder Haftung.
- **Inhalt:** nicht, ob das PDF wahr, echt oder vom genannten Autor ist. Der Eintrag nennt sich selbst einen Test mit synthetischen Belegen.
- **Herkunft der Tx:** nicht, wem der Schlüssel des Eingangs gehört und ob die Tx wirklich vom Team kommt. Die Signatur haben wir nicht selbst nachgerechnet.
- **Eingang und Gebühr:** siehe Abschnitt 3, nicht mehr lesbar.
- **Manifest und Commitment-Verfahren:** siehe Abschnitt 4.
- **Alles außerhalb dieser einen Tx:** andere Anker, andere Einträge des Archivs, die Zeitstempel der Archivseite und ob das Archiv Daten später ändert.
- **Unsere Knoten:** Es sind zwei öffentliche Knoten. Ein eigener Archivknoten würde auch ältere Daten halten, den haben wir für Testnet-10 nicht.

## Nebenbei

Das Skript hat beim Abholen der Archivseite alle Links derselben Seite verfolgt und dabei auch andere öffentliche Einträge und Endpunkte gelesen, nur per GET. Drei davon antworteten mit 401 (Entwürfe, Vault), einige mit 400 oder 404. Die öffentlichen Antworten liegen mit auf dem Messbranch. Nichts davon geht in diesen Bericht ein außer den Einträgen 51 und 52.

## Offene Fragen an Ben

1. Soll ich das Team um die ALX-KASPA-1-Spezifikation bitten, also die genaue Byte-Folge für das Commitment und ein öffentliches Manifest zu study/52? Dann rechne ich das Commitment nach.
2. Soll ich den Eingang über die Signatur prüfen? Die Signatur deckt den Betrag des Eingangs mit ab. Mit dem Script des vorherigen Ausgangs ließe sich so zeigen, dass der Eingang 1 TKAS war, auch ohne die vorherige Tx. Dafür bräuchte ich die Adresse des Eingangs vom Team, oder ich prüfe, ob sie einem der beiden Ausgänge entspricht. Das ist mehr Aufwand, etwa 2 h.
3. Darf die Tx-ID und der Blockhash so im Bericht stehen? Es sind die öffentlichen Kennungen des Ankers, die das Team selbst nennt. Adressen stehen keine drin.

## Was Ben tun muss

- Nichts mergen: Ich merge diesen PR selbst, wenn die Checks grün sind. Er enthält nur diesen Bericht.
- Fragen oben beantworten.
- Der Messbranch `messung/alexandria-anker` wird nicht gemergt.

Danach beginne ich die KCC-20-Migrationszählung.
