# Öffentliches Methoden-Repo pulsehawk/methods (Stand 8.11.2026)

Ben hat am 4.11. das öffentliche Methoden-Repo für PulseHawk beauftragt, dazu Laborgrundsätze im NU7-Report. Ziel ist, dass jeder unsere NU7-Zahlen nachrechnen kann, ohne dieses Repo zu kennen. Eine Akkreditierung behaupten wir nicht. Frist für den Inhalt ist So 8.11. 18:00.

## 0. Zugang

**Ein Branch nach `pulsehawk/methods` lässt sich pushen.** Getestet am 4.11. mit einem leeren Commit auf `zugang-test`.

- `main` ist geschützt, Ben merged.
- Den Testbranch konnte ich nicht wieder löschen, GitHub antwortete mit HTTP 403. Bitte löschen.
- Der Weg über `methods/export` in kaspa-pulse war deshalb nicht nötig.

## 1. Inhalt

[PR pulsehawk/methods#1](https://github.com/pulsehawk/methods/pull/1), Branch `nu7-report-v1`, gemergt am 4.11. als `04f3f6c`.

| Datei | Inhalt |
|---|---|
| `upgrade_report/report_v1.py` | M1 bis M7 nach Spezifikation v1.0. Jede Zeile hat Art, Verfahren (PH-M-001 bis 004), Fenster in UTC und n. Dazu eine Unsicherheits-CSV je Kennzahl und die sha256 aller Ein- und Ausgaben. Nur Standardbibliothek, Python ab 3.9. |
| `upgrade_report/configs/zcash-mainnet-nu7.json` | Höhe 3.543.405 mit Beleg (ZIP 259, Zebra v7.0.0, zcash_protocol 0.11.0), Ziel 75 s und 25 s, Schätzung 6.11. 02:39:52 UTC mit Band, Proben bei 0, 6, 24 und 72 h |
| `README.md` | „Reproduce the Zcash NU7 upgrade report in three commands“ |
| `METHODS.md` | die vier Verfahren, die Messunsicherheit, die Rückführbarkeit, M6 und warum der p50 verworfen wurde |
| `FORMATS.md` | Köpfe-CSV, Log der Wache, Zustand, Roh-Export, Report-CSV, Unsicherheits-CSV, Konfiguration. Deutsche Feldnamen mit englischer Bedeutung. |
| `ROUND_ROBIN.md` | Ringversuch, siehe Punkt 4 |
| `tools/heads_from_rpc.py` | Köpfe-CSV vom eigenen Knoten über JSON-RPC, für den Ringversuch |
| `examples/zcash-testnet-2026-10-17/` | Köpfe 4.508.646 bis 4.514.250 und der Roh-Export der Aufzeichnung vom 17.10., zusammen 412 KB, mit der erwarteten sha256 |

**Beispieldaten:**
- Echt sind Köpfe, Ankündigungen und Verbindungen.
- Die Aktivierung ist gestellt: Höhe 4.512.127 liegt mitten in der Aufzeichnung, das sagt das README des Beispiels.
- Log und Zustand stammen aus einem Replay der Aufzeichnung durch die Wache. Zwei Logzeilen nach dem Ende der Aufzeichnung habe ich entfernt, sie zeigen nur das Ende der Aufzeichnung. Auch das steht im README.
- Die Feldnamen im Roh-Export sind unverändert. So bleiben die sha256 in `SHA256SUMS` gültig.

**Selbsttest:**

| Aufruf | Ergebnis |
|---|---|
| `report_v1.py --selftest` | 11 von 11 ok, darunter das Nachrechnen der erwarteten sha256 des Beispiels |
| `heads_from_rpc.py --selftest` | ok gegen einen nachgebauten Knoten auf localhost; gegen einen echten Knoten nicht geprüft, wir betreiben keinen |

**Gegenprobe mit dem internen Skript:** Auf denselben Daten liefern das öffentliche und das interne `scripts/wache/report_v1.py` dieselben Zahlen, zum Beispiel M1 p50 nach Aktivierung 18,0 s und M6 3.612 s.

## 2. Regeln

- **Kein interner Name:** keine Namen aus kaspa-pulse, keine internen Bezeichner in Kommentaren, keine Workflows. Geprüft mit grep auf den ganzen Baum.
- **Keine Adressen:** keine Adressen, IPs oder Hostnamen in Code und Daten. Geprüft auch in den entpackten gz-Dateien.
- **Secret-Scan:** `secret_scan.py --baum` lief auf dem Baum von pulsehawk/methods vor dem Push und fand nichts.
- **Lizenz:** Die MIT-Lizenz bleibt.

## 3. Report am 9.11.

Die geplante Aufgabe für den Report am 9.11. ist angepasst. Der Report nennt:

- das Repo und den Commit, mit dem gerechnet wurde,
- die sha256 aller Eingänge aus `*-inputs.json`,
- je Zeile die Verfahrenskennung,
- je Kennzahl eine Zeile Messunsicherheit aus der Unsicherheits-CSV: Zeitbasis, Uhr, fehlende Daten, Lücken, Zahl der Peers.

Die NU7-Eingangsdaten kommen nach dem Fenster als PR nach `data/zcash-mainnet-nu7/` in pulsehawk/methods: Köpfe-Ausschnitt, Roh-Export und `SHA256SUMS`. Ben merged.

**Verfahrenskennungen:**

| Kennung | Verfahren | Kennzahlen |
|---|---|---|
| PH-M-001 | Blockabstände aus Köpfen | M1, M2, M6, Kopfzeit in M7 |
| PH-M-002 | Spitzenwechsel und Kettenspaltung | M3, M4 |
| PH-M-003 | Protokollversion beim Handschlag | M5 |
| PH-M-004 | erste Sicht und Ausbreitung | erste Sicht in M7 |

**Abgestimmt mit der Sitzung „PulseHawk Seite“ am 4.11.:** Die Seite übernimmt PH-M-001 bis 004 so und ergänzt zwei weitere Kennungen. Beide stehen jetzt auch in METHODS.md (Commit `ad2bf2b`).
- **PH-M-005**, stale-Blöcke nach 6 Bestätigungen: nicht im NU7-Report.
- **PH-M-006**, Prognose der Aktivierungszeit: gilt für die Schätzungszeilen in M7 (computed).

METHODS.md hat dazu einen Abschnitt „Validation so far“. Die Seite bekommt von mir:
- die drei Befehle für „reproduce this“, für das Beispiel und für den NU7-Mainnet-Report. Den Mainnet-Teil markiert die Seite bis zum Daten-PR als „kommt“.
- die Dateinamen je Kennung. Header-Client, Zuhörer, PH-M-005 und PH-M-006 sind noch nicht im Repo; auf der Seite steht dafür „implementation follows“.

## 4. Ringversuch

**Vorschlag:** M1, der Median der Blockabstände nach der Aktivierung (`p50_after`, PH-M-001).
- Fenster und Rechenweg stehen in `ROUND_ROBIN.md`, so genau, dass ein Dritter mit eigenem Knoten nachzählen kann: mit `tools/heads_from_rpc.py` und dem Report-Skript oder auf eigenem Weg.
- Veröffentlicht werden beide Zahlen, die Fenstergrenzen und n. Den Namen des Dritten nennen wir nur mit seiner Zustimmung.
- Wen wir fragen, entscheidet Ben.

## 5. Bis Mo 30.11.

Zählung mit dem Header-Client und die BCH-Tempnet-Skripte sollen nach demselben Muster ins Repo. Das ist noch nicht begonnen. Ich habe mir eine Erinnerung für den 12.11. gesetzt.

## 6. Stand 8.11.

**Seit dem 4.11. in pulsehawk/methods:**
- [pulsehawk/methods#2](https://github.com/pulsehawk/methods/pull/2): CONTRIBUTING.md nach den librustzcash-Regeln, von Ben gemergt am 7.11.
- [pulsehawk/methods#3](https://github.com/pulsehawk/methods/pull/3): `data/zcash-nu7/` mit der Testnet-CSV vom 4. bis 18.10. und den ersten 250 Mainnet-Abständen, von Ben gemergt am 7.11. Bericht dazu: `berichte/2026-11-06-grant-methods.md`.

**Bens Antworten (7.11.):**
- Die LICENSE bleibt MIT mit dem Inhaber „pulsehawk“.
- Der Verweis auf den Zcash Code of Conduct bleibt in der CONTRIBUTING.md.
- Ben schaltet Private Vulnerability Reporting ein und löscht die Branches `zugang-test` und `nu7-report-v1`. Beide Branches sind weg.
- Übrig sind die Branches `contributing` und `data-zcash-nu7` aus #2 und #3. Mir verweigert GitHub das Löschen (HTTP 403).

**Abstimmung mit der Sitzung PulseHawk Seite (4.11.), noch ohne Entscheidung:**
- **(a) Namen von PH-M-002 und PH-M-004:**

  | | METHODS.md | Seite |
  |---|---|---|
  | PH-M-002 | „Tip switches and chain split“ | „Reorg depth from the listener“ |
  | PH-M-004 | „First seen and propagation“ | „Propagation from the listener“ |

  Nach Bens Entscheidung gleiche ich METHODS.md an oder die Sitzung PulseHawk Seite die Seite.
- **(b) rufitnes/tempnet-data:** Soll METHODS.md diese öffentliche Vergleichsquelle beim Namen nennen? Die Seite tut es.
- **(c) M7 auf der Seite:** Soll die Seite in M7 auch die „erste Sicht“ (PH-M-004) zeigen?

METHODS.md bleibt unverändert, bis Ben (a) und (b) entschieden hat.

## Offene Fragen an Ben

1. **Datenumfang am 9.11.:** Sollen die NU7-Eingangsdaten vollständig ins öffentliche Repo, also der Roh-Export der 97 h und der Köpfe-Ausschnitt? Der Roh-Export enthält die Peer-Kennungen und Software, aber keine Adressen.
2. **Ringversuch:** Wen fragen wir?
3. **Feldnamen:** Sollen die deutschen Feldnamen in den Rohdaten bleiben (`hoehe`, `zeit`, `proben` und so weiter)? FORMATS.md erklärt sie. Eine Umbenennung würde die sha256 gegenüber unserem Datenbranch ändern.
4. **heads_from_rpc.py:** Das Werkzeug ist nur gegen einen nachgebauten Knoten getestet. Lassen wir es so im Repo, mit diesem Hinweis im PR?
5. **(a) Namen PH-M-002 und PH-M-004:** die aus METHODS.md oder die der Seite?
6. **(b)** Soll METHODS.md rufitnes/tempnet-data als öffentliche Vergleichsquelle nennen?
7. **(c)** Soll die Seite in M7 auch die erste Sicht (PH-M-004) zeigen?

## Was Ben tun muss

1. In pulsehawk/methods die Branches `contributing` und `data-zcash-nu7` löschen (#2 und #3 sind gemergt). `zugang-test` und `nu7-report-v1` sind schon weg.
2. Die Fragen oben beantworten. Frage 1 (Datenumfang) möglichst vor dem Report am 9.11.

## Merge-Zeilen

Merge-Regel vom 4.11.: Ich merge selbst, auch in pulsehawk/methods, außer bei Workflows, `deploy/`, c2-Dateien, Secrets, roten Checks, Konflikten oder Texten, die die Textregeln nicht bestehen.

| PR | Merge | Was jetzt live ist |
|---|---|---|
| [pulsehawk/methods#1](https://github.com/pulsehawk/methods/pull/1) | Squash `04f3f6c`, 4.11. | `report_v1.py` mit Selbsttest, METHODS.md mit PH-M-001 bis 006, FORMATS.md, ROUND_ROBIN.md, `tools/heads_from_rpc.py`, das Beispiel vom 17.10. und die NU7-Konfiguration mit der Schätzung vom 4.11. (02:40:58 UTC, Band 01:14:45 bis 04:07:28). Die Doku hat vorher den Textregel-Check bestanden; dafür habe ich Doppelpunkte im Fließtext ersetzt. |
| [kaspa-pulse#253](https://github.com/neoalphavault-png/kaspa-pulse/pull/253) | Squash `8fb01eb`, 4.11. | Forumsentwurf Woche 3 mit den drei Korrekturen |
| [pulsehawk/methods#2](https://github.com/pulsehawk/methods/pull/2) | von Ben, 7.11. | CONTRIBUTING.md |
| [pulsehawk/methods#3](https://github.com/pulsehawk/methods/pull/3) | von Ben, 7.11. | `data/zcash-nu7/` mit zwei CSV, README und SHA256SUMS |
| [kaspa-pulse#254](https://github.com/neoalphavault-png/kaspa-pulse/pull/254) | Squash `49a7734`, 4.11. | Upgrade-Wache: erwartet 6.11. 02:40:58 UTC, Band 01:14:45 bis 04:07:28. Auf c2 greift das erst nach `setup.sh wache zcash-mainnet`. |
