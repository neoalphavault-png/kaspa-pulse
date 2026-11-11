# TN10 storm Tue 10 Nov 2026, file 1, what we counted

Kaspa Pulse count of the window on Testnet-10 from 19:00 to 21:00 UTC, one to eight families and the ramp. The rules are those in STP's `plan/COUNT.md` and in our confirmation `berichte/2026-11-08-stp-termin-10-11.md`. Every number below is counted on two of our nodes, unless it is marked source STP. We publish hashes and counts only, no ids.

## Accepted hops

Every family landed on chain, and every family accepted more hops than the line in every step it ran. No family came within 10 hops of the line. The plan ran with the eight-family step (`mit_f8`).

| Step (UTC) | Families | Accepted in the step, per family | Per second, per family | All families per second | Line per family | Tail |
|---|---:|---|---|---:|---:|---:|
| f1, 19:00 to 19:15 | 1 | 1,221 | 1.357 | 1.357 | 1,026 | 1 |
| f2, 19:20 to 19:35 | 2 | 1,192 to 1,213 | 1.324 to 1.348 | 2.672 | 1,026 | 2 |
| f4, 19:40 to 19:55 | 4 | 1,161 to 1,218 | 1.290 to 1.353 | 5.272 | 1,026 | 4 |
| f8, 20:00 to 20:15 | 8 | 1,129 to 1,221 | 1.254 to 1.357 | 10.367 | 1,026 | 8 |

- **Rate:** only the hops whose accepting block falls inside the step, divided by its 900 s. The tail is the hops in the 10 s after the close, one per family in every step, listed apart and not in the rate.
- **Line:** 1.14 × 900 s gives 1,026 accepted hops per family for the whole step. No minute is marked as passing or failing.
- **Near the line:** no family in any step is within 10 hops of 1,026, so no first or last second is shown apart.
- **Clock:** the header time of the accepting block.
- **Valid minutes:** all 121 minutes from 19:00 to 21:00 UTC are valid. Both nodes read each of them in full, agree on every family, and the miner lines show no change (4 miners in every minute).

## Per family

| Step | f1 | f2 | f3 | f4 | f5 | f6 | f7 | f8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 1,221 | | | | | | | |
| f2 | 1,213 | 1,192 | | | | | | |
| f4 | 1,218 | 1,194 | 1,161 | 1,172 | | | | |
| f8 | 1,221 | 1,186 | 1,173 | 1,180 | 1,164 | 1,147 | 1,130 | 1,129 |

Accepted hops in the step. Both nodes give the same number in every cell.

## Landing

Share of the seconds in a step with at least one accepted hop. It decides nothing.

| Step | Any family | Per family |
|---|---:|---|
| f1 | 95.00 % | f1 95.00 % |
| f2 | 95.44 % | f1 94.56 %, f2 94.78 % |
| f4 | 95.22 % | f1 94.44 %, f2 93.33 %, f3 92.22 %, f4 93.33 % |
| f8 | 96.00 % | f1 94.78 %, f2 94.00 %, f3 93.33 %, f4 94.33 %, f5 93.11 %, f6 93.11 %, f7 92.22 %, f8 92.33 % |

## Ramp

Four families, steps of 50 s on and 10 s off from 20:20 UTC. Accepted hops came in the first three steps only.

| Step (UTC) | f1 | f2 | f3 | f4 | All, per second | Tail |
|---|---:|---:|---:|---:|---:|---:|
| r1, 20:20:00 to 20:20:50 | 67 | 66 | 64 | 64 | 5.22 | 4 |
| r2, 20:21:00 to 20:21:50 | 66 | 64 | 64 | 66 | 5.20 | 4 |
| r3, 20:22:00 to 20:22:50 | 70 | 68 | 65 | 64 | 5.34 | 0 |
| r4 to r10, 20:23:00 to 20:29:50 | 0 | 0 | 0 | 0 | 0 | 0 |

From r1 to r2 the four families lost 1 hop together, from r2 to r3 they gained 7. Why the ramp ends after r3 is not something our count can tell. In the quiet half hour from 20:30 to 21:00 UTC no hop of any family was accepted.

## Kept apart

- **Genesis:** one transaction per family, accepted between 18:54:57 and 18:55:06 UTC, before T0.
- **Gaps:** the only hops in the gaps after f1, f2, f4 and f8 are the tails above, all within the first 10 s.
- **Never accepted:** 0. Every family transaction we saw in a block was accepted.
- **Attempts:** come only from the desk sender log. We have no counts of it for this run, so we show none.

## Totals

18,520 accepted family transactions from 18:45 to 21:30 UTC, the same on both nodes in every second. Per family, genesis, steps, tails and ramp included, that is f1 5,083, f2 3,776, f3 2,532, f4 2,551, f5 1,166, f6 1,149, f7 1,132 and f8 1,131.

## The hashes

| File | Hash commit (UTC) | On origin line (UTC) | Deadline (UTC) | We read it (UTC) |
|---|---|---|---|---|
| `hashes/EIGHT.md`, f1 to f8 | f746514, 10 Nov 18:25:08 | 8106395, 18:25:12, names 18:25:08 and f746514 | 18:40 | 18:46:23 |
| `hashes/THIRTYTWO.md`, g1 to g32 | 503423e, 20:32:17 | ec8e7ea, 20:32:20, names 20:32:17 and 503423e | 21:10 | 21:13:29 |

- **Proved:** both files carry their On origin line in a commit before the deadline.
- **Armed:** there is no armed line in `hashes/`, the only folder we read.
- **Copied unchanged** into `messung/tn10/nach/covenant.sha256` and `messung/tn10/nach/covenant-load32.sha256`. None of the 32 load hashes is one of the eight.

## How we counted

- **Recount:** [run 42916097131](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/42916097131) on our branch `messung/tn10-zaehler`. Eight pieces from 18:45 to 21:30 UTC, blocks and chain, each piece on two different public nodes.
- **Two pieces read twice:** in pieces 6 (20:25 to 20:45 UTC) and 7 (20:45 to 21:05 UTC) the first node stopped with an error and no message, while the second read the piece in full. Both pieces were read again in the same run and came back complete on both nodes. The run keeps the files of both attempts, so our evaluation takes the newest file of each piece (commit f9afc4ed on our branch). Every count in this report comes from that evaluation.
- **Minute counter:** our counter ran on two nodes from 18:45 to 22:20 UTC, 215 of 215 minutes full, nodes equal in all 206 minutes both read. All transactions accepted per second rise from about 54 before T0 to about 64 in the f8 step and fall back to about 54 in the quiet half hour.
- **Files:** `messung/tn10/ergebnisse/lauf-42916097131/` holds the counts per second, per step and per minute. The minute table is data only.
