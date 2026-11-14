# Prime-token source-disjoint readiness — 2026-11-13

## Gate snapshot — 2026-11-13

The six-view prime-token catalog is not yet authorized for prospective scoring
or training.  The hash-pinned readiness scan currently has 4 closed-session
review-query candidates against a minimum of 30, leaving a deficit of 26.

- Stable source sessions: 17.
- Closed source sessions: 16.
- Open source sessions: 1.
- Collector-eligible unique turns: 176.
- Closed review-query candidates: 4.
- Open review-query candidates: 8.
- Projected total if the current open source closes unchanged: 12.

The missing material cannot be replaced with generated or relabelled rows.  The
evaluation contract requires real query-session families that are disjoint from
catalog source families, with connected components kept indivisible.  Until the
minimum is met, labels remain unopened and scoring, training intake, serving,
merge, promotion, tool dispatch, and partial unfreezing remain unauthorized.

Authoritative readiness receipt:

`C:\dev\clay-training-runs\prime-token-catalog-20261106\prospective-query-readiness-v2-20261113\QUERY_READINESS.json`

Receipt SHA-256 at 2026-11-13 04:18 Pacific:
`1a2829349af7dc0c6a54c2c61ba500ab10d99fc2cf75696966d3ee6552e5adfd`.

## Watcher recovery

The v7 collector, selection auditor, E92 gatekeeper, and source-family gate were
live, but the packet preparer had stopped on 2026-11-11.  Its log and preserved
pending file showed a Windows `PermissionError` during atomic status
replacement, not a catalog or selection failure.

The unchanged hash-pinned worker was restarted from the existing headless
configuration.  It emitted fresh status receipts at 04:23:33 and 04:24:33
Pacific with candidate count 4 and all authority still disabled.

- Recovery launcher PID: `19796`.
- Recovery worker PID: `28984`.
- Config SHA-256: `178f5c28c33b8bde887a68d9a3855ec90529cdaa9521e3975fb0fde9dfe558b3`.
- Watcher SHA-256: `6623f8d0682709c8457c3bccfce564ce1b74d7802af3c6b1ef5c2bf7ca0d0564`.
- Preparer SHA-256: `9b348e059bb6074385d5537e204af90a7b9b2171376724af9e0b4e9c46e80a58`.
- Recovery receipt SHA-256: `5c8dd081afeb0db40323ee8c36d6e819aa1c4fcd58f38a24d0259518a9ef491c`.

Recovery receipt:

`C:\dev\clay-training-runs\prime-token-catalog-20261106\prospective-preparer-watcher-v7-20261110\RECOVERY_ACTIVATION_20261113.json`

This recovery restores readiness for a future valid queue.  It does not reduce
the 30-query minimum, manufacture source material, or establish evaluation
evidence.

## Selection accounting and live-chain audit — 2026-11-14

A stable one-shot count-only scan now separates pipeline health from material
scarcity.  It observed 16 closed source sessions and one open source session.
Across all 17 stable sessions, the pinned collector exposed 195 eligible unique
turns; the frozen review selector accepted 4 closed-session candidates and 10
open-session candidates.  If the open session closed unchanged, the queue would
therefore contain 14 candidates and remain 16 short of the immutable floor.

Every eligible turn is accounted for.  The closed sources contain 11 eligible
turns: 4 accepted and 7 rejected by the frozen topic rule.  The combined stable
sources contain 195 eligible turns: 14 accepted, 143 rejected by topic, and 38
rejected by length.  Both selector accounting gaps are zero, there are no
invalid JSON lines, and source health is `HEALTHY`.  The receipt classifies the
shortfall as `FIXED_SELECTOR_CANDIDATE_SCARCITY`, not a collector, watcher, or
accounting failure.  The open candidates remain count-only telemetry and cannot
enter the queue until their source closes.

Immutable readiness snapshot:

`C:\dev\clay-training-runs\prime-token-catalog-20261106\source-disjoint-audit-20261114\QUERY_READINESS_SNAPSHOT_20261114T0522Z.json`

File SHA-256:
`8934aa1253e7b093ba5d65079329f8b4ebd358260d4cdf3e0b8786d2d172c1fe`.

The independently re-run pre-score chain audit reports
`VERIFIED_WAITING_NO_SCORING` with zero errors.  It verifies the 16 closed and
one deferred-open sources, candidate count 4 against minimum 30, the frozen v7
catalog SHA-256
`a720faae57ca5f64424624dd53f4a8913a7b01fdf12ae9b8e6855bd294ba751a`,
and live collector/preparer statuses.  It also confirms that scoring, training
intake, serving, merge, and promotion remain unauthorized.

Independent audit receipt:

`C:\dev\clay-training-runs\prime-token-catalog-20261106\source-disjoint-audit-20261114\LIVE_CHAIN_AUDIT_20261114T0520Z.json`

- canonical audit SHA-256:
  `e68775d64ab4d1ca3d37d5d53adc20f1446963abb697dc762b61700d6ae32e48`;
- file SHA-256:
  `ce8195eba9441c2513576dd6dd94215e19abc0d92641a6ccf0fd9bdae626d5ad`.

Focused selector/readiness verification passed `20 / 20` tests.  No selector,
minimum, catalog, probability table, model weight, training intake, promotion,
tool-dispatch, or partial-unfreeze authority changed.

