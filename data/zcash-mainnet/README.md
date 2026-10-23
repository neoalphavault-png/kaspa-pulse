# Zcash Mainnet, Zaehlung rund um NU7

Datenbranch, wird nie nach main gemergt (Ben, 22.10.2026: Roh-Header kommen nie nach main).
Der Workflow `zcash-mainnet.yml` schreibt hierher:

- `koepfe.csv.gz` und `koepfe-meta.json`: eigene Header aus dem P2P-Netz (Verkettung, Arbeitsnachweis, Zebra-Checkpoints geprueft)
- `stand-JJJJ-MM-TT.json` und `stand-JJJJ-MM-TT.md`: Kennzahlen gegen die 75-s-Kette und die Vorhersage fuer Hoehe 3.543.405

Keine IPs oder Hostnamen von Peers, nur die Software der Peers.
