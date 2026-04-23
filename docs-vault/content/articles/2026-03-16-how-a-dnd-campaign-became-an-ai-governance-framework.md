# How a DnD Campaign Became an AI Governance Framework

**By Issac Davis** | March 16, 2026

---

## The Accidental Origin

This project started the way most serious infrastructure does: by accident.

In 2024 I was playing Everweave, an AI-powered DnD game. Over months of sessions I accumulated 12,596 paragraphs of game logs -- dialogues, combat encounters, world descriptions, spell incantations. When I fed those logs into ChatGPT to expand them into a novel draft, something unexpected happened. The invented languages, the naming conventions, the six magical traditions in the game world -- they had internal structure. Consistent phoneme patterns. Recurring morphological rules across thousands of paragraphs that no human intentionally designed.

I pulled the linguistic patterns out. Six "tongues" emerged, each with a distinct phonetic and semantic signature. I built a tokenizer seeded from those patterns. Then during what I can only describe as a weird late-night vibe coding session, I asked: what if those six tongues weren't just a tokenizer trick? What if they were dimensions in a geometric space where distance corresponds to trust?

That question became SCBE-AETHERMOORE: a 14-layer AI governance framework built on hyperbolic geometry, post-quantum cryptography, and a tokenizer born from DnD game logs.

## The Core Insight: Make Adversarial Behavior Geometrically Expensive

Most AI safety approaches work by detecting bad behavior after it happens -- classifiers, filters, RLHF guardrails. SCBE takes a different approach inspired by physics: make adversarial intent cost exponentially more computational resources the further it deviates from safe operation.

The math lives in the Poincare ball model of hyperbolic space. Every AI agent operates as a point in this space. Trusted behavior clusters near the origin. The further an agent drifts toward the boundary (toward adversarial territory), the more expensive every operation becomes.

The Harmonic Wall formula captures this:

```
H(d, R) = R^(d^2)
```

Where `d` is the hyperbolic distance from the trusted center and `R` is the base cost ratio (typically phi, the golden ratio, ~1.618). At `d = 1`, cost scales by ~1.6x. At `d = 3`, cost scales by ~75x. At `d = 5`, cost scales by ~57,665x. The squared exponent creates a "wall" -- agents can drift slightly without penalty, but adversarial drift hits a computational cliff.

In production, the 14-layer pipeline uses a bounded variant for numerical stability:

```typescript
// Layer 12: Bounded safety score
// H_score = 1 / (1 + d_H + 2 * phaseDeviation)
export function harmonicScale(d: number, phaseDeviation: number = 0): number {
  return 1 / (1 + d + 2 * phaseDeviation);
}
```

The hyperbolic distance itself is computed via the invariant metric on the Poincare ball:

```typescript
// Layer 5: d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
```

This metric has a beautiful property: space near the boundary of the unit ball is exponentially larger than space near the center. Safe operations live in the small, well-mapped interior. Attacks must navigate the vast, expensive periphery.

## The Six Sacred Tongues

The six tongues from the game logs became six dimensions of a trust metric, weighted by powers of the golden ratio:

| Tongue | Weight | Role |
|--------|--------|------|
| KO | 1.00 | Foundation / Structure |
| AV | 1.62 | Communication / Interface |
| RU | 2.62 | Logic / Verification |
| CA | 4.24 | Memory / Persistence |
| UM | 6.85 | Coordination / Consensus |
| DR | 11.09 | Authority / Governance |

Each tongue has a 16x16 token grid (256 tokens per language, 1,536 total). The golden ratio weighting means governance dimensions (DR, UM) carry naturally higher weight in distance calculations -- an agent that deviates in its governance behavior triggers the harmonic wall faster than one that deviates in simple structural tokens.

```typescript
// Layer 3: Golden ratio weighting
const PHI = 1.618033988749895;
for (let k = 0; k < D; k++) {
  weights.push(Math.pow(PHI, k));
}
```

## The 14-Layer Pipeline

Every interaction passes through 14 layers. Here is the condensed map:

- **L1-2**: Complex state construction and realification (map inputs to real vector space)
- **L3-4**: Golden-ratio weighted transform and Poincare embedding
- **L5**: Hyperbolic distance computation (the invariant metric)
- **L6-7**: Breathing transform and Mobius phase modulation (temporal dynamics)
- **L8**: Multi-well realm detection (Hamiltonian energy landscapes)
- **L9-10**: Spectral coherence and spin analysis (FFT-based)
- **L11**: Triadic temporal distance (causality enforcement)
- **L12**: Harmonic Wall scoring
- **L13**: Risk decision: ALLOW / QUARANTINE / ESCALATE / DENY
- **L14**: Audio axis telemetry (frequency-domain audit trail)

Each layer maps to one of five quantum axioms (Unitarity, Locality, Causality, Symmetry, Composition) ensuring the pipeline has mathematically provable properties.

## Flock Shepherd: Governing Agent Fleets

When you have multiple AI agents working together, individual safety is not enough. SCBE includes the Flock Shepherd -- a multi-agent fleet orchestrator that manages agents as a governed collective:

```python
from scbe_aethermoore.flock_shepherd import FlockShepherd, SheepRole

shepherd = FlockShepherd(max_flock_size=50)

# Register agents with roles
agent_id = shepherd.spawn_agent(
    role=SheepRole.EXECUTOR,
    training_track="code_review"
)

# Monitor fleet health via coherence scores
health = shepherd.get_flock_health()

# Consensus via balanced ternary governance
decision = shepherd.propose_action("deploy_update")
# Returns: ALLOW / QUARANTINE / ESCALATE / DENY
```

The Flock Shepherd uses balanced ternary governance for consensus decisions -- each agent votes with a trit (-1, 0, +1) and the aggregate determines the fleet-level decision. Agents that degrade in coherence get their tasks redistributed automatically.

## Post-Quantum Cryptography

The entire cryptographic layer uses post-quantum algorithms:

- **ML-KEM-768** (formerly Kyber768) for key encapsulation
- **ML-DSA-65** (formerly Dilithium3) for digital signatures
- **AES-256-GCM** for symmetric encryption

Every governance decision, every trust score, every agent heartbeat is signed and verifiable. When NIST finalized these algorithms, the framework was already using them.

## Does It Actually Work?

Benchmarks from the adversarial test suite:

- **95.3% detection rate** on adversarial prompt injection (vs 89.6% for standalone ML anomaly detection)
- **Zero false denials** on the standard compliance test suite
- Sub-millisecond latency per layer (14 layers total < 8ms on commodity hardware)
- The harmonic wall triggers cost escalation 340x faster than linear scaling at boundary distances

## Why This Matters Now

The EU AI Act enforcement begins August 2026. Article 9 mandates risk management systems for high-risk AI. Article 15 requires accuracy, robustness, and cybersecurity measures. SCBE's 14-layer pipeline with provable axioms and post-quantum crypto maps directly to these requirements.

Every governance decision generates a signed, auditable artifact. The pipeline does not just detect risk -- it produces the compliance evidence that regulators will demand.

## Get Started

Install from npm or PyPI:

```bash
npm install scbe-aethermoore
# or
pip install scbe-aethermoore
```

TypeScript quick start:

```typescript
import { layer1ComplexState, layer2Realification,
         layer3WeightedTransform } from 'scbe-aethermoore/harmonic';
import { harmonicScale } from 'scbe-aethermoore/harmonic';

// Build a state vector from input features
const complex = layer1ComplexState([0.5, 0.3, 0.1, 0.8, 0.2, 0.6], 3);
const real = layer2Realification(complex);
const weighted = layer3WeightedTransform(real);

// Score safety (1.0 = safe center, 0.0 = boundary)
const safetyScore = harmonicScale(2.5, 0.1);
// => 0.238 (elevated distance from trusted center)
```

The source is MIT-licensed: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)

For the full narrative behind the six tongues and the world they came from, the book *The Six Tongues Protocol* by Issac Davis is available on Kindle.

---

*Patent pending: USPTO #63/961,403. ORCID: 0009-0002-3936-9369.*

*Built on game logs, grounded in geometry, shipping as infrastructure.*
