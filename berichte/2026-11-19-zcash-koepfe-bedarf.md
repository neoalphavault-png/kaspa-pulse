# Zcash Mainnet: Wer braucht die täglichen Köpfe aus zcash-mainnet.yml? (Ben 19.11.2026, Frist Fr 20.11. 12:00)

Antwort Ben zu pulsehawk-site#102, Frage 1: Der tägliche Lauf bleibt an, bis der erste Wochenbericht (So 22.11.) draußen ist. Vorher klären, ob die Wochenauswertung „dauer“ und der Wochenbericht die täglichen Köpfe brauchen. Danach wird über die Abschaltung entschieden, als PR an Ben.

<!-- discord -->
Zcash, tägliche Köpfe: Die Wochenauswertung des Zuhörers dauer braucht sie nicht, sie holt ihre Kette in jedem Lauf selbst. Der Wochenbericht braucht sie nur, wenn er Blockabstände oder Bestätigungszeiten der Woche nennt. Die tägliche Kette ist dafür die einzige gespeicherte Quelle. Vorschlag nach dem 22.11.: wöchentlich statt täglich, oder die Kette im Zuhörer-Lauf speichern. Bericht berichte/2026-11-19-zcash-koepfe-bedarf.md
<!-- /discord -->

## Was der tägliche Lauf schreibt

`zcash-mainnet.yml` läuft täglich um 05:23 UTC und schreibt auf `messung/zcash-mainnet`:
- `data/zcash-mainnet/koepfe.csv.gz` und `koepfe-meta.json`, die ganze Kette ab Höhe 3.489.717 (20.9.), jeden Tag neu
- `aktuell.json` und `aktuell.md`
- mittwochs `stand-JJJJ-MM-TT.json` und `.md`, dazu bis 18.11. die CSV der Abstände nach NU7

Ein neuer Stand löst `ph-entwurf-zcash-mainnet.yml` aus, den Entwurf in Discord, der die täglichen Köpfe liest. An Tagen ohne neuen Stand sendet er nichts.

## Wer die täglichen Köpfe liest

| Nutzer | braucht die täglichen Köpfe? | Beleg |
|---|---|---|
| Wochenauswertung „dauer“ (`zcash-mainnet-lauscher.yml`, `lauscher_auswertung.py` und `lauscher_woche.py`) | **nein** | Schritt „kette danach abrufen“ holt in jedem Lauf eine eigene Kette mit `zcash_koepfe.py` nach `$RUNNER_TEMP/kette.csv.gz`, ab der kleinsten Peer-Höhe der Serie minus 100. Beide Auswertungen lesen nur diese Kette. |
| `wochen.csv` und `wochen.json` (Kettenblöcke, angekündigt, abgehängt, Tiefe je Woche) | **nein** | dieselbe Kette aus dem Zuhörer-Lauf |
| PH-Entwurf Zcash | ja, aber nur zum Mittwochsstand | `--koepfe daten/data/zcash-mainnet/koepfe.csv.gz` |
| Wochenbericht Zcash und BCH (Sa 22.11.) | **nur für Blockabstände** | Abstände, Median, Anteil über 75 s und Bestätigungszeiten der Woche kommen aus einer gespeicherten Kette. Die einzige gespeicherte Zcash-Kette ist die tägliche `koepfe.csv.gz`. Die Kette des Zuhörer-Laufs liegt nur im Runner und wird nicht gespeichert. Die Zuhörer-Zahlen der Woche (verwaiste Blöcke) brauchen sie nicht. |

Der BCH-Teil des Wochenberichts hängt nicht an diesem Lauf. Er nutzt die Chipnet-Köpfe und den Chipnet-Zuhörer.

## Folgerung

- **Wenn der Wochenbericht Zcash-Blockabstände nennen soll:** Die Köpfe werden mindestens einmal je Woche gebraucht, kurz vor dem Bericht. Täglich ist dafür nicht nötig.
- **Wenn er für Zcash nur die Zuhörer-Zahlen nennt:** Der tägliche Lauf wird nicht mehr gebraucht.

## Vorschlag für den PR nach dem 22.11. (Ben merged)

1. **Variante A, empfohlen:** `zcash-mainnet.yml` läuft wöchentlich statt täglich, Sa früh vor dem Wochenbericht. Der Mittwochsstand und sein Discord-Entwurf entfallen damit oder wandern auf Samstag.
2. **Variante B:** Der Zuhörer-Lauf speichert seine Kette zusätzlich auf `messung/zcash-mainnet`, und der tägliche Lauf wird abgeschaltet. Das ändert zwei Workflows.
3. **Variante C:** abschalten, nur wenn der Wochenbericht für Zcash keine Blockabstände nennt.

## PR-Nummern

- dieser Bericht

## Fragen

1. Soll der Wochenbericht für Zcash Blockabstände oder Bestätigungszeiten der Woche nennen? Davon hängt ab, ob A oder C passt.
2. Soll der Mittwochsstand mit Discord-Entwurf weiterlaufen? Wenn nicht, passt A mit Samstag.

## Was Ben tun muss

- Die zwei Fragen beantworten. Den PR baue ich nach dem 22.11.
