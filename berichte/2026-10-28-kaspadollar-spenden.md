# KaspaDollar, Spenden gezählt zur Stichzeit Mi 28.10.2026 12:00 UTC

Bericht für Ben zum Auftrag vom 25.10.2026. Lieferung Mi 28.10. 18:00 Berlin. Zahlen aus unserem eigenen Knoten heißen counted, Zahlen der Seite heißen source kaspadollar.com.

## Ergebnis in einem Satz

Zur Stichzeit lagen auf der Spendenadresse 169.667,19 KAS aus 143 Einzahlungen (counted). Die Seite wurde erst um 12:42:28 UTC gelesen und zeigte 182.012 KAS (source kaspadollar.com), 6,78 % mehr. Eine Kontrollzählung genau zu dieser Uhrzeit ergibt 182.012,19 KAS (counted). Zur selben Minute stimmen Seite und Knoten also überein. Der Unterschied ist eine Einzahlung von 12.345 KAS zwischen 12:00 und 12:42 UTC. Weil die Abweichung zur Stichzeit über 1 % lag, ist nach der Regel vom 25.10. noch nichts Öffentliches vorbereitet. Ben entscheidet, ob X-Post und Grafik jetzt kommen.

## Methode in drei Sätzen

Die Spendenadresse lesen wir nur von kaspadollar.com aus dem Feld neben "Copy", und ein eigener Kaspa-Knoten (rusty-kaspa v2.1.0) liest alle angenommenen Transaktionen an diese Adresse. Den Bestand zur Stichzeit rechnet er zweimal, zurück von der Kettenspitze und vorwärts vom Pruning-Punkt. Absender früherer Einzahlungen vor unserem eigenen Fenster kommen von api.kaspa.org und werden nur als Prüfsumme gezählt, nie als Adresse gespeichert.

Spendenadresse laut kaspadollar.com, abgerufen am 28.10.2026 um 12:42:28 UTC. Ihr Hash ist in allen Läufen seit 25.10. derselbe.

## Zahlen zur Stichzeit (counted)

| | Wert |
|---|---|
| 1. Summe der Einzahlungen | 169.667,19 KAS (genau 169.667,18740296) |
| 2. Zahl der Einzahlungen | 143 |
| 3. Verschiedene Absender | 146 |
| 4. Median je Einzahlung | 400 KAS |
| 4. Größte Einzahlung, Anteil an der Summe | 26,52 % |
| 5. Abgänge von der Adresse | 0 |
| Bestand zur Stichzeit | 169.667,19 KAS, gleich Einzahlungen minus Abgänge |
| Ziel laut Seite | 5.000.000 KAS, also 3,39 % erreicht (counted gegen das Ziel der Seite) |

Absender: 39 kommen aus unserem eigenen Fenster seit 27.10. 06:12 UTC, 108 aus der Zeit davor über api.kaspa.org. Einer steht in beiden, das ergibt 146. Ein Absender kann mehr als eine Einzahlung haben, und eine Einzahlung kann mehrere Absender haben, deshalb ist die Zahl der Absender höher als die der Einzahlungen.

### Tageskurve (UTC, counted)

| Tag | KAS | Einzahlungen | kumuliert KAS |
|---|---|---|---|
| Fr 23.10. | 16.308,00 | 22 | 16.308,00 |
| Sa 24.10. | 73.804,19 | 31 | 90.112,19 |
| So 25.10. | 13.093,86 | 23 | 103.206,05 |
| Mo 26.10. | 19.954,09 | 26 | 123.160,13 |
| Di 27.10. | 24.108,70 | 22 | 147.268,83 |
| Mi 28.10. bis 12:00 | 22.398,36 | 19 | 169.667,19 |

Datei: `kaspadollar/ergebnis/kaspadollar-tage-2026-10-28.csv`, dazu `kaspadollar/ergebnis/kaspadollar-ergebnis-2026-10-28.json`. Beide enthalten keine Adresse und keine Transaktionskennung.

## Prüfung

- **Fenster lückenlos:** Die eigenen Fenster aus vier Läufen (So, Mo, Di, Mi) decken zusammen 24.10. 05:58 bis 28.10. 11:59:59 UTC ohne Lücke ab. 24 Einzahlungen liegen vor diesem Fenster, sie stammen aus dem UTXO-Bestand des eigenen Knotens.
- **Bestand:** Einzahlungen minus Abgänge ergeben genau den Bestand zur Stichzeit. Die Zweitprüfung des ganzen UTXO-Bestands auf dem Vorwärtsweg ist identisch mit dem Rückweg.
- **Keine ungelösten Eingänge, kein Kettenblock ohne Daten.**
- **Gegen die Vortage:** Die Tage 23. bis 26.10. sind in allen Läufen gleich. Der Dienstag-Lauf hatte 136.416,83 KAS zur Stichzeit 27.10. 12:00. Dazu kommen 10.852,00 KAS vom 27.10. nach 12:00 und 22.398,36 KAS vom 28.10. bis 12:00, zusammen genau 169.667,19 KAS.
- **Läufe:** So [40183002756](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40183002756), Mo [40308096150](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40308096150), Di [40489816938](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40489816938), Mi [40672753837](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40672753837) im zweiten Versuch.

## Was am Mittwoch schiefging

- **Erster Versuch:** Der Knoten war um 11:26 UTC synchron und blieb dann stehen. Um 12:22 UTC hat GitHub den Runner heruntergefahren, Exit-Code 143. Die Seite war um 12:00 UTC schon gelesen, der Wert ging aber mit dem Runner verloren.
- **Zweiter Versuch:** Er lief ab 12:39 UTC sauber durch. Weil die Ablesezeit 12:00 UTC da schon vorbei war, hat er die Seite sofort gelesen, um 12:42:28 UTC. Unsere Zählung gilt für 12:00 UTC, die Seite für 12:42:28 UTC.

## Abweichung zur Seite

| | KAS | Zeit (UTC) |
|---|---|---|
| counted | 169.667,19 | 12:00:00 |
| source kaspadollar.com | 182.012 | 12:42:28 |
| Unterschied | 12.344,81, also 6,78 % | |

Mögliche Gründe:
1. Einzahlungen zwischen 12:00:00 und 12:42:28 UTC.
2. Die Seite rechnet etwas mit, das nicht auf dieser Adresse liegt.

Zum Vergleich die Vortage, an denen die Seite zur Stichzeit gelesen wurde: So 93.435 gegen 93.435,19, Mo 105.477 gegen 105.477,05, Di 136.416 gegen 136.416,83. Die Seite rundet also ab und lag bisher nie daneben.

**Kontrollzählung:** Lauf [40707682036](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40707682036) zählt mit der Ablesezeit 12:42:28 UTC als Stichzeit. Stimmt sie mit 182.012 KAS überein, liegt der Unterschied nur an den 42 Minuten. Das Ergebnis steht unten, sobald der Lauf fertig ist.

Ergebnis der Kontrolle, Lauf 40707682036, Stichzeit 12:42:28 UTC:

| | KAS |
|---|---|
| Bestand der Adresse laut UTXO-Bestand (counted) | 182.012,19 (genau 182.012,18740296) |
| Seite zur selben Zeit (source kaspadollar.com) | 182.012 |
| Unterschied | 0,19, die Seite rundet ab |
| Bestand 12:42:28 minus Bestand 12:00:00 | 12.345,00 genau |

- **Woher die 12.345 KAS kommen:** Zwischen 12:00 und 12:42:28 UTC kam genau eine Transaktion an die Adresse dazu. Im Fenster stehen 39 statt 38 Zieltransaktionen. Abgänge gab es keine.
- **Zweitprüfung des UTXO-Bestands:** identisch, Fenster ohne Lücke.
- **Fehler in unserem Werkzeug:** Die Liste der Einzahlungen endet in der Kontrolle wie im Hauptlauf um 11:59:59 UTC. Sie enthält die neue Einzahlung also nicht, deshalb meldet die Kontrolle "Einzahlungen minus Abgänge gleich Bestand: nein". Der Bestand selbst kommt unabhängig davon aus dem UTXO-Bestand und stimmt. Ursache ist vermutlich das Zusammenlegen der Läufe in `scripts/kaspadollar_zaehlung.py`, wenn ein früherer Lauf genau bis zur Stichzeit eines späteren reicht. Den Hauptlauf betrifft das nicht, dort stimmt die Prüfung. Ich behebe das, bevor wir wieder zählen.
- Die Seite stand bei der Kontrolle (gelesen 14:37:48 UTC) schon bei 184.560 KAS. Diese Zahl gehört zu keiner unserer Stichzeiten und ist hier nur vermerkt.

## Offene Fragen an Ben

1. Der Unterschied ist geklärt: Zur selben Minute stimmen Seite und Knoten auf 0,19 KAS überein. Soll ich X-Post und Grafikvorgabe jetzt vorbereiten? Zur Wahl stehen 12:00 UTC mit 169.667,19 KAS oder 12:42:28 UTC mit 182.012,19 KAS. Für 12:42:28 stimmt der Bestand, die Tageskurve kann ich dann aber erst nach der Fehlerbehebung neu rechnen. Nach deinem Ja brauche ich etwa 15 Minuten.

## Was Ben tun muss

- Diesen PR mergen, wenn er passt. Er enthält nur Bericht, CSV und JSON, keinen Workflow.
- Frage 1 beantworten.
- Die Werkzeuge mit den beiden Workflows liegen auf `messung/kaspadollar-spenden`. Ob sie nach main sollen, entscheidest du. Bis dahin bleiben sie dort.
