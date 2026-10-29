# Warndienst-Prototyp „Upgrade-Wache Zcash NU7“, Bericht

Auftrag (Ben, 29.10.2026, Frist Mo 02.11. 16:00 Berlin): Rund um die NU7-Aktivierung auf dem Zcash Mainnet erkennt unser eigener Zuhörer Störungen und meldet sie intern nach #ops-log. Prototyp für ein späteres Abo je Chain, deshalb eine Konfiguration je Chain und kein Zcash-Sonderweg im Kern.

## 0. Aktivierung, aus offizieller Quelle

| | Wert | Quelle |
|---|---|---|
| Aktivierungshöhe Mainnet | 3.543.405 | ZIP 259 „Deployment of the NU7 Network Upgrade“, `ACTIVATION_HEIGHT (NU7) Mainnet: 3543405`. Eingetragen mit Commit `80c9e3a` „Set the NU7 mainnet activation height to 3543405“ am 20.10.2026 22:43 UTC: [zcash/zips, zips/zip-0259.md](https://github.com/zcash/zips/blob/main/zips/zip-0259.md) |
| Mindest-Protokollversion | 170190 | ZIP 259, `MIN_NETWORK_PROTOCOL_VERSION (NU7) Mainnet: 170190`: „nodes compatible with NU7 activation on that network MUST advertise a network protocol version greater than or equal to …“ |
| Software | Zebra 7.0.0, veröffentlicht 22.10.2026 | [Release Notes Zebra 7.0.0](https://github.com/ZcashFoundation/zebra/releases/tag/v7.0.0): „This release supports the NU7 network upgrade on Mainnet, which activates at height 3,543,405.“ und „advertise network protocol version 170190“ |
| Erwartete Zeit | **keine in einer Primärquelle** | Weder ZIP 259 noch die Zebra-Release-Notes nennen ein Datum oder eine Uhrzeit. Nachrichtenseiten schreiben „5. November“. |
| Erwartete Zeit, computed | 06.11.2026 02:26 UTC, 90-%-Band 05.11. 23:01 bis 06.11. 05:51 UTC | Unsere Vorhersage aus dem Wochenstand 28.10.2026 (Tempo der letzten 14 Tage, 75,29 s). Mit genau 75 s gerechnet: 06.11. 01:37 UTC. Zakura (laut Ben): 06.11. 00:50 UTC. |

zips.z.cash, z.cash und zfnd.org sind aus unserer Umgebung nicht erreichbar. Die ZIP-Datei habe ich deshalb aus dem GitHub-Repo `zcash/zips` gelesen. Eine Zakura-Release-Seite habe ich nicht gefunden.

Die erwartete Zeit steht in der Konfiguration (`aktivierung.erwartet_utc`). Sie legt nur den Fensterbeginn fest, das Ende rechnet die Wache ab dem ersten NU7-Block, den sie selbst sieht. Mit dem Wochenstand vom Mi 04.11. ziehe ich sie nach.

## 1. Fenster

- **Beginn:** erwartete Aktivierung minus 24 h, also ab 05.11. 02:26 UTC (03:26 Berlin).
- **Ende:** erster NU7-Block, den die Wache selbst sieht, plus 72 h. Bei Aktivierung um 06.11. 02:26 UTC also 09.11. 02:26 UTC.
- **Vorlauf:** Zehn Minuten vor dem Fenster baut die Wache ihre Verbindungen auf, damit die Höhen zum Beginn verankert sind.
- **Außerhalb:** Die Wache ruht. Sie baut keine Verbindung auf und schreibt nur stündlich eine Zeile „ruht“ ins Log.

## 2. Signale

Alle Signale kommen nur aus eigenen Daten: dem Zuhörer (Ankündigungen und Köpfe), dem Header-Client (Höhen, geprüft auf Verkettung und Arbeitsnachweis) und einer Handschlag-Probe. Alle Schwellen stehen in `scripts/wache/ketten/zcash-mainnet.json`.

| | Signal | Wann | Stufe | Ende, Entwarnung |
|---|---|---|---|---|
| a | Blockpause | seit 600 s kein neuer Block an der Spitze / seit 1.200 s | Hinweis / Alarm | nächster Block |
| b | Kettenspaltung | ab Höhe 3.543.405 zwei Zweige mit eigenem Hash auf derselben Höhe, je Seite mindestens 2 Peers, der kürzere mehr als 2 Blöcke tief | Alarm | der kürzere Zweig wächst 30 min nicht mehr |
| c | Reorg | unsere Spitze springt auf einen Zweig, und mindestens 2 Blöcke der alten Spitze fallen heraus | Alarm | 6 weitere Blöcke ohne neuen Reorg |
| d | Peers vor NU7 | Anteil erreichbarer Peers mit Protokoll unter 170190, zur Aktivierung und 6 h danach | Info | einmalig je Zeitpunkt, nur der Anteil |
| e | Median der Abstände | Median der letzten 12 Abstände (Kopf-Zeitstempel) über dem Doppelten des Ziels: 150 s vor NU7, 50 s ab NU7 | Alarm | Median wieder darunter |
| f | eigene Sicht (zusätzlich) | weniger als 2 Verbindungen seit 300 s | Hinweis | wieder mindestens 2 |

**Wie die Signale gemessen werden**
- **a, Ziel:** Bens Vorgabe nennt 75 s als Ziel. Die Schwellen von a gelten fest (10 und 20 min), auch nach NU7. Bei e wechselt das Ziel mit der Höhe auf 25 s, weil ab NU7 25-s-Blöcke gelten.
- **a, Messung:** Gemessen wird ab der Ankunft der aktuellen Spitze bei uns, nicht ab ihrem Zeitstempel.
- **b und c, Baum:** Die Wache hält einen Baum aller gesehenen Köpfe. Die beste Spitze ist die mit der meisten Arbeit aus nBits.
- **c, Log:** Jeder Spitzenwechsel steht im Log (`reorg_gesehen`), auch Tiefe 1. Die gehen in den Bericht nach dem Fenster.
- **d, Probe:** Handschlag mit bis zu 80 Adressen aus den DNS-Seeds. Gewertet wird nur die gemeldete Protokollversion, danach trennt die Probe die Verbindung. Die Peers des Zuhörers allein wären verzerrt, er hält je Software nur 8 Verbindungen und nimmt keine fremde Software.
- **f:** Ist neu. Ohne Verbindungen sähe eine Panne bei uns aus wie eine Blockpause im Netz. Bei f meldet die Wache deshalb keine Blockpause, sondern ihre eigene Blindheit.

## 3. Meldung

- **Ziel:** nach #ops-log über `DISCORD_WEBHOOK_LOG`, das Secret, das alle Workflows für #ops-log nutzen.
- **Inhalt:** Signal, Höhe, UTC-Zeit, Wert und Schwelle.
- **Takt:** höchstens eine Meldung je Signal und 30 min.
- **Ausnahme:** Der Aufstieg vom Hinweis zum Alarm geht einmal sofort raus, sonst käme der Alarm einer Blockpause erst nach 40 min.
- **Entwarnung:** kommt, sobald ein gemeldetes Signal endet, mit seiner Dauer.
- **Grenzen:** Nichts geht öffentlich, nichts geht auf X.

Beispiel aus der Simulation:

```
TEST upgrade-wache zcash-mainnet-simulation | ALARM reorg | hoehe 4,512,251 | 2026-10-17 16:10:57 UTC | wert 2 bloecke | schwelle ab 2 bloecke
```

Eine Korrektur zu meinem Bericht vom 28.10.: Das #ops-log-Secret heißt `DISCORD_WEBHOOK_LOG`. Ich hatte dort nach `DISCORD_WEBHOOK_OPS_LOG` gesucht und deshalb „kein Secret für #ops-log“ gemeldet. Das war falsch.

## 4. Log

- **Ablage:** `wache/wache-log.csv` auf dem Branch `messung/zcash-mainnet`, Spalten `utc, hoehe, signal, wert, schwelle, stufe`.
- **Inhalt:** jede Stufenänderung, jede Entwarnung, jeder Spitzenwechsel, die Proben, der Fensterbeginn, die gesehene Aktivierung und stündlich eine Zeile `lauf` mit der Zahl der Verbindungen.
- **Datenschutz:** Peers stehen nirgends, also keine Adressen, keine IPs und keine Hostnamen.
- **Sync:** Auf c2 schreibt die Wache das Log sofort. Ein Timer bringt es stündlich ins Repo, mit Secret-Scan.

## 5. Betrieb: auf c2, als Dienst

**Entscheidung: Dauerdienst auf c2** (`upgrade-wache@zcash-mainnet.service`), Takt 60 s.
- **Keine Übergaben:** Ein GitHub-Job läuft höchstens 6 h. Das Fenster dauert 96 h, also bräuchte es eine Kette von mindestens 18 Läufen. Jede Übergabe ist eine Lücke oder eine Überlappung mit doppelten Meldungen, und der Zustand der Wache müsste über die Läufe gerettet werden.
- **Keine Verspätung:** Geplante Läufe kommen in diesem Konto 6 bis 7 h zu spät (`deploy/c2/taktgeber/README.md`). Eine Wache, die erst Stunden nach ihrer Zeit startet, verpasst den Fensterbeginn.
- **Erprobtes Muster:** c2 betreibt mit `entity-x-alarm` schon einen Minutendienst nach demselben Muster. Secrets kommen dort verschlüsselt über `systemd-creds`, kein Wert liegt in einer Datei.
- **Abo-tauglich:** Eine Unit-Vorlage, eine Instanz je Chain, also `upgrade-wache@<kette>`.
- **Zweiter Netzwerkpfad:** Der Zuhörer für deine 48-h-Messung läuft ab 05.11. 17:00 UTC auf GitHub, die Wache auf c2.

Der Preis: Du musst auf c2 einmal Hand anlegen (unten). Es gibt keinen Cron. Fenster und Zeiten stehen in UTC in der Konfiguration, der stündliche Sync läuft zur Minute 23, in UTC und Berlin gleich.

**Was ich gebaut habe**

| Datei | Zweck |
|---|---|
| `scripts/wache/wache_kern.py` | Kern: Blockbaum, Signale, Meldesperren, Entwarnung, Log. Ohne Chain-Bezug |
| `scripts/wache/quelle_zcash.py` | Quelle `zcash_p2p`: der vorhandene Zuhörer, Anker über den Header-Client, Peer-Probe |
| `scripts/wache/wache.py` | Start: Fenster, Takt, Ruhephase |
| `scripts/wache/simulation.py` | Simulation mit aufgezeichneten Daten |
| `scripts/wache/ketten/zcash-mainnet.json` | Konfiguration NU7, scharf |
| `scripts/wache/ketten/bch-upgrade-2027.beispiel.json` | Beispiel BCH, nicht scharf |
| `deploy/c2/upgrade-wache/` | Unit, Sync-Timer, `start.sh`, `sync.sh`, README |
| `deploy/c2/setup.sh` | neue Schritte `wache` und `wache-aus` |
| `deploy/c2/credstore/kp-credstore-put`, `kp-credstore-ssh` | `discord_webhook_log` als erlaubter Name |
| `.github/workflows/server-secrets.yml` | neue Auswahl `was=nur-wache`. Die alten Schritte haben jetzt ausdrückliche Bedingungen, damit `nur-wache` den öffentlichen `discord_webhook` nicht anfasst |
| `.github/workflows/upgrade-wache-test.yml` | Probe, nur auf dem Branch `wache/prototyp` |

**Warum ein eigenes Credential:** `discord_webhook` auf c2 zeigt je nach `ziel` auf #ops-log oder auf den öffentlichen Kanal. Die Wache darf nie öffentlich melden, deshalb liest sie `discord_webhook_log`.

## 6. Test

### Simulation mit aufgezeichneten Daten

**Grundlage:** die echte Aufzeichnung unseres Zuhörers im Zcash-Testnet vom 17.10.2026 (14:51 bis 20:21 UTC, 776 Kettenblöcke, 5 abgehängte Blöcke der Tiefe 1) und die geprüften Testnet-Köpfe (`messung/zcash-nu7`).

**Was simuliert ist:** Der Kern ist derselbe wie im Betrieb, simuliert sind nur Uhr und Quelle. Die Aktivierungshöhe liegt 60 Blöcke nach Beginn der Aufzeichnung (4.512.127). Das Ziel ist auf beiden Seiten 25 s, weil Testnet seit 04.10. mit 25 s läuft. Die zweite Peer-Probe kommt nach 1 h statt nach 6 h, weil die Aufzeichnung nur 5,5 h lang ist.

| Szenario | gebaut aus der Aufzeichnung | erwartet | Ergebnis |
|---|---|---|---|
| grundlage | unverändert | nur Info zu d; die echten Reorgs der Tiefe 1 lösen nichts aus | ok, 2 Spitzenwechsel der Tiefe 1 im Log, kein Alarm |
| blockpause | ab Aktivierung + 2 h kommt alles 25 min später | Hinweis, Alarm, Entwarnung | ok, Hinweis bei 622 s, Alarm bei 1.222 s, Entwarnung mit dem nächsten Block |
| kettenspaltung | zweiter Zweig von 4 Blöcken ab Aktivierung + 30, von 2 Peers angekündigt | Alarm, Entwarnung | ok, Alarm „4 Blöcke“, Entwarnung nach 30 min Ruhe |
| reorg | 2 Blöcke eines Nebenzweigs kommen je 3 s vor der Kette und werden überholt | Alarm Tiefe 2, Entwarnung | ok, Alarm 23 s nach dem Spitzenwechsel (nächster Takt), Entwarnung nach 6 Blöcken |
| median_abstand | 14 Köpfe mit 120 s Abstand im Zeitstempel | Alarm, Entwarnung | ok, Alarm bei 52,5 s gegen 50 s, Entwarnung bei 21,5 s |
| eigene_sicht | 10 min nur 1 Verbindung | Hinweis, keine Blockpause | ok |
| peers_vor_upgrade | in jedem Szenario | Info zur Aktivierung und danach | ok, 57,1 % (8 von 14) und 53,3 % (8 von 15) unter 170190 |

Der Wert für d stammt aus dem Testnet. Dort gilt als Mindestwert 170180, und `Zebra 7.0.0-rc.0` meldet 170180. Die Simulation prüft mit dem Mainnet-Wert 170190 nur den Weg, nicht das Ergebnis.

Auf GitHub ([upgrade wache test](https://github.com/neoalphavault-png/kaspa-pulse/actions/workflows/upgrade-wache-test.yml)) läuft dieselbe Simulation bei jedem Push auf den Branch.

### Live, 15 Minuten auf dem Mainnet, trocken

Lauf [40912814954](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40912814954) am 29.10.2026, Job „live“, grün. Die Wache lief mit offenem Fenster 15 min gegen das echte Mainnet, ohne zu senden.

| | Ergebnis |
|---|---|
| Verbindungen | 3 Peers: 2 × /Zebra:7.0.0/, 1 × /Zakura:1.7.0/ |
| Anker | nach 4 min 6 s, 307 Köpfe bis Höhe 3.534.900. Der Header-Client holt ab dem letzten Zebra-Checkpoint, das dauert beim Start |
| Kette verfolgt | von 3.534.900 bis 3.534.905 in 11 min, jeder neue Block über den Zuhörer |
| Meldungen | 0, kein Signal aktiv |
| Peer-Probe (Signal d) | 8 von 34 Adressen aus den DNS-Seeds antworteten, 2 davon mit Protokoll 170150, also 25 % unter 170190. Die übrigen 6 melden 170190 |
| Adressen | keine in Log und Zustand, eigene Prüfung im Lauf |

Zwei Beobachtungen für den Betrieb:
- **Kurzer Anlauf:** In den ersten 4 Minuten nach einem Start kennt die Wache noch keine Höhe und meldet nichts, außer zur eigenen Sicht. Deshalb läuft der Dienst nicht mit geplantem Neustart.
- **Kleine Probe:** Nur 8 von 34 Adressen antworteten. Für Signal d ist die Probe damit klein; die Zahl der antwortenden Peers steht deshalb in jeder Meldung dabei.

### Beispielmeldungen in #ops-log

BEISPIELE

## 7. Konfig-Beispiel für BCH (nicht scharf)

- **Datei:** `scripts/wache/ketten/bch-upgrade-2027.beispiel.json`.
- **Was sich ändert:** Für eine zweite Chain ändert sich nur diese Datei: Quelle, Aktivierung, Ziel, Schwellen und Ablage.
- **Noch nicht gebaut:** die Quelle `bch_p2p`. Sie würde `scripts/bch/tempnet_lauscher.py` so einbinden wie `quelle_zcash.py` den Zcash-Zuhörer, das sind etwa 120 Zeilen.
- **Offen bei BCH:** Das Upgrade aktiviert nach Zeit (Median Time Past), nicht nach Höhe. Eine Mindest-Protokollversion ist nicht festgelegt.

## Offene Fragen an Ben

1. **Schwelle a nach NU7:** Bei 25 s Ziel bedeuten 10 min Pause 24 Zielabstände, vorher waren es 8. Sollen die Schwellen der Blockpause ab NU7 sinken, etwa auf 4 und 8 min? Bisher gelten 10 und 20 min, wie beauftragt.
2. **Signal f:** Passt „eigene Sicht“ als sechstes Signal, oder soll es nur ins Log?
3. **Rohdaten:** Die Ankündigungen und Köpfe des Zuhörers bleiben auf c2 unter `/var/lib/kaspa-pulse/wache/zcash-mainnet/roh/`. Soll ich sie nach dem Fenster auf `messung/zcash-mainnet` legen, wie beim Zuhörer auf GitHub?

## Was Ben tun muss, vor Do 05.11. 02:00 UTC

1. **Den PR prüfen und mergen.** Er ändert Workflow-, deploy- und c2-Dateien, deshalb kein Selbst-Merge.
2. **Auf c2:** `sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet`. Der erste Lauf hält an, weil das Credential noch fehlt, das ist erwartet. Er hat dann die neuen Schreibhilfen installiert.
3. **Auf GitHub:** `server-secrets` von Hand starten, mit **was = nur-wache**.
4. **Auf c2 noch einmal:** `sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet`, danach `journalctl -u upgrade-wache@zcash-mainnet -n 20`. Dort muss „ruht, fenster ab 2026-11-05 02:26:16 UTC“ stehen.

Die Schritte stehen auch in `deploy/c2/upgrade-wache/README.md`. Nach dem Fenster: `sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache-aus zcash-mainnet`.
