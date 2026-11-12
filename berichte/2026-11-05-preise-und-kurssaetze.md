# Keine Preise öffentlich, keine kursnahen Sätze im Newsletter

Auftrag von Ben vom 5.11.2026, erledigt am 5.11.2026.

- Nur Seiten und `scripts/`, keine Workflows.
- Selbst-Merge nach der Regel vom 26.10., Commit `4583770` auf `main` über `automerge-claude.yml`.

## 1. for-builders.html ohne Preise

- **Raus aus dem Text:**
  - die Preiszeilen bei Pre-audit review („from 150 € per round“), Testnet load measurement („250 € … 450 € … 150 € per month“) und On-chain count („from 75 €“)
  - „Price depends on scope.“
  - „All prices are net, plus VAT where it applies.“
- **Raus aus dem schema.org:** das ganze `offers` am Service, also jedes Offer, `price`, `minPrice`, `priceCurrency` und `UnitPriceSpecification`. Die Service-Beschreibung nennt keine EUR mehr.
- **Kopf:** In description, og und twitter hieß es vorher „Fixed prices in euro, and your first look is free.“ Jetzt steht dort „Your first look is free, then ask for a quote.“ Der Kopf wurde mit `seo_seiten.py` nachgezogen. Sitemap und `data/seiten-stand.json` stehen auf 5.11.
- **Kaspa Pulse behält:**
  - „Get a free first look“ (zweimal, Link auf X)
  - Schritt 3 „Ask for a quote, get a written report.“ (DM auf X)
  - bei Pre-audit review „Ask for a quote, DM on X“ mit Link auf X
- **PulseHawk:** Testnet load measurement und On-chain count tragen je den Satz „Measurements for builders run under PulseHawk, our independent measurement brand.“ mit Link auf `https://pulsehawk.io/contact`.
  - Kein Falke, kein PulseHawk-Look, nur Text im Stil der Seite.
  - Die Beschreibungen der beiden Leistungen bleiben.
- **Stehen geblieben:** „EUR by bank transfer, KAS on request.“ in der FAQ (sichtbar und im FAQ-Schema). Das ist ein Zahlweg ohne Betrag. Soll das auch raus, ist es eine Zeile.

## 2. weekly_numbers.py, keine Wenn-dann-Sätze zum Kurs

Der Satz „a close above $0.035239 next week would put it back above both lines“ kommt aus keinem Skript. Die Montagsroutine schreibt ihn von Hand, im read und im Newsletter-Abschnitt „worth watching“. `weekly_numbers.py` liest den read und prüft ihn. Dort sitzt jetzt die Regel:

- **`kurs_wenn_dann(text)`** findet Sätze wie „a close above / below …“, „a weekly close back above …“, „if kaspa / it closes / holds …“ sowie einen Dollarbetrag mit „would“ im selben Satz.
- **`linienwert_satz(wochen)`** liefert den reinen Linienwert mit Quelle, zum Beispiel „the 50 week line sits at $0.035296, source kraken“. Der Stand der Wochenschlüsse ist der vom 5.11.
  - 50 Wochen ist das einfache Mittel, 21 Wochen das exponentielle.
  - Es ist dieselbe Rechnung wie `weekly_facts.py` und kaspa-weekly.html.
- **`read_input()`** stoppt ab einer Ausgabe mit Datum 8.11.2026 oder später (`KURS_REGEL_AB`), wenn der read einen solchen Satz enthält. Die Meldung nennt gleich den Ersatz mit beiden Linienwerten.
- **Alte Ausgaben** unter `newsletter/` sind nicht angefasst. Eine Ausgabe vor dem 8.11. liest sich weiter wie bisher.

Selbsttest `python3 scripts/weekly_numbers.py --selftest`: grün. Neu sind:

| Prüfung | Ergebnis |
| --- | --- |
| Fall 1: read „a close above $0.035239 next week would …“, Ausgabe 9.11. | stoppt, Meldung nennt „the 50 week line sits at $…, source kraken“ |
| Fall 1, derselbe Satz in der Ausgabe 2.11. | läuft wie bisher |
| Fall 2: read „the 50 week line sits at $0.035239, source kraken. the 21 week line …“, Ausgabe 9.11. | geht durch |
| „if kaspa closes above …“, „a weekly close back above …“, „at $0.04 the close would …“ | erkannt |
| „it closed above the 21 week line for 3 weeks“ und andere reine Beschreibungen | bleiben stehen |
| `linienwert_satz(50)` | rechnet das einfache Mittel und besteht die Schreibregel |

## 3. Eigener Check: scripts/preis_wache.py

**Regeln:**

- **Preis im Text:** Ein Betrag mit €, EUR, $ oder USD, der direkt neben from, per, month, round oder price steht (3 Wörter davor oder danach), ist im sichtbaren Text rot. Das gilt auch für meta description, og und twitter.
- **Ausnahme Marktdaten:** Steht im selben Umfeld kas, kaspa, close, wallet, tvl, volume, worth, fees, source, line, average, unrealized, cost, basis oder ähnliches, ist der Betrag ein Kurs- oder Wallet-Wert und bleibt grün.
- **JSON-LD:** Jedes Offer und jede PriceSpecification sind rot, ebenso `offers`, `price`, `priceCurrency`, `minPrice` und eine description mit Preis.
- **„a close above“** ist im sichtbaren Text rot.

**Wo die Wache läuft:**

- **`seo_pruefung.py`** ruft sie für jede öffentliche Seite und jede Newsletter-Ausgabe ab 8.11. auf. Das ist Punkt 6 der Prüfung und läuft in jedem PR mit Seitentext.
- **`startseite.py`** ruft sie für jeden sichtbaren Satz auf, bevor index.html geschrieben wird. Ein Treffer bricht ab, und die alte Seite bleibt stehen.
- **Von Hand:** `python3 scripts/preis_wache.py` prüft alles. `--url` prüft live.

**Ergebnis:**

| Prüfung | Ergebnis |
| --- | --- |
| Selbsttest `preis_wache.py` | 0 Fehler |
| `startseite.py --selbsttest` | alle bestanden, neu „preis fällt auf“ und „a close above fällt auf“ |
| `seo_pruefung.py --selbsttest` | 0 Fehler |
| `seo_pruefung.py --gegen origin/main` | 0 Fehler |
| alter Stand von for-builders.html | 3 Preise im Text und 26 Schema-Treffer, rot |
| neuer Stand | 43 Seiten, 0 Verstöße |
| Gegenprobe alte Ausgabe `newsletter/2026-11-02.html` (wird im Lauf nicht geprüft) | beide „a close above“ rot |

Die Ausnahme für Marktdaten habe ich gegen alle Seiten geprüft:

- Mit 6 Wörtern Umfeld ließ sie die alten Preise durch, weil „A close read“ und „Kaspa testnet“ danebenstanden. Mit 3 Wörtern sind sie rot.
- entity-x.html („latest price − $88.0M unrealized“) bleibt grün.

## Abnahme auf kaspapulse.com

Nach dem Deploy habe ich am 5.11. `https://kaspapulse.com/for-builders.html` abgerufen. Die neue Fassung war etwa eine Minute nach dem Merge live.

| Gesucht | Treffer |
| --- | --- |
| „€“ | 0 |
| „All prices are net“ | 0 |
| „Fixed prices in euro“ | 0 |
| `priceCurrency` | 0 |
| `"offers"` | 0 |
| „Get a free first look“ | 2 |
| „Ask for a quote“ | da |
| „Measurements for builders run under PulseHawk, our independent measurement brand.“ | 2 |
| Link `https://pulsehawk.io/contact` | 2 |

Ich habe kein Falken-Bild und keinen PulseHawk-Look gefunden.

Danach habe ich die Live-Seiten mit `python3 scripts/preis_wache.py --url …` geprüft: for-builders.html, die Startseite, kaspa-weekly.html, how-we-fund-this.html und entity-x.html. Alle 5 Seiten: 0 Verstöße.

## Offen

- **kaspa-weekly.html** baut im Browser per JavaScript den Satz „A weekly close above $x. That would be the first close above the 21 week average in … weeks“ (Zeile 592). Das ist dieselbe Art Wenn-dann-Satz, nur auf der Website und nicht im Newsletter. Die Wache sieht ihn nicht, weil er erst im Browser entsteht. Nicht geändert, weil er nicht im Auftrag stand. Soll er ebenfalls auf den reinen Linienwert umgestellt werden?
- **Montagsroutine:** Ihr Text steht nicht im Repository. Sie sollte im Abschnitt „worth watching“ statt „threshold to get back above both lines next week“ den Linienwert nennen, zum Beispiel „the 50 week line sits at $x, source kraken“. Eine Ausgabe ab 8.11. mit „a close above“ fällt jetzt in `seo_pruefung.py` auf, ein read damit stoppt `weekly_numbers.py`.
- **kaspa-hashrate.html:** `seo_pruefung.py` ohne `--gegen` meldet dort eine description mit 176 Zeichen. Das ist ein Altbefund und hat mit diesem Auftrag nichts zu tun.
