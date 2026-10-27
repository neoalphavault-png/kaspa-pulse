# Bericht SEO-Runde v2, Priorität B (Frist So 8.11.2026 18:00 Berlin)

Auftrag von Ben vom 27.10.2026 abends. Erledigt am 27.10.2026, vor der Frist.

## Was gemacht wurde
4. **kaspa-wallets.html**
   - **Vergleichstabelle** mit den Spalten Wallet, Platform, Self-custody, KCC-20 tokens, Official download, Latest version und Checked. Je Zeile steht ein Prüfdatum.
   - **KCC-20:** Bei keiner Wallet steht KCC-20 in den offiziellen Release-Notes, Stand 27.10.2026. Geprüft habe ich auf GitHub:

     | Wallet | geprüfter Stand |
     | --- | --- |
     | Kaspa NG | bis v2.0.1 |
     | Kaspium | bis v1.3.0 |
     | Kasware | Release-Notes auf GitHub |
     | KasVault | README, es gibt keine Releases |
     | OneKey | bis 6.6.3 vom 23.10.2026 |
     | Tangem | Android bis 6.5 vom 26.10.2026 |

     „angekündigt“ kam nirgends vor.
   - **Download-Quellen:** nur solche, die ich heute belegen konnte. Das sind die GitHub-Releases der Hersteller, kaspa-ng.org, der Chrome Web Store für Kasware, kasvault.io (verlinkt aus dem eigenen Repository) und Ledgers eigene Kaspa-Seite. Die Websites von OneKey, Tangem, Kaspium und Kasware waren aus der Arbeitsumgebung nicht erreichbar.
   - **H2 je Plattform:** Web, iOS, Android, Desktop und Hardware gab es schon. Die Tabelle heißt jetzt „All Kaspa wallets at a glance“.
   - **Drei neue FAQ:** „Which wallets support Kaspa?“, „Which Kaspa wallets support KCC-20 tokens?“ und „What is the best Kaspa wallet?“, alphabetisch und ohne Werturteil.
   - **Bestehendes bleibt:** der Affiliate-Link mit Kennzeichnung, keine neuen. Der Link auf kaspa-web-wallet-safe.html stand schon im Web-Abschnitt und in der FAQ.
5. **Strukturierte Daten** in `scripts/seo_seiten.py`, damit auf allen 38 Unterseiten:
   - **WebPage, Article** mit dateModified und Bild, **BreadcrumbList** (Kaspa Pulse, dann die Seite).
   - **Dataset** auf den 4 Seiten mit eigener Datenreihe, je mit Methode, Zeitraum und, wo es die Datei gibt, dem Link auf die JSON-Rohdaten. CSV gibt es zu keiner Reihe.

     | Seite | Reihe |
     | --- | --- |
     | Hashrate | Tagesmittel |
     | Supply | Adressen nach Schwellen, JSON |
     | Covenants | Tagesreihe, JSON |
     | Weekly | Wochenzahlen, JSON |

   - **FAQPage** steht weiter auf 17 Seiten.
   - **Sitemap:** lastmod zieht wie bisher bei jeder Textänderung nach.
   - Warum die Search Console bisher nichts erkennt: Google zeigt FAQ-Rich-Results seit 2023 nur noch für Behörden- und Gesundheitsseiten. Breadcrumbs, Article und Dataset wertet die Search Console dagegen aus.
6. **Aufräumen**
   - **/balance:** leitet jetzt auf kaspa-wallets.html weiter, per meta refresh 0 und canonical, mit noindex und nicht in der Sitemap. GitHub Pages kann keinen echten 301, Google wertet diese Form wie eine dauerhafte Weiterleitung.
   - **kaspa-mining.html:** ausgebaut statt zusammengelegt. Merged Mining ist eine andere Suchabsicht, beide Seiten würden sich schwächen. Die Seite war nicht zu kurz, aber alle ihre Zahlen lud erst ein Skript im Browser, für Google standen dort Striche. Neu sind:
     - eine Tabelle „Kaspa mining in numbers“ mit Reward je Block, neuen KAS je Tag, nächster Stufe, Netz-Hashrate und KAS je Tag für 1 TH/s, jeweils mit Datum und computed oder source
     - ein Kurz-Fakt
     - die FAQ „How much does a Kaspa miner earn per day?“ mit Rechnung
     - „today“ ist aus dem festen Text raus

     Die Werte erneuert `seiten_zahlen.py` täglich, sobald Ben #171 gemergt hat.
7. **Lighthouse mobil**, gemessen am 27.10.2026, Ziel LCP unter 2,5 s und CLS unter 0,1

   | Seite | vorher live | nachher lokal |
   | --- | --- | --- |
   | Startseite | 100, LCP 1.1 s, CLS 0.02 | unverändert, nicht im Rahmen |
   | kaspa-halving | 91, LCP 2.0 s, **CLS 0.17** | LCP 2.3 s, CLS 0.001 |
   | merged-mining | 100, LCP 1.1 s, CLS 0.018 | LCP 2.1 s, CLS 0 |
   | entity-x | 97, LCP 1.3 s, CLS 0.098 | LCP 2.2 s, CLS 0.091 |
   | kaspa-data-sources | 100, LCP 1.0 s, CLS 0.004 | LCP 2.0 s, CLS 0 |

   - **Ursache des CLS:** der Schrifttausch. Die H1 der Unterseiten steht auf Gewicht 700 und nimmt damit Archivo 800. Vorab geladen wurde aber nur die 900. Die Ersatzschrift läuft schmaler, also brach die H1 anders um und schob die Seite nach unten.
   - **Lösung im Rahmen (`rahmen.css`, `rahmen.py`):**
     - eine Ersatzschrift „Archivo Ersatz“ aus Arial fett mit `size-adjust` 103,4 % für 800 und 110 % für 900
     - Preload von Archivo 800 und IBM Plex Sans 400 auf allen Unterseiten
   - **Lokal gegen live:** Die lokalen LCP-Werte liegen höher als live, weil der lokale Server ohne Kompression und ohne CDN ausliefert. Die Werte auf der echten URL messe ich nach dem Merge.

## Nebenbefund, schon live mit #172
KCC-1, KCC-2 und KCC-20 stehen seit dem 21.10.2026 im Repository kaspanet/kccs auf Final, belegt durch die Commits #39, #40 und #41. Smart Contracts, Token-Standard und Toccata nannten noch den Stand vom August. #172 hat das korrigiert und ist selbst gemergt (9e8c7c1).

## Prüfung
- Selbsttests grün: `seiten_zahlen` (Mining dazu), `seo_seiten` (Article, Breadcrumb und Dataset dazu), `rahmen`.
- Textwache über alle geänderten sichtbaren Texte.
  - Behoben: „at the moment“ auf der Mining-Seite und „now“ in der Description der Toccata-Seite.
  - Die übrigen Treffer sind JSON-Schlüssel oder die Strich-Platzhalter in Tabellen, die es schon vorher gab.
- Schema auf allen Seiten gültig: 57 JSON-LD-Blöcke.
- 390 und 1440 px für Wallets, Mining und Token-Standard ohne seitliches Scrollen.
- Die Mining-Tabelle hat jetzt zwei Spalten, die Grundlage steht klein unter dem Wert, so passt sie bei 390 px.

## PR-Nummern
- #172, KCC-20 final, selbst gemergt
- #171, Workflow `seiten-zahlen.yml` mit Halving und Mining, wartet auf Ben
- #173, Priorität B, selbst gemergt

## Selbst-Merge und Abnahme
- **#173 als a64b399, 27.10.2026.** Abnahme auf der echten URL:
  - Die Wallet-Tabelle mit KCC-20-Spalte ist live.
  - BreadcrumbList steht auf allen geprüften Unterseiten, Dataset auf Hashrate und Supply.
  - Der Preload von Archivo 800 ist überall drin.
  - /balance leitet auf kaspa-wallets.html.
  - Lighthouse mobil live: Halving 100 Punkte, CLS 0.001, entity-x CLS 0.085, alle fünf Seiten im Ziel.

## Offene Fragen an Ben
1. **/balance:** Ich leite auf die Wallet-Seite, weil die Suche nach einem Kontostand am ehesten dorthin passt. Wenn /balance früher etwas anderes war, sag mir das Ziel.
2. **Rich Results Test und Neu-Indexierung:** Die Google-Werkzeuge sind von hier nicht erreichbar, und für die Search Console habe ich keinen Zugang. Die Liste der URLs steht in der Lieferung.
3. **Wallet-Seiten der Hersteller:** Sie waren von hier nicht erreichbar. Wenn du willst, prüfe ich die Download-Quellen von OneKey, Tangem und Kaspium noch einmal von einem Rechner mit freiem Netz.

## Was Ben tun muss
- #171 mergen.
- Die geänderten URLs in der Search Console zur Indexierung einreichen.
- Für je einen Seitentyp den Rich Results Test laufen lassen.
