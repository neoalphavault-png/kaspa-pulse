# BCH Tempnet Woche 2, Machbarkeit des Zuhörers (25.10.2026)

**Ja, der Zuhörer kann durchgehend laufen: als Kette von Läufen zu je 330 min, jeder startet den nächsten 8 min vor seinem Ende. Erste Daten liegen seit 25.10.2026 09:15 UTC vor (Testlauf), der Dauerlauf läuft seit 25.10. 09:34 UTC und läuft bis 15.11. 12:00 UTC.**

Einschränkung: Das automatische Weiterreichen geht erst, wenn `.github/workflows/bch-tempnet-lauscher.yml` auf main liegt (`workflow_dispatch` verlangt das). Bis zum Merge stoße ich jeden Lauf von Hand mit einem Push auf `data/bch/lauscher-anstoss.txt` an, etwa alle 5 h 20 min. An den Übergängen kann dabei eine Lücke von einigen Minuten entstehen; jede Lücke steht in den Lauf-Metadaten und kommt in den Bericht.

## Testlauf 25.10.2026, 09:15 bis 09:27 UTC (12 min)

- 5 Verbindungen mit bestätigtem Abzweig 327.989 (Software: Bitcoin Cash Node 29.2.1, Vcash 0.1), 7 Peers ohne Abzweig abgelehnt
- 13 von 13 Kettenblöcken angekündigt gesehen, im Median von 5 Peers
- timestamp_deviation im Median 0,72 s; propagation_spread im Median 9,6 s
- cmpctblock auf Anfrage für 12 von 13 Blöcken: im Median 1 Kurz-ID, in einem Block 1 TX, die wir nicht kannten
- Keine Peer-Adressen in Daten und Log, Secret-Scan ohne Fund

## Was wir sehen und was nicht

- **inv und headers:** ja, je Peer und je Nachrichtentyp mit Millisekunden.
- **cmpctblock als Ankündigung:** kam im Test von keinem Peer von selbst. Ein Knoten wählt höchstens drei Peers für den High-Bandwidth-Modus und offenbar keinen reinen Zuhörer. Wir holen deshalb für jeden Block einen cmpctblock beim ersten Ankündiger und zählen ihn als Compact-Weg, nicht als Ankündigung.
- **Fehlende TX:** Wir haben keinen Mempool. Wir sammeln die per inv angekündigten Transaktionen und zählen, wie viele Kurz-IDs eines cmpctblock zu keiner davon passen. Das ist eine Schätzung, keine Zahl eines echten Knotens.
- **Stale-Blöcke:** angekündigt, aber 6 Blöcke später nicht in der Kette; dazu brauchen wir den Kopf, den wir aus headers oder cmpctblock haben.

## Was Ben tun muss

- PR mit Workflow und Skripten möglichst früh mergen, dann reicht sich die Kette selbst weiter. Bis dahin halte ich sie mit Pushes am Laufen.
