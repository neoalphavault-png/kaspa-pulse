# Voller Knoten je Netz und BCH-Tempnet-Abschluss (Ben 9.11.2026, Frist Fr 13.11. 15:00 Berlin)

**Stand 9.11. abends.** Teil A ist fertig. Du hast entschieden: kein Server jetzt, Zebra erst nach Bewilligung durch ZCG, BCHN geprunt auf c2 nach dem Tempnet-Ende (PR #300). Teil C läuft. Diese Datei wird bis Freitag ergänzt.

<!-- discord -->
Voller Knoten, Teil A fertig: Heute läuft kein eigener Zebra-, Zakura- oder BCHN-Knoten, weder auf c2 noch woanders. c2 (CX23, 2 vCPU, 4 GB, 40 GB) ist dafür zu klein. Empfehlung ist Variante 2, ein eigener dedizierter Server mit 1 TB NVMe für Zebra und BCHN, rund 46 EUR im Monat laut Drittquellen. Du entscheidest. Für die Messwerte von c2 bitte die drei Befehle aus dem Bericht ausführen. Bericht berichte/2026-11-13-voll-knoten.md
<!-- /discord -->

## Teil A, Bestandsaufnahme

### 1. Was heute läuft

**Auf c2** (Hetzner CX23, laut `deploy/c2/EINRICHTUNG.md`). Laut Hetzner hat ein CX23 2 vCPU (geteilt), 4 GB RAM und 40 GB Platte.
- `upgrade-wache@zcash-mainnet` mit eigenem Zuhörer für Zcash, Python. Das NU7-Fenster ist seit 9.11. 03:34 UTC zu, der Zuhörer ist beendet.
- `entity-x-alarm` und `entity-x-sync`
- die Taktgeber-Timer (`deploy/c2/taktgeber/`), die Posts und Grafiken anstoßen

**Auf GitHub-Runnern**, nicht auf c2:
- Header-Clients für Zcash (`zcash-mainnet.yml`, täglich) und BCH (`bch-tempnet.yml`)
- Zuhörer für das BCH Tempnet (`bch-tempnet-lauscher.yml`), den Zcash Mainnet (`zcash-mainnet-lauscher.yml`) und das Monero Stressnet

**Eigene Knoten: keine.**
- Kein Zebra, kein Zakura und kein BCHN läuft bei uns, weder auf c2 noch auf einem Runner.
- Header-Clients, Zuhörer und Wache verbinden sich mit fremden Knoten und prüfen Köpfe selbst, nämlich Verkettung, Arbeit und Checkpoints, dazu Gegenproben bei zwei Peers.
- Transaktionen und Blockinhalte prüft niemand bei uns. Genau das ist der Einwand aus der Ablehnung von Antrag #444.

**Messung auf c2 (Ben, 9.11.):**
- 2 vCPU, 3,7 GiB RAM, davon 3,3 GiB frei, kein Swap
- Platte 38 GB, davon 34 GB frei
- Last 0,15
- laufend nur `entity-x-alarm`
- Seit etwa 17:30 läuft zusätzlich der `bch-lauscher` (PR #298). `wache-aus zcash-mainnet` ist erledigt.

### 2. Bedarf je Knoten

| | Zebra, Zcash Mainnet | BCHN, BCH Mainnet, voll | BCHN, BCH Mainnet, geprunt |
|---|---|---|---|
| CPU | 4 Kerne empfohlen, 2 mindestens | ohne offizielle Angabe, 4 Kerne genügen nach Erfahrungswerten | wie voll |
| RAM | 16 GB empfohlen, 4 GB mindestens | Standard-Datenbankcache 450 MiB, für die Erstsynchronisation mehr sinnvoll | wie voll |
| Speicher | etwa 300 GB, wächst | rund 250 GB, wächst (Zahl aus einer Drittquelle, Datum unklar) | 550 MiB Blockdateien als Untergrenze, dazu der UTXO-Bestand von einigen GB |
| Erstsynchronisation | „takes days“ von der Genesis an | keine belastbare Quelle gefunden, wir messen beim Aufsetzen | wie voll, denn jeder Block wird geladen und geprüft |
| Ports | 8233 ausgehend nötig, eingehend optional | 8333 ausgehend, eingehend abschaltbar (`listen=0`) | wie voll |

**Quellen:**
- Zebra-Buch, `book/src/user/requirements.md` und `snapshots.md` im Repo ZcashFoundation/zebra, Stand 9.11.
- BCHN-Quellcode auf GitLab:
  - `src/init.cpp`: `-prune`, nicht mit `-txindex` vereinbar
  - `src/validation.h`: `MIN_DISK_SPACE_FOR_BLOCK_FILES` 550 MiB, `MIN_BLOCKS_TO_KEEP` 288
  - `src/txdb.h`: `nDefaultDbCache` 450
- Größe der BCH-Kette: eine Statusseite eines BCHN-Knotens mit 246 GB bei Block 956.292, über die Websuche gefunden. Die Seite selbst ist aus der Sitzung nicht erreichbar, das Datum ist unklar.

**Ein geprunter BCHN validiert voll.** Er lädt und prüft jeden Block und löscht danach nur alte Blockdateien. Für unsere Gegenprobe (Hash je Höhe) reicht er, solange wir nur Höhen innerhalb der behaltenen Blöcke abfragen oder die Hashes aus dem Index holen. Der Index der Blockköpfe bleibt auch geprunt vollständig.

**Zebra-Snapshots** würden die Synchronisation auf Stunden kürzen. Das Zebra-Buch sagt aber selbst, dass ein Snapshot nur so vertrauenswürdig ist wie sein Anbieter, und die Manifeste sind unsigniert. Weil es uns gerade um eigene Prüfung geht, empfehle ich die Synchronisation von der Genesis an.

### 3. Varianten und Monatskosten

Die Preise kommen aus Drittquellen (Preisvergleiche, Stand Juni bis September 2026). hetzner.com ist aus der Cloud-Sitzung nicht erreichbar. Bitte vor der Bestellung auf hetzner.com prüfen. Alle Werte netto in EUR je Monat.

| | Variante 1, c2 aufrüsten | Variante 2, eigener Server (Empfehlung) | Variante 3, zweiter Cloud-Server |
|---|---|---|---|
| Maschine | c2 von CX23 auf CX43 (8 vCPU geteilt, 16 GB, 160 GB) | dedizierter Server aus der Serverbörse, Klasse AX42 (8 Kerne, 64 GB, 1 TB NVMe) | CPX42 (8 vCPU, 16 GB, 320 GB) |
| Zusatzspeicher | Volume 350 GB für Zebra und BCHN geprunt | keiner | Volume 300 GB |
| Kosten | etwa 16 + 20 = 36 laut Drittquellen, also rund 30 mehr als heute | AX42 99,00 laut Bestellseite (12.11.), dazu 49,00 Einrichtung; aus der Serverbörse laut Drittquellen etwa 46 | etwa 69 + 17 = 86 laut Drittquellen |
| BCHN | nur geprunt | voll | geprunt oder knapp voll |
| Plattenzugriff | Volume über das Netz, langsam für RocksDB und LevelDB | lokale NVMe, schnell | Volume über das Netz |
| Risiko | Knoten teilen sich c2 mit Wache und Taktgeber. Eine volle Platte oder Speicherdruck trifft die Posts. Verkleinern geht nicht mehr. | eine Maschine mehr zu pflegen, keine Hetzner-Cloud-Firewall, die Firewall läuft auf dem Server | teuer seit der Preiserhöhung im Juni |

**Empfehlung: Variante 2.**
- Beide Knoten passen voll ungeprunt auf 1 TB, mit Platz für das Wachstum der nächsten Jahre.
- Mit lokaler NVMe dauert die Erstsynchronisation am kürzesten, und 64 GB RAM reichen für beide mit großem Cache.
- c2 bleibt, wie es ist. Ein Knoten, der die Platte füllt, kann dann keine Posts aufhalten.
- Für den ZCG-Antrag ist ein eigener Server sauberer zu beschreiben als Knoten neben Social-Media-Timern.

**Wenn es billiger sein soll:** Variante 1 mit BCHN geprunt. Zebra auf einem Netz-Volume braucht für die Erstsynchronisation deutlich länger. Den Faktor kann ich nicht belegen.

## Deine Entscheidung (9.11.)

Keine neuen Fixkosten, bevor ein Auftrag da ist.

### Kostenposten für den ZCG-Antrag, Zebra-Vollknoten

| | |
|---|---|
| Server-Klasse | dedizierter Server, 8 Kerne, 64 GB RAM, 1 TB NVMe (Hetzner AX42 oder gleichwertig aus der Serverbörse) |
| Monatspreis netto | 99,00 EUR laut Hetzner-Bestellseite am 12.11.2026 (Ben). Für 12 Monate sind das 1.188,00 EUR. Die Serverbörse lag laut Drittquellen bei etwa 46 EUR, ist aber nicht bestellbar zugesichert. |
| Einrichtung | 49,00 EUR netto, einmalig, laut Bestellseite am 12.11.2026. Für den Antrag zusammen 1.237,00 EUR im ersten Jahr. |
| Erstsynchronisation | „takes days“ laut Zebra-Buch, von der Genesis an, ohne fremden Snapshot. Im Plan 7 Tage. |
| Betrieb | nur ausgehende Verbindungen. Port 8233 eingehend erst mit einer Firewall-Regel. |
| Start | nach der Bewilligung |

**Berichtigt am 12.11.:** Hier stand vorher 57,30 EUR im Monat aus Drittquellen. Laut Hetzner-Bestellseite am 12.11.2026 kostet der AX42 99,00 EUR im Monat plus 49,00 EUR Einrichtung, netto (Ben). Die Drittquellen waren veraltet. Die Zahlen für die Serverbörse (37 bis 46 EUR) stammen weiter aus Drittquellen und sind nicht geprüft.

Auf demselben Server kann später auch ein ungeprunter BCHN laufen. Für den ZCG-Antrag zählt nur Zebra.

### BCHN geprunt auf c2

Vorbereitet als PR #300 (c2-Dateien, du mergst):
- `bitcoin.conf` mit `prune=4000`, `dbcache=300`, `listen=0`, RPC nur lokal und `logips=0`
- `bchn.service` mit `MemoryMax=1200M`, `CPUQuota=100%`, Nice 10 und IO im Leerlauf. Die Unit verweigert den Start vor dem 15.11. um 12:00 UTC.
- `setup.sh bchn`, `bchn-stand` und `bchn-aus`
- Installiert wird aus dem signierten PPA von Bitcoin Cash Node, mit geprüftem Fingerabdruck.

Erwartet: etwa 4 GB Blockdateien und einige GB UTXO-Bestand, die Erstsynchronisation dauert einige Tage bis zwei Wochen. Den Namen des Binärpakets (`bitcoind`) konnte ich nicht nachlesen. `setup.sh` bricht ab, wenn das installierte Programm nicht BCHN ist.

**Gegenprobe gegen BCHN und Methodensatz (Punkte 5 und 6):** Sobald BCHN synchron ist, prüft ein Timer auf c2 jede gezählte BCH-Höhe gegen `getblockhash`. Danach kommt der Satz in pulsehawk/methods, mit Datum, und nur für BCH. Für Zcash gilt er erst mit dem Zebra-Knoten.

## Teil C, BCH-Tempnet-Abschluss

**Stand 9.11. mittags.** Der Abschlussbericht für das Forum kommt am Fr 13.11. vormittags mit den Daten bis dahin. Am Sa 14.11. trage ich die Zahlen bis dahin nach, also vor dem Sonntag. Die letzten Stunden bis zum Tempnet-Ende am 15.11. um 12:00 UTC fehlen dann offen benannt.

**8. Stale nach Last.** Das neue `scripts/bch/tempnet_abschluss.py` (PR #299) zählt nach zwei Regeln, beide werden im Forum genannt. Zwischenstand mit den Daten bis 9.11. 08:25 UTC, 340 abgedeckte Stunden:

| Regel | Hochlast | ruhig |
|---|---|---|
| Blocklast, Stunden ab 2 × Median (116 Kettenblöcke je Stunde) | 770 stale bei 2.845 Kettenblöcken, 21,3 %, 8 Stunden | 141 bei 17.819, 0,79 %, 332 Stunden |
| Transaktionslast, Stunden ab dem 90. Perzentil (1.633 Transaktionen) | 20 bei 1.901, 1,04 %, 34 Stunden | 891 bei 18.763, 4,53 %, 306 Stunden |

Die Stale-Blöcke häufen sich in Stunden mit sehr vielen Blöcken, nicht in Stunden mit vielen Transaktionen. Welche Regel rufitnes meinte, weiß ich nicht. Deshalb zeigen wir beide.

**9. Uhr.** Seit dem 7.11. um 15:02 UTC schreibt jeder Lauf den Versatz aus `chronyc tracking` mit. Das sind bisher 8 von 66 Läufen, der größte Betrag war 14,7 µs. Die 58 Läufe davor haben keinen Wert, das steht offen im Bericht. Ist die Uhr beim Start noch nicht synchron, ist der erste Wert wenig aussagekräftig. Das zeigt `synchron_beim_start`.

**Lücken.** 25.10. 7 min beim Start, 26.10. 1,6 min, 3.11. 13:59 bis 4.11. 10:08 UTC (20 h, ein Lauf ohne gesicherte Daten).

**10. Zweiter Messpunkt.** Machbar bis zum 15.11., wenn du PR #298 bald mergst und auf c2 `sudo ./setup.sh bch-lauscher` ausführst. Dann misst derselbe Zuhörer von c2 aus, also über einen anderen Netzwerkpfad als die GitHub-Runner, bis zum Tempnet-Ende. Gerechnet ab Mittwoch wären das gut drei Tage. Ohne Merge steht im Bericht, dass der zweite Messpunkt fehlt und erst bei einer nächsten Messung kommt.

## Was Ben tun muss

1. **PR #300 mergen**, dann auf c2 `sudo ./setup.sh bchn`. Nach dem 15.11. um 12:00 UTC kommt `sudo systemctl start bchn`.
2. **Preise** für den ZCG-Antrag auf hetzner.com prüfen.

## Offene Fragen an Ben

Keine.
