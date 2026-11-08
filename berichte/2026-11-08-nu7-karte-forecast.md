# NU7-Karte „4 of 4 forecasts“, Nachtrag 2 (8.11.2026)

Ben am 8.11., Nachtrag 2: Kicker mit zwei kurzen Zeilen, große Zahl „4 of 4“, Tabelle mit „forecast made“, „we said (utc)“, „the block came“ und „90% band“, drei Fußzeilen. In allen englischen Texten „forecast“ statt „estimate“. Die 90-%-Bänder bleiben, nichts wurde nachträglich umgerechnet.

<!-- discord -->
NU7-Karte nach Nachtrag 2: „4 of 4“, forecasts landed inside their 90% band. Sie liegt mit der Vorschau mit 390 px in #ph-entwuerfe. Alle vier Prognosen haben eine öffentliche, datierte Quelle auf GitHub, daher 4 of 4 und nicht 3 of 3. Die Fußzeile mit pulsehawk.io/track-record stimmt erst, wenn der Track Record auch den 23.10. und den 4.11. zeigt. Die Daten dafür hat die Seiten-Sitzung. Bericht berichte/2026-11-08-nu7-karte-forecast.md
<!-- /discord -->

## Die Karte

- **Kicker** „zcash nu7 upgrade, 6 nov 2026“, darunter „nu7 starts at a block height, not a set time.“ und „we forecast the time, and published every forecast in advance.“
- **Große Zahl** „4 of 4“ in Türkis, darunter „forecasts landed inside their 90% band“ und klein „published 14 to 2 days ahead, scored against the counted block“.
- **Tabelle** aus Sicht des Blocks:

| forecast made | we said (utc) | the block came | 90% band |
|---|---|---|---|
| 23 oct | 02:21:52 | 12 min 10 s later | inside |
| 28 oct | 02:26:16 | 7 min 46 s later | inside |
| 2 nov | 02:39:52 | 5 min 50 s earlier | inside |
| 4 nov | 02:40:58 | 6 min 56 s earlier | inside |

- **Fuß** in dieser Reihenfolge:
  1. „block 3,543,405 at 02:34:02 utc, header time counted on our own header client.“
  2. „forecasts from the block pace of the 14 days before each date, the 2 nov one from 7 days. method PH-M-006.“
  3. „every forecast, hits and misses, on pulsehawk.io/track-record“
  4. „Data from PulseHawk · pulsehawk.io“
- **Vorlauf** „14 to 2 days“ rechnet das Skript aus dem Tag der Prognose und dem UTC-Tag des Blocks. Vom 23.10. bis 6.11. sind es 14 Tage, vom 4.11. bis 6.11. sind es 2.
- **Stil-Prüfung** bestanden. Die Vorschau mit 390 px habe ich angesehen, alles ist lesbar.
- **Versand** in #ph-entwuerfe über `ph/stil-muster`, Lauf 42506627263 am 8.11. um 17:46 UTC grün. Nicht gepostet.

## Warum 4 of 4 und nicht 3 of 3

Jede Prognose hat eine öffentliche Quelle mit Datum:

| Prognose | Quelle | Zeitpunkt |
|---|---|---|
| 23.10. | `stand-2026-10-23.json`, Commit `9b20504f` auf `messung/zcash-mainnet` | 23.10. 12:55 UTC |
| 28.10. | Commit `3ae68994`, auf pulsehawk.io ab 28.10. 13:42 | 28.10. 11:32 UTC |
| 2.11. | Wache-Konfiguration, Commit `77672e28` auf main | 2.11. 12:39 UTC |
| 4.11. | Commit `26d9aa54`, dazu pulsehawk/methods `04f3f6c` | 4.11. 13:12 UTC |

Das Repo ist öffentlich, die Commit-Zeiten liegen alle vor dem Block am 6.11. um 02:34:02 UTC.

## Offener Punkt beim Track Record

Auf pulsehawk.io/track-record stehen heute nur TR-003 (28.10.) und TR-004 (2.11.). Beide stimmen. Der 23.10. und der 4.11. fehlen. Die dritte Fußzeile sagt „every forecast“ und stimmt erst, wenn beide nachgetragen sind.

- Ich habe der Sitzung für die Seite die Daten geschickt: 23.10. mit 12 min 10 s later, inside, Quelle `9b20504f`; 4.11. mit 6 min 56 s earlier, inside, Quelle `26d9aa54` und `04f3f6c`.
- Dort gilt ebenfalls: „forecast“ statt „estimate“, Richtung aus Sicht des Blocks.
- Die Karte erst posten, wenn der Track Record vier Einträge zeigt.

## „forecast“ statt „estimate“

- **Karte:** alle Texte sagen „forecast“.
- **pulsehawk/methods:** [pulsehawk/methods#4](https://github.com/pulsehawk/methods/pull/4), selbst gemergt, Merge-Commit `0e5019c`. Die Prosa in METHODS.md, README.md, CONTRIBUTING.md, dem README des Beispiels und dem Docstring von `report_v1.py` sagt jetzt „forecast“.
  - Absichtlich unverändert sind die Feldnamen von Format v1 (`estimate_utc`, `estimate`, `header_time_minus_estimate`) und die Notizen, die `report_v1.py` in die CSV schreibt. So bleiben das Format und die sha256 des Beispiels gleich. Der Selbsttest läuft durch.
  - Wenn du auch die Notiz in der CSV geändert haben willst, wäre das Format v2. Das schlage ich nicht vor.
  - Der Branch `forecast-wording` ließ sich nach dem Merge nicht löschen, die Verbindung brach ab. Ich versuche es wieder.
- **Bericht am Mo 9.11.:** Die geplante Aufgabe für 10:00 UTC hat jetzt die Regeln im Auftrag. „forecast“ und „Prognose“ im Text, die Feldnamen der CSV bleiben, die 90-%-Bänder bleiben, die Richtung aus Sicht des Blocks, Zeiten in min und s.

## Stil-Modul

- `ph_stil.py` erlaubt jetzt Methoden-IDs wie PH-M-006 in Großbuchstaben (Ben 8.11.). Alles andere auf der Karte bleibt klein. Der Selbsttest hat dafür einen eigenen Fall.
- Die gleiche Änderung kommt in pulsehawk-site in `scripts/ph/ph_stil.py`, als eigener PR.
- In den Fußzeilen sind die Ziffern der Tabelle abgeschaltet (`font-feature-settings:normal`). Mit Tabellenziffern standen die Bindestriche in „PH-M-006“ und „track-record“ zu weit auseinander.

## Offene Fragen an Ben

1. Passt die Karte so? Sie liegt in #ph-entwuerfe.
2. Soll die Notiz in der Report-CSV („positive means later than estimated“) bei Format v1 bleiben? Mein Vorschlag ist ja.

## Was Ben tun muss

- Karte in #ph-entwuerfe ansehen und freigeben.
- Erst posten, wenn pulsehawk.io/track-record den 23.10. und den 4.11. zeigt.
