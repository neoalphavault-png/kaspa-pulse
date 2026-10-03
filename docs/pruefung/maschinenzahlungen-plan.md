# Experiment „100 Zahlungen“, Machbarkeit

Stand 03.10.2026. Nur Plan, kein Lauf, kein Schlüssel, nichts signiert.
Ziel ist der Erklärer am Do 08.10. Routine 4 liest am Mi 07.10. um 19:00 aus dem Repo.
Das Ergebnis muss also bis **Di 06.10. abends auf main** sein.

Zahlen in dieser Notiz sind **Schätzungen** aus einer Rechnung mit dem Kaspa-SDK, offline und ohne Netz.
Sie dürfen nicht in den Erklärer. Dort stehen nur Zahlen aus dem Runner-Lauf.

## 1. Machbarkeit: ja

- **Werkzeug:** das Kaspa-Python-SDK `kaspa` 2.1.0 von PyPI. Die Projekt-Links zeigen auf `kaspanet/kaspa-python-sdk`.
  - Es baut, signiert und sendet Transaktionen.
  - Es kann Zahlungen mit Payload bauen (`create_transaction(..., payload=...)`).
  - Es rechnet Masse und Gebühr (`calculate_storage_mass`, `calculate_transaction_fee`).
  - Es findet einen öffentlichen Knoten per `Resolver` und meldet über `subscribe_virtual_chain_changed`, wann eine Tx von der Kette angenommen ist.
  - Im Container ließ es sich installieren und laden. Einen Lauf gegen das Netz gab es nicht.
- **Ablauf auf dem Runner:**
  1. Den Schlüssel aus der Umgebung lesen.
  2. Die daraus abgeleitete Adresse A mit der erwarteten Adresse vergleichen, sonst Abbruch.
  3. Die UTXOs von A holen.
  4. 100 Zahlungen nacheinander an Adresse B senden. Jede gibt das Wechselgeld der vorigen aus.
  5. Vor der nächsten Zahlung warten, bis die Kette die vorige angenommen hat. So sind Median und Maximum sauber je Tx gemessen.
  6. Danach optional den Rest von A an B zurück.
- **Gemessen wird je Tx:**
  - Zeit vom Absenden bis zur Annahme durch die Kette (Wanduhr des Runners, dazu der DAA-Score)
  - Gebühr
  - Masse (Rechenmasse und Speichermasse)
  - Payload-Größe in Bytes
  - Fehler
  - Tx-ID
- **Gemessen wird gesamt:**
  - Gesamtzeit von der ersten Absendung bis zur letzten Annahme
  - Median und Maximum
  - Gebühren gesamt
  - Fehlerzahl
- **„Bestätigung“ heißt hier:** angenommen von einem Block der ausgewählten Kette (accepted). Das ist keine Finalität.
  - Genau so muss es im Erklärer stehen.
  - Zur Gegenprobe kommen `is_accepted` und die Blockzeit aus api.kaspa.org in die JSON.
- **Im selben Lauf gemessen:**
  - **Blockrate über 10 Minuten:** Zuwachs des virtuellen DAA-Scores über 600 s, wie Form 4 (`m_blockrate`).
  - **Typische Gebühr einer einfachen Tx:**
    - Median der Gebühr aller Tx mit 1 Eingang und höchstens 2 Ausgängen, ohne Coinbase.
    - Stichprobe aus den Blöcken genau dieser 10 Minuten, mit Zeitfenster und Zahl der Tx.
    - Dazu die Gebührenschätzung des Knotens (`get_fee_estimate`).
- **Covenant-Outputs:** aus `data/covenants-log.json`. Quelle ist Kaspalytics, ein Wert je Tag.
  - Genommen wird der letzte vollständige Tag mit Datum. Heute ist das der 01.10. mit 582 erzeugten Outputs.
  - Am 06.10. ist es voraussichtlich der 05.10.
- **Laufzeit, geschätzt:**
  - 100 Zahlungen dauern wenige Minuten.
  - Dazu kommen 10 Minuten Blockrate.
  - Workflow-Timeout ist 30 Minuten.

### Die Grenze, die den Betrag bestimmt: Speichermasse (KIP-9)

Kleine Ausgänge machen eine Tx „schwer“. Über 100.000 Gramm nimmt kein Knoten sie an.
Offline mit dem SDK gerechnet für 1 Eingang und 2 Ausgänge (Zahlung plus Wechselgeld) aus 20 KAS:

| Zahlung | Speichermasse | Standard-Grenze 100.000 |
|---|---|---|
| 0,05 KAS | 200.001 | abgelehnt |
| 0,10 KAS | 100.002 | abgelehnt |
| 0,11 KAS | 90.911 | knapp |
| 0,15 KAS | 66.669 | ok |
| 0,19 KAS | 52.635 | ok |
| 0,50 KAS | 20.012 | ok |

Mit 20 KAS und 100 Zahlungen in eine Richtung geht höchstens rund 0,19 KAS je Zahlung.

**Vorschlag: 0,15 KAS je Zahlung, 15 KAS gesamt.**
- Masse rund zwei Drittel der Grenze.
- Knapp 5 KAS Puffer für Gebühren und einen Teil-Wiederholungslauf.

Schon die Grenze ist ein Befund für den Erklärer: Unter etwa 0,1 KAS je Ausgang nimmt das Netz eine einfache Zahlung nicht an.
Im Lauf wird die Masse je Tx gemessen. Erst diese gemessene Zahl darf in den Text.

## 2. Kosten

- **KAS:**
  - Höchstens 20 KAS Einsatz, nach dem Kraken-Schluss vom 02.10. (0,04209 USD) rund 0,84 USD.
  - Die 15 KAS der Zahlungen landen auf Adresse B, also bei Ben. Mit dem Rücklauf geht auch der Rest von A an B.
  - Verbraucht werden nur die Gebühren.
- **Gebühren, geschätzt:**
  - Die Gebühr folgt der Masse, mindestens 1 Sompi je Gramm (Mindest-Relaygebühr).
  - Bei rund 66.700 Gramm sind das etwa 0,00067 KAS je Tx, für 100 Tx etwa 0,07 KAS. Das ist unter einem Cent.
  - Gemessen wird die echte Zahl. Ist das Netz voll, steigt sie.
  - Sicherung: Abbruch, wenn eine einzelne Tx mehr als 0,01 KAS Gebühr hätte.
- **Abhebung von der Börse auf A:** die Gebühr der Börse, Bens Seite.
- **GitHub Actions:** kostenlos, das Repo ist öffentlich.

## 3. Secret-Weg

Der Schlüssel liegt nie im Repo und nie im Chat. Er wird nur aus der Umgebung gelesen, nach der Regel vom 02.10.

1. **GitHub Environment `testwallet`:** Repo, Settings, Environments.
   - Required reviewers: Ben.
   - Deployment branches: nur `main` und `pruefung/maschinenzahlungen-*`.
   - Jeder Lauf, der das Secret braucht, wartet auf Bens Klick „Approve“. Ohne Klick bekommt der Job den Schlüssel nicht. Das ist die harte Freigabe je Lauf.
2. **Namen (Vorschlag):**
   - Secret im Environment: `KASPA_TESTWALLET_PRIVKEY` (privater Schlüssel als Hex, nur für Adresse A).
   - Variable, kein Secret: `KASPA_TESTWALLET_ABSENDER`, die Adresse A. Das Skript bricht ab, wenn der Schlüssel nicht zu A passt.
   - Variable, kein Secret: `KASPA_TESTWALLET_ZIEL`, die Adresse B.
   - Der Schlüssel von B kommt nie auf den Runner.
3. **Schlüssel erzeugen auf Bens Rechner**, nicht auf dem Runner. Ein Runner kann kein Secret anlegen, ohne dass wir ihm ein Admin-Token geben.
   - Vorschlag: ein kleines Skript im Branch.
   - Es erzeugt mit `kaspa.Keypair.random()` einen frischen Schlüssel und schreibt ihn nur nach stdout, direkt in `gh secret set KASPA_TESTWALLET_PRIVKEY --env testwallet`.
   - Auf den Bildschirm kommt nur die Adresse A.
   - Der Schlüssel steht so nie im Terminal, nie in einer Datei und nie im Chat.
   - Eine Sicherung gibt es dann nicht. Der Rücklauf am Ende holt den Rest auf B, danach wird das Secret gelöscht.
4. **Nach dem Experiment:** Rest an B, Secret und Environment löschen. Adresse A wird nicht wieder benutzt.

## 4. Risiken und was dagegen hilft

- **Öffentliche Logs.** Das Repo ist öffentlich, also auch jedes Actions-Log.
  - GitHub schwärzt den Secret-Wert, aber nur in genau dieser Schreibweise.
  - Gegenmittel:
    - Das Skript druckt nie ein Schlüsselobjekt.
    - Fehler im Signierteil werden gefangen und nur mit Typnamen gemeldet, ohne Text.
    - Kein `set -x`.
    - Vor dem Schreiben der JSON prüft das Skript, dass der Schlüssel in keiner Form im Text steht. Sonst schreibt es nichts.
- **Lücke im Secret-Scanner.** `scripts/secret_scan.py` erkennt heute keinen Kaspa-Schlüssel und keine Seed-Wörter.
  - Ein allgemeines 64-Hex-Muster geht nicht, Tx-IDs sehen genauso aus.
  - Vorschlag als eigener fix/-PR vor dem Lauf:
    - 64 Hex an einem Namen mit priv, key, seed oder mnemonic
    - 12 oder 24 Wörter aus der BIP39-Liste in Folge
- **Fremdpaket mit dem Schlüssel in der Hand.**
  - `kaspa` 2.1.0 ist vom 25.09.2026, also neu.
  - Für die Wheels hat PyPI keine Herkunftsbestätigung (provenance 404). Ich kann nicht prüfen, dass die Datei aus dem kaspanet-Repo gebaut wurde.
  - Gegenmittel: Version und Hash festnageln (`--require-hashes`) und höchstens 20 KAS auf A.
  - Alternative wäre 2.0.1, das länger im Umlauf ist. Ben entscheidet.
- **Speichermasse.** Unter etwa 0,1 KAS je Zahlung lehnt das Netz ab. Deshalb der Vorschlag 0,15 KAS.
- **Knoten und Messweg.** Der Resolver wählt einen öffentlichen Knoten. Die Zeiten enthalten den Weg vom Runner (Azure, USA) zum Knoten.
  - Die JSON nennt den Knoten (nur den Namen, keine IP) und den Runner-Standort.
  - Die Gegenprobe über api.kaspa.org steht daneben.
- **Hänger und Fehler.**
  - Je Tx höchstens 60 s warten, dann Fehler zählen und weiter.
  - Nach 3 Fehlern in Folge Abbruch, mit Teilergebnis.
  - Ein Fehler ist eine Zahl in der JSON, kein Grund für eine Lücke im Bericht.
- **Payload ist für immer öffentlich.** Jede Tx trägt den Payload auf der Kette.
  - Vorschlag: ein kurzer neutraler Text wie `kp-test 017/100` (15 Byte, ASCII), nichts Persönliches, keine IP.
  - Ben entscheidet über Text, Name oder gar keinen Payload.
- **Zuordnung.** Payload und Tx-IDs in einem öffentlichen Repo machen A und B Kaspa Pulse zuordenbar. Für die Offenlegung im Erklärer ist das gewollt, aber Ben sollte es wissen.
- **„Nichts posten“.** Die 100 Zahlungen sind selbst eine Veröffentlichung auf der Kette. Deshalb kein Lauf ohne Bens Freigabe, und auch der Probelauf braucht eine eigene.
- **Termin.** Workflow-Dateien merged Ben von Hand. Ohne den Merge am Mo 05.10. ist der Di eng.
- **Wortregel für den Erklärer.** Die Zahlungen wurden gesendet und sind angekommen. Kein „gekauft“, kein Motiv.

## 5. Was ich von Ben brauche, bis So 04.10. abends

1. Freigabe des Plans, und dazu:
   - Betrag je Zahlung: Vorschlag 0,15 KAS.
   - Modus: Vorschlag nacheinander, jede wartet auf die Annahme der vorigen.
   - Rücklauf des Rests an B: Vorschlag ja.
2. Den Payload-Text (oder „kein Payload“).
3. Die SDK-Version: 2.1.0 oder 2.0.1.
4. Ja oder nein zum Scanner-PR (Kaspa-Schlüssel und Seed-Wörter) vor dem Lauf.

Dann am Mo 05.10.:

5. Environment `testwallet` mit Ben als Reviewer anlegen.
6. Schlüssel mit dem Skript erzeugen, direkt als Secret setzen. Mir nur die Adresse A nennen.
7. Adresse B (eigene Wallet) als Variable setzen und mir nennen.
8. Höchstens 20 KAS auf A senden.
9. Den Workflow-PR von Hand mergen.
10. Zwei Klicks „Approve“:
    - Probelauf mit 3 Zahlungen.
    - Dann der Lauf mit 100 Zahlungen.

## 6. Zeitplan

| Wann | Was |
|---|---|
| So 04.10. abends | Ben gibt frei, Antworten zu 1 bis 4 |
| Mo 05.10. vormittags | ich: Skript, Workflow-PR, Erzeuger-Skript, Scanner-PR, Trockenlauf ohne Schlüssel |
| Mo 05.10. | Ben: Environment, Secret, Variablen, 20 KAS, Merge des Workflows |
| Mo abends oder Di früh | Probelauf 3 Zahlungen, dann 100 Zahlungen, je mit Bens Klick |
| Di 06.10. | `data/pruefung/maschinenzahlungen-2026-10-06.json` und Kurzbericht als fix/-PR, Ben merged bis abends |
| Mi 07.10. 19:00 | Routine 4 liest |

Puffer ist ein Wiederholungslauf am Di. Fällt der aus, fehlt die Zahl, und dann steht im Erklärer keine Zahl.
