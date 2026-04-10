# Hugging Face Training Regime (SCBE-AETHERMOORE)
Last updated: 2026-04-07

This document defines the **repeatable, auditable** training loop for new SCBE model designs (a.k.a. “new model designs” / “new covenants”) published to Hugging Face.

Goal: every training run produces (1) a model artifact, (2) a traceable dataset slice, and (3) a pass/fail evaluation packet aligned to SCBE’s governance layers.

## 1) Inputs (what we train on)
- **Primary**: `training-data/` JSONL corpora (SFT + adversarial + governance scenarios).
- **Supplemental**: `notes/` (Obsidian vault) → curated exports into `training-data/` (no raw secrets).
- **Generation** (optional): Spiralverse synthetic conversation factory (when enabled) outputs signed envelopes that are converted into training records.

Minimum required fields per training record (recommended):
- `id` (stable string)
- `source` (e.g. `obsidian`, `apollo_email`, `synthetic_spiralverse`, `handcrafted`)
- `track` (e.g. `sft`, `adversarial`, `eval`)
- `tongue` (KO|AV|RU|CA|UM|DR)
- `prompt`
- `response`
- `quality` (0–1)

## 2) Outputs (what we publish)
Every run must generate:
- **Model**: Hugging Face model repo update (weights + model card update)
- **Run record**: JSON summary written to `training-runs/` (config + hashes + metrics)
- **Eval packet**: pass/fail metrics aligned to CLARA-style requirements (verifiability, tractability, composability)

## 3) Training loop (high level)
1. **Dataset selection**: choose one “track” (SFT / adversarial / eval) and one or more tongues.
2. **Scrub + normalize**: remove secrets, normalize schema, compute content hashes.
3. **Train**: run on HF Jobs (preferred) or local GPU.
4. **Evaluate**: run adversarial + governance checks (must include at least one boundary/invalid-input suite).
5. **Publish**: only publish when evaluation gates pass.

## 4) Evaluation gates (pass/fail)
These gates are designed to prevent “agreement-only” overfitting and enforce “truth under tension”.

Required gates:
- **G1: Safety/Governance**: model must not regress on prompt-injection and authority-overwrite scenarios (SCBE Layer 12/13).
- **G2: Concept bottleneck stability**: tongue projection remains stable under small perturbations (offset/mirror tests).
- **G3: Tractability**: inference latency must remain within target (microsecond–millisecond envelope for the 6D pipeline).
- **G4: Determinism under constraints**: repeated eval prompts must be within tolerance for risk scores (bounded variance).

Recommended gates:
- **G5: Cross-track generalization**: no catastrophic drop when switching tracks (SFT → adversarial).
- **G6: Refusal correctness**: refuse unsafe content without over-refusing benign content.

## 5) HF execution (recommended)
We prefer Hugging Face Jobs for repeatability and audit logs.

Suggested run metadata to record per job:
- `model_id`
- `dataset_id` + dataset commit hash
- `training_config` (lr, epochs, batch size, max seq len)
- `eval_suite_version`
- `artifacts` (paths + sha256)

## 6) Repo integration points
Common places this regime connects into code:
- `scripts/` — dataset conversion, scrubbing, training launchers
- `training-data/` — curated JSONL corpora and schemas
- `training-runs/` — run summaries, eval outputs, model lineage
- `docs/` — model cards + proposal evidence (DARPA/NSF/NIST)

## 7) Non-negotiables (security + provenance)
- Never commit raw secrets to Git.
- Never embed third-party vendor API keys in browser bundles.
- Every published model must have:
  - training data provenance statement,
  - evaluation summary,
  - known limitations / failure modes.

