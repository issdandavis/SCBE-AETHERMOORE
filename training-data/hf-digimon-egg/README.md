# SCBE Polly Eggs Training Set (Draft)

This folder is the Hugging Face-facing training docs/data area for the AI egg-raising game system.

## Goal
Train batches of "Polly Eggs" that hatch into agents with:
- baseline language competence,
- Aethermore world grounding,
- GeoSeal governance reflexes,
- safe multi-agent behavior in long-running simulated worlds.

## Data Tracks
- `curriculum_v0.md` - lesson progression and competency gates.
- `decimal_drift_proof_of_process.md` - anti-spoof provenance doctrine.
- `schemas/egg_episode.schema.json` - episode record schema.
- `episodes_seed.jsonl` - starter episodes for fine-tuning and eval harnesses.

## Intended HF Layout
- Dataset repo path: `data/egg-episodes/*.jsonl`
- Card: this README + metrics and safety caveats.

## Export Strategy
Use `python training/build_polly_eggs_dataset.py` to produce deterministic JSONL artifacts for upload.

## Architecture Tie-In
- `docs/MASTER_SPEC_M4_21D.md` defines M4 ownership of dims 13-15 in canonical state.
- `training-data/hf-digimon-egg/decimal_drift_proof_of_process.md` captures process-provenance governance doctrine.
