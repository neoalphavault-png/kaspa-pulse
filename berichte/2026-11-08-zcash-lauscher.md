# Zcash Mainnet, Zuhörer nach NU7: Auswertung nach 48 h (8.11.2026)

Ben hat am 23.10. beauftragt: Zuhörer im Zcash Mainnet rund um NU7, 48 h nach der Aktivierung, dann Auswertung. Grundlage ist `data/zcash-mainnet/lauscher-nu7/` auf `messung/zcash-mainnet`, Stand nach Lauf 11 (Bot-Commit `0e9a7e05`, 8.11. 04:43 UTC). Ein Zuhörer an einem Ort, kein eigener Knoten. Keine Peer-Adressen.

<!-- discord -->
Zcash Mainnet, Zuhörer nach NU7. Ab NU7 sind 49 von 7.047 Kettenblöcken abgehängt (0,69 %), vor NU7 0 von 453. Alle Zweige mit Kopf haben Tiefe 1. Die Kette läuft wegen eines Fehlers im Endkriterium über 48 h hinaus weiter, bis spätestens 10.11. 00:00 UTC. Ben entscheidet, ob sie gestoppt wird. Bericht berichte/2026-11-08-zcash-lauscher.md
<!-- /discord -->

## Abdeckung

- **11 Läufe zu je 330 min**, 5.11. 17:02 bis 8.11. 04:37 UTC, zusammen 3.565,5 min (59,4 h).
- **Keine Lücke:** Jeder Lauf startete 4 bis 8 min vor dem Ende des vorigen.
- **NU7:** Block 3.543.405, Kopfzeit 6.11. 02:34:02 UTC. Das Fenster reicht bis 50 h danach. Die Werte „ab NU7“ gelten deshalb bis 50 h, die 6-h-Stücke decken 0 bis 48 h.
- **Kettenblöcke im Fenster:** 7.500, davon 7.494 bei uns angekündigt. Die 6 nicht angekündigten liegen alle nach NU7, je 3 in den Stücken 6 bis 12 h und 12 bis 18 h.

## Abgehängte Blöcke (counted)

| | Kettenblöcke | abgehängt | Anteil |
|---|---:|---:|---:|
| vor NU7 (75-s-Blöcke) | 453 | 0 | 0 % |
| ab NU7 (bis 50 h) | 7.047 | 49 | 0,691 % |

**Ab NU7 je 6 h:**

| Stunden nach NU7 | Kettenblöcke | angekündigt | abgehängt | Anteil |
|---|---:|---:|---:|---:|
| 0 bis 6 | 706 | 706 | 8 | 1,12 % |
| 6 bis 12 | 855 | 852 | 7 | 0,815 % |
| 12 bis 18 | 861 | 858 | 9 | 1,038 % |
| 18 bis 24 | 847 | 847 | 3 | 0,353 % |
| 24 bis 30 | 885 | 885 | 6 | 0,673 % |
| 30 bis 36 | 855 | 855 | 6 | 0,697 % |
| 36 bis 42 | 878 | 878 | 6 | 0,679 % |
| 42 bis 48 | 847 | 847 | 3 | 0,353 % |

Die Stücke ergeben zusammen 48 abgehängte Blöcke. Der 49. liegt zwischen 48 und 50 h.

**Tiefe der Zweige:**
- Von den 49 abgehängten Blöcken haben 37 einen Kopf bei uns, das sind 37 Zweige, alle mit **Tiefe 1**.
- 12 abgehängte Hashes haben keinen Kopf bei uns, ihre Tiefe ist unbekannt.

**Wer die abgehängten Blöcke angekündigt hat** (die 20 Beispiele in der Zusammenfassung):
- Zakura und Zebra: 10, nur Zakura: 7, nur Zebra: 3.
- 10 der 20 kamen von nur einem Peer.

**Vergleich mit dem Testnet am 17.10.:** 5 von 780 abgehängt (0,64 %), Tiefe 1. Das ist in derselben Größenordnung wie die 0,69 % ab NU7 im Mainnet.

## Ankunft und Peers

- **Zakura minus Zebra**, erste Ankunft je Block, 7.207 Blöcke:
  - Median −19 ms, p10 −135 ms, p90 +5.808 ms.
  - Zakura war bei 4.422 Blöcken zuerst (61,4 %).
- **Streuung über alle Peers** (erste bis letzte Ankündigung), 7.461 Blöcke: Median 18,0 s, p90 54,0 s, Maximum 167,6 s.
- **Erste Ankunft minus Kopfzeit:** Median 12,2 s, p90 36,8 s.
- **Verbindungen je Software** über alle Läufe: 263 zu Zakura, 139 zu Zebra (402 insgesamt).

  | Software | Verbindungen |
  |---|---:|
  | Zebra 7.0.0 | 109 |
  | Zakura 1.8.4 | 89 |
  | Zakura 1.8.3 | 67 |
  | Zakura 1.8.5 | 59 |
  | Zakura 1.7.0 | 26 |
  | Zebra 7.0.0-modified | 23 |
  | Zakura 1.8.0 | 8 |
  | Zakura 1.8.2 | 7 |
  | Zakura 1.8.0-modified | 7 |
  | Zebra 6.3.0 | 3 |
  | Zebra 5.0.0 | 2 |
  | Zebra 4.3.0 | 1 |
  | Zebra 6.2.3 | 1 |

- **Ankündigungen:** 35.271 von Zakura, 26.711 von Zebra.

## Problem: Die Kette endet nicht nach 48 h

- **Was passiert ist:** Lauf 11 meldete um 04:33 UTC „naechster lauf: ja, nu7 noch nicht erreicht“ und startete Lauf 12. Lauf 12 startete um 09:59 UTC Lauf 13.
- **Ursache:** Vor jedem Folgelauf ruft der Workflow kurz die Köpfe ab Höhe 3.543.355 ab, um die Zeit des NU7-Blocks zu finden. Dieser Abruf (`timeout 240`) liefert offenbar keine Datei mit dem Block. Dann gilt NU7 als „noch nicht erreicht“, und nur die harte Grenze `spaetestens_utc` (10.11. 00:00 UTC) beendet die Kette. Warum der kurze Abruf scheitert, sehe ich im Log nicht, weil seine Ausgabe verworfen wird.
- **Folge:** Die Kette läuft ohne Eingriff bis 10.11. 00:00 UTC weiter, also noch etwa 7 Läufe. Das schadet den Daten nicht, liegt aber außerhalb deines Auftrags. Jede Auswertung nach einem Lauf überschreibt `zusammenfassung.json` mit dem längeren Fenster. Die Zahlen oben gelten für den Stand nach Lauf 11.
- **Möglicher Fix:** Statt des kurzen Abrufs die Kopfzeit von 3.543.405 fest aus unseren Köpfen nehmen, oder die Ausgabe des Abrufs ins Log schreiben. Das ist eine Änderung an `.github/workflows/zcash-mainnet-lauscher.yml`, die prüfe ich und du mergst sie. Nötig ist sie nur, falls der Zuhörer noch einmal rund um ein Upgrade läuft.

## Offene Fragen an Ben

1. **Kette stoppen?** Soll ich den laufenden Lauf 13 abbrechen, damit kein weiterer startet? Oder lassen wir sie bis 10.11. 00:00 UTC laufen und werten nur bis 48 h aus?
2. **Post-Entwurf:** Soll die Zuhörer-Zahl (0,69 % abgehängt ab NU7, Tiefe 1) einen eigenen Entwurf nach #ph-entwuerfe bekommen?
3. **Fix am Workflow:** Soll ich ihn als PR vorbereiten, oder lassen wir es, weil der Zuhörer für NU7 fertig ist?

## Was Ben tun muss

1. Frage 1 entscheiden. Ohne Antwort läuft die Kette bis 10.11. 00:00 UTC.
