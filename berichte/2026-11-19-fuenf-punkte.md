# Bericht zum Auftrag vom 19.11.2026, fünf Punkte

Auftrag von Ben vom Do 19.11.2026. Die Punkte kommen nach Vorrang, jeder Punkt in einem eigenen PR. Dieser Bericht wächst mit jedem PR.

## 1. Wochenpost, die Reward-Zeile nur als Schätzung
- **Vorher:** `scripts/weekly_numbers.py`, `cut_phrase`, schrieb für Discord und Telegram „cut to 1.835 on december 5, 00.15 utc“. Bis 8 Tage vor der Stufe stand statt des Datums der Wochentag.
- **Jetzt:** „cut to 1.835 around 5 dec, estimate“. Ohne Uhrzeit und ohne Wochentag, in jeder Entfernung zur Stufe dieselbe Form. Die Form kommt aus `stufe_schaetzung.kurz`, wie im Cheat Sheet und auf /whales.
- **Wache vor dem Post:** `main()` ruft nach `assert_punctuation` jetzt `stufe_pruefen(msg, msg_tg)` auf. Nennt der fertige Post für Discord oder Telegram die nächste Stufe ohne „around“ und „estimate“ oder mit Uhrzeit, hält der Lauf an, bevor etwas gesendet wird.
- **`stufe_schaetzung.py`:** Die Wache erkennt jetzt auch „00.15 utc“ mit Punkt, so schrieb der Wochenpost die Uhrzeit. Ein Betrag wie „1.94 KAS“ zählt nicht als Uhrzeit.
- **Selbsttest `weekly_numbers.py`:**
  - Der Fall vom 16.11.2026 ergibt „cut to 1.835 around 5 dec, estimate“.
  - `stufe_schaetzung.verstoesse` findet in der Reward-Zeile nichts.
  - Der alte Satz ist rot und hält den Post an.
  - Der nahe und der ferne Fall (3.8. und 6.7.) haben dieselbe Form.
  - Der Goldpost vom 3.8. ist bis auf die Reward-Zeile zeichengleich geblieben.
- **Prüfung:**
  - Selbsttests mit 0 Fehlern: weekly_numbers, stufe_schaetzung, preis_wache, x_post und karussell.
  - `stufe_schaetzung` über 45 Seiten und `preis_wache` über 55 Seiten melden je 0 Verstöße.
  - Secret-Scan ohne Fund.
- **Kopf:** Die Änderung steht in `fcbfff57`. Dieser Abschnitt liegt als eigener Commit darauf.
