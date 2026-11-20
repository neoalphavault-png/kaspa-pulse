# Erster Wochenbericht Zcash und Bitcoin Cash, Entwurf und Zahlen (Auftrag Ben 20.11.2026, Frist Sa 21.11. 16:00 Berlin)

**Kopf:** Zahlen aus unseren Datenbranches, Seite als PR in pulsehawk-site ({site_pr}, Ben merged), Forums- und X-Texte unten, Ben postet am So 22.11. Dazu die Antwort zum roten Secret-Scan (Punkt 2), zu c2 (Punkt 3) und der Plan für `tools/week_check.py` (Punkt 4).

<!-- discord -->
Erster Wochenbericht: Entwurf und Zahlen liegen bereit, die Seite liegt als PR in pulsehawk-site bei Ben. Zcash zählt {z_orph} verwaiste Blöcke neben {z_chain} Kettenblöcken, Zuhörer ohne Lücke. BCH Chipnet braucht für 6 Bestätigungen üblich {b6}, für 12 üblich {b12}, nach Ankunft beim Zuhörer. Der rote Secret-Scan vom 18.11. war kein Fund, der Bereich ließ sich nach dem Löschen des Branch nicht mehr auflösen. Bericht berichte/2026-11-21-wochenbericht-1.md
<!-- /discord -->

## Bens Antworten (20.11.), umgesetzt

- **BCH:** Wartezeit nach Ankunft beim Zuhörer, Kopfzeit als Zusatz.
- **B1 und B2** (Knoten je Client, Gebühren) werden nicht gebaut und gehen auf den Parkplatz. Der kleine Test zur Gebührenfrage ist beendet.
- **`methods/koepfe-roh`:** Ben löscht ihn in der Oberfläche.
- **Zcash:** Teilwoche mit genanntem Fenster, vom Start der Zuhörer-Serie bis zur Stichzeit des Samstagslaufs. Die Basis der Rate nach NU7 bleibt 52 von 8.609 (Serie NU7).
- **Verbindungen je Client:** Sie bleiben draußen.

## a) Zahlentabelle

Der Samstagslauf wurde von Hand gestartet (workflow_dispatch, keine Workflow-Änderung), weil der geplante Lauf in diesem Konto Stunden zu spät kommt. Die Wartezeit für k Bestätigungen ist die Zeit von einem Block, bis k weitere Blöcke gefolgt sind. Üblich ist der Median, 9 von 10 das 90. Perzentil, 99 von 100 das 99.

{tab}

**Zcash:** Die Blockabstände laufen bis zur Stichzeit {z_bis} UTC. Der Zuhörer ist bis zum Ende seines letzten fertigen Laufs ausgewertet, {l_bis}.

**BCH Mainnet:** Mainnet-Köpfe gibt es ohne neuen Bau nicht. Unser Header-Client hat kein Profil für das BCH-Mainnet, und es läuft kein Mainnet-Zuhörer. Die Mainnet-Werte sind deshalb computed aus der 10-Minuten-Regel (Erlang mit Mittel 600 s).
**Vorschlag für KW48:** im Header-Client in pulsehawk/methods ein Profil `bch-mainnet` mit Fixpunkt und BCHN-Checkpoints anlegen, dann die Wartezeiten nach Kopfzeit zählen. Das ist ein kleiner PR, Ben merged.

## Lücken der Zuhörer (UTC)

- **Zcash, Serie „dauer“ ({zl_n} Läufe):** {zl}
- **BCH Chipnet ({bl_n} Läufe):** {bl}

## b) Seite auf pulsehawk.io

{site_pr}:
- `/weekly/2026-11-22`, gebaut aus `data/weekly/2026-11-22.json`. Diese Datei schreibt der Rechenlauf, keine getippten Zahlen.
- Auf `/reports/` ein neuer Abschnitt „Which weekly reports have we published?“.
- Die Textprüfung ist bestanden. Ben merged.

## c) Forum Zcash 59124 ({zcash_kopf})

> {zcash}

## d) Forum BCH 2173 ({bch_kopf})

> {bch}

## e) X-Post @pulsehawkio ({x_kopf})

> {x}

## Punkt 2, roter Secret-Scan vom 18.11.

- **Lauf:** „secret scan“ 44383308855, Ereignis pull_request, 18.11. 19:43:54 UTC. Grün waren „selbsttest“ und „alle dateien im stand“, rot war „neue commits“.
- **Gemeldet hat er keine Datei und keine Zeile.** Der Schritt brach mit „Invalid revision range“ ab, weil git den Bereich Basis..Spitze (`bd26cc2..7bf2d82`) im Checkout nicht auflösen konnte.
- **Ursache:** Ich hatte #331 um 19:42:27 UTC gemergt und den Branch gleich gelöscht. Der Lauf startete danach und fand die PR-Spitze nicht mehr.
- **Mein Fehler dabei:** Ich habe gemergt, bevor dieser Scan überhaupt angelaufen war. Bei meiner Prüfung standen nur die drei anderen Checks da, grün.
- **Nachgeprüft:** `secret_scan.py --bereich bd26cc2..7bf2d82` lokal, 1 Commit, nichts gefunden. Der Push-Lauf auf dem Branch (19:40:38 UTC) war grün. In der Historie steht keine Stelle.
- **Ab jetzt:** Ich warte vor einem Selbst-Merge, bis auch der Scan des pull_request-Ereignisses grün ist.

## Punkt 3, c2

- Keiner der beiden Zuhörer dieses Berichts läuft auf c2, beide laufen auf GitHub.
- Der c2-Zuhörer war ein Tempnet-Zuhörer. Sein letzter Lauf war am 15.11. um 06:37 UTC.
- Ein Neustart von c2 erzeugt deshalb keine Lücke in diesem Bericht. Kommt die Uhrzeit, prüfe ich trotzdem, ob ein Lauf in dem Fenster fehlt.

## Punkt 4

`tools/week_check.py` kommt bis Mo 30.11. als PR ins Methoden-Repo.

## PR-Nummern

- {site_pr}, Wochenseite, Ben merged
- dieser Bericht

## Fragen

1. Soll ich das Profil `bch-mainnet` für den Header-Client in KW48 bauen (Vorschlag oben)?

## Was Ben tun muss

- {site_pr} mergen, am besten am So 22.11. vor dem Posten.
- Die Texte c, d und e posten.
- Frage 1 beantworten.
