# SEO-Prüfung je PR

Ben, 06.10.2026, SEO-Ausbau Block E. Gilt für jeden PR, der eine Seite von kaspapulse.com ändert.

## Was automatisch läuft

`.github/workflows/seo-pruefung.yml` läuft bei jedem PR, der eine dieser Dateien anfasst:
- `*.html`, `sitemap.xml`, `robots.txt`, `capture.js`
- `data/seiten-stand.json`, `scripts/seo_*.py`

Der Lauf wird rot, wenn einer dieser Punkte nicht stimmt:

| Prüfung | Skript |
|---|---|
| Titel höchstens 60 Zeichen, Beschreibung 140 bis 155, ohne Doppelpunkt und Gedankenstrich (nur geänderte Seiten) | `seo_pruefung.py` |
| FAQPage-Schema ist gültiges JSON, und jede Frage steht sichtbar auf der Seite | `seo_pruefung.py` |
| Kein Affiliate-Link (`rel="sponsored"`) außerhalb von `kaspa-wallets.html` | `seo_pruefung.py` |
| Hinweissätze passen zum Stand. Ohne Live-Link stehen „0 affiliate links on this page“ und „This page earns nothing from your choice“ da. Mit Live-Link steht „Some hardware links are affiliate links. They never change the order or what we write.“ mit Link auf how-we-fund-this.html | `seo_pruefung.py` |
| fo-verify-Tag in index.html unverändert | `seo_pruefung.py` |
| Kopf (canonical, OG, Twitter, dateModified), Stand-Zeile, Navigation und Sitemap auf Stand | `seo_seiten.py --pruefen` |

Die Tabelle „Seite | title alt → neu | description alt → neu | Länge“ steht in der Zusammenfassung des Laufs. Sie gehört in den PR-Text.

Schema-Befunde auf Seiten, deren FAQPage-Block sich im PR nicht ändert, sind Altbefunde. Sie erscheinen als Warnung und machen den Lauf nicht rot.

## Vor dem Push, lokal

```
python3 scripts/seo_seiten.py
python3 scripts/seo_pruefung.py --gegen origin/main --markdown
```

`seo_seiten.py` setzt das Datum einer Seite nur neu, wenn sich ihr sichtbarer Text geändert hat. Eine Änderung am Menü oder an Titel und Beschreibung allein zählt nicht.

## Was Handarbeit bleibt

- **Rich Results Test.** Nach dem Deploy jede geänderte Seite unter https://search.google.com/test/rich-results mit der Live-Adresse prüfen. Das Ergebnis kommt mit Datum in den PR oder in den Bericht.
  - Google zeigt FAQ-Ergebnisse seit August 2023 nur noch für Behörden- und Gesundheitsseiten. Gültig muss das Schema trotzdem sein.
- **Quelle und Datum für jede neue Zahl.** Das prüft kein Skript. Im PR-Text steht je neuer Zahl die Quelle, das Lesedatum und, wo es einen gibt, der Runner-Lauf, der sie gelesen hat.
- **Affiliate-Links kommen nur von Ben.** Jeder Link trägt das sichtbare Label „affiliate link“ und `rel="sponsored noopener"` und steht nur auf kaspa-wallets.html. Leere Plätze stehen in `<template>` und werden nicht gerendert.
