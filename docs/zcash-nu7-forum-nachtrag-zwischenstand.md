Ahead of the mainnet go/no-go on 20 October, here are our final independent counts for NU7 on the public testnet, covering blocks 4,465,026 to 4,512,797 (47,772 blocks) with a cut-off of 2026-10-17 20:00:00 UTC. These are numbers only, without assessment.

We measured each block interval as the timestamp of a block minus that of its parent, starting at 4,465,027, and compare them with exponential intervals at a 25 s mean.

| | measured | expected |
| --- | --- | --- |
| mean | 23.64 s | 25 s |
| median | 17.0 s | 17.3 s |
| p90 / p99 | 52.0 s / 109.0 s | 57.6 s / 115.1 s |
| share > 75 s | 3.56 % | 4.98 % |
| share > 150 s | 0.199 % | 0.248 % |
| longest gap | 451 s at 4,495,487 | ≈ 284 s (expected maximum) |

In post 24 we quoted a dashboard median of 19.5 s over 300 blocks. Over 47,772 blocks the median is 17.0 s against 17.3 s expected.

We found 6 hashrate jumps of 2x or more. After them the difficulty came within ±15 % of the new level after a median of 960 blocks (159.7 min), and the longest catch-up took 1,839 blocks. 0 timestamps went backwards and 0 were more than 10 min ahead of the median of the next 11 blocks. Since activation there was 1 minimum-difficulty block.

**Listener, as promised in post 24**

We could not measure this part because the listener window was only 15 min (minimum 120 min).

**@shabam, confirmations at 25 s** (your question in post 13, measurement and arithmetic only)

10 blocks at 75 s cover 750 s on average, and at 25 s the same expected time is 30 blocks (32 blocks with the measured mean of 23.64 s). On the testnet 30 consecutive NU7 blocks spanned a median of 729 s, p90 926 s and p99 1,193 s over 47,742 overlapping windows. With exponential intervals 10 × 75 s give a median of 725 s, p90 1,065 s and p99 1,409 s, and 30 × 25 s give 742 s, 930 s and 1,105 s.

We could not measure the stale or orphan rate and the deepest reorg without a valid listener run.

30 blocks at 25 s vary less than 10 blocks at 75 s, p99 1,193 s measured against 1,409 s expected for the old target.

We did not measure orphaned blocks and reorg depth since activation outside the listener window, arrival times on our own nodes because we run none, or Equihash solutions and block contents because we only fetched headers.

We fetched the headers directly from testnet peers via P2P (`getheaders`), anchored them at a Zebra checkpoint, checked hash linkage and proof of work against nBits and cross-checked them against further peers.

Method, CSV and the full report are at pulsehawk.io/zcash-nu7.
