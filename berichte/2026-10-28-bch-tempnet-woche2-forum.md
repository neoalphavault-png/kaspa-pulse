# Forum draft, BCH tempnet week 2 (Ben posts)

Window for the listener is 25 Oct 2026 09:15 utc to 28 Oct 2026 07:36 utc. Window for the header counts is 21 Oct 2026 10:00 utc to 28 Oct 2026 10:00 utc. Everything below this line is the post.

Week two of our tempnet counts, now with a listener on our own network path.

**How we count.** A listener without its own node keeps connections only to tempnet peers that confirm the fork at block 327,989 and logs every block announcement with its message type (inv, headers, cmpctblock), a peer label such as peer_1 and the arrival time in milliseconds. We then match the announcements by hash against our own header chain, fetched over p2p and checked for linkage and proof of work. For each block we request one cmpctblock from the first announcer and estimate missing transactions from the BIP152 short IDs against the transactions announced to us by inv.

**Coverage.** The listener ran from 25 Oct 09:15 utc to 28 Oct 07:36 utc in 14 segments, 71.7 h in total. There are two gaps between segments, of 6 min 57 s on 25 Oct from 09:27:47 utc and of 1 min 35 s on 26 Oct from 12:37:49 utc. Each segment held 31 to 47 peers that confirm the fork.

**Block intervals, 21 Oct 10:00 utc to 28 Oct 10:00 utc, blocks 335,561 to 345,613**

| | counted | computed for 60 s |
|---|---:|---:|
| intervals | 10,053 | |
| mean | 60.16 s | 60 s |
| median | 45.0 s | 41.6 s |
| p90 | 132.0 s | 138.2 s |
| p99 | 212.5 s | 276.3 s |
| share above 5 min | 0.02 % (2) | 0.67 % |
| longest gap | 334 s, before block 335,881 on 21 Oct 15:45:56 utc | about 588 s |
| timestamp minus median time past, median / p90 / p99 | 355 / 518 / 658 s | 340 / 557 / 786 s |

In the same week 1,364 blocks carry the minimum difficulty.

**Listener, blocks 341,252 to 345,470 (4,207 blocks)**

We saw every one of the 4,207 chain blocks announced, in the median by 22 peers.

| | counted |
|---|---:|
| first seen by inv | 4,205 |
| first seen by headers | 2 |
| first seen by cmpctblock | 0 |
| timestamp_deviation, median / p90 / p99 | 0.78 / 3.40 / 31.1 s |
| timestamp_deviation, smallest / largest | 0.08 / 196.0 s |
| propagation_spread, median / p90 / p99 | 7.6 / 10.8 / 16.7 s |
| stale blocks after 6 confirmations | 16 of 4,223 announced (0.38 %) |
| cmpctblock received on request | 4,204 |
| cmpctblock received unsolicited | 0 |
| short IDs per block, median / p90 / largest | 5 / 25 / 78 |
| missing transactions (estimate), median / p99 / largest | 0 / 1 / 10 |

timestamp_deviation is first seen minus the header timestamp, the name bitcoincashautist suggested in this thread. It is not a pure propagation value because miners set the timestamp within the rules. Of the 42 blocks above the 99th percentile, 41 carry a header timestamp exactly 120 s after their parent, and none of them carries the minimum difficulty.

propagation_spread is the last minus the first announcement across our peers, for blocks seen from at least two peers. It describes the spread at one listener over 20 to 50 connections, not the propagation time across the network.

A stale block here is a block that was announced to us but is not in the chain 6 blocks later. The full list with height, hash, header time, first seen and number of announcing peers is in the CSV linked below.

**Why the compact block numbers are an estimate.** We run no mempool. We count the short IDs that match no transaction announced to us by inv. A real node also knows transactions it validated itself, so this approximates what a node would have to request.

**Why cmpctblock almost never arrives as an announcement.** Under BIP152 a node pushes new blocks as cmpctblock right away to at most three peers that it picks itself as high bandwidth peers, usually the peers that recently delivered blocks first. A listener that never relays blocks is never picked, so every other peer announces by inv or headers and sends the cmpctblock only on request.

**Next to rufitnes/tempnet-data.** We matched our 4,207 blocks by hash with the public data at commit 787f561 (snapshot 345,617), and all of them are in both sets.

| | counted | source rufitnes/tempnet-data |
|---|---:|---:|
| timestamp_deviation, median / p90 / p99 | 0.78 / 3.4 / 31.1 s | 1 / 4 / 33 s |
| blocks via compact | 4,204 (on request) | 4,189 |
| missing or requested transactions, median / p99 / largest | 0 / 1 / 10 | 0 / 1 / 10 |
| stale blocks or reorg events | 16 stale blocks | 0 reorg events |

The reorg count and our stale count measure different things. A node logs a reorg only if it had already moved its tip to the block that later lost, and a node that receives the winning block first never logs one. The time columns use whole seconds on his side and milliseconds on ours, and the two clocks are not aligned.

Data, one row per block, is at github.com/neoalphavault-png/kaspa-pulse on branch messung/bch-tempnet, file data/bch/tempnet-woche2-bloecke-2026-10-28.csv. The listener keeps running until the tempnet ends on 15 Nov.
