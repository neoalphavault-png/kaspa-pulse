# Zcash Testnet, lief die Kette über 4.548.314 hinaus? (28.10.2026)

Prüfauftrag Ben, Mi 28.10.2026, Frist 14:00 Berlin. Anlass: dr. alex (@soligxbt) meldet öffentlich, sein zebrad 7.0.0+git.e8db87e blieb auf dem Testnet bei 4.548.314 stehen.

## Ergebnis

**Ja, die Kette lief weiter.** Abruf 28.10.2026 08:52 UTC, Spitze 4.550.380 (Blockzeit 08:51:44 UTC), also 2.066 Blöcke nach 4.548.314. An dieser Stelle gab es keinen Abzweig und keinen Reorg.

## Methode

- Eigener Header-Client `scripts/zcash/zcash_koepfe.py --netz testnet`: Start beim Zebra-Checkpoint 4.518.360, Verkettung und Arbeitsnachweis aus nBits geprüft. Im Bereich lag kein weiterer Checkpoint.
- Hauptpeer und Zielhöhe aus Peers, die selbst synchron sind. Kein Peer-Fehler, kein verworfener Zweig.
- Gegenprobe an der Spitze: 2 Peers /Zebra:7.0.0/, je 500 von 500 Hashes gleich.
- Abzweig-Probe an der Stelle (`scripts/zcash/testnet_stall.py`): 3 weitere Peers liefern je die Köpfe 4.548.265 bis 4.548.904. Alle 3 stimmen in 640 von 640 Hashes mit unserer Kette überein (2 × /Zebra:7.0.0/, 1 × /Zakura:1.7.0/).
- Peer-Software im Abruf: /Zebra:7.0.0/, /Zakura:1.7.0-rc1/, /Zakura:1.7.0-modified/. Keine Adressen in Daten oder Log.

## Die Höhe und die 21 Blöcke danach

| Höhe | Hash | Zeit UTC | Abstand |
|---:|---|---|---:|
| 4,548,314 | `00001a5f4d7310fb7a38f30076be85d07201b771aa42d4ee7b56931e87fe4dbd` | 2026-10-27 18:29:29 | 17 s |
| 4,548,315 | `000013f21766a12db79a3a5ac42f549d160fe1db781d2bdb712e428d457761c9` | 2026-10-27 18:30:23 | 54 s |
| 4,548,316 | `00000a172c53d857b307c30116bc9279e0549a604543e76e3993342d7e485dbb` | 2026-10-27 18:30:55 | 32 s |
| 4,548,317 | `00000d10d4ca77dfc0fedcaf3f6086545e0532f81f4198e8e4fab248951d9de7` | 2026-10-27 18:31:20 | 25 s |
| 4,548,318 | `000000a7a7162304b3bae709f7cec2a6f7d2ec206d2909876faf5a7546a7c404` | 2026-10-27 18:32:04 | 44 s |
| 4,548,319 | `000020faffb1db1eaaa2f31d48d8c6dca5bc8ad262448aeb485bbf3e76871fb8` | 2026-10-27 18:32:17 | 13 s |
| 4,548,320 | `0000184e912a81aaab104df3ced029a68cce22cb9c1fa59b213800492d36fca5` | 2026-10-27 18:32:45 | 28 s |
| 4,548,321 | `000014a7264064b78c9c4d7d8ff781f6aab9a201f1eaaced4c6c8f0abbdf38ec` | 2026-10-27 18:33:23 | 38 s |
| 4,548,322 | `00000b85a2f22b4076fc2f9253c799446f547bd28a4dd79dbe487f6df8ee2271` | 2026-10-27 18:33:52 | 29 s |
| 4,548,323 | `00000591c998c64c3fd7319ee230fab6962eb3b9f5a215a58ba0f2c4630e0099` | 2026-10-27 18:34:09 | 17 s |
| 4,548,324 | `0000249ce532708b05a973252f6e86fdce81417305059a084696f30f50a27548` | 2026-10-27 18:34:21 | 12 s |
| 4,548,325 | `0000055dcee655b44f2bae4d734d1b2f992fc5e578358d7f041f839edd4ebcd7` | 2026-10-27 18:34:43 | 22 s |
| 4,548,326 | `00000becdedb28ffb404b64a9c0643c9f14aefe0e00f3b8afb0f6a4c653cbdbb` | 2026-10-27 18:35:08 | 25 s |
| 4,548,327 | `00001cc344f4d35a55cddd0450f7db620e9c6a3db7e7c5c53bf978f4ad838674` | 2026-10-27 18:35:25 | 17 s |
| 4,548,328 | `0000023ac552bceb026fdf8d1f0970540d6efaf032e0560b67fa3761ac351632` | 2026-10-27 18:35:33 | 8 s |
| 4,548,329 | `00000bc89b1d5cf748262e32b400593206b200225c73ba7965a0d1bfa094ce00` | 2026-10-27 18:35:45 | 12 s |
| 4,548,330 | `00001b20d49858d866a85790e63f8c3cd5f52f8b612ff3a0154f9ccc8d6c5ac6` | 2026-10-27 18:36:25 | 40 s |
| 4,548,331 | `0000116f22c168126f49bc1746a37e14519762cd8cef3f19a33b3d1bb761f39f` | 2026-10-27 18:36:40 | 15 s |
| 4,548,332 | `0000013e386c418be062920abbd4ad7d43414b77074c2817a485641c559a105f` | 2026-10-27 18:37:01 | 21 s |
| 4,548,333 | `000026e7c488b46638020c36cd28d66741ffd31227fc40125f622b4618915525` | 2026-10-27 18:37:05 | 4 s |
| 4,548,334 | `000016a81e426a596a4c6fa8b168fb081536f19605f7a0c7d582d179b28a531c` | 2026-10-27 18:37:27 | 22 s |
| 4,548,335 | `000027fbe4886b9403f5e3610deec5384301503dd78ef961a93586c0483d290b` | 2026-10-27 18:38:00 | 33 s |

## Fenster ±500 Blöcke

Blöcke 4.547.815 bis 4.548.814, 1.001 Abstände (counted):
- Median 20 s, Mittel 25,07 s, bei 25 s Ziel
- längste Lücke 181 s vor Block 4.548.253 (27.10.2026 18:08:02 UTC), 61 Blöcke vor 4.548.314

Nach 4.548.314 kein auffälliger Abstand: Die 21 Blöcke danach liegen zwischen 4 und 54 s.

## Entwurf öffentliche Antwort (englisch, Ben postet)

```
we counted the zcash testnet chain past 4,548,314 with our own header client. block 4,548,314 carries 27 oct 2026 18:29:29 utc and 4,548,315 followed 54 s later, and by 28 oct 08:51 utc the chain stood at 4,550,380, which is 2,066 blocks further. three other peers returned the same 640 headers around that height, so we counted no fork or reorg there.
```

Regelprüfung: klein, keine Gedankenstriche, Doppelpunkte nur in der Uhrzeit, keine Pfeile, Zeiten in UTC, keine Empfehlung zur Node-Software.

## Dateien und PR

- Daten auf diesem Branch: `data/zcash-testnet-stall/stall.json`, `stall.md`, `koepfe-meta.json`
- Workflow `.github/workflows/zcash-testnet-stall.yml` und Skript `scripts/zcash/testnet_stall.py`, einmalig, laufen nur auf `zcash/testnet-stall`

## Discord

- `#moderator-only` (DISCORD_WEBHOOK_OPS): Handlung für Ben, Antwort prüfen und posten
- `#ops-log`: Für #ops-log gibt es im Repo kein Secret, nur DISCORD_WEBHOOK_OPS (#moderator-only). Der Workflow versucht DISCORD_WEBHOOK_OPS_LOG und meldet „kein webhook“, wenn es fehlt.

## Offene Fragen an Ben

1. Soll es ein eigenes Secret für #ops-log geben (Vorschlag: DISCORD_WEBHOOK_OPS_LOG)? Bis dahin landet nur die Handlung in #moderator-only.

## Was Ben tun muss

- Antwort an @soligxbt prüfen und posten. Ich poste nichts.
- Den PR musst du nicht mergen; er enthält einen Workflow. Er kann als Beleg offen bleiben oder geschlossen werden.
