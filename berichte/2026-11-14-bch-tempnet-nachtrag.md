# BCH Tempnet, Nachtrag zum Abschlussbericht, Stand 14.11.2026

Zusage im Forum #38/#40: die letzten Zahlen vor dem Ende des Tempnet am So 15.11. 12:00 UTC. Grundlage, Regel und Tabellen wie im Abschlussbericht vom 13.11. (`berichte/2026-11-13-bch-tempnet-abschluss.md`, PR #305).

<!-- discord -->
BCH Tempnet, Nachtrag zum Abschluss (Stand 14.11. 14:02 UTC), Ben postet. Es gibt kein neues Hash-Fenster, die sechs Fenster bleiben bei 21,0 % stale. Außerhalb sind es 0,72 % (168 von 23.028), am 13.11. waren es 0,70 % (148 von 21.151). Die Gegenprobe mit der CSV von bitcoincashautist ist unverändert, 0 Abweichungen. Es fehlen noch die letzten Stunden bis 15.11. 12:00 UTC. Bericht berichte/2026-11-14-bch-tempnet-nachtrag.md
<!-- /discord -->

## Grundlage

- **Köpfe:** frisch über `data/bch/anstoss.txt` (Commit `654f339`), Lauf „koepfe und zaehlung [bot]“ (`81ac552`). Abruf 14.11. 14:02:54 UTC, Höhe 327.989 bis 370.349, 42.361 Köpfe.
- **Zuhörer GitHub:** `data/bch/lauscher/bloecke.csv` und `zusammenfassung.json`, 89 Läufe vom 25.10. 09:15 bis 14.11. 12:01 UTC, abgedeckt 473,4 h. 28.014 von 28.096 Kettenblöcken angekündigt, 1.495 stale nach 6 Bestätigungen. Gegen die frischen Köpfe neu gerechnet, ist das Ergebnis gleich.
- **Lücke im Zuhörer:** 3.11. 13:59 bis 4.11. 10:08 UTC bleibt. Fenster 4 liegt ganz darin.
- **Vergleich, source bitcoincashautist:** `tempnet_d.csv` aus dem Gist in #41, neu aus der HTML-Seite gelesen, nur als Daten. sha256 `e7ce24e0…94e`, gleich wie am 10.11. und 13.11.
- **Zahlen:** `data/bch/tempnet-fenster-2026-11-14.json` auf `messung/bch-tempnet` (Commit `1b9359c2`). Skript `scripts/bch/tempnet_fenster.py` von main, Selbsttest bestanden.
- **Was fehlt:** Blöcke nach dem letzten Zuhörerlauf (Ende 14.11. 12:01 UTC) bis zum Ende des Tempnet am 15.11. 12:00 UTC.

## Ergebnis (Stand 14.11.)

Seit dem 9.11. kam kein neues Hash-Fenster dazu. Die sechs Fenster sind dieselben wie am 13.11., mit denselben Grenzen, Blöcken und Stale-Zahlen.

| | Kettenblöcke angekündigt | stale | Anteil |
|---|---:|---:|---:|
| in den Hash-Fenstern | 4.986 | 1.327 | 21,0 % |
| außerhalb, Stand 14.11. | 23.028 | 168 | 0,72 % |
| außerhalb, Stand 13.11. | 21.151 | 148 | 0,70 % |

**rufitnes' fünf Fenster aus #37:** zusammen unverändert 761 stale auf 2.609 Kettenblöcken, 22,6 %. Übrige Zeit 734 auf 25.405, 2,8 % (am 13.11. 714 auf 23.528, 2,9 %).

**Gegenprobe, source bitcoincashautist:** 35.101 gemeinsame Höhen, 0 Abweichungen, 89 Höhen nur dort (vor dem Abzweig). Seine Datei endet weiter bei 363.089.

## Forumsentwurf (Ben postet)

Textregeln eingehalten: kein Doppelpunkt im Fließtext außer in Uhrzeiten, kein Gedankenstrich, kein Pfeil, kein Satz beginnt mit einer Ziffer. Keine Position zum Upgrade.

---

@bitcoincashautist @Rufitnes An update to our split of stale blocks by hash window, with headers up to block 370,349 fetched 14 Nov 14:02 utc and our listener up to 14 Nov 12:01 utc. No new hash window appeared after 9 Nov, so the six windows and their 1,327 stale blocks on 4,986 chain blocks, 21.0 %, stay as posted. Outside the windows the count grew to 168 stale on 23,028 chain blocks, 0.72 %. As of 13 Nov it was 148 on 21,151, 0.70 %.

For rufitnes' five windows the numbers stay at 761 stale on 2,609 chain blocks, 22.6 %. All other hours give 734 on 25,405, 2.8 %, against 714 on 23,528 as of 13 Nov.

The difficulty check against bitcoincashautist's csv (source bitcoincashautist, the gist in #41) is unchanged with no difference in 35,101 shared heights, and the file has the same sha256 as on 10 Nov. Our listener gap from 3 Nov 13:59 utc to 4 Nov 10:08 utc stays, and window 4 lies fully inside it.

The last hours up to the end of the tempnet on 15 Nov 12:00 utc are not in these numbers. The file is data/bch/tempnet-fenster-2026-11-14.json on messung/bch-tempnet in github.com/neoalphavault-png/kaspa-pulse.

---

## PR-Nummern

- PR #305, Abschlussbericht vom 13.11. (gemergt)
- PR #304, `tempnet_fenster.py`
- dieser Bericht, PR siehe unten im Stücke-Nachtrag

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

- Den Entwurf vor dem Ende des Tempnet am So 15.11. posten.
