# Tongue Domain Mappings

> Each Sacred Tongue governs a conceptual domain with physical, narrative, and governance variants.

## The Six Tongues and Their Domains

### KO — Control
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Energy | Joule | [0, 1M] |
| Narrative | Authority | AuthLevel | [0, 10] |
| Governance | CommandForce | CmdUnit | [0, 100] |

**Morphisms**: Energy -> Authority (log scale), Energy -> CommandForce (linear)

### AV — Transport
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Momentum | kg*m/s | [0, 100K] |
| Narrative | Communication | CommFlow | [0, 10] |
| Governance | DataFlow | Mbps | [0, 10K] |

**Morphisms**: Momentum -> Communication (log), Momentum -> DataFlow (linear)

### RU — Policy
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Entropy | J/K | [0, 1K] |
| Narrative | PlotChaos | ChaosLevel | [0, 10] |
| Governance | PolicyBreakdown | BreakdownIdx | [0, 100] |

**Morphisms**: Entropy -> PlotChaos (sigmoid, midpoint=500), Entropy -> PolicyBreakdown (linear)

### CA — Compute
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Complexity | FLOP | [0, 1T] |
| Narrative | Intrigue | IntrigueLevel | [0, 10] |
| Governance | ComputeLoad | TFLOP | [0, 1K] |

**Morphisms**: Complexity -> Intrigue (log)

### UM — Security
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Risk | RiskScore | [0, 1] |
| Narrative | Danger | DangerLevel | [0, 10] |
| Governance | ThreatIndex | ThreatIdx | [0, 100] |

**Morphisms**: Risk -> Danger (linear x10), Risk -> ThreatIndex (linear x100)

### DR — Schema
| Variant | Domain | Units | Bounds |
|---------|--------|-------|--------|
| Physical | Structure | ShannonBit | [0, 1M] |
| Narrative | WorldComplexity | ComplexityLevel | [0, 10] |
| Governance | SchemaIntegrity | IntegrityPct | [0, 100] |

**Morphisms**: Structure -> WorldComplexity (log), Structure -> SchemaIntegrity (exponential saturation)

## Cross-Tongue Morphisms

| From | To | Name | Meaning |
|------|-----|------|---------|
| KO_narrative (Authority) | UM_narrative (Danger) | authority_to_danger | High authority = low danger |
| RU_narrative (PlotChaos) | CA_narrative (Intrigue) | chaos_to_intrigue | Chaos drives intrigue |

## 3D Spatial Mapping

The [[3D Spatial Engine]] maps tongue pairs to 3D axes:
- **KO + AV -> X axis** (Control + Transport)
- **RU + CA -> Y axis** (Policy + Compute)
- **UM + DR -> Z axis** (Security + Schema)

## Cross-References
- [[CDDM Framework]] — The library implementing these mappings
- [[Six Sacred Tongues]] — Lexicon structure and tokenization
- [[Morphism Catalog]] — Full morphism details with inversion status
- [[Grand Unified Statement]] — How tongue domains feed into G(xi, i, poly)
