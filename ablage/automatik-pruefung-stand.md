# Automatik-Pruefung, Stand

**Zeitpunkt: Freitag, 06.11.2026, 10:05 Berlin** (09:05 utc).

Kein Montagslauf, deshalb ohne Uhrwerk-Bericht und ohne Kanalzeile.

## Meldung an Ben

NOD: heute lag bis 08:41 utc kein Lauf vor, die Pruefung hat genau einmal gestartet, Lauf 293 (Run-ID 42189529493, workflow_dispatch, Start 08:41:51 utc); der Lauf stand beim Schreiben noch auf in_progress, nach Vorgabe wird nicht gewartet, der Ausgang steht morgen hier.
X-Post: heute noch offen, weil der Lauf noch laeuft; letzter Eintrag in data/x-post-log.json bleibt nod-2026-11-04. Die Luecke vom 05.11. ist kein Fehler, dort traegt number-of-day-log.json candidate "none".
Datenstaende: beide ok. kas-candles.json auf 2026-11-06 07:18 utc, also heute; Multibagger in pulsehawk-site auf dem letzten Handelstag, pick.json date 2026-11-05 (Pick MRNA), state.json last_run 05.11., Cursor 874. Erstmals seit Tagen kein Rueckstand, nichts angefasst.
Wachstumslog: zwei Short-Zeilen eingetragen, ImyB-3dS_ns (316 Aufrufe, 25 s / 75,9 % gesehen, 6 Likes, 0 Kommentare, 0 neue Abos) und C3zATJEVIIY (204 Aufrufe, 15 s / 177,7 % gesehen, 4 Likes, 1 Kommentar, 1 neuer Abo); offen bleiben Impressionen und Klickrate bei beiden, die gibt es nur in Studio. Erklaerer MyGZT1BIBsc (05.11. 15:54 utc) erreicht die 24 Stunden erst heute 15:54 utc und ist morgen faellig. Diff: 107 Einfuegungen, 0 Loeschungen; Branch claude/wachstumslog-2026-11-06, Commit 3965bc0.
Reels: 2 eingetragen, DfSFWWmIem- und DfRvUSoDSV8, beide vom 03.11. und damit im Fenster 03.11. 09:00 bis 04.11. 09:00 utc; keine Reel-Ansicht faellig, beide Skip-Raten unter 80 % (65,7 und 67,8).
Haengende Laeufe: keiner ausser dem bekannten. entity-x-alert (Lauf 1241) liegt mit 5,8 h knapp ueber seiner Bauartdauer von rund 5 h, notiert, noch kein Befund.
Hinweis zur eigenen Arbeitsweise: ein erster Blick auf die Multibagger-Daten sah nach drei Tagen Rueckstand aus; Ursache war ein veralteter origin/main-Zeiger im Arbeitsklon, nicht die Automatik. Kuenftig wird der Remote-Zeiger vor jedem Datenstand-Urteil erneuert.
Ablage: claude/ablage-automatik-pruefung, Head <dieser Commit>

## Belege

- NOD-Lauf 293, Run-ID 42189529493, `workflow_dispatch`, Start
  2026-11-06 08:41:51 utc, Status beim Schreiben `in_progress`. Kein
  zweiter Start, weder jetzt noch spaeter im Lauf.
- Vorlauf: letzter Lauf davor war Lauf 292 (Run-ID 42076737506) vom
  05.11. 17:39 utc, `schedule`, `success`. Am 06.11. gab es bis 08:41 utc
  keinen Lauf, daher der eine Start.
- `data/x-post-log.json`: letzter Eintrag `nod-2026-11-04`, Post-ID
  2117900311910367343. Fuer den 05.11. steht in
  `data/number-of-day-log.json` `"candidate": "none"` -- alle Kandidaten
  standen in ihrer Sperrfrist, der Post fiel nach Bauart aus. Das ist am
  05.11. schon so festgehalten worden und ist kein offener Punkt.
- `data/kas-candles.json`, Feld `updated`: **2026-11-06 07:18 utc**.
- pulsehawk-site `data/multibagger-pick.json` Feld `date`
  **2026-11-05**, Pick MRNA; `data/multibagger-state.json`
  `last_run` **2026-11-05**, `cursor` 874. Heute ist Freitag, letzter
  Handelstag war Donnerstag der 05.11. Damit steht der Multibagger-Stand
  erstmals seit Tagen auf dem letzten Handelstag.
- Fenster Shorts (48 h) und Lang (24 h), Alter zum 06.11. 09:00 utc:

  | Was | ID | veroeffentlicht | Alter | Marke erreicht | Zeile |
  |---|---|---|---|---|---|
  | Short | ImyB-3dS_ns | 03.11. 11:00 utc | 70,0 h | 05.11. 11:00 utc | heute |
  | Short | C3zATJEVIIY | 03.11. 14:27 utc | 66,6 h | 05.11. 14:27 utc | heute |
  | Erklaerer | MyGZT1BIBsc | 05.11. 15:54 utc | 17,1 h | 06.11. 15:54 utc | morgen |
  | Short | TXxUHra5l34 | 05.11. 11:00 utc | 22,0 h | 07.11. 11:00 utc | am 07.11. |

- Zahlenherkunft der beiden Short-Zeilen. "YT Aufrufe" ist der
  oeffentliche Zaehler zum Checkzeitpunkt (316 und 204). YouTube
  Analytics zaehlt fuer 03. bis 06.11. weniger (170 und 105 Aufrufe,
  davon 64 und 29 `engagedViews`), weil der heutige Tag dort noch nicht
  vollstaendig verbucht ist. Beide Zahlen sind richtig, sie messen nur
  Verschiedenes.
- Die 177,7 Prozent bei C3zATJEVIIY sind kein Fehler: das Video ist 9
  Sekunden lang, die durchschnittliche Wiedergabedauer 15 Sekunden. Der
  Wert ueber 100 Prozent ist gezaehlte Wiederholung in der Schleife.
  Nicht geglaettet, nicht gekappt.
- Impressionen und Klickrate stehen weiter "offen". `vidiq_video_stats`
  liefert Aufrufe, Likes, Kommentare und VPH, `vidiq_channel_analytics`
  zusaetzlich `averageViewDuration`, `averageViewPercentage` und
  `subscribersGained`. Eine Thumbnail-Impression gibt die
  YouTube-Analytics-Schnittstelle nicht heraus. Es wird nichts
  geschaetzt.
- Reels im Fenster 48 bis 72 Stunden (03.11. 09:00 bis 04.11. 09:00
  utc), Werte aus `vidiq_instagram_owner_insights`, Konto kaspapulse,
  0 Credits:

  | Reel | veroeffentlicht | Aufrufe | Skip-Rate | geschauter Anteil | Ø Zeit | Likes | Komm. | Teilen | Speichern | Trial |
  |---|---|---|---|---|---|---|---|---|---|---|
  | DfSFWWmIem- | 03.11. 14:22 utc | 4.393 | 65,7 % | 56,6 % | 4,5 s | 101 | 6 | 8 | 3 | nein |
  | DfRvUSoDSV8 | 03.11. 11:09 utc | 408 | 67,8 % | 22,7 % | 7,5 s | 33 | 1 | 4 | 1 | nein |

- Keine Reel-Ansicht faellig: beide Skip-Raten unter 80 %. Die
  Ein-Reel-Grenze pro Tag bleibt unverbraucht. Naechstes Reel
  `DfW5XXKFAgl` vom 05.11. 11:13 utc (21,8 h) wird am 07.11. faellig.
- Ohne Handlung, nur notiert: `DfSFWWmIem-` ist mit 4.393 Aufrufen und
  56,6 % geschautem Anteil das staerkste Reel der Reihe seit Wochen und
  mit 8 Sekunden das kuerzeste; die anderen laufen 29 bis 35 Sekunden.
  Ob die Laenge die Ursache ist, entscheidet der Montagsbericht mit
  Median. Instagram-Follower 137.
- Haengende Laeufe in kaspa-pulse. `queued`: nur Lauf 166, der bekannte
  Fall vom 07.10. `in_progress`: `number of the day` (Lauf 293, von
  dieser Pruefung gestartet), `bch tempnet lauscher` (Lauf 52, seit
  05:06 utc, 3,9 h), `zcash mainnet lauscher` (Lauf 8, seit 03:49 utc,
  5,2 h), `entity-x-alert` (Lauf 1241, seit 03:13 utc, 5,8 h, Bauart
  rund 5 h) und `miner nach cut` (Lauf 1, seit 03.11. 18:55 utc,
  Fortschritt zuletzt heute 04:53 utc, Kette von 24 Laeufen im Abstand
  von rund 7,5 h). Kein Haenger.
- Kanal Pulse Hawk `UCk3Vebx2srRl6Eau2CwJq2w`: keine langen Videos,
  juengster Short weiter vom 14.09.2026. Kein neues Video.
- vidIQ-Guthaben nach dieser Pruefung: `totalCredits` 1.734
  (`renewableCredits` 1.680 von 2.000, Erneuerung 03.12.2026 12:57:46
  utc, `addOnCredits` 54 von 150).

## Was Ben tun muss

- Nichts Dringendes. Impressionen, Klickrate und die TikTok-Spalte
  bleiben Handarbeit in Studio beziehungsweise bei Ben.
- Falls `entity-x-alert` morgen wieder deutlich ueber 5 Stunden steht,
  waere ein Blick auf den Taktgeber faellig; das geht nur ueber einen PR,
  den Ben freigibt.

## Offene Fragen an Ben

- Keine.
