# scripts/ph/ph_entwurf.py, kurzer Bericht (6.11.2026)

Ben hat am 5.11. einen eigenen PR mit kurzem Bericht zu `scripts/ph/ph_entwurf.py` beauftragt.

**Stand des Codes:** Das Skript liegt schon unverändert auf `main`. Die letzte Änderung war `93b51ed` vom 23.10.2026 („ph entwurf: verlauf fuer lange fenster lesbar“). Am 5.11. war es auf allen Branches gleich, offene Änderungen gab es nirgends. Eine gleiche Kopie liegt in `pulsehawk-site/scripts/ph/`, laut Kopf des Skripts gilt: wer eine ändert, ändert beide. **Dieser PR bringt nur den Bericht, der Code bleibt unverändert.**

## Was das Skript tut

- **Entwurf:** Es baut aus einem unserer Stände einen Post-Entwurf für @pulsehawkio, mit Text und Grafik. Gepostet wird nie automatisch, Ben postet von Hand.
- **Quellen**, als Unterbefehle:
  - `bch`: BCH-Tempnet-Wochenstand (`--json`, `--koepfe`)
  - `zcash`: Zcash-CSV mit Blockabständen (`--csv`)
  - `zcash-mainnet`: Zcash-Mainnet-Stand (`--stand`, `--koepfe`)
- **Text:** ein gezählter Wert mit Vergleich zur Vorwoche oder zum computed Wert, eine Deutungszeile, das Fenster in UTC und als letzte Zeile „method on pulsehawk.io“.
- **Deutungszeile:** Sie wechselt Woche für Woche zwischen vier Arten: `vorwoche`, `luecke`, `alt_ziel` und `p90`. Eine Wertung wie „well above“ oder „well below“ gibt es höchstens einmal und nur, wenn die Zahl sie trägt, also bei Faktor 1,5 oder mehr gegen die ideale Kette.
- **Textregeln:** `regel_pruefen()` prüft jeden Text vor dem Senden und bricht bei einem Verstoß ab. Es prüft:
  - alles klein geschrieben
  - keine Gedankenstriche, Pfeile, Hashtags oder Emojis
  - Doppelpunkte nur in Uhrzeiten
  - keine Echtzeitwörter und keine Preise
  - „counted“ genau einmal und nur in der Zeile mit unserem gezählten Wert
  - „computed“ statt „expected“
  - das Fenster in UTC und „method on pulsehawk.io“
- **Grafik:** 1600 × 900 mit dem Fuß „Data from PulseHawk“. Je nach Parität der ISO-Woche wechselt sie zwischen Verteilung der Blockabstände und Verlauf. Dafür braucht es matplotlib und Pillow.
- **Versand:** Mit `--senden` gehen Text und Grafik an den Discord-Webhook aus der Umgebungsvariable `DISCORD_WEBHOOK_PH_DRAFTS`, ein GitHub Secret für #ph-entwuerfe. Die Webhook-Adresse wird nie gedruckt.

## Welche Workflows es nutzen

| Repo | Workflow | Aufruf |
|---|---|---|
| kaspa-pulse | `.github/workflows/ph-entwurf-bch.yml` | `--selbsttest`, dann `bch --json … --senden` nach jedem BCH-Wochenlauf |
| kaspa-pulse | `.github/workflows/ph-entwurf-zcash-mainnet.yml` | `--selbsttest`, dann `zcash-mainnet --stand … --senden` nach jedem neuen Zcash-Mainnet-Stand |
| pulsehawk-site | `.github/workflows/ph-entwurf-zcash.yml` | Testnet-CSV, Unterbefehl `zcash` |

`scripts/ph/ph_hand.py` ist ein eigenes Skript. Es meldet danach in #moderator-only, dass ein Entwurf von Hand zu posten ist, und nutzt `regel_pruefen` nicht.

## Selbsttest

```
python3 scripts/ph/ph_entwurf.py --selbsttest
```

Ausgabe am 6.11.2026 auf dem Stand von `main`:

```
selbsttest regeln: ok (14 verstoesse erkannt, gutes beispiel sauber, 4 deutungen sauber)
```

Der Selbsttest prüft 14 absichtlich falsche Texte, die alle erkannt werden müssen, und ein gutes Beispiel, das sauber durchgehen muss. Außerdem baut er für jede der vier Deutungsarten, mit und ohne Wertung, eine Zeile auf einer simulierten Kette und prüft sie gegen die Textregeln. Jeder Aufruf führt den Selbsttest vorher aus. Beide Workflows rufen ihn zusätzlich als eigenen Schritt auf.

## Offene Fragen an Ben

1. Falls du mit „`scripts/ph/ph_entwurf.py` als eigenen PR“ eine andere Fassung gemeint hast, etwa eine geänderte, die noch nicht auf `main` liegt: Welche ist es?
