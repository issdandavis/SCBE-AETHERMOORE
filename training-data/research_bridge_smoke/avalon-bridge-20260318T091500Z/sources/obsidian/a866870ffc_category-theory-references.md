# Category Theory References

> Academic foundations for the CDDM framework's categorical structure.

## Core Texts

### Foundational
1. **Mac Lane, S. (1971)** "Categories for the Working Mathematician" — Springer
   - The original. Defines categories, functors, natural transformations
   - Relevant to: [[CDDM Framework]] (composition, identity, associativity)
   - Key insight: morphism composition is *the* organizing principle

2. **Awodey, S. (2010)** "Category Theory" — Oxford Logic Guides
   - More accessible introduction, good for self-study
   - Relevant to: Domain/Morphism class design

### Applied Category Theory
3. **Fong, B. & Spivak, D.I. (2019)** "An Invitation to Applied Category Theory: Seven Sketches in Compositionality" — Cambridge University Press
   - **Primary reference for CDDM**
   - Chapter 1 (Generative Effects): How morphisms between ordered sets model causal processes
   - Chapter 4 (Collaborative Design): Profunctor composition for multi-domain integration
   - Free: [arXiv:1803.05316](https://arxiv.org/abs/1803.05316)

4. **Spivak, D.I. (2014)** "Category Theory for the Sciences" — MIT Press
   - Cross-domain mapping as functorial translation
   - Relevant to: [[Tongue Domain Mappings]] (mapping physical to narrative domains)

5. **Baez, J.C. & Stay, M. (2011)** "Physics, Topology, Logic and Computation: A Rosetta Stone" — Springer Lecture Notes in Physics
   - The definitive paper on using categories to translate between domains
   - Relevant to: The entire CDDM premise (energy <-> motivation via functors)
   - Free: [arXiv:0903.0340](https://arxiv.org/abs/0903.0340)

### Graph Isomorphism
6. **Cordella, L.P. et al. (2004)** "A (Sub)Graph Isomorphism Algorithm for Matching Large Graphs" — IEEE TPAMI
   - VF2 algorithm — basis for our `GraphIsomorphism` implementation
   - Relevant to: `functor.py` backtracking search

## How CDDM Uses Category Theory

| CT Concept | CDDM Implementation | File |
|-----------|---------------------|------|
| Object | `Domain` | `domain.py` |
| Arrow/Morphism | `Morphism` | `morphism.py` |
| Composition | `compose()`, `CompositionChain` | `functor.py` |
| Identity | `identity_morphism()` | `functor.py` |
| Functor | `DomainGraph` path finding | `functor.py` |
| Natural transformation | Cross-tongue morphisms | `tongue_domains.py` |

## Cross-References
- [[CDDM Framework]] — Implementation using these foundations
- [[Hyperbolic Geometry References]] — For the embedding space
- [[Grand Unified Statement]] — G as a natural transformation
