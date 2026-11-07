# PH-Stil umgestellt, Methods-Entscheidungen, Monero-Probe (7.11.2026)

Ben hat am 7.11. drei Dinge entschieden: Der PH-Stil ist freigegeben (Falke türkis, oben mittig), die Methods-Fragen sind beantwortet, und für Monero gilt Weg b, zuerst mit der Probe von 15 min.

<!-- discord -->
PH-Stil: alle Vorlagen umgestellt (kaspa-pulse #276, pulsehawk-site #68). Die finale NU7-Karte ist in #ph-entwuerfe. Monero-Stressnet: Die Probe von 15 min lief, 12 Stressnet-Peers, 3 Blöcke, Blockhash selbst nachgerechnet und durch die Kette bestätigt. Der Dauerlauf wartet auf Bens Ja.
<!-- /discord -->

## 1. PH-Stil

- **Falke:** türkis #49EACB, oben mittig, 56 px. Im Querformat 64 px. Der Fuß „Data from PulseHawk · pulsehawk.io“ bleibt unten. Der Falke ist die Marke und zählt nicht als das eine türkise Daten-Element.
- **[kaspa-pulse#276](https://github.com/neoalphavault-png/kaspa-pulse/pull/276)**, selbst gemergt (`1cfc090`):
  - `ph_stil.py` mit Falke, einem matplotlib-Teil für die Entwürfe im Querformat 1600x900 und Inter als ttf (aus den woff2 umgewandelt, OFL). Die Zeichenprüfung steckt jetzt im Modul, damit die Datei in beiden Repos gleich ist.
  - `ph_entwurf.py` für BCH, Zcash und Zcash-Mainnet:
    - Titel klein, Türkis nur für die gezählten Balken, die berechneten Werte als graue gestrichelte Linie mit 1,5 px.
    - Höchstens 8 Tagesbeschriftungen, sonst liefen sie bei 34 px ineinander.
    - Mit echten Daten neu gezeichnet und angesehen: BCH Stand 4.11., Zcash-Testnet 4. bis 18.10., Zcash-Mainnet Stand 6.11.
  - `report_karte.py`, neu: Karte zum Upgrade-Report v1 aus der Report-CSV von pulsehawk/methods.
    - Große Zahl ist der gezählte Median nach der Aktivierung, darunter p90, p99, Lücken über 5x Ziel und die längste Lücke, jeweils gezählt gegen berechnet.
    - Fehlt ein Wert in der CSV, bricht das Skript ab.
    - Gedacht für den PH-Post am Mo 9.11. 11:00.
  - `nu7_karte.py` in der finalen Fassung.
- **[pulsehawk-site#68](https://github.com/neoalphavault-png/pulsehawk-site/pull/68)**, selbst gemergt (`1ec652b`): gleiche `ph_entwurf.py` und `ph_stil.py`, dazu Inter und der Falke unter `assets/`. Auf beiden main-Branches sind die Dateien byte-gleich geprüft.
- **NU7-Karte im finalen Stil** in #ph-entwuerfe, 7.11. 08:34 UTC, über `ph/stil-muster` (Lauf 42356036814). Damit ist die Frist So 18:00 erfüllt.
- **nu7_zitat:** `nu7_zitat.py` lag nur auf dem Branch `ph/nu7-zitat`. Die Karte im neuen Stil ist `nu7_karte.py` auf main. Die alte Datei bleibt auf dem Branch als Beleg.
- **Nicht umgestellt:** `ph_kalender_post.py` in pulsehawk-site zeichnet die Kalender-Grafik noch im alten Stil. Sie stand nicht in Bens Liste, siehe Fragen.

## 2. Methods (Entscheidungen Ben)

- Die LICENSE bleibt MIT, Inhaber „pulsehawk“.
- Der Verweis auf den Zcash Code of Conduct bleibt in der CONTRIBUTING.md.
- Ben merged pulsehawk/methods#3 bis So 18:00 und pulsehawk/methods#2 bis Mo 12:00. Er schaltet Private Vulnerability Reporting ein und löscht die Branches `zugang-test` und `nu7-report-v1`.

## 3. Monero-Stressnet, Probe

- **Branch:** `messung/monero-stressnet`.
  - Skript `scripts/monero/stressnet_lauscher.py`.
  - Workflow `monero-stressnet-lauscher.yml`, nur auf diesem Branch, nur `--probe`, ohne Secret.
- **Selbsttest:** Keccak ist gegen pycryptodome geprüft, alle Längen gleich. Die Genesis-Blöcke von Testnet und Mainnet kommen richtig heraus. epee, Levin und ein Block mit Fork 17 bestehen ebenfalls.
- **Probe**, Lauf 42356483720, 7.11. 08:40 bis 08:55 UTC, Daten unter `data/monero-stressnet/probe-2026-11-07-0840/`:
  - 32 Adressen versucht, 18 verbunden, davon 12 Stressnet-Peers (top_version 18, Höhe 3.126.365).
  - 6 Peers waren kein Stressnet: 4 normale Testnet-Knoten mit Version 16, einer im Stressnet-Code unter dem Abzweig, einer noch beim Synchronisieren. Sie wurden getrennt.
  - **Alle 12 Stressnet-Peers schickten neue Blöcke**, in beiden Modi: 9 mit ehrlicher Höhe 1, 3 mit der gesehenen Spitze. Knoten schicken also auch einem Peer Blöcke, der wie ein synchronisierender Knoten aussieht. Plan B (Spitze angeben) ist nicht nötig.
  - Die Peers blieben verbunden. Jeder beantwortete 10 bis 14 timed_syncs, etwa einen pro Minute. Nur ein Peer fiel mit Timeout aus.
  - **3 Blöcke**, Höhen 3.126.362 bis 3.126.364. Für 362 und 363 ist unser nachgerechneter Hash genau der Vorgänger im nächsten Block. Die Hash-Rechnung mit den FCMP++-Feldern stimmt also.
  - Abstände nach Kopfzeit 265 s und 319 s (Ziel 120 s). Erste Sicht 8,7 s, 11,1 s und 32,5 s nach der Kopfzeit. Spread über die Peers 86, 122 und 296 ms.
  - Die Blöcke enthielten keine Transaktion, und es kamen keine Tx-Ankündigungen. Im Stressnet war zu dieser Zeit keine Last.
- **Fehler gefunden und behoben:** `bis_ende_verbunden` stand bei 0, weil das Skript am Ende die Sockets selbst schließt und das als Trennung zählte. Der Fix ist auf dem Branch (`c7f09dc`).
- **Laufzeit:** Das Stressnet läuft noch, die Spitze wächst. Ein Ende ist weiter nicht angekündigt.

## Offene Fragen an Ben

1. **Monero-Dauerlauf:** Ja? Er liefe wie beim BCH Tempnet als Kette von Läufen zu je 330 min auf GitHub Actions, mit täglicher Auswertung. Der Workflow bekommt dafür einen zweiten Modus, nur auf `messung/monero-stressnet`. Ich prüfe ihn vor dem Start.
2. **Wenig Last im Stressnet:** Zur Zeit der Probe gab es leere Blöcke und Abstände von 4 bis 5 min. Willst du trotzdem messen? Die Zahl wäre dann vor allem eine Leerlauf-Basis.
3. **Kalender-Grafik:** Soll `ph_kalender_post.py` in pulsehawk-site auch auf `ph_stil.py` umgestellt werden?

## Was Ben tun muss

1. Bis So 8.11. 18:00 pulsehawk/methods#3 mergen, bis Mo 9.11. 12:00 pulsehawk/methods#2.
2. In pulsehawk/methods Private Vulnerability Reporting einschalten und die Branches `zugang-test` und `nu7-report-v1` löschen.
3. Ja oder Nein zum Monero-Dauerlauf.
