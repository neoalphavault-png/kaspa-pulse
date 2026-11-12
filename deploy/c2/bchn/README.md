# BCHN geprunt auf c2

Ben, 9.11.2026: Ein eigener, voll validierender BCH-Knoten, damit jede gezählte Zahl gegen einen eigenen Knoten geprüft werden kann. Geprunt, weil c2 nur 38 GB Platte hat. Ein geprunter BCHN lädt und prüft trotzdem jeden Block. Er löscht danach nur alte Blockdateien, der Index aller Köpfe bleibt.

| Datei | Zweck |
|---|---|
| `bitcoin.conf` | `prune=4000` (MiB), `dbcache=300`, `listen=0`, RPC nur lokal, `logips=0` |
| `bchn.service` | Nutzer `bchn`, Daten unter `/var/lib/bchn`, `MemoryMax=1200M`, `CPUQuota=100%` (ein Kern von zwei), Nice 10, IO im Leerlauf. Startet nicht vor dem 15.11.2026 um 12:00 UTC. |

## Einrichten

Paket aus dem signierten PPA von Bitcoin Cash Node (Launchpad, Schlüssel `535B997250F23C9CD17B00ECF21A055668D26A91`). `setup.sh` prüft den Fingerabdruck, bevor es die Quelle einträgt.

```
cd /opt/kaspa-pulse/deploy/c2
sudo ./setup.sh bchn            # installieren, Nutzer, Unit; startet erst nach dem Tempnet-Ende
sudo ./setup.sh bchn-stand      # Höhe und Fortschritt, ohne Adressen
sudo ./setup.sh bchn-aus        # anhalten
```

Vor dem 15.11. um 12:00 UTC installiert `setup.sh bchn` nur und aktiviert die Unit. Gestartet wird sie mit `sudo systemctl start bchn` nach dem Tempnet-Ende, oder beim nächsten Neustart von c2.

## Bedarf, geschätzt

- **Platte:** rund 4 GB Blockdateien und der UTXO-Bestand von einigen GB. `setup.sh` bricht ab, wenn weniger als 20 GB frei sind.
- **RAM:** höchstens 1,2 GB durch `MemoryMax`.
- **Erstsynchronisation:** Die BCH-Kette hat rund 250 GB, die einmal geladen werden. Mit einem Kern und kleinem Cache rechne ich mit mehreren Tagen bis zwei Wochen. Die echte Dauer messen wir.
- **Verkehr:** einmal rund 250 GB nach innen, danach wenig.
