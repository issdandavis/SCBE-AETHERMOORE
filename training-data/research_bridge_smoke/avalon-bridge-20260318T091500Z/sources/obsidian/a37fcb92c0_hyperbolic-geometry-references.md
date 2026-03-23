# Hyperbolic Geometry References

> Academic foundations for Poincare ball embeddings, ds² metrics, and manifold operations.

## Core Papers

### Poincare Embeddings
1. **Nickel, M. & Kiela, D. (2017)** "Poincare Embeddings for Learning Hierarchical Representations" — NeurIPS
   - **Primary reference for our embedding approach**
   - Proves Poincare ball captures hierarchical structure with fewer dimensions
   - Relevant to: `dual_lattice.py`, 6D tongue subspace, [[Grand Unified Statement]]
   - Free: [arXiv:1705.08039](https://arxiv.org/abs/1705.08039)

2. **Nickel, M. & Kiela, D. (2018)** "Learning Continuous Hierarchies in the Lorentz Model of Hyperbolic Geometry" — ICML
   - Lorentz model as alternative to Poincare ball
   - Relevant to: Future work on alternative embedding models

### Hyperbolic Geometry Foundations
3. **Cannon, J.W. et al. (1997)** "Hyperbolic Geometry" — MSRI Publications
   - Definitive reference for the Poincare disk/ball model
   - ds² formula: `ds² = 4|dx|² / (1 - |x|²)²`
   - Relevant to: [[Harmonic Wall]], distance computations

4. **Ratcliffe, J. (2006)** "Foundations of Hyperbolic Manifolds" — Springer GTM
   - Riemannian metrics on hyperbolic manifolds
   - Relevant to: Layer 11 PHDM manifold validation

### Applied Hyperbolic ML
5. **Ganea, O. et al. (2018)** "Hyperbolic Neural Networks" — NeurIPS
   - Neural network operations in Poincare ball
   - Relevant to: `cymatic_voxel_net.py` (6D Chladni + hyperbolic distance)

6. **Chami, I. et al. (2019)** "Hyperbolic Graph Convolutional Neural Networks" — NeurIPS
   - Graph operations in hyperbolic space
   - Relevant to: DomainGraph in CDDM (future work: hyperbolic graph embeddings)

## How SCBE Uses Hyperbolic Geometry

| Component | Hyperbolic Feature | Reference |
|-----------|-------------------|-----------|
| 6D state embedding | Poincare ball B^6 | Nickel & Kiela 2017 |
| ds² computation | Riemannian distance | Cannon 1997 |
| Harmonic Wall H(d,R) | Distance-based cost | Analogous to WKB barrier |
| Realm centers | Points in B^6 | Ratcliffe 2006 (geodesics) |
| Evolving Lexicons | Drift in B^6 | Ganea 2018 (Poincare operations) |

## Cross-References
- [[Harmonic Wall]] — Uses hyperbolic distance d
- [[Grand Unified Statement]] — 9D state with 6D hyperbolic subspace
- [[CDDM Framework]] — Domain graphs could be embedded hyperbolically
- [[Evolving Lexicons]] — Drift computation in Poincare ball
