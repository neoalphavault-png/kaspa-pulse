# Methoden-Repo Schritt 5, Plan (12.11.2026, Frist Mo 30.11.)

Auftrag Ben 4.11.: Header-Client und BCH-Tempnet-Skripte nach dem Muster von `upgrade_report/` in pulsehawk/methods. Dazu gehört:
- englisch, ohne interne Namen und ohne Adressen
- nur Standardbibliothek
- Selbsttest mit kleinem Beispiel und erwarteter sha256
- Formate in FORMATS.md, Kennungen in METHODS.md

Ben merged jeden PR in pulsehawk/methods.

<!-- discord -->
Methoden-Repo Schritt 5 geplant: drei PRs in pulsehawk/methods bis 30.11., Header-Client, BCH-Tempnet-Auswertung, Zuhörer. Erster PR bis Mi 18.11. Zwei Fragen im Bericht. Bericht berichte/2026-11-12-methods-schritt5.md
<!-- /discord -->

## Bestand

| Skript | Ort heute | Zeilen | Inhalt |
|---|---|---:|---|
| `zcash_koepfe.py` | main | 512 | Header-Client Zcash, P2P, Equihash-Köpfe, Verkettung, Arbeit, Checkpoints, Gegenprobe |
| `tempnet_koepfe.py` | main | 514 | Header-Client BCH Tempnet, Abzweig 327.989 als Fixpunkt |
| `chipnet_koepfe.py` | `messung/bch-chipnet-xo` | 535 | Header-Client BCH Chipnet |
| `tempnet_auswertung.py` | main | 368 | Wochenstand, Abstände, MTP, 10 gegen 1 Block, Nachführung |
| `build_wechsel.py` | `messung/bch-tempnet` | 234 | Wechsel der Knoten-Builds |
| `forum_woche3.py` | `messung/bch-tempnet` | 418 | Zahlen für den Forumsbeitrag Woche 3 |
| `tempnet_lauscher.py` | main | 351 | Zuhörer BCH |
| `lauscher_auswertung.py` (BCH) | main | 213 | Auswertung Zuhörer BCH |
| `zcash_lauscher.py`, `lauscher_auswertung.py` (Zcash) | main | 229, 241 | Zuhörer Zcash |
| `tempnet_fenster.py`, `tempnet_stuecke.py` | main | neu | Hash-Fenster, Stücke von 120 Blöcken |

Alle nutzen nur die Standardbibliothek. Kommentare und Ausgaben sind deutsch und nennen interne Branches. Das muss beim Übertragen raus.

## Plan

| PR | Inhalt in pulsehawk/methods | Selbsttest | bis |
|---|---|---|---|
| 1 | `headers/`: ein Header-Client mit zwei Netzen, Zcash und BCH. Er übernimmt das Gemeinsame der drei Skripte, die Netze unterscheiden sich in Konfiguration und Kopfformat. Kennung PH-M-001 bekommt die Implementierung, die heute auf der Seite als „implementation follows“ steht. | 20 echte Köpfe je Netz als Datei. Der Selbsttest prüft Verkettung und Arbeit offline und vergleicht die sha256 der CSV. Netzverbindungen kommen im Selbsttest nicht vor. | Mi 18.11. |
| 2 | `bch_tempnet/`: Wochenstand (aus `tempnet_auswertung.py`), Hash-Fenster und Stücke, Build-Wechsel. `forum_woche3.py` geht nicht als eigenes Skript hinein, es war eine einmalige Zusammenstellung. Seine Rechnungen stecken in den anderen. | kleines Beispiel aus unseren Tempnet-Köpfen mit erwarteter sha256 | Mo 23.11. |
| 3 | `listener/`: Zuhörer für Zcash und BCH als ein Programm mit zwei Netzen, dazu die Auswertung (stale, first seen, Ausbreitung zwischen zwei Messpunkten). Kennungen PH-M-002 und PH-M-004. | aufgezeichnete Ankündigungen als Beispiel | Fr 27.11. |

Puffer bis Mo 30.11. für deine Prüfung. Jeder PR bekommt im PR-Branch von kaspa-pulse einen kurzen Bericht.

## Offene Fragen an Ben

1. Soll der Header-Client im Methoden-Repo ein Programm mit zwei Netzen sein, oder je Netz ein Skript wie heute? Mein Vorschlag ist ein Programm, denn so ist das Verfahren nur einmal beschrieben.
2. `forum_woche3.py` und `chipnet_koepfe.py` hängen an einzelnen Anlässen (Forumsbeitrag Woche 3, Chipnet-Messung). Reicht es, ihre Rechnungen in die allgemeinen Skripte zu übernehmen, statt sie einzeln zu veröffentlichen? Mein Vorschlag ist ja.

## Was Ben tun muss

- Die zwei Fragen beantworten, am besten bis Mo 16.11., damit PR 1 danach gebaut werden kann.
