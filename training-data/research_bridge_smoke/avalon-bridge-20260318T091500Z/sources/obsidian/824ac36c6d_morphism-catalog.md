# Morphism Catalog

> Complete inventory of registered cross-domain morphisms in the CDDM framework.

## Intra-Tongue Morphisms (Physical -> Narrative/Governance)

| Key | Name | Source | Dest | Function | Invertible |
|-----|------|--------|------|----------|-----------|
| `energy_to_authority` | Energy->Authority | Energy [0,1M] | Authority [0,10] | log(x+1)/log(1M) | Yes |
| `energy_to_command` | Energy->Command | Energy [0,1M] | CommandForce [0,100] | x * 1e-4 | Yes |
| `momentum_to_comm` | Momentum->Communication | Momentum [0,100K] | Communication [0,10] | log scale | No |
| `momentum_to_dataflow` | Momentum->DataFlow | Momentum [0,100K] | DataFlow [0,10K] | x * 0.1 | Yes |
| `entropy_to_chaos` | Entropy->PlotChaos | Entropy [0,1K] | PlotChaos [0,10] | sigmoid(500, 0.01) | No |
| `entropy_to_breakdown` | Entropy->PolicyBreakdown | Entropy [0,1K] | PolicyBreakdown [0,100] | x * 0.1 | Yes |
| `complexity_to_intrigue` | Complexity->Intrigue | Complexity [0,1T] | Intrigue [0,10] | log scale | No |
| `risk_to_danger` | Risk->Danger | Risk [0,1] | Danger [0,10] | x * 10 | Yes |
| `risk_to_threat` | Risk->ThreatIndex | Risk [0,1] | ThreatIndex [0,100] | x * 100 | Yes |
| `structure_to_world` | Structure->WorldComplexity | Structure [0,1M] | WorldComplexity [0,10] | log scale | No |
| `structure_to_integrity` | Structure->SchemaIntegrity | Structure [0,1M] | SchemaIntegrity [0,100] | 100*(1-exp(-x/1e5)) | No |

## Cross-Tongue Morphisms (Narrative <-> Narrative)

| Key | Name | Source | Dest | Function | Invertible |
|-----|------|--------|------|----------|-----------|
| `authority_to_danger` | Authority->Danger | Authority [0,10] | Danger [0,10] | 10 - x | Yes |
| `chaos_to_intrigue` | PlotChaos->Intrigue | PlotChaos [0,10] | Intrigue [0,10] | min(10, x*1.2) | No |

## Morphism Properties

### Invertibility
- **7 of 14** morphisms are invertible (round-trip validated)
- Log-scale morphisms are not invertible (information loss at boundaries)
- Sigmoid morphisms are not invertible (many-to-one at saturation)

### Function Types
- **Linear**: 5 morphisms (simplest, always invertible)
- **Logarithmic**: 4 morphisms (compresses large ranges)
- **Sigmoid**: 1 morphism (S-curve with saturation)
- **Exponential saturation**: 1 morphism (approaches ceiling)
- **Reflection**: 1 morphism (f(x) = c - x, self-inverse)
- **Capped linear**: 1 morphism (min(cap, x*k))

## Adding New Morphisms

```python
from cddm import Domain, Morphism, CROSS_DOMAIN_MAP

# Define domains
src = Domain("MyDomain", units=("MyUnit",), bounds=(0, 100))
dst = Domain("Target", units=("TgtUnit",), bounds=(0, 1))

# Create morphism
m = Morphism(src, dst, func=lambda x: x / 100, inverse_func=lambda y: y * 100)

# Register
CROSS_DOMAIN_MAP["my_mapping"] = m
```

## Cross-References
- [[CDDM Framework]] — Framework overview
- [[Tongue Domain Mappings]] — Domain definitions per tongue
- [[Composition Chains]] — How to chain morphisms
