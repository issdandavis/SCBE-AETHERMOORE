---
title: "Session 2026-04-05: System Review, Free Models, AetherSearch, Polly Training"
date: 2026-04-05
tags: [session, code-review, training, search, infrastructure, models, polly]
status: complete
tongue_profile: [RU, CA, DR]
---

# Session 2026-04-05 — Full Cross-Referenced Log

## Session Summary

1. Full system review of audio + chromatic + quantum + TTS pipeline (10 bugs fixed)
2. GPT Pro budget exhausted — identified free open-weight model replacements
3. Hardware assessment: Python 3.14 blocks CUDA, need 3.12 venv
4. Algolia research + $10K startup credits eligibility
5. AetherSearch architecture planned (SCBE-native search engine)
6. Polly training run prioritized for next session
7. Parallel session: 6,008 TS tests passed, polyhedral node generator P1-P3 in progress

## Documents Created This Session

| File | What | Cross-References |
|------|------|-----------------|
| `notes/session-2026-04-05-system-review-and-search.md` | Detailed session notes with all 10 bug fixes | Links to all modified source files |
| `notes/aethersearch-architecture.md` | AetherSearch full architecture plan | Links to `docs/ARCHITECTURE.md`, existing SCBE components |
| `notes/free-models-inventory.md` | All free models with HYDRA agent mapping | Links to training scripts, HF repos |
| `notes/pytorch-cuda-build-and-training-plan.md` | CUDA setup + wheel building guide | Links to training-data/sft/ corpus |
| `notes/sessions/2026-04-05-system-review-session.md` | This file — cross-referenced catalog |

## Cross-Reference: Files Modified

### Source Code (bugs fixed)

| Modified File | Related Docs | Related Tests |
|---------------|-------------|---------------|
| `src/crypto/choral_render.py` | `docs/specs/` (L14 Audio Axis) | `tests/harmonic/audioAxis.test.ts` |
| `src/crypto/speech_render_plan.py` | `docs/SACRED_TONGUE_SPECTRAL_MAP.md` | TTS integration tests |
| `src/crypto/gallery_chromatics.py` | `notes/round-table/2026-03-20-*` (color research) | Color field unit tests |
| `src/crypto/quantum_frequency_bundle.py` | `docs/SCBE_COMPLETE_SYSTEM.md`, `docs/specs/CANONICAL_FORMULA_REGISTRY.md` | `tests/crypto/` |
| `src/audio/gallery_sonifier.py` | `docs/specs/` (gallery ambient spec) | Audio pipeline tests |
| `scripts/tts_chunk_render.py` | NEW — `notes/aethersearch-architecture.md` | Manual test (run with --text) |
| `scripts/generate_quantum_frequency_sft.py` | `docs/guides/TRAINING_HUGGINGFACE_AND_PRIVACY.md` | Output: `training-data/sft/quantum_frequency_bundles_sft.jsonl` |
| `training/snake/pipeline.py` | Snake Pipeline plan (in Claude plan file) | `training-data/sft/snake_pipeline.jsonl` |

### Cross-Reference: Existing Architecture Docs

| Topic | Primary Doc | Notes Reference | Code |
|-------|------------|-----------------|------|
| 14-Layer Pipeline | `docs/SCBE_FULL_SYSTEM_LAYER_MAP.md` | `notes/theory/2026-04-01-formula-inventory.md` | `src/harmonic/pipeline14.ts` |
| Sacred Tongues | `docs/LANGUES_WEIGHTING_SYSTEM.md` | `notes/sphere-grid/` (full sphere grid) | `src/tokenizer/` |
| Gallery Chromatics | `docs/specs/` | `notes/round-table/2026-03-20-*` | `src/crypto/gallery_chromatics.py` |
| Dead Tones | Memory: `discovery_gallery_ambient_dead_tones.md` | `notes/theory/` | `src/crypto/quantum_frequency_bundle.py:556-654` |
| Polyhedral Friction | Memory: `discovery_polyhedral_friction_training.md` | `notes/theory/` | `src/symphonic_cipher/scbe_aethermoore/polyhedral_flow.py` |
| Harmonic Scaling | `docs/specs/CANONICAL_FORMULA_REGISTRY.md` | `notes/theory/2026-04-01-harmonic-training-complete-synthesis.md` | `src/symphonic_cipher/scbe_aethermoore/harmonic_scaling_law.py` |
| HYDRA Agents | `docs/hydra/ARCHITECTURE.md` | `notes/free-models-inventory.md` (new model mapping) | `src/fleet/`, `spaces/mesh-foundry/` |
| Polly | `docs/POLLY_PADS_ARCHITECTURE.md` | `notes/sessions/2026-04-01-mega-session.md` | `src/symphonic_cipher/scbe_aethermoore/concept_blocks/cstm/` |
| Sacred Eggs | `docs/01-architecture/sacred-eggs-systems-model.md` | Memory: `discovery_sacred_egg_developmental_psychology.md` | `src/geoseed/` |
| Snake Pipeline | Claude plan file | `notes/theory/2026-04-05-training-pair-taxonomy.md` | `training/snake/pipeline.py` (16 stages) |
| AetherSearch | `notes/aethersearch-architecture.md` (NEW) | `docs/AETHERBROWSE_BLUEPRINT.md` (browser, not search — different) | Phase 1: Meilisearch + SCBE enrichment |
| Polly Training | `notes/pytorch-cuda-build-and-training-plan.md` (NEW) | `docs/guides/TRAINING_HUGGINGFACE_AND_PRIVACY.md` | `scripts/hf_training_loop.py` |

### Cross-Reference: Training Data Corpus

| Dataset | Records | Size | Generator | Status |
|---------|---------|------|-----------|--------|
| `training-data/sft/quantum_frequency_bundles_sft.jsonl` | 11,389 | 183MB | `scripts/generate_quantum_frequency_sft.py` | Ready (includes color_field) |
| `training-data/sft/snake_pipeline.jsonl` | varies | - | `training/snake/pipeline.py` | Ready (16-stage) |
| `training-data/sft/codex_skill_tutorials_all_tiers.jsonl` | - | - | `scripts/generate_codex_skill_tutorials_sft.py` | Exists |
| `training-data/sft/attention_residuals_sft.jsonl` | - | - | `scripts/generate_attention_residuals_sft.py` | Exists |
| `training-data/sft/cutting_edge_research_*.jsonl` | - | - | `scripts/generate_cutting_edge_*.py` | Multiple files |
| `training-data/polly_training_merged.jsonl.gz` | - | - | Previous runs | Compressed, needs review |
| `training-data/mega_ingest_sft.jsonl.gz` | - | - | Previous runs | Compressed |

### Cross-Reference: Existing Session Notes

| Session | Key Outcomes | Carries Into This Session |
|---------|-------------|--------------------------|
| `2026-03-22-session.md` | Code scanning, storage compaction, HF training lane | Training infrastructure foundation |
| `2026-03-29-30-mega-session.md` | Mega build session, submodule backup | Repo structure for tonight's fixes |
| `2026-03-31-nightly-roundup-publish.md` | Pump architecture, 233K dataset, binary-first stack | Training corpus used tonight |
| `2026-04-01-mega-session.md` | Polly pad, personality matrix, training persistence | Polly training run priority |
| **2026-04-05 (this)** | System review, free models, AetherSearch, CUDA plan | Next: Polly training + AetherSearch Phase 1 |

### Cross-Reference: Theory Notes

| Theory Note | Relevance to Tonight |
|------------|---------------------|
| `theory/2026-04-01-formula-inventory.md` | Verified formulas match code in system review |
| `theory/2026-04-01-harmonic-training-complete-synthesis.md` | Training architecture for free model fine-tuning |
| `theory/2026-04-05-training-pair-taxonomy.md` | ~21 pair types available for Polly training |
| `theory/2026-04-01-personality-progression-matrix.md` | HYDRA agent mapping to free models |

### Cross-Reference: Round Table Research

| Round Table Note | Relevance |
|-----------------|-----------|
| `round-table/2026-03-19-phase-tunnel-resonance-finding.md` | Phase tunnel validated — informs mirror refractor (Stage 3.5) |
| `round-table/2026-03-20-phase-tunnel-tongue-mapping.md` | Tongue-to-phase mapping used in color field |
| `round-table/2026-03-22-professional-repo-cleanup-and-hf-training-lane.md` | HF training lane = where Polly training goes |
| `round-table/2026-03-29-bible-multi-geometry-historical-memory-system.md` | Multi-geometry approach validates AetherSearch concept |

## Next Session Priority Queue

1. **Create Python 3.12 venv with CUDA PyTorch** (5 min)
2. **Run Polly training** on Qwen2.5-0.5B with SCBE corpus
3. **Install Meilisearch** for website search (AetherSearch Phase 1)
4. **Apply for Algolia $10K credits** (backup search while building own)
5. **DARPA MATHBAC teaming profile** (due 2026-04-14)
6. **DARPA CLARA Volume 1** (deadline 2026-04-17)
7. Build PyTorch CUDA wheels for Python 3.14 (weekend project)
