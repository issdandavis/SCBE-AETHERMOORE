# Grand Unified Statement

> The single governance decision function that unifies all 14 layers.

## The Function

```
G(xi, i, poly) -> {ALLOW, DENY, QUARANTINE}
```

Where:
- **xi** = 9D state vector `[c(t), tau(t), eta(t), q(t)]`
  - `c(t)` = 6D tongue subspace position (Poincare ball)
  - `tau(t)` = temporal flow
  - `eta(t)` = entropy level
  - `q(t)` = quantum coherence
- **i** = intent signal (tongue-encoded)
- **poly** = polyhedral topology (PHDM manifold state)

## Decision Pipeline

1. **State Construction** (L1-L4): Raw input → 9D state xi
2. **Distance Check** (L5): Compute ds² between xi and reference state
3. **Coherence Check** (L9): Spectral residuals < threshold?
4. **Harmonic Cost** (L10): H(d, R) cost evaluation
5. **Manifold Validation** (L11): Riemannian distance within epsilon?
6. **Entropy Gate** (L12): rho_e within bounds?
7. **Consensus** (L12-L13): BFT vote among governing agents
8. **Envelope** (L14): PQC-sign the decision

If ALL gates pass → **ALLOW**
If entropy/coherence marginal → **QUARANTINE** (hold for review)
If ANY hard constraint violated → **DENY**

## The Harmonic Wall

Two variants exist in the codebase:
- **Root**: `H(d, R) = R^(d²)` — exponential cost multiplier (governance cost)
- **Safety**: `H(d, pd) = 1/(1 + d + 2*pd)` — bounded [0,1] safety score

See [[Harmonic Wall]] for full details.

## Cross-References
- [[14-Layer Architecture]] — Layer-by-layer breakdown
- [[CDDM Framework]] — Maps governance domains to physical/narrative
- [[Tongue Domain Mappings]] — How tongues encode intent
- [[Dual Lattice Framework]] — PQC dual consensus

## Academic Grounding
- Aaronson (2005) "NP-complete Problems and Physical Reality" — computational bounds
- Amari (1998) "Natural Gradient Works Efficiently in Learning" — information geometry
- [[Category Theory References]] — G as a natural transformation between categories
