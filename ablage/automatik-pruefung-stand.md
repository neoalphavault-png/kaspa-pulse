# Automatik-Pruefung, Stand

**Zeitpunkt: Mittwoch, 04.11.2026, 09:55 Berlin** (08:55 utc).

Kein Montagslauf, deshalb ohne Uhrwerk-Bericht und ohne Kanalzeile.

## Meldung an Ben

Unsicherheit zuerst: vidIQ-Guthaben steht auf 0 von 150, Reset 24.11. 19:14 utc, bis dahin keine vidIQ-Werte, auch keine oeffentlichen; Kaspa Pulse ist am verbundenen Konto nicht freigegeben, Instagram-Liste leer, youtube.com aus dieser Umgebung nicht erreichbar; Kanal Pulse Hawk daher heute nicht pruefbar; Ablage-Branch wird von automerge-claude.yml sofort nach main geholt und geloescht.
NOD: heute lag bis 08:41 utc kein Lauf vor, die Pruefung hat genau einmal gestartet, Lauf 283 (Run-ID 41801497007, workflow_dispatch), gruen, 52 Sekunden.
X-Post: ja, nod-2026-11-04, Post-ID 2117900311910367343, 04.11. 08:42:37 utc.
Datenstaende: Kerzen gruen (kas-candles.json auf 04.11. 06:55 utc), Multibagger abweichend, Schlusskurs 02.11. bei letztem Handelstag 03.11., last_run 03.11., der heutige Scanner-Lauf steht noch aus; nicht repariert.
Wachstumslog: eine Zeile eingetragen, Weekly Yj_0S7wFLos (02.11. 15:00 utc, 41,8 h alt), alle elf Werte offen, weil vidIQ bei 0 Credits auch oeffentlich nichts liefert; Short MMAsFwslJpo wird am 04.11. 16:00 utc faellig, also morgen; Diff: 88 Einfuegungen, 0 Loeschungen; Branch claude/wachstumslog-2026-11-04, Commit 6f42e71.
Reels: 0 eingetragen, kein Reel im Fenster 01.11. 08:45 bis 02.11. 08:45 utc, keine Reel-Ansicht faellig.
Haengende Laeufe: keiner ausser dem bekannten.
Ablage: claude/ablage-automatik-pruefung, Head <dieser Commit>

## Belege

- NOD-Lauf 283, Run-ID 41801497007, `workflow_dispatch`, 08:41:53 bis
  08:42:45 utc, Schluss `success`. Kein zweiter Start.
- `data/x-post-log.json`, Eintrag `nod-2026-11-04`, Post-ID
  2117900311910367343, `posted_at` 2026-11-04T08:42:37Z.
- `data/kas-candles.json`, Feld `updated`: `2026-11-04 06:55 utc`.
- pulsehawk-site `data/multibagger-pick.json`: `date` 2026-11-03, Pick MRNA,
  Feld `d` (Schlusskurs) **2026-11-02**; `multibagger-state.json`:
  `last_run` 2026-11-03, Cursor 964; `multibagger-universe.json`: `date`
  2026-10-30. Der Scan-Commit lief zuletzt am 03.11. 14:15 utc; die vier
  Commits davor liegen zwischen 12:24 und 14:57 utc, also stets vor dem
  US-Schluss. Das Muster ist damit bauartbedingt, nicht neu.
- `vidiq_balance`: `totalCredits` 0, `renewableCredits` 0 von 150,
  `addOnCredits` 0, `renewableResetsAt` 2026-11-24T19:14:21Z. Unveraendert
  gegenueber dem 03.11.
- `vidiq_user_channels`: `authenticatedAs` neo.alphavault@gmail.com, ein
  Kanal "Entrepreneurs Unveiled"; Kaspa Pulse nicht freigegeben.
  `vidiq_instagram_connected_accounts`: leere Liste. Stand unveraendert
  gegenueber dem 02.11.
- Oeffentlicher Ersatzweg geprueft und nicht verfuegbar: Abruf des
  YouTube-Kanal-Feeds endet im CONNECT-Tunnel mit 403.
- Fenster-Rechnung zur Stichzeit 04.11. 08:45 utc: Weekly `Yj_0S7wFLos`
  (02.11. 15:00 utc) 41,8 h alt, 24-h-Marke am 03.11. 15:00 utc passiert,
  Zeile heute eingetragen. Short `MMAsFwslJpo` (02.11. 16:00 utc) 40,8 h
  alt, 48-h-Marke erst 04.11. 16:00 utc, nicht vorgezogen.
- Videoliste nicht erneuerbar: beide Eintraege stammen aus dem
  vidIQ-Abruf vom 03.11., dem letzten, der durchging. Ob am 03.11. ein
  weiterer Short erschien, ist von hier aus nicht pruefbar; seine
  48-h-Marke laege erst am 05.11.
- Reel-Fenster 48 bis 72 h = 01.11. 08:45 bis 02.11. 08:45 utc. Der
  Sammler in pulse-studio (`data/insights/manifest.jsonl`) fuehrt als
  Reels den 30.10. 11:11 utc und den 03.11. 11:09 utc (`DfRvUSoDSV8`),
  dazwischen keinen. Das Reel vom 03.11. wird am 05.11. faellig.
- Haengende Laeufe: `queued` nur Lauf 166 (bekannter Fall vom 07.10.).
  `in_progress`: `entity-x-alert` Lauf 1227 (seit 06:32 utc, 2,2 h, laeuft
  nach Bauart rund 5 Stunden) und `miner nach cut` Lauf 1 (seit 03.11.
  18:55 utc, Kette von 24 Laeufen im Abstand von rund 7,5 Stunden,
  Fortschritt zuletzt 08:29 utc). Kein Haenger.

## Was Ben tun muss

1. **vidIQ-Guthaben ist leer** und erneuert sich erst am 24.11. Solange
   bleibt jede Videozeile offen, auch die oeffentlichen Aufrufzahlen. Die
   heute faellige Weekly-Zeile ist deshalb die erste, die ganz leer in der
   Datei steht.
2. **vidIQ haengt weiter am falschen Konto** (neo.alphavault@gmail.com,
   Kaspa Pulse nicht freigegeben, kein Instagram-Konto verbunden).
   Unveraendert seit dem 02.11. Ohne diese Freigabe bleibt Schritt 7
   (Instagram-Reels) dauerhaft ohne Werte.
3. **Multibagger liegt einen Handelstag hinten.** Der Scanner laeuft
   mittags, vor dem US-Schluss; das ist bauartbedingt. Wenn der Stand nach
   dem heutigen Lauf nicht auf dem Schlusskurs vom 03.11. steht, ist es
   mehr als eine Laufzeit-Frage.
4. **Ablage-Branch und automerge.** `automerge-claude.yml` holt jeden Push
   auf `claude/**` nach main und loescht den Branch. Ein dauerhafter
   Ablage-Branch mit Force-Push ist in diesem Repo dadurch nicht moeglich;
   die Datei landet stattdessen in main. Nichts umgestellt.
