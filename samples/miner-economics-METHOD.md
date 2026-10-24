# Miner economics, how it is counted

`miner-economics.csv` has one row per utc day, from 1 oct 2023 to 29 sep 2026, 1,095 rows. 1 oct 2023 is the first day of the fee series we read.

Counted on 30 sep 2026 at 10:12 utc in run https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36701002510 with `scripts/musterdateien.py`. The file was built from that run's log with `python3 scripts/musterdateien.py --aus <log>`.

## The columns

| column | meaning |
|---|---|
| `datum_utc` | the utc day |
| `hashrate_phs` | the day's hashrate in PH/s, the plain average of all readings in `api.kaspa.org/info/hashrate/history` for that day (`hashrate_kh` as the API gives it, not recalculated). The series has 41,917 readings, about one an hour, and every day in the file has at least 12. |
| `block_reward_kas` | the reward per block at the day's first hashrate reading, from that reading's DAA score and the protocol rule (see below) |
| `neue_kas_tag` | new KAS emitted in the utc day (see below) |
| `gebuehren_kas_tag` | fees paid that day, from Kaspalytics `transactions/accepted/fees/total`, series `Fees`. The stamp of a daily total is the counted day. |
| `gebuehren_anteil_pct` | fees as a share of what miners received that day, fees divided by fees plus new KAS |
| `naechste_senkung_utc` | the next monthly reward step after 00:00 utc of that day (see below) |

## Reward per block, from the protocol

The reward per block is computed the way a Kaspa node computes it.
* The source is `calc_block_subsidy` in rusty-kaspa v2.1.0, file `consensus/src/processes/coinbase.rs`, with the mainnet parameters from `consensus/core/src/config/params.rs`.
* The monthly table and the parameters are copied into `scripts/musterdateien.py`, and its self test checks them.
* The input is the DAA score of the day's first hashrate reading.

Until the Crescendo upgrade, at DAA score 110,165,000 on 5 may 2025, the chain ran at 1 block per second. After it, the chain runs at 10. The reward per block therefore drops by a factor of ten on 6 may 2025, while the KAS emitted per second stays the same.

For 29 sep 2026 the protocol gives 2.18267645 KAS per block, the same value as the project's emission schedule.

## New KAS per day, and the reward steps

The reward falls one step every month.
* The protocol counts those months in DAA score, not in clock time.
* A step counts as having happened at the first hashrate reading whose DAA score already lies in the new month. That is at most 3,702 seconds after the step itself.
* `neue_kas_tag` is the protocol's reward per second, summed over the utc day, with the reward changing at those moments.
* `naechste_senkung_utc` is the moment of the next such step.
* For the step that no reading has reached yet, 5 oct 2026, the time comes from the project's emission schedule (`scripts/number_of_day_data.py`). That schedule has matched the observed steps to within 1.2 hours since aug 2025.

**Where the project's schedule is off.**
* Before 2025 the schedule, which counts in clock time, puts the steps earlier than the protocol did. The gap was about 48 hours in 2023, 12 hours in mid 2024 and 6 hours in early 2025.
* The cause is that the chain produced slightly fewer blocks than one per second before Crescendo, so the DAA count ran behind the clock.
* On 50 step days this file's `neue_kas_tag` therefore differs from the schedule's figure by more than 0.01%, by up to 5.6%. The file follows the protocol.

**Assumption.** New KAS per day assumes the nominal block rate, 1 per second before Crescendo and 10 after. After Crescendo that matches measured circulation to within 3,684 KAS between 7 aug and 28 sep 2026. Before Crescendo it is not checked against a measured circulation, because we have none from that time.

## Gaps

Kaspalytics has no fee value for these 11 days.
* 1, 2, 3, 4, 5 and 6 feb 2025;
* 22 jan 2026;
* 17, 18, 19 and 20 mar 2026.

On those days `gebuehren_kas_tag` and `gebuehren_anteil_pct` are empty cells. Nothing is filled in or interpolated.

## What this file does not say

It has no prices and no dollar values, and it makes no forecast. Every number is either read from the chain, read from Kaspalytics as named above, or computed from the protocol rule.
