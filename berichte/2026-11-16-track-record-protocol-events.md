# Drei Punkte vom 16.11.2026: Track Record breiter, Upgrade-Kalender, History im Methoden-Repo

Auftrag Ben 16.11.2026, je Punkt ein eigener PR. Workflow-Änderungen gehen als PR an Ben.

<!-- discord -->
Drei Punkte vom 16.11.: Der Upgrade-Kalender hat Zcash NU8 als proposed, der BCH-Chipnet-Eintrag bleibt ohne offizielle Quelle unverändert, live geprüft. History liegt als pulsehawk/methods#8 bei Ben. Die Prognose des Kaspa-Reward-Schritts liegt als kaspa-pulse#325 und pulsehawk-site#99 bei Ben, beide mit Workflow. Probe 2 lief grün, die Vorschau ist 5.12. 00:10 UTC mit 80-%-Band von 00:00 bis 00:20 UTC, es ist noch keine veröffentlichte Prognose. Bericht berichte/2026-11-16-track-record-protocol-events.md
<!-- /discord -->

## 1. Track Record, „scheduled protocol events“ (Test ohne Fixkosten)

- **Ereignis:** Der nächste Kaspa-Reward-Schritt ist Monat 55 beim DAA score 610.101.000. Der Reward geht dann von 1,94454365 auf 1,83540480 KAS je Block.
  - Nachgerechnet aus rusty-kaspa v2.1.0 (`params.rs`, `coinbase.rs`).
  - Gegenprobe: Monat 50 ergibt 2,44997148 KAS, das ist der bekannte Schritt vom 5.7.2026.
- **Prognose:** `scripts/kaspa_reward_prognose.py` folgt Activation Forecast v1 wie PH-M-006.
  - Eingang sind etwa 400 Punkte der ausgewählten Kette des eigenen Knotens im Runner, vom Pruning-Punkt bis zur Spitze.
  - Daraus kommen 20.000 Ziehungen, mit 80- und 95-%-Band.
  - Stufen 14 Tage, 7 Tage, 2 Tage und 24 Stunden vor dem Prognosemedian.
  - Wertung im 80-%-Band, im 95-%-Band oder außerhalb. Gezählt wird die Kopfzeit des ersten Kettenblocks mit DAA score mindestens beim Ziel.
  - Der Selbsttest besteht 31 von 31 Prüfungen.
- **Workflow `kaspa-reward-prognose.yml`:** alle 12 h, kein Secret. Der Knoten startet nur, wenn eine Stufe fällig ist oder gewertet werden muss. Die Prognosen gehen als Commit auf `messung/kaspa-reward`, nie auf main.
- **Probe 1** (vom PR-Branch, ohne Commit, grün): Die Kette kam nur in einer Seite, das Fenster waren 28 min. Behoben mit Seiten bis zur Spitze und schnelleren Ziehungen.
- **Probe 2** (grün):
  - Fenster 15.11. 07:45 bis 16.11. 19:10 UTC, 402 Intervalle, 10,0067 DAA je s
  - Vorschau 5.12.2026 00:10 UTC, 80-%-Band 00:00 bis 00:20 UTC, 95-%-Band 4.12. 23:55 bis 5.12. 00:25 UTC
  - Die Vorschau ist keine veröffentlichte Stufe.
  - Im Log stehen keine Adressen.
- **Seite:** pulsehawk-site#99 bringt die Rubrik auf /track-record.
  - Sie hat eine eigene Zählung, die Upgrade-Bilanz (6 Einträge, 5 im Band) bleibt unverändert.
  - Kein festes Datum steht darin, nur forecast mit Band.
  - Ein stündlicher Sync übernimmt neue Prognosen nach pulsehawk-site, der Commit dort ist der Zeitstempel. Eine veröffentlichte Prognose ändert er nie.
- **Risiko:** Die Ziehungen nehmen kurze Intervalle als unabhängig an. Das Band ist deshalb schmal, rund 20 min über 18 Tage. Driftet die DAA-Rate über Tage, kann der Schritt außerhalb landen. Genau das prüft der Test.

## 2. Upgrade-Kalender (pulsehawk-site#98, selbst gemergt)

- **Merge:** PR pulsehawk-site#98, Merge-Commit `e8df3c9`. Abgenommen auf pulsehawk.io/upgrades: NU8 steht als proposed, die Tabelle ist geteilt in kommend und aktiviert, „Last updated on 16 November 2026“.
- **Zcash NU8:** Quelle Forum-Thread 59124, ohne Höhe und Datum. Der Thread ist ein Vorschlag eines Forumsteilnehmers für NU8, keine Spezifikation.
- **BCH Chipnet:** unverändert, denn die offizielle Quelle fehlt.
  - BCHN hat seit v29.2.0 (1.10.) kein Release, der letzte Commit auf master ist vom 12.11.
  - `chainparams.cpp` nennt das Upgrade weiter tentative, ohne Aktivierungshöhe.
  - Die Seite der Upgrade-Spezifikation ist aus der Sitzung gesperrt, nicht umgangen.
- **Generator:** Die Tabelle ist geteilt, weil der Abschnitt sonst 262 Wörter gehabt hätte. Statt „checked on“ steht „last updated“, weil jede Zeile ihr eigenes Prüfdatum hat.

## 3. History im Methoden-Repo (pulsehawk/methods#8)

Eine Zeile, ohne nachgebaute Historie. Zwei Abweichungen vom Wortlaut, damit es stimmt:
- „published here together by 9 Nov 2026“, weil die Commits vom 4. bis 9.11. reichen.
- Daten „collected from 15 Oct to 9 Nov“, weil die Testnet-Blockzeiten bis 4.10. zurückreichen.

Der lange Entwurf #6 ist überholt.

## PR-Nummern

- kaspa-pulse#325, Prognose und Workflow, Ben merged
- pulsehawk-site#99, Rubrik und Sync-Workflow, Ben merged
- pulsehawk-site#98, Upgrade-Kalender, gemergt `e8df3c9`, live geprüft
- pulsehawk/methods#8, History, an Ben
- dieser Bericht

## Offene Fragen an Ben

1. **Wertung:** Passt „im 80-%-Band, im 95-%-Band, außerhalb“? Bei den Upgrades hieß es in band oder outside gegen ein 90-%-Band.
2. **Chipnet-Status:** Warten auf eine BCHN-Quelle mit Aktivierungshöhe, oder den Eintrag mit unserer eigenen Zählung führen?
3. **Entwurf #6:** Soll ich pulsehawk/methods#6 schließen?
4. **Probeläufe:** Am 16.11. liefen zwei Workflows von eigenen Branches ohne Merge und ohne Secret, die Rohköpfe für methods#7 und die Probe von #325. Sind solche Probeläufe recht?

## Was Ben tun muss

- kaspa-pulse#325 und pulsehawk-site#99 bis etwa Do 19.11. mergen, damit die 14-Tage-Prognose rechtzeitig um den 21.11. kommt.
- In pulsehawk-site die Repo-Variable `TE_QUELLE` setzen (Settings, Secrets and variables, Actions, Variables). Der Wert ist die Raw-Adresse der Datei `data/kaspa-reward/zustand.json` auf dem Branch `messung/kaspa-reward` in kaspa-pulse, auf GitHub über den Knopf „Raw“ der Datei. Die Datei entsteht mit dem ersten Lauf nach dem Merge von #325.
- pulsehawk/methods#8 prüfen.
