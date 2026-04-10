# HuggingFace Training Guide — SCBE-AETHERMOORE

## 1. Setup

### Token

Your HF token lives at `HF_TOKEN` (user environment variable). To update it:

```powershell
# Temporary (this session only)
$env:HF_TOKEN = "hf_YOUR_TOKEN"

# Permanent (survives restarts)
[System.Environment]::SetEnvironmentVariable("HF_TOKEN", "hf_YOUR_TOKEN", "User")
```

Get tokens at: https://huggingface.co/settings/tokens

Required scopes: `repo.content.read`, `repo.write`, `inference.serverless.write`, `inference.endpoints.infer.write`

### Verify

```powershell
python -c "from huggingface_hub import whoami; print(whoami()['name'])"
# Should print: issdandavis
```

---

## 2. Your Repositories on HuggingFace

### Models
| Repo | Purpose |
|------|---------|
| `issdandavis/phdm-21d-embedding` | PHDM 21D embedding model (backup) |
| `issdandavis/phdm-21d-embedding-next` | PHDM embedding model (primary) |
| `issdandavis/spiralverse-ai-federated-v1` | Full codebase mirror (weekly sync) |
| `issdandavis/polly-chat-qwen-0.5b` | Polly chatbot (Qwen 0.5B fine-tune) |

### Datasets
| Repo | Purpose |
|------|---------|
| `issdandavis/scbe-aethermoore-training-data` | Primary SFT training data |
| `issdandavis/scbe-aethermoore-knowledge-base` | Knowledge base |
| `issdandavis/scbe-aethermoore-datasets` | Backup/mirror |

### Org
| Link | What |
|------|------|
| https://huggingface.co/issdandavis | Your profile |
| https://huggingface.co/SCBE-AETHER | SCBE org |

---

## 3. Training Data Pipeline

Training data flows through a governed pipeline before it ever touches a model:

```
Raw sources (code, docs, game sessions, scripts)
        |
        v
[1] build_training_ingestion_pool.py    -- consolidate from all sources
        |
        v
[2] auto_ledger.py                      -- quality audit + 21D embedding + tongue tag + curriculum level
        |
        v
[3] training_auditor.py                 -- ALLOW / QUARANTINE gate
        |
        v
[4] programmatic_hf_training.py         -- package + publish + train
        |
        v
    HuggingFace Hub
```

### Where training data lives locally

| Path | What | Size |
|------|------|------|
| `training/sft_records/sft_combined.jsonl` | All merged SFT records | ~215 MB |
| `training/sft_records/sft_ingestion_pool.jsonl` | Governed intake pool | ~14 MB |
| `training/ledgered/sft_ledgered_clean.jsonl` | Audited clean data | ~22 MB |
| `training/ledgered/sft_foundation.jsonl` | Foundation curriculum | ~7.5 MB |
| `training/ledgered/sft_practitioner.jsonl` | Practitioner curriculum | ~3.2 MB |
| `training/ledgered/sft_specialist.jsonl` | Specialist curriculum | ~4 MB |
| `training/ledgered/sft_architect.jsonl` | Architect curriculum | ~5.3 MB |
| `training/ledgered/sft_master.jsonl` | Master curriculum | ~1.8 MB |
| `training/ledgered/sft_tongue_KO.jsonl` | KO (Command) tongue | ~12.4 MB |
| `training/ledgered/sft_tongue_AV.jsonl` | AV (Transport) tongue | ~3.7 MB |
| `training/ledgered/sft_tongue_CA.jsonl` | CA (Compute) tongue | ~1.9 MB |
| `training/ledgered/sft_tongue_RU.jsonl` | RU (Rules) tongue | ~963 KB |
| `training/ledgered/sft_tongue_UM.jsonl` | UM (Understand) tongue | ~1.8 MB |
| `training/ledgered/sft_tongue_DR.jsonl` | DR (Structure) tongue | ~1.1 MB |
| `training-data/sft/` | Individual generator outputs | 30+ files |
| `training/runs/huggingface/` | Past training run artifacts | 12+ runs |

### SFT record format

Every record follows this schema:

```json
{
  "instruction": "What is the harmonic wall function?",
  "output": "H(d, pd) = 1/(1 + phi * d_H + 2 * pd) where phi = golden ratio...",
  "layer": "L3",
  "tongue": "CA",
  "curriculum": "practitioner",
  "phdm_21d": [0.1, 0.3, ...],
  "source": "synesthesia_cross_modal",
  "timestamp": "2026-04-05T..."
}
```

---

## 4. How to Train

### Option A: One-command governed pipeline (recommended)

```powershell
python scripts/programmatic_hf_training.py
```

This does everything: refresh ingestion pool, rebuild ledgered clean dataset, audit, package, publish to Hub, and optionally train. It's the master orchestrator.

### Option B: Train a governance classifier from SFT + adversarial data

```powershell
python scripts/unified_training_pipeline.py
```

Pulls 40K adversarial prompts from Kaggle, merges with your SCBE SFT data, fine-tunes a governance classifier, evaluates against benchmark attacks, and pushes to HF.

### Option C: Long-run local training with growth monitoring

```powershell
python scripts/train_hf_longrun_placeholder.py ^
  --dataset-repo issdandavis/scbe-aethermoore-training-data ^
  --model-repo issdandavis/phdm-21d-embedding-next ^
  --duration-hours 8
```

Trains a hashed-embedding softmax model, monitors growth across epochs, and uploads artifacts to your model repo.

### Option D: Multi-cloud overnight training

```powershell
# Dry run (see what would happen)
python scripts/long_run_training_bootstrap.py --plan

# Real execution (pick a provider)
python scripts/long_run_training_bootstrap.py --execute --provider huggingface
```

Supports: `huggingface`, `vertex`, `kubernetes`, `sagemaker`

### Option E: Game-session SFT collection

```powershell
python scripts/hf_training_loop.py
```

Runs the Aethermoor game headless with AI autopilot. Every player choice, battle, dialogue, and tower clear becomes an SFT pair governed through L7/L9/L12/L14 before recording.

---

## 5. Data Generation (Making New Training Records)

These scripts generate SFT records from different angles:

| Script | What it generates | Records |
|--------|-------------------|---------|
| `scripts/generate_synesthesia_sft.py` | Cross-modal reconstruction under degraded input | 200 |
| `scripts/generate_attention_residuals_sft.py` | AttnRes depth-attention training pairs | 15 |
| `scripts/generate_fu_dataset.py` | Functional Unit activation pairs | varies |
| `scripts/generate_pazaak_intent_pairs.py` | Internal evaluation (agency vs mimicry) | varies |
| `scripts/generate_quaternary_sft.py` | L0 quaternary substrate pairs | varies |
| `scripts/generate_autocorrection_pairs.py` | Autocorrection behavior pairs | varies |
| `scripts/generate_skill_tree_manhwa_pairs.py` | Skill tree progression pairs | varies |
| `scripts/generate_translateral_code_sft.py` | Cross-language code translation | varies |
| `scripts/canonicalize_code_atoms.py` | Code atom canonicalization | varies |

Run any generator:

```powershell
python scripts/generate_synesthesia_sft.py
```

Output lands in `training-data/sft/`. Then run the pipeline (Option A) to ingest, audit, and publish.

---

## 6. Publishing Data to HuggingFace

### Push a single file

```powershell
python scripts/push_ai_ide_sft_to_hf.py
```

### Push the full governed dataset

```powershell
python scripts/programmatic_hf_training.py
```

### Push from system tools

```powershell
python scripts/system/publish_training_dataset_repo.py
```

### Manual upload (any file)

```python
from huggingface_hub import HfApi
api = HfApi()
api.upload_file(
    path_or_fileobj="training/ledgered/sft_ledgered_clean.jsonl",
    path_in_repo="sft_ledgered_clean.jsonl",
    repo_id="issdandavis/scbe-aethermoore-training-data",
    repo_type="dataset"
)
```

---

## 7. Automated Workflows (GitHub Actions)

These run automatically:

| Workflow | Schedule | What |
|----------|----------|------|
| `huggingface-sync.yml` | Weekly Mon 6 UTC | Mirrors codebase to spiralverse-ai-federated-v1 |
| `programmatic-hf-training.yml` | Daily 8:15 UTC | Full pipeline: ingest, audit, publish, train |
| `nightly-multicloud-training.yml` | Weekly Sun 2 UTC | Multi-cloud training orchestration |

All require `HF_TOKEN` as a GitHub Actions secret. Set it at:
`github.com/issdandavis/SCBE-AETHERMOORE/settings/secrets/actions`

---

## 8. Quality Pipeline (auto_ledger.py)

Every record passes through 5 stages before it's training-ready:

### Stage 1: Quality Audit
- Instruction: 10-2000 chars
- Output: 5-10000 chars
- Records outside bounds are rejected

### Stage 2: 21D PHDM Embedding
- Each record gets a 21-dimensional embedding vector for semantic categorization

### Stage 3: Sacred Tongue Tagging
Assigned by keyword matching:
- **KO** (Command): intent, control, flow, route, orchestrate
- **AV** (Transport): api, message, metadata, send, receive
- **RU** (Rules): policy, bind, validate, enforce, permission
- **CA** (Compute): code, generate, build, optimize
- **UM** (Understand): model, knowledge, represent, embed
- **DR** (Structure): document, organize, design, architecture

### Stage 4: Curriculum Level
- **Foundation**: Basic Q&A, simple governance
- **Practitioner**: Multi-step tasks, tongue encoding
- **Specialist**: Domain-specific (crypto, browser, lore)
- **Architect**: System-level decisions, cross-domain
- **Master**: Novel situations, creative synthesis

### Stage 5: Clean JSONL Output
Split by curriculum level AND by tongue for targeted training runs.

---

## 9. Checking Past Training Runs

```powershell
ls training/runs/huggingface/
```

Each run folder contains:
- `hf_training_metrics.json` — loss, accuracy, epochs
- `label_map.json` — class labels used
- `growth_monitor_report.json` — accuracy deltas across epochs
- `model_weights.npz` — trained weights
- `training_growth_summary.md` — human-readable summary

---

## 10. Model Evaluation

```powershell
# Evaluate latest model
python scripts/eval_legacy_hf_model.py

# Run legacy eval suite
python scripts/run_legacy_hf_eval.py
```

Current benchmark: F1 = 0.813 (semantic projector vs 0.481 baseline)

---

## 11. Updating Model Cards

```powershell
python scripts/update_hf_model_cards.py
```

Updates the README.md on your HuggingFace model repos with current metrics and architecture info.

---

## 12. Quick Reference

```powershell
# Am I logged in?
python -c "from huggingface_hub import whoami; print(whoami()['name'])"

# Generate new training data
python scripts/generate_synesthesia_sft.py

# Run full governed pipeline (ingest, audit, publish, train)
python scripts/programmatic_hf_training.py

# Push dataset manually
python scripts/push_ai_ide_sft_to_hf.py

# 8-hour overnight training run
python scripts/train_hf_longrun_placeholder.py --duration-hours 8

# Check training history
ls training/runs/huggingface/
```

---

## 13. Troubleshooting

**"No token found"**: Run `python -c "from huggingface_hub import login; login(token='hf_...')"` or set `$env:HF_TOKEN`

**"401 Unauthorized"**: Token expired or missing scopes. Regenerate at https://huggingface.co/settings/tokens with `repo.write` + `inference.serverless.write`

**"Repository not found"**: Check repo name spelling. Your namespace is `issdandavis/`.

**Training hangs**: Check `training/runs/huggingface/` for the latest run's `growth_monitor_report.json` to see where it stalled.

**"QUARANTINE" blocking publish**: The auditor flagged records. Either fix them or pass `--allow-quarantine` (not recommended for production).
