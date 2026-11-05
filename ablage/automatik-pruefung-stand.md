# Automatik-Pruefung, Stand

**Zeitpunkt: Donnerstag, 05.11.2026, 10:15 Berlin** (09:15 utc).

Kein Montagslauf, deshalb ohne Uhrwerk-Bericht und ohne Kanalzeile.

## Meldung an Ben

NOD: heute lag bis 08:41 utc kein Lauf vor, die Pruefung hat genau einmal gestartet, Lauf 288 (Run-ID 41996427957, workflow_dispatch), gruen, 57 Sekunden.
X-Post: nein, und zwar nach Bauart, nicht durch einen Fehler; der Schritt "pick the number" schreibt "kein post heute. alle kandidaten mit zahlen stehen noch in ihrer sperrfrist (whale_weight, mined_left, blocks_per_day)", Log-Eintrag fuer den 05.11. ist candidate "none", letzter Post bleibt nod-2026-11-04.
Datenstaende: Kerzen gruen (kas-candles.json auf 05.11. 07:18 utc), Multibagger einen Handelstag hinten, Schlusskurs 03.11. bei letztem Handelstag 04.11., last_run 04.11., der heutige Scanner-Lauf steht noch aus; nicht repariert.
Wachstumslog: zwei Zeilen, Short MMAsFwslJpo (177 Aufrufe, 23 s / 69,7 % gesehen, 1 Like, 1 Kommentar, 0 neue Abos) und Nachtrag Weekly Yj_0S7wFLos (59 Aufrufe, 105 s / 43,1 % gesehen, 5 Likes, 1 Kommentar, 0 neue Abos), weil die Zeile am 04.11. bei 0 Credits ganz offen blieb; Impressionen und Klickrate bleiben offen, die gibt es nur in Studio; Diff: 104 Einfuegungen, 0 Loeschungen; Branch claude/wachstumslog-2026-11-05, Commit 6f6bb5d.
Reels: 0 eingetragen, kein Reel im Fenster 02.11. 09:00 bis 03.11. 09:00 utc; DfRvUSoDSV8 (45,9 h) und DfSFWWmIem- (42,6 h) erreichen die 48 Stunden erst heute nach der Pruefung und sind morgen faellig; keine Reel-Ansicht faellig.
vidIQ liefert wieder: 2.054 Credits, richtiges Konto, Kanal Kaspa Pulse freigegeben (119 Abos), Instagram kaspapulse mit Owner-Insights; der Ausfall vom 02. bis 04.11. ist beendet, Punkte 1 und 2 der letzten Ablage sind erledigt.
Haengende Laeufe: keiner ausser dem bekannten.
Ablage: claude/ablage-automatik-pruefung, Head <dieser Commit>

## Belege

- NOD-Lauf 288, Run-ID 41996427957, `workflow_dispatch`, 08:41:32 bis
  08:42:29 utc, Schluss `success`. Kein zweiter Start.
- Schritte des Laufs: `pick the number` `success`, danach `render`,
  `archive dated copy`, `post to discord and telegram` und `post to x`
  alle `skipped`. Die Zeile aus dem Log von `pick the number`: *kein post
  heute. alle kandidaten mit zahlen stehen noch in ihrer sperrfrist
  (whale_weight, mined_left, blocks_per_day). heute faellt der post aus,
  das ist besser als dieselbe zahl zweimal.*
- `data/number-of-day-log.json`, neuer Eintrag `date` 2026-11-05,
  `candidate` **none**. Der Commit des Laufs (a6bc788) beruehrt
  `data/x-post-log.json` nicht; letzter Eintrag dort bleibt
  `nod-2026-11-04`, Post-ID 2117900311910367343.
- `data/kas-candles.json`, Feld `updated`: `2026-11-05 07:18 utc`.
- pulsehawk-site `data/multibagger-pick.json`: `date` 2026-11-04, Pick MXL,
  Feld `d` (Schlusskurs) **2026-11-03**; `multibagger-state.json`:
  `last_run` 2026-11-04, Cursor 170. Der Scan-Commit lief zuletzt am 04.11.
  14:29 utc; die elf Commits davor liegen zwischen 10:58 und 14:57 utc,
  also stets vor dem US-Schluss. Das Muster ist bauartbedingt, nicht neu.
- `vidiq_balance`: `totalCredits` 2054, `renewableCredits` 2000 von 2000,
  `addOnCredits` 54 von 150, `renewableResetsAt` 2026-12-03T12:57:46Z.
- `vidiq_user_channels`: das hinterlegte Konto, ein Kanal, Kaspa Pulse
  `UCLheLoijZUZOE79vRtJtJ9Q`, 119 Abos, 18.390 Aufrufe, 54 Videos.
  `vidiq_instagram_connected_accounts`: `kaspapulse`, `accessLevel` owner,
  `tokenStatus` active, `ownerInsightsAvailable` true,
  `publishingAvailable` false. Damit ist der Stand vom 02. bis 04.11.
  (0 Credits, falsches Konto, leere Instagram-Liste) aufgehoben.
- Fenster-Rechnung zur Stichzeit 05.11. 09:00 utc: Short `MMAsFwslJpo`
  (02.11. 16:00 utc) 65,0 h alt, 48-h-Marke am 04.11. 16:00 utc passiert,
  Zeile heute eingetragen. Short `ImyB-3dS_ns` (03.11. 11:00 utc) 46,0 h
  alt und Short `C3zATJEVIIY` (03.11. 14:27 utc) 42,6 h alt, beide
  erreichen die 48 Stunden erst heute spaeter, nicht vorgezogen. Weekly
  `Yj_0S7wFLos` (02.11. 15:00 utc) 66,0 h alt, Zeile am 04.11. offen
  eingetragen, heute als Nachtrag mit Werten ergaenzt; die alte Zeile
  bleibt unangetastet.
- Werte je Video: `vidiq_channel_videos` liefert den oeffentlichen
  Zaehler (Short 177, Weekly 59), `vidiq_channel_analytics` mit
  `dimensions=['video']` fuer 02. bis 05.11. die Analytics-Sicht (Short
  112 Aufrufe, 23 s, 69,71 %; Weekly 39 Aufrufe, 105 s, 43,12 %), je
  `subscribersGained` 0. Eingetragen ist der oeffentliche Zaehler, die
  Abweichung ist die noch offene Verbuchung des heutigen Tages.
- Impressionen und Klickrate bleiben offen: `vidiq_video_stats` gibt
  Aufrufe, Likes, Kommentare und VPH, `vidiq_channel_analytics` zusaetzlich
  `averageViewDuration`, `averageViewPercentage` und `subscribersGained`.
  Eine Thumbnail-Impression oder eine Impressions-Klickrate gibt die
  YouTube-Analytics-Schnittstelle nicht heraus. Grenze des Werkzeugs, kein
  fehlender Abruf.
- Reel-Fenster 48 bis 72 h = 02.11. 09:00 bis 03.11. 09:00 utc.
  `vidiq_instagram_owner_insights` (Konto kaspapulse, recentMediaLimit 12,
  0 Credits) fuehrt als juengste Reels `DfSFWWmIem-` vom 03.11.
  14:21 utc und `DfRvUSoDSV8` vom 03.11. 11:08 utc, danach `DfHcdXkFYl5`
  vom 30.10., das am 02.11. eingetragen ist. Im Fenster liegt keines.
  Beide 03.11.-Reels sind morgen faellig. Die Ankuendigung vom 04.11., das
  Reel vom 03.11. werde am 05.11. faellig, war um die Tageszeit
  danebengelegen.
- Keine Reel-Ansicht faellig: ohne Reel im Fenster gibt es keine Skip-Rate
  ueber 80 %, die eine Ansicht ausloesen koennte.
- Haengende Laeufe: `queued` nur Lauf 166 (bekannter Fall vom 07.10.).
  `in_progress`: `bch tempnet lauscher` Lauf 48 (seit heute 07:37 utc,
  1,5 h), `entity-x-alert` Lauf 1234 (seit 04:52 utc, 4,2 h, laeuft nach
  Bauart rund 5 Stunden) und `miner nach cut` Lauf 1 (seit 03.11.
  18:55 utc, Kette von 24 Laeufen im Abstand von rund 7,5 Stunden,
  Fortschritt zuletzt 03:28 utc). Kein Haenger.
- Kanal Pulse Hawk `UCk3Vebx2srRl6Eau2CwJq2w`: `vidiq_channel_videos` gibt
  keine langen Videos zurueck, juengster Short vom 14.09.2026. Kein neues
  Video.

## Was Ben tun muss

1. **Nichts dringend.** Die beiden Punkte der letzten Ablage sind
   erledigt: vidIQ hat wieder Guthaben und haengt wieder am richtigen
   Konto, Kaspa Pulse ist freigegeben, Instagram ist verbunden.
2. **Kein X-Post heute, zur Kenntnis.** Die Sperrfrist hat alle drei
   Kandidaten mit Zahlen gleichzeitig blockiert. Einmal ist das die
   gewollte Bremse gegen dieselbe Zahl zweimal. Haeuft es sich an mehreren
   Tagen in Folge, ist der Kandidatenvorrat zu klein, und das waere ein
   Fall fuer einen PR, nicht fuer die Pruefung.
3. **Multibagger liegt einen Handelstag hinten.** Der Scanner laeuft
   mittags, vor dem US-Schluss; das ist bauartbedingt. Wenn der Stand nach
   dem heutigen Lauf nicht auf dem Schlusskurs vom 04.11. steht, ist es
   mehr als eine Laufzeit-Frage.
4. **Ablage-Branch und automerge.** `automerge-claude.yml` holt jeden Push
   auf `claude/**` nach main und loescht den Branch. Ein dauerhafter
   Ablage-Branch mit Force-Push ist in diesem Repo dadurch nicht moeglich;
   die Datei landet stattdessen in main. Nichts umgestellt.
