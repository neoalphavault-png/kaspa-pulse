# BCH-Mainnet, gezählte gegen gerechnete Wartezeit (Auftrag Ben 22.11.2026)

**Kopf:** Profil `bch-mainnet` für den Header-Client gebaut und einmal getestet. Der Testlauf lief am 22.11. auf einem eigenen Branch, ohne Secret und ohne Commit nach main. Das Ergebnis: Die üblichen Wartezeiten für 1, 3 und 6 Bestätigungen weichen nicht von den gerechneten Werten ab, die langen sind gezählt etwas länger. PR im Methoden-Repo an Ben (pulsehawk/methods#9). Das Ergebnis kommt in den Wochenbericht 2 am So 29.11.

<!-- discord -->
BCH-Mainnet gezählt, seit dem Upgrade 12, 27.314 Abstände nach Kopfzeit. Üblich brauchen 6 Bestätigungen 56 min 41 s, gerechnet 56 min 42 s. Bei 9 von 10 sind es gezählt 1 h 35 min 31 s, gerechnet 1 h 32 min 45 s. Die langen Wartezeiten sind also etwas länger als gerechnet. PR im Methoden-Repo bei Ben, Ergebnis im Wochenbericht 2. Bericht berichte/2026-11-22-bch-mainnet-wartezeit.md
<!-- /discord -->

## Was gemacht wurde

- **Profil `bch-mainnet`** in `headers/ph_headers.py` (pulsehawk/methods, Branch `headers/bch-mainnet`).
  - Parameter aus BCHN `src/chainparams.cpp`, Klasse CMainParams. Fixpunkt ist der UAHF-Block 478.559.
  - BSV teilt Message Start und Port mit BCH. Darum zählt ein Peer nur, wenn sein erster Kopf auf unseren Startblock folgt (`probe_follows_start`). Der Selbsttest prüft beide Fälle.
- **`tools/bchn_chainparams.py`:** liest Checkpoints und Seed-Namen zur Laufzeit aus der öffentlichen BCHN-Datei. Im Repo steht kein Seed-Name.
- **`tools/conf_wait.py`:** zählt die Wartezeit für k Bestätigungen aus einer Köpfe-CSV und stellt den gerechneten Erlang-Wert daneben.
  - Gegenprobe mit unseren Chipnet-Köpfen: Median für 1 Block 52 s, wie im Wochenbericht 1.
- **Testlauf:** kaspa-pulse, Branch `messung/bch-mainnet-probe`, Workflow nur auf diesem Branch.
  - Köpfe 951.146 bis 978.460, Abruf 2026-11-22T10:01:42Z, Bot-Commit `b7be3b44`.
  - 4 Peers für die Zielhöhe, keine Probe abgelehnt. Kreuzproben 2 × 500 von 500 gleich, Checkpoints 960.710 und 970.892 geprüft, nur Bitcoin Cash Node.
  - Im Log stehen nur die Software der Peers und die Zahl der Seed-Argumente.

## Ergebnis

Daten: `data/bch-mainnet/koepfe.csv.gz` und `data/bch-mainnet/wartezeit.json` auf `messung/bch-mainnet-probe`, Commit `b7be3b44`. Fenster ab Block 951.147 bis 978.460, nach Kopfzeit. Wir haben 27.314 Abstände gezählt, das Mittel liegt bei 603,8 s, 193 Abstände sind negativ.

| Bestätigungen | üblich, gezählt / gerechnet | 9 von 10, gezählt / gerechnet | 99 von 100, gezählt / gerechnet |
|---|---|---|---|
| 1 | 6 min 48 s / 6 min 56 s | 23 min 31 s / 23 min 2 s | 48 min 27 s / 46 min 3 s |
| 3 | 26 min 38 s / 26 min 44 s | 54 min 45 s / 53 min 13 s | 1 h 28 min 5 s / 1 h 24 min 4 s |
| 6 | 56 min 41 s / 56 min 42 s | 1 h 35 min 31 s / 1 h 32 min 45 s | 2 h 17 min 29 s / 2 h 11 min 5 s |

- **Üblich:** keine Abweichung. Alle drei Mediane liegen im 95-%-Bereich eines Bootstraps über Wochenstücke von 1.008 Blöcken, für 6 Bestätigungen zum Beispiel 55 min 54 s bis 57 min 33 s.
- **Lange Wartezeiten:** gezählt länger als gerechnet. Bei 6 Bestätigungen liegt der Bootstrap-Bereich für 9 von 10 bei 1 h 34 min 14 s bis 1 h 37 min 5 s. Bei 99 von 100 liegt er bei 2 h 14 min 20 s bis 2 h 20 min 59 s. Beide Bereiche liegen über dem gerechneten Wert.
- **Grund:** Die Abstände streuen etwas mehr als exponentiell (Variationskoeffizient 1,05). Ein Teil davon kann von den Uhren der Miner kommen, weil wir nach Kopfzeit zählen.

## Weitere Punkte

- **X-Text-Regel (Ben 22.11.):** Jede Chipnet-Spanne in einem X-Text führt den Hinweis auf Difficulty 1 mit. `texte.py` prüft das, und die 9-von-10-Zahl fällt aus dem X-Text. Der Stand liegt auf `wochenbericht/1-vorbereitung`, Commit `eb902b27`.
- **c2, Neustart am 21.11. 14:35 UTC:** Im Fenster 14:35:12 bis 14:35:23 UTC lief kein Workflow, und keine Zahl im Wochenbericht 1 kommt von BCHN auf c2. Es gab nichts zu wiederholen.
- **Bedarf laut Ben:** Börsen und Zahlungsabwickler, die Bestätigungen verlangen. Beleg sind zwei Wallet-Gespräche und die BCH-Gruppe auf Telegram, die Zahlungsbereitschaft ist unbelegt.

## PR-Nummern

- pulsehawk/methods#9, Profil und Werkzeuge, Ben merged
- dieser Bericht

## Offene Fragen an Ben

1. Soll der Wochenbericht 2 die Mainnet-Tabelle ganz zeigen, oder nur die Zeile für 6 Bestätigungen?
2. Soll der Testlauf wöchentlich laufen? Das wäre eine Workflow-Datei auf main, also ein PR an dich. Bis zu deiner Antwort bleibt es bei diesem einen Lauf.

## Was Ben tun muss

- pulsehawk/methods#9 prüfen und mergen.
- Die zwei Fragen beantworten.
