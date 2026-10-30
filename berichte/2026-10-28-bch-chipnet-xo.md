# BCH chipnet und XO, Machbarkeit und Zählung (Stand 28.10.2026)

Auftrag Ben, Mo 26.10.2026. Frist Mi 28.10. 17:00 UTC. Branch `messung/bch-chipnet-xo`.

Der Tempnet-Mitschnitt für den Forumsbeitrag am 28.10. läuft unverändert weiter. Er ist eine eigene Kette von Läufen, und dieser Auftrag hat ihn nicht berührt.

## Kurz

- **Was XO ist:** XO kommt von General Protocols. Es ist eine Wallet- und Engine-Schicht, die Transaktionen aus Wallet-Templates baut, kein eigenes Vertragsprotokoll.
- **Kein XO-Fingerabdruck:** XO-Transaktionen lassen sich auf chipnet **nicht eindeutig erkennen**. XO setzt keinen eigenen Marker, also kein OP_RETURN-Präfix und keine eigene Token-Kategorie. Die veröffentlichten Templates bauen gewöhnliche P2PKH-, Multisig- und Faucet-Transaktionen.
- **Ein fester Fingerabdruck:** Nur das Template „Wrapped BCH (chipnet)“ hat einen. Es nutzt die wBCH-Token-Kategorie und den wrapped.cash-Covenant. Gezählt: 17 solche Transaktionen seit 01.10., davon 13 am 25.10. Seit dem 25.10. 15:02 UTC kam bis zum Abruf am 28.10. 14:07 UTC keine weitere dazu. Das sind wBCH-Transaktionen, nicht zwingend XO-Transaktionen.
- **Blockabstände:** Chipnet-Header über unseren eigenen Client, 4.076 Abstände seit 01.10. Die Gegenprobe mit 3 Peers ergab je 500 von 500 gleich.
- **Der Schwanz ist abgeschnitten:** Jede Lücke über 20 min endete mit einem Block mit Mindestschwierigkeit, insgesamt 855. Die längste Lücke war 2.223 s, berechnet für eine ideale 600-s-Kette sind es 5.334 s. Für XO heißt das: Eine Einlösung wartete in 99 von 100 Fällen höchstens 1.299 s, berechnet sind es 2.763 s.

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
- Abruf 28.10.2026 14:07 UTC (Lauf [40702796242](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40702796242), Bot-Commit `5ab8ccc`), Spitze 329.866. Die Zielhöhe stammt von 4 chipnet-Peers; diesmal lieferte keine Probe den Tempnet-Block.
- Kein Peer-Fehler, kein verworfener Zweig.
- Gegenprobe mit Bitcoin Cash Node 28.0.2(EB2.0), Bitcoin Cash Node 29.0.0(EB2.0) und Rapids: je 500 von 500 Hashes gleich.
- Keine Adressen und keine Hostnamen in Daten und Log, der Secret-Scan im Lauf war sauber.
- Stand 26.10. zum Vergleich: Spitze 329.540, 3.750 Abstände, p99 1.503 s, 790 Blöcke mit Mindestschwierigkeit, Wartezeit p99 1.312 s.

Blöcke 325.791 bis 329.866, 01.10.2026 00:01 bis 28.10.2026 14:06 UTC, 4.076 Abstände. Computed gilt für eine ideale Kette mit 600 s und exponentiellen Abständen, ohne die Mindestschwierigkeits-Regel.

| Kennzahl | counted | computed (600 s) |
|---|---:|---:|
| Mittel | 584,8 s | 600 s |
| Median | 472,0 s | 415,9 s |
| p90 | 1.216 s | 1.381,6 s |
| p99 | 1.493 s | 2.763,1 s |
| Anteil über 5 min | 62,78 % | 60,65 % |
| Anteil über 20 min | 20,98 % | 13,53 % |
| Längste Lücke | 2.223 s (vor Block 326.691, 07.10. 06:38 UTC) | 5.334 s |
| Blöcke mit Mindestschwierigkeit (nBits 0x1d00ffff) | 855 (20,98 %) | im Modell 0 |
| MTP-Abstand Median / p90 / p99 | 3.500,5 / 5.096,0 / 8.042,5 s | 3.404,1 / 5.552,8 / 7.821,2 s |
| Wartezeit ab Zufallszeitpunkt Median / p90 / p99 | 397 / 1.005 / 1.299 s | 415,9 / 1.381,6 / 2.763,1 s |
| Negative Abstände | 58 | 0 |

| ISO-Woche | Abstände | Mittel | Median | Mindestschwierigkeit |
|---|---:|---:|---:|---:|
| 2026-W40 | 576 | 599,8 s | 514,5 s | 89 |
| 2026-W41 | 1.112 | 544,2 s | 397,0 s | 205 |
| 2026-W42 | 998 | 605,0 s | 519,5 s | 227 |
| 2026-W43 | 1.018 | 594,3 s | 465,0 s | 256 |
| 2026-W44 (bis 28.10. 14:06) | 372 | 603,4 s | 510,5 s | 78 |

Beobachtungen aus den Köpfen:
- **Die 20-Minuten-Regel hält den Schwanz kurz:** Alle 855 Blöcke mit Mindestschwierigkeit kamen nach mehr als 1.200 s (kürzester Abstand 1.201 s, Median 1.215 s). Kein anderer Block kam nach mehr als 1.199 s.
- **Mehr lange Abstände, aber kürzere Wartezeiten:** Der Anteil über 20 min liegt über der Rechnung (20,98 % gegen 13,53 %), die Wartezeiten im p99 und die längste Lücke liegen deutlich darunter.
- **Wartezeit für XO:** Ein zufälliger Zeitpunkt, etwa eine eingereichte Einlösung, wartete im Median 397 s und in 99 von 100 Fällen höchstens 1.299 s auf den nächsten Block. Raster 10 s über das ganze Fenster.
- **Was nach dem 15.11. folgt, ist offen:** Kommt der Zielabstand von 60 s, liegt die Schwelle der Regel nach `pow.cpp` bei 2 × 60 s. Das ist eine Rechnung, keine Zählung.
- **Negative Abstände:** 58. Das sind Zeitstempel, die vor denen des Vorgängers liegen, im Rahmen der Regeln. Nur einer folgt auf einen Block mit Mindestschwierigkeit.

## 3. XO auf der Kette

**Nicht eindeutig erkennbar.** XO setzt keinen eigenen Marker. Ich habe die Templates, die Engine und das wBCH-Dapp nach OP_RETURN, Präfix und Marker durchsucht und nichts gefunden. Eine mit `p2pkhTemplate` oder `multisigTemplate` gebaute Transaktion sieht auf der Kette aus wie jede andere P2PKH- oder 2-von-3-Transaktion.

**Was sich erkennen lässt:** das Template „Wrapped BCH (chipnet)“. Es hat zwei feste Merkmale:
- Token-Kategorie `bb61cd7a6c8a3a3742d965dc7ac73c1117382a5c8930b68338deb881f75c0214` (Konstante `wbchTokenCategory`)
- ein Covenant-Skript ohne Parameter (`wrapBCHLockingBytecode`, als Bytecode `c0cdc0c788c0d1c0ce88c0d0c0c693c0d3c0cc939c`)

**Gezählt** (`scripts/bch/chipnet_wbch.py`):
- 4.076 volle Blöcke von einem chipnet-Peer (Bitcoin Cash Node 28.0.2(EB2.0)), 409.381 Transaktionen gelesen, keine Abbrüche.
- **17 Transaktionen** mit dieser Kategorie und einer Covenant-Ausgabe, alle mit der Kategorie in interner Byte-Reihenfolge.
- Verteilung: 07.10. 1, 17.10. 1, 23.10. 2, 25.10. 13. Die letzte stand in Block 329.444 (25.10. 15:02 UTC), danach keine mehr bis 329.866.
- Liste mit Transaktions-IDs, Höhe und Zeit: `data/bch-chipnet/wbch-2026-10-28.json` (keine Adressen).

Das ist der wrapped.cash-Covenant, den jede Wallet benutzen kann. Ob eine dieser Transaktionen über XO entstand, lässt sich aus der Kette nicht sagen.

**Abstand erstes Sehen bis Bestätigung je Transaktion:** nicht gemessen. Dafür bräuchte es einen Zuhörer auf chipnet, der Transaktions-Ankündigungen mitschreibt, wie der Tempnet-Zuhörer. Rückwirkend geht das nicht. Für wBCH-Transaktionen wäre er ab sofort machbar, für XO-Transaktionen erst mit einem Erkennungsmerkmal.

## 4. Offene Fragen an das XO-Team

1. Gibt es ein Merkmal, an dem sich XO-Transaktionen auf der Kette erkennen lassen, etwa ein OP_RETURN-Präfix, eine Token-Kategorie oder feste Locking-Skripte?
2. Welche Templates für wiederkehrende und bedingte Zahlungen sowie Liquiditätspools sind auf chipnet im Einsatz, und wo sind sie veröffentlicht?
3. Läuft der wBCH-Covenant auf chipnet unter der Kategorie `bb61cd7a…0214` als offizielle XO-Demo, und stammen die 13 Transaktionen vom 25.10. aus XO?
4. Ab welcher Bestätigungszahl gilt eine XO-Einlösung als abgeschlossen?
5. Gibt es eine Anleitung, mit der Außenstehende XO auf chipnet ohne eigenen Server ausprobieren können?

## 5. Vorschlag PH-Post

Beide Entwürfe folgen deinen Format-Definitionen vom 26.10.:
- **A, Messung:** ein Netz, ein gezählter Wert mit Vergleich, eine Zeile Deutung, Grafik „Data from PulseHawk“.
- **F, wie wir zählen:** eine Methodenentscheidung mit einer Grafik.

Am 28.10. habe ich beide erneut gegen `regel_pruefen` aus `scripts/ph/ph_entwurf.py` (Stand main) geprüft, ohne Fund. Kein Satz beginnt mit einer Ziffer, das habe ich selbst geprüft. Beide enthalten keine Preise und keinen XO-Bezug. Der frühere F-Entwurf mit „xo ships“ ist ersetzt, weil F eine Methodenentscheidung zeigen soll.

**Format A (Schwanz der Abstände)**, 381 Zeichen
```
bch chipnet with ten minute blocks, ahead of the 15 nov upgrade.
we counted 4,076 block intervals since 1 oct with a p99 of 1,493 s, against 2,763 s computed for an ideal 600 s chain.
every gap longer than 20 min ended with a minimum difficulty block, which keeps the tail short.
window 1 oct 2026, 00:01 to 28 oct 2026, 14:06 utc, blocks 325,791 to 329,866.
method on pulsehawk.io
```

**Format F (Vergleich ohne die 20-Minuten-Regel)**, 393 Zeichen. Als Grafik würden sich die gezählte und die berechnete Verteilung der Abstände übereinander eignen, mit der Linie bei 1.200 s.
```
bch chipnet ahead of the 15 nov upgrade, and how we compare it.
we counted 855 of 4,076 blocks since 1 oct at minimum difficulty, each one after a gap of more than 20 min.
our computed values assume an ideal 600 s chain without that rule, so the distance to them shows what the rule changes.
window 1 oct 2026, 00:01 to 28 oct 2026, 14:06 utc, blocks 325,791 to 329,866.
method on pulsehawk.io
```

## Format F, Stand 30.10.

Bens Entscheidung vom 28.10.: F geht als PulseHawk-Post am Sa 31.10. um 16:30 Berlin raus. A wird nicht gepostet. Die Wartezeit geht als Antwort an Jonathan Silverblood, Frage 1 an das XO-Team stellt Ben. Ein Zuhörer auf chipnet läuft vorerst nicht.

**Neuer Kopf**
- **Zählung:** Lauf [41030633445](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41030633445) am 30.10.2026, Abruf 09:03:34 UTC, grün, Bot-Commit `d628009`.
- **Prüfung:** Gegenprobe mit 3 Peers, je 500 von 500 Hashes gleich. Keine Adressen in Daten und Log.
- **Kette:** Blöcke 325.791 bis 330.124, 01.10. 00:01 bis 30.10. 09:00 UTC, 4.334 Abstände.

| Kennzahl | counted | computed (600 s) |
|---|---:|---:|
| Median | 471 s | 415,9 s |
| p90 | 1.215 s | 1.381,6 s |
| p99 | 1.480,7 s | 2.763,1 s |
| Anteil über 20 min | 21,25 % | 13,53 % |
| Blöcke mit Mindestschwierigkeit | 921, alle nach mehr als 1.200 s | im Modell 0 |
| Längste Lücke | 2.223 s (07.10.) | |
| Wartezeit ab Zufallszeitpunkt Median / p90 / p99 | 397 / 1.004 / 1.291 s | 415,9 / 1.381,6 / 2.763,1 s |
| wBCH-Transaktionen seit 01.10. | 17, keine neue seit 25.10. | |

**Text** (264 Zeichen, wie X zählt, der Link mit 23. Ohne Link-Zählung 253 Zeichen):

```
bch chipnet, and how we compare it.
we counted 921 of 4,334 blocks since 1 oct at minimum difficulty, all after gaps over 20 min.
our computed line is an ideal 600 s chain without that rule.
window 1 oct 00:01 to 30 oct 09:03 utc.
method on pulsehawk.io
```

**Prüfung des Textes**
- `regel_pruefen` aus `scripts/ph/ph_entwurf.py` meldet keinen Fund.
- Selbst geprüft:
  - kein Satzanfang mit Ziffer, kein XO-Bezug, keine Preise
  - Doppelpunkte nur in Uhrzeiten, keine Gedankenstriche und keine Pfeile
  - kein now, live oder today
- Das Fenster nennt Enddatum und UTC-Uhrzeit, die letzte Zeile ist „method on pulsehawk.io“.

**Grafiken** auf `messung/bch-chipnet-xo`:
- `data/bch-chipnet/format-f-2026-10-30/format-f-1600x900.png`
- `data/bch-chipnet/format-f-2026-10-30/format-f-1080x1350.png`

Inhalt: gezählte Verteilung der Abstände, Blöcke mit Mindestschwierigkeit dunkler, darüber die berechnete Kurve für ideale 600 s, senkrechte Linie bei 1.200 s, Falke, „Data from PulseHawk“, Fenster unten. Beide habe ich auf 390 px Breite angesehen: lesbar, nichts abgeschnitten.

**Zwei Entwürfe in #ph-entwuerfe**, je HTTP 200:
- 09:02 UTC, der erste: Im Hochformat stand der Titel nur 18 px vor dem rechten Rand, weil die Schrift auf dem Runner breiter ist als lokal.
- 09:05 UTC, der gültige: mit kleinerem Titel.

Bitte den zweiten nehmen. Die Zahlen sind in beiden gleich, nur die Uhrzeit im Fenster ist 09:01 gegen 09:03.

## 6. Dateien

- Skripte: `scripts/bch/chipnet_koepfe.py`, `scripts/bch/chipnet_auswertung.py`, `scripts/bch/chipnet_wbch.py`
- Workflow: `.github/workflows/bch-chipnet.yml`. Er läuft nur auf diesem Branch und startet bei einem Push auf die Skripte oder auf `data/bch-chipnet/anstoss.txt`.
- Daten auf diesem Branch: `data/bch-chipnet/koepfe.csv.gz`, `koepfe-meta.json`, `stand-2026-10-26.json` und `.md`, `wbch-2026-10-26.json`, dazu der Stand vom 28.10. `stand-2026-10-28.json` und `.md`, `wbch-2026-10-28.json` (mit Transaktions-IDs, keine Adressen)

## Was Ben tun muss

- **Postentwurf:** A oder F wählen. Beide sind auf dem Stand vom 28.10. 14:06 UTC.
- **Zuhörer auf chipnet:** Entscheiden, ob einer für Transaktions-Ankündigungen laufen soll. Damit ließe sich für wBCH-Transaktionen der Abstand zwischen erstem Sehen und Bestätigung messen.
- **Fragen an das XO-Team:** über unsere Kanäle weitergeben, wenn gewünscht. Ich poste und schreibe nichts.
- **Kein Merge nötig:** Der Branch ist ein Messbranch, der Workflow läuft dort.

Die Zählung lief am 28.10. um 14:07 UTC vor der Frist noch einmal, und die Zahlen in den Abschnitten Kurz, 2, 3 und 5 sind nachgezogen. Der Secret-Scan über den ganzen Branch ist sauber.
