# AetherBrain / PHDM -- Mathematical Framework

> **Extracted from**: AetherBrain Architecture: The Case for Geometric Governance and Stateful Control Layers in Large Language Models (Executive Summary, February 2026)

This document isolates the mathematical and systems-theoretic content from the AetherBrain/PHDM executive summary. No new primitives are introduced; the innovation is in composition.

---

## 1. System Decomposition

### 1.1 Two-Layer Intelligence Model

The system defines a two-layer computational architecture:

**Layer 1 -- Probabilistic Generator (Cortex)**

A stochastic function:

```
f_theta : (x, h_t) -> y
```

**Layer 2 -- Deterministic Control Shell (Skull / Brain Case)**

A stateful, rule-driven operator:

```
G : (s_t, y, c_t) -> {ALLOW, BLOCK, TRANSFORM}
```

Key property: one layer is non-deterministic (generation), one is deterministic and auditable (control). This is control theory, not ML.

---

## 2. Geometric Governance

### 2.1 Hyperbolic Permission Space

The system operates on the Poincare disk / ball model:

```
B^n = { u in R^n : ||u|| < 1 }
```

Hyperbolic distance `d_H(u, v)` serves as:
- A partial order on permissions
- A monotone risk scalar
- A hierarchical embedding (tree-like structure)

### 2.2 Hierarchical Permissioning

Hyperbolic space is chosen because:
- Tree depth is proportional to radial distance
- Boundary = infinite cost
- Near-origin = dense, low-cost region

Permission function:

```
Permission(s) = phi(d_H(s, s_0))
```

where `phi` is monotone. This is order theory embedded in geometry.

---

## 3. Distributed Concealment Storage

### 3.1 Erasure Coding

Reed-Solomon codes over finite fields:

```
Encode: D -> {S_1, ..., S_n}
Decode: {S_i1, ..., S_ik} -> D    (any k of n shards reconstruct)
```

Loss tolerance: `n - k` shards can be lost without data loss.

### 3.2 "Holographic" Property

Mathematically, this is:
- Redundant linear reconstruction
- Information not localized to a single address
- Distributed linear algebra with fault tolerance

---

## 4. Reflexive Gating (Formal Control)

### 4.1 Deterministic Gating

Pre-execution constraint checks with hard decision boundaries:

```
Gate(a_t, s_t) = {
    ALLOW   if g(s_t, a_t) <= tau
    DENY    otherwise
}
```

This is static analysis + runtime enforcement, comparable to hardware interrupt handling.

### 4.2 Tokenized Authority

Capability-based access using cryptographic tokenization:

```
Capability = <id, scope, constraints>
```

Aligns with object-capability models and access control logic.

---

## 5. Control Physics

### 5.1 Energy Landscape

An implicit potential function:

```
V(s) = f(d_H(s, s_0))
```

Where:
- Low energy = allowed behavior
- High energy = forbidden behavior

Equivalent to Lyapunov-style stability analysis and barrier functions in control theory.

### 5.2 Timing Separation (Reflex Arcs)

Two distinct timing domains:
- **Fast deterministic layer** (control) -- reflex arcs
- **Slow stochastic layer** (generation) -- deliberation

This matches real-time systems and safety-critical control loop architecture.

---

## 6. Structural Novelty

Not new math, but new composition:

| Innovation | Description |
|-----------|-------------|
| **A** | Geometry used as authorization lattice, not embedding trick |
| **B** | Erasure coding used as concealment, not durability only |
| **C** | Deterministic gating placed outside the probabilistic model |
| **D** | Stateful control treated as physics, not policy |

This is systems mathematics, not ML novelty.

---

## 7. Scope Boundaries

What this framework does **not** contain:

- No new cryptographic primitives
- No new hardness assumptions
- No new learning algorithm
- No new geometry theorems

The contribution is architectural composition of known mathematical structures.

---

## 8. Minimal Mathematical Identity

Compressed to one statement:

> AetherBrain = deterministic control system over a hyperbolic state space, regulating a stochastic generator via geometric constraints and algebraic storage redundancy

---

## 9. Mapping to SCBE-AETHERMOORE Implementation

| Mathematical Object | Implementation |
|---|---|
| Poincare ball `B^n` | `src/harmonic/hyperbolic.ts` |
| Hyperbolic distance `d_H` | `src/harmonic/hyperbolic.ts`, `src/harmonic/adaptiveNavigator.ts` |
| Potential function `V(s)` | `src/harmonic/harmonicScaling.ts` (Harmonic Wall, L12) |
| Deterministic gate `G` | `src/harmonic/pipeline14.ts` (L13 risk decision) |
| Erasure coding | `src/crypto/envelope.ts`, `src/crypto/pqc.ts` |
| Capability tokens | `src/crypto/nonceManager.ts`, `src/crypto/replayGuard.ts` |
| Permission ordering | `src/harmonic/languesMetric.ts` (Sacred Tongues 6D metric) |
| Energy landscape | `H(d,R) = phi^d / (1 + e^-R)` in `harmonicScaling.ts` |
| Timing separation | 14-layer pipeline (fast L1-L8 control, slow L9-L14 analysis) |
| PHDM drift monitor | `src/harmonic/phdm.ts` |
| Quantum Axiom Mesh | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/` |

---

## References

- SCBE-AETHERMOORE 14-Layer Architecture: `LAYER_INDEX.md`
- System Architecture: `SYSTEM_ARCHITECTURE.md`
- Security Model: `SECURITY.md`
- Hyperbolic geometry implementation: `src/harmonic/hyperbolic.ts`
- Harmonic wall formula: `src/harmonic/harmonicScaling.ts`
