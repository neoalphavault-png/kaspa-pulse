# BCH-Tempnet-Zuhörer auf c2, zweiter Messpunkt

Ben, 9.11.2026, Auftrag „Voller Knoten je Netz und BCH-Tempnet-Abschluss“, Teil C Punkt 10. Der Zuhörer auf GitHub misst über einen Netzwerkpfad, den der Runner. Dieser Dienst lässt denselben Zuhörer (`scripts/bch/tempnet_lauscher.py`) zusätzlich von c2 aus laufen, bis zum Tempnet-Ende am 15.11. um 12:00 UTC.

| Datei | Zweck |
|---|---|
| `start.sh` | Läufe zu höchstens 330 min nacheinander, vor und nach jedem Lauf die Uhr (`scripts/bch/uhr_versatz.py`). Ein fertiger Lauf bekommt die Datei `fertig`. |
| `bch-lauscher.service` | startet `start.sh` als kpbot, höchstens 512 MB Speicher, endet von selbst am Tempnet-Ende |
| `sync.sh` | stündlich fertige Läufe nach `messung/bch-tempnet` unter `data/bch/lauscher-c2/<lauf>/`, Secret-Scan vor dem Push |
| `bch-lauscher-sync.service`, `.timer` | stündlich zur Minute 41 |

Einrichten nach dem Merge:

```
cd /opt/kaspa-pulse/deploy/c2
sudo ./setup.sh bch-lauscher
```

Anhalten vor dem Tempnet-Ende, falls nötig:

```
sudo ./setup.sh bch-lauscher-aus
```

Kein Credential nötig. Gepusht wird mit dem Deploy Key, den auch die Upgrade-Wache nutzt. In Daten und Log stehen keine Adressen. Die Peers heißen `peer_N` wie auf GitHub. Die Uhr liest `uhr_versatz.py` über `chronyc tracking` oder, ohne chrony, über `timedatectl timesync-status`.

Ein Lauf, der abbricht (Neustart, Fehler), bekommt kein `fertig` und kommt nicht ins Repo. Er erscheint in der Auswertung als Lücke.
