# Training Data Consolidation - 2026-04-26

**Status:** fresh consolidation and bucket regularization completed locally.  
**Rule:** do not flat-merge all corpora. Merge inside purpose buckets, preserve eval/holdout, then promote each bucket through its own gate.

## Fresh Consolidation Inputs

Command:

```powershell
python scripts/system/consolidate_ai_training.py --include-kaggle --include-hf
```

Outputs:

- Inventory: `artifacts/ai_training_consolidation/latest/inventory/inventory.json`
- Plan: `artifacts/ai_training_consolidation/latest/consolidation_plan.json`
- Report: `artifacts/ai_training_consolidation/latest/REPORT.md`

## Regularized Buckets

Command:

```powershell
$inv='artifacts\ai_training_consolidation\latest\inventory\inventory.json'
foreach ($p in @('coding_model','aligned_foundations','operator_agent_bus','governance_security','research_bridge')) {
  python scripts\regularize_training_bucket.py --inventory $inv --purpose $p --output-root artifacts\training_regularized\latest
}
```

| Bucket | Train | Eval | Source files | Duplicates removed | Status |
|---|---:|---:|---:|---:|---|
| `coding_model` | 2,755 | 140 | 22 | 1,068 | Ready for gated training |
| `aligned_foundations` | 1,175 | 67 | 11 | 6,071 | Ready for gated training |
| `operator_agent_bus` | 48 | 3 | 3 | 12 | Ready, but small |
| `governance_security` | 59 | 101 | 2 | 0 | Ready, eval-heavy |
| `research_bridge` | 84 | 19 | 2 | 35 | Ready, source-grounded |

Regularized outputs live under:

- `artifacts/training_regularized/latest/coding_model/`
- `artifacts/training_regularized/latest/aligned_foundations/`
- `artifacts/training_regularized/latest/operator_agent_bus/`
- `artifacts/training_regularized/latest/governance_security/`
- `artifacts/training_regularized/latest/research_bridge/`

These are ignored artifact outputs; treat this document as the Git-visible ledger.

## Bucket Roles

`coding_model` is the main action body. It should learn code primaries, binary transport, GeoSeal command recall, EML/T operators, bijective codeflow, command lattice, and approval metrics.

`aligned_foundations` is the long-horizon instructor body. It should preserve cross-representation concepts: math, English, Sacred Tongues, binary packet framing, chemistry templates, and layer/tongue identity.

`foundation_bundle_stacks` is the final cross-stack gate surface inside `aligned_foundations`. It binds dense semantic, mathematical, statistical, resonance, chemical, and coding surfaces to binary/hex transport and a seventh binding tongue for known/unknown state separation.

`operator_agent_bus` is the tool-use dispatcher. It should learn exact commands, route state, Apollo/email collection patterns, and fail-closed operator behavior.

`governance_security` is the referee. It should learn rejection, quarantine, invalid-input handling, code governance, prompt-injection boundaries, and high-risk decision separation.

`research_bridge` is the source-grounded scout. It should learn evidence extraction, claim verification, citation discipline, and research-to-SFT conversion.

## Dual-Nodal Model Strategy

Use two cooperating model bodies rather than one premature universal merge:

| Node | Role | Candidate data | Promotion gate |
|---|---|---|---|
| Main body | Fast coding/action model | `coding_model`, selected `operator_agent_bus` | executable coding benchmark, Stage 6 regression, tool-route smoke tests |
| Helper body | Instructor/reviewer model | `aligned_foundations`, `governance_security`, `research_bridge` | cross-representation preservation, governance eval, source-grounding eval |

The merge path should be route-first, merge-later:

1. Train or reuse adapters per bucket.
2. Evaluate each adapter against frozen eval/holdout sets.
3. Register passing adapters in the adapter registry.
4. Route by task type so each adapter proves value without damaging the others.
5. Run LoRA drift/sign-conflict analysis before any weighted merge.
6. Merge only adapters that preserve at least 95 percent of their solo executable performance and pass governance regression.

This matches the "Earth and Moon" design: one model body does the primary work, the helper body stabilizes review, memory, research, and governance.

## Foundation Bundle Gate

New generated lane:

- Builder: `scripts/build_foundation_bundle_stacks_sft.py`
- Gate: `scripts/eval/score_foundation_bundle_gate.py`
- Train output: `training-data/sft/foundation_bundle_stacks_train.sft.jsonl`
- Holdout output: `training-data/sft/foundation_bundle_stacks_holdout.sft.jsonl`
- Manifest: `training-data/sft/foundation_bundle_stacks_manifest.json`

Coverage:

- Stacks: `dense_semantic`, `mathematical`, `statistical`, `resonance`, `chemical`, `coding`, `foundation_bundle`
- Actions: `validate_input`, `transform_state`, `test_receipt`, `quarantine_drift`, `merge_evidence`, `route_agent`
- Tongues: `KO`, `AV`, `RU`, `CA`, `UM`, `DR`, `SE`
- Transport: binary and hex round-trip to the same `source_text`

Gate result:

```text
foundation_bundle_stacks_v1: pass=true, records=42, train=32, holdout=10, errors=0
```

The aligned-foundations profile now includes the bundle train/holdout pair so future instructor/foundation runs consume this final cross-stack test surface.

## Current Training Run State

As of this consolidation pass:

- Kaggle `polly-auto-bijective-tongue-coder-v1`: complete; high overfit risk; needs frozen executable eval before promotion.
- Kaggle `polly-auto-coding-approval-metrics-v1`: complete; healthier SFT curve; still needs frozen eval and HF push.
- Kaggle `polly-auto-dsl-syn-v2`: still running; promotion/eval blocked until completion.
- HF Jobs from 2026-04-26 show errors/cancellations on several attempts; do not assume the HF v7 run is good until logs and output artifacts are verified.

## HF Failure Analysis

Actual HF job logs show three separate failure classes:

| Failure class | Evidence | Fix in next run |
|---|---|---|
| Remote dataset path mismatch | Job `69edbf7cd70108f37acdfd30` loaded zero records because it requested `sft/<file>` paths while most files in `issdandavis/scbe-coding-agent-sft-stage6-repair-v7` live at repo root. | New launcher preflights exact required files before GPU launch. New v8 run uses `issdandavis/scbe-training-regularized-20260426` and exact `regularized/coding_model/...` paths. |
| Unicode/charmap log failure | Earlier failed jobs emitted `charmap codec can't encode characters`, caused by non-ASCII script/log text being replayed through a Windows codepage path. | New runner keeps comments/log lines ASCII-safe and reconfigures stdout/stderr as UTF-8 with replacement. |
| Timeout / oversized broad run | One l4x1 attempt timed out after dependency install/model setup/training. The broad v7 file list mixed multiple objectives and had no eval gate. | New v8 run is narrower: regularized coding bucket only, 120 max steps, 4h timeout, eval every 30 steps. |

Adjacent reasoning: the broad v7 run was trying to make one adapter learn too many lanes at once. That increases runtime, makes failure diagnosis muddy, and risks capability interference. The corrected path is to train a focused `coding_model` adapter first, then train/helper-route aligned foundations and governance as separate bodies before any merge.

## Next Steps

1. Wait for `dsl-syn-v2` to complete, pull artifacts, and generate a training report.
2. Run frozen eval against all three relevant adapters: bijective, approval metrics, and dsl-syn.
3. Push only passing adapters to Hugging Face, excluding optimizer/checkpoint junk.
4. Rebuild adapter registry and run LoRA drift analysis.
5. Promote route-first dual-node behavior before any full weighted merge.

## New Run Prepared

New scripts:

- `scripts/hf_jobs/train_regularized_coding_v8.py`
- `scripts/hf_jobs/launch_regularized_coding_v8.py`

Dataset:

- `issdandavis/scbe-training-regularized-20260426`

Remote files:

- `regularized/coding_model/coding_model_train.regularized.jsonl`
- `regularized/coding_model/coding_model_eval.regularized.jsonl`
- `sft/foundation_bundle_stacks_train.sft.jsonl`
- `sft/foundation_bundle_stacks_holdout.sft.jsonl`
- `sft/foundation_bundle_stacks_manifest.json`
- `regularized/aligned_foundations/aligned_foundations_train.regularized.jsonl`
- `regularized/aligned_foundations/aligned_foundations_eval.regularized.jsonl`
- `regularized/aligned_foundations/aligned_foundations_manifest.json`

Preflight result:

```text
Preflight OK: issdandavis/scbe-training-regularized-20260426 has 2 required files.
```

HF Jobs launch result:

```text
402 Payment Required: pre-paid credit balance is insufficient.
```

This was a billing/credits block before job start, not a training-code failure.

Kaggle fallback:

- Round: `regularized-coding-v8`
- Kernel: `issacizrealdavis/polly-auto-regularized-coding-v8`
- Launch time: 2026-04-26
- Status after launch: `RUNNING`
- Rationale: use the free Kaggle T4 lane while HF Jobs credits are blocked.

Kaggle readiness now checks both local Kaggle dataset mirrors and the configured Hugging Face dataset repo, so HF-hosted regularized files do not falsely block terminal-driven launches.
