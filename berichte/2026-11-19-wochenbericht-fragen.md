# Fragen vor dem ersten Wochenbericht (Auftrag Ben 19.11.2026, Frist Fr 20.11. 12:00)

**Kopf:** Antworten auf A, B und C aus vorhandenen Daten, nichts Neues gebaut. Dazu Bens Antworten zu #332. Bericht auf `bericht/2026-11-19-wochenbericht-fragen`, Selbst-Merge. Die Punkte D (Ringversuch) und E (Historie alexandria-anker) stehen in eigenen Berichten im selben PR.

<!-- discord -->
Fragen vor dem Wochenbericht: A, BCH Chipnet, die 12-Block-Fenster sind gezählt, nach Ankunft beim Zuhörer im Median 12 min 6 s. B, Zcash: Client und Version lassen sich je Verbindung aus vorhandenen Daten zählen, je Knoten mit einem Tag Arbeit. Gebühren lassen sich nicht aus vorhandenen Daten zählen und mit einem Tag nur teilweise. C, für die Rate gilt 8.609, die 9.062 enthalten 453 Blöcke vor NU7. Bericht berichte/2026-11-19-wochenbericht-fragen.md
<!-- /discord -->

## Antworten von Ben zu #332, aufgenommen

- **Blockabstände im Wochenbericht:** Der Wochenbericht nennt für Zcash Blockabstände und Bestätigungszeiten der Woche: Median, Anteil über 75 s, Wartezeit für 1, 3 und 6 Bestätigungen. Daher **Variante A**: `zcash-mainnet.yml` läuft wöchentlich, Samstag früh vor dem Bericht. Der PR kommt nach dem 22.11., Ben merged.
- **Mittwochsstand:** Er entfällt samt Discord-Entwurf.
- **Korrektur zu #332:** Der erste Wochenbericht erscheint am **Sonntag** 22.11., nicht am Samstag. Der Lauf am Samstag früh liegt davor.

## A. BCH Chipnet, Dauer von 12-Block-Fenstern (counted)

**Geht mit vorhandenen Daten.**
- **Köpfe:** frisch vom 19.11. 15:30 UTC, Lauf „bch chipnet“ (Commit `58e14ab`), Spitze 338.350, Gegenprobe mit drei Peers je 500 von 500.
- **Zeitraum:** ab der Aktivierung, also ab Block 332.451 (Vorgänger 332.450, 15.11. 12:33:16 UTC) bis 338.350 (19.11. 15:30:39 UTC).
- **Fensterdefinition:** Ein 12-Block-Fenster ab Block h ist die Zeit vom Kopf von h−1 bis zum Kopf von h+11, also die Wartezeit, bis 12 Blöcke dazugekommen sind.

**Nach Kopfzeit:**

| | überlappend (jeder Startblock) | getrennt (alle 12 Blöcke ein neues Fenster) |
|---|---:|---:|
| Fenster | 5.889 | 491 |
| Median | 12 min 4 s | 11 min 59 s |
| p10 / p90 | 8 min 40 s / 15 min 36 s | 8 min 41 s / 15 min 39 s |
| p99 | 19 min 59 s | 19 min 43 s |
| kürzestes | −5 min 38 s, ab Block 336.621 | −16 s, ab Block 335.427 |
| längstes | 25 min 25 s, ab Block 336.609 | 24 min 21 s, ab Block 335.571 |

Kopfzeiten setzen die Miner, im Testnetz sind sie nicht monoton. Deshalb gibt es negative Fenster. Für eine Wartezeit taugt die Ankunft beim Zuhörer besser:

**Nach erster Sichtung beim Chipnet-Zuhörer** (17.11. 19:46 bis 19.11. 14:49 UTC, Blöcke 335.748 bis 338.315, jeder Block gesehen, keine Lücke):

| | überlappend | getrennt |
|---|---:|---:|
| Fenster | 2.556 | 213 |
| Median | 12 min 6 s | 12 min 8 s |
| p10 / p90 | 7 min 43 s / 16 min 18 s | |
| p99 | 19 min 43 s | |
| kürzestes | 2 min 45 s, ab Block 336.625 | 2 min 45 s |
| längstes | 21 min 58 s, ab Block 337.600 | 20 min 34 s |

Zum Vergleich: ein einzelner Abstand seit der Aktivierung, nach Kopfzeit, liegt im Median bei 53 s, im Mittel bei 60,38 s (5.900 Abstände). 1.662 dieser Blöcke tragen Difficulty 1. Sie sind in den Fenstern enthalten, denn auch sie bestätigen.

## B. Zcash, kleiner Test zur Gebührenfrage (Schluss Fr 27.11.)

**B1. Knoten je Client und Version: geht mit vorhandenen Daten, aber nur als Verbindungen.**
- **Quelle:** Der Zuhörer „dauer“ schreibt je Lauf die Software-Kennung jeder Verbindung. Das sind 30 Läufe vom 12.11. 21:36 bis 19.11. 14:51 UTC, mit 1.096 Verbindungen.
- **Verbindungen je Client:**
  - **Zebra:** 7.0.0 mit 457 Verbindungen in allen 30 Läufen, 7.1.0 mit 188, ältere und „-modified“ einzeln.
  - **Zakura:** 1.8.5 bis 1.8.9 mit zusammen 407, dazu ältere.
- **zcashd:** In 30 Läufen kam keine einzige Verbindung zu zcashd (Kennung „MagicBean“).
- **Grenze:** Das sind Verbindungen, keine Knoten. Wir speichern keine Adressen, deshalb lässt sich ein Knoten über Läufe hinweg nicht wiedererkennen. Der Zuhörer hält außerdem gezielt 8 Verbindungen je Software, das Verhältnis Zebra zu Zakura ist also gewählt, nicht gemessen.
- **Knoten zählen geht mit einem Tag Arbeit:** Ein Lauf fragt alle Adressen aus den Seeds und per getaddr einmal ab. Er hält die Adressen nur im Speicher, um doppelte zu erkennen, und speichert nur Software und Version.

**B2. Blöcke mit Transaktionen unter der Gebührengrenze: geht nicht mit vorhandenen Daten, mit einem Tag nur teilweise.**
- **Grenzen aus den Clients**, beide als `MARGINAL_FEE` in `zip317.rs`, Einheit zatoshi je logischer Aktion, mindestens 2 Aktionen (GRACE_ACTIONS):
  - Zebra: 1.000 im Release v7.1.0 und auf main
  - Zakura: 400, im Code auf main (Stand 19.11.)
  - Die Werte aus dem Arborist Call stimmen damit überein.
- **Was uns fehlt:**
  - Der Zuhörer hält nur Köpfe und Ankündigungen, keine Transaktionen.
  - Um die Gebühr einer Transaktion zu rechnen, braucht man den Block und für transparente Eingänge den Betrag der Vorgänger-Ausgabe. Den liefert nur ein Knoten mit Index.
- **Mit einem Tag:** Volle Blöcke per P2P holen und die Gebühr für Transaktionen ohne transparente Eingänge rechnen, also aus den Wertbilanzen. Transaktionen mit transparenten Eingängen blieben offen. Das Ergebnis wäre also eine Teilmenge, kein voller Anteil.
- **Vollständig** geht es erst mit einem eigenen Zebra-Knoten. Das wäre eine Fixkosten-Frage.

Keine Position zur Gebühr.

## C. Basis der Zuhörer-Serie NU7: 9.062 oder 8.609

Beide Zahlen stammen aus derselben Auswertung, `lauscher-nu7/zusammenfassung.json`:
- **9.062:** Kettenblöcke im ganzen Fenster des Zuhörers, 5.11. 17:02 bis 8.11. 15:30 UTC. Darin sind 453 Blöcke **vor** der Aktivierung (5.11. 17:02 bis 6.11. 02:34 UTC), mit 0 abgehängten.
- **8.609:** nur die Kettenblöcke **ab** NU7. Die öffentliche Rate 0,60 % ist 52 von 8.609.
- 9.062 = 453 + 8.609. Ebenso zerfällt „angekündigt“ in 9.055 = 453 + 8.602.

**Für den Wochenbericht gilt 8.609**, wenn es um die Rate nach NU7 geht. 9.062 gehört nur zu einer Aussage über das ganze Zuhörer-Fenster. In #330 steht 9.062, weil dort der ganze Abgleich mit Sovright gemeint war. Der Satz „52 orphans“ stimmt in beiden Fällen.

## Nebenbei

- `methods/koepfe-roh` in kaspa-pulse ließ sich nach dem Merge von methods#7 nicht löschen. Der Push zum Löschen brach zweimal ab („remote end hung up“). Andere Branches ließen sich heute löschen. Vermutlich liegt es an der Workflow-Datei auf diesem Branch. Ich habe das nicht umgangen.

## PR-Nummern

- dieser PR, drei Berichte: Fragen, Ringversuch, Historie

## Fragen

1. **Wartezeit im Wochenbericht, BCH:** Soll der Bericht die Wartezeit nach Ankunft beim Zuhörer nennen? Mein Vorschlag ist ja, mit Kopfzeit als Zusatz.
2. **B1 und B2:** Soll ich einen davon bis Fr 27.11. bauen? B1 ist ein Tag. B2 liefert in einem Tag nur eine Teilmenge.
3. **`methods/koepfe-roh`:** Kannst du den Branch in der GitHub-Oberfläche löschen?

## Was Ben tun muss

- Die drei Fragen beantworten.
