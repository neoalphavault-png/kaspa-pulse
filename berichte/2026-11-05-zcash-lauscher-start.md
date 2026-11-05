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

## Offene Fragen an Ben

keine

## Was Ben tun muss

nichts
