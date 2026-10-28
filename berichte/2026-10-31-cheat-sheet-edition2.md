# Bericht 31.10.2026: Cheat Sheet Edition 2 am So 1.11. absichern

Auftrag von Ben vom 28.10.2026. Frist Sa 31.10.2026 18:00 Berlin, gebaut am 28.10.2026.

## Kurz
- **Ohne diese Änderungen wäre Edition 2 am Sonntag nicht erschienen.** Der erste Probelauf mit echten Daten brach ab: Die Umlaufreihe `supply/circulating` gibt es bei Kaspalytics nicht, HTTP 404. Der Generator war bis dahin nur mit der festen Probe gelaufen.
- **Jetzt ist der Probelauf grün.** Alle 8 Stichtage liegen am 1.11. innerhalb der 10-Tage-Frist, auch wenn bis dahin keine Reihe neue Daten bekommt.
- **Instagram:** Die 10 Seiten kommen als PNG in 1080x1350. Am Sonntag gehen sie mit deiner Caption als „📤 VON HAND“ nach #moderator-only.
- **Look:** Es bleibt der bisherige Look, siehe Teil 4.

## 1. Seite 10, Linktext
„live numbers“ heißt jetzt **„the dashboard“**, wie in der IG-Fassung 2.2. Kein anderer freigegebener Satz ist geändert.

## 2. Probelauf mit echten Daten, ohne Veröffentlichung
**Lauf 40662673288 vom 28.10.2026, 09:14 UTC, Dispatch auf `cheat/edition2`, `veroeffentlichen=false`, grün.**

| Zahl | Stichtag | Alter am 1.11., ohne neue Daten | Quelle |
| --- | --- | --- | --- |
| Entity X | 28.10.2026 | 4 Tage, am Sonntag frisch gemessen | api.kaspa.org |
| Entity X, Umlauf | 26.10.2026 | 6 Tage | weekly.json |
| Börsen | 25.10.2026, Sonntagspunkt | 7 Tage | Kaspalytics, Umlauf computed |
| Unbewegt | 27.10.2026 | 5 Tage | Kaspalytics |
| Halter | 25.10.2026 | 7 Tage | Schwellenlog |
| Senkung | 28.10.2026 | computed, am Sonntag neu gerechnet | Emissionsplan |
| Gebühren | 28.10.2026, Fenster 28.09. bis 27.10. | 4 Tage | tagesgrafik-log |
| Hashrate | 27.10.2026, Mittel 21. bis 27.10. | 5 Tage | api.kaspa.org |
| Covenants | 25.10.2026 | 7 Tage | Covenant-Log |

- **Börsen:** Am 1.11. ist der Sonntagspunkt der 25.10., weil der laufende Tag nicht zählt. Das sind 7 Tage, also innerhalb der Frist. Am 28.10. stand der Anteil bei 13.4% (3,722,422,346 KAS).
- **Gebühren:** Das Tageslog wird jeden Morgen vor dem Cheat Sheet geschrieben, Tagesgrafik 07:30, Cheat Sheet 09:00.
- **Unbewegt:** 51.2% für 1 Jahr und 26.3% für 2 Jahre. Beide liegen im Fenster, 45 bis 55% und 20 bis 30%. Also kein Abbruch, und „half“ und „a quarter“ stimmen.
- **Gegenprobe mit `--stand 2026-11-01`:** Mit den Daten vom 28.10. als Sonntag gebaut. Die Frist hält, die ältesten Zahlen sind 7 Tage alt.

**Was der Probelauf gefunden hat, alles behoben:**
1. **Umlauf für den Börsenanteil:** Es gibt keine Kaspalytics-Reihe dafür, HTTP 404 in Lauf 40661550981. Jetzt nimmt der Generator den Umlauf aus `api.kaspa.org/info/coinsupply`, wie Tagesgrafik und Wochenzahlen. Für jeden Sonntag rechnet er ihn über den Emissionsplan zurück, das ist computed. Der Fehler liegt unter 1 zu 100.000.
   - Gegenprobe: Der 4.10. ergibt 13.63%, Edition 1 zeigte 13.6%.
2. **Spanne auf Seite 3:** Kaspalytics liefert die Unbewegt-Reihe ab 2023. Ohne Grenze hätte dort „logged by us every week since august, the share sat between 14.1% and 51.3%“ gestanden. Jetzt zählt die Spanne ab unserem ersten Sonntag, dem 26.07.2026, wie in Edition 1: 50.5% bis 51.3%. Der Satz ist unverändert.
3. **Kontrast in den Diagrammen:** Mit echten Daten lag die Teal-Linie unter drei Marken, 1.4:1. Die Marken weichen der Linie jetzt aus, keine verdeckt einen Wert.
4. **Krumme Achsen:** Die Hashrate-Achse zeigte 333 und 367, und „mean 369“ lag auf der 367. Jetzt gibt es drei glatte Schritte (300, 340, 380, 420), und die Beschriftung unter „mean“ fällt weg.
   - Damit ändert sich auch die Börsen-Achse der Edition-1-Daten, von 13.4 bis 14.4 auf 13.4 bis 14.6.

**Nebenwirkung:** Der erste, rote Probelauf (40661550981) hat über den alten Rot-Schritt auf main „cheat sheet ist rot“ nach #moderator-only geschickt. #184 ist noch nicht gemergt, mit #184 ginge so etwas nach #ops-log. Die grünen Probeläufe haben nichts nach Discord geschickt. Von einem anderen Branch als main ist jeder Lauf jetzt eine Probe, und solange `DISCORD_WEBHOOK_LOG` fehlt, steht alles nur im Job-Log.

## 3. Instagram-Karussell
- **Bilder:** Jede der 10 Seiten zusätzlich als PNG in 1080x1350, in der Reihenfolge des PDF. Sie liegen im Artefakt unter `kaspa-pulse-cheat-sheet-edition-2-instagram/`.
- **Kontrast:** Er wird auf jeder Seite im fertigen Bild gemessen, mindestens 7:1. Verfehlt eine Seite den Wert, geht kein Paket raus, nur die Liste nach #ops-log.
- **Farben, keine Sätze:** Damit alle Seiten 7:1 schaffen, habe ich nur Farben geändert.
  - Die dritte Schriftfarbe geht von #6F7E7B (4.6:1) auf #96A5A2 (7.7:1).
  - Die Trichter-Balken werden dunkler, mit weißer Schrift darauf 11:1.
  - Die Anker der Treppe sind jetzt weiß.
- **Am Sonntag, nicht scharf, zwei Nachrichten „📤 VON HAND“ nach #moderator-only:**
  1. **Freigabe:** Deckblatt und PDF. Darin steht jetzt auch der zweite Schritt: Nach `CHEAT_SHEET_LIVE=scharf` musst du cheat-sheet noch mit `veroeffentlichen=true` starten. Vorher stand nur der erste Schritt da.
  2. **Upload-Paket:** die 10 Seiten mit der Caption, wortgleich mit deinem Text. Nur Edition und Monat kommen aus dem Lauf.
     ```
     the 8 kaspa numbers whales watch. edition 2, november 2026. every number dated, with its source. save it for later. the full cheat sheet arrives by email, link in bio. #kaspa #kas #blockdag
     ```
- **Kein Doppel:** Am 1.11. ist Winterzeit. Dann trifft der Cron um 08:00 UTC genau 09:00 Berlin, gleichzeitig mit dem c2-Takt. Der Cron-Lauf meldet nicht, wenn heute schon ein Lauf „bauen und melden“ grün beendet hat. Ein Lauf von Hand meldet immer.

## 4. Look v2
Bis zum Bau am 28.10. lag keine Wahl vor. Nach deiner Regel bleibt deshalb der bisherige Look, und Look v2 kommt mit Edition 3. Wählst du heute Abend und willst es trotzdem für Edition 2, sag es. Ich baue es nur, wenn es bis Sa 31.10. 18:00 sauber durch die Probe geht.

## 5. UTM
Beide Links im PDF tragen `utm_campaign=edition2`. Die Nummer kommt aus dem Ausgabe-Log, und der Selbsttest prüft das.

## Textregeln, deine Entscheidung
Die Wache findet in vier freigegebenen Sätzen Echtzeit-Wörter. Ich habe sie **nicht** geändert, weil du nur „live numbers“ freigegeben hast.

| Seite | Satz | Vorschlag |
| --- | --- | --- |
| 2 Börsen | „that share has slipped from 14.2% in august to 13.4% **now**.“ | „… to 13.4% on 25 oct.“ |
| 5 Senkung, Diagramm | „2.06 **now**“ | „2.06 until 4 nov“ |
| 6 Gebühren | „**today** the network is paid by issuance.“ | „the network is paid by issuance.“ |
| 8 Covenants | „since the toccata upgrade went **live** on 30 june“ | Fehlalarm, das ist ein datiertes Ereignis. Ich würde es lassen. |

Sagst du bis Sa 31.10. 18:00 Bescheid, ändere ich genau diese Stellen. Sonst gehen sie wie in Edition 1 raus.

## PR-Nummern
- PR „Cheat Sheet Edition 2 absichern“ von `cheat/edition2`. Nummer und Merge stehen unten, sobald er durch ist.

## Was Ben tun muss
Siehe „📤 VON HAND“ im Discord-Abschnitt.

<!-- discord -->
**Cheat Sheet Edition 2, abgesichert, 28.10.2026**
- **Ohne Fix wäre Sonntag nichts gekommen:** Die Umlaufreihe für den Börsenanteil gab es bei Kaspalytics nicht (HTTP 404). Jetzt kommt der Umlauf aus der Kaspa-API und dem Emissionsplan, wie bei Tagesgrafik und Wochenzahlen.
- **Probelauf mit echten Daten grün:** Alle 8 Stichtage halten am 1.11. die 10-Tage-Frist, am ältesten sind Börsen, Halter und Covenants mit 7 Tagen. Unbewegt 51.2% und 26.3%, beide im Fenster.
- **Seite 10:** „the dashboard“ statt „live numbers“. utm_campaign=edition2.
- **Instagram:** 10 PNG in 1080x1350, jede Seite ab 7:1. Dafür sind nur Farben geändert, keine Sätze.
- **Look:** Es bleibt der bisherige, Look v2 kommt mit Edition 3.
- **Bericht:** berichte/2026-10-31-cheat-sheet-edition2.md
<!-- teil -->
📤 VON HAND, bis Sa 31.10. 18:00, Discord. **Vier Sätze mit Echtzeit-Wort, ändern oder lassen?**
Ich habe sie nicht angefasst. Eine Antwort genügt, zum Beispiel „1 bis 3 ändern“.
1. Seite 2: „… to 13.4% now.“ Vorschlag: „… to 13.4% on 25 oct.“
2. Seite 5, Diagramm: „2.06 now“. Vorschlag: „2.06 until 4 nov“
3. Seite 6: „today the network is paid by issuance.“ Vorschlag: „the network is paid by issuance.“
4. Seite 8: „went live on 30 june“. Fehlalarm, ich würde es lassen.
https://github.com/neoalphavault-png/kaspa-pulse/blob/main/berichte/2026-10-31-cheat-sheet-edition2.md
<!-- teil -->
📤 VON HAND, So 1.11. ab 09:00 Berlin, Discord. **Was am Sonntag kommt**
Zwei Nachrichten hier in #moderator-only.
1. Freigabe mit Deckblatt und PDF. Erst Variable CHEAT_SHEET_LIVE auf scharf, dann cheat-sheet mit veroeffentlichen=true starten.
2. Instagram-Paket, 10 Seiten und die Caption, posten von Hand.
https://github.com/neoalphavault-png/kaspa-pulse/actions/workflows/cheat-sheet.yml
<!-- /discord -->
