# Clay random multi-view confirmation system map — 2026-11-13

Status: mapped after the hash-spread campaign and before new data generation or
model outcomes.

## Question

The hash-spread specificity run found no useful distinction between shuffled
factor cells and equal-width deterministic hash cells.  Its control arm did
find a stronger signal: random multi-view data beat static unique data in all
15/15 matched accuracy and stable-F1 comparisons, and led all four arms
globally.  This successor tests that observation as a preregistered primary on
fresh rows and initializations.

This is still a data-support experiment.  It changes neither model topology,
token identity, compiler authority, execution paths, nor frozen parent
weights.

## Reused graph

| Node | Path | Role |
| --- | --- | --- |
| Active repository | `C:\dev\_wt_scbe_atomic_stitch_20261113` | Source and receipts. |
| Read-only Clay source | `C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109` | Existing 37-field state/action generator. |
| Data selector | `python/scbe/clay_multiview_factor_coverage.py` | Existing static, random, true-factor, and shuffled-factor row-disjoint banks. |
| Standard learner | `python/scbe/clay_paired_orbit_training.py` | Unchanged 37 -> 64 -> 64 -> 5 MLP and AdamW loop. |
| Exposure auditor | `python/scbe/clay_multiview_exposure_audit.py` | Independent exact row-schedule reconstruction. |
| Headless launcher | `C:\dev\pc-health\run_headless.py` | No-window execution and redirected logs. |
| Prior result | `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-hash-specificity-v1` | Immutable `NO_SELECTION`; motivates but does not enter this run. |

```text
fresh training-only candidate pool
  -> matched view/action quotas
  -> three disjoint multi-view banks
       random natural support          [primary]
       true-factor balanced support    [control]
       shuffled-factor spread          [control]
  + static canonical support           [control]
  -> same standard MLP / optimizer / budget
  -> same-source anchor selection
  -> held-sector shifted evaluation
  -> frozen three-sector gate
  -> independent result and exposure verification
```

## Why the hash arm is not repeated

The completed specificity run measured shuffled minus hash at -0.00076
accuracy and +0.00053 stable F1, with near-even matched wins.  Repeating both
would spend one quarter of the campaign on a control already shown equivalent
at this scale.  Shuffled factor remains as the generic-spread control; true
factor remains as the semantically declared balancing control.  Static data is
the standard baseline.

## Invariants

- Four matched 30,000-row arms per held sector.
- Three legal views x 10,000 rows for every multi-view arm.
- Identical view/action quotas across multi-view arms.
- Zero selected-index and exact-feature overlap across those arms.
- No held/anchor row may enter selection or training.
- Same five model seeds in every arm/sector; initialization hashes must match.
- Same 4,800 steps, batch 192, optimizer, hidden width, and checkpoint rule.
- All results and checkpoints are written to a new append-only run directory.
- No outcome can promote, deploy, delete, grant execution authority, or
  authorize partial unfreeze.

The existing implementation and its focused tests are reused unchanged.  This
avoids introducing a new training code path after seeing the prior outcomes.

## Post-launch data-support receipt

The independent exposure auditor was extended after launch as an
observability-only change.  For each immutable bank it now records unique
feature rows, action counts, view counts, the view-by-action table, group
multiplicity, complete three-view groups, and whether a repeated group keeps or
changes its action label.  It still reads no losses, predictions, rewards, or
holdout outcomes and does not enter the trainer, sampler, optimizer, gate, or
weights.

This separates two questions that raw epoch counts conflate:

1. how often a stored row was sampled; and
2. which concept/view/factor relationships existed in the stored support.

Repeated sampling can reinforce the first.  Only the data builder can expand
the second.

