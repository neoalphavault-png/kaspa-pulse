# Methoden-Repo Schritt 5, PR 1: Header-Client in pulsehawk/methods (16.11.2026)

Plan `berichte/2026-11-12-methods-schritt5.md`, Frist PR 1 Mi 18.11., gesamt Mo 30.11. Umgesetzt nach deinen Antworten auf die zwei Plan-Fragen. Es ist ein Programm mit zwei Netzen, und die Rechnungen aus Einzelanlässen gehen in die allgemeinen Skripte.

<!-- discord -->
Methoden-Repo Schritt 5, PR 1 liegt bei dir: der Header-Client headers/ph_headers.py für Zcash und BCH in pulsehawk/methods#7. Der Selbsttest läuft offline mit je 20 echten Köpfen und macht 32 Prüfungen, alle bestanden. Im Repo steht keine Adresse. Frist Mi 18.11. ist eingehalten. Bericht berichte/2026-11-16-methods-schritt5-pr1.md
<!-- /discord -->

## Was gemacht wurde

- **`headers/ph_headers.py`:** ein Programm aus `zcash_koepfe.py`, `tempnet_koepfe.py` und `chipnet_koepfe.py`. Es ist englisch und nutzt nur die Standardbibliothek.
- **Netzprofile:** Es gibt vier, `zcash-mainnet`, `zcash-testnet`, `bch-tempnet` und `bch-chipnet`. Sie unterscheiden sich in Magic, Port, Protokoll, Kopfformat und Fixpunkten. Die Chipnet-Prüfung (327.989 darf nicht der Tempnet-Block sein) steckt als Profil darin statt als eigenes Skript.
- **Keine Adressen im Repo:** Seeds und Peers kommen nur über `--seed` und `--peers-file` auf der Kommandozeile, Checkpoints über `--checkpoints` als Datei. In Log und Meta steht je Peer nur der Software-Name ohne den Kommentar in Klammern. Damit ist auch der Fund vom 15.11. (Hostname in einer Software-Kennung) im neuen Client ausgeschlossen.
- **Prüfungen wie bisher:** Verkettung, Arbeit gegen nBits, Fixpunkte und Checkpoints, Probe am Abzweig für die Zielhöhe und Gegenprobe mit zwei weiteren Peers.
- **Fixtures:** je 20 echte Rohköpfe.
  - Zcash Mainnet 3.543.405 bis 3.543.424, die ersten 20 Blöcke nach NU7
  - BCH Tempnet 327.989 bis 328.008
  - Geholt hat sie der neue Client selbst am 16.11. über einen einmaligen Lauf auf dem Branch `methods/koepfe-roh` in kaspa-pulse.
  - Gegenprobe je 20 von 20, bei Zcash mit Zebra und Zakura.
  - Die Zeilen sind gleich wie in unseren bisherigen Kopf-CSVs.
- **Selbsttest offline, 32 Prüfungen, alle bestanden:** nBits, Varint, Locator und Software-Name, dazu die sha256 jeder Fixture und ihrer CSV. Außerdem prüft er, dass jede Prüfung ihren eigenen Fehler fängt, und dass Tempnet-Köpfe unter dem Chipnet-Profil abgelehnt werden.
- **Dokumentation:** In `METHODS.md` bekommt PH-M-001 einen Absatz zur Implementierung. `FORMATS.md` beschreibt das Meta-Format und das Fixture-Format, `README.md` und `CONTRIBUTING.md` nennen den neuen Selbsttest.
- **Prüfungen vor dem Push:** Secret-Scan `--baum` sauber, die beiden alten Selbsttests bestanden, der Datenfilter aus `CONTRIBUTING.md` über `headers/` leer.

| Datei | sha256 |
|---|---|
| `zcash-mainnet-3543405.json` | `afc39c3c37bc39e43bc13f95f59f40d2b99e4128738b5456d7228f66b200ef51` |
| CSV daraus | `6aabc88d7d7c6cc77deb7c0e4ecae468ae25920ea1ba634958415bc13c21a02d` |
| `bch-tempnet-327989.json` | `e9cda8048beb778b2454005a7e14555225d2fe2c4e6a9f4be29f535881136f06` |
| CSV daraus | `33e5cc218c444c5b68d15638167c8cca23c1be1db109ce658d205634a385da1b` |

## PR-Nummern

- pulsehawk/methods#7, Header-Client, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. **Branch `methods/koepfe-roh` in kaspa-pulse:** Er enthält einen einmaligen Abruf-Workflow und die Rohköpfe als Herkunftsnachweis. Er wird nicht gemergt. Soll ich ihn nach deinem Merge von #7 löschen, oder bleibt er als Nachweis stehen?
2. **Alter Treffer im Datenfilter:** `data/zcash-nu7/README.md` Zeile 7 nennt unsere eigene Seite und fällt deshalb in den Datenfilter aus `CONTRIBUTING.md`. Das stammt nicht aus diesem PR. Soll die Zeile ohne den Seitennamen auskommen, oder nimmt der Filter unsere Seite aus?

## Was Ben tun muss

- pulsehawk/methods#7 prüfen und mergen, Frist Mi 18.11.
- Die zwei Fragen beantworten.
