# Chemistry v6 Training Run Review

Date: 2026-05-07

## Run

- Profile: `scbe-chemistry-0.5b-qlora-v6-scaffolded-marker-gate`
- HF Job: `69fc98b3317220dbbd1a5d52`
- Base model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- Dataset repo: `issdandavis/scbe-chemistry-sft`
- Adapter repo target: `issdandavis/scbe-chemistry-0.5b-qlora-v6-scaffolded-marker-gate`
- Hardware: `t4-small`
- Status: `COMPLETED`
- Adapter pushed: `false`

## Training Summary

- Train rows loaded: `1261`
- Train rows used: `1261`
- Eval rows used: `34`
- Global steps: `320`
- Trainable parameters: `1,081,344 / 495,114,112` (`0.2184%`)
- Final training loss: `0.7275`

## Gate Result

- Contract: `chemistry_verification_unseen_eval_v1`
- Scaffolded gate pass: `5/5`
- Scaffolded pass rate: `1.0`
- Must-pass prompts: all passed
- Raw model pass: `0/5`
- Raw pass rate: `0.0`

Per-prompt scaffolded result:

| Prompt | Scaffolded | Raw | Raw Missing |
|---|---:|---:|---|
| `chem_eval_ethanol_route` | pass | fail | `oxygen`, `alcohol`, `SCBE fusion` |
| `chem_eval_aspirin_route` | pass | fail | `carboxylic acid` |
| `chem_eval_pentavalent_carbon_reject` | pass | fail | `C(C)(C)(C)(C)C` |
| `chem_eval_nacl_boundary` | pass | fail | `NaCl` |
| `chem_eval_lane_boundary` | pass | fail | `queue_drain_guard`, `not a molecule` |

## Interpretation

This run proves the deterministic chemistry gate wrapper can force the contract receipt to pass. It does not prove that the raw chemistry model learned the unseen gate behavior.

The key signal is the raw score: `0/5`. The raw completions often move in the right topical area, but they miss exact contract anchors and sometimes corrupt domain terms (`carboxyllic acid`, `NA_clathrine`, `queue_drill_guard`). That is not a production-ready raw adapter.

## Decision

Do not promote or publish this adapter from this run.

Do not spend more GPU on the same scaffolded marker recipe unless the objective is explicitly "wrapper receipt generation." If the objective is raw chemistry competence, the next experiment must change the training target, not just add steps.

## Recommended Next Move

Run a zero-cost/local diagnostic before another remote dispatch:

1. Build a raw-failure repair shard from the five raw misses.
2. Add exact-anchor contrast rows:
   - correct: `carboxylic acid`
   - incorrect: `carboxyllic acid`
   - correct: `NaCl`
   - incorrect: `NA_clathrine`
   - correct: `queue_drain_guard`
   - incorrect: `queue_drill_guard`
3. Evaluate with two separate gates:
   - raw-only gate, no scaffold
   - production-shim gate, scaffold plus forbidden suppression
4. Promote only if raw pass rate moves above the current `0/5` floor.

The current working production method remains constrained decoding plus verifier gating. The training lane needs targeted raw-anchor repair before it deserves more paid compute.

## Follow-Up Artifact Built

The raw-anchor repair shard has been built locally:

- Builder: `scripts/training_data/build_chemistry_raw_anchor_repair_sft.py`
- Tests: `tests/training_data/test_build_chemistry_raw_anchor_repair_sft.py`
- Train file: `training-data/sft/chemistry_raw_anchor_repair_v1_train.sft.jsonl`
- Eval file: `training-data/sft/chemistry_raw_anchor_repair_v1_eval.sft.jsonl`
- Manifest: `training-data/sft/chemistry_raw_anchor_repair_v1_manifest.json`
- Rows: `90` train, `2` eval

This shard is intentionally narrow. It teaches exact correction of the observed v6 raw misses without claiming v6 itself succeeded as a raw model.
