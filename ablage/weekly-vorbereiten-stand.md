# Stand: KASPA WEEKLY vorbereiten — So 01.11.2026, 08:30 Berlin time

Kopfteil der Meldung an Ben. Keine Skripte, keine Titel, keine Uploadfelder.

## Zahl der Woche

Kaspa hat die Woche zum Sa 31.10.2026 bei 0,03257 USD geschlossen, 9,65 %
tiefer, und steht 7,72 % unter der 50-Wochen-Linie — in den 52 Wochen, in
denen unsere Reihe beide Linien führt, ist das die erste Woche, die beide
Linien in einem Schritt verliert.

## Prüfzeilen

- Short-Skript enthalten: ja, Manifest-Eintrag: ja
- Rekorde geprüft: alle mit Zeitraum
- Quellen geprüft: ok (zwei Kaspalytics-Zahlen im Gesprochenen, beide mit
  „source kaspalytics" im selben Satz; keine Kaspalytics-Zahl im Short)
- Telegram 443 Zeichen, Discord 447 Zeichen, Verhältnisse geprüft, keine
  Echtzeit-Wörter
- Maschinelle Skriptprüfung: 0 Ziffern, 0 buy/bought/purchase, 0
  Echtzeit-Wörter, kein Satz ab 15 Wörtern, kein Rekord-Wort ohne Zeitraum
- Test dieser Woche: nur Test & Compare, kein von Ben freigegebener Test

## Zahlen auf offen

| Zeile | Letzte echte Messung |
| --- | --- |
| Gebührenanteil der gezählten Woche | 17.08.2026 |
| Gebührenanteil September (gesprochene Zahl) | 25.09.2026, am Erscheinungstag 38 Tage alt |
| Kaspalytics-Wochenzeile insgesamt | 26.10.2026, am Erscheinungstag 7 Tage alt |
| vidIQ-Scores für Titel und Cover | nicht gemessen, vidIQ in dieser Sitzung nicht angemeldet |

## Datenausfall

| Reihe | Letzter gültiger Wert | Alter am Erscheinungstag |
| --- | --- | --- |
| fees_day / fees_7d | Wochenzeile 17.08.2026 | 77 Tage |
| Entity-X-Transaktionsliste mit Absender-Label | keine Liste für 25.–31.10. | — |
| igra_tx / kasplex_tx | dauerhaft null | — |

Zusätzlich: der Selbsttest von `kp/shorts/build_kp_short.py` meldet seit
diesem Wochenschluss einen Fall rot („auf dem heutigen stand ist der abstand
nicht kleiner"). Ursache sind die Daten, nicht der Code: der Testfall nimmt
an, dass der Abstand zum letzten Schluss über der 21-Wochen-Linie nie
kleiner wird, und diese Woche schließt der Kurs unter dieser Linie. Nicht
geändert, Entscheidung liegt bei Ben.

## Branch und Head

- Lieferung: `review/weekly-2026-11-02`, Head `c726bd4` (pulse-studio)
- Diese Ablage: `claude/ablage-weekly-vorbereiten` (kaspa-pulse)
