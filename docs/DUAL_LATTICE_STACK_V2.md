# DualLatticeStack v2: Quasicrystal x Hyperbolic x GeoSeal

> Updated diagram spec aligned with SCBE v1.2, Symphonic Cipher, and GeoSeal immune RAG layer.

---

## Stack Layers (top to bottom)

### Layer 1: Quasicrystal

```
Quasicrystal: 6D projection, phason rekey, FFT defect channel
```

- **6D projection**: Icosahedral quasicrystal projected from 6D superspace
- **Phason rekey**: Quasicrystal phason flips trigger cryptographic re-keying
- **FFT defect channel**: Fourier analysis of lattice defects for covert signaling
- **Files**: `src/harmonic/qcLattice.ts`, `src/spectral/index.ts`

### Layer 2: Hyperbolic Governance

```
Hyperbolic: 9D SCBE state, breathing + phase, triadic risk
```

- **9D SCBE state**: Full state vector in Poincare ball (embedding + phase + drift + coherence)
- **Breathing + phase**: Mobius phase modulation and breathing transform (L6-L7)
- **Triadic risk**: Three-axis risk assessment (d_star, coherence, h_eff) -> ALLOW/QUARANTINE/DENY
- **Files**: `src/harmonic/hyperbolic.ts`, `src/harmonic/pipeline14.ts`, `src/harmonic/harmonicScaling.ts`

### Layer 3: Hamiltonian CFI

```
Hamiltonian CFI: lifted CFG, golden path, realm-aligned execution
```

- **Lifted CFG**: Context-free grammar lifted to Hamiltonian control flow graph
- **Golden path**: Phi-weighted optimal traversal through security realms
- **Realm-aligned execution**: Execution constrained to authorized multi-well potential realms (L8)
- **Files**: `src/harmonic/hamiltonianCFI.ts`

### Layer 4: GeoSeal + Entropic

```
GeoSeal + Entropic: immune RAG swarm, quarantine, adaptive k
```

- **Immune RAG swarm**: Phase-discipline swarm dynamics detect/quarantine adversarial retrievals
- **Quarantine**: Spatial consensus (3+ neighbors) pushes rogue agents to manifold boundary
- **Adaptive k**: Entropy-based adaptive parameter tuning for retrieval threshold
- **v2 extension**: Mixed-curvature product manifold H^a x S^b x R^c with uncertainty scoring
- **Files**: `src/geoseal.ts`, `src/geoseal-v2.ts`, `src/geosealRAG.ts`, `src/geosealMetrics.ts`

---

## Integration Points

```
+------------------------------------------------------------------+
|  Quasicrystal: 6D projection, phason rekey, FFT defect channel   |
+------------------------------------------------------------------+
        |  phason events trigger rekey  |  FFT defects -> L14 telemetry
        v                               v
+------------------------------------------------------------------+
|  Hyperbolic: 9D SCBE state, breathing + phase, triadic risk      |
+------------------------------------------------------------------+
        |  d_star + coherence + h_eff   |  phase -> tongue assignment
        v                               v
+------------------------------------------------------------------+
|  Hamiltonian CFI: lifted CFG, golden path, realm-aligned exec    |
+------------------------------------------------------------------+
        |  realm constraints            |  golden path -> execution trace
        v                               v
+------------------------------------------------------------------+
|  GeoSeal + Entropic: immune RAG swarm, quarantine, adaptive k    |
+------------------------------------------------------------------+
```

## Scoring Flow (GeoSeal v2)

```
Retrieval chunk
     |
     v
+------------------+     +------------------+     +------------------+
| Hyperbolic score |     | Phase score      |     | Gaussian score   |
| s_H = 1/(1+d_H) |     | s_S = 1-phaseDev |     | s_G = 1/(1+sig)  |
+------------------+     +------------------+     +------------------+
     |         w_H=0.4         |    w_S=0.35        |    w_G=0.25
     +------------+------------+----------+----------+
                  |                       |
                  v                       v
          trust = w_H*s_H + w_S*s_S + w_G*s_G
                  |
     +------------+------------+
     |            |            |
  >= 0.7       >= 0.3       < 0.3
   ALLOW     QUARANTINE      DENY
```

## Layer Mapping

| Stack Layer | Pipeline Layers | Primary Axiom |
|-------------|----------------|---------------|
| Quasicrystal | L9-L10 | Symmetry |
| Hyperbolic | L4-L7, L12 | Unitarity, Symmetry |
| Hamiltonian CFI | L8, L13 | Locality, Causality |
| GeoSeal + Entropic | L9, L12-L13 | Composition |

---

*Document maintained by: @Issac Davis*
*Architecture family: Spiralverse Protocol v2.x / DualLatticeStack v2*
