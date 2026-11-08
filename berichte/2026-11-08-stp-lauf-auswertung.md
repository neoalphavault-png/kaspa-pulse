# TN10 storm Sat 7 Nov 2026, file 1, what we counted

## Addendum, 8 Nov 2026

STP confirmed on 8 Nov that the window did not run. Our counter counted an empty window correctly as empty.

Kaspa Pulse count of the Saturday window on Testnet-10, 19:00 to 21:00 UTC, one to eight families. The rules are the ones in STP's `plan/COUNT.md` and in our confirmation `berichte/2026-11-07-stp-count-abgleich.md`. Numbers from our two nodes are marked counted. We publish hashes and counts only, no ids.

## Accepted hops

**We counted 0 accepted hops for each of the eight families, in every step from 19:00 to 21:00 UTC.** Our recount finds no transaction with an output bound to any of the eight family ids, and none that spends such an output. The same holds on both nodes.

This is not a statement that STP sent nothing. It says that none of the covenant ids we read on chain in the window hashes to one of the eight published hashes. Until that is settled, file 1 has no rate per family, no line check and no landing per family. We do not guess a mapping.

## The chain was read in full

- **Recount:** [run 42421412329](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42421412329) on our branch `messung/tn10-zaehler`, commit 8ee0e6d4. Eight pieces from 18:45 to 21:30 UTC, blocks and chain, each piece on two different public nodes.
- **Coverage:** all 165 minutes are complete on both nodes, and the nodes agree in every minute. The pruning point of both nodes was 6 Nov 15:18 UTC, so the whole window was readable.
- **Traffic in the window:** 98,160 blocks and 550,444 accepted transactions without coinbase (counted, both nodes equal).
- **Families loaded:** both nodes held all eight hashes during the read. Per family and step the tables in `messung/tn10/ergebnisse/lauf-42421412329/` show 0 accepted and 0 in tail, and the minute table shows 0 never accepted.

## The hashes were on time

| File | STP commit | Commit time (UTC) | Deadline (UTC) | We read it (UTC) |
|---|---|---|---|---|
| `hashes/SATURDAY.md`, 8 families | 0e99ff1a | 7 Nov 18:37:46 | 18:40 | 18:45:42 |
| `hashes/LOAD.md`, 32 families | a34f80d0 | 7 Nov 21:05:02 | 21:10 | 21:13:25 |

- **Copied unchanged:** we took the hashes as published into `messung/tn10/nach/covenant.sha256` (f1 to f8) and `messung/tn10/nach/covenant-load32.sha256` (g1 to g32).
- **No conflict between files:** `hashes/README.md` carries no hashes, and `SATURDAY.md` did not change after 18:37:46 UTC.
- **Noted for file 2:** families 1 to 4 in `LOAD.md` carry the same four hashes as families 1 to 4 in `SATURDAY.md`. Families 5 to 32 in `LOAD.md` do not appear in `SATURDAY.md`.

## Check of the id form

Because no hash matched, we counted every covenant output in two short pieces, whatever its id, and tested other forms of the id against the published hashes. Hashes and ids stay on the runner. Only counts leave it.

| Piece (UTC) | Run | Tx with a covenant output | Distinct covenant ids | Ids with 100 tx or more | Ids with 10 tx or more | Ids with 1 tx | Tx of the five busiest ids | Matches with the published hashes |
|---|---|---:|---:|---:|---:|---:|---|---:|
| 20:00 to 20:10 | [42426731727](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42426731727) | 2,055 | 866 | 5 | 17 | 661 | 624, 624, 309, 246, 228 | 0 |
| 21:30 to 21:40 | [42426731652](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42426731652) | 1,694 | 754 | 5 | 12 | 551 | 384, 384, 306, 231, 186 | 0 |

- **Forms tested:** the id as lowercase hex (our rule and STP's), as read, as uppercase, as raw bytes, byte order reversed as hex and byte order reversed as raw bytes. None matched in either piece.
- **Id format on chain:** every covenant id we read is a string of 64 characters.
- **Same rule as on 29 Oct:** on 29 Oct we hashed the ids Ben passed on with this rule, and all four hashes were equal to STP's `covenant-id-sha256.csv`.
- **Both nodes:** every number in this table is the same on both nodes.

We cannot tell from the chain which of these ids, if any, belong to STP.

## Our minute counter

Our minute counter ran on two nodes from 18:45 to 22:20 UTC without a gap, 215 of 215 minutes full. It counted 128,686 blocks and 716,525 accepted transactions without coinbase, between 53.4 and 59.07 per second in every minute (counted). The nodes agreed on blocks in every minute. On accepted transactions they differed in 1 of 212 minutes in which both were full.

## What we need from STP

1. The exact input of each family hash. Which field, which bytes, which text form.
2. One worked example on an id that is already public, for instance one family of the 29 Oct run, so we can check our side against it.
3. Attempts per family from the desk sender log, as counts, for the 19:00 to 21:00 UTC window.

With that, we rerun the recount on the same pieces. The window stays readable until the nodes prune it.

## Files

On `messung/tn10-zaehler`, counts only.

- `messung/tn10/ergebnisse/lauf-42421412329/` holds the recount of file 1, per second, per step and per minute.
- `messung/tn10/ergebnisse/lauf-42426731727/covenant-pruefung.json` and `messung/tn10/ergebnisse/load32-lauf-42426731652/covenant-pruefung.json` hold the check of the id form.
- `messung/tn10/notizen-2026-11-07.txt` keeps the points STP raised on 7 Nov about the clock and the line.
