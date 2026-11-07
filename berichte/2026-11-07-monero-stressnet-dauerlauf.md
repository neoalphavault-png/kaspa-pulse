# Monero Stressnet, Dauerlauf: erste Tagesauswertung und Köpfe (7.11.2026)

Ben hat am 7.11. den Dauerlauf des Zuhörers nach der erfolgreichen Probe freigegeben. Bedingungen: nur auf `messung/monero-stressnet`, keine IPs, keine Hostnamen, keine Peer-Adressen. Dieser Bericht enthält die erste Tagesauswertung nach Segment 1, dazu die Falken-Änderung vom selben Tag.

<!-- discord -->
Monero Stressnet, Dauerlauf läuft (Segment 2 von 30). Kette 3.125.743 bis 3.126.614 ohne Lücke, 872 Köpfe, alle durch den Nachfolger bestätigt. Am 7.11. Median der Abstände 80 s (computed 83,2 s), p90 301 s (276,3 s), Anteil über 10 min 1,1 % (0,67 %). PH-Falke oben rechts ist umgestellt. Bericht berichte/2026-11-07-monero-stressnet-dauerlauf.md
<!-- /discord -->

## Ablauf

- **Workflow:** `monero-stressnet-dauer.yml`, nur auf `messung/monero-stressnet`, Lauf 42374283536. Eine Matrix von 30 Läufen zu je 325 min, nacheinander (max-parallel 1), zusammen etwa 7 Tage.
  - Ein Neustart per workflow_dispatch wie beim BCH-Zuhörer ginge nur mit dem Workflow auf main. Deshalb die Matrix.
  - Nach jedem Lauf rechnet `stressnet_auswertung.py` die Hauptkette und die Zahlen je UTC-Tag neu.
- **Segment 1:** 7.11. 12:51 bis 18:15 UTC, grün.
  - Segment 2 startete um 18:16:15 UTC, die Lücke dazwischen war 22 s. Blöcke aus solchen Lücken holt der nächste Lauf nach.
  - Segment 1 hat zu Beginn 720 Blöcke rückwärts nachgeholt, damit die erste Tagesauswertung ganze Tage hat.
- **Peers in Segment 1:** 28 versucht, 17 verbunden, davon 12 Stressnet-Peers (7 mit ehrlicher Höhe 1, 5 mit der gesehenen Spitze).
  - Alle 12 schickten neue Blöcke und blieben bis zum Ende verbunden.
  - 5 Peers waren kein Stressnet und wurden getrennt. 8 Adressen antworteten nicht (Timeout), 2 lehnten ab.

## Köpfe (`koepfe.csv`)

- **Hauptkette:** Höhen **3.125.743 bis 3.126.614**, **872 Blöcke**, Kopfzeiten 6.11. 19:24:20 bis 7.11. 18:15:26 UTC.
- **Ohne Lücke:** Keine Höhe fehlt. Kein Block liegt abseits der Kette.
- **Herkunft:** 152 Blöcke wurden uns angekündigt, 720 wurden nachgeholt.
- **Hashes:** Jeden Blockhash rechnen wir selbst nach. 871 von 872 Hashes sind dadurch bestätigt, dass der nächste Block sie als Vorgänger nennt. Der letzte ist die Spitze, sein Nachfolger fehlt noch. Den Arbeitsnachweis (RandomX v2) prüfen wir nicht.
- **Transaktionen:** 2 in allen Blöcken zusammen, 12 Tx-Ankündigungen. Im Stressnet gibt es zurzeit fast keine Last.

## Erste Tagesauswertung (counted gegen computed)

Blockabstände nach Kopfzeit, je UTC-Tag des Blocks. Computed gilt für exponentielle Abstände mit Mittel 120 s.

| | 6.11. (ab 19:24 UTC) | 7.11. (bis 18:15 UTC) | computed |
|---|---:|---:|---:|
| Blöcke | 333 | 539 | |
| Abstände | 332 | 539 | |
| Median | 36,0 s | **80,0 s** | 83,2 s |
| p90 | 111,9 s | **301,2 s** | 276,3 s |
| p99 | 247,7 s | **590,6 s** | 552,6 s |
| Mittel | 49,1 s | 122,4 s | 120 s |
| Anteil über 10 min | 0 % | **1,11 %** | 0,674 % |
| negative Abstände | 0 | 0 | |
| längste Lücke | 437 s vor 3.126.070 | 1.016 s vor 3.126.378 | |

- **6.11.:** Der Tag ist nur zum Teil erfasst, 4,6 h ab 19:24 UTC. Die Blöcke kamen viel schneller als das Ziel, im Mittel alle 49 s. Das passt zu einer Schwierigkeit, die der Hashrate noch nachläuft. Die Ursache haben wir nicht untersucht.
- **7.11.:** Median und Mittel liegen nahe am Modell. Die langen Abstände sind etwas häufiger als berechnet: p90 und p99 liegen darüber, der Anteil über 10 min ist 1,11 % statt 0,674 %.

**Erste Sicht (nur Blöcke, die uns angekündigt wurden, 7.11.):**
- **Abdeckung:** 28,8 % der Kettenblöcke des Tages wurden uns angekündigt. Der Rest stammt aus der Zeit vor der Probe (08:40 UTC) und vor dem Dauerlauf (12:51 UTC) und wurde nachgeholt. Ab dem 8.11. sollte die Abdeckung bis auf die kurzen Lücken zwischen den Läufen bei fast 100 % liegen.
- **Peers je Block:** im Median 12.
- **Spread** über unsere Peers (erste bis letzte Ankunft), 155 Blöcke: Median **309 ms**, p90 1.062 ms.
- **Erste Sicht minus Kopfzeit:** Median 12,9 s.
- Ein Zuhörer an einem Ort, die Zeiten enthalten den Weg zu uns.

**Dateien** auf `messung/monero-stressnet`:
- `data/monero-stressnet/koepfe.csv`
- `auswertung/tage.csv`
- `auswertung/zusammenfassung.json`
- je Lauf `lauf/<zeit>/` mit `meta.json`, `peers.json`, `bloecke.csv` und `ankuendigungen.csv`

Keine IPs, keine Hostnamen, keine Peer-Adressen. Vor jedem Commit läuft der Secret-Scan.

## Falke oben rechts (PH-Stil)

- [kaspa-pulse#278](https://github.com/neoalphavault-png/kaspa-pulse/pull/278) und [pulsehawk-site#69](https://github.com/neoalphavault-png/pulsehawk-site/pull/69) sind selbst gemergt, Checks grün.
- `ph_stil.py` setzt den Falken jetzt oben rechts auf Höhe der ersten Textzeile (Kicker): 48 px, Türkis #49EACB, rechter Rand 96 px wie der Text. Im Querformat sind es 56 px auf Höhe des Titels.
- Alle Vorlagen übernehmen das. Angesehen habe ich die NU7-Karte, die Report-Karte und einen Zcash-Entwurf.
- Die NU7-Karte ist am 7.11. um 12:47 UTC in #ph-entwuerfe angekommen (Lauf 42374013999), zur Prüfung durch Ben um 20:05.

## Offene Fragen an Ben

1. **Schnelle Blöcke am 6.11.:** Interessiert dich der Grund? Ich könnte die Schwierigkeit je Block aus den Köpfen ableiten, sie steht aber nicht direkt im Kopf. Dafür bräuchte es einen weiteren Abruf.
2. **Warteschlange:** Ob GitHub so lange wartende Matrix-Jobs irgendwann abbricht, ist nicht sicher. Ich prüfe das am 8.11. um 14:00 UTC und melde mich, falls Segmente ausfallen.

## Was Ben tun muss

Nichts. Der Dauerlauf läuft von selbst bis etwa 14.11.
