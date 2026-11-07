# Monero Stressnet, Zuhörer

Messbranch für den eigenen P2P-Zuhörer im Monero-Stressnet (FCMP++ und Carrot beta v3), Weg b aus `berichte/2026-11-06-monero-stressnet-plan.md`.

- `anstoss.txt` startet den Workflow `monero-stressnet-lauscher.yml` (nur auf diesem Branch).
- `probe-<zeit>/` ist eine Probe von 15 min, mit `meta.json`, `peers.json`, `bloecke.csv` und `ankuendigungen.csv`.
- Peers heißen `peer_N`. Es gibt keine IPs, keine Hostnamen und keine Peer-Adressen, 64 Hex-Zeichen nur für Blockhashes.
- Der Arbeitsnachweis (RandomX v2) wird nicht geprüft. Den Blockhash rechnen wir selbst nach, die Verkettung bestätigt ihn.
