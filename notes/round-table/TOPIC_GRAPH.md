# TOPIC GRAPH -- Round Table Knowledge Map

**Generated:** 2026-03-20
**Notes indexed:** 20 files in `notes/round-table/`
**Concepts extracted:** 47 primary, 23 bridge

---

## 1. Concept Index

Each concept listed with its home note(s) and the cluster it belongs to.

### Cluster A: Mirror / Reflection / Differential

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| Mirror Problem | `2026-03-18-mirror-problem-and-introspection-architecture` | A1 |
| Mirror Differential Telemetry | `2026-03-19-mirror-differential-telemetry-and-riemann-attempt` | A2 |
| Mirror Health Score | `2026-03-19-mirror-differential-math-verification` | A3 |
| Whole-Mirror M_w | `2026-03-19-mirror-differential-math-verification` | A4 |
| Edge-Mirror M_e (Mobius) | `2026-03-19-mirror-differential-math-verification` | A5 |
| Thermal Mirror Probe | `2026-03-19-thermal-mirror-probe-results` | A6 |
| Riemann xi(s) Decomposition | `2026-03-19-mirror-differential-telemetry-and-riemann-attempt` | A7 |
| Decimal Drift Hypothesis | `2026-03-18-mirror-problem-and-introspection-architecture` | A8 |

### Cluster B: Spectral / FFT / Attention Probing

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| S_spec Formula (L9) | `2026-03-19-mirror-probe-first-results` | B1 |
| U-Shaped Depth Curve | `2026-03-19-mirror-probe-first-results` | B2 |
| Raw Q/K/V Weight FFT | `2026-03-19-h1b-raw-qkv-breakthrough-and-mirror-cstm-followup` | B3 |
| Softmax Blinding | `2026-03-19-unified-attention-probe-synthesis` | B4 |
| Head Specialization Gradient | `2026-03-19-mirror-probe-first-results` | B5 |
| SVD Spectrum Analysis | `2026-03-19-unified-attention-probe-synthesis` | B6 |
| Semantic vs Control Delta | `2026-03-19-mirror-probe-first-results` | B7 |

### Cluster C: Phase Tunnel / Governance Gate

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| PhaseTunnelGate | `2026-03-19-phase-tunnel-resonance-finding` | C1 |
| Mode-Selective Governance | `2026-03-19-phase-tunnel-resonance-finding` | C2 |
| Q/K/V Resonance Angles | `2026-03-19-phase-tunnel-resonance-finding` | C3 |
| OPT-1.3B Scale Validation | `2026-03-19-opt-1.3b-phase-tunnel-validation` | C4 |
| Superlinear Scaling (174x) | `2026-03-19-opt-1.3b-phase-tunnel-validation` | C5 |
| Behavioral Ablation Test | `2026-03-19-opt-1.3b-phase-tunnel-validation` | C6 |

### Cluster D: Nursery / Genesis / Training

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| Sacred Egg Genesis | `2026-03-17-sacred-egg-model-genesis` | D1 |
| Trit Matrix Weight Assignment | `2026-03-17-sacred-egg-model-genesis` | D2 |
| Chemistry Dimensional Analysis | `2026-03-17-sacred-egg-model-genesis` | D3 |
| Parent-Guided Nursery | `2026-03-19-nursery-architecture-and-intent-tomography` | D4 |
| Factorial Maturity | `2026-03-19-nursery-architecture-and-intent-tomography` | D5 |
| CSTM Nursery Runner | `2026-03-19-h1b-raw-qkv-breakthrough-and-mirror-cstm-followup` | D6 |
| Fairmath-Poincare Bridge | `2026-03-19-session-log` (Phase 9) | D7 |

### Cluster E: Fundamental Theory / Formulas

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| Davis Formula S(t,i,C,d) | `2026-03-19-mirror-differential-math-verification` | E1 |
| Harmonic Wall H(d,R)=R^(d^2) | `2026-03-19-mirror-differential-math-verification` | E2 |
| H_score (bounded) | `2026-03-19-mirror-differential-math-verification` | E3 |
| Breathing Transform (L6) | `2026-03-19-mirror-differential-math-verification` | E4 |
| Recursive Realification | `2026-03-18-recursive-realification-and-context-as-imaginary` | E5 |
| Context as Imaginary Number | `2026-03-18-recursive-realification-and-context-as-imaginary` | E6 |
| Langues Metric (phi-scaled) | `2026-03-19-unified-attention-probe-synthesis` | E7 |

### Cluster F: Communication / Conversation / Training Data

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| Spin Conversation (D&D combat) | `2026-03-20-spin-conversation-combat-research-mode` | F1 |
| Radial Matrix Array | `2026-03-20-spin-conversation-combat-research-mode` | F2 |
| PivotKnowledge System | `demo/pivot_knowledge.py` | F3 |
| Sacred Tongues (6) | Multiple | F4 |
| Multi-Model Convergence | `2026-03-18-research-pipeline-concept` | F5 |

### Cluster G: Architecture / Infrastructure

| Concept | Home Note(s) | Shorthand |
|---------|-------------|-----------|
| Introspection Architecture | `2026-03-18-mirror-problem-and-introspection-architecture` | G1 |
| Orthogonal Temporal Witness | `2026-03-19-nursery-architecture-and-intent-tomography` | G2 |
| Intent Tomography | `2026-03-19-nursery-architecture-and-intent-tomography` | G3 |
| Masquerade Detection | `2026-03-19-nursery-architecture-and-intent-tomography` | G4 |
| Session-Bound Capability Probes | `2026-03-19-nursery-architecture-and-intent-tomography` | G5 |
| Colab Bridge | `2026-03-19-colab-bridge-established` | G6 |
| Multiple Go Boards | `2026-03-18-mirror-problem-and-introspection-architecture` | G7 |

---

## 2. Connection Map (ASCII)

```
                    +-----------+
                    |  MIRROR   |
                    |  CLUSTER  |
                    |  (A1-A8)  |
                    +-----+-----+
                          |
            Mirror Health  |  Thermal suppression
            Score (A3)     |  reveals Q structure
                    +------+------+
                    |             |
              +-----+-----+ +----+------+
              |  SPECTRAL  | |  PHASE    |
              |  CLUSTER   +-+  TUNNEL   |
              |  (B1-B7)   | |  CLUSTER  |
              +-----+------+ |  (C1-C6)  |
                    |        +----+------+
                    |             |
    S_spec applied  |    Resonance angles per
    to Q/K/V weights|    Q/K/V = governance handle
                    |             |
              +-----+------+     |
              |  THEORY    +-----+
              |  CLUSTER   |
              |  (E1-E7)   |  Harmonic wall as
              +-----+------+  phase tunnel cost
                    |
     Davis Formula  |  Factorial maturity
     context moat   |  same C! structure
                    |
              +-----+------+
              |  NURSERY   |
              |  CLUSTER   |
              |  (D1-D7)   |
              +-----+------+
                    |
   Sacred Egg       |  Genesis -> training data
   = startup.txt    |  = SFT/DPO pairs
                    |
              +-----+------+
              | CONVO /    |
              | TRAINING   |
              | CLUSTER    |
              | (F1-F5)    |
              +-----+------+
                    |
   Pivot = topic    |  Combat mode =
   transition       |  research phase
                    |
              +-----+------+
              |  ARCH /    |
              |  INFRA     |
              |  CLUSTER   |
              |  (G1-G7)   |
              +------------+
```

---

## 3. Cross-Cluster Bridges (existing connections found in notes)

| Bridge | From -> To | Evidence |
|--------|-----------|----------|
| Thermal mirror reveals Q structure | A6 -> B3 | Both notes reference the same DistilBERT Q finding |
| xi(s) decomposition = 14-layer pipeline | A7 -> E2, E4 | L6/Gamma analogy in mirror-differential-telemetry |
| S_spec applied to attention weights | B1 -> B3 | Unified probe synthesis combines both |
| PhaseTunnelGate uses S_spec | C1 -> B1 | Resonance computed from spectral density |
| Factorial maturity = Davis Formula C! | D5 -> E1 | nursery-architecture note, table row |
| Sacred Egg = ChoiceScript startup.txt | D1 -> D7 | Session log, Phase 9 |
| Spin conversation uses radial matrix | F1 -> F2 | Same note |
| Orthogonal witness = "Pluto layer" | G2 -> B1 | Intent tomography uses spectral sampling |
| Masquerade detection = Langues Metric accent | G4 -> F4 | nursery-architecture note, table row |
| Multiple Go boards = multi-head attention | G7 -> B3, C3 | mirror-problem note + phase-tunnel finding |

---

## 4. MISSING BRIDGES -- Pivot Connection Opportunities

These are concept pairs that share deep structural similarity but have NO dedicated note connecting them. Each becomes a new "pivot note."

| Gap ID | Concept A | Concept B | Why they connect | New Note |
|--------|-----------|-----------|-----------------|----------|
| **P1** | PhaseTunnelGate resonance angles (C3) | Sacred Tongues weights (F4) | Both are 6-element phi-scaled systems; resonance angles per Q/K/V might map to KO/AV/RU tongue weights | `2026-03-20-phase-tunnel-tongue-mapping` |
| **P2** | Recursive Realification (E5) | Nursery Genesis Phases (D4) | Each hatching level IS a realification; the nursery shadow/overlap/autonomy phases mirror the C^D -> R^2D -> R^4D tower | `2026-03-20-recursive-realification-as-nursery-depth` |
| **P3** | Mirror Health Score (A3) | Spin Conversation combat mode (F1) | Mirror health = HP for research problems; the MH(T) score IS the "damage meter" for combat research mode | `2026-03-20-mirror-health-as-combat-hp` |
| **P4** | Thermal Mirror "quiet regions carry signal" (A6) | Intent Tomography / Masquerade Detection (G3, G4) | The finding that low-activation regions carry spectral signal maps directly to masquerade detection: the "quiet" behavior reveals the real identity | `2026-03-20-thermal-silence-as-intent-witness` |
| **P5** | Chemistry Dimensional Analysis (D3) | Davis Formula factorial moat (E1) | The chemistry metaphor (bonds, valence, orbital energy) IS a physical interpretation of the Davis Formula's C! term; each context dimension is a molecular orbital | `2026-03-20-molecular-orbitals-of-context` |

---

## 5. Note Chronology

```
2026-03-17  session-recap
            sacred-egg-model-genesis
2026-03-18  next-session-plan
            research-pipeline-concept
            mirror-problem-and-introspection-architecture
            recursive-realification-and-context-as-imaginary
2026-03-19  mirror-probe-first-results
            nursery-architecture-and-intent-tomography
            unified-attention-probe-synthesis
            mirror-differential-telemetry-and-riemann-attempt
            h1b-raw-qkv-breakthrough-and-mirror-cstm-followup
            session-log
            mirror-differential-math-verification
            thermal-mirror-probe-results
            phase-tunnel-resonance-finding
            colab-bridge-established
            research-publishing-and-search-handoff
            opt-1.3b-phase-tunnel-validation
2026-03-20  spin-conversation-combat-research-mode
            [NEW] phase-tunnel-tongue-mapping           (P1)
            [NEW] recursive-realification-as-nursery-depth  (P2)
            [NEW] mirror-health-as-combat-hp            (P3)
            [NEW] thermal-silence-as-intent-witness     (P4)
            [NEW] molecular-orbitals-of-context          (P5)
```
