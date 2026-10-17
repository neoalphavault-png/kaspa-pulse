Ahead of the mainnet go/no-go on 20 October, here are our final independent counts for NU7 on the public testnet: blocks 4,465,026 to 4,512,093 (47,068 blocks), cut-off 2026-10-17 15:00:00 UTC. Numbers only, no assessment.

**Block intervals** (timestamp of a block minus that of its parent, first interval at 4,465,027; expectation: exponential intervals with a 25 s mean)

| | measured | expected |
| --- | --- | --- |
| mean | 23.61 s | 25 s |
| median | 17.0 s | 17.3 s |
| p90 / p99 | 52.0 s / 109.0 s | 57.6 s / 115.1 s |
| share > 75 s | 3.54 % | 4.98 % |
| share > 150 s | 0.200 % | 0.248 % |
| longest gap | 451 s at 4,495,487 | ≈ 283 s (expected maximum) |

Difficulty: 6 hashrate jumps of 2x or more; difficulty caught up (within ±15 %) after a median of 960 blocks / 159.7 min, longest 1,839 blocks. Timestamps: 0 going backwards, 0 far ahead (>10 min ahead of the median of the next 11). Minimum-difficulty blocks since activation: 1.

**Listener (as promised in post 24)**

Not measured: the listener window was only 15 min (minimum 120 min).

**@shabam: confirmations at 25 s** (your question in post 13; measurement and arithmetic only)

- 10 blocks at 75 s cover 750 s on average; at 25 s the same expected time is 30 blocks (with the measured mean of 23.61 s: 32 blocks).
- Measured on the testnet: 30 consecutive NU7 blocks spanned a median of 729 s, p90 926 s, p99 1,196 s (47,038 overlapping windows).
- For comparison, exponential intervals: 10 × 75 s median 725 s, p90 1,065 s, p99 1,409 s; 30 × 25 s median 742 s, p90 930 s, p99 1,105 s.
- Stale/orphan rate and deepest reorg: not measured (no valid listener run), see above.

**Not measured**: orphaned blocks and reorg depth since activation (only in the listener window), arrival times on our own nodes (we run none), Equihash solutions and block contents (headers only).

Method: headers fetched directly from testnet peers via P2P (`getheaders`), anchored at a Zebra checkpoint, checked for hash linkage and proof of work against nBits, cross-checked against further peers. Scripts and data: `scripts/zcash/`, `data/zcash/` (kaspa-pulse repository).
