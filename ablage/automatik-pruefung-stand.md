# Automatik-Pruefung, aktueller Stand

Stand: Sonntag, 15.11.2026, 10:05 Uhr Berlin-Zeit (09:05 utc).
Geprueft wurde von 09:41 bis 10:05 Berlin (08:41 bis 09:05 utc).
Lauf gruen, kein roter Lauf, keine Unsicherheit. Eine Abweichung bei den
Multibagger-Daten, nur gemeldet, nichts korrigiert.

## Meldung an Ben, woertlich

NOD: heute lag bis 08:41 utc kein Lauf vor (der geplante um 08:12 utc hat
gefehlt), deshalb von der Pruefung genau einmal gestartet (workflow_dispatch
auf main, Antwort 204 queued), kein zweiter Start. Lauf 338, Run-ID
43695685612, ist gruen durchgelaufen (08:41:31 bis 08:42:22 utc) und hat
echte Arbeit getan.

X-Post: nein, nach Vorgabe pausiert (X_GOKU_AN steht auf false, Schritt
"x pausiert" success, "post to x" skipped), letzter Eintrag bleibt
nod-2026-11-08.

Datenstaende: abweichend. kas-candles.json ist ok, steht auf 2026-11-15
07:05 utc, letzte Tageskerze 14.11. Multibagger: Pick vom 14.11. traegt
Schlusskurse vom 12.11., letzter geschlossener Handelstag war aber Freitag
der 13.11.; am 14.11. war der Abstand noch ein Tag, heute sind es zwei.
state last_run 2026-11-14, Cursor 1233. Nichts angefasst, nichts korrigiert.

Wachstumslog: eine Zeile eingetragen, Short zpqk0P3GIJc (136 Aufrufe in
Analytics gegen 195 oeffentlich, 34 s, 104,35 Prozent gesehener Anteil,
1 neuer Abo). Offen bleibt 6TfVlsBJtQs (46,0 h), die 48-Stunden-Marke faellt
heute auf 11:00 utc, also nach dem Checkzeitpunkt, Zeile kommt am 16.11.
Diff: 119 Einfuegungen, 0 Loeschungen.

Reels: keine Zeile, kein Reel im Fenster 48 bis 72 Stunden, keine
Reel-Ansicht faellig (keine Skip-Rate ueber 80 Prozent). Dfry_BqJvHr vom
13.11. 14:00 utc steht bei 43,0 h und wird am 16.11. faellig, DfulgX6J1uU vom
14.11. 16:00 utc bei 17,0 h. Instagram-Follower 155 (14.11.: 151), netto
plus vier.

Wachstumslog liegt auf Branch claude/wachstumslog-2026-11-15, Commit
f6d6d415e8d0ef2b0dbbcfe08b3eb5b33bb79d0e.

Ablage: claude/ablage-automatik-pruefung, Head = der Commit, der diese Datei
traegt (Hash steht in der Meldung an Ben).

## Einzelheiten

- NOD-Workflow number-of-day.yml: Lauf 338 hat die Doppellauf-Sperre nicht
  ausgeloest, alle Schritte von "pick the number" ueber "render", "archive
  dated copy", "post to discord and telegram", "seitenstand und sitemap" bis
  "commit" und "upload for download" stehen auf success. Der Nachzuegler um
  09:42 utc war zum Checkzeitpunkt noch nicht faellig; die Sperre haelt ihn
  ab, wenn er kommt.
- Letzter Lauf vor der Pruefung war Lauf 337 (Run-ID 43613795162) vom
  14.11. 16:06 utc, success.
- Haengender Lauf: eine Abfrage aller Laeufe in kaspa-pulse mit status=queued
  gibt genau einen zurueck, den bekannten Lauf 166 vom 07.10. Nicht gemeldet,
  nicht angefasst.
- Kanal Kaspa Pulse: 121 Abos, 20.353 Aufrufe, 64 Videos (14.11.: 121 Abos,
  20.158 Aufrufe, 64 Videos). Abos und Videozahl unveraendert, Aufrufe plus
  195. Seit dem Short vom 13.11. kein neues Video.
- Der gesehene Anteil von zpqk0P3GIJc liegt mit 104,35 Prozent erstmals ueber
  100 Prozent, bisher hoechster Wert war 87,63 Prozent (2FmcA5-WBJU, 13.11.).
- Analytics fuehrt fuer zpqk0P3GIJc einen Kommentar, die oeffentliche
  Zaehlung null; beides so uebernommen, nichts geschaetzt.
- Impressionen und Klickrate bleiben offen, die gibt die Schnittstelle
  grundsaetzlich nicht heraus.
- Kanal Pulse Hawk: kein neues Video, kein vidIQ-Analytics-Zugang, bekannt
  und nicht als Fehler gewertet.
- Sonntag, deshalb keine Kanalzeile und kein Uhrwerk-Bericht. Der naechste
  ist morgen, am 16.11., dran.
- Nichts repariert, nichts umgestellt, keine Workflow-Datei angefasst, kein
  Post von Hand.
