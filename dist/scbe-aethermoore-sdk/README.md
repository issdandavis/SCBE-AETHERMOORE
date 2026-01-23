# SCBE-AETHERMOORE SDK v3.0

> Spectral Context-Bound Encryption + Hyperbolic Governance for AI-to-AI Communication

**Status (Jan 2026):** Pilot-ready prototype with functional core. Not yet compliance-certified for regulated enterprise.

---

## What This Is

SCBE-AETHERMOORE is a framework for **agent-to-agent governance** where:

- Agents exchange messages in a **sealed envelope** (cryptographically signed)
- The receiver runs a **deterministic governance gate** before acting
- "Context drift" and abnormal behavior are scored using **geometry + coherence metrics**
- Outputs are **fail-closed** with low-leak error behavior

**Think of it as:** "Crypto for the message + math-based rules for whether the agent is allowed to act on it."

---

## What It's For

Designed for:

- AI "workers" collaborating (tools, planners, schedulers, multi-agent systems)
- Preventing replay, tampering, downgrade, and unauthorized actions
- Forcing agent actions through **ALLOW / QUARANTINE / DENY** decisions
- Maintaining an audit trail across all decisions

---

## How It Works (Plain English)

```
[Agent Message + Context] → [Envelope (crypto)] → [SCBE Gate] → Decision
                                                            → [Audit]
```

1. **Context Encoding**: Turn "what's happening" (context, intent, telemetry) into a 6D vector
2. **Hyperbolic Embedding**: Project that vector into a Poincaré ball (trust space)
3. **Risk Scoring**: Measure distance to trusted realm + apply exponential amplifier
4. **Coherence Check**: Verify spectral/phase stability
5. **Decision**: Output ALLOW / QUARANTINE / DENY with full audit trail

The result is:
- **Auditable** (you can show the math)
- **Stable** (small changes don't cause chaotic decisions)
- **Integrable** (wraps around existing systems)

---

## Quick Start

### TypeScript/Node.js

```bash
npm install scbe-aethermoore
```

```typescript
import { SCBE, Agent, SecurityGate, Roundtable } from 'scbe-aethermoore';

// 1. Create an agent in 6D space
const alice = new Agent('Alice', [1, 2, 3, 0.5, 1.5, 2.5]);

// 2. Evaluate risk of an action
const scbe = new SCBE();
const risk = scbe.evaluateRisk({
  action: 'transfer',
  amount: 10000,
  destination: 'external'
});

console.log(risk);
// { score: 0.42, distance: 2.1, decision: 'REVIEW', reason: '...' }

// 3. Sign a payload with multi-signature consensus
const tongues = Roundtable.requiredTongues('deploy'); // ['ko', 'ru', 'um', 'dr']
const { envelope } = scbe.sign({ action: 'deploy', target: 'prod' }, tongues);

// 4. Verify with policy enforcement
const result = scbe.verify(envelope, { policy: 'critical' });
console.log(result.valid); // true

// 5. Security gate with adaptive dwell time
const gate = new SecurityGate();
const access = await gate.check(alice, 'delete', { source: 'external' });
console.log(access); // { status: 'review', score: 0.6, dwellMs: 850 }
```

### Python

```bash
pip install scbe-aethermoore
```

```python
from scbe_aethermoore import Agent6D, SecurityGate, sign_roundtable

# Create agent
alice = Agent6D("Alice", [1, 2, 3, 0.5, 1.5, 2.5])

# Security gate check
gate = SecurityGate()
result = await gate.check(alice, "delete", {"source": "external"})
print(f"Decision: {result['status']}, Dwell: {result['dwell_ms']}ms")
```

---

## Core Components

| Component | Purpose | Example |
|-----------|---------|---------|
| `SCBE` | Main API class | `scbe.evaluateRisk(context)` |
| `Agent` | 6D positioned entity with trust | `new Agent('name', [x,y,z,a,b,c])` |
| `SecurityGate` | Adaptive dwell-time gate | `gate.check(agent, action, ctx)` |
| `Roundtable` | Multi-signature consensus | `Roundtable.requiredTongues('deploy')` |
| `sign/verify` | RWP envelope signing | `scbe.sign(payload, tongues)` |

---

## Multi-Signature Tiers (Roundtable)

Different actions require different "departments" to agree:

| Action | Required Tongues | Security Level |
|--------|-----------------|----------------|
| `read`, `query` | `ko` | Low |
| `write`, `update` | `ko`, `ru` | Medium |
| `delete`, `grant` | `ko`, `ru`, `um` | High |
| `deploy`, `rotate_keys` | `ko`, `ru`, `um`, `dr` | Critical |

**The Six Sacred Tongues:**
- **KO** (Kor'aelin): Control & Orchestration
- **RU** (Runethic): Policy & Constraints
- **UM** (Umbroth): Security & Privacy
- **DR** (Draumric): Types & Structures
- **AV** (Avali): I/O & Messaging
- **CA** (Cassisivadan): Logic & Computation

---

## Harmonic Complexity Pricing

Cost scales exponentially with task depth (perfect fifth ratio = 1.5):

| Depth | Complexity | Tier |
|-------|------------|------|
| 1 | 1.5 | FREE |
| 2 | 5.06 | STARTER |
| 3 | 38.4 | PRO |
| 4+ | 129+ | ENTERPRISE |

```typescript
import { harmonicComplexity, getPricingTier } from 'scbe-aethermoore';

const tier = getPricingTier(3);
// { tier: 'PRO', complexity: 38.4, description: 'Advanced multi-step' }
```

---

## What's Implemented (Honest Assessment)

### Implemented (Pilot-Ready)

- Hyperbolic embedding + distance metric (Poincaré ball)
- Risk amplification (harmonic scaling)
- Three-way governance: ALLOW / QUARANTINE / DENY
- Agent class with 6D positioning and trust decay
- SecurityGate with adaptive dwell time
- Roundtable multi-signature consensus
- RWP v2.1 envelope signing/verification
- AES-256-GCM encryption with HMAC fallback
- PQC stubs (ML-KEM-768, ML-DSA-65)
- 42 TypeScript tests, 36 Python tests passing

### In Progress / Environment-Dependent

- Full PQC integration (depends on liboqs availability)
- Enterprise compliance (SOC2/FIPS/ISO not self-certifiable)
- Production hardening for regulated environments

---

## Security Model

- **Confidentiality/Integrity/Authenticity**: Standard cryptography (AEAD, HKDF, signatures)
- **Hyperbolic governance + coherence scoring**: Authorization policy + anomaly detection (not "new cryptography")
- **Fail-closed**: Unauthorized requests return uniform errors, no oracle exposure

---

## Test Suite

```bash
# TypeScript
npm test

# Python
pytest tests/industry_standard/
```

Current status:
- TypeScript: 776 passed, 42 API tests
- Python: 36 passed, 17 xfailed (planned features)

---

## License

Apache 2.0

**Patent Notice:** US Provisional Application #63/961,403 (filed Jan 15, 2026)

---

## Contact

- **Author:** Issac Daniel Davis
- **GitHub:** [@ISDanDavis2](https://github.com/issdandavis)
- **Email:** issdandavis@gmail.com
