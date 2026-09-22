# Herkunft der Dashboard-Wochenzahlen

Die Kommentare, die bis 07.08.2026 direkt im DATA-Block der index.html standen.
Seit dem Umbau wird der Block maschinell aus `data/weekly.json` erzeugt,
Kommentare dort wuerden ueberschrieben. Neue Herkunftsnotizen kommen hier rein,
pro Woche ein Abschnitt (Regel 42, eine Zahl ohne Quelle existiert nicht).

## Korrektur 16.09.2026, tps

Bens Frage: woher kommt 2,83 am Zaehltag, wenn Kaspalytics 1,38 im
Wochenschnitt meldet. Antwort: aus derselben Reihe, nur anders gezaehlt.

Unsere Zahl kam aus kaspalytics.com/api/charts/transactions/accepted/count,
Reihen "Standard" UND "Coinbase", EIN Tag (der letzte volle Tag vor dem
Wochenanker, hier Sonntag 06.09.), geteilt durch 86400. Kaspalytics meldet
Standard, im Wochenmittel.

Die Groessenordnung stimmt damit ueberein. Am 16.08., dem einzigen Tag, fuer
den wir die Aufteilung notiert haben, standen 75.050 Standard gegen 127.440
Coinbase, also 0,87 gegen 1,48 je Sekunde. Zieht man diese 1,48 von 2,83 ab,
bleiben rund 1,35, und das ist Kaspalytics 1,38 im Rahmen der Rundung.

Coinbase ist die Auszahlung, die jeder akzeptierte Block an sich selbst
schreibt. Sie misst, wie schnell die Kette laeuft, nicht wie sehr sie benutzt
wird. Ueber der Kachel steht "real network usage" und "spam filtered out"; mit
der Kettenauszahlung darin widersprach die Zahl ihrer eigenen Beschriftung.
Zweitens war es ein Tageswert, der als Wochenzahl gelesen wurde.

Beides ist ab dem 16.09. korrigiert (scripts/kaspalytics.py): tps ist das
MITTEL der sieben vollen Tage vor dem Wochenanker, nur Standard. Der hoechste
Tag im Fenster steht als tps_peak mit Datum daneben, damit ein Spitzentag
kuenftig als Spitzentag erkennbar ist. Die Kachelbeschriftung auf index.html
sagt jetzt "standard transactions per second, 7 day average, coinbase
excluded".

SERIENBRUCH, BEWUSST. Die alten Werte der Reihe (0,74 bis 2,83) sind auf der
alten Grundlage gemessen und mit den neuen nicht vergleichbar. Sie werden
NICHT umgerechnet: die Tagesaufteilung frueherer Wochen ist nirgends
gespeichert, und eine gerechnete Zahl als gemessene auszugeben ist genau das,
was wir sonst verhindern. Die neue Reihe beginnt mit der Woche 21.09. Der
Lesetext auf index.html nennt die alte Grundlage, solange er steht.

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

## Woche 2026-08-17, handwerte

tps aus dem accepted transaction count bei kaspalytics, 75.05K standard plus 127.44K coinbase am 16.08., geteilt durch 86400. active addresses, ruhender anteil, adresszahl und covenant transactions ebenfalls kaspalytics, stand 16.08. boersenbestand aus known exchange holdings, 3.94 mrd. gebuehren aus defillama chain fees 24h, igra 211 plus kasplex 9.03. die beiden l2 transaktionszahlen bleiben leer, defillama zeigt keine transaktionszahlen und kcc20 war nicht erreichbar.

## Neu 19.09.2026, Zeitstempel fuer Supply-Werte

Anlass: der Wert 27.696.515.267 KAS (96,49 Prozent gemintet) steht in mehreren
unserer Dokumente ohne Datum. Beim Tracker-Abgleich fiel auf, dass er unter dem
gemessenen Stand vom 14.09. liegt — gemintete Menge kann nicht schrumpfen, die
Zahl war also aelter, als sie aussah.

Rueckgerechnet aus dem Anker 27.699.388.458 KAS (14.09.2026 06:45:36 UTC) und
1.885.832 KAS Emission pro Tag gehoert sie zu etwa **12.09.2026, 19:10 UTC**.
Die Rueckrechnung ist sauber, weil der Block Reward seit dem 04.09. bei
2,18 KAS steht und im ganzen Fenster konstant war.

Konsequenz, ab jetzt verdrahtet:

- `data/weekly.json` fuehrt `circ_supply_as_of`, `context_fallback.mined_pct_as_of`
  fuehrt denselben Zeitstempel.
- `scripts/dashboard_weekly.py` schreibt beide bei jedem Abruf von
  `api.kaspa.org/info/coinsupply` automatisch mit.
- Der jetzt eingetragene Zeitstempel 2026-09-14T06:45:36Z ist die Commit-Zeit
  des schreibenden Laufs; der Abruf lag wenige Sekunden davor.

Warum ueberhaupt: die gemintete Menge waechst rund 1,9 Mio. KAS am Tag. Ein
Bestand als "Anteil am Geminteten" verschiebt sich dadurch in der vierten
Nachkommastelle pro Tag. Solange danebensteht, wann der Nenner galt, ist das
nachvollziehbar. Ohne Datum ist es eine Behauptung. Regel 42 sinngemaess
erweitert: eine Zahl ohne Quelle existiert nicht, eine Supply-Zahl ohne Datum
auch nicht.

## Umstellung 23.09.2026, die letzten Handwerte fallen weg

Ab der Woche 2026-09-28 holt der Bot alle fuenf Zahlen selbst, die bis dahin
von Hand aus Diagrammen abgelesen wurden. `data/week-input.json` traegt nur
noch "the read". Jede Zahl wurde vorher im Runner gegen den Handwert derselben
Woche gestellt (Lauf 35752265732, Woche 2026-09-21, gelesener Tag 20.09.):

    active_addr    hand 7760           bot 7791            +0,40%
    dormant_pct    hand 50,54          bot 50,59           +0,10%
    exchange_kas   hand 3.790.000.000  bot 3.791.425.244   +0,04%
    tps            hand 2,76           bot 1,47           -46,74%

Bei den ersten dreien ist das dieselbe Zahl, einmal abgelesen und einmal
gelesen. Bei exchange_kas ist die Botzahl genauer: der Handwert war der
gerundete Tooltip, der Bot nimmt den exakten Wert. Fuer dormant_pct wurde
zusaetzlich geprueft, ob die hodl-waves-Seite, die der alte Hinweis nannte,
dasselbe misst wie supply/inactive?minAge=1year. Die Summe der Reihen ab 1y
ergab 50,57 gegen 50,59, also dieselbe Zahl im Rahmen der Rundung.

ZWEI SPRUENGE IN DER WOCHE VOM 28.09., BEIDE EINMALIG UND BEIDE ERKLAERT.

Erstens, tps faellt um rund die Haelfte. Das ist kein neuer Messwert, das ist
die Korrektur vom 16.09., die endlich sichtbar wird. Sie steckte seit dem
16.09. im Bot (Wochenmittel, nur Standard), aber nicht im Post, weil der
Handwert weiter nach der alten Definition eingetragen wurde. Wer die Reihe in
`data/weekly-history.json` anschaut, sieht dort ab dem 28.09. einen Bruch:
die Werte davor sind auf der alten Grundlage gemessen und mit den neuen NICHT
vergleichbar. Sie werden nicht umgerechnet, aus demselben Grund wie am 16.09.

Zweitens, die drei Bestandsfelder holder_addr, exchange_kas und dormant_pct
lesen einen Tag frischer als bisher. Das ist die Korrektur des
Mitternachtsschlupfs vom 22.09.: eine Momentaufnahme, die auf 00:00:0x faellt,
ist der Stand vom Ende des Vortags und wird seitdem dort eingetragen. Vorher
trug die Montagszeile unter dem Sonntagsdatum den Samstagsstand. Gemessen am
22.09. betrug der Unterschied +0,07% bei holder_addr, +0,04% bei exchange_kas
und +0,05 Prozentpunkte bei dormant_pct.

DIE SPRUNGBREMSE SCHLAEGT BEI KEINEM DAVON AN, nachgerechnet gegen MAX_JUMP in
scripts/weekly_numbers.py:

    tps            -46,7%   grenze 150%
    active_addr     +0,4%   grenze 150%
    exchange_kas    +0,04%  grenze  25%
    dormant_pct     +0,1%   grenze  10%
    holders         +0,07%  grenze  20%

Es braucht also kein FORCE=1 am 28.09. Sollte der Lauf trotzdem stoppen, ist
das ein echter Fund und keine Nebenwirkung dieser Umstellung.

Was NICHT passiert ist: die beiden Bedeutungen von "holders" stehen weiter
nebeneinander. In scripts/kaspalytics.py ist holders der ruhende Anteil in
Prozent, in scripts/weekly_numbers.py ist holders die Adresszahl und der
ruhende Anteil heisst dormant_pct. Die Zuordnung in KL_FELDER ist deshalb
ueber Kreuz. Umbenannt wird nach dem Montagslauf, nicht davor.
