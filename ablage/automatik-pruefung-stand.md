# Automatik-Pruefung, Stand

Zeitpunkt: **Montag, 09.11.2026, 10:50 Berlin** (09:50 utc). Gemessen 08:42
bis 09:45 utc. Lauf gruen, ein Start ausgeloest, eine Meldung.

## Meldung an Ben (woertlich)

Unsicherheit zuerst: YouTube-Analytics reicht heute nur bis zum 06.11.
(Nachlauf zwei Tage), die Wochenwerte unten decken 5 von 7 Tagen und werden
deshalb je Tag verglichen.

1. NOD: heute lag bis 08:45 utc kein Lauf vor, deshalb genau einmal gestartet
   (workflow_dispatch auf main, Antwort 204 queued); letzter Lauf davor war
   Lauf 307, Run-ID 42499344589, vom 08.11. 16:20 utc, gruen.
2. X-Post: nein, fuer heute noch offen; letzter Eintrag nod-2026-11-08,
   Post-ID 2119349802983125215, 08:42:23 utc. Nichts von Hand gepostet.
3. Datenstaende ok: kas-candles.json 2026-11-09 07:05 utc (heute), letzte
   Tageskerze 08.11.; multibagger-pick.json date 2026-11-08 mit den
   Schlusskursen vom 06.11., also vom letzten Handelstag (Freitag),
   multibagger-state.json last_run 2026-11-08.
4. Wachstumslog: eingetragen Short RmTyDOI_Ni8 (06.11., 48-h-Marke am 08.11.
   erreicht). Offen keine. Weekly Folge 11 und der naechste Erklaerer waren
   noch nicht veroeffentlicht, ihre Zeilen werden am 10.11. und 13.11.
   faellig. Montags-Kanalzeile: 119 Abos, 35,9 Wiedergabestunden (10.10. bis
   06.11.), Abspann-Klickrate 0,00 % auf MyGZT1BIBsc.
   Diff: 108 Einfuegungen, 0 Loeschungen.
5. Reels: 0 eingetragen, kein Reel im Fenster 48 bis 72 Stunden (am 06. und
   07.11. ist keines erschienen). Keine Zwei-Satz-Notiz faellig, weil keine
   Skip-Rate zu pruefen war; die Ein-Reel-Grenze bleibt unverbraucht.
6. Haengender Lauf, weiter gemeldet: monero stressnet dauer, Lauf 1, Run-ID
   42374283536, seit 07.11. 12:51 utc auf queued, updated_at gleich
   created_at, also nie angelaufen. Nicht angefasst, Ben entscheidet.
7. Push: claude/wachstumslog-2026-11-09 in pulse-studio, Head 781274a,
   ein Commit.
8. Ablage: claude/ablage-automatik-pruefung, Head = dieser Commit.

## Uhrwerk-Bericht (Montag)

Der vollstaendige Bericht liegt als pulse-studio/docs/projekt/uhrwerk-2026-11-09.md
im selben Commit wie das Wachstumslog. Kurzfassung:

- YouTube: Abos netto Woche +5 (114 auf 119). Bester Short der Woche
  ImyB-3dS_ns (323 Aufrufe, 0,31 Abos je 100), schwaechster RmTyDOI_Ni8
  (113, erst 13 h im Analytics-Fenster). Testvorschlag Shorts: Einstieg
  Sekunde 0, Zahl gegen Frage.
- Instagram: Follower netto +44 (101 auf 145), Median-Reichweitenquote 1,90
  (Vorwoche 0,45), Reels Median Skip-Rate 66,3 %, Median geschauter Anteil
  35,9 %. Top explainer-moved 1.751, erstmals eine Tagesgrafik dicht dahinter
  (form08, 1.535). Flop form03 27, form02 40, form11 72.
- X: Follower netto 0 (271), Median-Reichweitenquote 0,17 (Vorwoche 0,03).
  Nur 5 Posts abgesetzt, am 05. und 06.11. gar keiner; 4 davon gemessen.
  Top nod-cut_countdown 131, Flop nod-whale_weight 11.
- Threads: Follower netto +2 (6 auf 8), alles andere offen, weiter kein
  Schnappschuss in der Rohtabelle.
- Kurzlink-Klicks und Newsletter-Anmeldungen je Kanal: offen mit Absicht.
  Kurzlinks zaehlen den Klick nicht, die Brevo-Zahlen gehen nie in dieses
  oeffentliche Repo.
- Testregeln: auf keinem Kanal laeuft ein getaggter Test, dritte Woche in
  Folge 0 von 7. variante beziehungsweise test steht ueberall auf "-" oder
  "keiner".
- Testvorschlaege zur Freigabe, je Kanal eine Stellschraube: Instagram
  Einstieg Sekunde 0 Zahl gegen Frage; X erste Zeile Zahl gegen Vergleich;
  Threads Frage zuerst statt Zahl zuerst; lange Videos zusaetzlich zu
  Test & Compare die Laenge auf 8 bis 9 Minuten; Shorts Einstieg Sekunde 0.
- Zwei Herausforderer-Formen (nur die Form): erstens der Irrtum in Sekunde 0,
  dann die Mechanik (@shadrixo1, TikTok, 1,4 Mio. Aufrufe, 21,3x ueber dem
  eigenen Median, 54 s, Motion Graphics ohne Gesicht); zweitens Frage als
  erster Satz mit einer Grafik, die sich genau einmal bewegt (@nikeser11,
  TikTok, 914.400 Aufrufe, 831,7x ueber dem eigenen Median).
- vidIQ-Befunde: Titel unter 85 sind C3zATJEVIIY (81) und RmTyDOI_Ni8 (84).
  Zuschauerfragen gibt es keine, auf beiden juengsten langen Videos steht nur
  der eigene angepinnte Kommentar; vierter Befund dieser Art seit 01.09.
  Lange Videos werden von der Suche getragen (48 bis 65 % Anteil Suche), der
  Abspann traegt bei beiden 0,00 %.
