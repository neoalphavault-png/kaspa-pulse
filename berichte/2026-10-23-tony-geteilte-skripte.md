# Abgleich mit Tony, geteilte Skripte, Stand 22.10.2026 10:58:40 UTC

Bericht für Ben zu Aufgabe B vom 23.10.2026. Die Aufgabe war schon am 22.10. erledigt (Bericht `berichte/2026-10-22-geteilte-skripte-tony.md` auf dem Messbranch `messung/covenants-stichzeit`, der nie gemergt wird). Diese Datei bringt dasselbe Ergebnis in den PR-Branch `fix/kcc20-zaehlung`, damit es mit dem PR auf GitHub lesbar ist. Neu gegenüber dem 22.10. ist nur die Kurzfassung: sie folgt jetzt den Textregeln vom 23.10. (kein Doppelpunkt, kein Wort "live", vier Sätze). Die Zahlen sind unverändert.

Unsere Zahlen sind "counted", Tonys tragen "source tony's indexer".

## Was gemacht wurde

1. Eigener Mainnet-Knoten (rusty-kaspa v2.1.0) im Runner frisch synchronisiert, gestoppt, UTXO-Bestand aus der Knoten-Datenbank auf den Kettenblock `e4312c72…22c6` (Blockzeit 10:58:39.591 UTC) zurückgerechnet. Lauf [39840676769](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/39840676769).
2. Zweitprüfung: Bestand am Pruning-Punkt (21.10.2026 05:49:51 UTC) vorwärts bis zum selben Block. Beide Wege identisch: 65.279.217 UTXOs, gleiche Summe, 0 Fehler.
3. Tonys Datei `examples/shared_scripts_2026-10-22.json` aus seinem Repo (Commit 3f18000, census_at 10:58:40 UTC) nur als Daten gelesen. Ins Repo kam nur eine Ableitung ohne Adressen: Skript als sha256(Adresse)[:16], Covenant-ID als sha256(ID)[:32], dazu seine Summen. In seinen Dateien steht kein Schlüssel und kein Secret.
4. Je Skript abgeglichen: Outputs und KAS am Skript laut Knoten, Covenant-IDs laut Konsens (UTXOs mit Covenant-Bindung), und die ID-Mengen gegeneinander. Die Bestandsliste mit Adressen blieb im Runner, hochgeladen wurden nur Summen.

## Ergebnis

- **Unser Knoten = Tonys Knotenprüfung, auf allen 33 Skripten exakt:** 3.089 Outputs, 22.819.501,45 KAS. Damit stimmt auch sein Urteil "20 von 33 stimmen als Summe" Zeile für Zeile.
- **Covenant-IDs:** Auf den 33 Skripten tragen am Knoten nur 103 Outputs eine Covenant-ID, unter 100 verschiedenen IDs. 13 der 33 Skripte tragen gar keine, darunter das größte (2.950 Outputs, 21.449.319,05 KAS). Von Tonys 1.173 IDs haben 46 am jeweiligen Skript einen lebenden Output mit dieser ID, 1.127 nicht. 54 IDs stehen nur am Knoten.
- **Abweichung der Claims:** Das größte Skript hat 997 Outputs mehr als beansprucht (+9.543.821,70 KAS). Bei 12 Skripten beansprucht der Indexer mehr, als am Knoten liegt; am deutlichsten Nr. 9 (−46), Nr. 6 (−39), Nr. 11 (−24), Nr. 4 (−10).
- **Unsere Definition** (mindestens zwei Konsens-Covenant-IDs auf einem Skript): 114 geteilte Skripte mit 158 IDs und 492 Outputs mit ID, 920,01 KAS. Von Tonys 33 Skripten erfüllen 19 diese Definition. Am 20.10. waren es bei uns 50 Skripte.
- Zur Einordnung, ganzer Bestand zur Stichzeit: 16.215 UTXOs mit Covenant-ID unter 1.251 IDs, 1.438.807,14 KAS. Um 10:58:00 und 10:59:00 dieselbe Zahl.

## Je Skript

Spalten: IDs, Outputs und KAS laut Tony (beansprucht), dann laut Knoten. "Outputs mit ID" = Outputs mit Covenant-Bindung. "IDs beide / nur Tony / nur Knoten" = Vergleich der ID-Mengen am Skript. Δ = Knoten minus Tony.

| Nr | Skript (sha256-Präfix) | IDs Tony | Outputs Tony | KAS Tony | IDs Knoten | Outputs Knoten | KAS Knoten | Outputs mit ID | IDs beide | nur Tony | nur Knoten | Δ Outputs | Δ KAS | Summe stimmt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | e710814d0c | 1083 | 1953 | 11.905.497,35 | 0 | 2950 | 21.449.319,05 | 0 | 0 | 1083 | 0 | +997 | 9.543.821,70 | nein |
| 2 | 936c6f6e8c | 16 | 16 | 1.126.177,05 | 0 | 16 | 1.126.177,05 | 0 | 0 | 16 | 0 | +0 | 0,00 | ja |
| 3 | 3d0c677a27 | 7 | 7 | 7,00 | 7 | 7 | 7,00 | 7 | 7 | 0 | 0 | +0 | 0,00 | ja |
| 4 | 3d22c2440c | 4 | 24 | 443,07 | 14 | 14 | 28,00 | 14 | 4 | 0 | 10 | -10 | -415,07 | nein |
| 5 | 204b0638fc | 4 | 4 | 0,89 | 0 | 4 | 0,89 | 0 | 0 | 4 | 0 | +0 | 0,00 | ja |
| 6 | ccb84c37e6 | 3 | 53 | 7.133,65 | 14 | 14 | 28,00 | 14 | 3 | 0 | 11 | -39 | -7.105,65 | nein |
| 7 | 739afb401b | 3 | 3 | 1,10 | 3 | 3 | 1,10 | 3 | 3 | 0 | 0 | +0 | 0,00 | ja |
| 8 | abf1b1c57a | 3 | 3 | 2,04 | 0 | 1 | 0,01 | 0 | 0 | 3 | 0 | -2 | -2,03 | nein |
| 9 | a9f2469e09 | 2 | 59 | 24.096,48 | 10 | 13 | 26,00 | 13 | 2 | 0 | 8 | -46 | -24.070,48 | nein |
| 10 | 8c9ab24e49 | 2 | 16 | 325,45 | 13 | 13 | 26,00 | 13 | 2 | 0 | 11 | -3 | -299,45 | nein |
| 11 | b4b77f2451 | 2 | 34 | 2.719,91 | 10 | 10 | 20,00 | 10 | 2 | 0 | 8 | -24 | -2.699,91 | nein |
| 12 | bd68bac616 | 2 | 15 | 1.030,96 | 6 | 6 | 12,00 | 6 | 2 | 0 | 4 | -9 | -1.018,96 | nein |
| 13 | 3194362fe5 | 2 | 6 | 3,00 | 2 | 2 | 1,00 | 2 | 2 | 0 | 0 | -4 | -2,00 | nein |
| 14 | 3cd2b0ea4f | 2 | 2 | 3,90 | 2 | 2 | 3,90 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 15 | fc6b504d70 | 2 | 2 | 0,40 | 1 | 2 | 0,40 | 1 | 1 | 1 | 0 | +0 | 0,00 | ja |
| 16 | 9fdd7b67dc | 2 | 2 | 1,08 | 0 | 2 | 1,08 | 0 | 0 | 2 | 0 | +0 | 0,00 | ja |
| 17 | fc74eab157 | 2 | 2 | 4,00 | 0 | 2 | 4,00 | 0 | 0 | 2 | 0 | +0 | 0,00 | ja |
| 18 | 28a014f9cc | 2 | 2 | 243.824,82 | 0 | 2 | 243.824,82 | 0 | 0 | 2 | 0 | +0 | 0,00 | ja |
| 19 | a2aadca6e1 | 2 | 2 | 1,70 | 2 | 2 | 1,70 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 20 | cd8b12a167 | 2 | 2 | 0,80 | 2 | 2 | 0,80 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 21 | 98d145b3c2 | 2 | 2 | 2,00 | 2 | 2 | 2,00 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 22 | 52629f807d | 2 | 2 | 0,60 | 2 | 2 | 0,60 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 23 | acb14e11b3 | 2 | 2 | 4,00 | 0 | 2 | 4,00 | 0 | 0 | 2 | 0 | +0 | 0,00 | ja |
| 24 | 37bb799806 | 2 | 2 | 1,00 | 2 | 2 | 1,00 | 2 | 1 | 1 | 1 | +0 | 0,00 | ja |
| 25 | e2203041ef | 2 | 2 | 4,00 | 0 | 2 | 4,00 | 0 | 0 | 2 | 0 | +0 | 0,00 | ja |
| 26 | 2be1038e0a | 2 | 5 | 7,95 | 0 | 1 | 0,01 | 0 | 0 | 2 | 0 | -4 | -7,94 | nein |
| 27 | c8508895b2 | 2 | 2 | 0,60 | 0 | 1 | 0,01 | 0 | 0 | 2 | 0 | -1 | -0,59 | nein |
| 28 | a47264593d | 2 | 6 | 4,55 | 0 | 1 | 0,01 | 0 | 0 | 2 | 0 | -5 | -4,54 | nein |
| 29 | 33b400aedf | 2 | 2 | 1,73 | 0 | 1 | 0,01 | 0 | 0 | 2 | 0 | -1 | -1,72 | nein |
| 30 | 16cce485d2 | 2 | 2 | 2,00 | 2 | 2 | 2,00 | 2 | 1 | 1 | 1 | +0 | 0,00 | ja |
| 31 | 87d78d6e40 | 2 | 2 | 1,00 | 2 | 2 | 1,00 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 32 | 774457b40b | 2 | 2 | 2,00 | 2 | 2 | 2,00 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| 33 | 029d0632bd | 2 | 2 | 2,00 | 2 | 2 | 2,00 | 2 | 2 | 0 | 0 | +0 | 0,00 | ja |
| **Summe** | | **1.173** | **2.240** | **13.311.308,09** | **100** | **3.089** | **22.819.501,45** | **103** | **46** | **1.127** | **54** | **+849** | **9.508.193,36** | **20 von 33** |

## Kurzfassung (englisch, klein geschrieben, Textregeln vom 23.10.)

> counted on our own node at 10:58:40 utc on 22 oct. your 33 scripts hold 3,089 outputs and 22,819,501.45 kas, exactly what your node check shows on all 33, and the same 20 of 33 match the claims as a sum. the difference is the covenant id, only 103 of those outputs carry one on chain, under 100 ids, and 13 of the 33 scripts carry none at all, so 1,127 of the 1,173 ids (source tony's indexer) have no unspent output with that id on their script. on our definition, two or more on-chain covenant ids on one script, we count 114 shared scripts with 158 ids and 492 outputs.

Geprüft auf Gedankenstrich, Doppelpunkt (nur die Uhrzeit), Pfeil, Echtzeitwörter, Preis und Kursziel.

## Offene Fragen an Ben

1. In deiner Nachricht vom 22.10. stand statt Tonys Link nur ein Platzhalter. Ich habe die Datei aus seinem Repo genommen (Commit 3f18000, `examples/shared_scripts_2026-10-22.json`). Zeigt dein Link auf dieselbe Datei?
2. Das Artefakt von Lauf 39551527664 (21.10.) enthält die Bestandsliste vom 20.10. mit Adressen. Löschen?
3. Lauf 39840060676 hat beim Paket-Install die IP eines Ubuntu-Paketspiegels ins Log geschrieben, keinen Kaspa-Knoten. Lauf löschen?

## Was Ben tun muss

- Kurzfassung prüfen und posten (falls die Tabelle vom 22.10. schon in Tonys Thread steht, ist das nur der Text dazu).
- Fragen 1 bis 3 beantworten.
