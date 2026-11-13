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
