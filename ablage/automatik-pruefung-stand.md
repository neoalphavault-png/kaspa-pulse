# Stand der taeglichen Automatik-Pruefung

Zeitpunkt: 13.11.2026, 09:41 bis 10:00 Uhr Berlin-Zeit (08:41 bis 09:00 utc).
Freitag, also kein Uhrwerk-Bericht.

## Meldung an Ben

1. NOD: heute lag bis 08:41 utc kein Lauf vor, deshalb von der Pruefung genau
   einmal gestartet (workflow_dispatch auf main) -- Lauf 328, Run-ID
   43395205821, gruen durchgelaufen 08:41:35 bis 08:42:14 utc. Kein zweiter
   Start. (Lauf 327 vom 12.11. 17:44 utc steht auf success, hat aber nichts
   getan: Die Doppellauf-Sperre hat gegriffen, alle Schritte danach skipped.)
2. X-Post: nein. `x pausiert` gruen, `post to x` bleibt `skipped`, der
   Schalter X_GOKU_AN steht weiter auf Bens Pause vom 07.11.; letzter Eintrag
   in data/x-post-log.json ist nod-2026-11-08, Post-ID 2119349802983125215.
   Kein Fehler, sondern der Schalter.
3. Datenstaende: ok. data/kas-candles.json auf 13.11. 07:09 utc (also heute),
   letzte Tageskerze 12.11.; multibagger-pick.json date 2026-11-12 und
   multibagger-state.json last_run 2026-11-12, Cursor 1321 -- Donnerstag war
   der letzte geschlossene Handelstag. Nichts repariert.
4. Wachstumslog: eingetragen wurde genau eine Zeile, der Short 2FmcA5-WBJU
   vom 10.11. 11:00 utc (69,9 h alt; 66 Aufrufe und 22 engagedViews in
   Analytics, 159 oeffentlich, 29 s durchschnittliche Wiedergabedauer,
   87,63 Prozent gesehener Anteil, 1 Like, 1 Kommentar, 0 neue Abos;
   Impressionen und Klickrate wie immer offen). Noch nicht faellig und
   deshalb nicht eingetragen: Short 7BkVbLxaIGc (48-h-Marke heute 11:00 utc),
   Short zpqk0P3GIJc (14.11. 11:00 utc) und der Erklaerer SFcWhABVOfg vom
   12.11. 22:01 utc (24-h-Marke heute 22:01 utc). Diff: 106 Einfuegungen,
   0 Loeschungen. Branch claude/wachstumslog-2026-11-13, Commit f18db03.
5. Reels: 0 eingetragen. Kein Reel im Fenster 48 bis 72 Stunden (10.11. 08:55
   bis 11.11. 08:55 utc); juengstes Reel ist weiter DffDJnHo7UR vom 08.11.
   15:18 utc, 113,6 h alt und am 11.11. eingetragen. Seit dem 08.11. kein
   neues Reel, das sind fuenf Tage ohne Instagram-Veroeffentlichung.
   Instagram-Follower 146 (12.11.: 145). Keine Zwei-Satz-Notiz faellig, da
   keine Skip-Rate im Fenster zu pruefen war.
6. Haengender Lauf: `monero stressnet dauer` Lauf 1, Run-ID 42374283536, steht
   seit 07.11. 12:51 utc auf queued, rund 140 Stunden, Branch
   messung/monero-stressnet. Nicht angefasst. Ben entscheidet.
7. Kanal Kaspa Pulse: 121 Abos, 19.694 Aufrufe, 63 Videos (12.11.: 120 Abos,
   19.638 Aufrufe, 61 Videos). Pulse Hawk wie bekannt ohne neues Video und
   ohne vidIQ-Analytics-Zugang, nicht als Fehler gewertet.

## Hinweis zur Ablage selbst

Dieser Branch faellt unter automerge-claude.yml: Der Push landet per Merge auf
main, danach wird der Branch geloescht. Die Ablage ist deshalb unter
ablage/automatik-pruefung-stand.md auf main zu finden, so wie am 12.11. Der
unten genannte Head-Commit bleibt gueltig.
