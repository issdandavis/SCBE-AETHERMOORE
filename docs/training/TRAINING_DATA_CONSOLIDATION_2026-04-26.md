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
| `aligned_foundations` | 1,143 | 57 | 9 | 6,071 | Ready for gated training |
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

## Current Training Run State

As of this consolidation pass:

- Kaggle `polly-auto-bijective-tongue-coder-v1`: complete; high overfit risk; needs frozen executable eval before promotion.
- Kaggle `polly-auto-coding-approval-metrics-v1`: complete; healthier SFT curve; still needs frozen eval and HF push.
- Kaggle `polly-auto-dsl-syn-v2`: still running; promotion/eval blocked until completion.
- HF Jobs from 2026-04-26 show errors/cancellations on several attempts; do not assume the HF v7 run is good until logs and output artifacts are verified.

## Next Steps

1. Wait for `dsl-syn-v2` to complete, pull artifacts, and generate a training report.
2. Run frozen eval against all three relevant adapters: bijective, approval metrics, and dsl-syn.
3. Push only passing adapters to Hugging Face, excluding optimizer/checkpoint junk.
4. Rebuild adapter registry and run LoRA drift analysis.
5. Promote route-first dual-node behavior before any full weighted merge.
