# NU7-Karte „how close our estimates came“, neu mit Tabelle (8.11.2026)

Ben am 8.11.: Die NU7-Karte „expected against counted“ gefällt im Design, ist aber schwer zu verstehen. Gründe: die Zeitachse mit Band, „early“ in zwei Richtungen und Dezimalminuten. Neu gebaut mit Tabelle statt Achse. Die Regel ab jetzt für alle PH-Karten: Zeitabstände immer als Minuten und Sekunden.

<!-- discord -->
NU7-Karte neu: „how close our estimates came“, Tabelle statt Zeitachse, Abstände in min und s aus einer Richtung. Sie liegt mit der Vorschau mit 390 px in #ph-entwuerfe. Die Schätzung vom 2.11. nutzte 7 Tage, nicht 14, der Fuß sagt das. Bericht berichte/2026-11-08-nu7-karte-tabelle.md
<!-- /discord -->

## Die Rechnung

Richtung: Schätzung minus Kopfzeit von Block 3.543.405. Positiv heißt „too late“, die Schätzung lag nach dem Block. Die Kopfzeit ist 1793932442, also 6.11.2026 02:34:02 UTC, counted aus unseren eigenen Köpfen (`data/zcash-mainnet/koepfe.csv.gz` auf `messung/zcash-mainnet`).

| Schätzung gemacht | Quelle | Schätzung (Median, UTC) | Kopfzeit (UTC) | Differenz | auf der Karte | 90-%-Band (UTC) | im Band |
|---|---|---|---|---:|---|---|---|
| 23.10. | `stand-2026-10-23.json` | 6.11. 02:21:52 | 6.11. 02:34:02 | −730 s | 12 min 10 s too early | 5.11. 22:02:16 bis 6.11. 06:40:25 | inside |
| 28.10. | `stand-2026-10-28.json` | 6.11. 02:26:16 | 6.11. 02:34:02 | −466 s | 7 min 46 s too early | 5.11. 23:01:22 bis 6.11. 05:51:31 | inside |
| 2.11. | Wache-Konfiguration, Commit `77672e28` | 6.11. 02:39:52 | 6.11. 02:34:02 | +350 s | 5 min 50 s too late | 6.11. 00:28:23 bis 05:00:17 | inside |
| 4.11. | `stand-2026-11-04.json` | 6.11. 02:40:58 | 6.11. 02:34:02 | +416 s | 6 min 56 s too late | 6.11. 01:14:45 bis 04:07:28 | inside |

- Kontrolle wie von Ben vorgegeben: 4.11., Median 02:40:58, ergibt 6 min 56 s too late. Das stimmt.
- `nu7_karte.py` liest alle Werte aus diesen Dateien und rechnet sie selbst. Nichts ist eingetippt. Die Rechnung steht zusätzlich in `rechnung.json` neben der Karte.

## Abweichung vom Auftrag, bitte prüfen

**Die Schätzung vom 2.11. nutzte die 7 Tage davor, nicht 14.** Sie stammt aus `berichte/2026-11-02-nu7-hoehe-pruefung.md`, Abschnitt „Prognose mit den letzten 7 Tagen“: 8.020 Abstände vom 26.10. bis 2.11., Bootstrap über die Abstände. Die drei anderen Stände nennen in ihrer `stand-*.json` `tempo_fenster_tage: 14`.

Die vorgegebene zweite Fußzeile („each estimate computed from the block pace of the 14 days before it.“) wäre damit für den 2.11. falsch. Auf der Karte steht deshalb: „each estimate computed from the block pace of the 14 days before it, the 2 nov one from 7 days.“ Wenn du die Zeile anders willst, ändere ich sie.

## Die Karte

- **Kicker** „zcash nu7, 6 nov 2026“, **Titel** „how close our estimates came“.
- **Große Zahl** „6 min 56 s“ in Türkis, das einzige türkise Daten-Element. Darunter „our last estimate was 6 min 56 s too late“.
- **Tabelle** mit den Spalten „estimate made“, „we said“, „off by“ und „90% band“, vier Zeilen wie oben.
- **Fuß**: „block 3,543,405 at 02:34:02 utc, header time counted on our own header client.“ und die zweite Zeile wie oben, darunter „Data from PulseHawk · pulsehawk.io“.
  - Jede der beiden Zeilen bricht bei 30 px Schrift auf zwei Zeilen um. Kleiner geht nach der Untergrenze für den Feed nicht.
- **Stil-Prüfung** bestanden. Die Vorschau mit 390 px habe ich angesehen, alles ist lesbar.
- **Versand:** in #ph-entwuerfe am 8.11. um 09:36 UTC über `ph/stil-muster`, Karte und Vorschau, nicht gepostet.

## Regel „min und s“ im Stil-Modul

- `ph_stil.dauer(sekunden)` gibt „6 min 56 s“, „45 s“ oder „1 h 2 min 3 s“ zurück.
- `ph_stil.pruefen_daten()` meldet jede Dezimalminute im sichtbaren Text (zum Beispiel „5.8 min“) als Fehler. Das gilt für alle Karten, die über das Stil-Modul geprüft werden.
- Selbsttest von `ph_stil.py` mit den neuen Fällen: bestanden. Die gleiche Datei geht in pulsehawk-site, im eigenen PR.

## report_karte.py für den PH-Post am Mo 9.11. 11:00

- Abstände ab 60 s stehen als min und s, darunter Sekunden („56 s“, „57.6 s“).
- Eine Aussage in Worten unter der großen Zahl: „half of all blocks came within 18 s of the one before, the model says 17.3 s“.
- Zeilen: „90% of gaps within“, „99% of gaps within“, „gaps longer than 2 min 5 s“, „longest gap“.
- Keine Achse. Die große Zahl ist türkis.
- Mit der Beispiel-CSV aus pulsehawk/methods gebaut und angesehen. Selbsttest und Stil-Prüfung bestanden.

## Offene Fragen an Ben

1. Ist die zweite Fußzeile mit „the 2 nov one from 7 days“ so in Ordnung?

## Was Ben tun muss

1. Die Karte in #ph-entwuerfe prüfen.
