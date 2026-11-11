# BCH Tempnet 2027, Wochenlauf 11.11.2026

## Was gemacht ist

- **Wochenlauf:** Stichtag 2026-11-11T10:00:00Z gesetzt (`6a0bacb`). Lauf [43000895100](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43000895100) war grün, Bot-Commit `f5dc16e`.
  - Abruf 10:07:23 UTC, Spitze 365.759.
  - Die Zielhöhe kam nur aus 4 Peers mit bestätigtem Abzweig 327.989. 2 Peers ohne Abzweig zählten nicht, verworfene Abzweige gab es keine.
  - Gegenprobe: 2 Peers, je 500 von 500 Hashes gleich.
  - Bereich ab 327.989 bis 365.753. Der Stand liegt in `data/bch/tempnet-2026-11-11.json` und `docs/bch-tempnet-2026-11-11.md`.
- **Gegenprobe gegen chaingraph:** wieder HTTP 403, wie am 21.10. und 28.10. Ich habe das nicht umgangen.
- **Zwischenstand-Dateien:** Es gab keine.
- **PH-Entwurf:** `ph-entwurf-bch.yml` lief grün ([43001021431](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/43001021431)). Die Aufforderung an #moderator-only kam mit HTTP 204 an.
- **Adressen:**
  - In `data/bch` und `docs` stehen keine IPs und keine Hostnamen unserer Server oder der Peers.
  - Es kommen nur die öffentlichen Quellen-Endpunkte chaingraph und, in der Fenster-Datei vom 10.11., der Gist von bitcoincashautist vor.
  - Im Job-Log steht eine Peer-Software, die einen fremden Namen im User-Agent trägt (`/Bitcoin Cash Node:29.2.0(…)/` mit einem Domainnamen). Das hat der Peer selbst so gesetzt, es ist keine Adresse von uns. Im Repo steht der Name nicht.

## Vergleich zur Vorwoche

Alle Werte sind counted, die Spalte für 60 s ist computed. Die Werte gelten jeweils vom ersten Tempnet-Block bis zum Stichtag.

| | 4.11. | 11.11. | computed für 60 s |
|---|---:|---:|---:|
| Blöcke | 327.989 bis 356.040 (28.052) | 327.989 bis 365.753 (37.765) | |
| Abstände | 28.051 | 37.764 | |
| Mittel | 61,22 s | 61,49 s | 60 s |
| Median | 40,0 s | 41,0 s | 41,6 s |
| p90 | 129,0 s | 130,0 s | 138,2 s |
| p99 | 244,0 s | 242,0 s | 276,3 s |
| über 5 min | 161 (0,57 %) | 218 (0,58 %) | 0,67 % |
| längste Lücke | 20.863 s (Höhe 328.223) | unverändert | etwa 667 s |
| Abstand 0 / negativ | 181 / 0 | 428 / 0 | |
| Mindestschwierigkeit | 6.614 | 8.645 | |
| Sprünge der Hashrate (Faktor 2) | 15 | 27 | |
| 10 Blöcke, Median / p99 | 571,0 / 2.313,6 s | 579,0 / 2.311,4 s | 580,1 / 1.127,0 s |

**Was sich in der Woche geändert hat:**
- 9.713 neue Blöcke.
- Die Zahl der Sprünge stieg von 15 auf 27. Dazu passt das Hash-Fenster vom 9.11. von 17:35 bis 19:38 UTC (`data/bch/tempnet-fenster-2026-11-10.json`).
- Abstände von 0 s stiegen von 181 auf 428.

## PR-Nummern

- PR #305 (Abschlussbericht für das Forum, offen bis zum Update am Fr 13.11.)
- PR #304 (`tempnet_fenster.py`, gemergt)

## Offene Fragen an Ben

1. Die Gegenprobe gegen chaingraph gibt seit drei Wochen 403. Soll sie bis zum Tempnet-Ende so bleiben? Ich schlage ja vor, und im Abschlussbericht steht sie als nicht verfügbar.

## Was Ben tun muss

- Den PH-Entwurf in #moderator-only ansehen.
