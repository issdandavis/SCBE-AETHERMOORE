# AI Training Consolidation Plan

Date: 2026-04-25

This is the working plan for consolidating SCBE training into specialist open-weight adapter buckets, testing those buckets independently, then merging only promoted adapters into a rounded coding/operator model.

## Convergence Goal

The model family should converge toward one practical behavior: turn messy human intent into routeable, testable, reversible SCBE work packets.

That means the training target is not "chat better." The target is:

- preserve bijective reasoning and coding as a first-class behavior,
- keep mathematics, English, Sacred Tongues full names and abbreviations, binary framing, chemistry packets, and coding primaries synchronized,
- turn ambiguous user requests into repo-grounded actions with explicit places to ask for clarity,
- choose the smallest useful agent formation, runner chain, tool route, and gate,
- keep research source-grounded with claim text, source identity, reject lists, and implementation targets,
- use local/free model pairs and triads by default, with explicit lane-change signals when crossing providers, permission tiers, phases, or language lanes,
- promote only artifacts that pass packet integrity, route consistency, code tests, benchmark checks, and release-readiness cleanup.

The compact training unit is a packet trace, receipt, or source-grounded card. Whole conversations are only raw material; they should be digested into smaller records before they become training data.

## Command

```powershell
python scripts\system\consolidate_ai_training.py
```

Outputs are written to:

- `artifacts/ai_training_consolidation/latest/inventory/inventory.json`
- `artifacts/ai_training_consolidation/latest/inventory/merge_plan.json`
- `artifacts/ai_training_consolidation/latest/consolidation_plan.json`
- `artifacts/ai_training_consolidation/latest/REPORT.md`

## Current Local Inventory

Latest local run:

- Local dataset/config/notebook files: `358`
- Local JSONL files: `153`
- Known local JSONL records: `10,737`
- Local repo notebooks: `22`

Purpose counts from the inventory:

- `aligned_foundations`: `19` files, `7,271` known records
- `coding_model`: `45` files, `2,867` known records
- `commerce_product`: `15` files, `452` known records
- `governance_security`: `19` files, `59` known records
- `operator_agent_bus`: `31` files, `88` known records
- `research_bridge`: `17` files, `0` known records
- `story_lore`: `62` files, `0` known records
- `uncategorized`: `150` files, `206` known records

## Specialist Buckets

The first pass regularized these buckets:

- `coding_primary_specialist`: `1,775` train, `34` eval, base `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- `aligned_foundations_specialist`: `1,143` train, `57` eval, base `Qwen/Qwen2.5-7B-Instruct`
- `governance_security_specialist`: `59` train, `0` eval, base `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- `operator_agent_bus_specialist`: blocked, no schema-ready train records
- `source_grounded_research_specialist`: blocked, no schema-ready train records

Blocked does not mean useless. It means those records need a schema adapter or Git LFS pull before they can be used safely.

## Training Ladder

1. Train specialist LoRA adapters with SFT.
2. Test each specialist on its own eval gate.
3. Use DPO only where chosen/rejected preference pairs exist.
4. Use GRPO only where rewards are mechanically verifiable, such as code tests, command recall, or governance decisions.
5. Merge promoted adapters with weighted adapter merge.
6. Run final smoke, coding benchmark, governance regression, and local GGUF export only after the merged model beats the base model.

## Active Training Lanes

- `aligned_foundations`: shared substrate learning across mathematics, English, Sacred Tongues, binary transport, chemistry, and coding.
- `stage5_command_harmony`: current GeoSeal command recall, analog action compression, provider lane signaling, and runtime-vs-structural boundaries.
- `stage6_coding_repair`: executable repair vocabulary and constrained code-output behavior under frozen must-pass gates.
- `agentic_packet_traces`: compact runner-chain and provider-pair behavior from executable packet traces instead of full conversations.
- `source_grounded_research`: source finding, falsifiable claims, and research-to-implementation routing.

## Promotion Gates

- G1 packet integrity: schema, hashes, and bijective round-trip evidence survive.
- G2 route and lane signaling: provider, permission, phase, or language lane changes fail closed without a signal.
- G3 executable coding: coding specialists pass focused repo tests or frozen executable contracts.
- G4 cross-lane alignment: aligned-foundations records preserve concept identity across every synchronized face.
- G5 source and research grounding: research records carry source identity, falsifiable claim text, and a routeable target.
- G6 release readiness: merged outputs pass benchmark/readiness checks and keep generated churn out of release commits.

## Merge Boundary

Do not flat-merge every dataset.

The final rounded model should be assembled from promoted adapters, not raw mixed data. The current merge profile is:

- `config/model_training/coding-agent-qwen-merged-coding-model.json`
- output repo target: `issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1`

## Immediate Fixes Before Bigger Training

- Pull or recover Git LFS pointer corpora before counting them as usable.
- Build adapters for `operator_agent_bus` from Apollo, browser, CLI, and agent-bus traces.
- Build source-grounded research records from `research_bridge_smoke` with explicit source identity and falsifiable claim text.
- Add frozen eval for governance/security before promotion.
- Keep story/lore out of the coding model unless a record is explicitly code-paired and passes code-lane validation.

