# Bericht 2.11.2026: SEO-Befund aus der Search Console

Auftrag von Ben vom 2.11.2026. Punkt 1 als eigener PR #237, Punkt 2 und 3 hier. Punkt 2 bitte nicht mergen, bevor die Prüfung durch ist. Die Titel und Beschreibungen sind nur Vorschläge, auf den Seiten ist nichts geändert.

## 1. /whales
- **a) noindex bleibt, es gibt einen dokumentierten Grund.** In `scripts/whales_seite.py` steht seit dem 26.10.2026 (Ben): „noindex: die Seite ist für die Anzeige da, nicht für die Suche.“
  - Dahinter steht die Idee der Seite: Sie löst das Versprechen der Anzeige ad1-whales ein und ist kein Suchziel.
  - Seit Edition 2 zeigt sie nur 2 der 8 Zahlen. Eine Suche, die dort landet, findet also absichtlich wenig Inhalt.
  - Soll /whales doch in die Suche, ist das eine Zeile in `whales_seite.py`. Danach kommen b) und c) mit.
- **b) Sitemap:** nicht eingetragen, solange noindex gilt. Eine noindex-Seite in der Sitemap meldet die Search Console als Fehler („Eingereichte URL als noindex markiert“), und `seo_seiten.py` meldet sie selbst als „keine öffentliche Seite“.
- **c) Interne Links** von Startseite, kaspa-halving.html und entity-x.html: noch nicht gesetzt, aus demselben Grund. Ein Link auf eine noindex-Seite schadet nicht, bringt der Suche aber nichts.
- **d) Weiterleitung:** `https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid&utm_campaign=ad1-whales-v3` antwortet mit **301** auf `https://kaspapulse.com/whales/?utm_source=...`, die UTM-Werte bleiben erhalten. `/whales/` liefert 200 (geprüft 2.11.2026).
  - Canonical war schon `/whales/`. Kein interner Link und keine Sitemap nennt /whales ohne Schrägstrich.
  - Neu in #237: Auch die dokumentierte Ziel-URL der Anzeige steht mit Schrägstrich. Wenn du die Anzeige ohnehin anfasst, trag dort `/whales/` ein, das spart die Weiterleitung.

## 2. Titel und Beschreibung, je zwei Vorschläge
Regeln: Titel höchstens 60 Zeichen, Beschreibung höchstens 155, die Suchanfrage am Anfang des Titels, eine Zahl oder ein Nutzen in der Beschreibung. Alle Vorschläge sind geprüft mit `content_wache.text_verstoesse` und `karussell.text_pruefen`: keine Gedankenstriche, Doppelpunkte oder Pfeile, kein now oder live, keine Kursziele, keine andere Chain als Vergleich. Zahlen tragen ihr Datum.

### kaspa-wallets.html, 1 Klick bei 1.107 Impressionen, Anfrage „kaspa wallet“ 203 / 0
Bisher: „Kaspa Wallets for Web, iOS, Android, Desktop and Hardware“. Die Beschreibung endet mit „Trezor does not support Kaspa today“, und „today“ ist ein Echtzeitwort.
- **A** (48 / 139): „Kaspa Wallet Guide, 8 Wallets Checked One by One“
  „Which Kaspa wallet for web, phone, desktop or hardware. 8 wallets checked on 6 October 2026, with self-custody and KCC-20 support for each.“
- **B** (57 / 137): „Kaspa Wallet Comparison for Web, Phone, Desktop, Hardware“
  „Pick a Kaspa wallet from one table. Platform, self-custody, KCC-20 tokens and official download for 8 wallets, checked on 6 October 2026.“

### kaspa-data-sources.html, 5 / 654, Anfrage „kaspalytics“ 377 / 4
Bisher: „Kaspalytics and Other Kaspa Data Sources Side by Side“
- **A** (50 / 152): „Kaspalytics Explained, What Each Kaspa Chart Shows“
  „Kaspalytics is the deepest free chart set for Kaspa. Which chart answers which question, next to the explorer and REST API, with 3 checks for any chart.“
- **B** (51 / 143): „Kaspalytics vs Kaspa Explorer, Which Source to Open“
  „Supply aging, exchange holdings and address buckets on Kaspalytics, single transactions on the explorer. Read daily by us since 27 August 2023.“

### kron.html, 4 / 418, Anfrage „kron dex“ 28 / 0 in 7 Tagen
Bisher: „Kron Kaspa DEX and Launchpad, How It Works and What to Check“
- **A** (59 / 144): „Kron DEX on Kaspa, Launchpad and Locked Liquidity Explained“
  „Kron is a DEX and token launchpad on Kaspa layer 1. How the bonding curve and locked liquidity work, and 3 checks before you trade a Kron token.“
- **B** (57 / 148): „Kron DEX Explained, How the Kaspa Layer 1 Launchpad Works“
  „No presale, a bonding curve and liquidity locked for good. What Kron runs on Kaspa layer 1, checked on 6 October 2026, and 3 numbers to check first.“

### kaspa-tvl.html, 5 / 277
Bisher: „Kaspa TVL on DefiLlama, Kasplex and Igra Explained“
- **A** (50 / 132): „Kaspa TVL Explained, Kasplex and Igra on DefiLlama“
  „Kaspa layer 1 holds no TVL by design, all of it sits on Kasplex and Igra. How DefiLlama counts it and 3 traps in reading the number.“
- **B** (56 / 142): „Kaspa TVL, Where the Value Locked on Kaspa Actually Sits“
  „The split of Kaspa TVL between Kasplex and Igra, read from DefiLlama, why layer 1 shows none and 3 traps to avoid before you quote the number.“
- **Hinweis außerhalb des Auftrags:** Die Seite selbst schreibt „Total value locked on Kaspa · today“ und lädt die Zahl beim Öffnen. „today“ ist nach unseren Regeln ein Echtzeitwort, und ohne Skript sieht Google dort keine Zahl. Eine datierte Zahl im HTML über seiten_zahlen.py wäre der nächste Schritt.

### kaspa-supply.html, 5 / 259
Bisher: „Kaspa Wallet Holders and Addresses, Supply and Max Supply“
- **A** (51 / 140): „Kaspa Supply, How Many KAS Exist and Who Holds Them“
  „How many KAS exist, the max supply of about 28.7 billion and how many addresses hold 100 KAS or more, every number with its date and source.“
- **B** (56 / 144): „Kaspa Max Supply, Circulating KAS and Holders by Balance“
  „Over 96% of the roughly 28.7 billion KAS was mined by 2 November 2026. Circulating supply, max supply and holders by balance, dated and sourced.“
- **Hinweis:** In B steht eine Zahl mit Datum, das veraltet. Fällt die Wahl auf B, zieht seiten_zahlen.py die Beschreibung mit, wie es das schon mit dem Kurz-Fakt tut.

## 3. Die 9 nicht indexierten URLs, aus dem Repo gesehen
Die Search Console nennt die URLs nicht. Hier steht, was das Repo hergibt.

**noindex, 2 bei Google:**
- **/whales/:** gewollt, siehe Punkt 1.
- **Wahrscheinlich die zweite: /balance**, `balance/index.html`, „noindex, follow“ mit meta refresh 0 und canonical auf kaspa-wallets.html. Gewollt und dokumentiert: SEO-Runde v2, Ben 27.10.2026, #173. Die Adresse lieferte vorher 404 und ist bei Google bekannt, nicht in der Sitemap.
- **Weitere noindex-Seiten im Repo, alle gewollt:**
  - impressum.html und datenschutz.html, Pflichtseiten, aus jedem Fuß verlinkt.
  - utm-test.html, Testseite, „noindex, nofollow“, nirgends verlinkt.
  - die Kurzlinks discord/, ig/, nl/, story/, threads/, x/, yt/: meta refresh, „noindex, nofollow“, nicht verlinkt.
  - Impressum und Datenschutz könnten bei Google statt /balance als zweite noindex-Seite zählen. Gewollt sind alle drei.

**Weiterleitungen, 3 bei Google:** Aus dem Repo kommen in Frage:
- /whales, 301 auf /whales/
- /balance, meta refresh auf kaspa-wallets.html
- die Kurzlinks oben, meta refresh
- dazu die Varianten von GitHub Pages: http auf https und www auf ohne www

Welche drei es sind, zeigt nur die Liste in der Search Console.

**404, 1 bei Google:**
- **Sitemap und interne Links:** Keine URL aus der Sitemap (41 Einträge) und kein interner Link einer Seite führt ins Leere. Geprüft sind alle absoluten und relativen `href` und `src` aller HTML-Dateien.
- **Einziger Fund:** Zwei Newsletter-Archivseiten, `newsletter/2026-09-14.html` und `newsletter/2026-11-02.html`, tragen den Platzhalter `href="VIDEO_URL"`. Auf der Website wird das zu `/newsletter/VIDEO_URL`, also 404.
  - Die Seiten sind die Mail-Vorlagen der Montagsroutine. Keine Seite verlinkt auf sie, sie sind nicht in der Sitemap.
  - Der Platzhalter ist gewollt, die Mail selbst bekommt den Link erst beim Versand (`brevo_send.py` stoppt ohne ihn). Nur die Kopie im Repo behält ihn.
  - Vorschlag: Die Kopie nach dem Versand mit dem echten Link überschreiben oder `newsletter/` auf noindex setzen. Die Dateien gehören zur Montagsroutine, deshalb hier nur der Vorschlag.
- **Früherer Kandidat:** /balance lieferte bis zum 27.10. 404. Kennt Google den alten Stand noch, kann der 404 auch daher kommen.

**gecrawlt, nicht indexiert, 3:** Aus dem Repo nicht zu bestimmen. Kandidaten sind die Wochenseiten unter week/ (neu jeden Montag) und archive/.

## Was Ben tun muss
- Entscheiden, ob /whales in die Suche soll. Dann setze ich a) bis c) in einem PR um.
- Für Punkt 2 je Seite A oder B wählen. Danach setze ich sie ein.
- In der Search Console die Listen „Weiterleitung“, „noindex“ und „404“ öffnen und mir die URLs nennen, falls die Zuordnung oben nicht passt.

<!-- discord -->
**SEO-Befund 2.11.2026**
- **/whales:** noindex bleibt, das ist dokumentiert (whales_seite.py, 26.10.: für die Anzeige, nicht für die Suche). Sitemap und Links folgen erst, wenn du es anders willst. /whales ohne Schrägstrich geht per 301 auf /whales/, die UTM bleiben. PR #237.
- **Titel und Beschreibung:** je 2 Vorschläge für wallets, data-sources, kron, tvl und supply, alle innerhalb der Längen und Textregeln. Noch nicht eingesetzt.
- **Nicht indexiert:** zweites noindex ist sehr wahrscheinlich /balance, gewollt seit 27.10. Kein Link aus Sitemap oder Seiten führt auf 404. Einziger Fund ist der Platzhalter VIDEO_URL in zwei Newsletter-Kopien im Repo.
- **Bericht:** berichte/2026-11-02-seo-befund.md
<!-- teil -->
📤 VON HAND
- **/whales in die Suche, ja oder nein?** Bei ja setze ich noindex, Sitemap und Links in einem PR um.
- **Titel:** je Seite A oder B wählen, die Liste steht im Bericht.
<!-- /discord -->
