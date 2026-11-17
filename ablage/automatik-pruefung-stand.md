# Automatik-Pruefung, aktueller Stand

Stand: Dienstag, 17.11.2026, 10:05 Uhr Berlin-Zeit (09:05 utc).
Geprueft wurde von 09:42 bis 10:05 Berlin (08:42 bis 09:05 utc).
Lauf gruen, kein roter Lauf, keine Unsicherheit. Dienstag, deshalb ohne
Kanalzeile und ohne Uhrwerk-Bericht.

## Meldung an Ben, woertlich

NOD: heute lag bis 08:42 utc kein Lauf vor, deshalb von der Pruefung genau
einmal gestartet (workflow_dispatch auf main, Antwort 204 queued), kein
zweiter Start. Lauf 348, Run-ID 44049136588, 08:43:14 bis 08:44:18 utc,
conclusion success.

X-Post: nein. Schritt "post to x" steht auf skipped, "x pausiert" auf
success, beide an der Bedingung X_GOKU_AN, im Lauf-Log auf false. Das ist
die Pause, die Ben am 07.11.2026 gesetzt hat, kein Fehler. Letzter Eintrag
in data/x-post-log.json bleibt nod-2026-11-08, insgesamt 53 Eintraege.

Datenstaende: abweichend. data/kas-candles.json steht auf 2026-11-17
08:24 utc, also auf heute, das ist in Ordnung. multibagger-pick.json in
pulsehawk-site traegt date 2026-11-16 (Pick MRNA, Moderna, mult 8,9491),
der Schlusskurs darin stammt aber vom 13.11., und multibagger-state.json
meldet last_run 2026-11-16 (Cursor 1143). Heute ist Dienstag, letzter
geschlossener Handelstag war Montag der 16.11. Der Montag ist im Pick
nicht angekommen; der Scan committet gegen 13 bis 15 utc, der heutige Lauf
steht also noch aus. Nur gemeldet, nichts korrigiert.

Wachstumslog: heute war keine YouTube-Zeile faellig. Das Weekly
Dz30qv1Ch5Y vom 16.11. 15:00 utc erreicht die 24-Stunden-Marke erst heute
um 15:00 utc, der Short RORbbV3uPWw vom 16.11. 16:00 utc die
48-Stunden-Marke am 18.11. um 16:00 utc. Beide sind damit nicht
vorgezogen. Offen: keine. Diff: 80 Einfuegungen, 0 Loeschungen, nur
docs/projekt/wachstum-log.md geaendert. Branch
claude/wachstumslog-2026-11-17, Commit 641251e.

Reels: 1 eingetragen, DfulgX6J1uU vom 14.11. 16:00 utc (Alter 64,8 h,
3.826 Aufrufe, Skip-Rate 64,5 %, geschauter Anteil 56,1 %, 3,4 s
durchschnittliche Wiedergabezeit, 29 Likes, 0 Kommentare, 2 Teilen,
1 Speichern, Trial nein). Die Skip-Rate liegt unter 80 %, deshalb war
heute keine Ansicht mit vidiq_watch_shortform_content faellig und keine
Zwei-Satz-Notiz. Dfw__UGpt7R vom 15.11. ist mit 42,3 h noch zu jung und
morgen faellig.

Ablage: claude/ablage-automatik-pruefung, Head siehe Commit dieser Datei.

## Weitere Festhaltungen

Haengende Laeufe: die Abfrage mit status=queued gibt genau einen zurueck,
den bekannten Lauf 166 vom 07.10.2026, der nach Vorgabe nicht gemeldet und
nicht angefasst wird. Kein anderer haengender Lauf.

Kanal Kaspa Pulse UCLheLoijZUZOE79vRtJtJ9Q: 121 Abos, 20.712 Aufrufe,
66 Videos (16.11.: 120 Abos, 20.533 Aufrufe, 64 Videos). Abos plus eins,
Aufrufe plus 179, Videos plus zwei. Guthaben vidIQ 669 (615 erneuerbar,
54 Zusatz).

Kanal Pulse Hawk: weiter kein Video im Fenster und kein
vidIQ-Analytics-Zugang. Nach Vorgabe kein Fehler und keine Unsicherheit.

Instagram kaspapulse: connectionActive true, Recht
instagram_business_manage_insights vorhanden, Follower 161.

Nichts gestartet ausser dem einen Tageslauf, nichts abgebrochen, keine
Daten korrigiert, kein Post von Hand, keine Workflow-Datei angefasst.
