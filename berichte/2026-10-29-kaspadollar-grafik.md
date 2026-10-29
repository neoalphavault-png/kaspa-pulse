# KaspaDollar-Grafik, Stand 28.10.2026 12:42:28 UTC

Bericht für Ben zum Auftrag vom 29.10.2026.

## Was gemacht wurde

Ben hat am 29.10. entschieden, den Stand 28.10. 12:42:28 UTC zu veröffentlichen:
- 182.012,19 KAS counted (Kontrollzählung, eigener Knoten)
- 182.012 KAS laut KaspaDollar-Seite zur selben Minute
- 0 Abgänge
- 3,6 % von 5.000.000 laut Seite

Zwei PNG mit 1080 x 1350 px im Look v2, Richtung A auf Papier, Wortmarke schwarz, kein Falke:

| Datei | Für |
|---|---|
| `kaspadollar/ergebnis/kaspadollar-spenden-2026-10-28-en.png` | englisch |
| `kaspadollar/ergebnis/kaspadollar-spenden-2026-10-28-de.png` | Telegram-Gruppe Kaspa German |

- **Werkzeug:** Gebaut mit `scripts/kaspadollar_grafik.py`. Es liegt im PR [#201](https://github.com/neoalphavault-png/kaspa-pulse/pull/201) (Branch `daten/kaspadollar-2026-10-28`), dort stehen auch Bilder und Bericht.
- **Wache:** Beide Bilder liefen durch `content_wache` im Feed-Profil: Größen, Textregeln, Kontrast 7:1, Rand 60 px.
- **Nicht im Bild:** keine Adresse, keine Transaktionskennung, kein Kurs, kein Link.
- **Deutsche Fassung:** Zahlen deutsch geschrieben, "gezählt" und "quelle" statt counted und source.

Damit die Bilder nach #ops-log kommen, kann der Bericht-Versand seit PR [#210](https://github.com/neoalphavault-png/kaspa-pulse/pull/210) Bilder an einzelne Teile hängen. Dieser Branch schickt nur nach #ops-log, nichts nach #moderator-only.

## Selbst-Merges seit dem 27.10.

| PR | Merge-Commit | Was live ist |
|---|---|---|
| #159 | cee9511 | Abschnitt Stand Parser im STP-Bericht |
| #165 | 9f602ab | Stand Parser nach dem Freeze im STP-Bericht |
| #167 | f5c4bad | Bericht STP-Zeitfenster plus 1 h |
| #182 | 0822a8d | Bericht STP-Zeitfenster, Historie bereinigt, neuer Kopf |
| #210 | c8f81a4 | `scripts/bericht_discord.py` hängt Bilder an |

Keine dieser PRs ändert eine Seite der Website, eine Abnahme auf einer echten URL entfällt deshalb.

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

- Die Bilder in #ops-log ansehen. Freigabe und Posten gehen von dir aus.
- PR #201 mergen, wenn er passt.

<!-- discord -->
KaspaDollar-Grafik, englisch. Stand 28 oct 2026 12.42 UTC, 182,012.19 KAS counted gegen 182,012 KAS laut Seite zur selben Minute, 0 Abgänge, 3.6 % von 5,000,000.
<!-- bild kaspadollar/ergebnis/kaspadollar-spenden-2026-10-28-en.png -->
<!-- teil -->
KaspaDollar-Grafik, deutsch, für die Telegram-Gruppe Kaspa German. Gleiche Zahlen, deutsch geschrieben.
<!-- bild kaspadollar/ergebnis/kaspadollar-spenden-2026-10-28-de.png -->
<!-- /discord -->
