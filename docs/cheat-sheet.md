# Das Cheat Sheet, monatlich gebaut

`the 8 kaspa numbers whales watch`, zehn Seiten, 1080 x 1350 px je Seite,
unter `kaspapulse.com/kaspa-pulse-cheat-sheet.pdf`. Edition 1 (Oktober 2026)
hat Ben von Hand gebaut, aus CSV-Dateien und mit Schriften aus
`node_modules`. Ab Edition 2 baut `scripts/cheat_sheet.py`.

## Die Regel, die alles traegt

Jede der acht Zahlen bringt ihren Stichtag mit. Ist einer aelter als zehn
Tage (`FRIST_TAGE`), bricht der Lauf ab und nennt die Zahl beim Namen:

    ABBRUCH zu alt oder fehlend, frist 10 tage: boersen, stichtag 2026-10-04 ist 21 tage alt

Kein stillschweigendes Weiterverwenden. Ein PDF mit "edition 3 - dezember"
und einem Gebuehrenwert vom Oktober waere eine Luege mit Datum, und genau
dafuer tragen unsere Seiten ihre Stichtage.

Zwei weitere Abbruchgruende, aus demselben Grund:

* Seite 3 sagt `half of all KAS` und `a quarter`. Liegt der Anteil seit
  einem Jahr unbewegt nicht zwischen 45 und 55 Prozent, oder der seit zwei
  Jahren nicht zwischen 20 und 30, bricht der Lauf ab. Den Text aendert
  Ben, nicht der Generator.
* Eine gespeicherte Probe (`--aus`) darf nachgebaut, aber nie
  veroeffentlicht werden, wenn sie selbst alt ist.

## Woher die acht Zahlen kommen

| Nr | Zahl | Quelle |
| --- | --- | --- |
| 1 | groesste Wallet, Anteil am Umlauf | Balance live von api.kaspa.org, Umlauf aus `data/weekly.json`, letzter Abfluss aus `data/entity-x-outflows.json` |
| 2 | KAS auf Boersen | kaspalytics `supply/exchange-holdings` gegen `supply/circulating`, ein Punkt je Sonntag |
| 3 | seit einem Jahr unbewegt | kaspalytics `supply/inactive?minAge=1year` und `2years`, beide vom selben Stichtag |
| 4 | Adressen ab 100 KAS | `data/address-thresholds-log.json`, dazu die Differenz ueber 7, 30 und 90 Tage |
| 5 | naechste Reward-Senkung | Emissionsplan in `scripts/number_of_day_data.py`, reine Rechnung |
| 6 | neue Coins gegen Gebuehren | `data/tagesgrafik-log.json`, Feld `messwerte.gebuehren` |
| 7 | Hashrate, 7-Tage-Mittel | api.kaspa.org `info/hashrate/history`, ein Tagesmittel je Tag |
| 8 | Covenants seit Toccata | `data/covenants-log.json` |

Alles, was Netz braucht, laeuft ueber `scripts/tagesgrafik.py`. Damit steht
die Mitternachtsregel aus `scripts/kaspalytics.py` nur an einer Stelle.

## Die Texte

Jeder Satz steht in `karten()` so, wie Ben ihn in Fassung 2 freigegeben hat.
Geaendert wird daran nichts, auch keine Wortstellung. Was sich monatlich
aendert, ist eine Einsetzung.

Wo ein Satz nur mit einem Vorzeichen stimmt, waehlt eine kleine Funktion das
Wort, statt es stehen zu lassen und falsch werden zu lassen:
`slipped / risen / barely moved`, `added / lost`, `more / less`,
`slightly / clearly negative`, `almost / just over`. Ein neues Wort kommt
nur mit Bens Freigabe dazu.

## Was gerechnet wird, statt im Quelltext zu stehen

In Edition 1 standen diese Zahlen fest im Bauskript. Jetzt nicht mehr:

* die Quadratzahl im Gebuehrenraster (766 = 765 + 1 helles Quadrat),
* der laufende Reward in der Treppe (2.060172),
* das 7-Tage-Mittel der Hashrate (339.1) und die Obergrenze der Balken,
* die drei Achsengrenzen (13.4 bis 14.4, 290 bis 380, 0 bis 300000).

Die Achsen folgen einer Regel fuer alle drei Diagramme: der Schritt ist die
groesste runde Zahl (1, 2, 2.5, 5 mal Zehnerpotenz), die hoechstens ein
Drittel der Spanne ist, weil vier Hilfslinien in Dritteln gezogen werden;
die Grenzen polstern die Spanne um ein Fuenftel und runden nach aussen auf
ein Vielfaches des Schritts. Eine kumulierte Reihe laeuft von null bis zum
naechsten Schritt ueber ihrem Hoechstwert. Damit kommen genau die Grenzen
von Edition 1 heraus, siehe Selbsttest.

## Unterschiede zu Edition 1

Der Selbsttest baut aus `scripts/cheat-sheet-probe.json`, den Daten vom
11.10.2026, mit denen Ben Fassung 2.1 gebaut hat. Das Ergebnis ist
zeichengleich zur veroeffentlichten Datei, bis auf zwei Stellen:

1. **Seite 8, mittlere Datumsmarke.** `11 sep` statt `12 sep`: die Marke
   sitzt genau in der Mitte der Reihe, statt nach Augenmass.
2. **Seite 9, mittlere Datumsmarke.** `19 aug` statt `15 aug`, aus demselben
   Grund. Beides von Ben freigegeben am 12.10.2026.

Format, Titel, Seitenzahl und MediaBox sind gleich: 10 Seiten,
810 x 1013.04 pt, Titel `The 8 Kaspa numbers whales watch`.

Die dritte Abweichung ist weg, weil die veroeffentlichte Datei nachgezogen
wurde: Fassung 2 nannte als Veraenderung ueber 90 Tage `-637`, gezaehlt
gegen den 07.07. und damit gegen 89 Tage. Fassung 2.1 nennt `-718`, streng
gegen den 90. Tag. Die 7- und 30-Tage-Werte stimmten in beiden.

## Schriften

Acht Schnitte im Repo unter `graphics/fonts`, OFL, siehe das README dort.
Kein npm und kein CDN, damit ein Lauf von heute in zwei Jahren dasselbe PDF
ergibt.

## Aufrufe

    python3 scripts/cheat_sheet.py --selbsttest
    python3 scripts/cheat_sheet.py --probe > probe.json
    python3 scripts/cheat_sheet.py --bauen
    python3 scripts/cheat_sheet.py --aus scripts/cheat-sheet-probe.json --bauen --edition 1
    python3 scripts/cheat_sheet.py --veroeffentlichen --melden

`--bauen` legt PDF, Deckblatt und HTML unter `graphics/cheat-sheet/` ab und
laesst alles andere in Ruhe. `--veroeffentlichen` ersetzt zusaetzlich
`kaspa-pulse-cheat-sheet.pdf` und traegt die Ausgabe in
`data/cheat-sheet-log.json` ein. Die Nummer der naechsten Ausgabe ist die
hoechste im Log plus eins; ein zweiter Lauf im selben Monat behaelt seine
Nummer.

## Der monatliche Lauf

`.github/workflows/cheat-sheet.yml`, am 1. jeden Monats 09:00 Berlin. Den
Takt gibt `takt-cheat-sheet` auf c2, der Cron im Workflow ist der Ersatz.

Der Lauf veroeffentlicht nichts. PDF und Deckblatt gehen nach
#moderator-only, dazu je Zahl ihr Stichtag und wie alt er ist. Die Datei der
Webseite wird nur ersetzt, wenn die Repo-Variable `CHEAT_SHEET_LIVE` auf
`scharf` steht - wie `IG_MODUS` bei Instagram und `REEL_LIVE` bei den Reels.
Solange sie das nicht tut, verbraucht auch kein Lauf eine Ausgabe-Nummer.
