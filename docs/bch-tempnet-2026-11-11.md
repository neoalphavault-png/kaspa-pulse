# BCH Tempnet 2027 (Faster Blocks), Zählung Stand 2026-11-11 10:00 UTC

**Fenster:** 2026-10-15 12:56:56 bis 2026-11-11 09:58:11 UTC, Blöcke 327.989 bis 365.753 (37.765 Blöcke). **Abruf:** 2026-11-13T06:02:01Z.

Quelle: eigene Header über P2P (`scripts/bch/tempnet_koepfe.py`), geprüft auf Verkettung und PoW gegen nBits, erster Tempnet-Block 327.989 als Fixpunkt, Gegenprobe mit weiteren Peers: /Bitcoin Cash Node:29.2.1(tempnet-20261015)/ 500/500, /Bitcoin Cash Node:29.2.1/ 500/500. Peer-Software: /Bitcoin Cash Node:29.2.1/, /Bitcoin Cash Node:29.2.1(tempnet-20261015)/.

Gegenprobe source chaingraph: nicht verfügbar (HTTPError: HTTP Error 403: Forbidden).

## Blockabstände gegen 60 s

|  | gemessen | erwartet (exponentiell, 60 s) |
| --- | --- | --- |
| Mittel | 61,49 s | 60 s |
| Median | 41,0 s | 41,6 s |
| p90 | 130,0 s | 138,2 s |
| p99 | 242,0 s | 276,3 s |
| über 5 min | 0,58 % (218) | 0,67 % |
| längste Lücke | 20.863 s (Höhe 328.223) | ≈ 667 s |
| Abstand 0 / negativ | 428 / 0 |  |

## MTP-Verzug (Median der letzten 11 Blöcke)

|  | gemessen | erwartet (Simulation, 60 s) |
| --- | --- | --- |
| Block-Zeitstempel minus MTP davor, Median | 342,0 s | 340,1 s |
| dto. p90 / p99 | 548,0 / 1.408,5 s | 556,5 / 786,0 s |
| dto. kleinster Wert (Konsens verlangt > 0) | 2 s |  |
| Abrufzeit minus MTP der Spitze | 212 s | Median 340,4 s, p90 555,8 s |
| Abrufzeit minus Zeitstempel der Spitze | 7 s | Median 41,7 s, p90 137,5 s |

Die Abrufzeit ist eine einzelne Messung je Lauf; die wöchentlichen Läufe sammeln weitere.

## 10 Blöcke gegen 1 Block à 600 s

|  | 10 Blöcke gemessen | 10 × 60 s erwartet | 1 × 600 s erwartet |
| --- | --- | --- | --- |
| Median | 579,0 s | 580,1 s | 415,9 s |
| p90 | 851,0 s | 852,4 s | 1.381,6 s |
| p99 | 2.311,4 s | 1.127,0 s | 2.763,1 s |

37.755 überlappende Fenster.

## Nachführung der Schwierigkeit

Fenster 100 Bloecke, Sprung ab Faktor 2.0 (bestaetigt), eingeholt, wenn die ASERT-Schwierigkeit innerhalb +-15 % der Hashrate der folgenden 100 Bloecke mal 60 s liegt. Sprünge: 27, eingeholt 6, vom nächsten Sprung abgelöst 19, am Stichtag offen 1, nicht in 2.000 Blöcken eingeholt 1. Eingeholt im Median nach 465,0 Blöcken bzw. 591,0 min (dieselben Sprünge), längstens 914 Blöcke.

| Höhe | Zeit UTC | Faktor | eingeholt nach Blöcken | min |
| --- | --- | --- | --- | --- |
| 328.239 | 2026-10-16 13:48:16 | 3,16 | nicht in 2.000 | – |
| 347.739 | 2026-10-29 21:13:37 | 6,78 | abgelöst | – |
| 347.939 | 2026-10-29 21:40:47 | 3,16 | abgelöst | – |
| 348.139 | 2026-10-29 21:49:02 | 3,35 | abgelöst | – |
| 348.339 | 2026-10-29 21:56:55 | 2,69 | 466 | 118,8 |
| 349.789 | 2026-10-30 15:55:43 | 0,15 | abgelöst | – |
| 349.989 | 2026-10-31 01:50:06 | 12,30 | 464 | 838,5 |
| 353.689 | 2026-11-02 22:00:55 | 2,02 | abgelöst | – |
| 353.889 | 2026-11-02 23:01:53 | 2,60 | abgelöst | – |
| 354.089 | 2026-11-02 23:17:00 | 2,91 | abgelöst | – |
| 354.539 | 2026-11-03 00:53:16 | 0,36 | abgelöst | – |
| 354.739 | 2026-11-03 08:23:21 | 557,91 | abgelöst | – |
| 355.089 | 2026-11-03 09:58:17 | 0,11 | abgelöst | – |
| 355.289 | 2026-11-03 17:28:26 | 99,71 | 427 | 114,5 |
| 355.789 | 2026-11-03 20:24:07 | 0,26 | abgelöst | – |
| 355.989 | 2026-11-04 06:15:03 | 29,48 | 549 | 829,8 |
| 357.139 | 2026-11-05 06:05:05 | 0,48 | 301 | 352,1 |
| 357.689 | 2026-11-05 16:05:40 | 2,45 | abgelöst | – |
| 357.889 | 2026-11-05 17:03:50 | 3,15 | abgelöst | – |
| 358.389 | 2026-11-05 17:57:57 | 0,21 | abgelöst | – |

## Je Tag (UTC)

| Tag | Blöcke | Höhen | mittl. Abstand | ASERT-Schwierigkeit Median |
| --- | --- | --- | --- | --- |
| 2026-10-15 | 10 | 327.989–327.998 | 3.585,3 s | 1,00 |
| 2026-10-16 | 855 | 327.999–328.853 | 109,8 s | 6,39 |
| 2026-10-17 | 1.525 | 328.854–330.378 | 56,7 s | 1,00 |
| 2026-10-18 | 1.888 | 330.379–332.266 | 45,8 s | 12,28 |
| 2026-10-19 | 1.282 | 332.267–333.548 | 67,4 s | 6,96 |
| 2026-10-20 | 1.433 | 333.549–334.981 | 60,3 s | 2,98 |
| 2026-10-21 | 1.399 | 334.982–336.380 | 61,8 s | 2,27 |
| 2026-10-22 | 1.466 | 336.381–337.846 | 58,9 s | 2,26 |
| 2026-10-23 | 1.402 | 337.847–339.248 | 61,6 s | 2,04 |
| 2026-10-24 | 1.449 | 339.249–340.697 | 59,6 s | 1,68 |
| 2026-10-25 | 1.435 | 340.698–342.132 | 60,2 s | 1,76 |
| 2026-10-26 | 1.450 | 342.133–343.582 | 59,6 s | 1,73 |
| 2026-10-27 | 1.438 | 343.583–345.020 | 60,1 s | 1,71 |
| 2026-10-28 | 1.437 | 345.021–346.457 | 60,1 s | 1,70 |
| 2026-10-29 | 2.353 | 346.458–348.810 | 36,7 s | 2,09 |
| 2026-10-30 | 1.147 | 348.811–349.957 | 75,2 s | 89.693,88 |
| 2026-10-31 | 961 | 349.958–350.918 | 90,0 s | 11,97 |
| 2026-11-01 | 1.402 | 350.919–352.320 | 61,6 s | 6,91 |
| 2026-11-02 | 2.104 | 352.321–354.424 | 41,1 s | 7,65 |
| 2026-11-03 | 1.470 | 354.425–355.894 | 58,4 s | 15.926,04 |
| 2026-11-04 | 888 | 355.895–356.782 | 97,9 s | 29,13 |
| 2026-11-05 | 1.783 | 356.783–358.565 | 48,4 s | 29,58 |
| 2026-11-06 | 910 | 358.566–359.475 | 95,0 s | 8,79 |
| 2026-11-07 | 1.410 | 359.476–360.885 | 61,3 s | 2,39 |
| 2026-11-08 | 1.468 | 360.886–362.353 | 58,9 s | 2,60 |
| 2026-11-09 | 2.069 | 362.354–364.422 | 41,6 s | 4,40 |
| 2026-11-10 | 829 | 364.423–365.251 | 104,5 s | 6,01 |
| 2026-11-11 | 502 | 365.252–365.753 | 71,5 s | 3,32 |

## Blöcke mit Mindestschwierigkeit

8.645 von 37.765 Blöcken tragen nBits = powLimit (Schwierigkeit 1). Der erste Block mit anderer Schwierigkeit ist 328.002. Vor 6.280 dieser Blöcke lag eine Lücke über 120 s, vor 2.364 eine bis 120 s. Die längste Lücke vor einem Block mit anderer Schwierigkeit war 120 s. Beobachtung aus den Köpfen; die Regel selbst prüfen wir nicht.

| Tag | Blöcke | davon Mindestschwierigkeit |
| --- | --- | --- |
| 2026-10-15 | 10 | 10 |
| 2026-10-16 | 855 | 698 |
| 2026-10-17 | 1.525 | 1.525 |
| 2026-10-18 | 1.888 | 641 |
| 2026-10-19 | 1.282 | 274 |
| 2026-10-20 | 1.433 | 220 |
| 2026-10-21 | 1.399 | 209 |
| 2026-10-22 | 1.466 | 203 |
| 2026-10-23 | 1.402 | 201 |
| 2026-10-24 | 1.449 | 190 |
| 2026-10-25 | 1.435 | 180 |
| 2026-10-26 | 1.450 | 185 |
| 2026-10-27 | 1.438 | 206 |
| 2026-10-28 | 1.437 | 199 |
| 2026-10-29 | 2.353 | 172 |
| 2026-10-30 | 1.147 | 324 |
| 2026-10-31 | 961 | 313 |
| 2026-11-01 | 1.402 | 235 |
| 2026-11-02 | 2.104 | 216 |
| 2026-11-03 | 1.470 | 268 |
| 2026-11-04 | 888 | 331 |
| 2026-11-05 | 1.783 | 329 |
| 2026-11-06 | 910 | 406 |
| 2026-11-07 | 1.410 | 205 |
| 2026-11-08 | 1.468 | 195 |
| 2026-11-09 | 2.069 | 230 |
| 2026-11-10 | 829 | 356 |
| 2026-11-11 | 502 | 124 |

## Nicht gemessen

- Blockinhalte und die ASERT-Regel selbst (nur Kopf, Verkettung, PoW gegen nBits).
- Die Nachführung nach der Zcash-Methode setzt voraus, dass jeder Block die laufende Schwierigkeit trägt. Mit Blöcken auf Mindestschwierigkeit dazwischen ist das Gleichgewicht ASERT-Schwierigkeit = Hashrate × 60 s nicht gegeben; die Zahlen dort sind deshalb nur eingeschränkt aussagekräftig.
- Verwaiste Blöcke und Ankunftszeiten (kein Zuhörer, kein eigener Knoten).
