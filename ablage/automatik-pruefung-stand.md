# Automatik-Pruefung, Stand 18.11.2026 09:47 Berlin-Zeit

Taegliche Pruefung der Kaspa-Pulse- und PulseHawk-Automatik. Heute ist
Mittwoch, kein Uhrwerk-Bericht faellig (der kommt montags).

## Meldung an Ben

Unsicherheit: YouTube-Analytics reicht nur bis zum 15.11., der 16. bis
18.11. fehlt ganz; das Weekly vom 16.11. hat deshalb noch keine
Analytics-Werte, alle Analytics-Felder seiner Zeile stehen auf "offen".

NOD: bis 08:41 utc lag heute kein Lauf vor, deshalb hat die Pruefung
number-of-day.yml genau einmal gestartet (workflow_dispatch auf main,
Antwort 204 queued). Nicht gewartet, kein zweiter Start.

X-Post: nein, und zwar nach Vorgabe. Der Schritt "post to x" steht auf
skipped, der Schalter X_GOKU_AN im Lauf-Log auf false. Letzter Eintrag in
data/x-post-log.json bleibt nod-2026-11-08, damit fehlen zehn Tage.

Datenstaende: ok. kas-candles.json steht auf 2026-11-18 07:52 utc,
multibagger-pick.json auf 2026-11-17, dem letzten geschlossenen Handelstag.

Wachstumslog: eingetragen das Weekly Dz30qv1Ch5Y (24-h-Marke erreicht,
Analytics-Felder offen) und das Reel Dfw__UGpt7R. Nicht faellig: Short
RORbbV3uPWw (19.11.) und Short xrkFmvbq00U (20.11.). Diff: 97
Einfuegungen, 0 Loeschungen. Branch claude/wachstumslog-2026-11-18.

Reels: 1 eingetragen. Die Skip-Rate liegt mit 82,5 Prozent ueber der
Schwelle, deshalb ist die eine Ansicht gelaufen: Die erste Sekunde zeigt
einen dunklen, vernebelten Spielhallengang, in dem der Automat gerade erst
angeht, die Zahl 864.000 ist da noch nicht lesbar. Ohne Stimme und ohne
einen Text, der sie ankuendigt, gibt es in Sekunde 0 nichts, worauf der
Zuschauer warten koennte.

Ablage: claude/ablage-automatik-pruefung, Head siehe Commit dieser Datei.

## Belege

- NOD-Laeufe heute: keiner bis 08:41 utc; letzter davor Lauf 352, Run-ID
  44151132014, 17.11. 18:44 utc, conclusion success. Kein roter Lauf,
  deshalb keine Fehlerzeile.
- Haengende Laeufe: status=queued gibt genau einen zurueck, den bekannten
  Lauf 166 vom 07.10. Nach Vorgabe nicht gemeldet und nicht angefasst.
  Kein anderer haengender Lauf.
- Kanal Kaspa Pulse: 121 Abos, 20.789 Aufrufe, 67 Videos (17.11.: 121 /
  20.712 / 66). Instagram kaspapulse: 163 Follower (17.11.: 161).
- Reel Dfw__UGpt7R, 15.11. 14:30 utc, Alter 66,4 h: 324 Aufrufe,
  Skip-Rate 82,5 Prozent, geschauter Anteil noch nicht da, 2,8 s
  durchschnittliche Wiedergabezeit, 9 Likes, 0 Kommentare, 0 Teilen,
  0 Speichern, Trial nein.
- Kanal Pulse Hawk: weiter kein Video im Fenster, kein Analytics-Zugang.
  Nach Vorgabe kein Meldepunkt.
