# Crypto / Blockchain Mechanisms — Research Notes

Status: Idea Seed → Research Brief (see `../RESEARCH_PACKET_STANDARD.md`)
Created: 2026-10-24
Author: Issac Davis (session write-up compiled by Peyton, Issac's Grok Bot assistant)

> "Trading is, at the end of the day, just a different sort of blockchain. Doesn't matter what currency it is, even dollars are a blockchain, it's just a paper one. Spread on the chain of trust."
> — Issac Davis, 2026-10-24

## What this folder is

A single consolidated write-up of one long working session that started with the
history of computational thinking and ended with a testable design for a
multi-venue exchange aggregator whose decision log feeds SCBE. The through-line:
**every ledger — tape, memory cell, order book, blockchain, dollar bill — is a
record of state that only means something if it persists, can be read back, and
can be reconciled against another record.**

The original session artifacts (`artifacts/*.md`, `artifacts/scbe_reconciliation_stubs.py`)
did not persist on the working box. These files are the durable reconstruction.

## Claim-boundary conventions used here

- **Verified** — checked against a primary source or reputable report; link given.
- **Paraphrase** — wording is ours, not the author's. Direct quotes appear only where we could confirm them.
- **⚠ Session note — verify** — stated in the session, not independently confirmed when written.

## Reading order

| # | File | Theme |
|---|------|-------|
| 01 | [01_denning_tedre_precepts.md](01_denning_tedre_precepts.md) | Computational-thinking precepts 2, 4, 5, 7, plus a deep dive on 9 |
| 02 | [02_stored_program_address_data.md](02_stored_program_address_data.md) | Precept 6, addresses vs constants, and Data = Concept + Identity + Location + Methods |
| 03 | [03_computing_without_electricity.md](03_computing_without_electricity.md) | Gears, beads, and the boulder: what makes matter into memory |
| 04 | [04_ceruzzi_microprocessor_era.md](04_ceruzzi_microprocessor_era.md) | Ceruzzi's four threads and the microprocessor era |
| 05 | [05_wozniak_efforce_wozx.md](05_wozniak_efforce_wozx.md) | Wozniak today, EFFORCE and WOZX market notes |
| 06 | [06_exchange_aggregator_design.md](06_exchange_aggregator_design.md) | Aggregator front end, adapter interfaces and auth vault |
| 07 | [07_reconciliation_engine_spec.md](07_reconciliation_engine_spec.md) | Reconciliation module spec (code in `prototype/reconciliation/`) |
| 08 | [08_reconciliation_research_findings.md](08_reconciliation_research_findings.md) | Prior art: FIX, NautilusTrader, finality, dedupe |
| 09 | [09_no_data_state.md](09_no_data_state.md) | Why "no data" is not "flat" |
| 10 | [10_topology_map_spec_v2.md](10_topology_map_spec_v2.md) | Five-layer topology map, version 2 |
| 11 | [11_topology_stress_test_results.md](11_topology_stress_test_results.md) | What the stress test broke, and the fixes |
| 12 | [12_parallel_universes_experiment.md](12_parallel_universes_experiment.md) | Two clocks, one seed (the Crusader Kings analogy) |
| 13 | [13_blackout_protocol_mars.md](13_blackout_protocol_mars.md) | Solar-conjunction blackout as a test of intent |
| 14 | [14_overlapping_cycles_engine_model.md](14_overlapping_cycles_engine_model.md) | Power, torque and traction across time grains |
| 15 | [15_low_budget_test_plan.md](15_low_budget_test_plan.md) | Zero-cost paper-trading plan |
| 16 | [16_conversation_trajectory.md](16_conversation_trajectory.md) | How the session moved, phase by phase |
| — | [CHANGELOG.md](CHANGELOG.md) | Spec v1 → v2 deltas |

## Code

- `prototype/reconciliation/scbe_reconciliation_stubs.py`: paper-only reconciliation core. It has no network access and no keys.
- `tests/research/test_scbe_reconciliation_stubs.py`: 9 tests.

## Scope boundary

This is research and paper trading only. Nothing here places real orders, holds
customer funds, or tries to avoid exchange or financial regulation. The aggregator
idea is a front-end and middleman layer (like YouTube for content ↔ viewers, or
Cash App between markets), and it runs on top of each venue's own compliance and
authentication.
