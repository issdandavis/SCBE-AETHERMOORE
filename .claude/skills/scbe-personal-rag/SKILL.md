---
name: scbe-personal-rag
description: Fast-recall knowledge base for SCBE-AETHERMOORE architecture, lore, formulas, file locations, and Issac's design decisions. Query this FIRST before searching the codebase or claiming something doesn't exist.
---

# SCBE Personal RAG — Fast Recall Index

This skill is Claude's personal knowledge base for the SCBE-AETHERMOORE project. Query it before searching files. If something isn't here, check Notion, then the round-table notes, then the codebase.

## RULE: NEVER say something doesn't exist without checking ALL sources:
1. This RAG index
2. Notion (mcp__notion-sweep__notion_search)
3. Round-table notes (notes/round-table/)
4. Training data (training/intake/notion/)
5. The book (content/book/reader-edition/)
6. Obsidian vault (notes/.obsidian/)
7. The codebase itself

---

## SACRED TONGUES (Canonical v2.1 — Tutorial Version)

### The 6 Tongues
| Code | Name | Domain | Phase | Weight | Freq |
|------|------|--------|-------|--------|------|
| KO | Kor'aelin | Nonce/Flow/Intent | 0° | 1.000 | 440 Hz |
| AV | Avali | AAD/Context/I/O | 60° | 1.618 | 712 Hz |
| RU | Runethic | Salt/Binding/Policy | 120° | 2.618 | 1152 Hz |
| CA | Cassisivadan | Ciphertext/Compute | 180° | 4.236 | 1864 Hz |
| UM | Umbroth | Redaction/Security | 240° | 6.854 | 3016 Hz |
| DR | Draumric | Auth Tags/Schema | 300° | 11.090 | 4880 Hz |

### KO Canonical Prefixes (Tutorial v2.1)
`ka, sil, kor, zar, vel, thul, ra, med, gal, zen, vak, lor, tor, jin, vok, rin`

### KO Canonical Suffixes (Tutorial v2.1)
`a, ae, ei, oth, ar, en, ok, ik, eth, os, ir, im, un, el, ul, al`

### Tutorial Test Vector
- 0x3c → zar'un (prefixes[3]=zar, suffixes[12]=un)
- 0x5a → thul'ir (prefixes[5]=thul, suffixes[10]=ir)

### Source of Truth Priority
1. Training data (training/intake/notion/tongues/) — what models are trained on
2. Notion tutorials (page 058b4372) — worked examples
3. src/tokenizer/ss1.ts — code (synced to v2.1 on 2026-03-20)
4. Notion Chapter 4 (page 1b9b084c) — has OLD consonant-cluster version, NOT canonical

### WARNING: Multiple Versions Exist
- v1.0: Original (had KO collisions)
- v2.0: Consonant-cluster rewrite (k, kr, kl, kv...) — NOT the canonical one
- v2.1: Tutorial/particle version (ka, sil, kor, zar...) — THIS IS CANONICAL

---

## KEY FORMULAS

### Harmonic Wall
```
H(d, R) = R^(d²)
```
- d = hyperbolic distance from safe, R = wall radius
- Safe: H=1, Attack: H=billions

### Davis Security Score
```
S(t, i, C, d) = t / (i × C! × (1 + d))
```
- t=trust, i=interactions, C=context complexity, d=drift
- C! is the factorial moat

### PhaseTunnelGate Transmission
```
T = cos²((β_phase - φ_wall) / 2)
```
- β = weight matrix spectral phase, φ_wall = governance dial
- T=1 → TUNNEL, T=0 → COLLAPSE

### Hyperbolic Distance (L5)
```
d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
```

### Langues Metric
```
L(x, t) = Σ wₗ × exp(βₗ × (dₗ + sin(ωₗt + φₗ)))
```
- wₗ = phi^n weights, βₗ = scaling, ωₗ = frequency

---

## 14-LAYER PIPELINE

| Layer | Function | Key Math |
|-------|----------|----------|
| L1-2 | Complex→Real | Realification of context |
| L3-4 | Tongue weighting→Poincaré embed | 6D projection into ball |
| L5 | Hyperbolic distance | arcosh metric |
| L6-7 | Breathing transform + Möbius | Ball oscillation + rotation |
| L8 | Hamiltonian multi-well | 16 polyhedra, energy budgets |
| L9-10 | Spectral + spin coherence | FFT analysis |
| L11 | Triadic temporal distance | Past/present/future check |
| L12 | Harmonic wall | H(d,R) = R^(d²) |
| L13 | Risk decision | ALLOW/QUARANTINE/ESCALATE/DENY |
| L14 | Audio axis telemetry | Harmonic fingerprint logging |

---

## PHDM (Chapter 6 in Notion)

### 16 Polyhedra as Cognitive Nodes
- **Platonic 5** (safe core): Tetrahedron(1.0), Cube(1.2), Octahedron(1.5), Dodecahedron(2.0), Icosahedron(2.5)
- **Archimedean 3** (complex reasoning): Semi-regular, multi-vertex
- **Kepler-Poinsot 2** (adversarial): Non-convex, spiky, exponential traversal cost
- **Specialized 6**: Domain-specific

### Energy Budget
- Start with 100 units
- Safe path: ~6 units for 4 nodes
- Attack path: 24+ units for 2 nodes (superlinear growth)
- Budget exhausted → reasoning collapses

### Dual Lattice
- PROJECT: 6D→3D (static, structural)
- LIFT: 3D→6D (runtime, dynamic)
- Phason shifts rotate projection window without changing topology

---

## DUAL-CORE MEMORY KERNEL (Built 2026-03-20)

### Architecture
- **GeoKernel** (brainstem): Fast decisions, reflexes, immune memory
- **MemoryLattice** (spinal cord): 7 layers, hash-chained, persistent
- **Bridge**: Quasi-lattice (icosahedral 6D projection, aperiodic)

### 7 Memory Layers
0. Working (seconds)
1. Session (hours)
2. Mission (days)
3. Identity (permanent — KernelStack)
4. Reflex (learned fast-paths, O(1))
5. Immune (attack patterns, Bloom filter)
6. Dream (offline consolidation)

### File: src/kernel/dual_core.py
### PHDM model: issdandavis/phdm-21d-embedding (83 categories, numpy weights)

---

## AETHERBROWSER

### TriLane Router (Built 2026-03-20)
- Lane 1: HEADLESS (CDP/Playwright) — bulk, parallel
- Lane 2: MCP (Claude-in-Chrome) — interactive
- Lane 3: VISUAL (screenshot + multimodal) — verification

### File: src/aetherbrowser/trilane_router.py
### Server: src/aetherbrowser/serve.py (port 8002)
### Launcher: scripts/launch_aetherbrowser.py
### Tests: 24/24 passing

### API Endpoints
- POST /v1/browse — execute governed browser task
- GET /v1/browse/classify — classify task intent
- GET /v1/browse/stats — usage statistics
- GET /health — full system status

---

## PHASE TUNNEL → TONGUE MAPPING (from round-table notes)
- Q matrices ≈ DR (Draumric, auth/structure) — high spectral density
- K matrices ≈ RU (Runethic, binding/policy) — near-random spectral
- V matrices ≈ AV (Avali, context/transport) — intermediate

---

## KEY FILE LOCATIONS

### Core Systems
- 14-layer pipeline: src/harmonic/pipeline14.ts
- Sacred Tongue tokenizer: src/tokenizer/ss1.ts
- Hyperbolic geometry: src/harmonic/hyperbolic.ts
- Harmonic scaling: src/harmonic/harmonicScaling.ts
- PHDM: src/harmonic/phdm.ts + src/ai_brain/
- Quasi-lattice: src/ai_brain/quasi-space.ts
- Dual lattice: src/ai_brain/dual-lattice.ts
- Phase tunnel: src/aetherbrowser/phase_tunnel.py
- Dual-core kernel: src/kernel/dual_core.py

### Lore & Content
- Full novel: content/book/reader-edition/the-six-tongues-protocol-full.md (776KB)
- World bible: docs/WORLDFORGE_TEMPLATE.md (288KB)
- Tech deck: docs/SCBE_TECH_DECK_V5.md (252KB)
- Tongue wiki: training/raw/six_tongues_enhanced_v2.md (144KB)
- Codex: docs/specs/SPIRALVERSE_CANONICAL_LINGUISTIC_CODEX_V1.md
- Interop matrix: docs/specs/SACRED_TONGUE_INTEROP_MATRIX.md

### Notion Pages (fetch with mcp__notion-sweep__notion_fetch_page)
- Ch4 Sacred Tongues: 1b9b084c-992b-42d5-b47d-4e411c133c7b
- Ch5 GeoSeal: 857dc65d-d633-4378-b3cf-d33dfc351fed
- Ch6 PHDM: fe67afda-1b30-4712-a905-292fa68133ab
- Ch7 Sacred Eggs: 59ff656a-f0a8-4545-93b4-f04755d550c7
- KO Lexicon: f8eff722-8a75-4a71-b5d0-fa151d78c260
- Complete Reference: b78e6933-0d79-45b1-a887-62337dc144b2
- Tutorial 1: 058b4372-d8c3-4288-b860-7eaa5d1fbe42
- Math Spec: 2d7f96de-82e5-803e-b8a4-ec918262b980

### HuggingFace Assets
- Models: scbe-pivot-qwen-0.5b, phdm-21d-embedding, spiralverse-ai-federated-v1, six-tongues-art-lora, scbe-research-bridge-qwen-0.5b
- Datasets: scbe-aethermoore-training-data (primary), scbe-aethermoore-knowledge-base, aethermoor-chat-sft, six-tongues-webtoon-panels, scbe-ops-assets
- User: issdandavis

### Voice Assets
- Issac samples: artifacts/voice/issac_voice_sample*.wav (3 takes, up to 94.7s)
- Character voices: artifacts/voice/test_*.wav (marcus, polly, senna, bram, alexander)
- Kokoro model: ~/.kokoro-onnx/kokoro-v1.0.int8.onnx
- Narration output: artifacts/narration/

---

## MONETIZATION ROUTES (Ranked by speed-to-revenue)
0. Book on Amazon KDP (LIVE)
1. Sacred Data Factory — sell datasets on HF/Gumroad ($29-99 each)
2. Governance Starter Kit — bundle docs as Gumroad product ($29-49)
3. Pruning Dashboard — PhaseTunnelGate as model optimization ($5K+/audit)
4. Safety Wedge API — hosted LatticeGate SaaS ($500-2500/mo)

---

## THE 5 DUALS (from Notion Integration Guide — THE kernel architecture spec)

This is the actual dual-core kernel specification from Notion Chapter 6 Addendum.
Every module must emit BOTH a continuous state vector AND a discrete signed decision.

| Dual | Core 1 (Continuous/Hot) | Core 2 (Discrete/Cold) |
|------|------------------------|----------------------|
| State | d_hyp, coherence, spectral, flux, tongue_phase[6] | CapabilityToken with TTL, quorum, signature |
| Decision | Risk' = smooth scalar from L1-L12 | ALLOW / QUARANTINE / DENY at L13 |
| Memory | Negative space (cymatic anti-nodes, geometric shaping) | VoxelKey[X,Y,Z,V,P,S] with payload_hash + sig |
| Consensus | Coherence fields, defect scores (fast layer) | >=4/6 quorum for irreversible actions (slow layer) |
| Channel | Audio axis L14 (rapid anomaly intuition) | Numeric telemetry (spectral centroid, d*, kappa) |

**Rule: Continuous governs motion. Quorum governs irreversibility.**

## KEY SYNTHESIS FROM RESEARCH NOTES (2026-03-20)

Full synthesis at: artifacts/research/round_table_synthesis_20260320.md

Critical findings:
- Sacred Tongues ARE the empirical resonance frequencies in transformer weights (not metaphor)
- Q≈DR (24° delta), K≈RU (2° delta), V≈AV (27° delta) — discovered empirically
- Recursive realification IS the nursery developmental tower
- Mirror health score IS the HP system for research problems
- Davis Formula C! term IS the combinatorial interaction of electron shells
- Thermal silence IS the 7th masquerade detection channel
- GeoSeal concentric rings = memory kernel write gates (exponential cost)
- Sacred Eggs = sealed memory units requiring geometric multi-factor auth
- PHDM quasicrystal = cognitive substrate where thoughts navigate geometrically

## ISSAC'S DESIGN PHILOSOPHY
- "Just have fun with it" — prefers autonomous creative work
- Build specialist models, not one monolith
- Pre-map to harmonic frequencies, fire asynchronously
- Like neurons — don't know the whole picture, coordinate through resonance
- "You can only expect so much of a tool" — plan multilaterally, execute in parallel
- Revenue is always the priority
- Local-first, API credits only for heavy stuff
- The system should get stronger from attacks (immune flywheel)
