# Clay frozen multi-view adapter system map — 2026-11-13

## Goal/input/output review

```text
counting rows
  -> embedding + 2-layer GRU + counting head
  -> frozen parent deed (one per fresh seed)

read-only Clay action state (37 float32 values)
  -> exact 148-byte serialization
  -> bijective 256-byte token plane
  -> equal-row support arm
       static view 0 --------------------------+
       three legal views ----------------------+--> frozen core
       three views + constant hidden carrier --+    -> matched adapter/head
       no update ------------------------------+    -> held action predictions
                                                     -> no execution authority

held diagonal source family
  -> fixed prediction ledger
  -> accuracy + macro-F1 + worst-action + per-sector outputs
  -> paired sign tests + 2 pooled-SD controls
  -> independent checkpoint replay
```

## Reused components

| Component | Role | Mutation |
| --- | --- | --- |
| `clay_paired_orbit_training.ClaySourceAdapter` | Pins and reads the existing 37-field state/action generator | read-only |
| `concept_exposure_ledger.py` v2 | Seals concept, operation, view, source, and presentation coordinates | training audit only |
| Frozen counting architecture | Preserves the previously validated input-adapter intervention | new parents; frozen after counting |
| Deterministic Clay label | Evaluation target and future compiler fallback | never learned or overridden |
| Two-slot checkpoint protocol | Resume-safe optimizer, sampler, RNG, model, and exposure state | new output only |

## New executable surfaces

- `python/scbe/clay_frozen_multiview_data.py`: exact byte-token data bridge.
- `python/scbe/clay_frozen_multiview_adapter.py`: controlled producer.
- `python/scbe/clay_frozen_multiview_replay.py`: separately declared model and
  separately implemented byte serialization, row balancing, manifest
  reconstruction, inference replay, and metric/gate comparison. It does not
  import the producer model, producer metrics, or producer data bridge.
- `scripts/research/run_clay_frozen_multiview_adapter.py`: CLI entry point.
- `scripts/research/verify_clay_frozen_multiview_adapter.py`: independent replay
  CLI. `--partial-completed` audits only atomic terminal artifacts and emits
  `PARTIAL_INDEPENDENT_REPLAY.json` without calculating a campaign verdict.
- `tests/governance/test_clay_frozen_multiview_data.py`: byte and split receipts.
- `tests/governance/test_clay_frozen_multiview_adapter.py`: frozen-surface and
  output-accounting tests.
- `tests/governance/test_clay_frozen_multiview_replay.py`: producer/replay state
  compatibility and independent metric-accounting tests.

## Boundaries

- Byte views are deterministic representations, not extra Shannon information.
- The learned adapter emits a measured proposal only.  It cannot call a tool or
  alter deterministic compiler authority.
- No selector, geometry view, or partial-unfreeze claim is under test.
- No result can promote a checkpoint under this experiment's authority.
- Partial replay is an early corruption/evaluator-drift check only. Missing
  horses remain pending, aggregate comparisons are absent, promotion is
  `NONE`, and partial unfreeze remains false.

## Live independent receipt — 2026-11-13

At campaign step 15,000/18,000 for the first multi-view horse, the partial
replay independently reconstructed the exact dataset manifest and vocabulary,
then reopened the completed parent and static-adapter artifacts:

- status: `PASS_PARTIAL_INDEPENDENT_REPLAY_NO_VERDICT`
- terminal artifacts checked: `2 / 12`
- dataset/source/vocabulary receipts: exact match
- prediction mismatches: `0` for both artifacts
- metric and counting deltas: `0.0`
- frozen core: bit-identical for both artifacts
- static held result: accuracy `0.2166666667`, macro-F1 `0.2105417755`

This verifies artifact integrity and evaluator agreement. It does not say the
multi-view intervention wins; ten terminal artifacts and all preregistered
matched-control gates are still outstanding.

