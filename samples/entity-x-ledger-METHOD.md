# Entity X ledger, how it is counted

`entity-x-ledger.csv` lists every movement of one Kaspa address, the one this project calls Entity X.

`kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a`

Counted on 30 sep 2026 at 10:12 utc in run https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/36701002510 with `scripts/musterdateien.py`. The file was built from that run's log with `python3 scripts/musterdateien.py --aus <log>`.

## What is in it

* 538 rows, one per transaction, from 6 mar 2024 10:42 utc to 29 sep 2026 08:03 utc.
* 512 rows are `in` and 26 are `out`.
* Every row is an accepted transaction that touches the address.
* The last `stand_danach_kas` is 1,521,367,293.63490706 KAS. That is exactly the balance api.kaspa.org reported for the address in the same run, a difference of 0 sompi. So no earlier transaction is missing, and the running balance starts at zero.

## How a row is counted

1. Every transaction comes from `api.kaspa.org/addresses/<address>/full-transactions-page` with the inputs resolved. A transaction the API marks as not accepted is dropped. None were.
2. The net amount is the outputs paid to the address minus the inputs spent from it, counted in sompi. Change the address pays back to itself is therefore not counted as an inflow.
3. A positive net is `in`, a negative net is `out`. `betrag_kas` is the net amount without its sign. A transaction with a net of exactly zero would be left out. There was none.
4. Rows are sorted by block time, then by transaction hash.

## The columns

| column | meaning |
|---|---|
| `datum_utc`, `zeit_utc` | block time of the transaction, utc |
| `richtung` | `in` or `out`, as above |
| `betrag_kas` | net amount in KAS, 8 decimals |
| `gegenadresse_gekuerzt` | the other party of the transaction, shortened to the first 14 and last 6 characters, never in full (see below) |
| `label_laut_explorer` | the name the explorer's label directory gives that other party (see below) |
| `tx_hash` | the transaction id, so every row can be checked on any explorer |
| `stand_danach_kas` | the running balance after this row |
| `anteil_umlauf_pct` | that balance as a share of the KAS in circulation at that moment (see below) |

**The other party.**
* For `in` it is the address that put the largest amount into the transaction's inputs.
* For `out` it is the address that received the largest output.
* `+N` after the address means N more parties took part in the same transaction. That holds for 56 rows.
* Only Entity X itself is ever written in full.

**Label.**
* The label comes from the label directory at `api.kaspa.org/addresses/names`. It had 138 entries at counting time.
* A label is that directory's name for the address. We did not verify it.
* An empty cell means the directory has no entry for the address, not that the address belongs to no exchange.
* The directory is marked experimental by its operator and may change.
* The labels that appear are Gate.io in 167 rows, Bybit in 61, Bitget in 24, Kraken in 5, Bitvavo in 4 and KuCoin in 1.

**Share of circulation.**
* The KAS in circulation at a past moment is not published anywhere we can read. It is therefore calculated.
* The starting point is the circulation api.kaspa.org reported in the run. From it we subtract the KAS emitted between the transaction and the run, using the project's emission schedule (`scripts/number_of_day_data.py`).
* Checked against six circulation readings stored in this repository between 7 aug and 28 sep 2026, the calculation is never more than 3,684 KAS off.
* Before 2025 the schedule places the monthly reward steps up to 48 hours away from where the protocol put them (see `miner-economics-METHOD.md`).
* Over the whole period since 6 mar 2024 that moves the denominator by at most 0.013%. The share therefore moves by less than 0.001 percentage points.

## Small amounts

95 rows are below 1 KAS. They stay in the file, because without them the running balance would not match the chain.

## Rule B, and why only one address is counted

This file counts one address and nothing else.
* **Rule A** checks for addresses that spend together with Entity X in the same transaction. It found none in the project's tracker audit of 21 sep 2026 (`data/entity-x-tracker-audit.json`).
* **Rule B** marks an address that Entity X paid and that also paid Entity X. It is weaker than rule A, and such addresses are never added to the balance.

Two addresses meet rule B.

| address | rows where it is the main other party | net KAS that came in, in those rows | net KAS that left, in those rows |
|---|---|---|---|
| `kaspa:qr4znets…s6s2sz` | 6 | 121,601,084.05979064 | 12.00005211 |
| `kaspa:qpu9pjmd…daewcx` | 6 | 11.99989576 | 1,321.00009491 |

These are the net amounts of whole rows. Where a row shows `+N`, other parties took part in the same transaction, so the figures are not what the address alone sent.

## What this file does not say

* It does not name who controls the address, and it does not say why anything moved.
* `in` means KAS came into the address and `out` means KAS left it. Neither is a trade.
* A transfer to or from an address with an exchange label shows a transfer, not a trade and not its reason.
