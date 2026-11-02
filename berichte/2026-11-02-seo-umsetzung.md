# Bericht 2.11.2026: SEO-Umsetzung nach Bens Entscheidungen

Bezug: SEO-Befund vom 2.11.2026 (#238). Punkt 1 (/whales bleibt noindex) ist mit #237 erledigt. Dieser PR enthält die Punkte 2 bis 4.

## 2. Titel und Beschreibungen, Bens Wahl, wortgleich eingesetzt
| Seite | Titel | Zeichen | Beschreibung | Zeichen |
| --- | --- | --- | --- | --- |
| kaspa-wallets.html | Kaspa Wallet Comparison for Web, Phone, Desktop, Hardware | 57 | Pick a Kaspa wallet from one table. Platform, self-custody, KCC-20 tokens and official download for 8 wallets, checked on 6 October 2026. | 137 |
| kaspa-data-sources.html | Kaspalytics Explained, What Each Kaspa Chart Shows | 50 | Kaspalytics is a free chart set for Kaspa. Which chart answers which question, next to the explorer and REST API, with 3 checks for any chart. | 142 |
| kron.html | Kron DEX on Kaspa, Launchpad and Locked Liquidity Explained | 59 | Kron is a DEX and token launchpad on Kaspa layer 1. How the bonding curve and locked liquidity work, and 3 checks before you trade a Kron token. | 144 |
| kaspa-tvl.html | Kaspa TVL Explained, Kasplex and Igra on DefiLlama | 50 | Kaspa layer 1 holds no TVL by design, all of it sits on Kasplex and Igra. How DefiLlama counts it and 3 traps in reading the number. | 132 |
| kaspa-supply.html | Kaspa Supply, How Many KAS Exist and Who Holds Them | 51 | How many KAS exist, the max supply of about 28.7 billion and how many addresses hold 100 KAS or more, every number with its date and source. | 140 |

- **og und twitter:** og:title, og:description, twitter:title und twitter:description schreibt `seo_seiten.py` aus title und description, sie sind also gleich. Das Schema (WebPage, Article) trägt dieselben Texte.
- **Sitemap:** lastmod der 5 Seiten steht auf 2026-11-02, dem Merge-Datum. Dazu sind in `data/seiten-stand.json` Datum und Zeitpunkt der 5 Seiten auf den Lauf gesetzt. dateModified und „page last updated“ folgen damit.
- **SEO-Prüfung:** `scripts/seo_pruefung.py` verlangte bisher 140 bis 155 Zeichen für die Beschreibung. Bens Regel vom 2.11. heißt „höchstens 155“. Die Obergrenze stoppt weiter. Unter 140 gibt es jetzt nur eine Warnung, denn die freigegebenen Texte für kaspa-tvl (132) und kaspa-wallets (137) sind kürzer.

## 3. kaspa-tvl.html, datierte Zahl statt „today“
- **Neue Überschrift:** Statt „Total value locked on Kaspa · today“ steht der Block jetzt im HTML: „Total value locked on Kaspa · 2 November 2026“, **$806K**, „Kasplex and Igra combined on 2 November 2026, Kaspa layer 1 holds none of it, source defillama“.
- **Quelle:** `seiten_zahlen.py` (Marke `tvl-zahl`) liest jeden Morgen um 06:17 UTC DefiLlama (`api.llama.fi/v2/chains`) und schreibt Gesamt, Kasplex, Igra und den Anteil an aller DeFi mit dem Datum des Laufs.
- **Ohne DefiLlama:** Ist DefiLlama nicht erreichbar, nimmt der Lauf den letzten Tageswert aus `data/number-of-day-log.json` mit dessen Datum. Der stammt ebenfalls von DefiLlama, nur die Summe ist dort geloggt, Kasplex und Igra stehen dann als Strich da.
  - Der Stand in diesem PR ist so entstanden, weil DefiLlama aus der Sitzung nicht erreichbar war. Der Lauf am Di 3.11. füllt die Aufteilung.
- **Skript und Hinweis:** Das Skript auf der Seite überschreibt den Block nicht mehr. Es füllt nur noch die Vergleichstabelle weiter unten. Der Satz „Nothing here is hardcoded“ ist ersetzt durch „read from DefiLlama once a day and written into this page with their date“.

## 4. newsletter/*.html noindex, nofollow
- **Vorhandene Dateien:** Alle 8 Dateien (2026-09-14 bis 2026-11-02) tragen `<meta name="robots" content="noindex, nofollow">` direkt nach charset.
- **Neue Ausgaben:** Eine eigene Vorlagendatei gibt es nicht. Die Montagsroutine baut jede Ausgabe aus der vorigen und ruft dann `scripts/newsletter_issue.py set` auf. `set` schreibt das Tag jetzt in jede Ausgabe, wo es fehlt, und ist wiederholbar. So trägt auch jede künftige Ausgabe noindex.
- **VIDEO_URL:** Der Platzhalter bleibt in der Kopie von 2026-09-14, die Seite ist aber nicht mehr indexierbar und gibt keine Links weiter.

## Prüfung
- **Selbsttests grün:** seiten_zahlen (3 neue Fälle für TVL), newsletter_issue (noindex), brevo_send, seo_seiten, seo_pruefung.
- **SEO:** `seo_seiten --pruefen` auf Stand. `seo_pruefung` gegen main ohne Fehler, mit 2 Warnungen zur Länge der Beschreibung.
- **Newsletter:** `newsletter_issue check` ist für 7 von 8 Dateien ok. 2026-09-14 meldet wie bisher „keine frühere Ausgabe“, weil es die erste Datei im Ordner ist. Das ist älter als dieser PR.
- Keine Workflow-Dateien, keine Schlüssel in Dateien.
