# Upgrade-Wache: Rohwerte für den PulseHawk Upgrade Report v1 (2.11.2026)

Ben hat am 2.11. entschieden, dass die NU7-Messung der erste „PulseHawk Upgrade Report“ nach der Spezifikation v1 wird. Die Wache und ein neues Skript liefern dafür die Rohwerte M1 bis M7. Jede Zeile ist als counted, source oder computed gekennzeichnet und trägt ein Fenster in UTC und n. Die Werte stehen in einer CSV mit sha256.

## Was gemacht wurde

**Die Änderungen sind auf zwei PRs verteilt.**

| PR | Inhalt | Merge |
|---|---|---|
| `wache/report-v1` | `scripts/wache/` und dieser Bericht | ich, nach den Regeln vom 26.10. |
| `wache/report-v1-c2` | `deploy/c2/upgrade-wache/` (`sync.sh`, Unit-Kommentar, README) | Ben |

**Deine Antworten, umgesetzt:**
1. **Blockpause ab NU7:**
   - Ab der Aktivierungshöhe gilt Hinweis ab 300 s und Alarm ab 600 s.
   - Vorher bleibt es bei 600 und 1.200 s.
   - Umgeschaltet wird wie bei Signal e, sobald unsere Spitze die Aktivierungshöhe erreicht. Dafür steht in der Konfiguration ein neuer Block `blockpause.nach_aktivierung`.
   - In der Simulation zeigt das Log nach der Aktivierung die Schwellen 300 und 600.
2. **Signal f** (eigene Sicht) bleibt ein Hinweis, wie bisher.
3. **Rohdaten:**
   - Nach dem Fenster bringt `sync.sh` sie auf `messung/zcash-mainnet`, in den Ordner `wache/roh/`. Ausgelöst wird das durch die Zeile `fenster_zu` im Log.
   - Das neue Skript `scripts/wache/roh_export.py` schreibt die Dateien. Es nimmt nur Daten aus dem Fenster und schreibt gz ohne Zeitstempel: gleiche Daten ergeben gleiche Bytes, also keinen neuen Commit.
   - Dazu kommt eine Datei `SHA256SUMS`.
   - Findet das Skript etwas, das wie eine IPv4- oder IPv6-Adresse aussieht, bricht es ab und schreibt nichts. Getestet mit einer eingeschleusten Testadresse.
   - Vor dem Push läuft wie bisher der Secret-Scan.
   - Nach dem Fenster beendet die Wache den Zuhörer, damit die Rohdaten nicht weiterwachsen.

**Neu für den Report v1:**
- **Peer-Probe (M5):**
  - Zeitpunkte jetzt 0, 6, 24 und 72 h nach der gesehenen Aktivierung.
  - Jede Probe speichert n, die Zahl unter dem Mindestprotokoll, den Anteil, die Höhe und die Verteilung der Protokollversionen.
  - `fenster.nach_h` steht jetzt auf 73 statt 72. Sonst wäre das Fenster genau zur Probe +72 h zu, und sie liefe nicht mehr. Der Report wertet trotzdem genau 72 h aus.
- **Software der Peers:** Die Quelle schreibt sie laufend in `roh/<lauf>-peers.json`. Darin stehen nur unsere Nummer je Peer (zum Beispiel `zebra-3`), Kennung, Protokoll, gemeldete Höhe und die Zeiten. Adressen stehen dort nicht.
- **Report-Skript `scripts/wache/report_v1.py`:**
  - Schreibt die CSV `report-v1-<kette>-<upgrade>.csv`.
  - Dazu `.csv.sha256` im Format von `sha256sum`.
  - Dazu `-eingang.json` mit der sha256 jeder Eingangsdatei.

## Die CSV

**Spalten:** `metrik, kennzahl, wert, einheit, art, fenster_von_utc, fenster_bis_utc, n, quelle, anmerkung`

**Fenster:** t_akt ist die Kopfzeit des Blocks 3.543.405.
- „vor“ umfasst die Blöcke unter der Aktivierungshöhe ab t_akt − 24 h.
- „nach“ umfasst die Blöcke ab der Aktivierungshöhe bis t_akt + 72 h.
- Abgegrenzt wird über die Höhe, weil Kopfzeiten nicht steigen müssen.

| Metrik | Zeilen | Art | Eingang |
|---|---|---|---|
| M1 | p50, p90, p99 und Mittel der Abstände, je vor und nach; Ziel 75 s und 25 s; dazu Modellwerte bei exponentiellen Abständen (ln2, ln10, ln100 × Ziel); Zahl negativer Abstände | counted, source (Ziel), computed (Modell) | eigene Köpfe `koepfe.csv.gz` |
| M2 | längste Lücke mit Block und Zeit; Zahl der Abstände über 5 × Ziel; Modell n × e⁻⁵ | counted, computed | eigene Köpfe |
| M3 | Zahl der Reorgs (jeder Wechsel unserer Spitze, auch Tiefe 1), größte Tiefe | counted | `wache-log.csv` |
| M4 | Gesamtdauer und längste Episode des Signals Kettenspaltung, n = Episoden | counted | `wache-log.csv` |
| M5 | Anteil unter dem Mindestprotokoll 170190 bei 0, +6, +24 und +72 h, mit n und Versionen | counted | `zustand.json` |
| M6 | Zeit bis stabil und Anteil der Zeit im Band, in drei Varianten (siehe unten) | counted, computed (Modell) | eigene Köpfe |
| M7 | Aktivierungshöhe (source, ZIP 259 und Zebra 7.0.0), Kopfzeit des ersten Blocks, erste Sicht bei uns, Schätzung 02:39:52 UTC mit Band, Abstand Kopfzeit minus Schätzung, im Band ja oder nein | source, counted, computed | Köpfe, Ereignisse, Konfiguration |

**Der Ablauf nach dem Fenster:**
1. Die Rohdaten kommen über `sync.sh` auf den Datenbranch.
2. Der tägliche Lauf von `zcash-mainnet.yml` schreibt die eigenen Köpfe bis über t_akt + 72 h nach `data/zcash-mainnet/koepfe.csv.gz`.
3. Dann laufen:
   ```
   python3 scripts/wache/report_v1.py --kette scripts/wache/ketten/zcash-mainnet.json \
       --koepfe data/zcash-mainnet/koepfe.csv.gz --roh wache/roh --aus wache/report
   ```
4. Das Ergebnis landet in `wache/report/` auf `messung/zcash-mainnet`.

## Tests

1. **Report gegen die echte NU7-Aktivierung im Testnet:**
   - Datengrundlage: Block 4.465.026, Kopfzeit 4.10.2026 18:21:45 UTC, eigene Köpfe von `messung/zcash-nu7`.
   - Die CSV hat 45 Datenzeilen, `sha256sum -c` ist OK.
   - Beispiele nach der Aktivierung: 10.695 Abstände, p50 18 s, p90 51 s, p99 112 s, Mittel 24,24 s, längste Lücke 434 s, 60 Abstände über 125 s (Modell 72,1).
   - Vor der Aktivierung sind die Testnet-Werte wegen der Mindestschwierigkeit unbrauchbar (p50 2 s, 438 negative Abstände). Für den Mainnet-Report stört das nicht.
2. **Rohdaten-Export und M3 bis M5, M7 mit Rohdaten:**
   - Aufzeichnung des Zuhörers vom 17.10. im Testnet, dazu das Log des Simulations-Szenarios „reorg“.
   - Ergebnis: Reorgs werden gezählt (Tiefe 2), die Probe kommt mit n = 14, und die erste Sicht des Aktivierungsblocks lag 16 s nach seiner Kopfzeit.
3. **`sync.sh` gegen ein lokales Test-Repo:**
   - Der erste Lauf bringt nur das Log.
   - Nach der Zeile `fenster_zu` kommen Log und Rohdaten.
   - Der dritte Lauf meldet „log unveraendert“.
   - Der Secret-Scan ist jedes Mal sauber.
   - **Dieser Test war fehlerhaft**, siehe den Abschnitt „Nachtrag 3.11.“: Die Zeile `fenster_zu` hatte ich mit `echo` angehängt, also mit `\n`. Die Wache selbst schreibt `\r\n`.
4. **Simulation der Wache:** Alle 6 Szenarien sind weiter ok.

## Nachtrag 3.11.: Fensterende in `sync.sh` (PR #242)

**Fehler, gefunden von Ben:** `wache_kern.log` schreibt mit `csv.writer` und `newline=""`, also mit `\r\n` am Zeilenende. `grep -q ',fenster_zu$'` trifft `fenster_zu\r` nicht. Damit wären die Rohdaten nie ins Repo gekommen, auch nicht bei `setup.sh wache-aus`. Mein erster Test hat das nicht gezeigt, weil ich die Zeile von Hand mit `\n` angehängt hatte.

**Geändert in `deploy/c2/upgrade-wache/sync.sh`:**
1. Die Erkennung entfernt vorher die `\r`: `tr -d '\r' < "$LOG" | grep -q ',fenster_zu$'`.
2. Bricht `roh_export.py` ab, etwa bei einem Adressfund oder einem anderen Fehler, geht das Log trotzdem ins Repo. Danach endet das Skript mit `exit 1` und schreibt „fehler: rohdaten nicht exportiert“ nach stderr. So zeigen `systemctl status upgrade-wache-sync@zcash-mainnet` und `journalctl` den Fehler. Das gilt auch, wenn das Log unverändert ist.

**Neuer Test mit einem Log, das die Wache selbst schreibt:**
- Alle Logzeilen kommen aus `Kern.log`: `start`, `aktivierung_gesehen` und nach dem Fenster `fenster_zu`, wie in `wache.py`. Nur Lauf 4 hängt zusätzlich eine `lauf`-Zeile mit `printf` an, ebenfalls mit `\r\n`.
- Die Rohdaten stammen aus der Testnet-Aufzeichnung vom 17.10.
- Gepusht wird in ein lokales Test-Repo, ohne Netz.

So endet die letzte Logzeile (`od -c`):

```
   e   n   s   t   e   r   _   z   u  \r  \n
```

**Mit dem alten `sync.sh` (`b191618`):** Lauf 2 nach `fenster_zu` meldet nur „log gepusht, 4 zeilen“, ohne Rohdaten. Der Fehler ist damit nachgestellt.

**Mit dem neuen `sync.sh`:**

```
== lauf 1, fenster offen
secret-scan: alle dateien im checkout, nichts gefunden
log gepusht, 3 zeilen
exit 0
== lauf 2, nach fenster_zu
secret-scan: alle dateien im checkout, nichts gefunden
log gepusht, 4 zeilen, rohdaten in wache/roh
exit 0
== lauf 3, unveraendert
log unveraendert
exit 0
== adresse in peers.json eingeschleust
abbruch: adresse in peers.json, nichts geschrieben
rohdaten nicht exportiert, nur das log
secret-scan: alle dateien im checkout, nichts gefunden
log gepusht, 5 zeilen
fehler: rohdaten nicht exportiert
exit 1
== lauf 5, log unveraendert, export weiter fehlerhaft
abbruch: adresse in peers.json, nichts geschrieben
rohdaten nicht exportiert, nur das log
log unveraendert
fehler: rohdaten nicht exportiert
exit 1
== commits im test-repo
upgrade-wache testkette: log [bot]
upgrade-wache testkette: log und rohdaten [bot]
upgrade-wache testkette: log [bot]
init
== dateien
README
wache/roh/SHA256SUMS
wache/roh/ereignisse.jsonl.gz
wache/roh/koepfe.jsonl.gz
wache/roh/peers.json
wache/roh/wache-log.csv
wache/roh/zustand.json
wache/wache-log.csv
```

**Was der Test zeigt:**
- Mit Adressfund kommt das Log ins Repo, die Rohdaten nicht. Eingeschleust war im Test eine Adresse aus dem Bereich, der für Dokumentation reserviert ist; der Wert steht hier bewusst nicht.
- Was zuvor sauber exportiert wurde, bleibt im Repo stehen.

**Commits auf `wache/report-v1-c2`:**
- `8311f2f`: die Änderung an `sync.sh`.
- Danach habe ich `main` hineingemergt (`c1f7057`), weil dieser Bericht erst auf `main` liegt.
- Den neuen Kopf nenne ich in der Meldung an Ben, weil ein Commit seinen eigenen Hash nicht enthalten kann.

## M6: Die Definition trifft eine gesunde Kette fast nie

„Gleitender 1-h-p50 innerhalb 10 % des Ziels“ ist bei Proof of Work fast nie erfüllt. Der Median exponentieller Abstände liegt bei ln2 × Ziel, bei 25 s also 17,3 s und nicht 25 s.

**Simulation:** Ich habe eine ideale Kette mit 25 s simuliert, 72 h lang (computed). Gezählt ist der Anteil der Zeit im Band.

| Variante | Anteil im Band |
|---|---:|
| 1-h-p50 gegen 25 s ± 10 % (Spezifikation wörtlich) | 1,7 % |
| 1-h-p50 gegen ln2 × 25 s = 17,3 s ± 10 % | 64,4 % |
| 1-h-Mittel gegen 25 s ± 10 % | 77,2 % |
| 1-h-Mittel gegen 25 s ± 20 % | 97,5 % |
| 3-h-Mittel gegen 25 s ± 10 % | 90,0 % |
| 3-h-p50 gegen 17,3 s ± 10 % | 83,6 % |

**Gegenprobe mit echten Daten:** Das Zcash-Mainnet ab Block 3.520.002, mit 75 s als „Ziel nach“, ist eine gesunde Kette (Mittel 75,2 s). Nach der wörtlichen Definition wird sie in 72 h **nie** stabil und liegt nur 10 % der Zeit im Band. Mit dem Modell-Median sind es 37,1 %.

**Was das Skript deshalb liefert:** Drei Varianten, jeweils mit „stabil“ als erstem Zeitpunkt, ab dem der Wert 60 min ohne Unterbrechung im Band bleibt.
- `ziel`: wörtlich
- `modell`: p50 gegen ln2 × Ziel
- `mittel`: 1-h-Mittel gegen das Ziel

Im Testnet nach NU7 ergab das 1.541 min, 913 min und 800 min.

**Mein Vorschlag:** Die Spezifikation sollte das 1-h-Mittel gegen das Ziel nehmen, mit ± 20 %, oder ± 10 % über 3 h. Dann misst M6 die Kette und nicht das Rauschen.

## Offene Fragen an Ben

1. **M6:** Welche Definition geht in die Spezifikation v1 (pulsehawk.io/standard)? Die Seite wird bis Do 5.11. gebaut, die Frage sollte vorher geklärt sein. Mein Vorschlag steht oben. Die CSV enthält alle drei Varianten. Was nicht in die Spezifikation kommt, kann im Report als Anmerkung stehen oder entfallen.
2. **M3:** Gezählt wird jeder Wechsel unserer Spitze, auch Tiefe 1. Das passiert bei einem gesunden Netz ab und zu, wenn zwei Blöcke gleichzeitig gefunden werden. Soll der Report alle Wechsel nennen oder erst ab Tiefe 2? Die CSV hat Zahl und größte Tiefe; die Zahl ab Tiefe 2 lässt sich aus dem Log ergänzen.
3. **Grenzen der Zeitbasis:** M3 und M4 nehmen die Zeit unserer Wache (Ankunft), M1, M2 und M6 die Kopfzeiten. Die Fenstergrenzen weichen dadurch um Sekunden voneinander ab. Für v1 reicht das aus meiner Sicht; bitte bestätigen.

## Was Ben tun muss

1. **PR `wache/report-v1-c2` prüfen und mergen.** Er enthält nur `deploy/c2/upgrade-wache/`.
2. **Vor dem Fenster, also vor dem 5.11. 02:39 UTC, die Wache auf c2 neu starten**, damit sie den neuen Code und die neue Konfiguration lädt:
   ```
   sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet
   journalctl -u upgrade-wache@zcash-mainnet -n 20
   ```
   Der Schritt holt `main`, verlinkt die Units und startet die Instanz neu. Im Journal muss „ruht, fenster ab 2026-11-05 02:39:52 UTC“ stehen, oder ein späterer Wert, falls die Aufgabe am 4.11. die Schätzung nachzieht.
3. **Nach dem Fenster** (frühestens 73 h nach dem ersten NU7-Block, bei einer Aktivierung um 02:40 UTC also ab 9.11. 03:40 UTC):
   ```
   sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache-aus zcash-mainnet
   ```
   Dabei kommen Log und Rohdaten ins Repo.

## Merge-Zeilen

- [PR #241](https://github.com/neoalphavault-png/kaspa-pulse/pull/241) (`wache/report-v1`), Squash-Merge `7a1508f` am 2.11.2026. Ab jetzt sind auf `main` live: die Blockpause ab NU7 mit 300 und 600 s, die Proben bei 0, 6, 24 und 72 h, die Software der Peers in den Rohdaten, `roh_export.py` und `report_v1.py`. Auf c2 greift das erst nach `setup.sh wache zcash-mainnet`.
- [PR #242](https://github.com/neoalphavault-png/kaspa-pulse/pull/242) (`wache/report-v1-c2`) ist offen. Ben prüft und merged.
