# Miner nach dem Reward Cut, Datenstand

Gezählt vom eigenen Mainnet-Knoten im Runner (Workflows `miner-nach-cut.yml` und `miner-lauf.yml`, nur auf diesem Branch).

- `daten/stand.json`: gelesener Bereich, Läufe, erster beobachteter Kettenblock
- `daten/daa-zeit.csv`: je UTC-Minute kleinster und größter DAA-Score der Kettenblöcke
- `daten/rein.csv`: je UTC-Minute neue Coinbase-Ausgaben, Anzahl und sompi
- `daten/raus-<tag>.json`: je Entstehungsstunde (ms) der Verzug bis zur ersten Ausgabe in Eimern (Minuten), je Eimer Anzahl und sompi

Keine Adresse, kein Skript, keine Tx-ID. Auswertung mit `python3 scripts/miner_cut.py --auswerten`.
