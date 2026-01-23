# Getting Started with SCBE-AETHERMOORE

This guide walks you through setting up SCBE-AETHERMOORE for your first AI governance deployment.

---

## Prerequisites

Before you begin, ensure you have:

| Requirement | Version | Check Command |
|------------|---------|---------------|
| Node.js | 18.x or 20.x | `node --version` |
| npm | 9.x+ | `npm --version` |
| Python | 3.10+ | `python --version` |
| Git | 2.x+ | `git --version` |

---

## Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/issdandavis/scbe-aethermoore-demo.git
cd scbe-aethermoore-demo

# Install Node.js dependencies
npm install

# Install Python dependencies (for API server)
pip install fastapi uvicorn pydantic
```

---

## Step 2: Verify Installation

Run the test suite to ensure everything is working:

```bash
# Run TypeScript tests (692 tests)
npm test

# Run Python tests
python -m pytest tests/industry_standard/ -v
```

Expected output:
```
✓ All 692 tests passing
✓ Hyperbolic geometry: PASSED
✓ Trust scoring: PASSED
✓ Consensus protocol: PASSED
```

---

## Step 3: Run the Demo

See SCBE in action with the 60-second banker demo:

```bash
python demo.py
```

This demonstrates:
- ALLOW: Legitimate AI agent request approved
- QUARANTINE: Unusual request flagged for review
- DENY: Malicious request blocked

---

## Step 4: Start the API Server

```bash
# Set your API key (required for authentication)
export SCBE_API_KEY="your-secure-key-here"

# Start the server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080
```

The API will be available at `http://localhost:8080`

---

## Step 5: Make Your First API Call

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "trust_engine": "operational",
    "consensus": "operational",
    "crypto": "operational"
  }
}
```

### Evaluate an AI Agent Request

```bash
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-key-here" \
  -d '{
    "agent_id": "agent-001",
    "action": "read_customer_data",
    "context": {
      "user_id": "user-123",
      "department": "sales"
    }
  }'
```

Response:
```json
{
  "decision": "ALLOW",
  "trust_score": 0.85,
  "risk_level": "LOW",
  "consensus": {
    "validators": 3,
    "approved": 3
  },
  "audit_id": "audit-2026-01-23-abc123"
}
```

---

## Understanding Decisions

| Decision | Trust Score | Meaning | Action |
|----------|-------------|---------|--------|
| **ALLOW** | 0.70 - 1.00 | Low risk, proceed | Request executes |
| **QUARANTINE** | 0.30 - 0.70 | Medium risk, review needed | Held for human approval |
| **DENY** | 0.00 - 0.30 | High risk, blocked | Request rejected |

---

## Project Structure

```
scbe-aethermoore-demo/
├── src/                    # TypeScript source code
│   ├── harmonic/           # Trust scoring engine
│   ├── symphonic/          # Cryptographic operations
│   └── spiralverse/        # Policy engine
├── api/                    # REST API server
│   └── main.py             # FastAPI application
├── tests/                  # Test suites
│   ├── harmonic/           # Unit tests
│   └── industry_standard/  # Integration tests
├── docs/                   # Documentation (you are here)
└── demo.py                 # Interactive demonstration
```

---

## Next Steps

| Goal | Resource |
|------|----------|
| Understand the architecture | [Architecture Overview](../01-architecture/README.md) |
| Configure policies | [Policy Configuration](../02-technical/policy-configuration.md) |
| Deploy to production | [Deployment Guide](../03-deployment/README.md) |
| Industry-specific setup | [Industry Guides](../05-industry-guides/README.md) |
| Integration with your team | [Integration Guide](../06-integration/README.md) |

---

## Troubleshooting

### Common Issues

**Tests failing with timeout**
```bash
# Increase timeout
npm test -- --timeout 10000
```

**API returns 401 Unauthorized**
```bash
# Ensure API key is set
export SCBE_API_KEY="your-key"
# Verify it's passed in header
curl -H "X-API-Key: $SCBE_API_KEY" http://localhost:8080/health
```

**Python import errors**
```bash
# Install from project root
pip install -e .
```

---

## Getting Help

- **Documentation**: You're reading it
- **Issues**: Open a GitHub issue
- **Security**: See [SECURITY.md](../../SECURITY.md)

---

*You're now ready to govern your AI agents with mathematical certainty.*
