# Forum draft, BCH tempnet week 3 (Ben posts)

Window 28 Oct 10:00 utc to 4 Nov 10:00 utc, split at 29 Oct 21:00 utc. Header chain up to block 356,042, listener data up to 3 Nov 13:59 utc. Reply to bitcoincashautist and rufitnes. Numbers from scripts/bch/forum_woche3.py on messung/bch-tempnet, commit 2b5c3c8, file data/bch/tempnet-woche3-forum-2026-11-04.json. Weekly run 4 Nov, header fetch 10:07:51 utc, cross check 500 of 500 with two peers. Everything below this line is the post.

@bitcoincashautist @rufitnes Week three of our tempnet counts.

**Two windows.** Our listener numbers change from 29 Oct 21:00 utc on. At 22:35 utc all our connections to one node dropped in the same second, which looks like a restart, but the change in our numbers starts about 95 min earlier. So every table below has one column before and one after 29 Oct 21:00 utc, and no value is averaged across both.

**Block intervals from our own headers**

| | before, 28 Oct 10:00 utc to 29 Oct 21:00 utc | after, 29 Oct 21:00 utc to 4 Nov 10:00 utc | computed for 60 s |
|---|---:|---:|---:|
| blocks | 345,614 to 347,726 | 347,727 to 356,040 | |
| intervals | 2,113 | 8,314 | |
| mean | 59.62 s | 57.59 s | 60 s |
| median | 43.0 s | 30.0 s | 41.6 s |
| p90 | 132.0 s | 129.0 s | 138.2 s |
| p99 | 207.0 s | 382.9 s | 276.3 s |
| share above 5 min | 0.0 % (0) | 1.56 % (130) | 0.67 % |
| longest gap | 276 s | 1,159 s | about 576 s |
| blocks with minimum difficulty | 282 | 1,513 | |
| intervals of exactly 120 s | 46 | 57 | |

**Listener on our own network path**

| | before | after |
|---|---:|---:|
| chain blocks seen | 2,113 | 7,449 |
| peers announcing a block, median | 23 | 16 |
| timestamp_deviation, median / p90 / p99, all blocks | 0.80 / 3.34 / 36.3 s | 3.19 / 5.29 / 14.1 s |
| same without blocks exactly 120 s after their parent | 0.78 / 3.20 / 5.1 s (without 46) | 3.18 / 5.25 / 12.2 s (without 55) |
| propagation_spread, median / p90 | 7.8 / 11.0 s | 7.2 / 10.3 s |
| stale blocks after 6 confirmations | 4 of 2,117 announced (0.19 %) | 398 of 7,847 announced (5.07 %) |

**A correction to how we showed week two.** We gave a timestamp_deviation p99 of 31.1 s. Without the 107 blocks whose header timestamp is exactly 120 s after their parent the p99 is 5.2 s, so that tail came almost entirely from those blocks. Thanks to rufitnes, who showed on 30 Oct that 101 of the 106 such blocks in his data come from one miner (source rufitnes). We only count timestamps and do not look at who mined a block.

**Stale blocks** use the same definition as in week two. A block counts as stale when it was announced to us and is not in the chain 6 blocks later, and the share is stale blocks over chain blocks plus stale blocks.

In the before window 38 blocks reached one of our peers more than 10 min after the first announcement, between 29 Oct 00:21 utc and 29 Oct 00:55 utc. That is why we leave out the p99 of propagation_spread this week.

Of the 398 stale blocks in the after window, 356 fall into three short periods, 216 from 29 Oct 21:00 utc to 29 Oct 23:00 utc with 488 chain blocks per hour, 112 from 2 Nov 22:00 utc to 3 Nov 00:00 utc with 369 chain blocks per hour and 28 from 3 Nov 08:00 utc to 3 Nov 09:00 utc with 254 chain blocks per hour. Across the whole after window the median is 58 chain blocks per hour.

**Coverage.** The listener covered 148.0 h of the 148.0 h from window start to 3 Nov 13:59 utc, in 28 segments with 35 to 47 peers that confirm the fork at block 327,989. There was no gap between segments. Listener data ends at 3 Nov 13:59 utc, because the segment after it stopped without saving its data, so the last 20 h of the window are missing from the listener tables.

All numbers in the tables are counted by us from our own header chain and our own listener, except the column computed for an ideal 60 s chain. The listener keeps running until the tempnet ends on 15 Nov.
