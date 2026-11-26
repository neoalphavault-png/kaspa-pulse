# Methoden-Repo Schritt 5, PR 3: Zuhörer für Zcash und Bitcoin Cash in pulsehawk/methods (26.11.2026)

Plan `berichte/2026-11-12-methods-schritt5.md`, Frist PR 3 Fr 27.11., gesamt Mo 30.11. Der Zuhörer und seine Auswertungen liegen als pulsehawk/methods#11 bei dir. Das Ergebnis: Auf denselben Daten wie die Originale geben die Auswertungen dieselben Zahlen, und der Zuhörer verarbeitet dieselben Nachrichten Zeile für Zeile gleich.

<!-- discord -->
Methoden-Repo Schritt 5, PR 3 liegt bei dir, der Zuhörer für Zcash und Bitcoin Cash in pulsehawk/methods#11. Ein Programm für beide Netze, dazu die Auswertungen und der Vergleich zweier Messpunkte. Auf allen Chipnet- und Tempnet-Läufen und 56 Zcash-Läufen geben die Auswertungen dieselben Zahlen wie die Originale, die Block-Tabellen sind bytegleich. Die Selbsttests laufen offline, dazu ein Beispiel mit 42 sha256, alle gleich. Frist Fr 27.11. ist eingehalten. Bericht berichte/2026-11-26-methods-schritt5-pr3.md
<!-- /discord -->

## Was gemacht wurde

- **`listener/listen.py`** aus `scripts/zcash/zcash_lauscher.py` und `scripts/bch/tempnet_lauscher.py`, ein Programm mit den Profilen `zcash-mainnet`, `zcash-testnet`, `bch-tempnet` und `bch-chipnet`.
  - Netzprofile, Nachrichtenschicht und Kopfformat übernimmt es aus `headers/ph_headers.py`.
  - Peers kommen nur über `--seed` oder `--peers-file`. Im Log und in den Dateien steht je Verbindung nur ein Label und der gekürzte User-Agent, wie seit #327.
  - Die Dateien und Feldnamen sind dieselben wie in unseren Aufzeichnungen, damit alte und neue Läufe gleich lesbar bleiben. FORMATS.md erklärt jedes Feld auf Englisch.
- **`listener/evaluate_bch.py`** aus `scripts/bch/lauscher_auswertung.py`: first seen, Streuung, Ankunft minus Kopfzeit, Compact-Block-Weg und Stale nach 6 Bestätigungen.
- **`listener/evaluate_zcash.py`** aus `scripts/zcash/lauscher_auswertung.py`: abgehängte Blöcke mit Zweigen und Tiefe, Phasen vor und ab der Aktivierung, Zakura minus Zebra.
- **`listener/propagation.py`:** die Ausbreitung zwischen zwei Messpunkten aus `tempnet_stuecke.py`, die PR 2 ausgelassen hat. Im Repo heißen die Messpunkte A und B.
- **Kennungen:** PH-M-004 und PH-M-005 haben in METHODS.md jetzt ihre Implementierung. PH-M-002 (Spitzenwechsel) gehört zum Wächter und ist nicht Teil dieses PR.
- **Dokumentation:** FORMATS.md (Zuhörer-Dateien, Ausgaben der Auswertungen, Beispiel), README.md und CONTRIBUTING.md (Selbsttests, Datenfilter auch über `listener/examples/`).

## Selbsttests und Beispiel

| Skript | Prüfungen |
|---|---|
| `listen.py` | 28 |
| `evaluate_bch.py` | 10 |
| `evaluate_zcash.py` | 8 |
| `propagation.py` | 3 |

- **`listen.py`:** prüft SipHash-2-4 gegen die Referenzwerte und die Kürzung der User-Agents. Dazu spielt es Nachrichten aus den echten Köpfen in `headers/fixtures/` durch die Verarbeitung beider Netze. Die Testnamen und Testadressen setzt es erst zur Laufzeit zusammen, im Code steht keine.
- **`listener/example.py`:** rechnet alle Auswertungen auf einem Auszug unserer Aufzeichnungen und vergleicht 42 sha256, alle gleich.
  - Zwei Chipnet-Läufe vom 24.11.
  - Zwei Zcash-Mainnet-Läufe vom 25.11.
  - Ein Tempnet-Abend vom 9.11. mit beiden Messpunkten.
- **Alte Selbsttests:** alle weiter bestanden.

## Vergleich mit den Originalen

| Port gegen Original | Eingabe | Ergebnis |
|---|---|---|
| evaluate_bch | 35 Chipnet-Läufe, 9.864 Kettenblöcke | CSV bytegleich, 566 von 566 Zahlen |
| evaluate_bch | 94 Tempnet-Läufe, 29.522 Kettenblöcke | CSV bytegleich, 3.232 von 3.232 Zahlen |
| evaluate_bch | 25 Tempnet-Läufe vom zweiten Messpunkt | CSV bytegleich, 1.244 von 1.244 Zahlen |
| evaluate_zcash | 56 Läufe der Zcash-Dauerserie, 43.350 Kettenblöcke, 178 abgehängt | 2.144 von 2.144 Zahlen |
| propagation | zweiter Messpunkt gegen GitHub, 8.150 Blöcke | 9 von 9 Werten |
| listen.py | dieselben Nachrichten an die alten Zuhörer | alle Zeilen gleich (ohne Ankunftszeit), getdata und Zähler gleich |

- Verschieden sind nur die freien Texte. Die Schlüssel der Zusammenfassungen sind jetzt englisch, ihre Reihenfolge ist gleich.
- **Was nicht verglichen werden konnte:** Der Zuhörer selbst lief hier nicht in einem Netz, weil diese Umgebung keine P2P-Verbindung hat. Verglichen ist die Verarbeitung der Nachrichten.
- **Zcash, 56 statt 59 Läufe:**
  - Die drei jüngsten Läufe enden nach der Spitze der täglichen Köpfe, 25.11. 15:48 UTC.
  - Gegen diese Kette bricht das Original mit einer Rekursion ab, weil es die späteren Kettenblöcke als einen langen abgehängten Zweig zählt. Im Workflow passiert das nicht, dort wird die Kette nach den Läufen geholt.
  - Der Port rechnet die Tiefe ohne Rekursion und läuft auch auf allen 59 Läufen durch. METHODS.md sagt, dass die Kette nach den Läufen geholt werden muss.

## Was anders ist als im Original

- Ein Programm statt zwei. Die Ausgabe geht in einen Ordner `--out` je Lauf.
- Die Zusammenfassungen haben englische Schlüssel. Die Block-Tabelle (`--csv`) ist unverändert.
- `evaluate_zcash.py` liest Lauf-Ordner und unsere bisherigen Dateien `sNN-…`.
- **Alte Tempnet-Metadaten:** Darin standen User-Agents noch ungekürzt, mit Kommentaren, die die Peers selbst wählen. Im Beispiel sind sie mit derselben Kürzung wie seit #327 gekürzt.

## PR-Nummern

- pulsehawk/methods#11, Zuhörer und Auswertungen, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. Die Datei- und Feldnamen der Zuhörer-Ausgabe bleiben deutsch (`ereignisse`, `koepfe`, `zeit`, `von_selbst` …), damit alte und neue Läufe gleich lesbar sind. FORMATS.md übersetzt jedes Feld. Passt das so, oder sollen neue Läufe englische Namen bekommen? Dann bräuchten die Auswertungen einen Leser für beide Namen.

## Was Ben tun muss

- pulsehawk/methods#11 prüfen und mergen, bis Mo 30.11.
- Die Frage beantworten.
