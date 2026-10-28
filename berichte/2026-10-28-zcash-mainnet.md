# Zcash Mainnet, Wochenstand und Kettentest des Zuhörers, Bericht 28.10.2026

Auftrag (Ben, 23.10.2026): erster Mittwochsstand bis Mi 28.10. 18:00 Berlin (17:00 UTC), dazu der Kettentest des Zuhörers, sobald kaspa-pulse#135 gemergt ist. kaspa-pulse#133 und #135 sind gemergt.

## Was gemacht ist

- **Wochenstand:** Er lag schon vor.
  - Der tägliche Lauf [40679904274](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40679904274) startete um 11:25 UTC statt 05:23 UTC. Geplante Läufe kommen in diesem Konto wie bekannt Stunden zu spät.
  - Weil Mittwoch ist, schrieb der Lauf `stand-2026-10-28.json` und `.md` auf `messung/zcash-mainnet` (Bot-Commit `3ae6899`).
  - Ein Start von Hand war nicht nötig.
- **Entwurf:** `ph-entwurf-zcash-mainnet.yml` lief grün ([40680792268](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40680792268)) und hat den Entwurf an #ph-entwuerfe geschickt (HTTP 200).
- **Kettentest:**
  - Der erste Versuch zeigte einen Fehler im Workflow.
  - Den habe ich in [kaspa-pulse#205](https://github.com/neoalphavault-png/kaspa-pulse/pull/205) behoben und vom PR-Branch aus erneut getestet. Der zweite Versuch war grün.
  - Siehe unten.

## Wochenstand gegen 75 s

Eigene Header über P2P, Abruf 28.10. 11:29:09 UTC. Blöcke 3.489.718 bis 3.533.510, 20.09. 07:01 bis 28.10. 11:28 UTC, 43.793 Abstände.

| Kennzahl | gezählt | berechnet (75 s) |
|---|---:|---:|
| Mittel | 75,34 s | 75 s |
| Median | 53 s | 52,0 s |
| p90 | 172,0 s | 172,7 s |
| p99 | 349,0 s | 345,4 s |
| Anteil über 225 s | 5,06 % | 4,98 % |
| Anteil über 518 s | 0,114 % | 0,1 % |
| Längste Lücke | 930 s, vor Block 3.524.451 am 20.10. 14:01 UTC | 845 s |
| Negative Abstände | 0 | 0 |

Die Wochenmittel W39 bis W44 liegen zwischen 75,27 und 75,41 s.

**Prüfung**
- **Verkettung und Checkpoints:** Verkettung, Arbeitsnachweis aus nBits und 89 Zebra-Checkpoints geprüft, kein Abzweig verworfen.
- **Gegenprobe:** Zwei Peers mit /Zebra:7.0.0/ lieferten je 500 von 500 gleiche Hashes.
- **Zakura:** Drei Gegenproben bei /Zakura:1.7.0/ blieben ohne Antwort (Zeitüberschreitung). Das ist dieselbe Beobachtung wie bisher: Zakura beantwortet `getheaders` in unserem Abruf nicht.
- **Datenschutz:** In Daten und Job-Log stehen keine IPs und keine Hostnamen. Der Log nennt nur Software und Fehlerart, der Secret-Scan im Lauf war sauber.

## Vorhersage für Höhe 3.543.405

Noch 9.895 Blöcke ab der Spitze 3.533.510. Das Tempo der letzten 14 vollen Tage liegt bei 75,29 s, die Tagesmittel zwischen 74,8 und 76,0 s.

| Rechnung | Stand 28.10. (UTC) | Stand 23.10. (UTC) |
|---|---|---|
| Gezähltes Tempo, Median | 06.11. 02:26 | 06.11. 02:21 |
| Band 5 % bis 95 % | 05.11. 23:01 bis 06.11. 05:51 (6,8 h) | 05.11. 22:02 bis 06.11. 06:40 (8,6 h) |
| Berechnet mit genau 75 s | 06.11. 01:37 | 06.11. 01:04 |
| Zakura (laut Ben) | 06.11. 00:50 | 06.11. 00:50 |

- **Median:** fünf Minuten später als am 23.10.
- **Band:** um 1,8 h schmaler, weil weniger Blöcke fehlen.
- **Zakura:** Die Schätzung liegt weiter im Band, 1 h 36 min vor unserem Median.
- **Rechnung mit 75 s:** Sie rückte um 33 min nach hinten, weil die Kette seit dem 23.10. im Mittel minimal langsamer als 75 s lief und die Rechnung jeweils ab der Spitze beginnt.

## Kettentest des Zuhörers

**Erster Versuch** (Dispatch auf main, Name `kettentest`, 2 × 20 min, `spaetestens_utc` 15:33 UTC)
- **Lauf 1** ([40711958040](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40711958040)) startete Lauf 2 nach knapp 13 min.
- **Lauf 2** ([40714132559](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40714132559)) meldete „nein, spaetestens erreicht“. Das Weiterreichen funktioniert also.
- **Rohdaten:** Beide Läufe haben ihre Rohdaten committet (`lauscher-kettentest/s01-*`, `s02-*`).
- **Fehler:** Danach scheiterten beide am Schritt „kette danach abrufen“ mit „kein peer erreichbar“. Der Abruf beginnt für jeden Namen außer `test` fest bei 3.540.000. Die Spitze lag bei 3.533.690, also lehnte der Client jeden Peer als „zurück“ ab.
- **Folge:** Eine `zusammenfassung.json` entstand nicht.

**Fix** ([kaspa-pulse#205](https://github.com/neoalphavault-png/kaspa-pulse/pull/205))
- Die Kette beginnt höchstens bei 3.540.000, sonst bei der kleinsten Median-Höhe der Peers eines Laufs minus 100.
- Für den Start am 5.11. ändert das nichts, die Peers melden dann über 3.540.000.

**Zweiter Versuch** (Dispatch auf dem PR-Branch, Name `kettentest2`, 2 × 20 min, `spaetestens_utc` 16:17 UTC)

| | Lauf 1 | Lauf 2 |
|---|---|---|
| Run | [40719377839](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40719377839), grün | [40721515847](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40721515847), grün |
| Zuhören UTC | 15:46:50 bis 16:06:50 | 15:59:46 bis 16:19:46 |
| Weiterreichen | startete Lauf 2 nach 12:55 min | kein dritter Lauf, „spaetestens erreicht“ |

- **Ablage:** Auf `messung/zcash-mainnet` liegen unter `data/zcash-mainnet/lauscher-kettentest2/` die Dateien `s01-*`, `s02-*` und eine `zusammenfassung.json` über 2 Läufe (Bot-Commit `8ed8170`).
- **Überdeckung:** Fenster 15:46:50 bis 16:19:46 UTC, abgedeckt 28,5 min. Die Läufe überlappen um 7 min, es gibt keine Lücke.
- **Peers:** 7 Zebra und 3 Zakura.
- **Blöcke:** Alle 33 Kettenblöcke haben wir angekündigt gesehen, 0 abgehängt.
- **Zakura minus Zebra:** Bei der ersten Ankündigung liegt der Median über 23 Blöcke bei 17,4 s, Zakura war nie zuerst. Im Testnet am 17.10. waren es 36 ms. Die Stichprobe ist klein. Ich nenne die Zahl, deute sie aber nicht.
- **Datenschutz:** In Daten und Log stehen nur Labels wie `zebra-1` und die Software, keine Adressen.

## Selbst-Merge

- [kaspa-pulse#206](https://github.com/neoalphavault-png/kaspa-pulse/pull/206) gemergt als `15e2267` am 28.10.2026. Live auf main ist dieser Bericht. Keine Seite betroffen, deshalb keine Abnahme auf einer URL.

## Offene Fragen an Ben

1. Die Testordner `lauscher-kettentest/` (unvollständig, ohne Zusammenfassung) und `lauscher-kettentest2/` liegen auf dem Datenbranch. Sollen sie bleiben oder vor dem 5.11. weg?
2. Im Entwurf vom 28.10. fehlt in der Deutungszeile ein Komma: „the share of intervals longer than 225 s, three times the target was 5.1 %“. Soll ich die Vorlage in `scripts/ph/ph_entwurf.py` korrigieren (nach „target“ ein Komma)? Das wäre ein eigener kleiner PR.

## Was Ben tun muss

- **[kaspa-pulse#205](https://github.com/neoalphavault-png/kaspa-pulse/pull/205) prüfen und mergen, vor dem Start des Zuhörers am Do 05.11. 17:00 UTC.** Ohne den Fix bricht der Kettenabruf ab, sobald die Spitze unter 3.540.000 liegt. Am 5.11. sollte sie knapp darüber liegen, sicher ist das nicht. Der PR ändert eine Workflow-Datei, deshalb kein Selbst-Merge.
- **Für diesen Berichts-PR nichts:** Ich habe ihn selbst gemergt, siehe unten.

Der Secret-Scan ist sauber. Peer-Adressen und Hostnamen stehen in keiner Datei und keinem Log.
