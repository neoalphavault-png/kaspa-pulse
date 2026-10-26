**Plausible und Landingpage /whales, Lieferung 26.10.2026**

Plattform kaspapulse.com und Instagram-Anzeige ad1-whales-v3. Claude prüft, Ben merged.

**Stand**
- **#148:** Plausible auf allen 42 Seiten, Ereignis Signup mit page und utm_campaign (nie die Adresse), Datenschutz ergänzt
- **#150:** /whales mit den 8 Zahlen vom 11 oct 2026, eine Anmeldung (Liste #16), UTM wie überall, paid in MEDIEN
- **Anmeldeknopf ohne Scrollen:** bei 390 x 844 an der Stelle 439 px
- **LCP und Kontrast:** LCP gedrosselt 0.43 s, Kontrast mindestens 8.9:1
- **Test im Browser:** Brevo erhält UTM_MEDIUM=paid und UTM_CAMPAIGN=ad1-whales-v3
- Bericht: berichte/2026-10-28-landingpage-whales.md

**Reihenfolge Merge**
1. #148, Frist heute 18:00
2. #149, Workflow für diese Lieferungen
3. #150

**In Plausible anlegen,** Website kaspapulse.com
1. Goals, Custom event, Name zum Kopieren:
```
Signup
```
2. Custom properties freigeben:
```
page
```
```
utm_campaign
```
3. Anteil Signup je Besuch auf /whales: Filter Page, Wert zum Kopieren, dann in Goal Conversions die Conversion Rate bei Signup:
```
/whales/
```

**Prüfung auf dem Betriebspfad**
1. kaspapulse.com aufrufen, der Besuch erscheint in Plausible
2. Test-Anmeldung mit deiner Testadresse über den v3-Link
3. In Brevo am Kontakt UTM_CAMPAIGN=ad1-whales-v3 und UTM_MEDIUM=paid prüfen, Liste #16
4. In Plausible erscheint Signup mit page /whales/

📤 VON HAND: Ziel-URL in der Anzeige ad1-whales-v3 tauschen
```
https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3
```

Falls die UTM-Werte im Test fehlen (Weiterleitung von /whales auf /whales/), diese URL nehmen:
```
https://kaspapulse.com/whales/?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3
```

Erst danach die Anzeige wieder starten.
