# Bericht 24.10.2026: Zahl des Tages, „now“ raus aus drei Vorlagen

Branch `fix/nod-now-vorlage`, eigener kleiner PR von main (Ben, 24.10.2026).

## Befund
- **Ursache:** Die Echtzeit-Wache aus #124 (gemergt am 21.10.) erkennt „now“ als Echtzeitwort. `number_of_day_data.py` hatte das Wort in drei festen Vorlagen. Deshalb war `--selbsttest` auf main rot.
- **Der tägliche Lauf ist betroffen.** Der Workflow ruft den Selbsttest zwar nicht auf. Im echten Lauf prüft aber `write_out()` den Text des gewählten Kandidaten mit derselben Wache (`walk_and_check`). Gewinnt ein betroffener Kandidat, bricht der Schritt „pick the number“ ab: Der Lauf ist rot, und es gibt keinen Post.
  - `weekly_line`: „that has now been true for … weeks in a row“. Dieser Kandidat kann an jedem Tag gewinnen, zuletzt am 21.10. (vor #124).
  - `cut_today`: „the network now mints …“ im Post und „… from now on“ in der Bildzeile. Er gewinnt nur am Tag einer Senkung, dann vor allen anderen; die nächste ist am 4.11.2026.
- **Bisher ohne Ausfall:** Seit #124 hat keiner der beiden gewonnen. Die Läufe vom 22. und 23.10. sind grün (whale_weight, mined_left).

## Was gemacht wurde
- „the network now mints %s fewer KAS per day“ heißt jetzt „the network mints %s fewer KAS per day than before the cut“.
- „… minted every day from now on.“ heißt jetzt „… minted every day from this cut on.“
- „that has now been true for %d weeks in a row.“ heißt jetzt „that has been true for %d weeks in a row.“
- Zahlen und Aussagen bleiben gleich, nur die Formulierung ändert sich.
- **Geprüft:**
  - `number_of_day_data.py --selftest` ist grün, unter anderem „jeder kandidat liefert einen posttext“ und „posttexte halten den hausstil“.
  - Grün sind auch die Selbsttests von `number_of_day`, `x_post`, `content_wache` und `tagesgrafik`.
  - Secret-Scan sauber.

## PR-Nummern
- dieser PR: die Nummer trage ich beim Öffnen nach
- Zusammenhang: #124 (die Wache), #137 (Jekyll)

## Offene Fragen an Ben
Keine.

## Was Ben tun muss
- **Diesen PR bald mergen.** Gewinnt `weekly_line`, bleibt der Tag ohne Zahl. Spätestens muss er vor dem 4.11. drin sein, dem Tag der nächsten Senkung.
