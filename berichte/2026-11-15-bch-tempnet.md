# BCH Tempnet, Abschlusslauf zum Ende am 15.11.2026 12:00 UTC

Ben am 21.10.: Abschlusslauf am So 15.11. 12:00 UTC, wenn das Tempnet endet. Die Zahlen kommen aus eigenen Köpfen über P2P, gezählt ab dem ersten Tempnet-Block 327.989.

<!-- discord -->
BCH Tempnet, Endstand 15.11. 12:00 UTC. Gezählt sind 43.658 Blöcke (327.989 bis 371.646), das Mittel liegt bei 61,27 s, der Median bei 42,0 s. Die Gegenprobe ist mit zwei Peers je 500 von 500 gleich. Bei chaingraph gab es wieder 403, das haben wir nicht umgangen. Der Entwurf ging an Discord (http 200). Ein Peer trägt im Job-Log einen Hostnamen in seiner Software-Kennung, in data/bch und docs steht er nicht, siehe offene Fragen. Bericht berichte/2026-11-15-bch-tempnet.md
<!-- /discord -->

## Was gemacht wurde

- **Frischer Stand und Stichtag:** `data/bch/stichtag.txt` steht auf `2026-11-15T12:00:00Z` (Commit `ad821122`). Das hat `bch-tempnet.yml` gestartet, Lauf 10.
- **Lauf grün:** Alle Schritte sind grün, Koepfe holen, Gegenprobe chaingraph, Auswerten, Secret-Scan und Commit. Der Bot-Commit ist `2126609e` mit `data/bch/tempnet-2026-11-15.json` und `docs/bch-tempnet-2026-11-15.md`.
- **Peers:**
  - 4 Peers haben den Abzweig bei 327.989 bestätigt, 4 Proben ohne Abzweig zählten nicht. Das Tempnet hatte also bis zum Abruf noch Peers.
  - Die Zielhöhe 371.652 hat 4 Peers mit Abzweig.
  - Abruf 15.11. 12:06:50 UTC, Spitze 371.652.
  - Wir haben nichts erfunden, und ein Fallback auf den Wochenstand war nicht nötig.
- **Gegenprobe Peers:** Zwei Peers, je 500 von 500 gleich, beide mit Spitze 371.652. Es wurde kein Abzweig verworfen und kein Peer-Fehler gezählt.
- **Gegenprobe chaingraph:** HTTP 403 Forbidden, 0 Proben verglichen. Wie in den Wochen davor ist das nicht umgangen und in JSON und Markdown so vermerkt.
- **Bereich:** Er beginnt bei 327.989 (Fixpunkt erster Tempnet-Block, letzter gemeinsamer 327.988) und endet beim letzten Block vor dem Stichtag, 371.646 um 11:59:48 UTC.
- **IPs und Hostnamen:**
  - Keine IP steht in `data/bch`, in `docs/bch-tempnet-2026-11-15.md` oder im Job-Log.
  - In `data/bch` steht nur der öffentliche Endpunkt der chaingraph-Gegenprobe, wie seit dem 21.10. Er ist kein Server von uns und kein Peer.
  - **Fund im Job-Log:** Die Peer-Software in `data/bch/tempnet-koepfe-meta.json` hat nur zwei Kennungen ohne Hostnamen. Im Job-Log des Schritts „koepfe holen“ (Lauf 10, Zeile um 12:06:51.667 UTC) steht aber ein Peer, der in seiner eigenen Software-Kennung einen Hostnamen trägt. Den Namen nenne ich hier nicht. Der Peer lag zurück und zählte nicht.
- **Zwischenstand-Dateien:** Keine vorhanden, `abcc4826` hatte sie schon entfernt. Dieser Lauf hat keine neue geschrieben, weil der Abruf nach dem Stichtag lag.
- **ph-entwurf-bch.yml:** Lauf 9 ist grün. Er nahm `data/bch/tempnet-2026-11-15.json`, der Selbsttest der Regeln war ok und der Entwurf ging an Discord (http 200), die Aufforderung an #moderator-only (http 204). Der Entwurf vergleicht den Median 42,0 s über 43.657 Abstände mit 41,0 s im Fenster bis 11.11. 09:58 UTC.

## Endstand und Verlauf über alle Wochenstände

Alle Stände sind gezählt ab 327.989. Abstand ist die Kopfzeit minus die Kopfzeit des Vorgängers. Die Erwartung für eine ideale 60-s-Kette liegt beim Median 41,6 s, p90 138,2 s, über 5 min 0,67 %.

| Stand (UTC) | bis Höhe | Blöcke | Mittel | Median | p90 | p99 | über 5 min | längste Lücke | MTP-Verzug Median | Difficulty 1 | Gegenprobe Peers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 21.10. 10:00 | 335.560 | 7.572 | 67,07 s | 43,0 s | 125 s | 232 s | 0,38 % (29) | 20.863 s | 335 s | 3.455 | 2 × 500/500 |
| 28.10. 10:00 | 345.613 | 17.625 | 63,13 s | 44,0 s | 128 s | 216 s | 0,18 % (31) | 20.863 s | 348 s | 4.819 | 2 × 500/500 |
| 4.11. 10:00 | 356.040 | 28.052 | 61,22 s | 40,0 s | 129 s | 244 s | 0,57 % (161) | 20.863 s | 337 s | 6.614 | 2 × 500/500 |
| 11.11. 10:00 | 365.753 | 37.765 | 61,49 s | 41,0 s | 130 s | 242 s | 0,58 % (218) | 20.863 s | 342 s | 8.645 | 2 × 500/500 |
| **15.11. 12:00** | **371.646** | **43.658** | **61,27 s** | **42,0 s** | **130 s** | **234 s** | **0,50 % (220)** | 20.863 s | 344 s | 9.461 | 2 × 500/500 |

- Die längste Lücke liegt in allen Ständen bei Höhe 328.223 am 16.10.
- chaingraph gab in allen Ständen 403 und lieferte keinen Vergleich.
- Die Stale-Zahlen des Zuhörers und die Hash-Fenster stehen in den Berichten vom 13.11. und 14.11. (#305, #321). Die Blöcke nach dem letzten Zuhörerlauf bis 12:00 UTC sind dort noch nicht gezählt.

## PR-Nummern

- Keine neue PR für den Lauf. Er lief über Push auf `messung/bch-tempnet` (`ad821122`, Bot `2126609e`).
- Dieser Bericht liegt auf `messung/bch-tempnet` und kommt zusätzlich über einen eigenen `bericht/`-Branch nach main.
- Zum Vergleich: #305 (Abschluss 13.11.) und #321 (Nachtrag 14.11.) sind gemergt, #310 ist offen.

## Offene Fragen an Ben

1. **Hostname im Job-Log:** Die Fundstelle steht oben. Sollen die Logs von Lauf 10 gelöscht werden? Das kannst nur du in den Actions. Für künftige Läufe könnte `scripts/bch/tempnet_koepfe.py` die Software-Kennung im Log vor der Klammer abschneiden. Das wäre ein kleiner PR, nach dem Ende des Tempnet nur noch für eine spätere Messung nötig.
2. **Letzter Zuhörer-Nachtrag:** Sollen die letzten Zuhörerläufe bis 12:00 UTC noch in Fenster und Stücke eingehen, mit einem Stand nach dem Ende?

## Was Ben tun muss

- Die Frage zum Job-Log entscheiden. Wenn du löschen willst, geht das unter Actions, Lauf 10 von „bch tempnet“, Logs löschen.
- Den Entwurf in #ph-drafts prüfen. Er geht nicht automatisch auf X.
