# Coding Systems Master Reference

> Consolidated reference for the SCBE-AETHERMOORE coding intelligence system: vision, core loop, 14-layer pipeline, tongue encoding, language mapping, musical modes, binary strategy, swarm architecture, photonic vision, implementation status, and file index.

## 1. Vision

SCBE-AETHERMOORE trains AI models that understand code the way code actually executes -- not the way training data traditionally frames it. The gap between "what training teaches" and "what actually runs" is the training signal. This residual is captured through the Sacred Six Tongues framework, which decomposes code understanding into six orthogonal dimensions weighted by the golden ratio.

The system produces training data that teaches:

- **How code flows** (not how code looks): Execution traces, opcode analysis, memory models
- **Why code works** (not what code does): Mechanism-level explanations, cost models
- **What code protects against** (not just what code achieves): Adversarial patterns, race conditions, hidden costs
- **How languages relate** (not just syntax differences): Tongue affinity space, interop bridges, cultural lenses

The endpoint is a coding model that thinks in terms of intent (KO), knowledge (AV), governance (RU), computation (CA), defense (UM), and architecture (DR) simultaneously -- and that maps onto photonic hardware where these dimensions become physical wavelength channels.

## 2. Core Loop

The training data generation pipeline follows a snake-like sequential process:

```
Stage 1: Ingest       -- Raw data from Notion, web, HuggingFace, GitHub
Stage 2: HYDRA        -- Multi-model consensus (6 models, one per tongue)
Stage 3: Auto-mark    -- 6D tongue activation scoring
Stage 3.5: Mirror     -- Antisymmetric refraction through mirror pairs
Stage 4: Sacred Egg   -- Hatch training eggs with phi-weighted attributes
Stage 5: Friction     -- 198-dimensional friction analysis (33 boundaries x 6 tongues)
Stage 6: Forge        -- Multi-language polyglot generation (7 patterns)
Stage 7: Adversarial  -- Trap detection and DPO pair generation
Stage 8: Coach Rune   -- NIST CSF alignment (Identify/Protect/Detect/Respond/Recover)
Stage 9: Export       -- Final JSONL output with deduplication
```

Each stage transforms and enriches the data. Records that fail quality gates at any stage are recycled back to Stage 1 as negative examples.

## 3. The 14-Layer Security Pipeline

The SCBE pipeline processes every input through 14 mathematical layers, organized by tongue:

### KO Layers (Foundation) -- phi^0 = 1.000

- **L1: Complex State Encoder** -- Maps time-series features to complex numbers: c = A * exp(i*phi). Converts real-valued input into a complex representation that preserves phase information.
- **L2: Realification** -- Isometric mapping from C^D to R^{2D}. Doubles dimensionality but enables real-valued matrix operations while preserving complex structure.

### AV Layers (Temporal) -- phi^1 = 1.618

- **L3: Weighted Transform** -- Applies a symmetric positive-definite (SPD) metric tensor: x_G = G^{1/2} * x. The metric G is learned from the data manifold and encodes tongue-specific distance relationships.
- **L4: Poincare Embedding** -- Maps from Euclidean to hyperbolic space: p = tanh(alpha * ||x||) * x/||x||. Hyperbolic space has exponentially more room near the boundary, naturally encoding hierarchical relationships (intent -> knowledge -> governance -> ...).

### RU Layers (Verification) -- phi^2 = 2.618

- **L5: Hyperbolic Distance** -- Computes distances in the Poincare ball: d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2))). This distance grows exponentially near the boundary, creating a natural "harmonic wall" where distant patterns are separated by vast hyperbolic distances.
- **L6: Breathing Transform** -- Time-varying diffeomorphism: B(p,t) = tanh(||p|| + A*sin(omega*t)) * p/||p||. The "breathing" makes the embedding space pulsate, preventing adversarial inputs from finding stable fixed points.

### CA Layers (Consensus) -- phi^3 = 4.236

- **L7: Phase Transform** -- Mobius transformation plus rotation: Phi(p,a,Q) = Q * (p + a). Shifts and rotates patterns in hyperbolic space to align them with realm centroids.
- **L8: Realm Distance** -- Minimum distance to any known realm centroid: d_realm = min_k d_H(u, mu_k). Determines which "realm" (authorized behavior cluster) the input is closest to.

### UM Layers (Trust) -- phi^4 = 6.854

- **L9: Spectral Coherence** -- FFT-based analysis: S_spectral = ||FFT(signal)||_peak / ||FFT(signal)||_total. Measures whether the input has coherent spectral structure (legitimate) or diffuse noise (adversarial). Authorized patterns have clean spectra; attacks are broadband.
- **L10: Spin Coherence** -- Quaternion-based: S_spin = ||sum(exp(i*theta_k))|| / N. Measures alignment of phase angles across dimensions. Legitimate inputs have coherent spin; adversarial inputs have random spin.

### DR Layers (Deep Security) -- phi^5 = 11.090

- **L11: Triadic Temporal Aggregation** -- Three-window weighted distance: d_triadic = lambda_1*d_1 + lambda_2*d_2 + lambda_3*d_G. Combines short-term, medium-term, and long-term (golden ratio windowed) distance measurements.
- **L12: Harmonic Scaling** -- The harmonic wall function: H(d) = R^(d^2) where R=1.5. Maps linear distance to exponential penalty. At d=1, H=1.5. At d=2, H=5.06. At d=5, H=759. At d=10, H=57,665. The wall is effectively impenetrable beyond d=5.

### Violet Layers (Meta) -- Combined

- **L13: Risk Decision Engine** -- Threshold-based: ALLOW if Risk < theta_1, QUARANTINE if theta_1 <= Risk < theta_2, DENY if Risk >= theta_2. Binary output with an intermediate quarantine zone for human review.
- **L14: Audio Axis** -- High-frequency ratio analysis: S_audio = 1 - rHF. Cymatic/acoustic telemetry layer that detects patterns in the frequency content of the combined signal. Acts as a final integrity check.

## 4. Tongue Encoding

Each data record carries a 6D tongue activation vector:

```
tongue_vector = [KO, AV, RU, CA, UM, DR]
```

Where each component is in [0, 1] and represents the degree to which that tongue's concerns are relevant.

### Encoding Method

The auto-marker (Stage 3) scores each record by analyzing:

- **KO activation**: Presence of imperative verbs, command structures, direct instructions
- **AV activation**: Type annotations, schema definitions, knowledge declarations, explanatory content
- **RU activation**: Validation logic, constraint checking, rule enforcement, governance patterns
- **CA activation**: Mathematical operations, algorithmic complexity, raw computation
- **UM activation**: Error handling, security checks, defensive patterns, threat mitigation
- **DR activation**: Architectural patterns, module structure, composition, abstraction layers

### Phi-Weighting

Raw activations are multiplied by tongue weights before distance calculations:

```
weighted_vector = [KO * 1.000, AV * 1.618, RU * 2.618, CA * 4.236, UM * 6.854, DR * 11.090]
```

This means DR-heavy records dominate the distance metric by 11x, ensuring that architectural understanding has the strongest training signal per record.

## 5. Language Mapping

### Primary Mapping

| Tongue | Language | Domain | Phase |
|--------|----------|--------|-------|
| KO (Kor'aelin) | Python | Intent/Command | 0 deg |
| AV (Avali) | TypeScript | Wisdom/Knowledge | 60 deg |
| RU (Runethic) | Rust | Governance/Entropy | 120 deg |
| CA (Cassisivadan) | C | Compute/Logic | 180 deg |
| UM (Umbroth) | Julia | Security/Defense | 240 deg |
| DR (Draumric) | Haskell | Structure/Architecture | 300 deg |

### Mirror Pairs

- KO <-> DR (Python <-> Haskell): Intent vs Architecture
- AV <-> CA (TypeScript <-> C): Knowledge vs Compute
- RU <-> UM (Rust <-> Julia): Governance vs Security

### Foundation Trio

Python (AV) + TypeScript (DR) + Rust (UM) form the primary interop triangle connected by PyO3, wasm-bindgen, and subprocess bridges.

See `docs/TONGUE_CODING_LANGUAGE_MAP.md` for full mapping including standard, esoteric, and international tiers.

## 6. Musical Modes

Each tongue resonates with a Western musical mode:

| Tongue | Mode | Character | Interval Pattern |
|--------|------|-----------|-----------------|
| KO | Ionian (major) | Bright, foundational | W-W-H-W-W-W-H |
| AV | Lydian | Elevated, aspirational | W-W-W-H-W-W-H |
| RU | Dorian | Disciplined, balanced | W-H-W-W-W-H-W |
| CA | Mixolydian | Driving, unresolved | W-W-H-W-W-H-W |
| UM | Aeolian (minor) | Dark, introspective | W-H-W-W-H-W-W |
| DR | Phrygian | Exotic, complex | H-W-W-W-H-W-W |
| Anti (Mal'kythric) | Locrian | Unstable, dissonant | H-W-W-H-W-W-W |

The modal assignments follow spectral frequency: KO (lowest frequency, longest wavelength, major key) through DR (highest frequency, shortest wavelength, most exotic mode).

## 7. Binary Strategy

The training pipeline produces two types of training data:

### SFT (Supervised Fine-Tuning)

Standard instruction-response pairs in chat format. Each record includes:

```json
{
  "messages": [
    {"role": "system", "content": "[TONGUES: KO=... AV=... RU=... CA=... UM=... DR=...] [LAYERS: ...] ..."},
    {"role": "user", "content": "instruction"},
    {"role": "assistant", "content": "response"}
  ],
  "tongue_affinity": {"KO": 0.5, "AV": 0.1, ...},
  "_source": "coding_agent_sft"
}
```

### DPO (Direct Preference Optimization)

Preference pairs generated by the adversarial stage (Stage 7):

```json
{
  "prompt": "instruction",
  "chosen": "safe response",
  "rejected": "unsafe/low-quality response",
  "tongue_profile": {"KO": 0.5, ...},
  "trap_domain": "chemistry"
}
```

The binary strategy: SFT teaches the model what good looks like. DPO teaches it what bad looks like. Both are tongue-tagged so the model learns which tongue-dimensions distinguish good from bad.

### Combined Training Recipe

1. Pre-train on code-flow documents (CLM, full-context)
2. SFT on coding_combined_all.jsonl (4,167 records)
3. DPO on adversarial pairs (from snake Stage 7)
4. Phi-weighted sampling: oversample DR/UM, undersample KO

## 8. Swarm Architecture (HYDRA)

The HYDRA system uses 6 language models, one per tongue:

| Tongue | Model | Role |
|--------|-------|------|
| KO | Qwen/Qwen2.5-7B-Instruct | Intent extraction |
| AV | meta-llama/Llama-3.1-8B-Instruct | Knowledge synthesis |
| RU | Qwen/Qwen2.5-72B-Instruct | Governance verification |
| CA | meta-llama/Llama-3.3-70B-Instruct | Computation analysis |
| UM | Qwen/Qwen2.5-7B-Instruct | Security assessment |
| DR | Qwen/Qwen2.5-Coder-32B-Instruct | Architecture evaluation |

### Consensus Protocol

All 6 models evaluate each record independently. The consensus score is the phi-weighted average of their scores. Records require 4/6 agreement to pass to the next stage. The two dissenting models' objections are logged as friction signals.

### Swarm Scaling

The HYDRA swarm can be deployed as:

- **Local**: All 6 models on a single GPU server (requires 80GB+ VRAM for full swarm)
- **Distributed**: Models spread across multiple machines with gRPC coordination
- **Cloud**: HuggingFace Inference API calls with rate limiting and retry logic
- **Hybrid**: Large models (RU: 72B, CA: 70B) on cloud, small models (KO, UM: 7B) local

## 9. Photonic Vision

The SCBE pipeline's mathematical operations (FFT, phase transforms, Poincare embeddings, harmonic scaling) map directly onto photonic hardware. Lithium niobate (LiNbO3) waveguides provide:

- Electro-optic phase modulation for layers L4, L7 (phase transforms)
- Second-harmonic generation for layer L12 (harmonic scaling)
- On-chip Fourier transforms for layer L9 (spectral coherence)
- Polarization diversity for layer L10 (spin coherence)

The photonic NPU vision: security as physics, where the harmonic wall is a physical waveguide property rather than a software threshold. See `docs/PHOTONIC_NPU_VISION.md` for full technical details.

## 10. Implementation Status

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Snake Pipeline (Stages 1-9) | Implemented | `training/snake/` | Python, runs locally |
| HYDRA Swarm | Implemented | `training/snake/config.py` | HF Inference API |
| Auto-marker (Stage 3) | Implemented | `training/snake/` | 6D tongue scoring |
| Multi-Language Forge (Stage 6) | Implemented | `training/snake/multilang_forge.py` | 7 forge patterns |
| Code-Flow Generator | Implemented | `scripts/generate_code_flow_dataset.py` | 7 seed samples, CLM format |
| Sphere Grid | Implemented | `training/snake/sphere_grid.py` | 39 languages mapped |
| coding_agent_sft.jsonl | 206 records | `training/sft_records/` | Chat-format SFT |
| coding_combined_all.jsonl | 4,167 records | `training/sft_records/` | Merged from all sources |
| Forge pairs | 1,442 records | `training/generated/forge/` | Generated from coding_agent_sft |
| Code-flow data | 7 samples | `training/generated/code-flow/` | Multi-view pretraining docs |
| Coding extracts | 2,512 records | `training/generated/` | From sft_combined |
| training-data symlink | BROKEN | repo root | Unresolvable; data regenerated in training/generated/ |
| Photonic NPU | Design only | `docs/PHOTONIC_NPU_VISION.md` | No hardware prototype |
| DPO Adversarial Pairs | Planned | `training-data/dpo/` (blocked by symlink) | Stage 7 output |
| NIST CSF Alignment | Planned | Stage 8 | Coach Rune integration |
| HuggingFace Upload | Planned | `issdandavis/code-flow-pretraining` | Needs `--upload` flag |

## 11. File Index

### Core Pipeline

```
training/snake/config.py                     -- Constants, tongue definitions, phi weights
training/snake/sphere_grid.py                -- FFX Sphere Grid language mapping (39 languages)
training/snake/multilang_forge.py            -- Stage 6: 7-pattern polyglot forge
training/snake/baby_babble.py                -- Stage 1: Initial data ingestion
training/snake/lore_code_multiplier.py       -- Lore-to-code multiplication
training/snake/operator_pivot_trajectories.py -- Operator pivot analysis
training/snake/trichromatic_curriculum.py    -- Trichromatic training curriculum
```

### Training Data

```
training/sft_records/coding_agent_sft.jsonl        -- 206 coding SFT records
training/sft_records/coding_combined_all.jsonl      -- 4,167 merged coding records
training/sft_records/sft_combined.jsonl             -- 27,234 general SFT records
training/sft_records/sft_ingestion_pool.jsonl       -- Ingestion pool
training/sft_records/sft_repo_merged.jsonl          -- Repo-wide merged SFT
training/generated/forge/forge_pairs.jsonl          -- 1,442 multilang forge pairs
training/generated/code-flow/train.jsonl            -- 7 code-flow pretraining docs
training/generated/code-flow/train.txt              -- Plain text CLM format
training/generated/coding_from_combined.jsonl       -- 2,512 coding extracts
```

### Scripts

```
scripts/generate_code_flow_dataset.py    -- Code-flow dataset generator
scripts/generate_hexforge_sft.py         -- HexForge SFT generator
scripts/train_code_flow_scratch.py       -- Code-flow training script
```

### Documentation

```
docs/TONGUE_CODING_LANGUAGE_MAP.md        -- Tongue-to-language mapping with phase geometry
docs/PHOTONIC_NPU_VISION.md              -- Q-ANT LiNbO3 photonic compute vision
docs/CODING_SYSTEMS_MASTER_REFERENCE.md  -- This document
docs/SACRED_TONGUE_SPECTRAL_MAP.md       -- Spectral color mapping and 14-layer diagram
docs/SACRED_TONGUES_TUTORIALS.md         -- Tutorial guides
docs/SIX_TONGUES_CLI.md                  -- CLI reference for six-tongues tools
```

### Configuration

```
training/snake/config.py                 -- Pipeline constants, tongue weights, HYDRA models
training/config/                         -- Training configuration files
training/registry.json                   -- Training data registry
```

---

*SCBE-AETHERMOORE v3.0 Coding Intelligence System*
*Last updated: 2026-04-15*
*Maintainer: Issac Davis (issdandavis7795@gmail.com)*
