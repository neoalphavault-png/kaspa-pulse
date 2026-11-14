# Automatik-Pruefung, aktueller Stand

Stand: Samstag, 14.11.2026, 10:10 Uhr Berlin-Zeit (09:10 utc).
Geprueft wurde von 09:41 bis 10:10 Berlin (08:41 bis 09:10 utc).
Lauf gruen, kein roter Lauf, keine Unsicherheit.

## Meldung an Ben, woertlich

NOD: heute lag bis 08:41 utc kein Lauf vor, deshalb von der Pruefung genau
einmal gestartet (workflow_dispatch auf main, Antwort 204 queued), kein
zweiter Start, nicht auf das Ergebnis gewartet.

X-Post: nein, nach Vorgabe pausiert (X_GOKU_AN steht auf false, Schritt
"post to x" ist skipped), letzter Eintrag bleibt nod-2026-11-08.

Datenstaende: ok. kas-candles.json auf 2026-11-14 06:57 utc, letzte
Tageskerze 13.11.; multibagger-pick.json date 2026-11-13, state last_run
2026-11-13, Scan committet nachmittags, also planmaessig der Vortagslauf.

Wachstumslog: zwei Zeilen eingetragen, Short 7BkVbLxaIGc (88 Aufrufe,
24 s, 67,26 Prozent gesehen, 0 neue Abos) und Erklaerer SFcWhABVOfg
(Analytics liefert noch nichts, deshalb alles offen ausser 110
oeffentlichen Aufrufen). Offen bleiben zpqk0P3GIJc (46,0 h) und
6TfVlsBJtQs (22,0 h), beide noch nicht faellig. Diff: 128 Einfuegungen,
0 Loeschungen.

Reels: keine Zeile, kein Reel im Fenster 48 bis 72 Stunden, keine
Reel-Ansicht faellig. Neu: am 13.11. 14:00 utc ist nach fuenf Tagen Pause
wieder ein Reel erschienen (Dfry_BqJvHr, 488 Aufrufe, Skip-Rate 62,7
Prozent), es wird am 15. oder 16.11. faellig.

Nebenbei: der am 13.11. gemeldete haengende Lauf "monero stressnet dauer"
(Run-ID 42374283536) ist fertig, completed und success, zuletzt
aktualisiert 14.11. 07:39 utc. Es bleibt nur der bekannte Lauf 166.
Wachstumslog liegt auf Branch claude/wachstumslog-2026-11-14, Commit
3d16c9736829f10ee6aa6e91e59b1f9284517d02.

## Einzelheiten

- NOD-Workflow number-of-day.yml: letzter Lauf vor der Pruefung war Lauf 332
  (Run-ID 43472198854) vom 13.11. 17:22 utc, success, aber ohne Arbeit, weil
  die Doppellauf-Sperre gegriffen hat. Letzter Lauf mit echter Arbeit war
  Lauf 328 vom 13.11. 08:41 utc.
- graphics/archive/2026-11-14.png lag zum Pruefzeitpunkt nicht auf main,
  juengster Stand 2026-11-13.png. Der heute gestartete Lauf hat also Arbeit.
- Kanal Kaspa Pulse: 121 Abos, 20.158 Aufrufe, 64 Videos (13.11.: 121 Abos,
  19.694 Aufrufe, 63 Videos).
- Instagram kaspapulse: 151 Follower (13.11.: 146), netto plus fuenf.
- Kanal Pulse Hawk: kein neues Video, kein vidIQ-Analytics-Zugang, bekannt
  und nicht als Fehler gewertet.
- Samstag, deshalb keine Kanalzeile und kein Uhrwerk-Bericht.
- Nichts repariert, nichts umgestellt, keine Workflow-Datei angefasst, kein
  Post von Hand.
