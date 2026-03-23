# Composition Chains

> Multi-step cross-domain pipelines built from chained morphisms.

## What Is a Composition Chain?

A sequence of morphisms where each step's destination is the next step's source:

```
Energy --[log]--> Authority --[reflect]--> Danger
  KO physical      KO narrative              UM narrative
```

## Example Chains

### Energy -> Danger (KO -> UM via narrative)
```python
chain = CompositionChain()
chain.add(CROSS_DOMAIN_MAP["energy_to_authority"])   # Energy -> Authority
chain.add(CROSS_DOMAIN_MAP["authority_to_danger"])    # Authority -> Danger
danger = chain.apply(100_000)  # 100KJ -> ~5.7 authority -> ~4.3 danger
```

**Interpretation**: High energy = high authority = low danger. A powerful entity is safe.

### Entropy -> Intrigue (RU -> CA via narrative)
```python
chain = CompositionChain()
chain.add(CROSS_DOMAIN_MAP["entropy_to_chaos"])       # Entropy -> PlotChaos
chain.add(CROSS_DOMAIN_MAP["chaos_to_intrigue"])       # PlotChaos -> Intrigue
intrigue = chain.apply(800)  # 800 J/K -> ~9.2 chaos -> ~10.0 intrigue
```

**Interpretation**: High entropy = high chaos = maximum intrigue. Disorder is interesting.

## Tracing

Every chain supports `apply_traced()` which returns the value at each step:
```python
trace = chain.apply_traced(100_000)
# [("Energy", 100000), ("Authority", 5.7), ("Danger", 4.3)]
```

## Invertibility

A chain is invertible if ALL its steps are invertible. The inverse chain runs in reverse:
```python
inv = chain.invert()
energy = inv.apply(4.3)  # Danger -> Authority -> Energy
```

## DomainGraph Auto-Chaining

Instead of manually building chains, use DomainGraph's BFS path finder:
```python
graph = DomainGraph()
for m in all_tongue_morphisms():
    graph.add_morphism(m)
chain = graph.build_chain("Energy", "Danger")  # Auto-finds shortest path
```

## Cross-References
- [[CDDM Framework]] — The library
- [[Morphism Catalog]] — Available morphisms to chain
- [[Tongue Domain Mappings]] — Domain definitions
