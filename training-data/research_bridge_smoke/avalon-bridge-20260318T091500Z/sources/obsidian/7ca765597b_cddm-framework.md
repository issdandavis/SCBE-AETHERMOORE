# CDDM Framework

> Cross-Domain Dimensional Mapping — a category-theoretic library for mapping structural forms across domains.

## What It Does

CDDM provides a rigorous mathematical scaffold for cross-domain translation:

| Physical Domain | Narrative Domain | Governance Domain |
|----------------|-----------------|-------------------|
| Energy (Joule) | Authority (level) | Command Force |
| Momentum (kg*m/s) | Communication (flow) | Data Flow (Mbps) |
| Entropy (J/K) | Plot Chaos (level) | Policy Breakdown |
| Complexity (FLOP) | Processing Load | Compute Load |
| Risk (score) | Danger (level) | Threat Index |
| Structure (bits) | World Complexity | Schema Integrity |

Each mapping is a **Morphism** — a structure-preserving function with bounds validation.

## Core Concepts

### Domain
A bounded, typed region: `Domain(name, units, bounds)`
```python
energy = Domain("Energy", units=("Joule",), bounds=(0, 1e6))
```

### Morphism
A map between domains: `Morphism(src, dst, func)`
```python
e_to_m = Morphism(energy, motivation, lambda x: min(1.0, x / 1e6))
result = e_to_m(500_000)  # -> 0.5
```

### CompositionChain
Chain morphisms: `A -> B -> C -> ...`
```python
chain = CompositionChain()
chain.add(energy_to_authority)
chain.add(authority_to_danger)
danger = chain.apply(100_000)  # Energy -> Authority -> Danger
```

### DomainGraph
Directed graph of domains + morphisms with BFS path finding:
```python
graph = DomainGraph()
graph.add_morphism(energy_to_motivation)
graph.add_morphism(motivation_to_incentive)
chain = graph.build_chain("Energy", "Incentive")
```

### GraphIsomorphism
Check if two domain graphs have the same structure (VF2-lite):
```python
GraphIsomorphism.is_isomorphic(physics_graph, narrative_graph)
```

## File Layout
```
src/cddm/
  __init__.py          # Package exports
  domain.py            # Domain class + validation
  morphism.py          # Morphism class + composition
  functor.py           # CompositionChain, DomainGraph, GraphIsomorphism
  tongue_domains.py    # Sacred Tongue domain definitions + morphisms
  selftest.py          # 7-section selftest (all passing)
```

## Why Category Theory?

The "pseudoscience flag" problem: when you map energy to motivation, critics ask "by what rigorous mechanism?" Category theory answers:

1. **Objects** = Domains (bounded, typed, validated)
2. **Arrows** = Morphisms (bounds-checked, optionally invertible)
3. **Composition** = Chains (associative, traceable)
4. **Functors** = Graph structure preservation (isomorphism checks)

This means every cross-domain claim is mathematically grounded with:
- Explicit bounds (no unbounded mappings)
- Invertibility checks (can you go back?)
- Composition safety (does A->B->C actually land in C's bounds?)

## Cross-References
- [[Tongue Domain Mappings]] — How each tongue maps to 3 domain variants
- [[Morphism Catalog]] — Full list of registered morphisms
- [[Composition Chains]] — Multi-step pipeline examples
- [[14-Layer Architecture]] — CDDM spans Layers 1, 5, and 9
- [[Grand Unified Statement]] — G(xi, i, poly) uses CDDM for state translation

## Academic Grounding
- [[Category Theory References]] — Mac Lane, Awodey, Fong & Spivak
- Spivak (2014) "Category Theory for the Sciences" — applied CT for cross-domain mapping
- Fong & Spivak (2019) "An Invitation to Applied Category Theory" — composition as engineering principle
- Baez & Stay (2011) "Physics, Topology, Logic and Computation" — Rosetta Stone paper connecting categories

## Status
- **v1.0.0** — Implemented 2026-02-22
- 7-section selftest: all passing
- 14 registered morphisms across 6 tongue domains
- Pure stdlib, zero dependencies
