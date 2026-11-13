# ph_entwurf.py aus pulsehawk-site übernommen (13.11.2026)

Ben am 13.11.: `scripts/ph/ph_entwurf.py` ist in pulsehawk-site mit #92 berichtigt, also Dauern in min und s und Vergleich nur mit benanntem Fenster. Die Kopie in kaspa-pulse war noch die alte. Ohne die neue Fassung trügen die BCH- und Zcash-Entwürfe am 18.11. wieder „4 min“ und „a week earlier“.

<!-- discord -->
ph_entwurf.py in kaspa-pulse ist jetzt dieselbe Datei wie in pulsehawk-site nach #92. Beide Entwürfe nennen „4 min 9 s“ und vergleichen mit einem benannten Fenster samt Zahl der Abstände. Der Selbsttest erkennt 17 Verstöße. Bereit für die Läufe am 18.11. Bericht berichte/2026-11-13-ph-entwurf-uebernahme.md
<!-- /discord -->

## Was gemacht ist

- **Datei:** `scripts/ph/ph_entwurf.py` aus pulsehawk-site `main` (Commit `bd85ec7`, PR #92) unverändert nach kaspa-pulse übernommen, auf dem eigenen Branch `ph/entwurf-dauer-fenster`.
- **sha256:**

  | Datei | sha256 |
  |---|---|
  | pulsehawk-site, `scripts/ph/ph_entwurf.py` (bd85ec7) | `3b2638dcd175c29468095a90194a2511e100489e6d4dc36f04807e8d76eab919` |
  | kaspa-pulse, `scripts/ph/ph_entwurf.py` nach dieser Übernahme | `3b2638dcd175c29468095a90194a2511e100489e6d4dc36f04807e8d76eab919` |
  | kaspa-pulse vorher (alte Fassung) | `c97a0026d4e2c1bcfc170949adaf633e2bbd32a5308bd65ca4f1a9331d4722fb` |

  Die beiden ersten sind gleich.
- **Selbsttest:** `python3 scripts/ph/ph_entwurf.py --selbsttest` ergibt „ok (17 verstoesse erkannt, gutes beispiel sauber, 4 deutungen sauber)“. Neu erkannt werden „4 min“ ohne Sekunden, „a week earlier“ und „last week“.
- **Probe mit echten Ständen**, wie in den Workflows aufgerufen, ohne `--senden`:
  - **Zcash** (`stand-2026-11-11.json`):
    - „the longest gap was 4 min 9 s“
    - „against 25.0 s over 250 intervals in our window 6 nov 2026, 02:34 to 6 nov 2026, 05:13 utc“
  - **BCH** (`tempnet-2026-11-11.json`): „against 40.0 s over 28,051 intervals in our window 15 oct 2026, 12:56 to 4 nov 2026, 09:58 utc“
  - Beide bestehen die Regelprüfung.
- **Workflows:** `ph-entwurf-bch.yml` und `ph-entwurf-zcash-mainnet.yml` rufen die Datei aus `main` auf. Mit dem Merge gilt die neue Fassung für die Läufe am 18.11.

## PR-Nummern

- dieser PR
- pulsehawk-site #92, die Vorlage

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

Nichts. Der PR ändert nur ein Skript, ich merge ihn nach den Regeln selbst.
