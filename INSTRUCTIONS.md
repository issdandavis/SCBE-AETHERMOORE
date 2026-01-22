# SCBE-AETHERMOORE Instructions

> Complete guide for developers, integrators, and operators

---

## Quick Start (2 Minutes)

```bash
# 1. Clone
git clone https://github.com/ISDanDavis2/scbe-aethermoore-demo.git
cd scbe-aethermoore-demo

# 2. Install
npm install
pip install -r requirements.txt

# 3. Test (728 tests)
npm test

# 4. Run Demo
python demo_memory_shard.py

# 5. Start API
python -m uvicorn src.api.main:app --reload
# Open http://localhost:8000/docs
```

---

## For Developers

### Project Layout

```
src/
├── harmonic/           # 14-Layer Pipeline (CORE)
│   ├── pipeline14.ts   # Layers 1-14 implementation
│   ├── hyperbolic.ts   # Layers 5-7 (Poincaré ball)
│   ├── harmonicScaling.ts # Layer 12 (risk amplification)
│   └── audioAxis.ts    # Layer 14 (telemetry)
├── crypto/             # Cryptographic primitives
│   ├── envelope.ts     # Sealed envelope (AES-256-GCM)
│   ├── pqc.ts          # Post-quantum (ML-KEM, ML-DSA)
│   └── replayGuard.ts  # Nonce management
├── fleet/              # Multi-agent orchestration
│   └── redis-orchestrator.ts
└── api/                # REST API
    └── main.py         # FastAPI server
```

### Running Tests

```bash
# All tests
npm test

# Specific category
npm test -- tests/harmonic/
npm test -- tests/enterprise/
npm test -- tests/network/

# With coverage
npm test -- --coverage

# Python tests
pytest tests/ -v
```

### Building

```bash
# TypeScript build
npm run build

# Type checking only
npm run typecheck
```

---

## For Integrators

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List agents |
| POST | `/seal-memory` | Seal memory shard |
| POST | `/retrieve-memory` | Retrieve with auth |
| POST | `/verify` | Verify envelope |
| GET | `/audit` | Get audit trail |
| WS | `/ws/dashboard` | Real-time stream |

### Example: Seal and Retrieve

```bash
# Seal a secret
curl -X POST http://localhost:8000/seal-memory \
  -H "Content-Type: application/json" \
  -d '{
    "shard_id": "secret-001",
    "content": "classified data",
    "context": [0.5, 0.3, 0.8, 0.2, 0.9, 0.4]
  }'

# Retrieve (governance check)
curl -X POST http://localhost:8000/retrieve-memory \
  -H "Content-Type: application/json" \
  -d '{
    "shard_id": "secret-001",
    "agent_id": "agent-b",
    "context": [0.5, 0.3, 0.8, 0.2, 0.9, 0.4]
  }'

# Response: {"decision": "ALLOW", "risk_score": 0.23, ...}
```

### SDK Usage (TypeScript)

```typescript
import {
  runPipeline14,
  createEnvelope,
  verifyEnvelope
} from 'scbe-aethermoore';

// Run governance check
const result = await runPipeline14({
  context: [0.5, 0.3, 0.8, 0.2, 0.9, 0.4],
  agentId: 'my-agent',
  topic: 'sensitive-data'
});

if (result.decision === 'ALLOW') {
  // Create sealed envelope
  const envelope = await createEnvelope({
    body: { data: 'secret' },
    aad: { intent_id: 'auth-001' }
  });
}
```

---

## For Operators

### Docker Deployment

```bash
# Build image (includes liboqs for real PQC)
docker build -t scbe-aethermoore .

# Run
docker run -p 8000:8000 scbe-aethermoore

# With Redis for fleet management
docker-compose up
```

### Environment Variables

```bash
# .env file
SCBE_API_KEY=your-api-key
SCBE_REDIS_URL=redis://localhost:6379
SCBE_LOG_LEVEL=info
SCBE_MAX_REQUESTS_PER_MINUTE=100
```

### Monitoring Dashboard

1. Start API server
2. Open `dashboard/scbe_monitor.html` in browser
3. Dashboard connects via WebSocket to `/ws/dashboard`
4. See real-time ALLOW/QUARANTINE/DENY decisions

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Expected: {"status": "healthy", "version": "3.0.0", ...}
```

---

## Layer Reference

| Layer | Function | File |
|-------|----------|------|
| **L1** | Complex State | `pipeline14.ts:layer1ComplexState` |
| **L2** | Realification | `pipeline14.ts:layer2Realification` |
| **L3** | Weighted Transform | `pipeline14.ts:layer3WeightedTransform` |
| **L4** | Poincaré Embedding | `pipeline14.ts:layer4PoincareEmbedding` |
| **L5** | Hyperbolic Distance | `hyperbolic.ts:hyperbolicDistance` |
| **L6** | Breathing Transform | `hyperbolic.ts:breathingTransform` |
| **L7** | Phase Transform | `hyperbolic.ts:mobiusAddition` |
| **L8** | Realm Distance | `pipeline14.ts:layer8RealmDistance` |
| **L9** | Spectral Coherence | `pipeline14.ts:layer9SpectralCoherence` |
| **L10** | Spin Coherence | `pipeline14.ts:layer10SpinCoherence` |
| **L11** | Triadic Temporal | `pipeline14.ts:layer11TriadicTemporal` |
| **L12** | Harmonic Scaling | `harmonicScaling.ts:harmonicScale` |
| **L13** | Risk Decision | `pipeline14.ts:layer13RiskDecision` |
| **L14** | Audio Axis | `audioAxis.ts:computeAudioAxisFeatures` |

---

## Troubleshooting

### Tests failing?

```bash
# Clear cache and reinstall
rm -rf node_modules
npm install
npm test
```

### API not starting?

```bash
# Check Python dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8000
```

### WebSocket not connecting?

- Ensure API is running
- Check browser console for errors
- Dashboard falls back to demo mode if API unavailable

---

## Support

- **GitHub Issues**: https://github.com/ISDanDavis2/scbe-aethermoore-demo/issues
- **Documentation**: See `docs/` directory
- **Patent**: USPTO #63/961,403

---

_Last updated: January 2026_
