# Erste öffentliche KCC-20-Zählung vom eigenen Knoten

Bericht für Ben zu Aufgabe A vom 23.10.2026. Branch `fix/kcc20-zaehlung`, PR [#136](https://github.com/neoalphavault-png/kaspa-pulse/pull/136).

**Stichzeit Mo 26.10.2026 12:00 UTC**, Hauptlauf [40308051997](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40308051997). Unsere Zahlen tragen "counted". Fremde Zahlen tragen ihre Quelle ("source kcc20.info", "source kasplex", "api.kaspa.org").

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
| Transfers counted | nur aus dem eigenen, lückenlosen Knotenfenster: 22.10.2026 05:53:20 UTC bis Stichzeit, Zeit des annehmenden Kettenblocks |

## Ergebnis zur Stichzeit 26.10.2026 12:00 UTC (counted)

- **240 KCC-20-Tokens** mit 2.646 Halter-Outputs. 857 eindeutige Halter (1.863 je Token aufsummiert).
- **4.560 KCC-20-Transfers counted** zwischen 22.10. 05:53:20 UTC und der Stichzeit, jede Tx einmal. Je Token aufsummiert sind es 4.566, weil einzelne Transaktionen mehrere Tokens berühren.
- **Eigene Knotenfenster lückenlos:** 22.10. 05:53 bis 23.10. 15:10, 23.10. 05:54 bis 24.10. 12:40, 24.10. 05:58 bis 25.10. 12:17, 25.10. 06:06 bis 26.10. 12:17 UTC (Läufe 39967185904, 40087545641, 40186478752, 40308051997).
- Nicht counted: 1.281 Transfers zwischen 21.10. 00:00 und 22.10. 05:53 UTC. Diese Transaktionen kamen von api.kaspa.org (der KCC-20-Zustand ist auch dort von uns per Hash bewiesen). Zusammen 5.841 seit 21.10. 00:00 UTC.
- Zweitprüfung des Bestands identisch, 0 Fehler. Genesis für 240 von 240 Tokens per KIP-20-Covenant-ID bewiesen.
- Namen: 102 aus KCC-23, 132 aus dem JSON im Genesis-Payload (Launchpad-Format, kein KCC-23), 6 ohne Namen. Ticker sind nicht eindeutig (z.B. TEST, MOON, ROCKET mehrfach), deshalb steht immer die Covenant-ID davor.
- Lebende Covenant-UTXOs insgesamt 18.048. Davon 15.402 ohne finalen KCC-20-Zustand (andere Covenants, darunter alle 97 Tokens von kcc20.info). Bei 104 Tokens liegt je genau ein weiterer Output ohne Zustand unter derselben Covenant-ID (zusammen 889,50 KAS), vermutlich der Mint-Ausgang des Tokens; diese zählen nicht als Halter.

Vollständige Tabelle aller 240 Tokens, nur Summen je Token: `kcc20/ergebnis/kcc20-tokens-2026-10-26.csv`. Grafik: `kcc20/ergebnis/kcc20-grafik-2026-10-26.png` (1600x900).

Die 20 größten nach Halter-Outputs. Menge mit Dezimalstellen nur, wo die Metadaten sie nennen, sonst in Basiseinheiten.

| Covenant-ID | Ticker | Name aus | Halter-Outputs | Halter | Menge | Transfers counted | KRC-20 gleicher Ticker (source kasplex), geminted | Weg |
|---|---|---|---|---|---|---|---|---|
| d8c4356d20 | THEN | genesis-payload | 440 | 234 | 1.000.000.000 Basiseinheiten | 392 | nein | unbekannt |
| 3cb7bd371e | GUZA | genesis-payload | 353 | 200 | 1.000.000.000 Basiseinheiten | 353 | nein | unbekannt |
| cecb547d3a | TEK | kcc-23 | 181 | 88 | 800.000.000 (dec 0) | 315 | kein krc-20-ticker moeglich | unbekannt |
| efcf006e57 | BTE | genesis-payload | 131 | 80 | 1.000.000.000 Basiseinheiten | 210 | kein krc-20-ticker moeglich | unbekannt |
| 7cf4b45ebf | ROCKET | genesis-payload | 115 | 64 | 1.000.000.000 Basiseinheiten | 166 | ja, 1.234.567.890 | unbekannt |
| 244cd20dac | DAGAS | genesis-payload | 90 | 65 | 1.000.000.000 Basiseinheiten | 111 | ja, 21.000.000 | unbekannt |
| b75a6e90f5 | KB | genesis-payload | 80 | 46 | 1.000.000.000 Basiseinheiten | 112 | kein krc-20-ticker moeglich | unbekannt |
| 9f665e60a7 | LUCIFER | genesis-payload | 41 | 34 | 1.000.000.000 Basiseinheiten | 49 | kein krc-20-ticker moeglich | unbekannt |
| d5b7fd011e | ORPHAN | genesis-payload | 38 | 24 | 1.000.000.000 Basiseinheiten | 53 | nein | unbekannt |
| e22cebe470 | FROG | genesis-payload | 32 | 28 | 1.000.000.000 Basiseinheiten | 30 | ja, 210.000.000 | unbekannt |
| cbe213cecb | Wobbly.k | kcc-23 | 28 | 3 | 515 (dec 6) | 9 | kein krc-20-ticker moeglich | metadaten nennen bridge_covenant_id/eth_vault |
| 84dc7ecf0f | MISTYDAG | genesis-payload | 26 | 13 | 1.000.000.000 Basiseinheiten | 43 | kein krc-20-ticker moeglich | unbekannt |
| 1c30b57d79 | BFLY | genesis-payload | 25 | 25 | 1.000.000.000 Basiseinheiten | 49 | nein | unbekannt |
| 7f174f86e1 | KASX | kcc-23 | 25 | 14 | 800.000.000 (dec 0) | 177 | ja, 435.498 | unbekannt |
| ffc20f9076 | UNNACHOD | kcc-23 | 23 | 15 | 800.000.000 (dec 0) | 77 | kein krc-20-ticker moeglich | unbekannt |
| e6dd8f5a67 | RCAT | genesis-payload | 21 | 20 | 1.000.000.000 Basiseinheiten | 3 | nein | unbekannt |
| 1b8e34f33e | THEN | genesis-payload | 20 | 19 | 1.000.000.000 Basiseinheiten | 13 | nein | unbekannt |
| 5cbdbc59f4 | WALLET | kcc-23 | 20 | 13 | 21.000.000 (dec 8) | 0 | ja, 100.000.000 | unbekannt |
| 5ef85ec7ef | DKANGO | genesis-payload | 20 | 18 | 1.000.000.000 Basiseinheiten | 12 | nein | unbekannt |
| 5fe878ecc6 | JFROG | genesis-payload | 20 | 13 | 1.000.000.000 Basiseinheiten | 30 | nein | unbekannt |

## Post-Entwurf für X (@gokugalax)

> counted on our own kaspa node at 12:00 utc on 26 oct. 240 kcc-20 tokens, 2,646 holder outputs, 857 unique holders and 4,560 kcc-20 transfers since 22 oct 05:53 utc. every amount is proven by hash against the chain state.

220 Zeichen. Geprüft mit den Textregeln der Tagesgrafik (`pruefe_eine`): kein Gedankenstrich, kein Doppelpunkt außer in Uhrzeiten, kein Pfeil, keine Echtzeitwörter, keine Preise. Nur unsere Zahlen, deshalb nur "counted".

## Migration KRC-20 zu KCC-20

Der Weg je Token (Brücke über KaspaCom oder KAT, oder 1:1-Snapshot mit Airdrop) steht in keinem der Metadaten-Felder, die wir lesen. Einzige Ausnahme: Wobbly.k nennt `bridge_covenant_id` und `eth_vault`. Das ist eine Brücke, aber offenbar von Ethereum, nicht von KRC-20. **Der Weg ist deshalb bei allen Tokens "unbekannt".** Bei 62 Tokens gibt es denselben Ticker bei KRC-20 (source kasplex), bei 108 nicht, bei 64 ist der Ticker als KRC-20-Ticker nicht möglich, 6 haben keinen. Die Tabelle stellt bei den 62 die geminte KRC-20-Menge neben die KCC-20-Menge, ausdrücklich ohne Aussage, dass es derselbe Token ist. Mehrere KCC-20-Tokens teilen sich denselben Ticker.

## Abgleich mit kcc20.info (source kcc20.info)

Stand 26.10. 11:59 UTC, aus deren öffentlicher API: 97 Tokens, 18.031 lebende UTXOs, 189.069 Covenants, 26.004 Token-Aktionen. Am 23.10. 14:32 UTC waren es 97 Tokens, 17.137 lebende UTXOs, 188.808 Covenants, 25.836 Token-Aktionen.
- Aufteilung der 97 (Stand 23.10.):
- Davon 81 "kron-native" (Kron, eigener Standard mit signiertem Namensregister) und 16 "legacy-kcc20" (Genesis zwischen DAA rund 494 und 515 Millionen, also deutlich vor dem 21.10.).

Unterschiede durch Definition, kein Fehler auf einer Seite:
1. **Andere Standards.** Alle 97 Token-IDs von kcc20.info haben bei uns lebende UTXOs, aber keinen Zustand in der finalen KCC-20-Kodierung. Umgekehrt führt kcc20.info keinen unserer Tokens (geprüft am 23.10. mit 133 und am 26.10. mit 240). Die Mengen sind also disjunkt: kcc20.info zählt Kron und ältere KCC-20-Vorläufer, wir zählen Tokens nach der seit 21.10. finalen KCC-20-Spezifikation.
2. **Lebende UTXOs.** Deren 18.031 (26.10. 11:59 UTC) sind alle lebenden Covenant-UTXOs, nicht nur Tokens. Unser Gegenstück sind 18.048 Covenant-UTXOs zur Stichzeit 12:00 UTC.
3. **Covenants.** Deren 188.808 zählen alle je gesehenen Covenant-Ausgänge seit Beginn ihres Archivs. Das zählen wir nicht.

## Antworten von Ben (24.10.) und was daraus folgt

1. **Kron:** Wo wir keine eigenen Daten haben, steht nur "source kcc20.info", nie "counted". Kron-Tokens erscheinen deshalb nur im Abgleich, mit Quelle.
2. **Transfers:** "counted" gilt nur ab unserem eigenen Knotenfenster, also ab 22.10.2026 05:53:20 UTC (07:53 Berlin). Umsetzung im Zähler (Commit 1478157):
   - Jede Tx in den Listen trägt jetzt ihre Quelle ("eigener knoten" oder "api.kaspa.org").
   - Der Zähler liest die Fenster aller Läufe (`tx-stand.json`) und zählt "counted" nur im lückenlosen eigenen Fenster bis zur Stichzeit. Hat das Fenster eine Lücke, beginnt "counted" erst nach der Lücke.
   - Neue Spalten und Felder: `transfers_counted` je Token, `transfers_counted_ab_utc`, `eigene_fenster_utc`, `transfers_vor_eigenem_fenster_nicht_counted`.
   - Die Läufe am Samstag, Sonntag und Montag schließen die Fenster bis Montag 12:00 UTC.
3. **Die Zeit davor (21.10. 00:00 bis 22.10. 05:53 UTC), source kcc20.info:** Abruf 26.10. 11:52 UTC aus deren Zeitreihe (6-Stunden-Blöcke, Zeiten aus der DAA geschätzt): 181 Token-Aktionen und 3.810 Covenant-Ereignisse in 5 Blöcken mit Zeitstempeln von 21.10. 05:52 bis 22.10. 05:52 UTC. kcc20.info dokumentiert nicht, ob der Zeitstempel Anfang oder Ende eines Blocks ist; der Zeitraum ist also entweder 20.10. 23:52 bis 22.10. 05:52 oder 21.10. 05:52 bis 22.10. 11:52 UTC. Die Zahl gilt für deren Tokens (Kron und ältere), nicht für die finalen KCC-20-Tokens. Abruf vom 24.10. 06:26 UTC zum Vergleich: 165 und 3.005.

## Antwort von Ben (24.10.) zur Zeit vor dem eigenen Fenster

Die Token-Aktionen von kcc20.info (Kron und ältere Tokens, source kcc20.info) stehen nur hier im Bericht, nicht im Post. Der Post trägt nur unsere eigene gezählte Zahl aus dem lückenlosen Knotenfenster.

## Offene Fragen an Ben

Keine. Aus Discord #data-requests kamen vor dem Hauptlauf keine Wünsche.

## Was Ben tun muss

- Tabelle, Grafik und Post-Entwurf prüfen, dann posten.
- Den PR [#136](https://github.com/neoalphavault-png/kaspa-pulse/pull/136) mergen, wenn er passt. Die Workflows starten nur auf diesem Branch, auf main tun sie nichts.
