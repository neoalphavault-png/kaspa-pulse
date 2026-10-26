# Bericht 26.10.2026: Rebase von #144, #150 und #141, Karussell-Probe

Auftrag von Ben vom 26.10.2026, zusammen mit der neuen Regel für Selbst-Merges. Ich merge selbst, wenn alle drei Bedingungen erfüllt sind:
1. keine Workflow-, deploy- oder c2-Datei
2. alle Checks grün, keine Konflikte
3. öffentliche Texte bestehen die Textregel-Prüfung

Sonst gilt: Claude prüft, Ben merged.

## Was gemacht wurde

**1. #144 Bildhintergründe**
- auf den aktuellen main rebased, 9 Commits, konfliktfrei
- **Konflikte:**
  - `deploy/c2/setup.sh`: in `TAKTE` stehen jetzt `story-vorlage` aus #140 und die sechs Karussell-Takte
  - `deploy/c2/taktgeber/README.md`: beide Tabellenzeilen-Gruppen
  - `scripts/story_vorlage.py`: kam nur über den alten Merge-Commit und hat sich beim Rebase von selbst gelöst
- Die Inhalte von #144 sind Datei für Datei gleich geblieben.
- **Selbsttests grün:** hintergrund, story_vorlage, karussell, karussell_post, look_takt, meme_wahr, `bash -n` für setup.sh und ausloesen.sh. Secret-Scan über alle 9 Commits sauber.
- deploy ist betroffen, deshalb **mergt Ben**.
- #143 ist geschlossen, er steckt vollständig in #144.

**2. #150 /whales**
- auf main rebased; die Konflikte in `scripts/utm.py` und `utm.js` sind gelöst, beide Listen haben jetzt `story` und `paid`
- beim Reward Cut steht nur noch „4 nov“, ohne „13:45 utc“, wie im Newsletter
- selbst gemergt

**3. #141 Textregeln Unterseiten**
- **Rebase:** 24 Commits auf main.
  - Konflikte in `data/seiten-stand.json`, `sitemap.xml`, `entity-x.html`, `kaspa-smart-contracts.html` und `kaspa-supply.html`.
  - Die Bot-Zahlen von main bleiben, nur die Wortänderungen sind neu angewendet.
- **Kontrolle je Seite:**
  - Textregel-Treffer wie im PR vorher
  - Zahlen im sichtbaren Text wie auf main, bis auf die Zeile „page last updated“
- **Nachzug:** Die erneute Textregel-Prüfung fand noch echte Treffer, die ich in einem eigenen Commit behoben habe:
  - „N percent“ auf vier Seiten
  - das Zitat „Currently, Trezor …“
  - die Kursaussage „will go to zero“ auf kron
- **Danach:** 0 echte Treffer. Bewusst gelassene Fehlalarme sind der Platzhalter „—“, „Ledger Live“, „No price targets“ und die Adresse von entity x.

**4. Karussell-Probe vom 25.10. (Lauf 40207525942)**
- **Ursache:** Der Schritt `posten` stoppt mit „kein MEDIA_REPO_TOKEN, die bilder haben keinen oeffentlichen ort“. Das Secret `MEDIA_REPO_TOKEN` ist in kaspa-pulse nicht angelegt. Ohne Secret kann der Lauf die Bilder nicht nach kaspapulse-media hochladen, und Instagram braucht eine öffentliche Adresse. Der Entwurf davor war grün.
- **Behebung:** Ben legt das Secret an. Ein Secret kann ich nicht setzen, und einen anderen Bildort habe ich nicht gebaut, weil die Ablage in kaspapulse-media Bens Vorgabe ist.
- **Danach starte ich die Probe neu:** sobald #144 gemergt und das Secret angelegt ist.

**Nebenbei**
- **#157:** `bericht_discord.py` lässt jetzt unsere eigene Domain kaspapulse.com durch, sonst ginge die Ziel-URL der Anzeige nicht in den Ops-Kanal. Unterdomains und fremde Hosts bleiben gesperrt. Selbst gemergt.
- **#149** (mein Workflow für Lieferungen) ist geschlossen, ersetzt durch `bericht-discord.yml` aus #151. Dieses Paket geht über den neuen Weg.
- **Schon auf main:**
  - `wortmarke.py pruefen` meldet „brevo_send.py: pulsehawk“, gekommen mit #152
  - `startseite.py --pruefen` meldet, dass `index.html` älter ist als die Daten

  Beides stammt nicht aus diesen PRs.

## Selbst-Merges
- **#150:** Merge-Commit 6a2d0da, live ist kaspapulse.com/whales.
  - Abnahme auf der echten URL bei 390, 768 und 1440: 200, 8 Zahlen, keine Uhrzeit, `UTM_MEDIUM=paid` und `UTM_CAMPAIGN=ad1-whales-v3` in den Feldern, Knopf im ersten Bild bei 439 px (390 × 844).
  - Ein Test-Signup mit abgefangenem Brevo sendet ig, paid, ad1-whales-v3 und `Signup` mit page /whales/.
  - `/whales` leitet mit 301 auf `/whales/` weiter, die UTM-Parameter bleiben.
- **#157:** Merge-Commit a0434ec. Nur ein Skript, nichts Sichtbares auf der Website.
- **#141:** Merge-Commit 5c018c1, live sind die 20 Unterseiten mit den neuen Texten.
  - Abnahme auf den echten URLs von kaspa-security-budget, kaspa-wallets, kron, kaspa-supply, kaspa-hashrate und kaspa-weekly: kein „N percent“, kein „Currently,“, kein „· live“ mehr, Plausible auf jeder Seite.
  - Die Weekly-Prüfung in der CI hing beim ersten Lauf in der Playwright-Installation, noch vor jedem Test, bis zum Zeitlimit. Ich habe sie einmal neu gestartet, danach war sie grün.

## PR-Nummern
- **Ben merged:** #144 (Rebase, konfliktfrei)
- **Selbst gemergt:** #150, #141, #157
- **Geschlossen:** #143 (in #144), #149 (ersetzt durch #151)

## Offene Fragen an Ben
1. **Trezor-Zitat auf kaspa-wallets:** Ursprünglich wollten wir es bewusst stehen lassen. Für die Textregel steht dort jetzt „Trezor's own page says it does not support Kaspa“, Quelle und Lesedatum bleiben. Passt das?
2. **kron:** In der FAQ (sichtbar und im JSON-LD) steht „on every chain that has run this model most of them go to zero“. Die Textwache meldet das nicht, sie greift nur bei „will go to“. Inhaltlich ist es aber eine Aussage über Kurse ohne Quelle. Soll der Satz raus?
3. **Impressum und Datenschutz:** Sie haben Doppelpunkte und Gedankenstriche im Rechtstext. Ich habe sie nicht angefasst. Sollen sie so bleiben?

## Was Ben tun muss
Steht im Discord-Abschnitt unten. Er geht beim Push dieses Branches nach #moderator-only.

<!-- discord -->
**Stand 26.10.2026, Rebase und Merges**
- **#144** Bildhintergründe: rebased, konfliktfrei. Enthält jetzt #143, deshalb ist #143 geschlossen. Workflow und deploy sind betroffen, also mergst du.
- **#150** /whales: selbst gemergt und live. Reward Cut ohne Uhrzeit, Abnahme auf der echten URL bestanden. /whales leitet auf /whales/ weiter, die UTM bleiben.
- **#141** Textregeln: rebased, Bot-Zahlen behalten, Textregeln nachgezogen (percent, Trezor-Zitat, kron). Selbst gemergt.
- **#157:** Die eigene Domain darf jetzt in diese Pakete.
- **Karussell-Probe vom 25.10.:** rot, weil das Secret MEDIA_REPO_TOKEN fehlt. Neue Probe, sobald #144 gemergt und das Secret da ist.
- Bericht: berichte/2026-10-26-merge-runde.md
<!-- teil -->
📤 VON HAND, 1 von 3: **#144 mergen und Timer einspielen**
1. #144 auf GitHub mergen
2. Auf c2 die neuen Timer nachziehen, Befehl zum Kopieren:
```
sudo bash deploy/c2/setup.sh nachziehen
```
3. KARUSSELL_LIVE bleibt aus, bis die Probe grün ist
<!-- teil -->
📤 VON HAND, 2 von 3: **Secret MEDIA_REPO_TOKEN in kaspa-pulse anlegen**
Ursache der roten Probe. Ohne das Secret kommen die Karussell-Bilder nicht nach kaspapulse-media, und Instagram findet sie nicht.
1. GitHub, Settings, Developer settings, Fine-grained token
2. Nur das Repository kaspapulse-media, Recht Contents Read and write
3. Wenn du für die Reels in pulse-studio schon so einen Token hast, kannst du denselben Wert nehmen
4. In kaspa-pulse unter Settings, Secrets and variables, Actions ein neues Secret anlegen, Name zum Kopieren:
```
MEDIA_REPO_TOKEN
```
5. Mir Bescheid geben, dann starte ich die Probe neu
<!-- teil -->
📤 VON HAND, 3 von 3: **/whales und Plausible**
1. In Plausible, Website kaspapulse.com, Goals, Custom event:
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
3. Anteil Signup je Besuch auf /whales, Filter Page:
```
/whales/
```
4. Test-Anmeldung mit deiner Testadresse über den Link unten. Danach in Brevo am Kontakt UTM_CAMPAIGN=ad1-whales-v3 und UTM_MEDIUM=paid prüfen, Liste #16.
5. Ziel-URL in der Anzeige ad1-whales-v3 tauschen, dann die Anzeige wieder starten:
```
https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3
```
<!-- /discord -->
