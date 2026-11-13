# Clay hash-spread specificity system map — 2026-11-13

Status: mapped before implementation or data generation.

## Capability and boundary

The preceding discovery and confirmation runs both found a global directional
lead for selection over shuffled factor signatures, but the confirmation gate
remained `NO_SELECTION`.  The missing causal control is a factor-free
deterministic hash spread.  This successor asks whether the repeated lead comes
from the shuffled factor table specifically or from generic deterministic
dispersion over a candidate pool.

This is a data-selection experiment.  It adds no model layer, tokenizer
identity, compiler authority, execution path, source authority, or checkpoint
promotion.

## Reused nodes

| Node | Exact path | Role / status |
| --- | --- | --- |
| Active repository | `C:\dev\_wt_scbe_atomic_stitch_20261113` | Clean research branch after confirmed result. |
| Read-only Clay source | `C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109` | Existing 37-field action-state provider; no writes. |
| Candidate and factor utilities | `python/scbe/clay_multiview_factor_coverage.py` | Reuse candidate collection, true factor codes, quota checks, and balanced selector. |
| Standard learner | `python/scbe/clay_paired_orbit_training.py` | Reuse unchanged 37 -> 64 -> 64 -> 5 MLP, optimizer, evaluation, and checkpoints. |
| Exposure auditor | `python/scbe/clay_multiview_exposure_audit.py` | Independent post-completion exact row-exposure receipt. |
| Headless launcher | `C:\dev\pc-health\run_headless.py` | No-window execution with redirected streams. |
| Prior immutable result | `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-shuffled-confirm-v1` | `NO_SELECTION`; never overwritten. |

The inventory receipt remains
`docs/research/CLAY_SHUFFLED_FACTOR_EXPOSURE_AUDIT_INVENTORY_20261113.json`;
the connected roots are unchanged.

## New nodes and edges

```text
training-only candidate pool (60,000 rows per legal view)
  -> exact view/action quota allocator
  -> three row-disjoint multi-view lanes
       random order
       shuffled factor-signature spread
       factor-free deterministic hash-signature spread
  + static canonical lane
  -> unchanged standard MLP and compute budget
  -> same-source anchor checkpoint selection
  -> shifted-source held evaluation
  -> preregistered sector/control gate
  -> independent exposure and checkpoint receipts
```

The genuinely new component is
`python/scbe/clay_multiview_hash_spread.py`.  For every candidate row and
signature column it hashes the exact feature-row digest, experiment seed, and
column address, then reduces the digest into the same per-column cardinality as
the factor code.  It must not use holdout rows, reward, post-outcome fields,
gradients, or model predictions.  The existing balanced selector then operates
over those hash cells without knowing their physical meaning.

## Shapes and invariants

- Four arms: `static_unique`, `multiview_random`,
  `multiview_factor_shuffled`, and `multiview_hash_spread`.
- Three multi-view arms x 10,000 rows/view fit exactly inside each 60,000-row
  candidate view while retaining unused reserve.
- All selected banks: `(30,000, 37)` float features and `(30,000,)` int labels.
- Multi-view arms share exact view/action quotas.
- Selected indices and exact feature rows are disjoint across multi-view arms.
- Hash column widths equal the corresponding shuffled-factor column widths.
- Preflight must show that the hash selector improves hash-cell entropy over
  random and shuffled-factor rows; otherwise no optimizer starts.
- Hash cells and shuffled factor cells are deterministic derived views, not new
  observations or added Shannon information.

## Controls, budget, saves, and stops

Primary: `multiview_factor_shuffled`.

Controls:

1. `multiview_hash_spread` — mechanism-specific equal-width selector control;
2. `multiview_random` — no structured selection;
3. `static_unique` — standard one-view training.

The learner, row count, steps, batch, optimizer, evaluation families, and five
initializations are matched.  The planned run remains 60 horses (`4 arms x 5
seeds x 3 sectors`) on the local GTX 1660 Ti.  Expected disk growth is below
0.5 GB, with a 20 GB launch floor.  Inputs, checkpoints, aggregate result,
gate, and exposure ledger are append-only in a new run directory.  Rollback is
non-selection: prior weights remain untouched.

Stop before training on any source hash drift, missing CUDA, capacity gate,
quota mismatch, row collision, non-finite tensor, selection leakage, or failed
hash-space intervention.  Stop after training with `NO_SELECTION` unless the
primary beats every control under the frozen sector gate.  Even a pass grants
neither promotion nor partial unfreezing.
