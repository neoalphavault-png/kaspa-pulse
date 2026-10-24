# Bericht 24.10.2026: Textregeln auf den Unterseiten

Branch `fix/textregeln-unterseiten`, eigener Text-PR von main nach #134 (Ben, 24.10.2026). Eine Seite pro Commit.

## Was gemacht wurde
- **Was raus ist:** „right now“, „live“, „now“, „currently“, „real time“, Gedankenstriche, Doppelpunkte und Pfeile im Fließtext. Dazu einmal „percent“ (security-budget, „99 percent“ wird „99%“).
- **Was gleich bleibt:** Zahlen und Aussagen, nur die Formulierung ist neu. Ein Hilfsskript vergleicht vor und nach jeder Seite alle Zahlen im sichtbaren Text. Jede Seite hat dieselben Zahlen wie vorher.
- **Auch erfasst**, weil Leser sie sehen:
  - Titel und Beschreibungen im Kopf (zum Beispiel „Kaspa Hashrate Today, Live PH/s“ wird „Kaspa Hashrate Today in PH/s“)
  - die FAQ: Ich habe das JSON-LD geändert und den sichtbaren Block mit `seo_faq.py` neu gesetzt
  - die Texte, die das Seitenskript bei Erfolg oder Fehler einsetzt (zum Beispiel „live feed temporarily unavailable“ wird „kaspa api temporarily unavailable“, „source: api.kaspa.org“ wird „source api.kaspa.org“)
  - die Fußzeile „further reading:“ wird „further reading“
- **„live“ als Verb** („rules that live inside coins“, „where the TVL lives“) ist auch raus und heißt jetzt „sit“. Sonst schlägt die Echtzeit-Wache an, sobald der Satz in einen Post wandert.
- **20 Seiten, je ein Commit:**
  - kaspa-hashrate, kaspa-mining, kaspa-supply, entity-x (Bens vier)
  - kaspa-halving, kaspa-smart-contracts, kaspa-tvl, kaspa-wallets, kaspa-weekly, kron, kaspa-staking
  - kaspa-token-standard, kaspa-data-sources, merged-mining, kaspa-security-budget, kaspa-toccata
  - kaspa-covenants, for-builders, how-we-fund-this, kaspa-web-wallet-safe
  - zwei kleine Nachzüge für Kacheln in smart-contracts und staking
- **Seitendatum:** Weil sich der Text geändert hat, steht bei diesen Seiten „page last updated 24 October 2026“. `seo_seiten.py` hat das gesetzt, wie es der tägliche Lauf auch täte.
- **Geprüft:**
  - `seo_seiten.py --pruefen` und `--selbsttest`
  - `seo_pruefung.py --gegen origin/main` mit 0 Fehlern; zwei Beschreibungen und ein Titel waren zu lang und sind gekürzt
  - `rahmen.py --pruefen` und `wortmarke.py pruefen`
  - `entity_x_page.py --check` (Abgleich mit dem Browser, gestempelte Werte unberührt)
  - `covenants_page.py --check` und `seiten_zahlen.py --selbsttest`
  - Alle 20 Seiten im Browser bei 390 px: kein JavaScript-Fehler, keine Seite scrollt quer
  - Secret-Scan sauber

## Bewusst stehen gelassen
- **Platzhalter „—“ und „–“** in leeren Wertefeldern (69 Stellen): Sie stehen, bis das Skript den Wert einsetzt, und in den Tabellen von wallets und halving für „keine Angabe“. Kein Fließtext.
- **„Ledger Live“:** Produktname, drei Stellen auf kaspa-wallets.
- **Das Trezor-Zitat** „Currently, Trezor does not support Kaspa“ bleibt wörtlich, mit Quelle und Datum.
- **Der Doppelpunkt in der Adresse** von Entity X („kaspa:…“) gehört zur Adresse.
- **impressum.html und datenschutz.html:** Die Doppelpunkte sind Feldnamen („Email:“, „Register court:“), und „live data“ steht im Text der Datenschutzerklärung. Rechtstexte habe ich nicht umformuliert, siehe Frage 1.
- **utm-test.html:** interne Testseite mit noindex.
- **Die Meldungen des Anmeldekastens** („✓ almost there — check your inbox …“, „something went wrong — please try again“): Sie stehen gleich auf der Startseite und allen Unterseiten, die Startseite baut `startseite.py`. Siehe Frage 2.

## PR-Nummern
- dieser PR: #141 (geöffnet im Sammelfenster 24.10.2026, 16:00)
- Story-Vorlagen: #140
- Zusammenhang: #134 (Rahmen), #124 (Echtzeit-Wache)

## Offene Fragen an Ben
1. **Rechtsseiten:** Sollen Impressum und Datenschutz auch nach den Textregeln umformuliert werden? Die Feldnamen mit Doppelpunkt sind dort üblich, und eine Datenschutzerklärung würde ich nur mit deinem Okay umschreiben.
2. **Anmeldekasten:** Sollen die zwei Meldungen ohne Gedankenstrich kommen, zum Beispiel „✓ almost there, check your inbox …“? Das wäre ein eigener kleiner Commit über alle Seiten und `startseite.py`, damit Startseite und Unterseiten gleich bleiben.
3. **Aufgefallen, nicht geändert, weil es Aussagen sind:**
   - kaspa-wallets: Unten steht „That is the entire disclosure, no referral codes, no sponsored placements“. Auf derselben Seite steht aber der Affiliate-Link zum Ledger-Shop. Der Satz widerspricht der Seite, bitte entscheiden, wie er lauten soll.
   - kaspa-staking: „With roughly 320 PH/s securing the network“ steht ohne Datum, und am 24.10. waren es 386.9 PH/s. Soll ich ein Datum ergänzen oder die Zahl auf den Stand der Hashrate-Seite bringen?

## Was Ben tun muss
- PR prüfen, gern Commit für Commit, und mergen. Workflow-Dateien sind nicht betroffen.
- Die Fragen 1 bis 3 beantworten.
