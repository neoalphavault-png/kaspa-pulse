# BCH Tempnet, Erste Sicht je Block (für das Forum, 7.11.2026)

`tempnet-first-seen-2026-10-25-bis-2026-11-07.csv`, eine Zeile je Block, den unser Zuhörer gesehen hat oder der in der Kette steht. Abgeleitet aus `../bloecke.csv` (Kettenblöcke) und `../zusammenfassung.json` (Stale-Blöcke), Stand nach Lauf 20261107T0235.

| Spalte | Inhalt |
|---|---|
| `height` | Höhe |
| `hash` | Blockhash |
| `header_time_utc` | Zeit im Kopf (vom Miner gesetzt) |
| `first_seen_utc` | erste Ankündigung bei unserem Zuhörer, Uhr des GitHub-Runners, Millisekunden. Leer, wenn der Block in eine Lücke zwischen zwei Läufen fiel |
| `announce_type` | Weg der ersten Ankündigung: `inv`, `headers` oder `cmpctblock` |
| `stale_after_6` | `yes`, wenn der Block angekündigt wurde, aber nicht in der Kette steht, obwohl die Kette 6 Blöcke darüber reicht |

- 55 Läufe, 25.10. 09:15 bis 7.11. 08:05 UTC, zusammen 297,2 h abgedeckt.
- Höhen 341.252 bis 359.938: 17.808 Kettenblöcke (43 ohne Erste Sicht) und 878 Stale-Blöcke.
- Ein Zuhörer an einem Ort, kein eigener Knoten. Keine IPs, keine Hostnamen, keine Peer-Adressen.
