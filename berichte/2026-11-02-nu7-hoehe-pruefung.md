# Prüfung NU7 Mainnet, Aktivierungshöhe 3.543.405 (2.11.2026)

Ben hat den Auftrag am 2.11. gegeben. Anlass war der Mittagscheck vom 2.11. Er behauptet, die Höhe 3.543.405 liege schon unter der aktuellen Mainnet-Höhe.

**Ergebnis:** Die Behauptung stimmt nicht. Die Höhe liegt noch 4.118 Blöcke vor uns, und die Höhe selbst ist richtig. Eine Korrektur auf X ist nicht nötig.

## 1. Aktuelle Mainnet-Höhe

**Woher die Zahl kommt:**
- Einen eigenen Zcash-Knoten betreiben wir nicht.
- Unsere eigene Quelle ist der Header-Client `scripts/zcash/zcash_koepfe.py`. Er holt die Header über P2P von Zebra- und Zakura-Peers. Geprüft werden Verkettung, Arbeitsnachweis aus nBits und Zebras Checkpoints.
- Aus dieser Cloud-Sitzung lassen sich die DNS-Seeds nicht auflösen. Deshalb habe ich den Lauf über `zcash-mainnet.yml` von Hand gestartet: Run [41444643633](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41444643633), ohne datierten Stand und damit ohne Discord-Entwurf. Die Daten liegen auf `messung/zcash-mainnet`, Commit `e8132c3`.

**Messwerte:**

| | Wert |
|---|---|
| Abruf | 2026-11-02 12:27:46 UTC |
| Spitze | **3.539.287**, Header-Zeit 2026-11-02 12:25:41 UTC |
| Gegenprobe Peer 1 | `/Zebra:7.0.0/`, 500 von 500 Hashes gleich, Spitze des Peers 3.539.287 |
| Gegenprobe Peer 2 | `/Zebra:7.0.0/`, 500 von 500 Hashes gleich, Spitze des Peers 3.539.288 |
| Abstand zu 3.543.405 | **noch 4.118 Blöcke** |

Den Mittagscheck selbst habe ich im Repo nicht gefunden. Woher seine Zahl stammt, kann ich deshalb nicht sagen. Zum Vergleich: Die Testnet-Aktivierung liegt bei 4.465.026, also über beiden Mainnet-Werten.

## 2. Quelle der Aktivierungshöhe

Für Mainnet ist die Höhe **3.543.405** in allen drei Quellen gleich. Testnet hat eine andere Höhe, nämlich 4.465.026.

| Quelle | Stelle | Mainnet | Testnet |
|---|---|---:|---:|
| Zebra **v7.0.0**, Tag-Commit `e8db87e` vom 22.10.2026 | `zebra-chain/src/parameters/constants.rs`, Zeile 106 (`activation_heights::mainnet::NU7`) | 3_543_405 | Zeile 76: 4_465_026 |
| Zebra v7.0.0 | `zebra-chain/src/parameters/network_upgrade.rs`, Zeile 119 (`MAINNET_ACTIVATION_HEIGHTS`, `(NU7, Nu7)`) | über die Konstante | |
| `zcash_protocol` **0.11.0** (crates.io, von Zebra 7.0.0 genutzt) | `src/consensus.rs`, Zeile 567 (`impl Parameters for MainNetwork`) | 3_543_405 | Zeile 601: 4_465_026 |
| ZIP 259 (zcash/zips, main) | `zips/zip-0259.md`, Zeilen 109 bis 111, „ACTIVATION_HEIGHT (NU7)“ | 3543405 | 4465026 |

Den Code von zcashd habe ich nicht geprüft.

## 3. Prognose mit den letzten 7 Tagen

**Grundlage:** 8.020 Abstände aus den 7 Tagen vor der Spitze (26.10. 12:25 bis 2.11. 12:25 UTC).
- Mittel 75,42 s, Median 53 s.
- Tagesmittel zwischen 74,88 und 75,71 s.

**Methode:** Für die 4.118 fehlenden Blöcke ziehe ich die Abstände 4.000-mal zufällig mit Zurücklegen aus diesen Abständen und addiere sie. Die Saat ist 2026.

| Rechnung | UTC |
|---|---|
| Mitte (Median) | **2026-11-06 02:39:52** |
| 90-%-Band (5 % bis 95 %) | **2026-11-06 00:28:23 bis 2026-11-06 05:00:17** |
| Gerechnet mit genau 75 s | 2026-11-06 02:13:11 |
| Workflow (14 Tage, eigene Methode), zum Vergleich | Mitte 02:36:57, Band 00:24:58 bis 04:48:01 |

**Vergleich mit dem, was öffentlich steht:**

| | Öffentlich (30.10.) | Neu (2.11.) |
|---|---|---|
| Mitte | 6 nov 02:26 utc | 6 nov 02:40 utc, 14 min später |
| Band | 5 nov 23:01 bis 6 nov 05:51 utc | 6 nov 00:28 bis 05:00 utc |

Das neue Band liegt ganz innerhalb des veröffentlichten. Die Aussage auf X und im Forum stimmt also weiter.

## 4. Korrektur

Die Höhe liegt noch vor uns, und sie ist richtig. **Ein Korrekturtext ist nicht nötig.** Ein Update-Text für X schlage ich nicht vor, solange Ben keinen will.

## Offene Fragen an Ben

- Woher stammt die Zahl im Mittagscheck? Wurde dort vielleicht eine Testnet-Höhe oder ein Explorer mit anderer Zählung gelesen? Der Check liegt nicht im Repo.
- Soll die Upgrade-Wache auf c2 `erwartet_utc` von 02:26:16 auf 02:39:52 setzen? Ihr Fenster beginnt 24 h vorher, das neue Band liegt darin. Die geplante Aufgabe am 4.11. passt den Wert ohnehin an.

## Was Ben tun muss

Nichts Dringendes. Die öffentliche Angabe bleibt richtig.
