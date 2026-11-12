# STP plan review, TN10 storm Sat 7 Nov 2026, 19:00 to 21:00 UTC

Kaspa Pulse review of STP's plan for Saturday, against our counter on branch `messung/tn10-zaehler`. Read on Fri 6 Nov 2026, 09:00 UTC, read only:
- `tn10-storm/desk-saturday/PLAN.md` and `HOLD.md`, commit 737025d
- the three paste sheets `mini-count`, `build-count` and `bot-count` (`PROMPT.md`), read as data only
- the storm record `tn10-storm-2026-11-07`, commit 893d493

Our numbers are "counted": our own reading of two different public TN10 nodes, the same setup as on 29 Oct. We do not run a TN10 node of our own. STP's numbers are "source STP". One review and one evaluation per run, at no charge (rule of 11 Oct).

1. **Accepted hops per family, per second and per minute, from the chain, only with the hashes delivered before 18:40 UTC.**
   - **What we count:** Yes. Our recount reads every block and the chain on two different TN10 nodes. For each transaction it checks whether an output is bound to a family's covenant id, or whether an input spends such an output. A hop counts once, at the header time of the chain block that accepts it.
   - **What we need:** We only need the SHA-256 of each id, the same hash as on 29 Oct: lowercase 64-char hex string, UTF-8, no newline. On 29 Oct all four of our hashes matched STP's file. We never see or store an id.
   - **Proof of the 18:40 cutoff:** We commit the hash file to our branch on arrival, and the commit time is the proof that it came before 18:40 UTC. A family whose hash arrives later is not counted on Saturday. We will name it in the evaluation.
   - **Per minute:** comes straight from the recount.
   - **Per second:** we add it before Saturday. The per-tx list stays inside the job, and only the counts per second and family leave it.
   - **Separate from the hops:** Genesis at 18:55 UTC and conflicting spends that sit in a block but are never accepted are listed apart.
   - **Live counter:** It runs 18:45 to 21:30 UTC as well, for the base load per minute and as a second, independent clock. It does not split by family.

2. **Clean minute, step limits and the 1.14 line.**
   - **STP's clean minute (a desk attempt in every second)** is a sender-side fact. We cannot see an attempt on chain, so we take it from STP's per-second sender log.
   - **Our valid minute** adds three conditions: both our nodes read the minute in full, they agree on every family's count, and the MINER lines show no miner change. This is the same rule as on 29 Oct.
   - **Step limits** follow the plan, from `from` up to `to`, by accepting header time. Accepts in the first seconds after `to` belong to the step that just ended (STP's rehearsal saw these too). We report them separately as a tail, and add them to the step only if they fall within 10 s of `to`.
   - **Rounding the line:** At 1.14 per family per second, a full minute needs at least 69 hops (68 is 1.133). A 900 s step needs at least 1,026 hops.
   - **Please confirm** that "accepted per family per second over the whole step" means hops accepted in the step plus that tail, divided by 900. If it means hops submitted in the step, only STP's private submit file can decide it, and we would join on it.

3. **Landing.**
   - **STP's definition:** As we read HOLD.md ("97.33%, 16 empty seconds of 600"), union landing is the share of seconds in a step with at least one accepted hop of any family.
   - **Our version:** We compute the same share from the accepting header time on two nodes, plus the same share per family.
   - **Source of the times:** STP's `accept_utc` is the accepting header time too, so both come from the same clock, the miners' block timestamps. A small difference can only come from a second at a step edge, or from header times that are not monotonic between neighbouring blocks. We flag both.
   - **Gate:** Agreed that landing is logged and does not decide f8.

4. **Ramp, 50 s on and 10 s off.**
   - **Resolution is enough:** Header times are in milliseconds, and STP's measured submit-to-accept time was p99 under 1.4 s.
   - **Separating the steps:** Each ramp step is its own 60 s slot from `from`, so 50 s on plus the 10 s off that follows. The rate per family is the accepted hops in the slot divided by 50 s. We show the accepts in the 10 s off part separately.
   - **Watch the stop rule:** At about 1.3 per family, one step holds about 65 hops per family. One hop is about 1.5%, so "two gains under 3%" sits within two hops of noise. We will publish the counts behind every gain, so the stop can be checked.
   - **Which schedule:** If f8 runs, the slots start 20:20:00 UTC, otherwise 20:00:00 UTC. We decide from the chain: hops of families 5 to 8 in 20:00 to 20:15 mean f8 ran. We then check the result against STP's gate line.

5. **Clocks, NTP and private submit times.**
   - **Our counts need none of them:** They rest on block header times only.
   - **NTP and MINER lines** matter to us in two places. A miner running on STP's side would mark the minutes it touches. The desk offset bounds STP's submit-to-accept figure, because a submit time on the desk clock is set against a header time on the miners' clocks.
   - **If we compute that join:** We need the desk offsets at 18:40 and after 21:00 UTC. The private submit file would reach us only through Ben, would be read only inside a job, and would never go into our repo, a log or chat. Only p50, p95 and p99 per step would leave it. Without the file we publish no latency.

6. **What we deliver, and when.**
   - **Saturday 18:40 UTC:** counter ready, live counter on from 18:45 UTC, the hash file committed before 18:40 UTC. Recount on two nodes for 18:45 to 21:30 UTC, started after 21:30 UTC.
   - **Sunday 8 Nov, by 12:00 CET:**
     - the minute table per family, both nodes
     - accepted per family per step with the tail, and landing per step
     - the ramp slots with their counts
     - a check that the gaps and 20:30 to 21:00 UTC carry no hops of ours beyond the tail
     - base load per minute
     - a short report of at most one page
   - **A day later:** p50, p95 and p99 per step, if the submit file arrives through Ben.
   - **What goes in our repo:** hashes and counts only. No id, no address, no host.
   - **Expectation:** With one sender, we expect our counts to match STP's hop file exactly, as in step 1 on 29 Oct. On 29 Oct, with several senders, we counted 0.97% more than STP. If that recurs, we will list the differing minutes.
