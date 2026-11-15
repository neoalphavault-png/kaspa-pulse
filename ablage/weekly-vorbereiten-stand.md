# Stand der Montagsvorbereitung — KASPA WEEKLY

**Zeitpunkt: Sonntag, 15.11.2026, 08:33 Berlin time.**
Lauf: Wochenvorbereitung für Montag 16.11.2026 (Folge 12 und Montags-Short).
Diese Datei ist die Ablage für Claude. Sie enthält keine Skripte, keine Titel
und keine Uploadfelder; das Repo ist öffentlich.

## Zahl der Woche

Kaspa hat die Woche zum Samstag 14.11.2026 bei 0,02637 USD geschlossen,
11,12 % tiefer als die Woche davor, und steht damit 23,63 % unter der
50-Wochen-Linie — der weiteste Abstand unter dieser Linie seit **elf Wochen**
und die dritte Woche in Folge unter beiden Linien. Die Reihe trägt die
50-Wochen-Linie seit dem 02.11.2025, also 54 Wochen; über alle 54 ist dieser
Abstand der 44.-weiteste, also **kein Rekord**.

## Prüfzeilen

| Prüfung | Ergebnis |
| --- | --- |
| Short-Skript enthalten | **ja** |
| Manifest-Eintrag des Shorts enthalten | **ja** |
| Rekorde geprüft | **alle mit Zeitraum** |
| Quellen geprüft | **ok**, keine Quelle ergänzt |
| Keine Wenn-dann-Sätze zum Kurs | **geprüft**, 0 Treffer in Skript, Short und allen geschriebenen Texten |
| Echtzeit-Wörter in veröffentlichten Texten | **0** |
| Verhältnisse gegen die Rechnung geprüft | **ja**, Tabelle in der Lieferung |
| Gegenprobe gegen die Vorwoche | **bestanden**, zwölf von zwölf Werten gleich |
| Maschinelle Prüfung des Sprechskripts | 685 Wörter, 9 Befunde, alle von Hand geprüft, keiner ein Regelbruch |
| Maschinelle Prüfung des Shorts | 80 Wörter, 2 Befunde, beide wie in den Wochen 43 bis 46 |
| Test dieser Woche | **keiner von Ben freigegeben**, es gilt nur Test & Compare; der Short trägt `test: "keiner"` |

## Zeilen, die auf „offen" stehen

| Zeile | Letzte echte Messung |
| --- | --- |
| Gebührenanteil in Dollar (`fees_day`) | Mo 17.08.2026, am Erscheinungstag **91 Tage** alt |
| vidIQ-Score der drei Cover | **nicht gemessen** — der Upload-Weg über `vidiq_upload_image` ist in diesem Lauf erstmals versucht worden und am Netz dieser Sitzung gescheitert |

Alles Übrige ist gerechnet oder aus einer frischen Reihe gelesen.

## Datenausfall

| Reihe | Letzter gültiger Wert |
| --- | --- |
| `fees_day` / `fees_7d` | Wochenzeile Mo 17.08.2026 |
| `igra_tx` / `kasplex_tx` | dauerhaft leer |
| Entity-X-Transaktionsliste mit Absender-Label | keine Liste für 08. bis 14.11.2026 |

Keine dieser Reihen trägt eine gesprochene Zahl.

## Weitere Meldungen aus diesem Lauf

1. **Kaspalytics ist aus dieser Sitzung nicht erreichbar** (Netzrichtlinie).
   Die jüngste Kaspalytics-Zeile stammt vom 09.11.2026 und ist am
   Erscheinungstag genau sieben Tage alt, also nicht älter als sieben Tage.
2. **`data/weekly-history.json` hat keine Zeile für den 09.11.2026**, die
   letzte ist die Ausgabe 17 vom 02.11. `data/weekly.json` hat die Zeile.
   Für die Lieferung folgenlos, sieht aber so aus, als wäre der Montags-Post
   am 09.11. nicht durchgelaufen. Nur gemeldet, nicht repariert.
3. **Das im Auftrag genannte Verzeichnis `data/pruefung/` existiert nicht.**
   Die eigene Monatszählung der Gebühren steht wie in den Vorwochen in
   `data/tagesgrafik-log.json`, Lauf vom 15.11.2026.
4. **Hashrate-Lesungen nachgetragen**: 7 Lesungen dazu, 91 insgesamt. Keine
   Lücke gemeldet, kein Fehler.
5. **Keine „LUECKE:"-Zeile** im Lauf von `build_kp_short.py
   --lesungen-nachtragen`.

## Branch und Head

| | |
| --- | --- |
| Lieferung | `review/weekly-2026-11-16` im Repo `pulse-studio` |
| Head der Lieferung | `215959f99db6facf0726f58a10455192a3ec6f09` |
| Ablage | `claude/ablage-weekly-vorbereiten` im Repo `kaspa-pulse` |

Die Lieferung liegt bewusst **nicht** auf einem `claude/`-Branch: Ben liest
sie und merged selbst.
