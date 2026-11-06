# Zcash Retro-Grant: CONTRIBUTING und NU7-Daten in pulsehawk/methods (6.11.2026)

Ben hat am 6.11. zwei Dinge für den Antrag zum Coinholder Retro Grant beauftragt (Frist Mo 9.11. 12:00): eine CONTRIBUTING.md nach den Regeln von librustzcash, und die Intervall-CSV als Lieferung unter MIT im Repo pulsehawk/methods (Frist für die Daten So 8.11. 18:00). Claude prüft, Ben merged.

## Was gemacht wurde

- **[pulsehawk/methods#2](https://github.com/pulsehawk/methods/pull/2), CONTRIBUTING.md.** Kein Draft, ohne Konflikt, bereit zum Merge.
  - Folgt der CONTRIBUTING.md von librustzcash und verlinkt sie.
  - Inhalt: Fehler melden, Vorschläge, Datenregeln, Selbsttest vor jedem PR, Git-Regeln (Merge, Branch, Review), Commit-Stil, Änderungen an Methoden und Formaten, Code-Stil.
  - Datenregeln: keine IPs, Hostnamen, Onion- oder I2P-Adressen, Wallet-Adressen, Schlüssel oder Zugangsdaten. Peers heißen `peer_N`, 64 Hex-Zeichen nur für Block- und Transaktions-Hashes.
  - Ein Prüfbefehl für `examples/` und `data/` gehört dazu. Er findet auf main und auf dem Daten-Branch nichts.
- **[pulsehawk/methods#3](https://github.com/pulsehawk/methods/pull/3), `data/zcash-nu7/`.**
  - `zcash-nu7-testnet-intervals-2026-10-18.csv`: Testnet, Höhen 4.465.026 bis 4.514.228, 4.10. 18:21:45 bis 18.10. 05:59:48 UTC, 49.202 Abstände. Byte-gleich mit der Datei auf pulsehawk.io.
  - `zcash-mainnet-nu7-intervals-2026-11-06.csv`: Mainnet, Höhen 3.543.405 bis 3.543.655, 6.11. 02:34:02 bis 05:13:14 UTC, die ersten 250 Abstände nach der Aktivierung. Gleicher Dateiname wie in pulsehawk-site PR #65.
  - `README.md` mit Formatzeile und `SHA256SUMS`. Das README oben im Repo verweist auf den Ordner.
- **Prüfungen:**
  - Die Höhen sind lückenlos, jeder Abstand ist die Differenz der Kopfzeiten, kein Abstand ist negativ.
  - `sha256sum -c` ist ok.
  - Der Prüfbefehl findet keine Adresse, keine IP und keinen Hostnamen.
  - `report_v1.py --selftest` besteht.
  - Der Secret-Scan `--baum` ist sauber.
- **LICENSE:** Die Datei liegt im Repo, MIT, „Copyright (c) 2026 pulsehawk“. Nicht geändert. Damit stehen die Daten unter MIT, das README des Ordners sagt das.

## Offene Fragen an Ben

1. Bleibt es bei MIT, mit „pulsehawk“ als Inhaber im Copyright?
2. Bleibt der Verweis auf den Zcash Code of Conduct in der CONTRIBUTING.md?
3. Die zwei alten Branches in pulsehawk/methods (`zugang-test`, `nu7-report-v1`) liegen noch. Ich darf dort keine Branches löschen.

## Was Ben tun muss

1. **Bis So 8.11. 18:00:** pulsehawk/methods#3 mergen (Daten).
2. **Bis Mo 9.11. 12:00:** pulsehawk/methods#2 mergen (CONTRIBUTING.md).
3. In pulsehawk/methods „Private vulnerability reporting“ einschalten (Settings, Code security). Die CONTRIBUTING.md verweist darauf.
