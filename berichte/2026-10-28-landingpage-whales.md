# Bericht 26.10.2026: Plausible auf kaspapulse.com und Landingpage /whales

Auftrag vom 26.10.2026.
- **Teil 1:** Frist 26.10.2026 18:00 Berlin
- **Teil 2:** Frist 28.10.2026 18:00 Berlin

Beide Teile sind am 26.10.2026 als PR fertig. Claude prüft, Ben merged.

## Was gemacht wurde

### Teil 1, Plausible (PR #148)
- **Snippet:** Das Plausible-Snippet (Methode Script) steht im `<head>` aller 42 öffentlichen Seiten, ab #150 auch auf /whales.
  - wo: zwischen `<!--AUTO:plausible-->` und `<!--/AUTO:plausible-->`
  - wer es setzt: `scripts/plausible.py` mit `--pruefen` und `--selbsttest`
  - Seitenliste wie in `seo_seiten.py`: alle `*.html` außer `utm-test.html`, Wochenseiten, Archiv, method
  - Startseite, Wochenseiten, Archiv und method erben den Block aus dem Rahmen von `index.html`
  - keine Cookies, kein weiteres Skript
- **Ereignis „Signup“:** im bestehenden Handler nach `j.success`, auf allen Seiten mit Formular und im Cheat-Sheet-Fenster (`capture.js`).
  - Eigenschaften `page` (Pfad) und `utm_campaign` aus dem versteckten Feld
  - nie die E-Mail-Adresse
  - steht in `try`, ein Blocker stört die Anmeldung nicht
- **Datenschutzseite,** Abschnitt 6 „Cookies and web analytics (Plausible)“:
  - Anbieter Plausible Insights OÜ, Tartu
  - cookielos, keine personenbezogenen Daten, Hash mit täglich neuem Salz, Server in der EU
  - Zweck und das Signup-Ereignis
  - Rechtsgrundlage Art. 6 (1)(f)

### Teil 2, Landingpage /whales (PR #150)
- **Seite:** `whales/index.html`, gebaut von `scripts/whales_seite.py`.
  - **Oben:** h1 „the 8 kaspa numbers whales watch“, darunter „the october edition, read on 11 oct 2026. every number with its date and where it comes from.“
  - **Anmeldung:** eine einzige, „get the next edition every monday“ mit „the weekly kaspa numbers in one mail every monday, free, unsubscribe anytime.“
  - **Darunter:** alle 8 Zahlen sichtbar.
- **Woher die 8 Zahlen kommen:** Karussell vom 13.10.2026, also Edition 1 des Cheat Sheets mit den Daten vom 11.10.2026 (`scripts/cheat-sheet-probe.json`).
  - Frage, Zahl, Einheit und Datumszeile baut `cheat_sheet.karten()`, so bleiben sie gleich wie im Karussell.
  - Die einzige Abweichung: „about one in seven“ steht als „about 1 in 7“, weil auf der Website die Zahlregel gilt.
- **Herkunft je Zahl:**

  | Nr | Zahl | Herkunft auf der Seite |
  | --- | --- | --- |
  | 1 | 5.5% in der größten Wallet, 10 oct 2026 | counted by kaspa pulse from the public address, supply as of 5 oct 2026 |
  | 2 | 13.6% auf Börsen, 4 oct 2026 | source kaspalytics |
  | 3 | 50.7% seit einem Jahr unbewegt, 6 oct 2026 | source kaspalytics |
  | 4 | 293,978 Adressen ab 100 KAS, 4 oct 2026 | source kaspalytics |
  | 5 | nächste Reward-Senkung 4 nov (nur Datum, wie im Newsletter) | computed from the emission schedule |
  | 6 | 765x neue Coins gegen Gebühren, 3 sep bis 2 oct 2026 | fees source kaspalytics, new coins computed from the emission schedule |
  | 7 | 339 PH/s, Mittel 4 bis 10 oct 2026 | source kaspa rest api, 7 day mean computed by kaspa pulse |
  | 8 | 292,292 Covenant-Ausgaben seit 30 june, 9 oct 2026 | source kaspalytics |

- **Formular:** dasselbe Brevo-Formular wie auf der Startseite (`startseite.anmeldung`).
  - Liste #16 ist laut Brevo „Kaspa Pulse Subscribers“, #17 „PulseHawk Leads“.
  - Die UTM-Felder mit ids für `utm.js` sind drin, `utm.js` ist eingebunden.
  - Die vier UTM-Attribute sind in Brevo angelegt (nachgesehen, nichts geändert).
- **„paid“:** steht jetzt in MEDIEN in `scripts/utm.py` und `utm.js`. Ohne den Eintrag käme die Anzeige als „other“ an.
  - Dazu die Quelle `ig` mit Vorgabe `paid` in `utm.py`.
  - `utm.py --selftest` und `utm_fields.py --selftest` sind grün.
- **Kein zweites Ziel:**
  - keine Navigation, kein zweites Formular, kein `capture.js`
  - das Logo führt zur Startseite
  - unten nur Impressum und Datenschutz, beides Pflicht
  - Die Wache bricht ab bei mehr als einem Formular oder einem Link nach außen.
- **Kurzlink:** kaspapulse.com/whales ist ein Ordner mit `index.html`, wie die bestehenden Kurzlinks. Die Seite selbst ist das Ziel, eine Weiterleitung braucht es nicht.
- **noindex:** Die Seite ist für die Anzeige da, nicht für die Suche, und taucht nicht in der Sitemap auf.
- **Lieferweg nach Discord:** PR #149, Workflow `ops-paket.yml`. Er schickt eine Datei aus `berichte/` von Hand nach #moderator-only. Bisher gab es dafür keinen Weg, siehe unten.

## Prüfung

**Mobil zuerst:**

| Breite | Unterkante Anmeldeknopf | Höhe des Bildschirms |
| --- | --- | --- |
| 390 | 439 px | 844 px |
| 768 | 419 px | 1024 px |
| 1440 | 457 px | 900 px |

Kein seitliches Scrollen.

**LCP:**
- Aufbau: Netz gedrosselt (150 ms Latenz, 1.6 Mbit/s), CPU vierfach gedrosselt, gzip, 9 Läufe.
- Median 424 ms bei 390 und 432 ms bei 1440, der höchste Wert 448 ms.
- Damit weit unter 2 s. Es gibt keine Bilder, Archivo 900 wird vorgeladen.

**Kontrast:**
- 50 Textelemente geprüft, das niedrigste Verhältnis ist 8.9:1.
- Platzhalter im Feld 5.9:1.
- Alles über WCAG AA.

**Taste Skill (12af471):**
- Verlauf: erster Entwurf 8 FAIL / 3 WARN, nachher 4 FAIL / 3 WARN.
- **Behoben:**
  - Versprechen auf zwei Zeilen bei 390, 768 und 1440
  - die Frage je Karte als echte Überschrift statt kleiner Kopfzeile
  - das Versprechen bei 1440 groß über beide Spalten
  - Datums- und Herkunftszeilen 14 px
- **Bleibt:**
  - IBM Plex Mono und drei Schriften (Marke)
  - keine Bilder, kein Video und keine Bewegung: ein Ziel, LCP
  - Fließtext 14 px in den Datumszeilen
  - Ränder 196 und 219 px bei 1440: der Skill misst Textzeilen, die Karten reichen bis an den Rand

**Web Interface Guidelines,** Zeilen in `whales/index.html`:

| Datei:Zeile | Befund | Status |
| --- | --- | --- |
| whales/index.html:82 | E-Mail-Feld ohne `autocomplete`, mit Rechtschreibprüfung, Platzhalter ohne Muster | behoben, wie in #146 |
| whales/index.html:154 | `translate="no"` auf dem ganzen Fuß | behoben, nur noch an der Wortmarke (Zeile 73) |
| whales/index.html:6, 19 | `theme-color` und `color-scheme: dark` | in Ordnung |
| whales/index.html:25, 43 | Fokusrahmen und Hover am Knopf | in Ordnung |
| whales/index.html:53 | Zahlen mit `tabular-nums` | in Ordnung |
| whales/index.html:97 | Überschriften h1, dann h2 für Anmeldung und Karten | in Ordnung |
| whales/index.html (ganz) | kein Link zum Überspringen | bleibt, die Seite hat keine Navigation |

**Formular, im Browser:**
- Aufbau: `/whales/?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3`, Brevo abgefangen, keine echte Anmeldung.
- Brevo erhält `UTM_SOURCE=ig`, `UTM_MEDIUM=paid`, `UTM_CAMPAIGN=ad1-whales-v3`, `UTM_MEDIUM_RAW=paid`.
- Plausible erhält `Signup {page: "/whales/", utm_campaign: "ad1-whales-v3"}`.
- Die Bestätigung erscheint im Kasten.

**Plausible auf den anderen Seiten,** im Browser unter der echten Adresse aus den lokalen Dateien, Plausible abgefangen:
- Startseite: beide Formulare senden `Signup {page: "/", utm_campaign: "ad1-whales-v3"}`
- kaspa-mining mit `w44`: `Signup` mit `utm_campaign: "w44"`
- Cheat-Sheet-Fenster und Wochenseite ohne UTM: `"none"`
- 0 Cookies

**Prüfungen im Repo, alle grün:**
- whales_seite `--pruefen` und `--selbsttest`
- plausible `--pruefen` und `--selbsttest`
- utm, utm_fields, kurzlinks
- seo_seiten, seo_pruefung (0 Fehler), startseite `--pruefen`, cheat_sheet `--selbsttest`
- Secret-Scan

**Bilder:** `docs/whales/whales-390.png`, `-768.png`, `-1440.png`, je erstes Bild und ganze Seite.

**Nicht von hier prüfbar:**
- **Plausible:** plausible.io ist aus der Arbeitsumgebung gesperrt (Netzrichtlinie). Den Besuch im Dashboard und das echte Ereignis sieht nur Ben.
- **Test-Anmeldung:** Sie geht nur mit Bens Testadresse, selbst habe ich mich nicht angemeldet.

## PR-Nummern
- **#148:** Plausible auf allen Seiten, Signup, Datenschutz (Teil 1)
- **#150:** Landingpage /whales, `paid` in MEDIEN, dieser Bericht (Teil 2). Baut auf #148 auf.
- **#149:** Workflow `ops-paket.yml` für die Lieferung nach Discord

## Offene Fragen an Ben
1. **/whales ohne Schrägstrich:** GitHub Pages leitet `/whales` auf `/whales/` weiter. Nach meinem Wissen bleiben die UTM-Parameter dabei erhalten. Das prüfen wir beim Test-Signup. Gehen sie verloren, nimmt die Anzeige `https://kaspapulse.com/whales/?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3`.
2. **Edition 2:** Sollen die 8 Zahlen auf /whales mit Edition 2 des Cheat Sheets (Anfang November) mitwandern? `whales_seite.py` müsste dann statt der Probe die neue Edition lesen. Bis dahin steht dort die Oktober-Ausgabe mit ihren Daten.
3. **Wortliste:** „whales“ steht auf der Wortliste der Tagesgrafik. Auf /whales ist nur der Satz der Anzeige davon ausgenommen. Passt das so?
4. **Datenschutzseite:** Liest du den neuen Abschnitt 6 rechtlich gegen?

## Was Ben tun muss
1. **Mergen in dieser Reihenfolge:**
   1. #148 (Frist heute 18:00)
   2. #149 (Workflow-Datei)
   3. #150
2. **In Plausible, Website kaspapulse.com:**
   - **Ziel:** unter Goals ein Custom event `Signup` anlegen.
   - **Eigenschaften:** unter Custom properties `page` und `utm_campaign` freigeben.
   - **Anteil Signup je Besuch auf /whales:** Dashboard mit Filter Page ist `/whales/`. In Goal Conversions steht dann bei `Signup` die Conversion Rate.
3. **Betriebspfad Teil 1:** kaspapulse.com aufrufen, der Besuch erscheint in Plausible. Eine Test-Anmeldung mit deiner Testadresse löst `Signup` aus.
4. **Betriebspfad Teil 2:** Test-Anmeldung über den v3-Link mit deiner Testadresse. Danach in Brevo am Kontakt `UTM_CAMPAIGN=ad1-whales-v3` und `UTM_MEDIUM=paid` prüfen, Liste #16.
5. 📤 VON HAND: Ziel-URL in der Anzeige tauschen.

   ```
   https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3
   ```

6. Erst danach die Anzeige wieder starten.
