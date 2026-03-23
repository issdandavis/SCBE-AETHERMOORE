# HF Training Lane for SCBE Agents

## Purpose

This note defines a practical Hugging Face training lane for SCBE agent and NPC style work.

The goal is not to train "the whole SCBE system" into one model. The goal is to keep law, routing, provenance, and governance deterministic while using Hugging Face for the bounded parts that benefit from learned behavior:

- agent and NPC voice/style consistency
- response ranking and preference shaping
- lightweight embedding and retrieval heads for routing and curation

The current portfolio map already positions `phdm-21d-embedding` as the model/data research lane. In this repo, that should be treated as the first HF-facing training surface, not as a license to collapse governance into model weights.

## Repo Surfaces To Anchor On

### Core training and dataset surfaces

- `phdm-21d-embedding`
  - Called out in `docs/operations/2026-03-16-github-portfolio-map.md` as the active training/model/data research lane.
- `training-data/README.md`
  - Canonical shape for SCBE training rows: `prompt`, `response`, `metadata`.
- `training-data/npc_roundtable_sessions/README.md`
  - NPC dataset landing zone produced by `scripts/system/polly_npc_roundtable_builder.py`.
- `training-data/hf-digimon-egg/README.md`
  - Existing HF-facing pattern: deterministic JSONL export, explicit dataset layout, and safety caveats.
- `training-data/hf-digimon-egg/decimal_drift_proof_of_process.md`
  - Provenance doctrine: data must be value-correct and process-valid.

### Existing builder, export, and training scripts

- `scripts/system/run_polly_npc_roundtable.ps1`
  - Builds lore-grounded NPC cards plus SFT and DPO rows.
- `scripts/system/run_polly_cross_model_bootstrap.ps1`
  - Funnel merge, audit, and training bootstrap lane.
- `scripts/train_hf_longrun_placeholder.py`
  - Current HF training driver with deterministic dedup, local artifact capture, and optional push to Hub.
- `scripts/run_hf_training_and_monitor.ps1`
  - Wraps the HF training driver and defaults the model repo to `issdandavis/phdm-21d-embedding`.
- `scripts/push_jsonl_dataset.py`
  - Governed dataset push path with explicit quarantine behavior.
- `scripts/push_to_hf.py`
  - Richer dataset push path with train/test split and dataset card upload.
- `scripts/convert_to_sft.py`
  - Wrapper for converting raw JSONL or Notion exports into SCBE SFT format.
- `scripts/scbe_ai_kernel_wrapper.py`
  - Emits governance artifacts and HF training rows from bounded, defensive-mesh-reviewed jobs.

### Existing HF-adjacent skills

- `hugging-face-model-trainer`
- `hugging-face-datasets`
- `hf-publish-workflow`
- `notion-hf-curator`

Those skills are the operational lane around the repo scripts. The scripts define the local truth; the skills define repeatable execution patterns.

## What To Train First

### 1. Train the deterministic routing and embedding lane first

Start with `phdm-21d-embedding` and keep the task narrow:

- classify SCBE records by stable labels such as `category`, `track`, `source_type`, or event type
- support retrieval and routing across agent/NPC datasets
- improve curation and head selection before style tuning

Why first:

- the repo already has a runnable lane for this in `scripts/train_hf_longrun_placeholder.py`
- `scripts/run_hf_training_and_monitor.ps1` already points to `issdandavis/phdm-21d-embedding`
- the current trainer uses deterministic dedup by `sha256(label::text)` and writes auditable metrics into `training/runs/huggingface/<run_id>`

This lane should stay bounded and boring. It is closer to "index the system cleanly" than "teach a model to improvise."

### 2. Train NPC style through SFT after the routing lane is stable

Use the roundtable outputs as the first learned style surface:

- `training-data/npc_roundtable_sessions/npc_cards.jsonl`
- `training-data/npc_roundtable_sessions/npc_roundtable_sft.jsonl`
- `training-data/npc_roundtable_sessions/npc_registry.json`

This is the right first style target because it is:

- lore-grounded
- already separated from the full repo corpus
- aligned to concrete NPC identities instead of generic SCBE voice

Train for:

- voice consistency
- character-specific phrasing
- stable role behavior under canon constraints

Do not train governance decisions into this lane. Style models should operate inside governance, not replace it.

### 3. Use DPO or preference tuning only after SFT is clean

The roundtable lane already produces:

- `training-data/npc_roundtable_sessions/npc_roundtable_dpo.jsonl`

Use that only after:

- SFT outputs are canon-stable
- the audit lane is clean
- you have a known-good evaluation set for drift, lore fidelity, and refusal behavior

DPO is for response ranking and preference shaping. It is not the first place to solve missing canon or noisy source data.

## Practical Data Flow

### Step 1. Build bounded source data

For NPC style work, start with the roundtable lane:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_npc_roundtable.ps1 -RunAudit
```

This gives a small, named, inspectable dataset with cards, SFT rows, DPO rows, and a registry.

For broader system data, use the cross-model bootstrap lane:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer dry-run
```

That lane already builds funnel data, runs `scripts/training_auditor.py`, and stops on quarantine unless explicitly overridden.

### Step 2. Normalize or convert to SCBE SFT shape

Use `scripts/convert_to_sft.py` when raw exports are still page-like or mixed-format.

The normalized contract should remain:

- `prompt`
- `response`
- `metadata`

Within `metadata`, keep explicit fields such as:

- `track`
- `source_type`
- `quality`
- NPC or speaker identity
- canon/lore tags
- run or source provenance

### Step 3. Keep a deterministic export layer before Hub upload

Use the `training-data/hf-digimon-egg` pattern as the baseline:

- deterministic JSONL artifacts
- explicit schema or data contract
- a dataset card that explains safety and provenance
- proof-of-process notes alongside the data

This is where bounded-AI discipline matters. The exported dataset should be reproducible from source inputs plus the build scripts. If the lane cannot recreate the JSONL, it is not ready to publish.

### Step 4. Push curated datasets to HF

Two push paths exist now:

- `scripts/push_jsonl_dataset.py`
  - simple governed upload path
  - quarantines on missing token, missing files, or invalid repo ID
  - expects `HUGGINGFACE_TOKEN`
- `scripts/push_to_hf.py`
  - richer dataset push with split creation and README upload
  - expects `HF_TOKEN`

Operational note:

The token name mismatch is a lane hazard. Until that is unified, document which script was used in each run record.

### Step 5. Train into a timestamped run directory

Use the existing wrapper for the `phdm-21d-embedding` lane:

```powershell
python scripts/run_hf_training_and_monitor.ps1
```

or run the trainer directly when a custom plan is needed:

```powershell
python scripts/train_hf_longrun_placeholder.py `
  --dataset-repo issdandavis/scbe-aethermoore-training-data `
  --model-repo issdandavis/phdm-21d-embedding `
  --run-dir training/runs/huggingface/<run_id>
```

The current trainer already captures:

- `label_map.json`
- `model_weights.npz`
- `hf_training_metrics.json`
- `training_growth_summary.md`

Those should be treated as the minimum run packet, not optional extras.

### Step 6. Feed governed machine-generated rows through the defensive mesh

If the lane is generating training rows from agent jobs, use `scripts/scbe_ai_kernel_wrapper.py` rather than ad hoc scraping or copy-paste corpora.

That wrapper:

- gates tasks through the defensive mesh
- records `ALLOW`, `DENY`, or `QUARANTINE` style decisions around the task outputs
- appends HF rows in a controlled way
- writes a run summary that includes `hf_rows_written` and `hf_output`

This is the bounded-AI pattern in practice: use models to produce candidate material, but only promote rows that passed deterministic review gates.

## What Must Stay Deterministic

These parts should remain code-and-data governed, not learned:

- `ALLOW`, `DENY`, `QUARANTINE` gate behavior
- safety thresholds and quarantine rules
- provenance and proof-of-process metadata
- dataset manifests and run manifests
- record dedup rules
- canonical label sets for routing and track assignment
- model promotion criteria
- exact run IDs, timestamps, and artifact locations

This is consistent with the SCBE architecture material:

- governance returns a bounded decision set
- the src `symphonic_cipher` surface uses `H(d,pd) = 1 / (1 + d + 2*pd)` as a bounded safety score
- deterministic logs and replay matter at the system boundary

If a learned model is allowed to redefine the gate, the lane has stopped being SCBE and turned into ordinary prompt-time guesswork.

## What Can Be Learned

These parts are good first candidates for HF fine-tuning:

- NPC speaking style
- tone and cadence per role
- lore-grounded response ranking
- retrieval embeddings for routing and curation
- safe preference tuning on already-governed candidate responses

The safe pattern is:

1. deterministic law and routing boundary
2. curated dataset build
3. learned style layer inside the boundary
4. deterministic evaluation and promotion back outside the boundary

## Run Logging and Curation Rules

Every promoted run should have a compact packet under `training/runs/huggingface/<run_id>` with:

- trainer arguments
- dataset repo ID and dataset snapshot reference
- model repo ID
- source files or manifest used for the run
- `hf_training_metrics.json`
- `training_growth_summary.md`
- evaluation notes for lore fidelity, style stability, and refusal behavior
- promotion decision: `promote`, `hold`, or `quarantine`

Recommended curation order:

1. Keep a small golden set of NPC prompts and expected behavior for each major character lane.
2. Evaluate new runs against the same set before promotion.
3. Promote only one change class at a time:
   - routing
   - SFT style
   - DPO preference
4. Record why a run was promoted, not just that it trained successfully.

Training success is not deployment readiness. Growth curves alone are not enough.

## Recommended First Operating Sequence

Use this order for the next clean HF lane:

1. Build `npc_roundtable_sessions` with audit on.
2. Run cross-model bootstrap in `dry-run` mode.
3. Publish only the curated NPC SFT subset to a dataset repo with a dataset card.
4. Run `phdm-21d-embedding` training first for routing and retrieval.
5. After the routing lane is stable, train a small NPC style SFT lane.
6. Add DPO only when you have stable eval prompts and clear preference deltas.
7. Keep governance decisions, quarantine thresholds, and promotion rules outside the model.

## Bottom Line

SCBE should use Hugging Face as a bounded training lane, not as a replacement for the bounded-AI architecture.

Train the smallest useful thing first:

- embeddings and routing in `phdm-21d-embedding`
- NPC style via roundtable SFT
- preference tuning only after style is stable

Keep the law deterministic, keep the provenance auditable, and let the learned layer operate only where style and ranking actually benefit from learning.
