# Erste öffentliche KCC-20-Zählung vom eigenen Knoten

Bericht für Ben zu Aufgabe A vom 23.10.2026. Branch `fix/kcc20-zaehlung`, PR [#136](https://github.com/neoalphavault-png/kaspa-pulse/pull/136) (Entwurf bis Montag).

**Stand dieses Berichts: Zwischenstand vom Freitag, 23.10.2026, Lauf 2 mit Stichzeit 14:30 UTC.** Die Hauptzählung zur Stichzeit Mo 26.10.2026 12:00 UTC ersetzt diese Zahlen am Montag. Nichts hieraus veröffentlichen, bevor der Montag eingetragen ist.

Unsere Zahlen tragen "counted". Fremde Zahlen tragen ihre Quelle ("source kcc20.info", "source kasplex", "api.kaspa.org").

## Was gemacht wurde

1. **Eigener Mainnet-Knoten** (rusty-kaspa v2.1.0) im Runner, frisch synchronisiert, gestoppt. Das Werkzeug `kcc20/werkzeug` liest den UTXO-Bestand zur Stichzeit aus der Knoten-Datenbank, mit Zweitprüfung (Pruning-Punkt vorwärts, muss identisch sein). Mit `KP_TX=1` schreibt es jede angenommene Transaktion mit Covenant-Ausgang oder KCC-20-Dispatch-Tag ab dem Pruning-Punkt.
2. **Ältere Transaktionen** (erzeugende Tx lebender Outputs vor dem Pruning-Punkt, Vorfahren bis 21.10. 00:00 UTC) holt `scripts/kcc20_api.py` von api.kaspa.org. Sie werden genauso bewiesen wie die eigenen.
3. **Beweis je Output** (`scripts/kcc20_zaehlung.py`): Ein lebender Covenant-Output zählt als KCC-20 nur, wenn sein P2SH-Hash genau Blake2b(Template-Präfix ‖ EncodeState(Zustand) ‖ Suffix) ist. Die Kodierung ist gegen die offiziellen KCC-20-Konformitätsvektoren (kaspanet/kccs, Final seit 21.10.) getestet. Ohne Beweis kein Token, keine Menge.
4. **Genesis und Namen** (`scripts/kcc20_namen.py`): Je Token wird die Genesis gesucht und über die KIP-20-Covenant-ID bewiesen (Hash wie im Konsens, getestet gegen den KCC-23-Vektor). Namen kommen aus KCC-23-Metadaten der Vorbereitungs-Tx oder, wenn es die nicht gibt, aus dem JSON im Genesis-Payload. Jede Zeile nennt ihre Namensquelle.
5. **KRC-20** je Symbol bei Kasplex abgefragt, nur als "source kasplex".
6. **kcc20.info** über deren öffentliche API gelesen (`.github/workflows/kcc20-quellen.yml`, kein Knoten, nur Skalarfelder, keine Adressen).

Hochgeladen werden nur Summen je Token, Tx-Listen ohne Skripte und die Namensliste. Die Bestandsliste mit Adressen bleibt im Runner.

## Definitionen

| Kennzahl | Definition |
|---|---|
| Token | Covenant-ID mit mindestens einem lebenden Output, dessen KCC-20-Zustand per Hash bewiesen ist |
| Halter-Outputs | lebende Outputs eines Tokens mit bewiesenem Zustand zur Stichzeit |
| Halter | verschiedene (owner_scheme, owner) je Token; "eindeutig" zählt jeden Besitzer über alle Tokens einmal |
| Menge | Summe der `amount`-Felder der Halter-Outputs in Basiseinheiten (Dezimalstellen nur, wo die Metadaten sie nennen) |
| Transfer | angenommene Tx mit Dispatch-Tag transfer oder transfer_delegator, die einen bewiesenen Output dieses Tokens erzeugt oder ausgibt. Eine Tx zählt einmal |
| Zeitraum Transfers | 21.10.2026 00:00 UTC bis Stichzeit, Zeit des annehmenden Kettenblocks |

## Zwischenstand Lauf 2, 23.10.2026 14:30 UTC (counted)

- Lauf [39967185904](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/39967185904). Zweitprüfung identisch, 0 Fehler.
- **133 KCC-20-Tokens** mit 1.900 Halter-Outputs. 638 Halter eindeutig (1.366 je Token aufsummiert).
- **3.356 Transfer-Tx seit 21.10. 00:00 UTC.** Davon 2.075 aus dem eigenen Knoten (Fenster ab 22.10. 05:53 UTC), 1.281 über die Vorfahren von api.kaspa.org (davor).
- Genesis bewiesen für 133 von 133. Namen: 40 aus KCC-23, 87 aus dem Genesis-Payload, 6 ohne Namen.
- Lebende Covenant-UTXOs insgesamt 17.150. Davon 15.250 ohne KCC-20-Zustand (andere Covenants, siehe Abgleich). Bei 42 Tokens liegt je genau ein weiterer Output ohne Zustand unter derselben Covenant-ID (zusammen 269,50 KAS), vermutlich der Mint-Ausgang des Tokens.

Die 15 größten nach Halter-Outputs. Namensquelle "kcc-23" oder "genesis" (JSON im Genesis-Payload, kein KCC-23). Ticker sind nicht eindeutig, deshalb steht der Anfang der Covenant-ID davor.

| Covenant-ID | Ticker | Quelle Name | Halter-Outputs | Halter | Menge (Basiseinheiten) | Transfers seit 21.10. | KRC-20 gleiches Symbol (source kasplex) |
|---|---|---|---|---|---|---|---|
| d8c4356d20 | THEN | genesis | 426 | 208 | 1.000.000.000 | 725 | nicht abgefragt |
| 3cb7bd371e | GUZA | genesis | 270 | 174 | 1.000.000.000 | 347 | nicht abgefragt |
| 7cf4b45ebf | ROCKET | genesis | 112 | 61 | 1.000.000.000 | 257 | nicht abgefragt |
| efcf006e57 | BTE | genesis | 111 | 71 | 1.000.000.000 | 151 | nicht abgefragt |
| 244cd20dac | DAGAS | genesis | 61 | 53 | 1.000.000.000 | 81 | nicht abgefragt |
| 7f174f86e1 | KASX | kcc-23 | 37 | 28 | 800.000.000 | 38 | gefunden |
| e22cebe470 | FROG | genesis | 26 | 25 | 1.000.000.000 | 58 | nicht abgefragt |
| 1c30b57d79 | BFLY | genesis | 25 | 25 | 1.000.000.000 | 48 | nicht abgefragt |
| cbe213cecb | Wobbly.k | kcc-23 | 25 | 4 | 465.000.000 | 7 | kein KRC-20-Ticker möglich |
| 7ed938b220 | DAGDOG | kcc-23 | 24 | 20 | 800.000.000 | 52 | nicht gefunden |
| 299b50a700 | KSEAL | kcc-23 | 23 | 14 | 800.000.000 | 247 | nicht gefunden |
| 494e76ec08 | PRISM | genesis | 23 | 17 | 1.000.000.000 | 38 | nicht abgefragt |
| 5ef85ec7ef | DKANGO | genesis | 21 | 18 | 1.000.000.000 | 38 | nicht abgefragt |
| 1b8e34f33e | THEN | genesis | 20 | 19 | 1.000.000.000 | 44 | nicht abgefragt |
| 5cbdbc59f4 | WALLET | kcc-23 | 20 | 13 | 2.100.000.000.000.000 | 2 | gefunden |

Am Freitag wurde KRC-20 nur für KCC-23-Symbole abgefragt. Ab dem Samstagslauf auch für Ticker aus dem Genesis-Payload. Die vollständige Tabelle aller Tokens kommt am Montag als `kcc20/ergebnis/kcc20-tokens-2026-10-26.csv` (nur Summen je Token).

## Migration KRC-20 zu KCC-20

Der Weg je Token (Brücke über KaspaCom oder KAT, oder 1:1-Snapshot mit Airdrop) steht in keinem der Metadaten-Felder, die wir lesen. Einzige Ausnahme: Wobbly.k nennt `bridge_covenant_id` und `eth_vault`. Das ist eine Brücke, aber offenbar von Ethereum, nicht von KRC-20. **Der Weg ist deshalb bei allen Tokens "unbekannt".** Wo es dasselbe Symbol bei KRC-20 gibt, stehen am Montag beide Mengen nebeneinander, ausdrücklich ohne Aussage, dass es derselbe Token ist.

## Abgleich mit kcc20.info (source kcc20.info)

Stand 23.10. 14:32 UTC, aus deren öffentlicher API:
- 97 Tokens, 17.137 lebende UTXOs, 188.808 Covenants, 25.836 Token-Aktionen.
- Davon 81 "kron-native" (Kron, eigener Standard mit signiertem Namensregister) und 16 "legacy-kcc20" (Genesis zwischen DAA rund 494 und 515 Millionen, also deutlich vor dem 21.10.).

Unterschiede durch Definition, kein Fehler auf einer Seite:
1. **Andere Standards.** Alle 97 Token-IDs von kcc20.info haben bei uns lebende UTXOs, aber keinen Zustand in der finalen KCC-20-Kodierung. Umgekehrt führt kcc20.info keinen unserer 133 Tokens. Die Mengen sind also disjunkt: kcc20.info zählt Kron und ältere KCC-20-Vorläufer, wir zählen Tokens nach der seit 21.10. finalen KCC-20-Spezifikation.
2. **Lebende UTXOs.** Deren 17.137 sind alle lebenden Covenant-UTXOs, nicht nur Tokens. Unser Gegenstück sind 17.150 Covenant-UTXOs zur Stichzeit 14:30 UTC, zwei Minuten vor deren Abruf.
3. **Covenants.** Deren 188.808 zählen alle je gesehenen Covenant-Ausgänge seit Beginn ihres Archivs. Das zählen wir nicht.

## Antworten von Ben (24.10.) und was daraus folgt

1. **Kron:** Wo wir keine eigenen Daten haben, steht nur "source kcc20.info", nie "counted". Kron-Tokens erscheinen deshalb nur im Abgleich, mit Quelle.
2. **Transfers:** "counted" gilt nur ab unserem eigenen Knotenfenster, also ab 22.10.2026 05:53:20 UTC (07:53 Berlin). Umsetzung im Zähler (Commit 1478157):
   - Jede Tx in den Listen trägt jetzt ihre Quelle ("eigener knoten" oder "api.kaspa.org").
   - Der Zähler liest die Fenster aller Läufe (`tx-stand.json`) und zählt "counted" nur im lückenlosen eigenen Fenster bis zur Stichzeit. Hat das Fenster eine Lücke, beginnt "counted" erst nach der Lücke.
   - Neue Spalten und Felder: `transfers_counted` je Token, `transfers_counted_ab_utc`, `eigene_fenster_utc`, `transfers_vor_eigenem_fenster_nicht_counted`.
   - Die Läufe am Samstag, Sonntag und Montag schließen die Fenster bis Montag 12:00 UTC.
3. **Die Zeit davor (21.10. 00:00 bis 22.10. 05:53 UTC) als "source kcc20.info":** Deren Zeitreihe hat 6-Stunden-Blöcke, deren Grenzen am Abrufzeitpunkt hängen. Die Zeiten sind aus der DAA geschätzt (`daa_10bps`). Abruf 24.10. 06:26 UTC: 5 Blöcke von 21.10. 00:26 bis 22.10. 06:26 UTC, 165 Token-Aktionen und 3.005 Covenant-Ereignisse. Am Montag rufe ich um 11:53 UTC ab, dann endet ein Block genau um 05:53 UTC.

## Antwort von Ben (24.10.) zur Zeit vor dem eigenen Fenster

Die 165 Token-Aktionen von kcc20.info (Kron und ältere Tokens, source kcc20.info) stehen nur hier im Bericht, nicht im Post. Der Post trägt nur unsere eigene gezählte Zahl aus dem lückenlosen Knotenfenster.

## Was Ben tun muss

- Wünsche aus Discord #data-requests bis Montag vor dem Hauptlauf an mich geben. Ich prüfe sie vor dem Start um 10:30 UTC.
- Am Montag den fertigen Bericht, die Grafik und den Post prüfen.
- Den PR [#136](https://github.com/neoalphavault-png/kaspa-pulse/pull/136) mergen, wenn er passt. Die Workflows starten nur auf diesem Branch, auf main tun sie nichts.
