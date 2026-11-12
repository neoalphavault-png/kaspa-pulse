# Stand: KASPA WEEKLY vorbereiten (Routine 3)

**So 08.11.2026, 08:35 Berlin time.** Lauf für die Montagsfolge am
09.11.2026 und den Montags-Short desselben Tages.

Diese Datei ist die Ablage des Kopfteils der Meldung an Ben. Sie enthält
keine Skripte, keine Titel und keine Uploadfelder — das Repo ist öffentlich.

---

## Zahl der Woche

Kaspa hat die Woche zum 07.11.2026 bei 0,02967 $ geschlossen, 8,90 % tiefer,
und steht 15,54 % unter der 50-Wochen-Linie — der weiteste Abstand unter
dieser Linie seit der Woche zum 05.09.2026, gezählt in den 53 Wochen, die
unsere Reihe diese Linie führt, und die zweite Woche in Folge unter beiden
Linien.

## Prüfzeilen

- **Short-Skript enthalten: ja, Manifest-Eintrag: ja.**
- **Rekorde geprüft: alle mit Zeitraum.** Vier Rekord-Aussagen, jede mit
  ihrem Fenster im selben Satz: „widest gap … in nine weeks", „the fewest
  sats in nine weeks", „the third strongest of the ten full weeks in our own
  log", „five of them closed above it … fifty three weeks". Ausdrücklich
  **kein** Allzeitwert: der Abstand ist der 45.-weiteste von 53 Wochen.
- **Quellen geprüft: ok.** Zwei fremde Zahlen im Gesprochenen, beide mit
  „source kaspalytics" im selben Satz. Nichts ergänzt, nichts nachgetragen.
- **Keine Wenn-dann-Sätze zum Kurs: geprüft.** `preis_wache.verstoesse()`
  und `weekly_numbers.kurs_wenn_dann()` über Skript, Beschreibung, Pin,
  X-Teaser, Telegram, Discord, Short und Befund: leer. Erste Folge, die den
  Schwellensatz durch die beiden Linienwerte als Daten ersetzt.
- **Telegram 440 Zeichen, Discord 444 Zeichen, Verhältnisse geprüft, keine
  Echtzeit-Wörter.**
- **Gegenprobe bestanden:** dieselbe Rechnung reproduziert die vierzehn
  Endzahlen der Vorwoche exakt.
- **Maschinelle Prüfung des Sprechskripts:** 690 Wörter, längster Satz 14
  Wörter, 0 Ziffern, 0 verbotene Wörter; elf Befunde der Wache, alle von
  Hand geprüft und im Paket einzeln begründet (Einheiten, Liniendefinition,
  Rückbezug, feste Wendung, Linienwert-Sätze, ein Fehlalarm).
- **Test dieser Woche: keiner von Ben freigegeben.** Der Uhrwerk-Bericht vom
  02.11. schlägt zwei vor, eine Freigabe steht in keiner Datei. Es gilt nur
  Test & Compare.

## Zahlen auf offen

| Zeile | Letzte echte Messung | Alter am Montag |
| --- | --- | --- |
| Gebührenanteil in Dollar (`fees_day`) | Mo 17.08.2026 | 84 Tage |
| Kaspalytics-Wochenzeile (tps, Halter, aktive Adressen, Börsen, ruhender Anteil) | Mo 02.11.2026 | 7 Tage |
| vidIQ-Score der drei Cover | nicht gemessen, das Werkzeug braucht eine abrufbare Adresse | — |

Alles Übrige ist gerechnet. Die drei Titel **sind** gescort, vidIQ war in
dieser Sitzung angemeldet.

## Datenausfall

| Reihe | Letzter gültiger Wert |
| --- | --- |
| `fees_day` / `fees_7d` | Wochenzeile Mo 17.08.2026 |
| Entity-X-Transaktionsliste mit Absender-Label | keine Liste für 01.–07.11.2026 |
| `igra_tx` / `kasplex_tx` | dauerhaft `null` |

Keine dieser Reihen trägt eine gesprochene Zahl. Die beiden fremden
Datendienste sind aus dieser Sitzung durch die Netzrichtlinie nicht
erreichbar; die Kaspalytics-Zeile ist deshalb die vom 02.11.2026.

## Branch und Head

- **Lieferung:** `review/weekly-2026-11-09` in `pulse-studio`, Head
  `f8583bf`, ein Commit, nichts unter `.github/workflows/`.
- **Diese Ablage:** `claude/ablage-weekly-vorbereiten` in `kaspa-pulse`.

## Was Ben tun muss

1. Die Lieferung bis Sonntagabend mergen, sonst rechnet die Montagsroutine
   selbst.
2. Die sechs m4a der Folge in die Rendersitzung geben, die eine m4a des
   Shorts in die Shorts-Builder-Sitzung.
3. Entscheiden, ob die Wochenseiten-Adresse in Telegram und Discord
   UTM-Parameter tragen soll — die Form steht in der Lieferung, sie braucht
   vorher einen Eintrag in `docs/kanal-links.md`.
4. Zur Kenntnis: die vier Donnerstags-Titel der Woche 46 sind am 08.11.
   nachgemessen worden, drei liegen unter 85. Geändert wurde keiner, das ist
   die Lieferung eines anderen Laufs.
