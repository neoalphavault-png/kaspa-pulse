# BCH Tempnet, Klärung zum Zuhörer für die Forum-Antwort (7.11.2026)

Ben hat am 7.11. drei Fragen für eine Antwort an rufitnes (#35) und bitcoincashautist (#34) gestellt, Frist So 8.11. 12:00. Grundlage ist der Zuhörer `scripts/bch/tempnet_lauscher.py` mit den Daten auf `messung/bch-tempnet`, Stand nach Lauf 20261107T0235.

<!-- discord -->
BCH Tempnet, Klärung für die Forum-Antwort. Erste Sicht und Ankündigungsweg gibt es je Block. Die Uhr ist die NTP-Uhr des GitHub-Runners, einen Versatz haben wir nicht mitgeschrieben. Die CSV je Block mit Stale nach 6 liegt auf messung/bch-tempnet. Bericht berichte/2026-11-07-bch-zuhoerer-klaerung.md
<!-- /discord -->

## 1. Erste Sicht und Ankündigungsweg je Block

**Ja.** `data/bch/lauscher/bloecke.csv` hat je Kettenblock:
- `first_seen_utc`: erste Ankündigung bei uns, auf die Millisekunde.
- `first_seen_type`: Weg dieser ersten Ankündigung, also `inv`, `headers` oder `cmpctblock`.
- dazu die erste Ankunft je Weg (`first_inv_utc`, `first_headers_utc`, `first_cmpctblock_utc`), die Zahl der ankündigenden Peers und den Spread über die Peers.

Die Rohdaten je Ankündigung (Zeit, `peer_N`, Weg, Hash) liegen je Lauf in `ereignisse.jsonl.gz`.

**Verteilung der ersten Ankündigung über 17.765 gesehene Kettenblöcke:**
- `inv` 17.736
- `headers` 29
- `cmpctblock` 0

Wir bitten jeden Peer per `sendcmpct` um Compact Blocks im High-Bandwidth-Modus. Trotzdem kam kein `cmpctblock` von selbst zuerst. Ein Compact Block kam erst, nachdem wir ihn angefragt hatten (bei 17.348 Blöcken).

## 2. Uhr der Zuhörer-Läufe

- **Zeitquelle:** die Systemuhr des GitHub-Runners (ubuntu-24.04). Im `meta.json` jedes Laufs steht „Uhr des Runners (NTP), Millisekunden“. Die Uhr stellt das Runner-Image, nicht wir. Welchen Dienst es nutzt (chrony oder systemd-timesyncd), haben wir nicht geprüft.
- **Versatz:** Den haben wir **nicht** mitgeschrieben. Es gibt keine gezählte Zahl dazu.
- **Indirekte Schranke, kein Messwert:** Über 17.765 Blöcke lag unsere Erste Sicht immer nach der Kopfzeit, im Minimum 0,058 s danach (Median 2,5 s). Ginge unsere Uhr deutlich nach, kämen Blöcke scheinbar vor ihrer Kopfzeit an. Das passt zu einer Uhr, die höchstens Bruchteile einer Sekunde nachgeht. Die Kopfzeit setzt aber der Miner, und sie ist auf ganze Sekunden abgeschnitten. Belegen lässt sich so nur die grobe Richtung.
- **Vorschlag für die restlichen Läufe bis 15.11.:** Am Anfang und am Ende jedes Laufs `chronyc tracking` mitschreiben, nur die Zeilen zu Versatz und Status, ohne Referenz-ID und ohne Server. Das ist eine Änderung an `.github/workflows/bch-tempnet-lauscher.yml` auf main, die prüfe ich und du mergst sie. Für die bisherigen 297 h hilft das nicht mehr.

## 3. CSV je Block

**Ja, sie liegt bereit:** `data/bch/lauscher/forum/tempnet-first-seen-2026-10-25-bis-2026-11-07.csv` auf `messung/bch-tempnet` (Commit `dbae9da`), mit README.
- **Spalten:** `height`, `hash`, `header_time_utc`, `first_seen_utc`, `announce_type`, `stale_after_6`.
- **Zeitraum:** 55 Läufe vom 25.10. 09:15 bis 7.11. 08:05 UTC, zusammen 297,2 h. Die kleinen Lücken zwischen den Läufen sind nicht abgedeckt.
- **Umfang:** 18.686 Zeilen, Höhen 341.252 bis 359.938. Das sind 17.808 Kettenblöcke, davon 43 ohne Erste Sicht, weil sie in eine Lücke fielen. Dazu 878 Stale-Blöcke (4,71 % der angekündigten Blöcke).
- **Stale nach 6:** Ein Block ist stale, wenn er uns angekündigt wurde und nicht in der Kette steht, obwohl die Kette 6 Blöcke darüber reicht. Kein Fall ist mehr offen.
- Ein Zuhörer an einem Ort, kein eigener Knoten. Keine IPs, keine Hostnamen, keine Peer-Adressen.

## Offene Fragen an Ben

1. Soll ich die Uhr-Zeilen (`chronyc tracking`, nur Versatz) für die restlichen Läufe als PR vorbereiten?
2. Soll die CSV im Forum verlinkt werden? Der Link ginge auf den Messbranch des öffentlichen Repos. Nach den Textregeln stehen in Forumsposts keine Links, also entscheidest du.

## Was Ben tun muss

1. Die Forum-Antwort aus diesem Bericht schreiben (Haupt-Sitzung), bis So 8.11. 12:00.
