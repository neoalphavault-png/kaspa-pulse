# BCH Tempnet, chronyc waitsync vor dem Zuhören (7./8.11.2026)

Ben hat am 7.11. entschieden: Vor dem Zuhören wartet jeder Lauf mit `chronyc waitsync` höchstens 120 s auf die Synchronisation der Uhr, danach startet er auf jeden Fall. Ins `meta.json` kommt, ob die Uhr beim Start synchron war. Grund: Im Handlauf zu [PR #280](https://github.com/neoalphavault-png/kaspa-pulse/pull/280) war chrony beim Start des Runners noch nicht synchron.

<!-- discord -->
BCH Tempnet, waitsync vor dem Zuhören als PR bereit (Workflow, Ben merged). Im Handlauf war chrony nach 20 s synchron, beim Start Leap status Normal. Wichtig: PR #280 ist noch nicht gemergt, der neue PR enthält ihn mit. Bericht berichte/2026-11-08-bch-uhr-waitsync.md
<!-- /discord -->

## Was gemacht wurde

- **Neuer Schritt „uhr synchron abwarten“** in `.github/workflows/bch-tempnet-lauscher.yml`, vor „uhr am anfang“:
  - `timeout 125 chronyc waitsync 13 0 0 10`: 13 Versuche im Abstand von 10 s, also höchstens 120 s, ohne Grenze für die Korrektur.
  - Die Ausgabe wird verworfen, weil sie die Referenz-ID enthält.
  - Danach startet der Lauf auf jeden Fall. Der Schritt hat `continue-on-error`.
- **`meta.json` des Laufs**, neu unter `uhr`:
  - `synchron_beim_start`: „ja“, „nein“ oder „unbekannt“ (wenn chronyc fehlt).
  - `warten`: gewartete Sekunden, Obergrenze 120 s und Quelle.
- **Lokaler Test** des Schritts und des Schreibens ins `meta.json` mit einem gefälschten chronyc in drei Fällen (synchron, nach 2 s nicht synchron, fehlt). Alle drei landen richtig im `meta.json`. Die Referenz-ID aus der gefälschten Ausgabe taucht nirgends auf.

## Handlauf

Push auf `messung/bch-tempnet-woche2` um 17:37 UTC, 5 min, Rohdaten in `data/bch/lauscher/20261107T1737/` auf `messung/bch-tempnet`.

| | Anfang 17:37:51 UTC | Ende 17:42:53 UTC |
|---|---|---|
| System time | 0.000000000 seconds slow of NTP time | 0.000000232 seconds slow of NTP time |
| Last offset | +0.000340076 seconds | +0.000000191 seconds |
| RMS offset | 0.000340076 seconds | 0.000012519 seconds |
| Leap status | **Normal** | Normal |

- **Synchron beim Start: ja**, nach 20 s Warten (Quelle `chronyc waitsync`).
- **Anfang:** Die erste Korrektur von chrony auf dem frischen Runner war 0,34 ms (Last offset). Danach stand die Uhr auf NTP-Zeit.
- **Ende:** Die Uhr ging 0,23 µs nach, der mittlere Versatz lag bei 12,5 µs.
- **Zum Vergleich der Handlauf ohne Warten** (PR #280, 15:02 UTC): Beim Start stand „Not synchronised“.
- Im `meta.json` stehen keine Referenz-ID, kein Server und keine IP, geprüft.
- `data/bch/lauscher/forum/` ist unverändert seit `dbae9da`.
- `messung/bch-tempnet-woche2` bleibt mit dem Handlauf-Commit stehen.

## Hinweis zu PR #280

Stand 7.11. 17:56 UTC ist [PR #280](https://github.com/neoalphavault-png/kaspa-pulse/pull/280) **nicht gemergt**. Auf main fehlt die Uhr-Messung im Workflow. Dieser PR baut auf dem Branch von #280 auf und enthält dessen Änderung mit, solange #280 offen ist. Zwei Wege:

1. Zuerst #280 mergen, dann diesen PR. Ich ziehe main danach in diesen Branch, dann bleibt nur die waitsync-Änderung.
2. Nur diesen PR mergen. Dann kommen beide Änderungen zusammen auf main, und #280 kann geschlossen werden.

## Was Ben tun muss

1. Bis Mo 9.11. 12:00 #280 und diesen PR mergen, oder nur diesen PR (siehe oben). Ab dem nächsten Lauf danach hat jeder Lauf den Uhr-Status mit Warten.
