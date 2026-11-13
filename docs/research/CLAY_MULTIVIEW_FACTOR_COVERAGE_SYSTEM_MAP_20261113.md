# Clay multi-view factor-coverage system map — 2026-11-13

Status: completed build and measured 60-horse result; `NO_SELECTION`.

Inventory receipt:
`CLAY_MULTIVIEW_FACTOR_COVERAGE_INVENTORY_20261113.json`
(`69f7a91e8066c5ce51c953caa1155815720de6c82afb5936facfae0b56c8c25d`).

## Bounded system

| Node | Exact path | Role / authority | Status |
| --- | --- | --- | --- |
| Active implementation | `C:\dev\_wt_scbe_atomic_stitch_20261113` | New data selector, matched trainer, evaluator, tests, and research receipts | clean branch before this map except the completed-result note |
| Clay source authority | `C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109` | Existing 37-field state vector, deterministic action labels, three legal training views, held source family | read-only; parent worktree is dirty and must not be edited |
| Prior immutable evidence | `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-depth-confirm-v1` | Completed 45-horse doubled-exposure campaign | verified; never overwritten |
| New immutable run | `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-factor-coverage-v1` | Planned candidate pools, selected banks, checkpoints, traces, and receipts | absent before launch |
| Runtime | local GTX 1660 Ti, 6 GiB VRAM | Standard 6,917-parameter MLP training | available; 0 MiB used at map time |
| Storage | local C: plus indexed OneDrive lifecycle | Checkpoints local during run; cloud lifecycle remains external | healthy; 28.44 GB C: free, no cloud enumeration |

The connected Clay worktree is an input authority only.  All new code and
research records belong to the active SCBE worktree.  The side PC is not an
authority or runtime dependency.

## Existing measured path

```text
Clay state generator
  -> 37-field exact state vector + deterministic action label
  -> legal geometry view (0, +22.5 degrees, -22.5 degrees)
  -> immutable OrbitBank tensors
  -> ordinary Linear/GELU MLP (6,917 learned scalars)
  -> cardinal anchor selects checkpoint
  -> shifted-physics held sector evaluates transfer
  -> horse/checkpoint/result/gate receipts
```

Every edge above is measured by a tensor, source, checkpoint, or result hash.
The previous run proved that 55--140 repetitions of one canonical concept did
not replace independent multi-view support.  Separate shape experiments proved
that transformed support and explicit cross-factor coverage helped, while the
elite-gradient scheduler did not beat shuffled controls.

## New capability

Add a deterministic training-only selector that fills useful cross-factor
cells **conditional on view and action**, before ordinary uniform replay.  It
does not add model parameters, read holdout rows, change labels, or grant
execution authority.

The selector uses these declared input-factor products:

1. `phase x drive x target`
2. `phase x target`
3. `drive x target`
4. `position_x_bin x position_y_bin`
5. `velocity_x_bin x velocity_y_bin`
6. `scope_sign_x x scope_sign_y`
7. `memory_slots x stagnation_ticks`
8. `memory_slots x outburst_ticks`

Action is used only to hold identical `(view, action)` quotas across the three
multi-view arms.  It is not inserted into model input.  Evaluation, anchor,
reward, post-outcome, and held-source fields are prohibited from selection.

## Matched arms

| Arm | Purpose |
| --- | --- |
| `static_unique` | Standard single-view baseline with equal rows, parameters, steps, and seeds. |
| `multiview_random` | No-intervention multi-view baseline selected by deterministic random order. |
| `multiview_factor` | Proposed factor-cell selector with the random arm's exact view/action quotas. |
| `multiview_factor_shuffled` | Size-matched ablation: identical selector over independently shuffled factor signatures. |

The three multi-view banks are selected without replacement from one hash-pinned
training-source candidate pool and must be mutually row-disjoint.  They must
have byte-identical view/action count tables.  The shuffled arm preserves each
factor-product marginal while breaking its attachment to the physical row.

## Edge contracts

| Edge | Shape / invariant | Evidence |
| --- | --- | --- |
| source -> candidate pool | `N x 37` float32, int64 action/sector/group/view; finite; held sector absent | source hashes + bank receipt |
| candidate -> selected arm | 30,000 rows; 10,000 per view; no replacement; declared quota table | selection receipt |
| selected arm -> learner | uniform sampler only; 4,800 x 192 observations; no online holdout access | exact schedule/config receipt |
| learner -> checkpoint | identical 6,917-scalar initialization by fold/seed across arms | state hashes |
| checkpoint -> evaluator | 10,000 held-source rows and 10,000 same-source anchor rows per fold | split manifests |
| evaluator -> verdict | sector-stratified accuracy + stable macro-F1, finite floor, two pooled SD, anchor retention | independent gate receipt |

## Pre-build gate

- Capability: measured factor-cell data support for the existing action learner.
- Reuse: Clay source adapter, OrbitBank schema, standard MLP, checkpoint
  selection, source-disjoint evaluator, canonical receipt functions.
- New downstream risk: factor selection can secretly become class balancing or
  attach label-derived information.  Exact quota matching and shuffled binding
  are mandatory controls.
- Baselines: static unique and random multi-view.
- Size-matched control: shuffled factor binding.
- Holdout: shifted-physics source and held sectors 1, 4, and 7.
- Compute budget: 60 horses (4 arms x 5 seeds x 3 folds), 4,800 steps, one local
  GPU, expected under 30 minutes after data preparation.
- Disk budget: under 0.5 GB, with a 20 GB free-space launch floor.
- Save/rollback: new non-overwriting run directory; earlier checkpoints remain
  immutable; rollback is stopping the new headless launcher only.
- Stop before training if any manifest fails, selected arms overlap, view/action
  quotas differ, held rows influence selection, source hashes drift, finite
  tensors fail, or the disk floor is not met.

Even a passing mechanics gate cannot promote a checkpoint or authorize partial
unfreeze.  It can only select the data construction for a later independent
model confirmation.

## Post-build update

Implementation commit: `1f0fbb83e1a584791061f5c2ae8cb7d867481278`.

Changed executable surfaces:

- `python/scbe/clay_multiview_factor_coverage.py`
- `scripts/research/run_clay_multiview_factor_coverage.py`
- `tests/governance/test_clay_multiview_factor_coverage.py`

Verification after the commit hook:

- Ruff: all selected files passed.
- Focused plus related regressions: `19 passed`.
- Real Clay preflight, held sector 1, 18,000 candidate rows and 3,000 rows per
  arm: true-factor entropy `0.98553`, random `0.94086`, shuffled `0.92878`;
  true-factor cell coverage `0.99850`; zero selected-index and exact-feature
  overlap; all view/action quotas matched.

The full immutable run was launched headlessly at
`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-factor-coverage-v1`.
Its configuration SHA-256 is
`9f4269b5e00b18cb2242611579ccb21fab2d3c76a07a84c34e0c784696139e01`.
Data construction for all folds precedes every optimizer step, so a failed
full-scale intervention check leaves zero trained horses.

## Measured closure

The run completed all 60 horses.  The semantic factor arm increased declared
factor-cell entropy in every fold but lost to random multi-view data in all
three held sectors and missed anchor retention in all three.  The producer and
stratified verdicts are both `NO_SELECTION`.

The unexpected shuffled-factor control led globally at `0.9166` accuracy and
`0.7763` stable F1 while retaining `0.9816` anchor accuracy.  Because it was an
ablation rather than the preregistered primary arm, this is exploratory and
requires fresh confirmation.  Exact results and the receipt audit are in
`CLAY_MULTIVIEW_FACTOR_COVERAGE_RESULT_20261113.md`.

Result receipt:
`b51cd41d2d441c95333e164d99301119d730ebba8927bd600c28502dc28113fc`.

Stratified gate receipt:
`c57a0913f409fe353d1979010ad4546aeb3e6bc9945a38e2187fed5d9945c009`.

