# Host training routes

This is the clean map for the current host lanes.

## 1. Quick-call entrypoint

- Script: `scripts/system/model_host_quickcall.ps1`

Use:

```powershell
pwsh -File scripts/system/model_host_quickcall.ps1 -Action status
pwsh -File scripts/system/model_host_quickcall.ps1 -Action routes
pwsh -File scripts/system/model_host_quickcall.ps1 -Action inventory-colab
pwsh -File scripts/system/model_host_quickcall.ps1 -Action inventory-kaggle
pwsh -File scripts/system/model_host_quickcall.ps1 -Action inventory-hf
```

## 2. Hugging Face: what it is for

Hugging Face is the main hosted lane right now.

Use it for:

- model hosting
- dataset hosting
- demo Spaces
- live model evaluation
- shipping approved training datasets

### Current model lane

- `issdandavis/scbe-pivot-qwen-0.5b`
- `issdandavis/polly-chat-qwen-0.5b`
- `issdandavis/phdm-21d-embedding`
- `issdandavis/geoseed-network`
- `SCBE-AETHER/phdm-21d-embedding`
- `SCBE-AETHER/spiralverse-ai-federated-v1`

### Current dataset lane

- `SCBE-AETHER/scbe-aethermoore-training-data`:
  primary SFT dataset
- `SCBE-AETHER/scbe-aethermoore-knowledge-base`:
  grounding / retrieval dataset
- `SCBE-AETHER/scbe-interaction-logs`:
  raw or curated interaction logs before promotion
- `SCBE-AETHER/aethermoor-rag-training-data`:
  lore / RAG training lane
- `issdandavis/scbe-red-team-benchmark`:
  adversarial eval corpus

### Current demo/app lane

- `issdandavis/SCBE-AETHERMOORE-Demo`
- `issdandavis/scbe-aethermoore-ai-hub`
- `issdandavis/scbe-red-team-sandbox`
- `issdandavis/six-tongues-protocol`

### Evaluate HF models

- Script: `scripts/eval_legacy_hf_model.py`

Use this to compare hosted text-generation models against the SCBE eval set before training or deployment.

## 3. Kaggle: what it is for

Kaggle is the remote notebook / competition lane.

Use it for:

- hosted notebooks
- experiments on Kaggle compute
- competition submissions
- secondary remote training runs

Current state:

- the new `KAGGLE_API_TOKEN` is wired locally
- the quick-call script can load it
- Codex sandbox still blocks live Kaggle network fetches with `WinError 10013`

So the practical rule is:

- use Kaggle from your normal local shell when you want live Kaggle notebook or competition work
- keep Hugging Face as the main hosted model/dataset lane
- treat `python scripts/system/kaggle_notebook_smoke.py --micro-train` as the required preflight before any long Kaggle run; if preflight fails, the run is invalid and should not start

## 4. Colab: what it is for

Colab is the flexible compute lane for training and data generation.

Use it for:

- free or low-cost LoRA / QLoRA runs
- data generation
- pivot-training experiments
- ad hoc remote GPU work

### Current notebook routes

- `notebooks/scbe_pivot_training_v2.ipynb`:
  pivot-conversation training
- `notebooks/scbe_finetune_colab.ipynb`:
  free T4 fine-tune lane
- `notebooks/colab_qlora_training.ipynb`:
  compact QLoRA lane
- `notebooks/colab_aethermoor_datagen.ipynb`:
  data generation
- `notebooks/scbe_cloud_workspace.ipynb`:
  general Colab workspace

### Kaggle guardrail

- `scripts/system/kaggle_notebook_smoke.py`
  - hard-fail preflight for Kaggle runtime, imports, dataset access, artifact write, and optional one-step micro-train
  - use this before long Kaggle jobs so queued, CPU-only, or broken-auth notebooks fail in minutes instead of hours

Catalog source:

- `scripts/system/colab_workflow_catalog.py`
- generated snapshot:
  `artifacts/host_inventory/colab_catalog.json`

## 5. How data becomes trainable datasets

### Route A: gather and audit

- Script: `scripts/cloud_kernel_data_pipeline.py`

Use this when you want to:

- gather source records
- scrub obvious secrets
- score/analyze records
- produce approved JSONL outputs
- ship to cloud dataset targets

### Route B: interaction logs to dataset

- Script: `scripts/hf_training_loop.py`

Use this when you want to:

- collect new interaction/game-session data
- write JSONL batches locally
- push approved batches to a Hugging Face dataset repo

### Route C: eval before promotion

- Script: `scripts/eval_legacy_hf_model.py`

Use this before promoting a hosted model into a demo or assistant lane.

## 6. Practical operating order

1. Inventory the lanes with `model_host_quickcall.ps1`
2. Evaluate HF models with `eval_legacy_hf_model.py`
3. Choose Colab notebook from `colab_workflow_catalog.py`
4. Consolidate trainable data with `cloud_kernel_data_pipeline.py`
5. Push approved datasets to the `SCBE-AETHER` dataset repos
6. Use Kaggle as the extra remote compute lane when you need it outside the Codex sandbox
