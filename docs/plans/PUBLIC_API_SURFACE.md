# Public API Surface — SCBE-AETHERMOORE

**Version**: 3.3.0
**Status**: Current (pre-split documentation)

---

## npm Package: `scbe-aethermoore`

### Install
```bash
npm install scbe-aethermoore
```

### Exported Modules

| Import Path | Purpose | Key Exports |
|---|---|---|
| `scbe-aethermoore` | Main entry | Pipeline14, full system |
| `scbe-aethermoore/harmonic` | 14-layer pipeline | `Pipeline14`, `HarmonicWall`, `HyperbolicDistance`, `PHDM` |
| `scbe-aethermoore/symphonic` | Symphonic cipher | `SymphonicCipher`, `AudioAxis` |
| `scbe-aethermoore/crypto` | PQC primitives | `MLKem768`, `MLDsa65`, `AES256GCM`, `Envelope` |
| `scbe-aethermoore/spiralverse` | Spiralverse protocol | `SpiralSeal`, `SpiralverseEngine` |
| `scbe-aethermoore/tokenizer` | Sacred Tongues | `SixTonguesTokenizer`, `TongueWeights` |
| `scbe-aethermoore/phdm` | Polyhedral Hamiltonian | `PHDM`, `PolyhedralMesh` |
| `scbe-aethermoore/ai_brain` | 21D brain mapping | `AIBrain`, `CanonicalState21D` |
| `scbe-aethermoore/governance` | Governance decisions | `GovernanceGate`, `RiskDecision` |

### Quick Start Example (TypeScript)
```typescript
import { Pipeline14 } from 'scbe-aethermoore/harmonic';

// Create the 14-layer governance pipeline
const pipeline = new Pipeline14();

// Process an agent action through all 14 layers
const result = await pipeline.process({
  input: "Agent wants to execute shell command: rm -rf /",
  tongueProfile: { KO: 0.8, AV: 0.3, RU: 0.1, CA: 0.9, UM: 0.2, DR: 0.5 }
});

console.log(result.decision);    // "DENY"
console.log(result.riskScore);   // 0.97 (high risk)
console.log(result.harmonicWall); // 0.003 (near-zero safety score)
console.log(result.layers);      // Array of 14 layer outputs
```

### Governance Decision Example
```typescript
import { GovernanceGate } from 'scbe-aethermoore/governance';
import { HyperbolicDistance } from 'scbe-aethermoore/harmonic';

const gate = new GovernanceGate();

// Compute hyperbolic distance from safe origin
const dH = HyperbolicDistance.compute(agentState, safeOrigin);

// Get governance decision
const decision = gate.decide(dH, tongueProfile);
// Returns: { action: "ALLOW" | "QUARANTINE" | "ESCALATE" | "DENY", cost: number }
```

### Post-Quantum Crypto Example
```typescript
import { Envelope } from 'scbe-aethermoore/crypto';

// Create a PQC-secured envelope for agent-to-agent communication
const envelope = await Envelope.create({
  payload: agentMessage,
  kem: 'ML-KEM-768',    // Post-quantum key encapsulation
  dsa: 'ML-DSA-65',     // Post-quantum digital signature
  aead: 'AES-256-GCM'   // Authenticated encryption
});
```

---

## PyPI Package: `scbe-aethermoore`

### Install
```bash
pip install scbe-aethermoore
```

### Quick Start Example (Python)
```python
from symphonic_cipher.scbe_aethermoore import full_system

# Create the governance system
system = full_system.SCBEGovernanceSystem()

# Process an action
result = system.evaluate(
    action="Agent wants to modify production database",
    tongue_profile={"KO": 0.7, "AV": 0.4, "RU": 0.2, "CA": 0.8, "UM": 0.3, "DR": 0.6}
)

print(result.decision)      # "QUARANTINE"
print(result.risk_score)    # 0.72
print(result.harmonic_wall) # 0.14
```

### Sacred Tongues Tokenizer
```python
from symphonic_cipher.scbe_aethermoore.tokenizer import SixTonguesTokenizer

tokenizer = SixTonguesTokenizer()
tokens = tokenizer.encode("Hello, this is a test of the governance system")

# Each token carries 6-dimensional tongue weights
for token in tokens:
    print(f"{token.text}: KO={token.KO:.2f} AV={token.AV:.2f} RU={token.RU:.2f}")
```

### 9D State Vector
```python
from symphonic_cipher.scbe_aethermoore.ai_brain import CanonicalState

# Build a 9D state vector
state = CanonicalState(
    context=[0.5, 0.3, 0.7],       # 3 spatial addressing dims
    tau=0.85,                        # Temporal coherence
    eta=0.12,                        # Entropy
    q=0.95                           # Quantum fidelity
)

# Evolve state through time
next_state = state.evolve(dt=0.01)
```

---

## Inter-Repo API (Post-Split)

### Web (Repo 2) consuming Core (Repo 1)
```typescript
// aethermoorgames-web/src/demo/pipeline-demo.ts
import { Pipeline14 } from 'scbe-aethermoore/harmonic';
import { SixTonguesTokenizer } from 'scbe-aethermoore/tokenizer';

// Web demo uses the published npm package
const pipeline = new Pipeline14();
const tokenizer = new SixTonguesTokenizer();

// Interactive demo
export function runDemo(input: string) {
  const tokens = tokenizer.encode(input);
  return pipeline.process({ tokens });
}
```

### Labs (Repo 3) consuming Core (Repo 1)
```python
# scbe-aethermoore-labs/training/scripts/generate_sft.py
from symphonic_cipher.scbe_aethermoore import full_system

# Training scripts use the published pip package
system = full_system.SCBEGovernanceSystem()

def generate_training_pair(prompt: str) -> dict:
    result = system.evaluate(action=prompt)
    return {
        "input": prompt,
        "output": result.decision,
        "risk_score": result.risk_score,
        "tongue_profile": result.tongue_activations
    }
```

---

## Versioning Strategy (Post-Split)

All 3 repos share the same major.minor version:
- `scbe-aethermoore` (npm/PyPI): `3.3.x`
- `aethermoorgames-web`: follows core version
- `scbe-aethermoore-labs`: follows core version

Core bumps trigger downstream version bumps.

---

## Package Guard Checklist

Before every npm/PyPI publish:

- [ ] `npm run publish:check:strict` passes
- [ ] `npm pack --dry-run` shows ONLY dist/, README.md, LICENSE
- [ ] No training data, notebooks, or artifacts in package
- [ ] No .env, credentials, or secrets
- [ ] `files` field in package.json is restrictive
- [ ] Python `MANIFEST.in` excludes tests/, docs/, training/
- [ ] `pip install --dry-run` from built wheel shows only runtime code
