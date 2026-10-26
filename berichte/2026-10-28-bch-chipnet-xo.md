# BCH chipnet und XO, Machbarkeit und erste Zählung (Stand 26.10.2026)

Auftrag Ben, Mo 26.10.2026. Frist Mi 28.10. 17:00 UTC. Branch `messung/bch-chipnet-xo`.

Der Tempnet-Mitschnitt für den Forumsbeitrag am 28.10. läuft unverändert weiter. Er ist eine eigene Kette von Läufen, und dieser Auftrag hat ihn nicht berührt.

## Kurz

- **Was XO ist:** XO kommt von General Protocols. Es ist eine Wallet- und Engine-Schicht, die Transaktionen aus Wallet-Templates baut, kein eigenes Vertragsprotokoll.
- **Kein XO-Fingerabdruck:** XO-Transaktionen lassen sich auf chipnet **nicht eindeutig erkennen**. XO setzt keinen eigenen Marker, also kein OP_RETURN-Präfix und keine eigene Token-Kategorie. Die veröffentlichten Templates bauen gewöhnliche P2PKH-, Multisig- und Faucet-Transaktionen.
- **Ein fester Fingerabdruck:** Nur das Template „Wrapped BCH (chipnet)“ hat einen. Es nutzt die wBCH-Token-Kategorie und den wrapped.cash-Covenant. Gezählt: 17 solche Transaktionen seit 01.10., davon 13 am 25.10. Das sind wBCH-Transaktionen, nicht zwingend XO-Transaktionen.
- **Blockabstände:** Chipnet-Header über unseren eigenen Client, 3.750 Abstände seit 01.10. Die Gegenprobe mit 2 Peers anderer Software ergab je 500 von 500 gleich.
- **Der Schwanz ist abgeschnitten:** Jede Lücke über 20 min endete mit einem Block mit Mindestschwierigkeit, insgesamt 790. Die längste Lücke war 2.223 s, berechnet für eine ideale 600-s-Kette sind es 5.284 s. Für XO heißt das: Eine Einlösung wartete in 99 von 100 Fällen höchstens 1.312 s, berechnet sind es 2.763 s.

## 1. Quellen

Nur Primärquellen. Was ich nicht selbst einsehen konnte, steht unter „offen“.

| Frage | Befund | Quelle |
|---|---|---|
| Was ist XO | „XO templates“, „The XO engine“, „The coordinator server for XO apps“; Pakete `@xo-cash/*`, Herausgeber `generalprotocols`, MIT-Lizenz, Hinweis „early development phase … Do not use funds you are not willing to lose“ | npm `@xo-cash/templates` 0.0.11 (08.10.2026), `@xo-cash/engine`; GitLab `GeneralProtocols/xo` (15 öffentliche Projekte, letzte Aktivität 26.10.2026) |
| Wie XO arbeitet | Die Engine importiert Wallet-Templates (Schema `libauth.org/schemas/wallet-template-v0`), erzeugt daraus „Invitations“, die eine externe XO-Wallet füllt und signiert, und spricht über Electrum-Server mit der Kette | README `GeneralProtocols/xo/engine`, README `GeneralProtocols/xo/dapps/wrapped-cash` |
| Templates heute | `p2pkhTemplate`, `multisigTemplate` (2 von 3), `faucetCashTemplate`, `wrapBCHTemplate` (mainnet), `wrapBCHChipnetTemplate` („Convert between BCH and wBCH tokens on the chipnet“) | `@xo-cash/templates` 0.0.11, Exporte; Repo-Stand `40dc8ca` |
| Wiederkehrende, bedingte Zahlungen, Liquiditätspools | In den öffentlichen Templates und in der Engine nicht enthalten. „Liquidity“ kommt nur in der wBCH-Oberfläche vor, gemeint ist der Covenant-Bestand. | Volltextsuche in `templates`, `engine`, `dapps/wrapped-cash` |
| Software auf chipnet | Unsere chipnet-Peers meldeten Bitcoin Cash Node 29.2.0 und 28.0.2 sowie Rapids 2026-10. Laut BCHN master gilt für chipnet `nPowTargetSpacing = 10 * 60`, `fPowAllowMinDifficultyBlocks = true` (Regel: Mindestschwierigkeit nach 2 × 600 s ohne Block), ASERT-Halbwertszeit 1 h und `upgrade2027ActivationTime = 1794744000` (15.11.2026 12:00 UTC, „tentative protocol upgrade activates 6 months early“). | Handschlag unseres Clients; BCHN `src/chainparams.cpp`, `src/pow.cpp` (master, gelesen 26.10.2026) |
| Öffentliche chipnet-Endpunkte | Für Electrum gibt es eine öffentliche Liste mit chipnet-Servern im npm-Paket `@electrum-cash/servers` 4.2.0, das die XO-Engine nutzt. Für P2P stehen 2 Seeds in den BCHN-chainparams. Namen nenne ich nicht. | npm `@electrum-cash/servers`, BCHN chainparams |
| Anleitung | Eine Anleitung zur Nutzung von XO auf chipnet habe ich nicht gefunden. Die READMEs beschreiben Installation und Entwicklung, das wBCH-Dapp nennt einen Sync-Relay-Dienst. | GitLab-READMEs |

**Offen:**
- **Ankündigung vom 25.10.:** Die Posts von @BitcoinCashOG bzw. @BitcoinCashBCH konnte ich nicht lesen, x.com ist von hier nicht erreichbar.
- **Projektseite:** xo.cash sperrt der Proxy. Laut Regel nicht umgangen.
- **Zitat Jonathan Silverblood:** XO ist auf chipnet bereit, auf tempnet bräuchte es eine manuell bereitgestellte ElectrumServerWithBlockchain. Das stammt aus deinem Auftrag und ist von mir nicht geprüft.
- **1-Minuten-Blöcke auf chipnet ab 15.11.:** In BCHN master steht für chipnet nur der Aktivierungszeitpunkt. Eine Änderung des Zielabstands auf 60 s ist dort nicht enthalten. Wie tempnet ab dem Lock-in auf chipnet umleitet, ist für mich offen.

## 2. Chipnet-Zählung seit 01.10.2026

**Methode:**
- Eigener Header-Client (`scripts/bch/chipnet_koepfe.py`). Die Peers kommen aus den BCHN-chainparams für chipnet.
- Ein Peer zählt nur, wenn er nach dem letzten gemeinsamen Block 327.988 nicht den Tempnet-Block liefert. Chipnet und Tempnet teilen Magic und Port.
- Geprüft werden die Verkettung, der Arbeitsnachweis aus nBits und die BCHN-Checkpoints. Start ist der Checkpoint 313.653.

**Prüfung:**
- Abruf 26.10.2026 08:05 UTC, Spitze 329.540. Die Zielhöhe stammt von 4 chipnet-Peers; ein Peer wurde abgelehnt.
- Kein Peer-Fehler, kein verworfener Zweig.
- Gegenprobe mit Bitcoin Cash Node 29.2.0 und Rapids: je 500 von 500 Hashes gleich.

Blöcke 325.791 bis 329.540, 01.10.2026 00:01 bis 26.10.2026 08:02 UTC, 3.750 Abstände. Computed gilt für eine ideale Kette mit 600 s und exponentiellen Abständen, ohne die Mindestschwierigkeits-Regel.

| Kennzahl | counted | computed (600 s) |
|---|---:|---:|
| Mittel | 583,8 s | 600 s |
| Median | 471,0 s | 415,9 s |
| p90 | 1.216 s | 1.381,6 s |
| p99 | 1.503 s | 2.763,1 s |
| Anteil über 5 min | 62,48 % | 60,65 % |
| Anteil über 20 min | 21,07 % | 13,53 % |
| Längste Lücke | 2.223 s (vor Block 326.691, 07.10. 06:38 UTC) | 5.284 s |
| Blöcke mit Mindestschwierigkeit (nBits 0x1d00ffff) | 790 (21,07 %) | im Modell 0 |
| MTP-Abstand Median / p90 / p99 | 3.497,5 / 5.124,3 / 8.069,2 s | 3.404,1 / 5.552,8 / 7.821,2 s |
| Wartezeit ab Zufallszeitpunkt Median / p90 / p99 | 399 / 1.009 / 1.312 s | 415,9 / 1.381,6 / 2.763,1 s |
| Negative Abstände | 57 | 0 |

| ISO-Woche | Abstände | Mittel | Median | Mindestschwierigkeit |
|---|---:|---:|---:|---:|
| 2026-W40 | 576 | 599,8 s | 514,5 s | 89 |
| 2026-W41 | 1.112 | 544,2 s | 397,0 s | 205 |
| 2026-W42 | 998 | 605,0 s | 519,5 s | 227 |
| 2026-W43 | 1.018 | 594,3 s | 465,0 s | 256 |
| 2026-W44 (bis 26.10. 08:02) | 46 | 649,1 s | 615,0 s | 13 |

Beobachtungen aus den Köpfen:
- **Die 20-Minuten-Regel hält den Schwanz kurz:** Alle 790 Blöcke mit Mindestschwierigkeit kamen nach mehr als 1.200 s (kürzester Abstand 1.201 s, Median 1.215,5 s). Kein anderer Block kam nach mehr als 1.198 s.
- **Mehr lange Abstände, aber kürzere Wartezeiten:** Der Anteil über 20 min liegt über der Rechnung (21,07 % gegen 13,53 %), die Wartezeiten im p99 und die längste Lücke liegen deutlich darunter.
- **Wartezeit für XO:** Ein zufälliger Zeitpunkt, etwa eine eingereichte Einlösung, wartete im Median 399 s und in 99 von 100 Fällen höchstens 1.312 s auf den nächsten Block. Raster 10 s über das ganze Fenster.
- **Was nach dem 15.11. folgt, ist offen:** Kommt der Zielabstand von 60 s, liegt die Schwelle der Regel nach `pow.cpp` bei 2 × 60 s. Das ist eine Rechnung, keine Zählung.
- **Negative Abstände:** 57. Das sind Zeitstempel, die vor denen des Vorgängers liegen, im Rahmen der Regeln. Nur einer folgt auf einen Block mit Mindestschwierigkeit.

## 3. XO auf der Kette

**Nicht eindeutig erkennbar.** XO setzt keinen eigenen Marker. Ich habe die Templates, die Engine und das wBCH-Dapp nach OP_RETURN, Präfix und Marker durchsucht und nichts gefunden. Eine mit `p2pkhTemplate` oder `multisigTemplate` gebaute Transaktion sieht auf der Kette aus wie jede andere P2PKH- oder 2-von-3-Transaktion.

**Was sich erkennen lässt:** das Template „Wrapped BCH (chipnet)“. Es hat zwei feste Merkmale:
- Token-Kategorie `bb61cd7a6c8a3a3742d965dc7ac73c1117382a5c8930b68338deb881f75c0214` (Konstante `wbchTokenCategory`)
- ein Covenant-Skript ohne Parameter (`wrapBCHLockingBytecode`, als Bytecode `c0cdc0c788c0d1c0ce88c0d0c0c693c0d3c0cc939c`)

**Gezählt** (`scripts/bch/chipnet_wbch.py`):
- 3.750 volle Blöcke von einem chipnet-Peer, 356.562 Transaktionen gelesen.
- **17 Transaktionen** mit dieser Kategorie und einer Covenant-Ausgabe, alle mit der Kategorie in interner Byte-Reihenfolge.
- Verteilung: 07.10. 1, 17.10. 1, 23.10. 2, 25.10. 13.

Das ist der wrapped.cash-Covenant, den jede Wallet benutzen kann. Ob eine dieser Transaktionen über XO entstand, lässt sich aus der Kette nicht sagen.

**Abstand erstes Sehen bis Bestätigung je Transaktion:** nicht gemessen. Dafür bräuchte es einen Zuhörer auf chipnet, der Transaktions-Ankündigungen mitschreibt, wie der Tempnet-Zuhörer. Rückwirkend geht das nicht. Für wBCH-Transaktionen wäre er ab sofort machbar, für XO-Transaktionen erst mit einem Erkennungsmerkmal.

## 4. Offene Fragen an das XO-Team

1. Gibt es ein Merkmal, an dem sich XO-Transaktionen auf der Kette erkennen lassen, etwa ein OP_RETURN-Präfix, eine Token-Kategorie oder feste Locking-Skripte?
2. Welche Templates für wiederkehrende und bedingte Zahlungen sowie Liquiditätspools sind auf chipnet im Einsatz, und wo sind sie veröffentlicht?
3. Läuft der wBCH-Covenant auf chipnet unter der Kategorie `bb61cd7a…0214` als offizielle XO-Demo, und stammen die 13 Transaktionen vom 25.10. aus XO?
4. Ab welcher Bestätigungszahl gilt eine XO-Einlösung als abgeschlossen?
5. Gibt es eine Anleitung, mit der Außenstehende XO auf chipnet ohne eigenen Server ausprobieren können?

## 5. Vorschlag PH-Post

Beide Entwürfe haben die Regelprüfung von `scripts/ph/ph_entwurf.py` bestanden. Ohne Preise. Welche Buchstaben-Formate A und F genau meinen, habe ich hier nicht vorliegen. Ich habe A als den Zahlen-Post zum Schwanz und F als den Post mit XO-Bezug gelesen. Bitte korrigieren, falls das falsch ist.

**Format A (Schwanz der Abstände)**
```
bch chipnet with ten minute blocks, ahead of the 15 nov upgrade.
we counted 3,750 block intervals since 1 oct with a p99 of 1,503 s, against 2,763 s computed for an ideal 600 s chain.
every gap longer than 20 min ended with a minimum difficulty block, 790 of them, and the longest gap stayed at 2,223 s.
window 1 oct 2026, 00:01 to 26 oct 2026, 08:02 utc, blocks 325,791 to 329,540.
method on pulsehawk.io
```

**Format F (XO-Bezug)**
```
bch chipnet ahead of the 15 nov upgrade.
we counted 17 transactions since 1 oct that use the wrapped bch covenant xo ships as its chipnet template, 15 of them in the last seven days.
a transaction sent at a random moment waited 1,312 s for a block in 99 of 100 cases, against 2,763 s computed for an ideal 600 s chain.
window 1 oct 2026, 00:01 to 26 oct 2026, 08:02 utc, blocks 325,791 to 329,540.
method on pulsehawk.io
```

Bei F ist eine Formulierung heikel. „xo ships“ stimmt für das Template, die Transaktionen selbst ordnet der Post XO nicht zu. Wenn das zu nah an einer Zuordnung ist, nimm A.

## 6. Dateien

- Skripte: `scripts/bch/chipnet_koepfe.py`, `scripts/bch/chipnet_auswertung.py`, `scripts/bch/chipnet_wbch.py`
- Workflow: `.github/workflows/bch-chipnet.yml`. Er läuft nur auf diesem Branch und startet bei einem Push auf die Skripte oder auf `data/bch-chipnet/anstoss.txt`.
- Daten auf diesem Branch: `data/bch-chipnet/koepfe.csv.gz`, `koepfe-meta.json`, `stand-2026-10-26.json` und `.md`, `wbch-2026-10-26.json` (mit Transaktions-IDs, keine Adressen)

## Was Ben tun muss

- **Postentwurf:** A oder F wählen und das Format bestätigen.
- **Zuhörer auf chipnet:** Entscheiden, ob einer für Transaktions-Ankündigungen laufen soll. Damit ließe sich für wBCH-Transaktionen der Abstand zwischen erstem Sehen und Bestätigung messen.
- **Fragen an das XO-Team:** über unsere Kanäle weitergeben, wenn gewünscht. Ich poste und schreibe nichts.
- **Kein Merge nötig:** Der Branch ist ein Messbranch, der Workflow läuft dort.

Am Mi 28.10. lasse ich die Zählung vor der Frist noch einmal laufen und ziehe die Zahlen in diesem Bericht nach.
