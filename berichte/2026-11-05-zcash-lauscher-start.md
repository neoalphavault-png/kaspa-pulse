# Zcash Mainnet, Zuhörer für NU7 gestartet (5.11.2026)

Grundlage ist Bens Auftrag vom 23.10. Der Zuhörer soll wie am 17.10. im Testnet bis 48 h nach der Aktivierung zuhören. Die wichtigste Zahl ist der Anteil der angekündigten Blöcke, die bei 25 s nicht in die Kette kommen.

## Was gemacht ist

**Zeitpunkt des Starts:** Der Start sollte mindestens 4 h vor der unteren Bandgrenze liegen, damit auch ein Stück mit 75 s zum Vergleich da ist. Beide Stände erlauben einen Start jetzt.

| Stand | Median (computed) | untere Bandgrenze | spätester Start |
|---|---|---|---|
| Wochenstand 4.11. | 6.11. 02:40:58 UTC | 01:14:45 UTC | 5.11. 21:14 UTC |
| Tagesstand 5.11., Abruf 13:21:16 UTC | 6.11. 02:37:47 UTC | 01:46:56 UTC (Band bis 03:29:54) | 5.11. 21:46 UTC |

**Start:** `zcash-mainnet-lauscher.yml` lief per workflow_dispatch auf `main` als [Run 42070564704](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42070564704), Start 5.11. 17:02 UTC.
- Eingaben: name=nu7, segment=1, dauer_min=330, stunden_nach_nu7=48, spaetestens_utc=2026-11-10T00:00:00Z.
- Der Workflow liegt auf `main`, kaspa-pulse#135 ist also gemergt.
- Damit liegen bis zur unteren Bandgrenze gut 8,7 h mit 75 s.

**Prüfung der Verbindungen:** steht noch aus. Das Log eines laufenden Jobs gibt GitHub erst nach dessen Ende frei (HTTP 404 auf die Abfrage). Lauf 1 endet gegen 22:35 UTC. Am 5.11. um 22:50 UTC prüfe ich:
- die Verbindungen je Software in `s01-meta.json`, nur Labels und Software,
- ob das Job-Log frei von Adressen ist,
- ob Segment 2 startet.

Fehlt Zebra oder Zakura, oder startet Segment 2 nicht, melde ich das sofort und starte Segment 2 von Hand.

## Nachtrag 5.11. 22:50 UTC: Lauf 1 geprüft

**Lauf 1 ist grün.** [Run 42070564704](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42070564704) hörte von 17:02:19 bis 22:32:19 UTC zu (330 min). Die Rohdaten liegen auf `messung/zcash-mainnet`, Commit `fba722f`, die Auswertung im Commit `92c9053`.

**Verbindungen** laut `lauscher-nu7/s01-meta.json` und `zusammenfassung.json`, nur Kennung und Software:

| Software | Verbindungen im Lauf |
|---|---:|
| Zebra 7.0.0 | 9 |
| Zebra 7.0.0-modified | 1 |
| Zakura 1.8.3 | 11 |
| Zakura 1.8.2 | 7 |
| Zakura 1.7.0 | 4 |
| Zakura 1.8.0 | 1 |
| Zakura 1.8.0-modified | 1 |

Zusammen waren das 10 Zebra- und 24 Zakura-Verbindungen. Sie meldeten 1.124 und 1.189 Ankündigungen.

**Erster Stand, vor NU7** (counted):
- 260 Kettenblöcke im Fenster, alle bei uns angekündigt, 0 abgehängt, keine Zweige.
- abgedeckt 320,2 min.
- Zakura kündigte im Median 3.319 ms nach Zebra an, p10 73 ms, p90 12.784 ms, über 248 Blöcke.

**Adressen:** In `s01-meta.json` steht keine IP. In den letzten 120 von 673 Zeilen des Job-Logs steht ebenfalls keine; abgelehnte Peers erscheinen dort nur mit dem Fehlertyp. Das ganze Log konnte ich nicht laden: Der Download-Link führt auf einen Speicher-Host, den der Proxy dieser Sitzung mit 403 sperrt. Das habe ich nicht umgangen.

**Segment 2** hat Lauf 1 selbst gestartet: [Run 42121429677](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42121429677), ab 22:25:55 UTC. Es überlappt mit Lauf 1, es gibt also keine Lücke.

## Offene Fragen an Ben

keine

## Was Ben tun muss

nichts
