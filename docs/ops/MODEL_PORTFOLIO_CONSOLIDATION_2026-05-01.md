# Model Portfolio Consolidation - 2026-05-01

Generated from live Hugging Face inventory plus local `config/model_training/*.json`
profiles.

Source command:

```powershell
npm run training:model-portfolio
```

Latest local board:

- `artifacts/model_portfolio/latest/model_portfolio.json`
- `artifacts/model_portfolio/latest/MODEL_PORTFOLIO.md`

## Current State

- Hugging Face model repos checked: `41`
- Active or potentially active: `20`
- Archive/reference candidates: `21`
- Local Ollama runnable models found: `3`
- Default Hugging Face cache directory: not present/empty on this machine at scan time.

Bucket counts:

- `active_specialist_adapter`: 5
- `active_training_profile`: 5
- `archive_candidate`: 11
- `foundational_reference`: 6
- `merge_candidate`: 4
- `public_interest_archive`: 10

## Core Rule

Do not merge every model together.

Only merge adapters that:

1. share a compatible base model,
2. serve the same target lane,
3. pass frozen eval gates,
4. have a clear role in a merge profile.

Old or public-interest models should be kept discoverable, but removed from the
active training plan unless they gain eval evidence.

## Target Buckets

### Promoted Full Model

Goal: one current coding model that GeoShell and paired agents should use by
default.

Current candidates:

- `issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1`
- `issdandavis/scbe-coding-agent-qwen-merged-coding-model-v2`

Action:

- Run smoke/eval gates.
- Promote one as the current default.
- Mark the other as superseded if it loses.

### Specialist Adapter Inputs

Keep these only because current merge profiles reference them:

- `issdandavis/scbe-coding-agent-qwen-online-v2`
- `issdandavis/scbe-coding-agent-qwen-binary-geoseal-v3`
- `issdandavis/scbe-coding-agent-qwen-geoseal-command-v4`
- `issdandavis/scbe-coding-agent-qwen-atomic-workflow-stage6`
- `issdandavis/scbe-coding-agent-qwen-ca-geoseal-smoke-repair-v1`

Action:

- Keep as merge inputs.
- Do not retrain blindly.
- Replace only when a newer adapter beats the frozen gate.

### Active Training Profiles

These have local profile evidence but are not all merge inputs yet:

- `issdandavis/scbe-aligned-foundations-qwen-primary`
- `issdandavis/scbe-coding-agent-qwen-full-coding-system-v8`
- `issdandavis/scbe-coding-agent-qwen-stage6-repair-v7`
- `issdandavis/scbe-coding-agent-qwen-ca-opcode-exact-repair-v2`
- `issdandavis/scbe-coding-agent-qwen-ca-geoseal-combined-repair-v3`

Action:

- Train/evaluate only through profile-specific gates.
- Add to merge profile only after passing.
- Keep records in the training ledger.

### Foundational References

These are references/assets, not merge inputs:

- `issdandavis/phdm-21d-embedding`
- `issdandavis/geoseed-network`
- `issdandavis/scbe-ops-assets`
- `issdandavis/spiralverse-ai-federated-v1`
- `SCBE-AETHER/phdm-21d-embedding`
- `SCBE-AETHER/spiralverse-ai-federated-v1`

Action:

- Keep public/reference role.
- Confirm whether org copies are mirrors or canonical.
- Do not include in coding-model merge.

### Public Interest Archive

These have downloads, so do not delete. Keep public, but remove from active
training/merge unless eval evidence appears:

- `issdandavis/polly-1`
- `issdandavis/polly-chat-qwen-0.5b`
- `issdandavis/polly-covenantal-qwen-0.5b`
- `issdandavis/polly-deep-knowledge-qwen-0.5b`
- `issdandavis/polly-scbe-7b-v2`
- `issdandavis/polly-scbe-v1`
- `issdandavis/scbe-1.5b-multi_lang_forge-lora`
- `issdandavis/scbe-bijective-tongue-coder-qwen-kaggle-v1`
- `issdandavis/scbe-coding-approval-metrics-qwen-kaggle-v1`
- `issdandavis/scbe-pivot-qwen-0.5b`

Action:

- Keep cards.
- Add archive/superseded language later if needed.
- Do not use as active defaults.

### Archive Candidates

Likely old checkpoints, smoke runs, or unreferenced experiments:

- `issdandavis/polly-focused-qwen-0.5b`
- `issdandavis/polly-r8-qwen-0.5b`
- `issdandavis/scbe-coding-agent-qwen-dsl-synthesis-v3-fast-hfjobs`
- `issdandavis/scbe-coding-agent-qwen-smoke`
- `issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-hfjobs`
- `issdandavis/scbe-governance-qwen-0.5b`
- `issdandavis/scbe-polly-chat-v1`
- `issdandavis/tongue-table-lora-brick0-v5`
- `issdandavis/tongue-table-lora-brick1-ckpt175`
- `issdandavis/tongue-table-lora-brick1-hf-v1`
- `issdandavis/tongue-table-lora-brick2-hf-v1`

Action:

- Do not delete now.
- Confirm no active profile references.
- Later tag/card as archived or superseded.

## Training Consolidation Plan

Use a three-layer system:

1. Local lane: preflight, dataset build, small eval, manifest validation.
2. Free/cheap remote lane: Colab/Kaggle/HF smoke jobs for small adapters.
3. Merge lane: HF Jobs only after adapters pass gates.

Immediate next merge target:

- Build a new merge profile only after the GeoShell pair-agent adapter is trained
  and gated.
- Candidate name: `coding-agent-qwen-merged-coding-model-v3`.
- Inputs should be the current coding merge set plus any newly proven GeoShell
  pair-agent adapter.

Local runtime posture:

- Keep the small Ollama models as local smoke-test runtimes:
  - `smollm2-ctx512:latest`
  - `smollm2:135m`
  - `qwen2.5-coder:0.5b`
- Do not delete `.ollama\models`; it is the real local model store.
- Use local runtime for cheap route/smoke checks, not as proof that a remote
  adapter is promotion-ready.

## Useful Commands

```powershell
npm run training:model-portfolio
npm run training:geoshell-pairs
python scripts/system/geoseal_coding_training_system.py profiles
python scripts/system/geoseal_coding_training_system.py plan --profile coding-agent-qwen-geoshell-pair-agent-v1 --smoke
python scripts/system/dispatch_coding_model_merge_hf_job.py plan --profile config/model_training/coding-agent-qwen-merged-coding-model-v2.json
```

## Do Not Do

- Do not merge Polly/story models into the coding model.
- Do not merge old tongue-table checkpoint bricks into the current model without
  a fresh eval.
- Do not delete public models just because they are not active.
- Do not promote a merged model from downloads or vibes; use gates.
