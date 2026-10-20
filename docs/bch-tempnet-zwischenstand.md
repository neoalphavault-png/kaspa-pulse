# BCH Tempnet 2027 (Faster Blocks), Zählung Stand 2026-10-20 16:00 UTC

**Fenster:** 2026-10-15 12:56:56 bis 2026-10-20 15:59:59 UTC, Blöcke 327.989 bis 334.495 (6.507 Blöcke). **Abruf:** 2026-10-20T16:33:16Z.

Quelle: eigene Header über P2P (`scripts/bch/tempnet_koepfe.py`), geprüft auf Verkettung und PoW gegen nBits, erster Tempnet-Block 327.989 als Fixpunkt, Gegenprobe mit weiteren Peers: /Bitcoin Cash Node:29.2.1(tempnet-20261015)/ 500/500, /Vcash:0.1/ 500/500. Peer-Software: /Rapids:2026-10.d46922c2/, /Vcash:0.1/, /Bitcoin Cash Node:29.2.1(tempnet-20261015)/.

Gegenprobe source chaingraph: nicht verfügbar (HTTPError: HTTP Error 403: Forbidden).

## Blockabstände gegen 60 s

|  | gemessen | erwartet (exponentiell, 60 s) |
| --- | --- | --- |
| Mittel | 68,09 s | 60 s |
| Median | 42,5 s | 41,6 s |
| p90 | 124,0 s | 138,2 s |
| p99 | 236,0 s | 276,3 s |
| über 5 min | 0,45 % (29) | 0,67 % |
| längste Lücke | 20.863 s (Höhe 328.223) | ≈ 562 s |
| Abstand 0 / negativ | 0 / 0 |  |

## MTP-Verzug (Median der letzten 11 Blöcke)

|  | gemessen | erwartet (Simulation, 60 s) |
| --- | --- | --- |
| Block-Zeitstempel minus MTP davor, Median | 330,0 s | 340,1 s |
| dto. p90 / p99 | 525,0 / 795,1 s | 556,5 / 786,0 s |
| dto. kleinster Wert (Konsens verlangt > 0) | 49 s |  |
| Abrufzeit minus MTP der Spitze | 333 s | Median 340,4 s, p90 555,8 s |
| Abrufzeit minus Zeitstempel der Spitze | 23 s | Median 41,7 s, p90 137,5 s |

Die Abrufzeit ist eine einzelne Messung je Lauf; die wöchentlichen Läufe sammeln weitere.

## 10 Blöcke gegen 1 Block à 600 s

|  | 10 Blöcke gemessen | 10 × 60 s erwartet | 1 × 600 s erwartet |
| --- | --- | --- | --- |
| Median | 562,0 s | 580,1 s | 415,9 s |
| p90 | 827,0 s | 852,4 s | 1.381,6 s |
| p99 | 1.285,5 s | 1.127,0 s | 2.763,1 s |

6.497 überlappende Fenster.

## Nachführung der Schwierigkeit

Fenster 100 Bloecke, Sprung ab Faktor 2.0 (bestaetigt), eingeholt bei +-15 %. Sprünge: 1, eingeholt 1, vom nächsten Sprung abgelöst 0, am Stichtag offen 0. Eingeholt im Median nach 0 Blöcken bzw. 0,0 min (dieselben Sprünge), längstens 0 Blöcke.

| Höhe | Zeit UTC | Faktor | eingeholt nach Blöcken | min |
| --- | --- | --- | --- | --- |
| 328.239 | 2026-10-16 13:48:16 | 3,16 | 0 | 0,0 |

## Je Tag (UTC)

| Tag | Blöcke | Höhen | mittl. Abstand | Schwierigkeit Median |
| --- | --- | --- | --- | --- |
| 2026-10-15 | 10 | 327.989–327.998 | 3.585,3 s | 1,00 |
| 2026-10-16 | 855 | 327.999–328.853 | 109,8 s | 1,00 |
| 2026-10-17 | 1.525 | 328.854–330.378 | 56,7 s | 1,00 |
| 2026-10-18 | 1.888 | 330.379–332.266 | 45,8 s | 3,83 |
| 2026-10-19 | 1.282 | 332.267–333.548 | 67,4 s | 6,19 |
| 2026-10-20 | 947 | 333.549–334.495 | 60,9 s | 3,17 |

Blöcke mit Mindestschwierigkeit (nBits = powLimit): 3.292.

## Nicht gemessen

- Blockinhalte und die ASERT-Regel selbst (nur Kopf, Verkettung, PoW gegen nBits).
- Verwaiste Blöcke und Ankunftszeiten (kein Zuhörer, kein eigener Knoten).
