# Monero Stressnet, Zuhörer: Machbarkeit und Plan (6.11.2026)

Ben hat am 5.11. eine eigene gezählte Messung für das Monero-Stressnet beauftragt: je Block eine eigene Erste-Sicht-Zeit und die Köpfe, als Beitrag zu seraphis-migration/monero#495 (Stressnet Monitor). Zuerst die Klärung, gebaut wird erst nach Bens Ja. Frist für diesen Bericht ist Mo 9.11. 09:00 Berlin. Installiert ist nichts, gepostet ist nichts, in #495 steht kein Kommentar von mir.

<!-- discord -->
Monero Stressnet, Plan fertig. Empfehlung: Weg b, ein reiner P2P-Zuhörer über Levin auf GitHub Actions wie bei BCH, ohne Last auf c2. Vorher eine Probe von 15 min, ob das Stressnet noch lebt. Ben entscheidet Ja oder Nein. Bericht berichte/2026-11-06-monero-stressnet-plan.md
<!-- /discord -->

## Kurz

- **Empfehlung: Weg b.** Ein reiner P2P-Zuhörer über das Levin-Protokoll ohne volle Prüfung, als Kette von Läufen auf GitHub Actions, wie der Zuhörer im BCH Tempnet. Er gibt je Block die Erste-Sicht-Zeit je Peer und den vollen Kopf, weil jeder neue Block als „fluffy block“ mit Kopf ankommt. c2 trägt davon nichts.
- **Weg c** nur als tägliche Gegenprobe der Köpfe.
- **Weg a nicht jetzt.** Ein eigener monerod kostet auf c2 Platte, Bandbreite und vor allem CPU für die FCMP++-Prüfung. Belastbare Zahlen dazu gibt es nirgends, nicht einmal in #495, dessen Ziel genau diese Zahlen sind. Neben der Wache bis 9.11. ist das das falsche Risiko.
- **Laufzeit ist das größte Risiko.** Das Stressnet v3 läuft seit 5.10. „The run is expected to last several weeks, up to about a month“ (#495). Heute ist Tag 32. Ein Ende ist nirgends angekündigt, und am 26.10. kam noch v3.1 mit neuen Seeds. Deshalb zuerst eine Probe von 15 min, dann bauen.

## Was #495 ist und was dort fehlt

- **#495, „Stressnet Monitor / data collection“**, eröffnet am 30.9. von Fountain5405, Status „draft for feedback. No code yet.“
  - Ziel: „Find the minimum hardware needed to run a Monero node with FCMP++ under heavy network load.“
  - Gemessen werden soll vor allem die Annahmeverzögerung je Block („when this node accepted the block, minus when the first reference node did“), dazu Zeiten aus `--show-time-stats`, Ankunft von Transaktionen, Last je Rechner.
  - Ein P2P-Crawler soll Höhe, Spitze und kumulierte Schwierigkeit aus dem Handschlag aller erreichbaren Knoten lesen.
- **Was fehlt:** Erste-Sicht-Zeiten je Block von einem unabhängigen Zuhörer sind nicht im Entwurf. Ben hat am 28.10. in #495 gefragt, ob sie helfen würden. Eine Antwort steht dort nicht.
- **Kopfzeiten** fordert #495 nicht an. Sie stehen ohnehin in der Kette. Unsere eigene Zahl dazu sind die Abstände nach Kopfzeit aus selbst empfangenen Köpfen.
- **Weitere Beteiligte:** Rucknium bietet an, Messsoftware auf bis zu vier Knoten laufen zu lassen. Sein Werkzeug monerod-monitor liest nur den eigenen Knoten über RPC, ohne Ankunftszeiten von Blöcken. libetsdelay-code betreibt einen vollen v3-Knoten und misst alle 15 s Höhe, Peers, Pool und Größe der Datenbank. Zahlen dazu hat dort niemand veröffentlicht.

## Was das Stressnet technisch ist

Quelle ist der Quelltext von v0.19.0.0-beta.3.1 (Release vom 26.10.).

- **Netz:** Das Stressnet nutzt Ports und Netzwerk-ID des Testnets (P2P 28080, RPC 28081) und zweigt bei Höhe 3.102.800 ab (Fork 17, FCMP++, Carrot, RandomX v2). Fork 18 folgt bei 3.103.520.
- **Folge daraus:** Normale Testnet-Knoten sprechen dasselbe Protokoll mit derselben ID, laufen aber auf einer anderen Kette. Der Zuhörer behält nur Peers, deren `top_version` mindestens 17 ist und deren Kette den Stressnet-Block 3.102.800 enthält. Das ist dieselbe Regel wie beim BCH Tempnet (Abzweig 327.989).
- **Seeds:** 4 fest eingetragene Seed-Adressen für das Testnet, ohne DNS. Die Panne mit der DNS-Auflösung aus der NU7-Nacht kann hier nicht auftreten. Die Adressen liest der Zuhörer zur Laufzeit aus dem Quelltext, wie beim BCH Tempnet aus der öffentlichen Konfiguration. Ins Repo kommen sie nicht.
- **Blockzeit:** Das Ziel ist 120 s (`DIFFICULTY_TARGET_V2 120`).
- **Blockgröße:** Volle Belohnung bis 10 MB je Block (`CRYPTONOTE_BLOCK_GRANTED_FULL_REWARD_ZONE_V17`, „STRESSNET SPECIFIC“). Unter Last können die Blöcke also groß werden.
- **Neue Blöcke:** Sie kommen als `NOTIFY_NEW_FLUFFY_BLOCK` (2008). Darin stehen der Kopf (Version, Zeit, Vorgänger, Nonce), die Miner-Transaktion und die Hashes der Transaktionen, nicht die Transaktionen selbst.
- **Transaktionen:** Mit Tx Relay v2 (Unterstützungsflag 0x02) kündigen Peers neue Transaktionen nur als Hash an (`NOTIFY_TX_POOL_HASH`, 2011). Die Daten kommen erst auf Anfrage (2012). Ein Zuhörer, der nie anfragt, bekommt also nur 32 Byte je Transaktion und Peer.
- **Blockhash:** Keccak-256 über den serialisierten Kopf, den Inhalts-Hash und die Zahl der Transaktionen plus 1. Ab Fork 17 gehen zwei FCMP++-Felder (Zahl der Baumebenen, Wurzel) in den Inhalts-Hash ein. Das ist ohne monerod nachrechenbar. Den Arbeitsnachweis (RandomX v2) kann der Zuhörer nicht prüfen.

## Die drei Wege

| | a) eigener monerod, gepruned | b) P2P-Zuhörer über Levin | c) restricted RPC fremder Knoten |
|---|---|---|---|
| Erste Sicht je Block | ja, aber nur „bei unserem Knoten angenommen“, nach der FCMP++-Prüfung | **ja, je Peer, roh beim Eintreffen** | nein |
| Köpfe | ja, geprüft | ja, aus jedem fluffy block, Lücken über Kettenabfrage | ja, aber fremde Zahl |
| Prüfung | voll | Verkettung, Hash nachgerechnet, von mindestens zwei Peers bestätigt, **kein** Arbeitsnachweis | keine eigene |
| Ort | c2 | GitHub Actions, wie BCH und Zcash | GitHub Actions |
| Last auf c2 | hoch, unbekannt | keine | keine |
| Aufwand | Installation und Pflege, Ersteinlesen „several hours“ (Release) | etwa 1,5 bis 2 Tage | wenige Stunden |

**a) Eigener monerod.** Schätzung (computed), keine gezählte Zahl. In #495 und den Releases steht dazu keine einzige Zahl.
- **Platte:** Kette des Testnets bis 3,1 Mio. Blöcke plus Stressnet-Blöcke. Gepruned bleiben die letzten rund 5.500 Blöcke voll, das sind etwa 7,6 Tage. Bei 1 bis 5 MB je Block wären das 5 bis 28 GB nur für diesen Teil, dazu der geprunte Rest. Rechnung: 720 Blöcke je Tag mal 1 bis 5 MB ergibt 0,7 bis 3,6 GB je Tag. Ich setze 30 bis 60 GB an, mit großer Unsicherheit.
- **Bandbreite:** Jede Transaktion kommt einmal herein und geht an Peers weiter. Unter Last sind das grob 1 bis 4 GB je Tag herein, hinaus je nach Zahl der Peers ein Vielfaches. Begrenzbar mit `--limit-rate`.
- **CPU:** Die FCMP++-Prüfung ist der teure Teil. Die Kosten je Eingang unter Last sind gerade das, was #495 erst messen will. Ich habe keine belastbare Zahl. Fällt der Knoten hinter das Netz zurück, wird auch unsere Erste-Sicht-Zeit falsch.
- **RAM:** monerod selbst grob 1 bis 3 GB, dazu der Cache der Datenbank.
- **c2:** Was c2 an Kernen, RAM und Platte hat, steht nicht im Repo. Ohne diese Zahlen kann ich nicht sagen, ob c2 das neben der Wache trägt. Ich empfehle es auch mit den Zahlen nicht vor dem 9.11.

**b) P2P-Zuhörer.**
- **Was zu bauen ist:**
  - Levin-Rahmen und das Binärformat „portable storage“ von epee, zum Lesen und Schreiben, rund 300 Zeilen
  - Handschlag (1001), Antworten auf Timed Sync (1002) und Ping (1003), damit uns die Peers nicht trennen
  - Empfang von fluffy blocks (2008) und Hash-Ankündigungen (2011)
  - Kettenabfrage (2006 und 2007) zum Filtern der Peers und für die Bestätigung durch einen zweiten Peer
- **Gleiche Felder und Regeln wie beim BCH Tempnet:** `first_seen` je Block und Peer, Peers als `peer_N`, keine IPs, keine Hostnamen, 64-hex nur für Block- und Transaktions-Hashes. Rohdaten auf `messung/monero-stressnet`, Auswertung täglich.
- **Bandbreite:** klein. Köpfe, Hash-Listen der Blöcke, dazu 32 Byte je angekündigter Transaktion und Peer. Bei 20 Peers und 100.000 Transaktionen am Tag sind das rund 64 MB.
- **Risiken:**
  1. Monero-Knoten könnten einen Peer trennen, der nie Transaktionen anfragt oder weiterleitet. Das zeigt erst die Probe.
  2. Im Handschlag müssen wir eine Höhe und eine Spitze angeben. Ich nehme die echte: Höhe 0 und den Genesis-Block, also wie ein Knoten, der noch synchronisiert. Ob Knoten einem solchen Peer neue Blöcke schicken, prüft die Probe ebenfalls. Wenn nicht, ist Plan B, die zuletzt gesehene Spitze als eigene anzugeben. Das würde ich im Bericht ausweisen.
  3. Den Arbeitsnachweis prüfen wir nicht, anders als bei BCH und Zcash. Wir nennen das in jeder Zahl („verkettet, von zwei Peers bestätigt, Arbeitsnachweis nicht geprüft“).
  4. Ändert sich das Format der Miner-Transaktion mit Carrot, scheitert die Hash-Rechnung. Dann bleibt der Hash, den mindestens zwei Peers in ihrer Kette nennen. Die Probe zeigt, ob unsere Rechnung passt.

**c) Restricted RPC fremder Knoten.** Nur als Gegenprobe: einmal am Tag `get_block_headers_range` über die Fenster der Auswertung, Hash und Zeit gegen unsere Köpfe vergleichen. Adressen solcher Knoten kämen nur aus einem GitHub Secret, nie ins Repo. Fehlt ein Kopf bei uns, darf er aus c nur gekennzeichnet einfließen, nie als gezählt.

## Lohnt sich der Aufbau?

- **Ja, wenn das Stressnet noch mindestens 10 Tage läuft.** Bau 1,5 bis 2 Tage, dann eine Woche Daten für die erste Wochenzahl.
- **Belege:**
  - Für ein Weiterlaufen: v3.1 am 26.10. mit neuen Seeds und zwei DoS-Fixes, kein Ende angekündigt.
  - Dagegen: „up to about a month“, gezählt ab 5.10.
- **Vorschlag:** Erst eine Probe von 15 min. Sie zeigt, ob Stressnet-Peers erreichbar sind, ob die Spitze wächst und ob uns die Peers fluffy blocks schicken und verbunden lassen. Danach erst der Dauerlauf. Läuft in der Probe nichts, bauen wir nicht.
- **Von hier aus nicht prüfbar:** Diese Sitzung bekommt keine direkte TCP-Verbindung. An allen 4 Seeds kam es zum Timeout. Das liegt an dieser Umgebung, nicht am Stressnet. Die Probe muss auf GitHub Actions laufen.

## Die erste Wochenzahl (nach Bens Ja)

- **Blockabstände nach Kopfzeit**, gezählt, gegen 120 s (computed):
  - Median, gezählt gegen computed 83,2 s (120 mal ln 2)
  - p90 gegen 276,3 s (120 mal ln 10)
  - p99 gegen 552,6 s (120 mal ln 100)
  - Anteil über 10 min gegen 0,67 % (e hoch minus 5)
- **Hinweis zu Kopfzeiten:** Bei Monero setzt der Miner die Zeit. Erlaubt ist alles über dem Median der letzten 60 Blöcke und bis 2 h in der Zukunft. Negative Abstände sind also möglich. Sie werden gezählt und ausgewiesen, nicht entfernt.
- **Spread der Ersten Sicht:** je Block die Zeit zwischen dem ersten und dem letzten Peer, der ihn uns angekündigt hat. Dazu Median und p90 über die Woche und die Zahl der Peers je Block. Ein Zuhörer an einem Ort, die Zeit enthält also auch den Weg zu uns.

## Was ich nach einem Ja baue

1. **Probe (15 min):** `scripts/monero/stressnet_lauscher.py --probe` mit Handschlag, Filter auf Fork 17, ein fluffy block und eine Kettenabfrage. Ausgabe nur Zahlen. Dazu ein Workflow `monero-stressnet-lauscher.yml`, der nur auf `messung/monero-stressnet` läuft. Den prüfe ich, du mergst ihn.
2. **Dauerlauf:** eine Kette von Läufen zu 330 min wie beim BCH Tempnet. Rohdaten je Lauf auf `messung/monero-stressnet`, Auswertung täglich.
3. **Gegenprobe c:** täglich, nur wenn du einen Knoten als Secret hinterlegst.
4. **Erste Wochenzahl** sieben Tage nach dem Start des Dauerlaufs, als Bericht. Den Text für #495 schreibt die Haupt-Sitzung.

## Offene Fragen an Ben

1. **Ja oder Nein zu Weg b**, zuerst mit der Probe von 15 min?
2. **Laufzeit:** Weißt du aus dem Matrix-Raum des Stressnets, wie lange v3 noch läuft? Mir ist nur „several weeks, up to about a month“ aus #495 bekannt.
3. **Workflows:** Die Workflows für Probe und Dauerlauf laufen nur auf `messung/monero-stressnet`, wie `bch-chipnet.yml`. Reicht dir das als Prüfung vor dem Lauf, oder willst du sie vorher auf main mergen?
4. **Gegenprobe c:** Willst du dafür einen öffentlichen Stressnet-RPC-Knoten als GitHub Secret hinterlegen? Ohne ihn fällt c weg.
5. **Nur falls du später doch a willst:** Die Ausgabe von `nproc`, `free -g` und `df -h /` auf c2, ohne Hostnamen, damit ich die Last gegen echte Zahlen rechnen kann.

## Was Ben tun muss

1. Ja oder Nein zu Weg b sagen. Eine Frist gibt es nicht. Je später das Ja kommt, desto weniger Stressnet-Tage bleiben für die Messung.
