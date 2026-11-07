# Monero Stressnet, Zuhörer

Messbranch für den eigenen P2P-Zuhörer im Monero-Stressnet (FCMP++ und Carrot beta v3), Weg b aus `berichte/2026-11-06-monero-stressnet-plan.md`.

- `anstoss.txt` startet eine Probe (Workflow `monero-stressnet-lauscher.yml`), `dauer-anstoss.txt` den Dauerlauf (`monero-stressnet-dauer.yml`, 30 Läufe zu je 325 min nacheinander). Beide laufen nur auf diesem Branch.
- `lauf/<zeit>/` hat je Lauf `meta.json`, `peers.json`, `bloecke.csv` und `ankuendigungen.csv`. Blöcke aus den Lücken zwischen zwei Läufen holt der nächste Lauf nach (`quelle` = `nachgeholt`, ohne Erste Sicht).
- `koepfe.csv` ist die Hauptkette aus allen Läufen. `auswertung/tage.csv` und `auswertung/zusammenfassung.json` enthalten die Zahlen je UTC-Tag, gezählt gegen berechnet für 120 s.
- `probe-<zeit>/` ist eine Probe von 15 min, mit `meta.json`, `peers.json`, `bloecke.csv` und `ankuendigungen.csv`.
- Peers heißen `peer_N`. Es gibt keine IPs, keine Hostnamen und keine Peer-Adressen, 64 Hex-Zeichen nur für Blockhashes.
- Der Arbeitsnachweis (RandomX v2) wird nicht geprüft. Den Blockhash rechnen wir selbst nach, die Verkettung bestätigt ihn.
