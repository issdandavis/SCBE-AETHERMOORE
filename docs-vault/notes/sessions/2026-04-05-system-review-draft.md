---
title: "Session 2026-04-05: System Review, Free Models, AetherSearch"
date: 2026-04-05
tags: [session, code-review, training, search, infrastructure, models]
status: complete
tongue_profile: [RU, CA, DR]
---

# Session 2026-04-05 — System Review + Free Models + AetherSearch Plan

## What Happened

### 1. Full System Review — 10 Bugs Fixed Across 8 Files

Three parallel code review agents scanned the audio + chromatic + quantum bundle + TTS pipeline.

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | CRITICAL | `src/crypto/choral_render.py:206` | Relative import `from .speech_render_plan` crashes when loaded via sys.path from scripts | Changed to absolute: `from src.crypto.speech_render_plan import TONGUE_PAN` |
| 2 | CRITICAL | `src/audio/gallery_sonifier.py` | Duplicate `LabColor` class with incompatible hue interface (degrees vs radians) | Removed local copy, imported from `gallery_chromatics`; added `hue_degrees` property to canonical class |
| 3 | CRITICAL | `src/crypto/speech_render_plan.py:35` | Wrong ratio comment: `# 9:5 ratio` on minor_seventh | Fixed to `# 16:9 ratio` |
| 4 | CRITICAL | `scripts/tts_chunk_render.py:86-106` | Boundary stress detection used unfiltered word index (punctuation-only words skewed position) | Pre-filter words, then enumerate cleaned list for boundary detection |
| 5 | CRITICAL | `scripts/generate_quantum_frequency_sft.py:67` | `json.loads(line)` with no try/except — single malformed line crashes entire 11K pipeline | Added `try/except json.JSONDecodeError: continue` |
| 6 | MEDIUM | `src/crypto/choral_render.py` | `import math` was inline inside function branch, not at module top | Moved to top-level import |
| 7 | MEDIUM | `scripts/tts_chunk_render.py` | Unused `from dataclasses import asdict` | Removed |
| 8 | MEDIUM | `src/crypto/quantum_frequency_bundle.py:671` | Autorotation docstring says `blind_spot_proximity > 0.7` but code uses `> 0.5` | Fixed docstring to match code (0.5) |
| 9 | MEDIUM | `src/crypto/gallery_chromatics.py:37` | Forward reference `GalleryAmbientNote` unresolvable at runtime type inspection | Added `TYPE_CHECKING` import block |
| 10 | MEDIUM | `training/snake/pipeline.py:2` | Docstring says "9-stage" but 16 stages are implemented | Updated to "16-stage" with full stage list |

### Verified Clean (no action needed)
- Quantum bundle + color field integration: all 24 CIELAB points correct
- Biological detection models (Lotka-Volterra, immune, sonar): math verified
- Gallery chromatics phi-scaled offsets: within 0.001 radians
- Cross-eye coherence cosine similarity: properly bounded [0, 1]
- No circular imports (manifold_mirror lazy import correct)
- All 16 snake pipeline stages functional
- SFT output: 11,389 records, 183MB, all fields including color_field
- `chords[tone]` dict access: keys guaranteed by DEAD_TONE_RATIOS

### Future work noted
- `choral` field not in quantum bundle (by design — separate TTS pipeline)
- Cross-modal alignment needs richer features when texts share dominant tongue
- Hoist `_TONE_SENSITIVITY` to module scope (minor perf)
- Minor seventh cortisol floor clamp at 1.0 may mask signal

---

### 2. GPT Pro Budget Exhausted — Switching to Free Open Models

GPT Pro subscription budget is spent. Identified free alternatives:

**Best fits for our hardware (GTX 1660 Ti, 6GB VRAM):**
- Qwen2.5-0.5B-Instruct (Apache 2.0) — safest for 6GB QLoRA
- Qwen3-1.7B (Apache 2.0) — stretch fit
- Llama-3.2-1B-Instruct — good alternative

**For Kaggle/cloud (bigger models):**
- Qwen3-8B (Apache 2.0) — 9.3M downloads, thinking mode built in
- Llama-3.1-8B-Instruct — Meta's workhorse
- Mistral-7B-Instruct-v0.3 (Apache 2.0) — good for HYDRA agents

**Key insight:** We have 11,389 SFT records + 16-stage snake pipeline output ready. The training corpus IS the competitive advantage — free base models + our data = custom models that understand SCBE geometry.

---

### 3. Hardware Assessment

- CPU: i7-10750H, 12 threads
- RAM: ~12 GB
- GPU: GTX 1660 Ti, 6 GB VRAM (compute 7.5)
- NVIDIA Driver: 591.86 (CUDA 13.1 capable)
- PyTorch: 2.10.0 **CPU-only** (Python 3.14 too new for CUDA wheels)
- Python 3.12 and 3.13 also installed (CUDA wheels available)

**Fix:** Create Python 3.12 venv for training. Details in `notes/pytorch-cuda-build-and-training-plan.md`.

**Building wheels from source** (weekend project):
- Need CUDA Toolkit 12.4 + cuDNN 9.x + VS2022 C++ tools
- `TORCH_CUDA_ARCH_LIST=7.5` for 1660 Ti
- 2-4 hour compile time

---

### 4. Algolia Research + AetherSearch Architecture

**Algolia:** Search-as-a-service, $10K startup credits available. We qualify.
- Apply at algolia.com/industries/startups or through Secret/NachoNacho/FounderPass
- Eligibility: < 3 years old, < $5M raised, no previous coupons
- 12-month credit window

**Open-source alternatives studied:**
- Meilisearch (Rust): LMDB storage, Charabia tokenizer, actix-web API, parallel extraction pipeline
- Typesense (C++): Custom ADI tree, ONNX embeddings, Raft consensus clustering, single binary

**AetherSearch concept:** Build our own search engine using SCBE geometry as the ranking/relevance layer. We already have pieces they don't:
- Sacred Tongues tokenizer vs standard BPE
- 198-dim polyhedral friction scoring vs TF-IDF/BM25
- Harmonic wall distance vs flat vector cosine
- 14-layer governance on search results
- Cross-modal search (text + audio + color)

Phase 1: Use Meilisearch as runtime, SCBE as enrichment layer
Phase 2: Build SCBE-native index in Rust
Phase 3: AetherSearch as Mesh Foundry product

---

### 5. Test Results (parallel session)

- TypeScript: **6,008 passed**, 8 skipped (176 test files, 37.3s)
- Python: running (results pending)
- Polyhedral node generator P1-P3 being built in parallel session

---

## Polly Training Priority

Polly (website chatbot) needs updated training run:
1. Create Python 3.12 venv with CUDA PyTorch
2. Pick base model (Qwen2.5-0.5B local or Qwen3-8B on Kaggle)
3. QLoRA fine-tune on SCBE corpus
4. Push to HF, serve via vLLM/Ollama
5. Wire into website
