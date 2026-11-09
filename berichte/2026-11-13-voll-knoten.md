# Voller Knoten je Netz und BCH-Tempnet-Abschluss (Ben 9.11.2026, Frist Fr 13.11. 15:00 Berlin)

**Stand 9.11. mittags: Teil A ist fertig, Teil B wartet auf deine Wahl der Variante, Teil C läuft.** Diese Datei wird bis Freitag ergänzt.

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

**Was ich nicht messen kann:** CPU-Last, belegten RAM und freien Speicher auf c2. Ich habe keinen Zugang zu c2, und das gehört nicht in die Cloud-Sitzung. Bitte auf c2 ausführen und mir die Ausgabe geben. Sie enthält weder IP noch Hostnamen.

```
nproc; free -h; df -h /
uptime
systemctl list-units --type=service --state=running --no-legend | awk '{print $1}' | grep -E 'wache|entity|takt'
```

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
| Kosten laut Drittquellen | etwa 16 + 20 = 36, also rund 30 mehr als heute | etwa 46, dazu einmalige Einrichtungsgebühr | etwa 69 + 17 = 86 |
| BCHN | nur geprunt | voll | geprunt oder knapp voll |
| Plattenzugriff | Volume über das Netz, langsam für RocksDB und LevelDB | lokale NVMe, schnell | Volume über das Netz |
| Risiko | Knoten teilen sich c2 mit Wache und Taktgeber. Eine volle Platte oder Speicherdruck trifft die Posts. Verkleinern geht nicht mehr. | eine Maschine mehr zu pflegen, keine Hetzner-Cloud-Firewall, die Firewall läuft auf dem Server | teuer seit der Preiserhöhung im Juni |

**Empfehlung: Variante 2.**
- Beide Knoten passen voll ungeprunt auf 1 TB, mit Platz für das Wachstum der nächsten Jahre.
- Mit lokaler NVMe dauert die Erstsynchronisation am kürzesten, und 64 GB RAM reichen für beide mit großem Cache.
- c2 bleibt, wie es ist. Ein Knoten, der die Platte füllt, kann dann keine Posts aufhalten.
- Für den ZCG-Antrag ist ein eigener Server sauberer zu beschreiben als Knoten neben Social-Media-Timern.

**Wenn es billiger sein soll:** Variante 1 mit BCHN geprunt. Zebra auf einem Netz-Volume braucht für die Erstsynchronisation deutlich länger. Den Faktor kann ich nicht belegen.

## Teil B

Wartet auf deine Wahl. Vorab zwei Punkte zur Gegenprobe:
- **Wo die Prüfung läuft.** Die Header-Clients laufen auf GitHub-Runnern, die Knoten auf unserem Server. Eine Freigabe der RPC-Schnittstelle nach außen schlage ich nicht vor. Mein Vorschlag ist ein Timer auf dem Knotenserver. Er liest die gezählten Köpfe aus dem Repo, fragt je Höhe den Hash beim eigenen Knoten ab und schreibt die Abweichungen als CSV zurück auf den Datenbranch, wie heute `sync.sh` der Wache.
- **Ab wann es gilt.** Der Satz „every header checked against our own fully validating node“ kommt erst in pulsehawk/methods, wenn die Knoten synchron sind und der erste Prüflauf ohne Abweichung durch ist. Das Datum steht dann dabei.

## Teil C, BCH-Tempnet-Abschluss

Läuft. Stand und Plan folgen hier bis Freitag.
