Ahead of the mainnet go/no-go on 20 October, here are our final independent counts for NU7 on the public testnet, covering blocks 4,465,026 to 4,514,228 (49,203 blocks) with a cut-off of 2026-10-18 06:00:00 UTC. These are numbers only, without assessment.

We measured each block interval as the timestamp of a block minus that of its parent, starting at 4,465,027, and compare them with exponential intervals at a 25 s mean.

| | measured | expected |
| --- | --- | --- |
| mean | 23.68 s | 25 s |
| median | 17.0 s | 17.3 s |
| p90 / p99 | 52.0 s / 109.0 s | 57.6 s / 115.1 s |
| share > 75 s | 3.59 % | 4.98 % |
| share > 150 s | 0.203 % | 0.248 % |
| longest gap | 451 s at 4,495,487 | ≈ 284 s (expected maximum) |

In post 24 we quoted a dashboard median of 19.5 s over 300 blocks. Over 49,203 blocks the median is 17.0 s against 17.3 s expected.

We found 6 hashrate jumps of 2x or more. After them the difficulty came within ±15 % of the new level after a median of 960 blocks (159.7 min), and the longest catch-up took 1,839 blocks. No timestamps went backwards, and none were more than 10 min ahead of the median of the 11 following blocks. Every timestamp was above the median of the 11 previous blocks. Since activation there was 1 minimum-difficulty block.

**Listener, as promised in post 24**

One listener at one location ran on Saturday, not our own node. The actual window was 17 Oct 2026, 14:51 to 20:21 UTC (330 min). It kept connections to Zebra and Zakura nodes and logged every block announcement with its arrival time, and these arrival times include the path from the node to the listener. Of 776 chain blocks with timestamps in the window it saw 775 announced. Five of the 780 announced blocks did not end up in the chain, each at depth 1. For the 730 blocks announced by both, the first Zakura announcement came a median of 36 ms after the first Zebra announcement (p10 -2,871 ms, p90 418 ms). The peers ran `/Zakura:1.6.0/` (25), `/Zakura:1.7.0-rc0/` (8), `/Zakura:1.7.0-rc1/` (22), `/Zebra:7.0.0-rc.0/` (8), with the number of connections in brackets.

**@shabam, confirmations at 25 s** (your question in post 13, measurement and arithmetic only)

Ten blocks at 75 s cover 750 s on average, and at 25 s the same expected time is 30 blocks (32 blocks with the measured mean of 23.68 s). On the testnet 30 consecutive NU7 blocks spanned a median of 730 s, p90 926 s and p99 1,187 s over 49,173 overlapping windows. With exponential intervals 10 × 75 s give a median of 725 s, p90 1,065 s and p99 1,409 s, and 30 × 25 s give 742 s, 930 s and 1,105 s.

In the listener window 5 of 780 announced blocks were stale or orphaned (0.64 %). The deepest reorg we observed was 1 block.

Thirty blocks at 25 s vary less than ten blocks at 75 s, p99 1,187 s measured against 1,409 s expected for the old target.

For perfect 25 s blocks the p99 over 30 blocks would be about 1,105 s. The measured 1,187 s sits above that, partly because of the hashrate jumps (1,154 s without the windows around them), and still well below the 1,409 s for 10 blocks at 75 s.

We did not measure orphaned blocks and reorg depth since activation outside the listener window, arrival times on our own nodes because we run none, or Equihash solutions and block contents because we only fetched headers.

We fetched the headers directly from testnet peers via P2P (`getheaders`), anchored them at a Zebra checkpoint, checked hash linkage and proof of work against nBits and cross-checked them against further peers.

Method, CSV and the full report are at pulsehawk.io/zcash-nu7.
