# Quellen der Testdaten

| Datei | Herkunft | Lizenz |
|---|---|---|
| `kcc-0020-conformance.json` | kaspanet/kccs, `kcc-0020/vectors/conformance.json`, Commit 1ed87ae (21.10.2026, KCC-20 Final) | CC0 1.0 |
| `kcc-0023-conformance.json` | kaspanet/kccs, `kcc-0023/vectors/conformance.json`, Commit 1ed87ae (KCC-23 Draft) | CC0 1.0 |
| `public-mint-artifact.json` | argent-lang/kcc20-reference, `fixtures/public-mint/artifact.json`, Commit 27f8403 (21.10.2026) | ISC |

Unverändert übernommen. Der Selbsttest von `scripts/kcc20_zaehlung.py` prüft die eigene Kodierung gegen die Konformitätsvektoren. Das Artefakt liefert das öffentliche Referenz-Template des KCC-20-Programms, mit dem auch frisch geminte Outputs bewiesen werden können.

`scripts/kcc20_namen.py` prüft gegen `kcc-0023-conformance.json` die KIP-20-Covenant-ID (Genesis-Beweis) und die Regeln für den Metadaten-Payload.

`kcc20info-token-ids.txt` sind die 97 `token_id` aus `https://kcc20.info/v1/tokens`, abgerufen am 23.10.2026 um 14:32 UTC, nur als "source kcc20.info". Die Diagnose in `scripts/kcc20_namen.py` markiert damit, welche Covenant-IDs ohne bewiesenen KCC-20-Zustand dort gefuehrt werden.
