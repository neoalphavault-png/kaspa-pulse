# Bericht 27.10.2026: Format „Kaspa in Zahlen, zum Anfassen“ und Halloween-Post

Auftrag von Ben vom 27.10.2026.

## Was gemacht wurde
- **Generator `scripts/vergleichs_karussell.py`**, mit Selbsttest. Ein wiederholbares Karussell: Eine gezählte Zahl wird in Alltagsmomente übersetzt.
  - **Look:** sehr große Zahl, klare Hierarchie, freigestelltes Objekt, Grund #080B0F, Weiß #F2F5F4, Akzent #49EACB, Wortmarke KASPA PULSE, kein Falke.
  - **Neue Zahl:** `--lauf JJJJ-MM-TT` nimmt einen anderen Tag aus dem Tagesgrafik-Log.
- **Muster-Karussell „how fast is kaspa, really?“,** 8 Folien, 1080 × 1350.
  - **Zahlengrundlage:** `data/tagesgrafik-log.json`, Lauf vom 21.10.2026: 9.962104 Blöcke je Sekunde über 600 s, gezählt. Alles andere ist daraus gerechnet.

  | Folie | Zahl | Herkunft |
  | --- | --- | --- |
  | 1 | Titel, 9.962 | counted 21 oct 2026 über 600 s, Stoppuhr |
  | 2 | 10 | Protokollrate seit Crescendo, 5 may 2025, darunter „we counted 9.962“, 10 Blöcke als Reihe |
  | 3 | 100 | computed, 9.962 × 10 s = 99.6, Sanduhr |
  | 4 | 2,989 | computed, 9.962 × 300 s = 2,988.6, Tasse |
  | 5 | 287,000 | computed, 9.962 × 8 h = 286,908.6, auf der Folie „rounded from 286,909“, Bett |
  | 6 | 1 und 5,977 | Bitcoin 1 Block je 600 s by design, Kaspa 9.962 × 600 s = 5,977.3, nebeneinander gleich groß, ohne Werturteil |
  | 7 | 9.962 | how we count: virtueller DAA-Score aus der Kaspa REST API, 600 s, 21 oct 2026 |
  | 8 | link in bio | „the weekly kaspa numbers by email“, Umschlag |

- **Halloween-Post** für den 31.10.2026, Einzelbild 1080 × 1350.
  - **Zahl:** „99,903“, also „KAS less new supply every day from 4 nov 2026“.
  - **Satz:** „daily emission steps down from 1,779,989 to 1,680,086 KAS on 4 nov 2026.“ Computed aus dem Emissionsplan (`startseite.emission`).
  - **Bild:** Spinnennetz mit Spinne oben rechts, Kürbis mit Gesicht in #49EACB.
- **Captions** für beide, durch `karussell.caption_pruefen`: `docs/vergleichs-karussell/caption-*.txt`.
- **Bilder** als JPEG unter `ig/vergleich/`, nach dem Merge auf kaspapulse.com zum Herunterladen. Dazu der Kontaktbogen `docs/vergleichs-karussell/kontaktbogen-390.png` und das Bildregister `docs/vergleichs-karussell/README.md`.

## Was ich gegenüber dem Auftrag geändert habe
1. **Folie 2:** Die große 10 ist die Protokollrate, nicht „counted“. Gezählt haben wir am 21 oct 9.962, das steht klein darunter. „10 blocks per second, counted 21 oct“ wäre falsch gewesen.
2. **Folie 6:** „about 5,977“ statt „about 5,980“. 9.962 × 600 s ergeben 5,977.3. So stimmt die Zahl mit unserer Zählung überein.
3. **Zahlen in Ziffern:** „in 10 minutes“ statt „in ten minutes“ und „1 block“ statt „one block“, weil die Textwache Zahlwörter sperrt. Statt „protocol target“ steht „by design“, „target“ steht auf der Wortliste.
4. **Objekte gezeichnet statt fotografiert:** Die offenen Bildarchive waren aus der Arbeitsumgebung nicht erreichbar (ENOTFOUND bei allen vier). Nach dem Taste Skill heißt das: zeichnen und melden. Die Objekte sind graue Freisteller mit Schatten im Collage-Stil, ohne Lizenzfrage.

## Prüfung
- **Selbsttest grün:**
  - jede Zahl gegen die Daten (100, 2,989, 287,000 mit 286,909, 5,977, 99,903, 1,779,989 auf 1,680,086)
  - die 10 heißt Protokollrate und nicht counted
  - Werturteil, andere Chain, Bitcoin außerhalb von Folie 6, Zahl ohne Datum und Echtzeitwort fallen auf
  - beide Captions grün
- **Textwache:** `karussell.text_pruefen` für jeden sichtbaren Satz. „bitcoin“ ist nur auf Folie 6 erlaubt, als Maßstab mit zwei Zahlen.
- **Bild:** `content_wache` im Profil feed für jede Folie (Rand 60 px, Mindestgrößen, Fußzeile mittig). Dazu eine eigene Prüfung, dass kein Objekt auf einem Text liegt und keine Zahl breiter ist als ihre Spalte.
- **Lesbarkeit bei 390 px:** alle 9 Bilder auf dem Kontaktbogen in Handybreite angesehen. Die kleinste Schrift ist 34 px bei 1080, also gut 12 px am Handy, wie bei der Tagesgrafik.
- Secret-Scan sauber.

## PR-Nummern
- #162, Generator, Muster-Karussell, Halloween-Post und dieser Bericht

## Offene Fragen an Ben
1. **Fotos:** Sollen die Objekte später doch freigestellte Fotos aus offenen Archiven werden? Das ginge von einem Rechner mit Netz, Register und Ablauf stehen in `docs/vergleichs-karussell/README.md`.
2. **Nächste Ausgabe:** Welche gezählte Zahl kommt als nächste in dieses Format? Ideen sind Gebühren je Tag, Adressen ab 100 KAS oder Covenants.

## Was Ben tun muss
Steht im Discord-Paket, das nach dem Merge geht.
