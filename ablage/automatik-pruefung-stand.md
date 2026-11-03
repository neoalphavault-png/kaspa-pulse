# Automatik-Pruefung, Stand

**Zeitpunkt: Dienstag, 03.11.2026, 10:05 Berlin** (09:05 utc).

Kein Montagslauf, deshalb ohne Uhrwerk-Bericht und ohne Kanalzeile.

## Meldung an Ben

Unsicherheit zuerst: vidIQ-Guthaben steht auf 0 von 150, Reset 24.11. 19:14 utc, bis dahin keine vidIQ-Werte, auch keine oeffentlichen; Kanal Pulse Hawk daher heute nicht pruefbar; Ablage-Branch wird von automerge-claude.yml sofort nach main geholt und geloescht.
NOD: heute lag bis 08:41 utc kein Lauf vor, die Pruefung hat genau einmal gestartet, Lauf 278 (Run-ID 41605223692, workflow_dispatch), gruen, 59 Sekunden.
X-Post: ja, nod-2026-11-03, Post-ID 2117537996362936556, 03.11. 08:42:55 utc.
Datenstaende: Kerzen gruen (kas-candles.json auf 03.11. 07:11 utc), Multibagger abweichend, Schlusskurs 30.10. bei letztem Handelstag 02.11., last_run 02.11., der heutige Scanner-Lauf steht noch aus; nicht repariert.
Wachstumslog: keine Zeile faellig, Weekly Yj_0S7wFLos erreicht die 24 h erst heute 15:00 utc, Short MMAsFwslJpo die 48 h am 04.11. 16:00 utc, Short 0IpwOkAi42A und Erklaerer YvM8g-3r-Jg stehen schon drin; Diff: 78 Einfuegungen, 0 Loeschungen; Branch claude/wachstumslog-2026-11-03, Commit bb80076.
Reels: 0 eingetragen, kein Reel im Fenster 31.10. 08:41 bis 01.11. 08:41 utc, nur Bild-Beitraege, keine Reel-Ansicht faellig.
Haengende Laeufe: keiner ausser dem bekannten.
Ablage: claude/ablage-automatik-pruefung, Head <dieser Commit>

## Belege

- NOD-Lauf 278, Run-ID 41605223692, `workflow_dispatch`, 08:42:04 bis
  08:43:03 utc, Schluss `success`. Kein zweiter Start.
- `data/x-post-log.json`, Eintrag `nod-2026-11-03`, Post-ID
  2117537996362936556, `posted_at` 2026-11-03T08:42:55Z.
- `data/kas-candles.json`, Feld `updated`: `2026-11-03 07:11 utc`.
- pulsehawk-site `data/multibagger-pick.json`: `date` 2026-11-02, Pick MRNA,
  Feld `d` (Schlusskurs) **2026-10-30**; `multibagger-state.json`:
  `last_run` 2026-11-02, Cursor 261; `multibagger-universe.json`: `date`
  2026-10-30. Scanner `multibagger.yml` ("365 days later scanner") lief
  zuletzt 02.11. 13:23 bis 14:57 utc, `success`.
- `vidiq_balance`: `totalCredits` 0, `renewableCredits` 0 von 150,
  `addOnCredits` 0, `renewableResetsAt` 2026-11-24T19:14:21Z. Gestern 95.
  Zwei Abrufe gingen durch (je 5 Credits), der dritte wurde mit
  "Not enough credits" abgewiesen.
- `vidiq_user_channels`: `authenticatedAs` neo.alphavault@gmail.com, ein
  Kanal "Entrepreneurs Unveiled"; Kaspa Pulse nicht freigegeben.
  `vidiq_instagram_connected_accounts`: leere Liste. Stand unveraendert
  gegenueber dem 02.11.
- Fenster-Rechnung zur Stichzeit 03.11. 08:41 utc: Weekly `Yj_0S7wFLos`
  (02.11. 15:00 utc) 17,7 h alt, 24-h-Marke 03.11. 15:00 utc. Short
  `MMAsFwslJpo` (02.11. 16:00 utc) 16,7 h alt, 48-h-Marke 04.11. 16:00 utc.
- Reel-Fenster 48 bis 72 h = 31.10. 08:41 bis 01.11. 08:41 utc.
  `data/insights/manifest.jsonl` fuehrt fuer Instagram am 30.10., 31.10.,
  02.11. und 03.11. je einen Beitrag im Format `bild`, fuer den 01.11.
  keinen. Jueneste Reel-Messung im Sammler: Veroeffentlichung 30.10.
  11:10 utc, am 02.11. eingetragen.
- Haengende Laeufe: `queued` nur Lauf 166 (bekannter Fall vom 07.10.).
  `in_progress`: `bch tempnet lauscher` Lauf 42 (seit 08:29 utc),
  `entity-x-alert` Lauf 1219 (seit 08:11 utc), `kcc20 zaehlung` Lauf 7
  (seit 07:21 utc, wartet nach Bauart auf die Stichzeit 03.11. 12:00 utc).
  Kein Haenger.

## Was Ben tun muss

1. **vidIQ-Guthaben ist leer** und erneuert sich erst am 24.11. Bis dahin
   bleiben alle vidIQ-Werte offen, auch die oeffentlichen Aufrufzahlen, mit
   denen die Pruefung bisher die Short-Zeilen gefuellt hat.
2. **vidIQ haengt weiter am falschen Konto** (neo.alphavault@gmail.com,
   Kaspa Pulse nicht freigegeben, kein Instagram-Konto verbunden).
   Unveraendert seit dem 02.11.
3. **Multibagger liegt einen Handelstag hinten.** Nach dem heutigen
   Scanner-Lauf sollte der Stand auf dem Schlusskurs vom 02.11. stehen.
   Wenn nicht, ist es mehr als eine Laufzeit-Frage.
4. **Ablage-Branch und automerge.** `automerge-claude.yml` holt jeden Push
   auf `claude/**` nach main und loescht den Branch. Ein dauerhafter
   Ablage-Branch mit Force-Push ist in diesem Repo dadurch nicht moeglich;
   die Datei landet stattdessen in main. Nichts umgestellt.
