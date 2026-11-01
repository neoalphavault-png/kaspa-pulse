# Bericht 1.11.2026: Zahl des Tages ohne Preise, Newsletter mit Adressen ab 100 KAS

Entscheidungen von Ben vom 1.11.2026, Punkte 5 und 6. Gemergt mit #227 (55b6064).

## Zahl des Tages: keine Preise, kein USD, kein „today“
- **Festgeschrieben in der Wache** (`content_wache.zahl_des_tages_verstoesse`): Sie stoppt einen $-Betrag, USD, dollar, cent, euro, price, priced, spot, valued, market cap, sats, satoshis, ATH und today. Der Cashtag $KAS bleibt erlaubt.
- **Jeder sichtbare Text** des Bildes und der Posts wird vor dem Posten geprüft. Bei einem Verstoß wird nichts gepostet, und die Meldung geht nach #ops-log.
- **Gesperrt sind die vier Kandidaten mit Kurs oder Dollar:**
  - emission_vs_btc, die Emission in USD gegen Bitcoin
  - weekly_line, der Wochenschluss in USD
  - sats_divergence, der Kurs in Satoshi
  - tvl_move, die TVL in USD

  Ihre Messwerte laufen weiter ins Log.
- **Datum statt „today“:** Wo bisher „today“ oder „this morning“ stand, steht jetzt der Messtag, zum Beispiel „342 PH on 1 nov“.
- **#197** gibt dem Auswahlschritt der Zahl des Tages den Zugang zu #ops-log. Genau darüber meldet sich die Wache, wenn sie stoppt. Er passt also zu Punkt 6 und kann gemergt werden.

## Newsletter: Adressen ab 100 KAS mit Stichtag
- **Statt** „addresses holding a balance“ steht jetzt „addresses with 100 KAS or more **295,772** as of 25 oct 2026“. Das ist dieselbe Definition wie im Karussell und im Cheat Sheet.
- **Quelle:** Kaspalytics `distribution/kas-threshold/100+`, der letzte abgeschlossene Tag vor dem Lauf.
- **Von Hand:** Ein Wert von Hand braucht auch seinen Stichtag, sonst stoppt der Lauf.
- **Erster Montag:** Die Zeile trägt in der ersten Woche keinen Vergleich zur Vorwoche, wie bisher bei den Adressen.

## Prüfung
- Alle betroffenen Selbsttests sind grün, darunter neue Fälle für alle Kandidaten und für den Tag des Cuts.
- Keine Workflow-Dateien.

<!-- discord -->
**Zahl des Tages und Newsletter, 1.11.2026**
- **Zahl des Tages:** kein Preis, kein USD, kein „today“, festgeschrieben in der Wache. Bei einem Verstoß wird nichts gepostet, die Meldung geht nach #ops-log. Die 4 Kandidaten mit Kurs oder Dollar sind gesperrt, statt „today“ steht der Messtag.
- **#197** passt dazu: Darüber meldet sich die Wache. Du kannst ihn mergen.
- **Newsletter:** „addresses with 100 KAS or more“ mit Stichtag, dieselbe Definition wie Karussell und Cheat Sheet.
- Gemergt mit #227. Bericht: berichte/2026-11-01-nod-newsletter.md
<!-- /discord -->
