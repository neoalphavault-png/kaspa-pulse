# Herkunft der Dashboard-Wochenzahlen

Die Kommentare, die bis 07.08.2026 direkt im DATA-Block der index.html standen.
Seit dem Umbau wird der Block maschinell aus `data/weekly.json` erzeugt,
Kommentare dort wuerden ueberschrieben. Neue Herkunftsnotizen kommen hier rein,
pro Woche ein Abschnitt (Regel 42, eine Zahl ohne Quelle existiert nicht).

## Serien-Definitionen (fortlaufend gueltig)

- **circ_supply**: kaspa.stream druckt nur "27.62B", keine exakte Ziffernfolge.
  Gegenprobe 03.08.: mcap 718.15M / 0.026 = 27.621B.
- **annual_inflation** neu berechnet 03.08.: block reward 2.45 x 10.2 BPS x 86400
  x 365 / circ supply ~ 2.9 % (alter Wert 4.6 % war veraltet).
- **next_reduction** wird aus dem Datum gerechnet, nicht als Text gepflegt,
  sonst steht am Donnerstag noch "in 2 days" auf der Seite (SEO-Regel 9).
- **fees_7d**: DefiLlama zeigt auf der Chain-Seite nur 24h, die 7-Tage-Summe
  braucht den Umschalter. Bis dahin null.

## Serien-Umstellung 27.07.

- **holder_addr** = Kaspalytics Distribution Table, Summe aller Buckets ab
  0.01 KAS (vorher gemischte Quelle).
- **active_addr** = Kaspalytics "Number of Unique Active Addresses" (vorher
  breitere Zaehlung, alte Werte auf null gesetzt).
- **holders** (1J+ inaktiv) = Kaspalytics "Supply Not Moved in Over 1 Year",
  Serie frisch ab 27.07.

## Serien-Umstellung 03.08. (drei Stueck, Grund: Definition war nicht festgenagelt)

1. **covenant_tx** = ab jetzt Kaspalytics "Covenant-Creating Txs" (24h). Die
   alten Werte 44/1578/918 kamen von kcc20 und zaehlten Events, nicht
   Transaktionen. kcc20 zeigt am 03.08. 6.534 Events gegen 3.517 Creating-Txs.
   Der scheinbare Sprung von 918 auf 3.517 waere reine Definition gewesen,
   nicht Wachstum. Alte Werte auf null, Reihe startet neu.
2. **active_addr** = Kaspalytics "Number of Unique Active Addresses", ab jetzt
   IMMER der letzte VOLLE Tag (also gestern), nie der laufende. 7.440 und 7.950
   waren am Lesetag angebrochene Tage und damit zu niedrig. Der Sprung auf
   13.940 ist ueberwiegend dieser Lesefehler, nicht Wachstum. Alte Werte auf null.
3. **holders** = Summe der Kaspalytics-Aging-Buckets ueber 1 Jahr. Die
   sichtbaren Zeilen (3-4J 7,13 + 2-3J 13,27 + 1-2J 26,51) ergeben 46,91 %,
   alle neun Zeilen zusammen aber nur 96,31 %. Die fehlenden 3,69 % sind der
   nicht gerenderte Bereich ueber 4 Jahren (Kaspa startete 11/2021).
   46,91 + 3,69 = 50,60, was zur Vorwoche (50,47) passt. Reine 46,91 zu melden
   waere ein Minus von 3,6 Punkten in einer Woche gewesen, also rund 980M KAS
   in Bewegung. Das hat nicht stattgefunden.

## Woche 03.08.

- **hashrate_windows**: d7 aus der eigenen Reihe (262.3 auf 342.5). d30/d90
  gegen die ABSOLUTEN Vorwochen-Basen gerechnet (389.7 / 381.3 PH/s), die Anker
  sind damit eine Woche alt. TODO: Kaspalytics-Hashrate-Kurve mitscreenshotten,
  dann haben wir eigene 30/90-Tage-Anker.
- **dex_windows**: je Chain gegen die Vorwoche aus history gerechnet.
- **exchange_kas 03.08. ist FORTGESCHRIEBEN, nicht frisch abgelesen.** Diese
  Woche kam der Screenshot der Adressliste statt der Summen-Ansicht. Die neun
  boersenmarkierten Adressen in den Top 10 summieren sich auf 5,42 Mrd, unsere
  Reihe steht aber bei 3,94 Mrd, das ist also ein anderer Korb (Uphold und
  Bitvavo sind Verwahrer, kaspa.stream zaehlt sie in der Summen-Ansicht
  vermutlich nicht mit). Gemessen ist der NETTOFLUSS: die Summe der
  7-Tage-Spalten dieser neun Adressen ist minus 85.200.658 KAS, angewendet auf
  3,94 Mrd. Richtung und Groesse sind belegt, das absolute Niveau ist geerbt.
  TODO Montag: Summen-Ansicht screenshotten, dann den Korb einmal sauber
  definieren.
- **holder_baselines**: m3 = Distribution Table 27.04., Summe Buckets >= 0.01.
- **exchange_baselines**: m3 23.04. = 3.89B KAS, y1 24.07.25 = 3.07B KAS.
- **entityx_baselines**: m3 = Distribution Table 1B-10B-Bucket 27.04., y1 null,
  vor einem Jahr existierte keine 1B+-Adresse.

## Woche 2026-08-10, handwerte

Serienumstellung holder_addr ab 10.08.: Kaspalytics Address Count (Holding More than a Dust Balance), eine einzige Zahl statt Summe der Distribution-Table-Buckets. Der neue Wert 788.730 liegt 41.127 ueber der alten Reihe (747.603 am 03.08.), bei einem normalen Wochenwachstum von rund 1.500. Andere Metrik, kein Wachstum. Alte Werte und Baselines auf null, Reihe startet neu. holders 50,68 kommt ab jetzt direkt aus Supply Not Moved in Over 1 Year statt aus der Bucket-Summe; Gegenprobe: die Bucket-Rechnung ergab am 03.08. 50,60, der Chartwert schliesst nahtlos an, also kein Bruch sondern eine Vereinfachung. covenant_tx 1.060 am 09.08. gegen 3.517 in der Vorwoche; die Reihe ist extrem volatil (Spitzen bis 9.800 im Juli), ein Tageswert ist kein Trend. hashrate 289,5 PH/s live abgelesen, Anker aus dem Kaspalytics-Chart: 09.07. = 320 PH/s, 09.05. = 390 PH/s. exchange_kas erneut FORTGESCHRIEBEN: Nettofluss aus den 7-Tage-Spalten der neun boersenmarkierten Top-10-Adressen ist plus 38.275.446 KAS, angewendet auf 3.854.799.342. Vorschlag: naechste Woche auf Kaspalytics Exchange Holdings umstellen, eine einzige Zahl aus derselben Quellfamilie. fees_day 244 = Igra 235 plus Kasplex 9,03. igra_tx und kasplex_tx fehlen diese Woche, Quelle ungeklaert.

## Woche 2026-08-17, handwerte

tps aus dem accepted transaction count bei kaspalytics, 75.05K standard plus 127.44K coinbase am 16.08., geteilt durch 86400. active addresses, ruhender anteil und adresszahl ebenfalls kaspalytics, stand 16.08. boersenbestand aus known exchange holdings, 3.94 mrd. covenant und die beiden l2 transaktionszahlen bleiben diese woche leer, dafuer lag zur lesezeit keine quelle vor. lieber ein strich als eine geschaetzte zahl.
