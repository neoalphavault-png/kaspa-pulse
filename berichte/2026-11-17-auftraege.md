# Aufträge vom 17.11.2026: Cron-Kommentar, methods#7, Peer-Kennung, BCH-Zweigregel

Auftrag Ben 17.11.2026, vier Punkte in dieser Reihenfolge, dazu Bens Antworten auf die Fragen aus #326 und #98.

<!-- discord -->
Aufträge 17.11.: #325 hat den Kommentar zur Berliner Zeit, neuer Kopf b8482e4. methods#7 hat peer_height_checked statt peer_tip, und die README nennt die Seite nicht mehr, methods#6 ist geschlossen. Die Peer-Kennung ist gekürzt in BCH und Zcash, PR 327 gemergt, dieselbe Stelle stand in den Läufen 6, 7 und 8. Die zweite BCH-CSV folgt jetzt der Zweigregel von bitcoincashautist, Daten bis 15.11. 12:00 UTC. Höhen, block_count und Difficulty stimmen in allen 363 Stücken mit seinen Dateien, Stale weicht in 52 Stücken ab. Forumsentwurf im Bericht. Bericht berichte/2026-11-17-auftraege.md
<!-- /discord -->

## 1. Kommentar zur Cron-Zeit in #325

- Über `cron: "41 3,15 * * *"` steht jetzt der Kommentar mit der Berliner Zeit, sonst ist nichts geändert.
- Neuer Kopf von kaspa-pulse#325 ist **`b8482e4`**. Ben merged, weil es eine Workflow-Datei ist.
- Der Push startet wie vorgesehen eine Probe ohne Commit.

## 2. pulsehawk/methods#7 vor dem Merge

- **Feldname:** `peer_tip` in `cross_checks` heißt jetzt `peer_height_checked`. `FORMATS.md` beschreibt es als die höchste Höhe in den Köpfen, die dieser Peer für die Gegenprobe geschickt hat, nicht als die Spitze seiner Kette.
- **README:** `data/zcash-nu7/README.md` Zeile 7 schreibt „published on our site“ statt des Seitennamens. Der Datenfilter aus `CONTRIBUTING.md` ist damit über `examples`, `data` und `headers` leer, ohne Ausnahme.
- **Prüfungen:** Neuer Kopf von #7 ist `5f3dfae`. Alle drei Selbsttests sind bestanden, der Secret-Scan ist sauber.
- **#6:** geschlossen, mit Hinweis auf #8.
- **`methods/koepfe-roh`:** Den Branch in kaspa-pulse lösche ich nach deinem Merge von #7.

## 3. Peer-Kennung (PR #327, selbst gemergt)

- **Merge:** PR #327, Merge-Commit `5b46156`. Es ist keine Workflow-, Deploy- oder c2-Datei geändert, die Checks sind grün.
- **Kürzung:** `scripts/peer_kennung.py` behält von der Software-Kennung den Teil vor der ersten Klammer und ersetzt Hostname, IPv4 und IPv6 durch „[entfernt]“.
- **Wo:**
  - Eingesetzt beim Lesen der version-Nachricht in `tempnet_koepfe.py`, im Zuhörer `tempnet_lauscher.py` (vor der Umstellung auf Chipnet) und in `zcash_koepfe.py`, damit auch im Zcash-Zuhörer der Serie „dauer“.
  - Das gilt für Log und alle Dateien. Der Selbsttest prüft 11 Fälle, alle richtig.
- **Was jetzt live ist:** Der nächste Lauf des Zcash-Zuhörers und jeder BCH-Lauf von main nutzen die gekürzte Kennung. Auch c2 nutzt sie nach seinem nächsten Abgleich mit dem Repo.
- **Job-Logs von „bch tempnet“, Schritt „koepfe holen“:**
  - Lauf 6 (10.11.), 7 (11.11.) und 8 (13.11.) enthalten dieselbe Stelle wie Lauf 10.
  - Lauf 9 (14.11.) ist sauber.
  - Der Wert steht nicht hier, die Zeilen stehen im Bericht `berichte/2026-11-17-peer-kennung.md`.
- **Gespeicherte Dateien:** Keine enthält eine solche Kennung.

## 4. BCH 2173, Zweigregel von bitcoincashautist (Beitrag 52)

**Regel der zweiten CSV:**
- Blöcke mit nBits 1d00ffff zählen nicht, für `block_count`, Mittel und Blockzeiten, wie bisher.
- Stale neu: Stale-Blöcke, die über prev aneinander hängen, bilden einen Zweig. Der ganze Zweig fällt weg, wenn am Abzweig der Kettenblock oder sein Geschwister Difficulty 1 hat. Die Köpfe der Stale-Blöcke stammen aus den Aufzeichnungen der Läufe.
- Ergebnis:
  - 1.314 Zweige, davon fallen 77 mit 103 Stale-Blöcken weg.
  - Jeder Zweig hat am Abzweig einen Kopf.
  - Bei der weiteren Lesart (Difficulty 1 irgendwo im Zweig) wäre ein einziger Zweig anders.

**Daten bis 15.11. 12:00 UTC:**
- Köpfe gekürzt auf 327.989 bis 371.646, den letzten Block vor 12:00 UTC.
- Zuhörer mit 94 Läufen, der letzte bis 15.11. 14:52 UTC, neu ausgewertet gegen dieselben Köpfe.
- Die Lücke vom 3.11. 13:59 bis 4.11. 10:08 UTC bleibt.

**Hash-Fenster:**
- Es bleiben sechs Fenster, mit 1.327 Stale-Blöcken auf 4.986 Kettenblöcken, 21,0 %.
- Außerhalb sind es mit Stand 15.11. 12:00 UTC 170 auf 24.448, 0,69 %. Mit Stand 14.11. waren es 168 auf 23.028.

**Stücke:**
- 363 Stücke, davon 243 voll abgedeckt.
- Erste CSV: 1.494 Stale in 1.237 Ereignissen.
- Zweite CSV nach der Zweigregel: 1.392 in 1.135 Ereignissen.

**Abgleich mit seinen Dateien** (source bitcoincashautist, Beitrag 50: `chunks.csv` und `chunks_nomin.csv`, aus der HTML-Seite der Gists gelesen, sein Skript nicht ausgeführt):

| Spalte | gleich in | abweichend in |
|---|---:|---:|
| Höhen, `block_count`, mittlere Difficulty | 363 von 363 Stücken | 0 |
| mittlere Blockzeit | 31 | 332 |
| mediane Blockzeit | 56 | 307 |
| Stale-Blöcke oder Stale-Ereignisse (nur voll abgedeckte Stücke) | 191 von 243 | 52 |

- **Stale:** In den vollen Stücken zählt er ohne Difficulty 1 1.593 Stale-Blöcke in 1.088 Ereignissen, wir 1.392 in 1.135. Er zählt in 45 Stücken mehr Stale-Blöcke, in 4 weniger.
- **Blockzeit:** Die Abweichungen gibt es schon in der Datei mit allen Blöcken. Er rechnet die Blockzeit offenbar anders als wir (Kopfzeit minus Kopfzeit des Vorgängers). Das deute ich nicht weiter.
- **Grenze des Abgleichs:** Seine Dateien gehen nur je Stück, nicht je Höhe. Feiner als je Stück lässt sich deshalb nicht abgleichen.
- **Dateien** auf `messung/bch-tempnet`, Commits `6c9c754` und `39720e6`:
  - `data/bch/tempnet-stuecke-120-2026-11-15.csv`, `-ohne-diff1-2026-11-15.csv` und `.json`
  - `data/bch/tempnet-fenster-2026-11-15.json`
  - `data/bch/tempnet-stuecke-abgleich-bitcoincashautist-2026-11-15.csv`, eine Zeile je Stück mit beiden Werten je Spalte und einer Spalte `abweichend`
- **Skript:** `scripts/bch/tempnet_stuecke.py` mit `zweig_filter()`, Selbsttest 17 von 17, in diesem PR.

**Forumsentwurf (Ben postet), ein Punkt, 119 Wörter, kein Link:**

> @bitcoincashautist we switched our second csv to your rule, so a forked branch goes out whole when the main block or its sibling has difficulty 1, and joined both of our files against yours. In the 243 chunks our listener fully covered between 25 Oct 09:15 utc and 15 Nov 12:00 utc, leaving out our gap from 3 Nov 13:59 to 4 Nov 10:08 utc, heights, block_count and mean difficulty match yours in every chunk. Stale numbers differ in 52 of them. Without difficulty 1 you count 1,593 stale blocks in 1,088 events, we count 1,392 in 1,135. Your node and our listener see different peers, so we list each chunk and do not read a cause into it.

## Antworten von Ben (17.11.), umgesetzt

- Die Wertung im 80- und 95-%-Band bleibt so.
- Der Chipnet-Eintrag wartet auf eine BCHN-Quelle mit Aktivierungshöhe. Unsere eigene Zählung kommt nicht in den Kalender.
- Probeläufe auf eigenen Branches ohne Secret und ohne Commit nach main sind in Ordnung.

## PR-Nummern

- kaspa-pulse#325, neuer Kopf `b8482e4`, Ben merged
- pulsehawk/methods#7, neuer Kopf `5f3dfae`, Ben merged; #6 geschlossen
- kaspa-pulse#327, gemergt `5b46156`
- dieser PR, Zweigregel und Bericht

## Offene Fragen an Ben

1. **Blockzeit:** Soll der Beitrag bitcoincashautist nach seiner Rechnung der Blockzeit fragen? Sie weicht in fast allen Stücken ab, auch ohne jeden Filter. Im Entwurf steht das nicht, damit es bei einem Punkt bleibt.
2. **Alte Logs:** Sollen die Logs der Läufe 6, 7 und 8 gelöscht werden? Das geht nur über die Actions-Seite.

## Was Ben tun muss

- #325 und methods#7 mergen.
- Den Forumsentwurf posten.
- Die zwei Fragen beantworten.
