# Automatik-Pruefung, aktueller Stand

Stand: Montag, 16.11.2026, 10:30 Uhr Berlin-Zeit (09:30 utc).
Geprueft wurde von 09:41 bis 10:30 Berlin (08:41 bis 09:30 utc).
Lauf gruen, kein roter Lauf, keine Unsicherheit. Montag, deshalb mit
Kanalzeile und Uhrwerk-Bericht.

## Meldung an Ben, woertlich

NOD: heute lag bis 08:41 utc kein Lauf vor, deshalb von der Pruefung genau
einmal gestartet (workflow_dispatch auf main, Antwort 204 queued), kein
zweiter Start. Lauf 343, Run-ID 43833311493, 08:41:42 bis 08:42:51 utc,
gruen, echte Arbeit (Doppellauf-Sperre hat nicht gegriffen).
X-Post: nein. "x pausiert" auf success, "post to x" auf skipped, der
Schalter X_GOKU_AN ist weiter aus. Letzter Eintrag in data/x-post-log.json
bleibt nod-2026-11-08, das ist der achte Tag ohne Post.
Datenstaende: ok. kas-candles auf 2026-11-16 07:11 utc (letzte Kerze 15.11.),
Multibagger-Pick date 2026-11-15 auf Schlusskurs vom 13.11., dem letzten
Handelstag; die Abweichung vom 15.11. ist damit weg.
Wachstumslog: Short 6TfVlsBJtQs eingetragen (48-h-Marke), nichts offen, seit
dem 13.11. ist kein neues Video erschienen. Diff: 119 Einfuegungen,
0 Loeschungen; dazu die neue Montagsdatei uhrwerk-2026-11-16.md mit 185
Einfuegungen. Branch claude/wachstumslog-2026-11-16, Commit 873ccd6.
Reels: 1 eingetragen (Dfry_BqJvHr vom 13.11., Skip-Rate 58,4 Prozent). Keine
Zwei-Satz-Notiz faellig, keine Reel-Ansicht ausgeloest.
Ablage: claude/ablage-automatik-pruefung, Head <dieser Commit>

## Uhrwerk-Bericht, Kurzfassung fuer Ben

YouTube: Abos netto Woche +2; bester Short zpqk0P3GIJc 12.11. (180 Aufrufe,
gesehener Anteil 99,3 Prozent, 0,56 Abos je 100 Aufrufe), schwaechster
yy6M1vPoHPk 09.11. (82 Aufrufe); Testvorschlag Shorts: Einstieg Sekunde 0,
Zahl gegen Frage, und test im Manifest setzen.
Kanal gegen den Schnitt der 4 Wochen davor: Aufrufe 1.010 gegen 1.668
(minus 39 Prozent), Wiedergabestunden 6,2 gegen 8,8 (minus 30 Prozent).
Lange Videos: Weekly pCJG90JmXCg gesehener Anteil 57,7 Prozent, nach 30 s
noch 76 Prozent, Suche 52,8 Prozent, Abspann-Klickrate 0,00 Prozent.
Erklaerer SFcWhABVOfg 46,5 Prozent, nach 30 s noch 67 Prozent, Suche
66,7 Prozent, Abspann-Klickrate 0,00 Prozent. Klickrate auf Impressionen und
"angesehen statt weggewischt" gibt die Schnittstelle nicht heraus.
Test & Compare: Gewinner bitte aus Studio eintragen, pCJG90JmXCg und
SFcWhABVOfg.
Instagram: Follower netto +16 (144 auf 160), Median-Reichweitenquote 0,36 aus
7 Posts (Vorwoche 1,90), Median-Reichweite 54, Median Skip-Rate der 3 Reels
64,6 Prozent. Top: tagesgrafik-form04 1.728, form06 1.686, form03 531.
Flop: form02 39, form05 40, form09 52.
X: Follower netto +2 (269 auf 271), nur ein gemessener Post der Woche
(25 Impressionen, Quote 0,09) -- nicht belastbar, weil der Post seit dem
09.11. pausiert. Threads: Follower netto +1 (8 auf 9), sonst alles offen,
weiter kein Schnappschuss.
Tests: auf keinem Kanal laeuft ein getaggter Test, vierte Woche in Folge
0 von 7. Kurzlink-Klicks ohne Quelle, Newsletter-Anmeldungen gehen nach
#moderator-only.
Titel der Woche unter 85: Shorts Di 79, Do 64, Fr 80 (am 08.11. gemessen,
nicht geaendert). Langvideos 88 und 95.
vidiq_comment_insights findet keine belastbare Zuschauerfrage (9 indizierte
Kommentare aus 2 Kanaelen, einziger Treffer eine Chainlink-Bitte auf einem
fremden Kanal); unsere beiden juengsten Langvideos haben 0 Kommentare.
Testvorschlaege je Kanal: Instagram Einstieg Sekunde 0, Zahl gegen Frage
(Vorrang, Median-Skip 64,6 Prozent). X erste Zeile, Zahl gegen Vergleich --
ruht, solange X_GOKU_AN aus ist. Threads Frage zuerst statt Zahl zuerst.
Lange Videos: Test & Compare mit 3 Thumbnails, dazu nur der Einstieg der
ersten 30 Sekunden.
Zwei Herausforderer-Formen, nur die Form: (1) Gegenthese als Texttafel in
Sekunde 0, dann harter Schnitt auf den Chart, der sie belegt (DfimIMrNtfc
204,1K bei 3,6K Followern, 104x Median; DfroDlZo94U 656,8K, 26,6x).
(2) Zweiteiler-Bild, Chart oben, grosse Textzeile unten, dynamische Captions,
Abschlussfrage (DfqgcFvoway 352,2K, 27,9x; TikTok kanaiwatrades 315,3K bei
3,4K Followern, 542,7x). Ben gibt mit einem Klick frei.
Zwei vidIQ-Formen, die uns bei langen Videos fehlen: Kommentar in 8 bis 9
Minuten mit Ich-Haltung im Titel (ZwNvn1egRfQ, 3x Breakout) und Ereignis-
oder Personen-Aufhaenger statt Metrik (DgUJ_GsNkac, 2,1x).
Der vollstaendige Bericht steht in
pulse-studio/docs/projekt/uhrwerk-2026-11-16.md.

## Belege und Einzelheiten

- Lauf 343 (Run-ID 43833311493), workflow_dispatch auf main, von dieser
  Pruefung um 08:41:42 utc genau einmal gestartet. "sperre gegen doppellauf"
  hat nicht ausgeloest, alle Schritte von "pick the number" ueber "render",
  "archive dated copy", "post to discord and telegram", "seitenstand und
  sitemap" bis "commit" und "upload for download" stehen auf success.
- Letzter Lauf vor der Pruefung war Lauf 342 (Run-ID 43736382669) vom
  15.11. 16:36 utc, success, aber durch die Doppellauf-Sperre ohne Arbeit.
- Haengender Lauf: eine Abfrage aller Laeufe in kaspa-pulse mit status=queued
  gibt genau einen zurueck, den bekannten Lauf 166 vom 07.10. Nicht gemeldet,
  nicht angefasst.
- Kanal Kaspa Pulse: 120 Abos, 20.533 Aufrufe, 64 Videos (15.11.: 121 Abos,
  20.353 Aufrufe, 64 Videos). Aufrufe plus 180, Videozahl unveraendert, die
  oeffentliche Abozahl um eins gefallen -- Analytics meldet fuer die Woche
  dagegen 2 gewonnene und 0 verlorene Abos. Beides so uebernommen, nichts
  verrechnet.
- Kanalzeile Montag: Abos 120, Wiedergabestunden der letzten 28 Tage 30,6
  (1.838 Minuten, 20.10. bis 16.11., dazu 5.808 Aufrufe), Abspann-Klickrate
  des juengsten Langvideos SFcWhABVOfg 0,00 Prozent.
- Reel Dfry_BqJvHr: 562 Aufrufe, 25 Likes, 0 Kommentare, 0 Teilen,
  0 Speichern, 6,3 s durchschnittliche Wiedergabezeit, Skip-Rate 58,4
  Prozent, geschauter Anteil "noch nicht da" (avgWatchedPct null), Trial
  nein. Beste Skip-Rate seit Beginn dieser Zeilen.
- Zwei Reels noch zu jung: DfulgX6J1uU vom 14.11. 16:00 utc (41,0 h) und
  Dfw__UGpt7R vom 15.11. 14:30 utc (18,5 h). Dfw__UGpt7R liegt mit 82,6
  Prozent ueber der 80-Prozent-Grenze, ist aber nicht im Fenster und loest
  die Ansicht nach der Regel nicht aus. Nichts vorgezogen.
- Instagram-Follower 160 (15.11. 159), Guthaben vidIQ 774.
- Impressionen und Klickrate bleiben offen, die gibt die Schnittstelle
  grundsaetzlich nicht heraus.
- Kanal Pulse Hawk: kein neues Video, kein vidIQ-Analytics-Zugang, bekannt
  und nicht als Fehler gewertet.
- Nichts repariert, nichts umgestellt, keine Workflow-Datei angefasst, kein
  Post von Hand, kein Zeitplan und kein Generator geaendert.
