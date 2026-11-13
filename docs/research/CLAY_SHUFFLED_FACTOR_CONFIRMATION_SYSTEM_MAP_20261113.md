# Clay shuffled-factor confirmation system map — 2026-11-13

Status: mapped before launch; no confirmation outcome has been read.

## Reused measured path

This confirmation adds no architecture and no new source authority.  It reuses:

- active code: `C:\dev\_wt_scbe_atomic_stitch_20261113`;
- read-only Clay source:
  `C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109`;
- selector/trainer: `python/scbe/clay_multiview_factor_coverage.py`;
- headless launcher: `C:\dev\pc-health\run_headless.py`;
- completed discovery evidence:
  `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-factor-coverage-v1`.

The new immutable output is:

`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-shuffled-confirm-v1`

The side PC, sidekick ledger host, cloud storage, and OneDrive are not runtime
authorities.  OneDrive remains an indexed backup/access path only.

## Changed claim, unchanged mechanics

The discovery run registered semantic factor coverage as primary and the
shuffled-signature arm as an ablation.  The ablation unexpectedly led globally.
This run freezes that observation into a new primary hypothesis before new
data or model outcomes are read.

```text
training-only candidate pool
  -> exact view/action quota table
  -> deterministic shuffled factor signatures
  -> greedy spread selection without replacement
  -> ordinary 37 -> 64 -> 64 -> 5 MLP
  -> same-source anchor checkpoint selection
  -> shifted-source held evaluation
  -> sector-stratified matched-control gate
```

No token identity, compiler authority, action label, model width, optimizer,
holdout source, or execution path changes.  Only data/model seeds and the
predeclared primary arm change.

## Controls and hazards

| Arm | Role |
| --- | --- |
| `multiview_factor_shuffled` | Primary deterministic spread selector. |
| `multiview_random` | Direct no-selection multi-view baseline. |
| `static_unique` | Standard single-view baseline. |
| `multiview_factor` | Named-factor binding control. |

The main hazard is post-hoc promotion of the discovery winner.  It is prevented
by fresh data/model seeds, a new immutable directory, a frozen gate, all three
controls, and no promotion authority even if the mechanics gate passes.

Launch requires at least 20 GB free on C:, available CUDA, matching source
hashes, zero selected-row overlap, exact view/action quotas, valid manifests,
and no evaluation/reward fields in selection.  A failed preflight must stop
before the first optimizer step.

## Launch receipt

The confirmation launched headlessly at `2026-11-13T14:00:09Z`.

- Git commit: `32869c5ba4b5d9e98bbbcba88e0a59752a152487`.
- Configuration SHA-256:
  `c4b86e3a4fb802780bc269337a24d2db017d4a9f260403cabb5c8f681d941b08`.
- Implementation SHA-256:
  `3757789bccf65755d2cc35b7548ffe83e17e58e8ec9f592a403a2bd906ec7164`.
- Campaign receipt:
  `016157a7aa805db29257133d614178705b362a4f4fba8787bd60857e3c96bf44`.
- Capacity at launch: 26.32 GB free on C:; GPU 0 MiB used.
- Headless launcher/worker at launch: PID 27996 / PID 28884.
- Focused and related verification after the commit hook: `15 passed`; Ruff
  passed; the historical gate reproduced bit-for-bit.

The campaign record confirms primary `multiview_factor_shuffled`, controls
`static_unique`, `multiview_random`, and `multiview_factor`, new model seeds,
new data offset, CUDA execution, and false promotion/partial-unfreeze flags.

## Independent exposure-receipt seam

Mapped after launch but before implementing the auditor.  The active trainer
draws deterministic uniform-with-replacement row indices, yet its horse result
does not persist the exact per-row count vector requested by the preregistration.
The schedule is recoverable because every horse initializes a dedicated CPU
generator with `held_sector * 1,000,000 + model_seed` and then draws
`batch_size` indices for every optimizer step.

```text
CAMPAIGN.json configuration
  + hash-verified per-arm input bank
  -> independent CPU generator replay (no trainer import)
  -> exact int64 exposure-count vector
  -> count-vector SHA-256 + quantiles + effective rows
  -> immutable EXPOSURE_AUDIT.json
```

| Node | Path | Role / authority |
| --- | --- | --- |
| Active producer | `python/scbe/clay_multiview_factor_coverage.py` | Already loaded by PID 28884; remains untouched and is the only optimizer writer. |
| Sampler definition | `python/scbe/clay_paired_orbit_training.py::_sample_indices` | Measured producer behavior to reproduce independently; not imported by the auditor. |
| Existing generic replay audit | `python/scbe/training_data_coverage.py` | Reused design, but its older seed formula is not valid for this campaign. |
| New auditor | `python/scbe/clay_multiview_exposure_audit.py` | Proposed read-only reconstruction and bank-integrity check. |
| CLI | `scripts/research/audit_clay_multiview_exposure.py` | Proposed bounded command surface. |
| Immutable output | `<campaign>/EXPOSURE_AUDIT_V2.json` | Proposed append-only receipt; refuses overwrite. |

The auditor may read only campaign configuration and training-bank metadata. It
must not read model outcomes, holdout metrics, gradients, rewards, or checkpoint
selection.  It must independently verify each bank manifest, require equal row
counts across arms, reconstruct exactly `steps * batch_size` draws, and prove
that matched arms used the same positional schedule.  A missing bank, manifest
drift, schema mismatch, non-finite tensor, or existing output stops the audit.

The current confirmation requires only 15 unique schedules (`3 sectors x 5
seeds`), each with 921,600 draws and a 30,000-entry count vector.  Memory is
therefore bounded by one count vector plus one bank payload; the audit is CPU
only and does not compete for GPU training.  Unit controls must compare a tiny
replay with an explicit `torch.randint` sequence and prove fail-closed behavior
under manifest tampering.  This receipt can verify data exposure; it cannot
promote a model or authorize partial unfreezing.

Read-only inventory receipt:
`docs/research/CLAY_SHUFFLED_FACTOR_EXPOSURE_AUDIT_INVENTORY_20261113.json`.

## Exposure-auditor implementation receipt

Implemented without modifying the active producer or sampler:

- `python/scbe/clay_multiview_exposure_audit.py`;
- `scripts/research/audit_clay_multiview_exposure.py`;
- `tests/governance/test_clay_multiview_exposure_audit.py`.

Focused and neighboring regression suite: `16 passed`; Ruff passed; CLI help
launch passed.  The auditor fails closed on incomplete campaigns, altered bank
manifests, horse-lineage mismatch, and output overwrite.

The completed discovery campaign was replayed as the real-data validation. Its
v2 receipt verified 60 horse results, 15 deterministic schedules, all input
bank manifests, and exactly 921,600 row draws per horse. Every 30,000-row bank
position was observed; exposure ranged from 10 to 60 with median 31. Auditor
and sampler-reference source hashes reproduced exactly.

- Audit SHA-256:
  `f791bb97c0b1a9e289b1cbeea0841fc66d3a9b5769b153ac749bd329363ab00f`.
- Audit file SHA-256:
  `e57a4ac04d385d866b439652e0c91da1a126dbc2d182e7fd66195f454b999b7f`.
- Immutable validation output:
  `C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-factor-coverage-v1\EXPOSURE_AUDIT_V2.json`.
- Promotion authority: false; partial-unfreeze authority: false.

The live confirmation will receive its own non-overwriting v2 receipt only
after all 60 horse results and the aggregate producer result exist. Until then,
the auditor refuses to label intended schedules as observed training.
