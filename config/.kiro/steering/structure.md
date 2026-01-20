# Project Structure & Organization

## Directory Layout

```
SCBE_Production_Pack/
├── src/
│   ├── crypto/              # TypeScript cryptographic envelope
│   ├── metrics/             # Telemetry and observability
│   ├── rollout/             # Canary deployments & circuit breakers
│   ├── selfHealing/         # Automated failure recovery
│   └── scbe_cpse_unified.py # Python 14-layer mathematical core
├── tests/                   # Test suites (acceptance, security, performance)
├── config/                  # YAML configurations & alerts
├── docs/                    # Documentation & mathematical proofs
└── examples/                # Usage examples
```

## Core Modules

### src/crypto/ (TypeScript Security Core)

- `envelope.ts`: Main API (`createEnvelope`, `verifyEnvelope`)
- `kms.ts`: Key management abstraction
- `nonceManager.ts`: Session-scoped nonce generation
- `replayGuard.ts`: Bloom filter + map-based replay detection
- `hkdf.ts`, `jcs.ts`, `bloom.ts`: Cryptographic utilities

### src/scbe_cpse_unified.py (Python Mathematical Core)

- `SCBEConfig`: Configuration dataclass with A1-A12 validation
- `HyperbolicOps`: Poincaré ball operations (embed, clamp, distance, Möbius)
- `SCBESystem`: 14-layer pipeline (L1-L14)
- `test_axiom_compliance()`: Axiom verification

### src/metrics/ (Observability)

- `telemetry.ts`: Pluggable metrics with dimensional tags

### src/rollout/ (Deployment Safety)

- `canary.ts`: Staged rollout manager (5%→25%→50%→100%)
- `circuitBreaker.ts`: Failure-driven circuit breaker

## Configuration Files

### config/ (Operational Thresholds)

- `scbe.alerts.yml`: Alert thresholds (GCM failures, nonce reuse, latency)
- `sentinel.yml`: Gating rules (rate limits, risk weights)
- `steward.yml`: Review policies (SLA, approvers)

## Documentation

### docs/

- `COMPREHENSIVE_MATH_SCBE.md`: Full mathematical specification with axioms A1-A12
- `SCBE_Production_Security_Spec.md`: Production security requirements

## Naming Conventions

- **TypeScript Files**: camelCase (`envelope.ts`, `replayGuard.ts`)
- **Python Files**: snake_case (`scbe_cpse_unified.py`)
- **Classes**: PascalCase (`SCBESystem`, `ReplayGuard`)
- **Functions**: camelCase (TS) / snake_case (Python)
- **Axiom References**: Comment format `# A4: Clamping`
