# Upgrade-Wache Zcash NU7: Bericht nach dem Fenster und Upgrade Report v1 (9.11.2026)

Auftrag: Ben 29.10. (Punkt 8) und 2.11. (Spezifikation v1.0 auf pulsehawk.io/standard). Gerechnet mit dem öffentlichen Repo **pulsehawk/methods, Commit `0e5019c`** (main am 9.11., frisch geklont). Daten und Ergebnis liegen dort seit PR #5 (Merge `0820cde`).

<!-- discord -->
Zcash NU7, Upgrade Report v1 fertig und reproduzierbar in pulsehawk/methods (PR #5, Merge 0820cde). M1 nach der Aktivierung: Median 17,0 s (Modell 17,3 s), n 10.195. Stabil nach 3 h 36 min 56 s. Der Block kam 6 min 56 s früher als die Prognose vom 4.11., im 90-%-Band. Keine Kettenspaltung, 19 Spitzenwechsel der Tiefe 1. Der Header-Client brach heute in der Gegenprobe ab, Fix #296 gemergt. Report-Karte in #ph-entwuerfe. Bericht berichte/2026-11-09-upgrade-wache-nu7.md
<!-- /discord -->

## Ablauf heute

- **Fenster zu:** Die Wache schrieb `fenster_zu` am 9.11. um 03:34:41 UTC, 73 h nach `aktivierung_gesehen` (6.11. 02:34:52 UTC). Die Rohdaten kamen mit dem Sync auf `messung/zcash-mainnet` unter `wache/roh/`, `sha256sum -c` ist OK.
- **Köpfe fehlten:** `koepfe.csv.gz` reichte nur bis 8.11. 12:01 UTC, gebraucht wird t_akt + 72 h, also 9.11. 02:34 UTC. Ich habe `zcash-mainnet.yml` mit `stand=false` von Hand gestartet.
- **Header-Client brach ab:** Lauf 21 endete in der Gegenprobe mit `AttributeError`, weil der Hauptpeer beim Abruf wegfiel. Fix in `scripts/zcash/zcash_koepfe.py`, PR #296, Merge `cca1ec9`, selbst gemergt. Lauf 22 lief durch, die Köpfe reichen jetzt bis 3.554.698.
- **Rechnung:** Köpfe-Ausschnitt 3.542.245 bis 3.553.625 (t_akt − 24 h − 10 min bis t_akt + 72 h + 10 min, lückenlos, gzip mit mtime 0), Rohdaten unverändert. `report_v1.py --selftest` bestanden, Report gerechnet, `sha256sum -c` OK. Ein zweiter Lauf aus den Dateien im Repo ergibt dieselben Prüfsummen.

## Eingänge (aus `report-v1-zcash-mainnet-nu7-inputs.json`)

| Datei | sha256 |
|---|---|
| `zcash-mainnet-nu7.json` (Konfiguration) | `96b09319b88411453bc4ec1d98b93bc67dbf95a9248d1335a0918d718395bd2a` |
| `heads.csv.gz` | `0792a4de5065f77bf0480ffbf906e1134dd2144c561444615ee08e032451b376` |
| `raw/SHA256SUMS` | `f607705044fffc0e5bc23b8d138fa934cc1d4e75786d3d4681d859612dbcc11c` |
| `raw/ereignisse.jsonl.gz` | `0c58a601046c66f018b3f32f3d3ea1d69472e5f2bc10cb230fdb4a834026f55f` |
| `raw/koepfe.jsonl.gz` | `e69db91b020be07517c9be0ddd3ebecdb7d5786e27ef778fb9696ee2b724dfbd` |
| `raw/peers.json` | `bb2662666227d64ac60e59754d02ed328833d25a3ff52b54161ad957254c9937` |
| `raw/wache-log.csv` | `98f37a561f3409cfec4dddec44acf726208c4b8d4900ee05dfd8d142bc995b61` |
| `raw/zustand.json` | `ce56fbc1515919314b97ff0076203d0ed717f12ad92a97fe451b4926a5f12749` |

**Ausgaben:**
- `report-v1-zcash-mainnet-nu7.csv`: `0f1e19697430244708ba0729be5fd3c93f645ee5c5deea4d530f67c6dd748b8e`
- `report-v1-zcash-mainnet-nu7-uncertainty.csv`: `89204abadc31558a199ac3c2c72fc3a5a78da04024bcf257f496085498eb45cf`

## Wo die Dateien liegen

- **pulsehawk/methods**, `data/zcash-mainnet-nu7/`: `heads.csv.gz`, `raw/`, `expected/report-v1-zcash-mainnet-nu7.sha256`, `output/` mit beiden CSV und `-inputs.json`, dazu ein README mit den drei Befehlen. PR #5, selbst gemergt (nur Daten und ein README, Textregeln und Secret-Scan bestanden).
- **kaspa-pulse**, `messung/zcash-mainnet`, `wache/report/`: CSV, `.sha256` und `-inputs.json` (Commit `311d01bc`).
- **Sitzung PulseHawk Seite:** Merge-Commit, die drei Befehle und die Kernwerte geschickt, damit sie die Befehle auf /reports/zcash-nu7 freischaltet.

## Fenster

t_akt ist die Kopfzeit von Block 3.543.405, 6.11. 02:34:02 UTC.

| | von (UTC) | bis (UTC) | Höhen | n Abstände |
|---|---|---|---|---:|
| vor | 5.11. 02:34:58 | 6.11. 02:33:21 | 3.542.255 bis 3.543.404 | 1.150 |
| nach | 6.11. 02:34:02 | 9.11. 02:33:51 | 3.543.405 bis 3.553.599 | 10.195 |

## M1 bis M7

| Kennzahl | vor | nach | Art | Verfahren |
|---|---:|---:|---|---|
| M1 Ziel | 75 s | 25 s | source (ZIP 208, ZIP 218) | PH-M-001 |
| M1 Median | 51,0 s (Modell 52,0 s) | **17,0 s** (Modell 17,3 s) | counted, Modell computed | PH-M-001 |
| M1 p90 | 2 min 49 s (Modell 2 min 53 s) | 59,0 s (Modell 57,6 s) | counted, computed | PH-M-001 |
| M1 p99 | 6 min 29 s (Modell 5 min 45 s) | 1 min 58 s (Modell 1 min 55 s) | counted, computed | PH-M-001 |
| M1 Mittel | 75,12 s | 25,43 s | counted | PH-M-001 |
| M1 negative Abstände | 0 | 0 | counted | PH-M-001 |
| M2 längste Lücke | 10 min 5 s vor Block 3.543.368 (6.11. 01:53:36) | 4 min 9 s vor Block 3.543.445 (6.11. 03:11:24) | counted | PH-M-001 |
| M2 Abstände über 5 × Ziel | 13 (Modell 7,7) | 81 (Modell 68,7) | counted, computed | PH-M-001 |
| M3 Spitzenwechsel ab Tiefe 2 (Kopfzahl) | 0 | 0 | counted | PH-M-002 |
| M3 Verteilung Tiefe 1 / 2 / 3+ | 0 / 0 / 0 | 19 / 0 / 0 | counted | PH-M-002 |
| M4 Kettenspaltung | 0 s, 0 Episoden | 0 s, 0 Episoden | counted | PH-M-002 |
| M6 Zeit bis stabil | | 13.016 s (3 h 36 min 56 s), stabil ab 6.11. 06:10:58 | counted | PH-M-001 |
| M6 Anteil der Zeit im Band | | 96,7 % (n 10.128) | counted | PH-M-001 |

**M5, Peers unter dem Mindestprotokoll 170190** (counted, PH-M-003):

| Probe | UTC | n | darunter | Anteil | Versionen |
|---|---|---:|---:|---:|---|
| 0 h | 6.11. 02:34:52 | 28 | 2 | 7,1 % | 170140 ×1, 170150 ×1, 170190 ×26 |
| 6 h | 6.11. 08:34:32 | 12 | 2 | 16,7 % | 170150 ×2, 170190 ×10 |
| 24 h | 7.11. 02:34:40 | 6 | 2 | 33,3 % | 170140 ×1, 170150 ×1, 170190 ×4 |
| 72 h | 9.11. 02:34:41 | 8 | 2 | 25,0 % | 170140 ×1, 170150 ×1, 170190 ×6 |

Die Probe bei 6 h lief pünktlich, obwohl die Wache bis 08:11 UTC hing (Bericht vom 6.11.).

**M7, Aktivierung:**
- Aktivierungshöhe 3.543.405 (source, ZIP 259, Zebra 7.0.0, zcash_protocol 0.11.0).
- Kopfzeit des ersten Blocks 6.11. 02:34:02 UTC (counted, PH-M-001).
- Erste Ankündigung an unseren Zuhörer um 02:34:10 UTC, 9 s nach der Kopfzeit (counted, PH-M-004).
- **Der Block kam 6 min 56 s früher als die Prognose vom 4.11.** (02:40:58 UTC), im 90-%-Band 01:14:45 bis 04:07:28 UTC (computed, PH-M-006). In der CSV steht `header_time_minus_estimate` = −416 s. Positiv hieße, der Block kam später. Die Feldnamen gehören zu Format v1 und bleiben.
- Die anderen drei Prognosen (23.10., 28.10., 2.11. mit 7 Tagen) und ihre Quellen stehen in `berichte/2026-11-08-nu7-karte-forecast.md`. Alle vier liegen im Band.

## Messunsicherheit je Kennzahl (aus der Unsicherheits-CSV)

- **M1 und M2:** Zeitbasis Kopfzeiten. Die setzen die Miner im Rahmen der Konsensregeln, sie sind keine Uhr. 0 Höhen fehlen vor und nach der Aktivierung, die Köpfe sind eine lückenlose Kette, auf Verkettung und Arbeit geprüft.
- **M3 und M4 vor:** Zeitbasis Ankunft bei unserer Wache, Uhr per NTP, Abweichung nicht gemessen. 7 von 1.150 Kettenblöcken wurden uns nie angekündigt. 1 Pause über 10 min ohne Ankündigung, längste 10 min 30 s. 20 Peers haben Blöcke angekündigt.
- **M3 und M4 nach:** 9 von 10.195 Kettenblöcken nie angekündigt, keine Pause über 10 min, 46 Peers haben Blöcke angekündigt. Ein Wechsel, den wir nicht sehen, wird nicht gezählt.
- **M5:** Nur Peers, die den Handschlag beantworten, zählen in n. Eine Probe je Zeitpunkt. Der Anteil gilt für erreichbare Peers, nicht für alle Knoten.
- **M6:** Zeitbasis Kopfzeiten. Die 60 min Haltezeit liegen ganz in den Daten. Das gleitende Mittel über 60 min ist unruhig, siehe METHODS.md.
- **M7:** Kopfzeit und Ankunft bei unserem Zuhörer, 242 Verbindungen in den Rohdaten. Die Prognose ist eine Prognose, keine Messung.

## Grenzen

- **M3 und M4** zählen nach der Ankunftszeit bei unserer Wache, nicht nach der Kette. Ein Knoten, der den Gewinnerblock zuerst sieht, wechselt nie. Ein Wechsel, den wir nicht sehen, fehlt.
- **Die Wache hing am 6.11.** von etwa 02:50 bis 08:11 UTC, weil die DNS-Seeds von ihrem Host aus nicht auflösbar waren. In diesen Stunden kann M3 Wechsel verpassen. Die Blockpause-Meldungen in dieser Zeit (siehe unten) kommen von dem Hänger, nicht von der Kette.
- **M1, M2 und M6** kommen aus den Kopfzeiten. Die Abgrenzung der Fenster geht über die Höhe, weil Kopfzeiten nicht steigen müssen. Negative Abstände gab es keine.

## Festlegungen Ben 3.11., so umgesetzt

- **M6** ist das 1-h-Mittel im Band ±20 % (20 bis 30 s), gehalten 60 min. `zeit_bis_stabil` steht in Sekunden.
- **M3** steht als Verteilung Tiefe 1, 2 und 3+. Die Kopfzahl zählt ab Tiefe 2.

## Ringversuch

`ROUND_ROBIN.md` in pulsehawk/methods: Wer M1 nach der Aktivierung (`p50_after`, PH-M-001) mit eigenen Köpfen zählt, kann unseren Wert vergleichen. Unser Wert ist 17,0 s bei n 10.195.

## Alle Signale aus dem Log

| UTC | Höhe | Signal | Wert | Schwelle | Stufe |
|---|---|---|---:|---:|---|
| 6.11. 02:34:52 | 3.543.408 | aktivierung_gesehen | 3.543.405 | | wache |
| 6.11. 02:35:18 | 3.543.408 | peers_vor_upgrade | 7,1 % | 170190 | info |
| 6.11. 02:46:52 | 3.543.419 | median_abstand | 61,5 s | 50 s | alarm |
| 6.11. 02:50:52 | 3.543.426 | median_abstand | 45,0 s | 50 s | entwarnung |
| 6.11. 02:59:52 | 3.543.431 | blockpause | 330 s | 300 s | hinweis |
| 6.11. 03:04:52 | 3.543.431 | blockpause | 630 s | 600 s | alarm |
| 6.11. 08:15:32 | 3.544.061 | blockpause | 17 s | 300 s | entwarnung |
| 6.11. 08:34:58 | 3.544.110 | peers_vor_upgrade | 16,7 % | 170190 | info |
| 6.11. 13:29:40 bis 9.11. 01:58:41 | | reorg_gesehen | Tiefe 1, 19-mal | 2 | info |
| 7.11. 02:34:59 | 3.546.673 | peers_vor_upgrade | 33,3 % | 170190 | info |
| 9.11. 02:35:07 | 3.553.599 | peers_vor_upgrade | 25,0 % | 170190 | info |
| 9.11. 03:34:41 | | fenster_zu | | | wache |

- Der Alarm `median_abstand` um 02:46:52 fällt in die ersten 13 min nach NU7. Vermutlich lag der Median der letzten Blöcke da noch über der neuen Schwelle von 50 s, geprüft habe ich das nicht. Nach 4 min kam die Entwarnung.
- Die Blockpause ab 02:59:52 ist der Hänger der Wache, nicht die Kette. Die längste echte Lücke nach der Aktivierung war 4 min 9 s (M2).

## Wie schnell unsere Meldung kam

- **Zuhörer:** erste Ankündigung 9 s nach der Kopfzeit.
- **Wache:** `aktivierung_gesehen` um 02:34:52 UTC, 50 s nach der Kopfzeit. Der Abstand kommt vom Takt der Wache.
- **Probe bei 0 h:** um 02:35:18 UTC, 76 s nach der Kopfzeit.

## Was wir vor öffentlichen Quellen gesehen haben

- **Zebra-Issues auf GitHub:** Seite 1 von 8 der Suche nach NU7 gelesen. Kein Issue oder PR vom 5. bis 8.11. meldet die Aktivierung, Störungen, Spaltungen oder lange Pausen. GitHub zeigt dort nur das Datum, keine Uhrzeit.
- **Zcash Forum, Zcash Foundation und Nachrichtenseiten:** aus dieser Umgebung nicht erreichbar (DNS). Nicht umgangen. Ein Vergleich der Uhrzeiten mit unserer Meldung fehlt deshalb.
- **Websuche:** Mehrere Nachrichtenseiten melden die Aktivierung bei Höhe 3.543.405. Die meisten nennen den 5.11., eine nennt den 6.11. 02:34 UTC. Nach unserer Kopfzeit ist der 6.11. 02:34:02 UTC richtig.

## Vergleich mit dem Zuhörer auf GitHub

`lauscher-nu7/zusammenfassung.json` auf `messung/zcash-mainnet`, Fenster 5.11. 17:02 bis 8.11. 15:30 UTC, ein Zuhörer an einem Ort, kein eigener Knoten.

| | Zuhörer (GitHub) | Wache |
|---|---|---|
| Fenster nach NU7 | bis etwa 61 h | 72 h |
| Kettenblöcke ab NU7 | 8.609, davon 8.602 angekündigt | 10.195, davon 10.186 angekündigt |
| abgehängte Blöcke ab NU7 | 52 (0,60 %) | |
| Spitzenwechsel Tiefe 1 | | 19 |
| Tiefe 2 oder mehr | keine Zweige mit Kopf tiefer als 1 | 0 |

Beide sehen nur Tiefe 1. Der Zuhörer zählt jeden abgehängten Block, den er angekündigt bekam. Die Wache zählt nur, wenn ihre eigene Spitze wechselt. Die Zahlen messen also nicht dasselbe.

## Karte

`scripts/ph/report_karte.py` aus der Report-CSV: „17 s“, darunter „half of all blocks came within 17 s of the one before, the model says 17.3 s“, Tabelle counted gegen computed. Stil-Prüfung bestanden, in #ph-entwuerfe mit der Vorschau mit 390 px, nicht gepostet. Der Post um 11:00 war die NU7-Prognosekarte (Bericht `berichte/2026-11-09-nu7-karte-ruhig.md`).

## PRs und Merges

| PR | Merge | Inhalt |
|---|---|---|
| kaspa-pulse #296 | `cca1ec9` | Fix im Header-Client |
| pulsehawk/methods #5 | `0820cde` | Daten, erwartete Prüfsummen, Ausgaben |
| dieser Bericht | | kaspa-pulse, Branch `bericht/2026-11-09-upgrade-wache-nu7` |

## Offene Fragen an Ben

1. Der Header-Client war die Ursache für die fehlenden Köpfe. Soll der tägliche Lauf von `zcash-mainnet.yml` bei einem Abbruch nach #ops-log melden?
2. Forum, Zcash Foundation und die Nachrichtenseiten sind aus der Cloud-Umgebung nicht erreichbar. Soll ich sie für solche Vergleiche in der Netzwerk-Freigabe der Umgebung beantragen?

## Was Ben tun muss

- Report-Karte in #ph-entwuerfe ansehen. Ob sie gepostet wird, entscheidest du.
- Wenn die Seite die Reproduce-Befehle auf /reports/zcash-nu7 freigeschaltet hat, einmal ansehen.
