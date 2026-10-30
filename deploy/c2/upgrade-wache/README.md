# Upgrade-Wache auf c2

Ben, 29.10.2026. Rund um eine Netz-Aktivierung erkennt unser eigener Zuhörer Störungen und meldet sie nach #ops-log. Der erste Einsatz ist Zcash NU7. Code und Signale: `scripts/wache/`, Bericht: `berichte/2026-11-02-warndienst-prototyp.md`.

In diesem Ordner steht kein Wert, keine IP und kein Hostname.

## Dateien

| Datei | Zweck |
|---|---|
| `upgrade-wache@.service` | Dauerdienst, eine Instanz je Chain (`upgrade-wache@zcash-mainnet`). Takt 60 s im Skript. Außerhalb des Fensters ruht die Wache und baut keine Verbindungen auf, deshalb darf die Unit vorher laufen. Nach einem Absturz startet sie nach 10 s neu. |
| `start.sh` | Setzt `DISCORD_WEBHOOK_LOG` aus dem Credential `discord_webhook_log` und startet `scripts/wache/wache.py` mit der Konfiguration der Chain. |
| `upgrade-wache-sync@.service`, `.timer` | Stündlich zur Minute 23: das Log der Wache auf den Datenbranch aus der Konfiguration (Zcash: `messung/zcash-mainnet`, Datei `wache/wache-log.csv`), mit Secret-Scan, als `kpbot` mit dem Deploy Key. |
| `sync.sh` | Der Ablauf dazu, in einem eigenen flachen Klon unter `/var/lib/kaspa-pulse/wache/<kette>/repo`. |

Auf c2 liegt alles unter `/var/lib/kaspa-pulse/wache/<kette>/`:
- `wache-log.csv`: das Log
- `zustand.json`: die Meldesperren und die Proben, übersteht einen Neustart
- `roh/`: die Ankündigungen und Köpfe des Zuhörers, bleiben auf c2

## Warum ein eigenes Credential

`discord_webhook` zeigt je nach `ziel` in `server-secrets.yml` auf #ops-log oder auf den öffentlichen Kanal. Die Wache meldet nur intern, deshalb liest sie `discord_webhook_log`. Das ist immer `DISCORD_WEBHOOK_LOG`, also #ops-log.

## Einrichten (Ben, einmal, vor Do 05.11. 02:00 UTC)

1. Den PR mergen.
2. Auf c2 die neuen Schreibhilfen holen. Der erste Lauf hält an, weil das Credential noch fehlt, das ist erwartet:
   ```
   ssh c2
   sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet
   ```
3. Auf GitHub `server-secrets` von Hand starten, mit **was = nur-wache**. Das Ziel spielt dabei keine Rolle, `discord_webhook` wird nicht angefasst. Die Gegenprobe am Ende zeigt `discord_webhook_log` mit seiner Größe.
4. Auf c2 noch einmal:
   ```
   sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet
   journalctl -u upgrade-wache@zcash-mainnet -n 20
   ```
   Vor dem Fenster steht dort stündlich eine Zeile „ruht, fenster ab …“.

## Nach dem Fenster

```
sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache-aus zcash-mainnet
```

Das hält Dienst und Timer an und bringt das letzte Log ins Repo. Bleibt der Dienst stehen, ruht er nur: Nach dem Fenster baut er keine Verbindungen mehr auf.

## Zeiten

Fenster und Zeiten stehen in UTC in der Konfiguration (`aktivierung.erwartet_utc`, `fenster.vor_h`, `fenster.nach_h`). Für NU7 ab 05.11. 02:26 UTC (03:26 Berlin), bis 72 h nach dem ersten NU7-Block. Der Sync-Timer läuft zur Minute 23 jeder Stunde, in UTC und Berlin gleich.
