# STP count plan, our alignment, TN10 storm Sat 7 Nov 2026

Kaspa Pulse confirmation of STP's `plan/COUNT.md` in `tn10-storm-2026-11-07`. Read on Sat 7 Nov 2026 at 16:25 UTC, last change to the file in commit be786fc at 12:25:42 UTC (13:25:42 CET). Only that file was read. STP accepted our plan review (`berichte/2026-11-07-stp-plan-durchsicht.md`) on 7 Nov around 16:30 CET.

## Two rules changed from our review, now in our counter

1. **No tail in the rate.**
   - **Rule:** The rate of a step counts only the hops whose time is inside the step, from its opening up to its close, divided by the length of the step.
   - **The tail:** Hops after the close, even within 10 s, are not in the rate. We list them apart as the tail.
   - **The gate's 3 s:** The gate reads 3 s after the close, and that wait is not part of the length.
   - **Ramp:** A ramp step is its 50 s on. The 10 s off that follow are its tail.
2. **The line is the whole step.**
   - **Exact counts:** 1.14 × 900 s gives 1,026 accepted hops per family. 1.14 × 2,700 s for the 32-family load gives 3,078 per family. Both are exact, and we compute them with exact decimals.
   - **No minute verdict:** No minute is marked as passing or failing, and there is no 69-hop minute line. The minute table stays as data.
   - **Late landings:** The 15 minutes after 22:00 UTC count as late landings, listed apart from the 32-family rate.

These rules are in `scripts/tn10_sekunden.py` and in the two plan files on our branch `messung/tn10-zaehler`, commit 810cbd77. The self-test passes (14 of 14). It includes a step with 1,026 hops on one family and 1,025 on another, plus a tail that does not enter the rate.

## Unchanged

- **A valid minute:** both our nodes read it in full and agree on every family, and the miner lines show no change.
- **Attempts** come from the desk sender log only. On our side they are counts, never ids.
- **Landing:** the share of seconds with a hop, as in HOLD.md, also per family. It decides nothing.
- **Ramp:** we show the hop counts behind every gain.
- **Kept apart:** genesis and conflicting spends (already spent, orphan) are listed apart from hops.
- **Hash deadlines:** file 1 before 18:40 UTC, file 2 before 21:10 UTC.
- **What we publish:** hashes and counts only, no ids.
- **Seen time:** Until STP says otherwise, we take it as the header time of the accepting block, the same as `accept_utc`.

## Delivery

- **File 1,** Saturday 19:00 to 21:00 UTC: on our branch by Sun 8 Nov 10:45 CET, delivered by 12:00 CET (11:00 UTC).
- **File 2,** the 32-family load: on our branch by Mon 9 Nov 16:45 CET, delivered by 18:00 UTC.

## One open point

`COUNT.md` names the hash files `hashes/SATURDAY.md` and `hashes/LOAD.md`. Our read access for the run covers `hashes/README.md` only, so we take the hashes from there unless Ben clears the two named files.
