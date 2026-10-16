# Covenant daily series up to 9 October 2026

Kaspa Pulse takes this series over from Kaspalytics and did not count covenant outputs itself. Every number in this folder is a Kaspalytics number as Kaspalytics published it on the day we fetched it. We have no list of individual covenant outputs, so the figure of 13,936 unspent covenant outputs at the end of 9 October 2026 cannot be rebuilt from a per output list here. It is the Kaspalytics end of day value for that date.

## Files

| File | Content |
|---|---|
| tagesreihe.csv | one row per UTC day from 30 June 2026 to 9 October 2026, 102 rows plus header |
| tagesreihe.json | the same rows plus source, range, origin commit and a short summary |
| METHOD.md | this text |

Every row in both data files carries the column source with the value Kaspalytics.

## Source

Kaspalytics publishes three public chart feeds without login. We read them once a day.

| Our column | Kaspalytics feed |
|---|---|
| created and spent | https://www.kaspalytics.com/api/charts/covenants/outputs (series Created and Spent) |
| unspent_end_of_day | https://www.kaspalytics.com/api/charts/utxo/covenant-count (series Covenant UTXOs) |

The feed https://www.kaspalytics.com/api/charts/covenants/transactions is also logged by us but is not part of this release.

## How the values reached this folder

A scheduled job in this repository (scripts/covenants_log.py, workflow covenants-log.yml) fetches the three feeds once a day and appends the result to data/covenants-log.json. The files here were derived from data/covenants-log.json at commit 5d66931ac9f86063ff5590495b7262edd203f553 without any change to the values. Anyone can rebuild them from that file and that commit.

Rules the daily job applies, unchanged since before this release

1. Days are UTC days. created and spent are daily sums that Kaspalytics stamps at midnight UTC of the day they count.
2. unspent_end_of_day is a stock that Kaspalytics measures close to midnight UTC. A stock point counts for a day only if it lies within two hours of the following midnight. source_timestamp_utc shows the exact Kaspalytics timestamp.
3. The current day is never read. Only finished days are logged.
4. Kaspalytics filled the history back to 26 June 2026 when we first fetched on 22 September 2026. Rows up to 21 September therefore all carry fetched_utc 2026-09-22T08:17:09+00:00.
5. If Kaspalytics changes an old value, the job takes the new value and moves fetched_utc of that day, so a later revision stays visible.

## Columns

| Column | Meaning |
|---|---|
| date | UTC day |
| created | covenant outputs created on that day, Kaspalytics |
| spent | covenant outputs spent on that day, Kaspalytics |
| unspent_end_of_day | unspent covenant outputs at the end of that day, Kaspalytics |
| source_timestamp_utc | Kaspalytics timestamp of that stock point |
| change_in_unspent | unspent_end_of_day of this day minus that of the day before |
| created_minus_spent | created minus spent of this day |
| divergence | change_in_unspent minus created_minus_spent |
| status | ok, divergence, missing or not computable, with the reason |
| source | always Kaspalytics |
| fetched_utc | when our job last took the value from Kaspalytics |

The last three derived columns are our arithmetic on the Kaspalytics values. Nothing else is computed by us.

## The 13 days with divergence

If the three Kaspalytics series fit together, the stock should change each day by exactly created minus spent. On 13 of the 101 days where both sides can be computed it does not.

| Date | change_in_unspent | created_minus_spent | divergence |
|---|---|---|---|
| 2026-07-01 | 8 | 16 | minus 8 |
| 2026-07-02 | 8 | 14 | minus 6 |
| 2026-07-06 | 2 | 10 | minus 8 |
| 2026-08-04 | 341 | 349 | minus 8 |
| 2026-08-05 | 89 | 90 | minus 1 |
| 2026-08-10 | 31 | 32 | minus 1 |
| 2026-08-11 | 39 | 38 | plus 1 |
| 2026-08-19 | 96 | 95 | plus 1 |
| 2026-08-20 | 160 | 161 | minus 1 |
| 2026-08-24 | minus 129 | minus 128 | minus 1 |
| 2026-08-25 | 179 | 178 | plus 1 |
| 2026-09-21 | 317 | 331 | minus 14 |
| 2026-10-09 | 16 | 17 | minus 1 |

The divergences add up to minus 46. Over the whole range Kaspalytics shows 292,292 created and 278,310 spent, a difference of 13,982, while the stock went from 0 at the end of 29 June to 13,936 at the end of 9 October. The gap of 46 equals the sum of the 13 daily divergences. Twelve of the 13 days come from the history Kaspalytics returned on 22 September, the last one is 9 October itself.

We do not know the cause. We did not count on chain and cannot say which of the three series is off on these days. The stock timestamps of these days lie between 0 and 39 seconds after midnight, so a late stock point does not explain them.

## Missing and not computable

| Date | What is missing | Why |
|---|---|---|
| 2026-09-29 | unspent_end_of_day | Kaspalytics measured this stock at 12:02:05 UTC on 30 September, far from midnight, so the day stays empty under rule 2 |
| 2026-09-30 | divergence | the stock of the day before is missing |

On 30 September our job first logged that midday value, 13,342, as the stock of 29 September, and it was published that way. Rule 2 was added on 3 October, and on 5 October the value was removed from the log and the day left empty. This is the only value in the range that changed after it was first logged.

created and spent are present on both days. Taken together, 29 and 30 September show no divergence. The stock rose by 338 from the end of 28 September to the end of 30 September, and created minus spent on the two days is 75 plus 263, also 338.

## Known limits

1. Not counted by Kaspa Pulse. Every value depends on how Kaspalytics defines and counts a covenant output, and we do not know that definition in detail.
2. No per output list. We cannot give outpoints, covenant ids, scripts, amounts or creation times. Public nodes keep about one and a half days of history, so the state of 9 October cannot be rebuilt from our nodes either.
3. Kaspalytics can revise its history. This release shows the values as logged at the commit named above.
4. No independent chain check. The divergence column only shows whether the three Kaspalytics series agree with each other.

## Second check

A second pass, written separately from the code that built these files, recomputed the range from data/covenants-log.json and walked all 25 commits of that file from 22 September to 16 October 2026. It found

1. 102 days in the range, every day present, the stock missing only on 29 September.
2. 13,936 as the stock at the end of 9 October, first logged on 10 October at 13:00:30 UTC and never changed since.
3. The same 13 days of divergence with the same values, summing to minus 46, and no divergence over 29 and 30 September taken together.
4. 292,292 created and 278,310 spent over the range.
5. No value in the range changed after it was first logged, except the stock of 29 September described above.

## Checksums

sha256 of the data files in this folder

```
a31d13b43f8c8eb7e53519184fe34915d52656ca724ac1c1d2a07f11c82e453d  tagesreihe.csv
0ca8b9fcc24d56e9112d326e21ad91ba3313097197677d48deec03d3e2bf8ad8  tagesreihe.json
```
