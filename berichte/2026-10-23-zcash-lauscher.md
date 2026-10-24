# Zcash Mainnet, Zuhörer nach NU7, Bericht 23.10.2026

Auftrag (Ben, 23.10.2026, nach dem Merge von kaspa-pulse#133 und pulsehawk-site#35):

1. Die CSV nach NU7 kommt nach pulsehawk-site unter `data/zcash-mainnet/`.
2. Nach der Aktivierung 48 Stunden zuhören wie am 17.10. im Testnet. Die wichtigste Zahl ist der Anteil angekündigter Blöcke, die bei 25 s nicht in die Kette kommen. Keine Peer-Adressen in Dateien oder Logs.
3. Die eigene Workflow-Datei für die Mainnet-Entwürfe passt so.
4. Am Cron von `zcash-mainnet.yml` die Berliner Zeit als Kommentar ergänzen.

## Was gebaut ist (PR kaspa-pulse#135, Branch `zcash/mainnet-lauscher`)

- `scripts/zcash/zcash_lauscher.py`: der Testnet-Zuhörer vom 17.10., jetzt mit `--netz testnet|mainnet`.
  - Auf dem Mainnet läuft er mit Protokoll 170190.
  - Peers heißen zebra-1, zakura-2 usw., dazu ihre Software. Adressen stehen weder in Daten noch im Log.
- `.github/workflows/zcash-mainnet-lauscher.yml`: Ein GitHub-Job läuft höchstens 6 h. Die 48 h sind deshalb eine Kette von Läufen.
  - **Wechsel ohne Lücke:** Jeder Lauf hört bis 330 min zu und startet 8 min vor seinem Ende den nächsten. Die Läufe überlappen also kurz.
  - **Entscheidung über den nächsten Lauf:** Vor dem Weiterreichen holt der Lauf kurz die Köpfe ab 3.543.355 und prüft, ob der NU7-Block schon da ist und wann.
  - **Ende:** wenn das Ende des Laufs mehr als 48 h nach dem ersten NU7-Block liegt, spätestens am 10.11.2026 00:00 UTC.
  - **Rohdaten:** Die Daten jedes Laufs gehen sofort auf `messung/zcash-mainnet` unter `data/zcash-mainnet/lauscher-nu7/sNN-*`. Danach holt der Lauf die Kette und wertet alle Läufe bis dahin aus (`zusammenfassung.json`).
- `scripts/zcash/lauscher_auswertung.py`:
  - legt mehrere Läufe zusammen
  - zählt mit `--nu7` den Anteil abgehängter Blöcke vor NU7 und ab NU7, ab NU7 zusätzlich je 6 h
  - **Definition des Anteils:** abgehängte Blöcke geteilt durch die angekündigten Kettenblöcke plus die abgehängten
  - Weil der Zuhörer am 5.11. einige Stunden vor der Aktivierung startet, gibt es auch ein Stück 75 s zum Vergleich.
- `scripts/zcash/daten_committen.sh`: Commit auf den Datenbranch mit Secret-Scan und drei Push-Versuchen. Zuhörer-Läufe und der Tageslauf schreiben gleichzeitig.
- `scripts/zcash/zcash_koepfe.py`: `--gegenproben 0` für den kurzen Abruf im Zuhörer.
- `.github/workflows/zcash-mainnet.yml`: Am Cron steht jetzt der Kommentar "05:23 UTC = 07:23 Berlin bis 25.10.2026 (Sommerzeit), danach 06:23 Berlin". Der Commit läuft über `daten_committen.sh`.

## Prüfungen

- **Rückwärtsprobe:** Die Auswertung mit dem Testnet-Lauf vom 17.10. ergibt dieselben Zahlen wie damals.
  - 776 Kettenblöcke im Fenster, 775 angekündigt gesehen
  - 5 abgehängt, Tiefe 1
  - Zakura minus Zebra im Median 36 ms
- **Zwei Läufe und NU7-Trennung:** Den Testnet-Lauf habe ich doppelt eingespeist und eine NU7-Höhe mitten ins Fenster gelegt.
  - Die Summen bleiben gleich.
  - Die 5 abgehängten Blöcke teilen sich in 2 vor und 3 ab der Höhe.
- **Entscheidung über den nächsten Lauf:** mit vier Fällen geprüft.
  - NU7 vor 1 h: weiter.
  - NU7 vor 49 h: Schluss.
  - NU7 noch nicht erreicht: weiter.
  - Grenze `spaetestens_utc` erreicht: Schluss.
- **Testlauf auf dem Mainnet** (8 min, Push auf den PR-Branch): grün.
  - 9 Verbindungen: 6 /Zebra:7.0.0/, 2 /Zakura:1.7.0/, 1 /Zakura:1.5.0/
  - 5 von 6 Kettenblöcken angekündigt gesehen, 0 abgehängt
  - Kette und Gegenprobe: /Zebra:7.0.0/ 500 von 500 gleich
  - Die Testdaten liegen auf `messung/zcash-mainnet` unter `lauscher-test/`.
  - In Daten und Log stehen nur Labels und Software, keine Adressen. Der Secret-Scan hat nichts gefunden.
- **Noch nicht getestet:** das Weiterreichen an den nächsten Lauf. `workflow_dispatch` geht erst, wenn die Datei auf main liegt. Der Kettentest ist für Mi 28.10. eingeplant: zwei Läufe von je 20 min, der zweite darf keinen dritten starten.

## Termine (UTC)

| Termin | Was |
|---|---|
| Mi 28.10. 15:00 | Mittwochsstand Mainnet, Kettentest des Zuhörers (wenn #135 gemergt) |
| Mi 04.11. 15:00 | Letzter Stand vor der Aktivierung |
| Do 05.11. 17:00 | Start des Zuhörers, mindestens 4 h vor der unteren Bandgrenze der Vorhersage |
| Fr 06.11. 09:00 | Kurznotiz nach der Aktivierung, CSV-PR in pulsehawk-site, erster Zwischenstand des Zuhörers |
| So 08.11. 10:00 | Auswertung des Zuhörers nach 48 h, Lücken zwischen den Läufen offen genannt |
| Mi 11.11. und 18.11. 15:00 | Wochenstand mit CSV in pulsehawk-site `data/zcash-mainnet/` |

## Offene Fragen an Ben

1. Soll die Zuhörer-Zahl am 8.11. einen eigenen Post-Entwurf nach #ph-entwuerfe bekommen? Gemeint ist der Anteil abgehängter Blöcke ab NU7. Bisher gehen nur die Stände der Blockabstände dorthin.

## Was Ben tun muss

- **kaspa-pulse#135 prüfen und mergen, möglichst vor Mi 28.10.:** sonst entfällt der Kettentest, und der Start am 5.11. geht nicht.
- **Sonst nichts.** Den Start am 5.11. und die Auswertung übernehme ich.

Der Secret-Scan hat in `zcash/mainnet-lauscher` und `messung/zcash-mainnet` keine Schlüssel und keine Tokens gefunden.
