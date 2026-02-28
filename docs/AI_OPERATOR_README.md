# SCBE-AETHERMOORE: AI Operator Reference

**For:** Any AI operator (Claude, ChatGPT, Gemini, Copilot, Codex, or other)
**Version:** 3.0.0
**Status:** Patent Pending
**Author:** Issac Davis

This document gives you the minimum viable context to operate effectively within the SCBE-AETHERMOORE codebase. Read it before making changes.

---

## 1. System Overview

**SCBE-AETHERMOORE** (Spiralverse Context-Bound Enforcement) is a 14-layer AI safety and governance framework built on hyperbolic geometry. It uses the Poincare ball model to make adversarial behavior exponentially expensive: the further an action drifts from safe operation, the more it costs.

Traditional security makes attacks hard. SCBE makes attacks geometrically impossible.

The system is implemented in both TypeScript (canonical production) and Python (reference implementation). It includes post-quantum cryptography (ML-KEM-768, ML-DSA-65), a custom tokenizer (SS1), a multi-agent coordination system (HYDRA), and a polyhedral cognitive governance mesh (PHDM).

---

## 2. The 14 Layers

| Layer | Name | Formula / Operation | What It Does |
|-------|------|---------------------|--------------|
| **L1** | Complex Context | c(t) in C^D | Maps input to complex-valued state (amplitude = magnitude, phase = intent) |
| **L2** | Realification | Phi: C^D -> R^2D | Isometric embedding from complex to real space |
| **L3** | Weighted Transform | x_G = G^(1/2) * x | SPD-weighted transformation using tongue weights (LWS or PHDM profile) |
| **L4** | Poincare Embedding | u = tanh(alpha * norm) * x_G / norm | Maps to the open unit ball B^n = {u : norm(u) < 1} |
| **L5** | Hyperbolic Distance | d_H = arcosh(1 + 2*norm(u-v)^2 / ((1-norm(u)^2)(1-norm(v)^2))) | **THE INVARIANT.** This metric never changes. All governance derives from it. |
| **L6** | Breathing Transform | T_breath(u; t) via radial rescaling | Temporal modulation. Diffeomorphism that pushes/pulls state within the ball. |
| **L7** | Phase Transform | Mobius addition: Q(t) * (a(t) + u) | Isometric hyperbolic translation + rotation. Preserves d_H. |
| **L8** | Multi-Well Realms | d* = min_k d_H(u, mu_k) | Distance to nearest trusted realm center. Multiple safe zones. |
| **L9** | Spectral Coherence | S_spec = 1 - r_HF | FFT-based pattern stability score. Detects frequency-domain anomalies. |
| **L10** | Spin Coherence | C_spin = mean resultant length | Phase alignment across multiple signals. Consensus measure. |
| **L11** | Triadic Distance | d_tri | Byzantine consensus temporal distance. Three-axis time ordering. |
| **L12** | Harmonic Wall | H(d, pd) = 1/(1+d+2*pd) (bounded) or H(d,R) = R^(d^2) (exponential) | Safety score or cost multiplier. Two variants exist (see Section 8). |
| **L13** | Decision Gate | ALLOW / QUARANTINE / ESCALATE / DENY | Risk-gated governance decision. Final output of the pipeline. |
| **L14** | Audio Axis | S_audio = harmonic + stellar octave mapping | FFT telemetry. Sonification of system state for monitoring. |

**Critical invariant:** L5 hyperbolic distance is preserved through L6 and L7 transforms. This is the foundation of the entire system.

---

## 3. Six Sacred Tongues

The system uses six semantic domains called Sacred Tongues. Each tongue is a complete 256-token vocabulary (16 prefixes x 16 suffixes) used by the SS1 tokenizer.

| Tongue | Code | Phase | Domain | LWS Weight | Phi Weight |
|--------|------|-------|--------|------------|------------|
| Kor'aelin | KO | 0 deg | Intent / Control / Orchestration | 1.000 | 1.000 |
| Avali | AV | 60 deg | Transport / Context / Communication | 1.125 | 1.618 |
| Runethic | RU | 120 deg | Policy / Authorization / Binding | 1.250 | 2.618 |
| Cassisivadan | CA | 180 deg | Compute / Encryption / Execution | 1.333 | 4.236 |
| Umbroth | UM | 240 deg | Security / Redaction / Privacy | 1.500 | 6.854 |
| Draumric | DR | 300 deg | Authentication / Integrity / Schema | 1.667 | 11.090 |

**Two weight systems exist:**
- **LWS-Linear** (base operations): Used in `cli_toolkit.py`. Weights are 1.000 to 1.667.
- **PHDM-Golden** (governance/crisis): Weights scale by phi (golden ratio): w_l = phi^(l-1). Always label which profile is active.

---

## 4. Key Subsystems

### 4.1 GeoSeal (Geometric Access Control)

An immune system for vector RAG. Uses hyperbolic swarm dynamics with phase-discipline to detect and quarantine adversarial retrievals. Agents carry tongue phase assignments; null-phase or mismatched-phase agents are repelled toward the Poincare ball boundary.

- Location: `src/geoseal.ts`, `src/geoseal-v2.ts`
- Docs: `docs/GEOSEAL_ACCESS_CONTROL.md`

### 4.2 Sacred Eggs (Ritual-Based Genesis)

Protocol for creating high-privilege identity tokens through ritual validation. Three ritual types: solitary (single-tongue), triadic (three-tongue conjunction), ring_descent (full 6-tongue). Eggs have TTL enforcement and phi-weight thresholds.

- Location: `sacred_egg_integrator.py`
- Notion: `069c0520-a59c-4c56-8099-c83236625ae8`

### 4.3 SS1 Tokenizer (Sacred Tongue Encoding)

Bijective binary-to-text encoding. Every byte maps to exactly one token per tongue. Format: `tongue:prefix'suffix`. Example: `ko:vel'an` encodes byte 0x2A in Kor'aelin. 256 tokens per tongue, 1536 total. O(1) encode/decode.

- Location: `sacred_tongues.py`, `cli_toolkit.py`
- Docs: `docs/SS1_TOKENIZER_PROTOCOL.md`

### 4.4 Dual Lattice (Quasicrystal Consensus)

6D icosahedral quasicrystal projected into physical space. Phason flips trigger cryptographic re-keying. FFT defect channel for covert signaling. Provides spatial indexing for the 21D canonical state.

- Location: `src/harmonic/qcLattice.ts`
- Docs: `docs/DUAL_LATTICE_STACK_V2.md`

### 4.5 PHDM (Polyhedral Hamiltonian Dynamic Mesh)

16 polyhedra as cognitive nodes: 5 Platonic (safe core), 3 Archimedean (complex reasoning), 2 Kepler-Poinsot (adversarial/high-risk), 6 specialized. Each has an energy cost. Reasoning paths obey Hamiltonian conservation. Adversarial paths exhaust energy budgets before reaching targets.

- Location: `src/harmonic/hamiltonianCFI.ts`
- Docs: `docs/CHAPTER_6_PHDM_POLYHEDRAL_HAMILTONIAN_DYNAMIC_MESH.md`

### 4.6 HYDRA (Multi-Agent Coordination)

Distributed agent coordination with Byzantine fault tolerance. Uses L11 triadic temporal distance for consensus. Manages headless multi-agent missions with governance checkpoints.

- Location: `hydra/`
- Docs: `docs/HYDRA_MULTI_AGENT_COORDINATION_SYSTEM_COMPLETE_ARCHITECTURE.md`

### 4.7 21D Canonical State (Brain)

Every entity in the system is represented as a 21-dimensional state vector:

| Dims | Subsystem |
|------|-----------|
| 1-3 | SCBE context |
| 4-6 | Dual Lattice perpendicular space |
| 7-9 | PHDM cognitive position |
| 10-12 | Sacred Tongues phase |
| 13-15 | M4 model position |
| 16-18 | Swarm composite node state |
| 19-21 | HYDRA ordering / meta |

- Reference: `src/m4mesh/canonical_state.py`, `docs/MASTER_SPEC_M4_21D.md`

### 4.8 GeoSeed Network (Design Phase)

Geometric Bit Dressing system. Bits traversing the 14-layer pipeline produce dressed tokens with geometric provenance. Three tiers: F1 (training), F2 (inference interop), F3 (identity genesis). Uses Cl(6,0) Clifford algebra (64 components) over 6 icosahedral sphere grids (3852 nodes total).

- Docs: `docs/plans/2026-02-26-geoseed-network-design.md`

---

## 5. Repository Structure

```
SCBE-AETHERMOORE/
|-- src/                              # TypeScript core (canonical)
|   |-- harmonic/                     # 14-Layer Pipeline
|   |   |-- pipeline14.ts            # L1-L14 implementation
|   |   |-- hyperbolic.ts            # L5 distance, Mobius addition
|   |   |-- harmonicScaling.ts       # L12 harmonic wall
|   |   |-- hamiltonianCFI.ts        # L8 PHDM / realm navigation
|   |   |-- qcLattice.ts             # Dual Lattice quasicrystal
|   |-- crypto/                       # PQC: ML-KEM-768, ML-DSA-65, AES-256-GCM
|   |-- spectral/                     # L9-L10 FFT coherence
|   |-- ai_brain/                     # 21D Brain mapping (TS)
|   |-- fleet/                        # Multi-agent orchestration
|   |-- gateway/                      # Unified API gateway
|   |-- geoseal.ts                    # GeoSeal immune RAG
|   |-- symphonic_cipher/             # Python reference impl
|   |   |-- scbe_aethermoore/
|   |       |-- layers/
|   |       |   |-- fourteen_layer_pipeline.py  # Full 14-layer (Python)
|   |       |-- axiom_grouped/        # 5 Quantum Axiom implementations
|   |       |-- ai_brain/             # 21D brain mapping (Python)
|   |       |-- pqc/                  # Post-quantum crypto (Python)
|-- tests/                            # Test suites
|-- packages/                         # NPM package exports
|   |-- kernel/src/languesMetric.ts   # LWS implementation
|-- hydra/                            # HYDRA multi-agent system
|-- agents/                           # Agent implementations
|-- training-data/                    # SFT/DPO training pairs
|-- docs/                             # Documentation (you are here)
|-- config/                           # Configuration files
|-- scripts/                          # Build and deployment
|-- demo/                             # Demos including Tuxemon mod
```

---

## 6. Quick Validation

```bash
# Python: validate a governance decision
python -c "
from symphonic_cipher.scbe_aethermoore.qc_lattice import quick_validate
result = quick_validate('user123', 'read_data')
print(f'Decision: {result.decision.value}')
"

# TypeScript: build and test
npm run build
npm test

# Python: run full test suite
python -m pytest tests/ -v

# Python: run PQC tests specifically
python -m pytest tests/test_pqc.py -v

# Python: run benchmarks
python symphonic_cipher/scbe_aethermoore/axiom_grouped/benchmark_comparison.py
```

---

## 7. Working Guidelines

### DOs

- **DO** tag files with `@layer` comments indicating which of the 14 layers your code touches.
- **DO** add axiom compliance comments: `# A4: Clamping`, `// A3: Metric invariance`.
- **DO** write tests in the correct tier (L1-basic through L6-adversarial).
- **DO** label which weight profile (LWS or PHDM) is active in any experiment or claim.
- **DO** preserve the L5 hyperbolic distance invariant. All transforms in L6-L7 must be isometries or diffeomorphisms.
- **DO** use the 21D canonical state vector format when representing entities.
- **DO** keep TypeScript and Python implementations in sync. TypeScript is canonical.
- **DO** use commit convention: `feat(harmonic):`, `fix(crypto):`, `test(spectral):`, etc.
- **DO** check `LAYER_INDEX.md` and `CLAUDE.md` before making architectural changes.

### DON'Ts

- **DON'T** modify L5 (hyperbolic distance). It is the invariant. Everything else can change; L5 cannot.
- **DON'T** mix LWS and PHDM weight profiles without explicit conversion and labeling.
- **DON'T** confuse the two `symphonic_cipher/` directories. Root uses `H(d,R) = R^(d^2)` (exponential cost). `src/` uses `H(d,pd) = 1/(1+d+2*pd)` (bounded score). See CLAUDE.md for details.
- **DON'T** bypass Sacred Egg validation for identity creation. Seeds require full ritual validation.
- **DON'T** push directly to `main`. Use branch-first workflow.
- **DON'T** claim one universal harmonic formula across all modules. Different modules use different L12 regimes. Tag them.
- **DON'T** skip the Poincare ball projection. Raw embeddings must pass through `projectToBall()` before any hyperbolic operations.
- **DON'T** use `sys.path.insert(0, "src/")` without understanding the import collision between the two `symphonic_cipher` packages.

---

## 8. Critical Gotcha: Two Harmonic Wall Formulas

There are two `symphonic_cipher/` directories with different math:

| Location | Formula | Output Range | Use Case |
|----------|---------|-------------|----------|
| Root `symphonic_cipher/` | H(d,R) = R^(d^2) | [1, infinity) | Exponential cost multiplier for adversarial paths |
| `src/symphonic_cipher/` | H(d,pd) = 1/(1+d+2*pd) | (0, 1] | Bounded safety score for governance decisions |

Tests use a `_IS_SAFETY_SCORE` flag to detect which variant loaded. When importing, be explicit about which module you need.

---

## 9. Key Notion Page References

| Page | Notion ID | Purpose |
|------|-----------|---------|
| Master Wiki & Navigation Hub | `0414bbae-8417-4a97-9cd4-d279af7ef8d7` | Top-level navigation |
| SCBE-AETHERMOORE Hub | `300f96de-82e5-80d0-9a66-cdd048e5cab5` | Central system hub |
| Core Theorems (arXiv candidate) | `cef7755e-a1b2-418e-88f7-5b1c38f1f50e` | Mathematical proofs |
| Complete Math & Security Spec | `2d7f96de-82e5-803e-b8a4-ec918262b980` | Full specification |
| Sacred Eggs Protocol | `069c0520-a59c-4c56-8099-c83236625ae8` | Genesis protocol |
| Sacred Tongue Tokenizer Chapter | `1b9b084c-992b-42d5-b47d-4e411c133c7b` | Tokenizer reference |
| SS1 Tokenizer Protocol | `191399b1-ded0-4bcc-a16f-983c7f6769c3` | SS1 encoding spec |
| GeoSeal Trust Manifold | `e98b6184-d102-4ce9-9d21-34463ff3de1c` | GeoSeal architecture |
| HYDRA Architecture | `0ecedff1-2370-4e65-b249-897bf534d6ef` | Multi-agent coordination |
| 21D Master Spec (M4) | `310f96de-82e5-8117-9333-f801f5076610` | 21D canonical state |

---

## 10. For ChatGPT Operators

If you are a ChatGPT instance working on this codebase:

1. **Context window management:** This is a large codebase. Focus on the specific layer or subsystem mentioned in the user's request. Use `LAYER_INDEX.md` to find the right files.
2. **Math notation:** The codebase uses LaTeX-style math in docs. When generating code, translate formulas directly. Do not approximate.
3. **Two implementations:** TypeScript is canonical. If the user asks you to implement something, do TypeScript first unless they specify Python.
4. **Weight profiles:** Always ask which profile (LWS or PHDM) before generating code that touches tongue weights. They produce different numbers.
5. **Testing:** Use Vitest for TypeScript, pytest for Python. Tier your tests (L1-L6). See `CLAUDE.md` for marker conventions.
6. **Import collision:** If you write Python tests, be aware of the dual `symphonic_cipher` packages. Add explicit path handling or use the `_IS_SAFETY_SCORE` detection pattern.

---

## 11. For Claude Operators

If you are a Claude instance (Claude Code, Claude API, or Codex) working on this codebase:

1. **CLAUDE.md is your primary reference.** It lives at the repo root and contains build commands, architecture details, and coding conventions. This AI Operator README supplements it; it does not replace it.
2. **Branch:** The primary working branch is `codex/implement-mission-specifications-and-job-execution`. Check which branch you are on before committing.
3. **Skills:** There are custom skills in `.claude/skills/` and `~/.claude/skills/` covering Tuxemon mod development, agent handoff, multi-agent orchestration, and review gates. Load relevant skills before specialized tasks.
4. **MCP:** The Docker MCP gateway is configured in `~/.claude.json`. Use it for GitHub operations, file management, and browser automation.
5. **Gacha Isekai subsystem:** Located in `src/gacha_isekai/`. Full gacha tower combat integrated with SCBE governance. See `demo/gacha_squad_demo.py`.
6. **Tuxemon mod:** Located in `demo/tuxemon_src/mods/aethermoor/`. AI training simulator disguised as a Pokemon-style game. Battle telemetry generates training data via combat blockchain.
7. **Patent sensitivity:** This codebase has pending patent claims. Do not publish implementation details outside the repository without explicit authorization. Refer to `PATENT_CLAIMS_COVERAGE.md` and `SCBE_PATENT_PORTFOLIO.md`.

---

## 12. Five Core Axioms

The system enforces five quantum-inspired axioms across all 14 layers:

| Axiom | Name | Layers | Implementation |
|-------|------|--------|----------------|
| A1 | Unitarity | L2, L4, L7 | Norm preservation through transforms |
| A2 | Locality | L3, L8 | Spatial bounds on influence |
| A3 | Causality | L6, L11, L13 | Time-ordering of decisions |
| A4 | Symmetry | L5, L9, L10, L12 | Gauge invariance of the metric |
| A5 | Composition | L1, L14 | Pipeline integrity (input/output consistency) |

Each axiom has a Python implementation in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`.

---

## 13. Quick Reference Card

```
Poincare ball:       B^n = { u : ||u|| < 1 }
Hyperbolic distance: d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
Langues metric:      L(x,t) = sum_l w_l * exp(beta_l * (d_l + sin(omega_l*t + phi_l)))
Harmonic wall:       H(d,R) = R^(d^2)  [exponential]
                     H(d,pd) = 1/(1+d+2*pd)  [bounded]
Decision tiers:      ALLOW < QUARANTINE < ESCALATE < DENY
Tongue order:        KO(0) -> AV(60) -> RU(120) -> CA(180) -> UM(240) -> DR(300)
Phi scaling:         phi = 1.618..., weights: 1.0, 1.618, 2.618, 4.236, 6.854, 11.090
21D state:           [SCBE(3) | DualLattice(3) | PHDM(3) | Tongues(3) | M4(3) | Swarm(3) | HYDRA(3)]
Flux states:         Polly(>=0.9) | Quasi(0.5-0.9) | Demi(0.1-0.5) | Collapsed(<0.1)
```
