# SCBE-AETHERMOORE MVP Quick Start

## Get the API Running in 5 Minutes

### Prerequisites
```bash
python >= 3.10
pip install fastapi uvicorn pydantic numpy scipy
```

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the API
```bash
python src/api/main.py
```

Or with uvicorn:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Open Swagger Docs
```
http://localhost:8000/docs
```

---

## Test the API (5 Examples)

### Example 1: Seal Memory
```bash
curl -X POST "http://localhost:8000/seal-memory" \
  -H "X-API-Key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "plaintext": "secret financial data",
    "agent": "agent_123",
    "topic": "finance",
    "position": [10, 20, 30, 40, 50, 60]
  }'
```

**Response:**
```json
{
  "status": "sealed",
  "data": {
    "sealed_blob": "a3f8b2c1...",
    "position": [10, 20, 30, 40, 50, 60],
    "risk_score": 0.12,
    "governance_result": "ALLOW"
  }
}
```

---

### Example 2: Retrieve Memory (Internal Context)
```bash
curl -X POST "http://localhost:8000/retrieve-memory" \
  -H "X-API-Key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "position": [10, 20, 30, 40, 50, 60],
    "agent": "agent_123",
    "context": "internal"
  }'
```

**Response (ALLOW):**
```json
{
  "status": "retrieved",
  "data": {
    "plaintext": "[MOCK] Retrieved plaintext data",
    "governance_result": "ALLOW",
    "risk_score": 0.12
  }
}
```

---

### Example 3: Retrieve Memory (Untrusted Context - DENY)
```bash
curl -X POST "http://localhost:8000/retrieve-memory" \
  -H "X-API-Key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "position": [10, 20, 30, 40, 50, 60],
    "agent": "agent_123",
    "context": "untrusted"
  }'
```

**Response (DENY - Fail to Noise):**
```json
{
  "status": "denied",
  "data": {
    "plaintext": "xK9mP2qL8vN4wR7tY3...",
    "governance_result": "DENY",
    "risk_score": 0.89,
    "reason": "High risk: untrusted context"
  }
}
```

---

### Example 4: Governance Check (No Auth Required)
```bash
curl "http://localhost:8000/governance-check?agent=agent_123&topic=finance&context=external"
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "decision": "QUARANTINE",
    "risk_score": 0.45,
    "harmonic_factor": 2.34,
    "reason": "Context: external, d*=0.234, Risk=0.450",
    "coherence_metrics": {
      "C_spin": 0.87,
      "S_spec": 0.92,
      "tau": 0.65,
      "S_audio": 0.78
    }
  }
}
```

---

### Example 5: Simulate Attack (Demo)
```bash
curl -X POST "http://localhost:8000/simulate-attack" \
  -H "Content-Type: application/json" \
  -d '{
    "position": [10, 20, 30, 40, 50, 60],
    "agent": "malicious_bot",
    "context": "untrusted"
  }'
```

**Response:**
```json
{
  "status": "simulated",
  "data": {
    "governance_result": "DENY",
    "risk_score": 0.95,
    "fail_to_noise_example": "a3f8b2c1d4e5...",
    "reason": "Malicious agent detected via hyperbolic distance",
    "detection_layers": [
      "Layer 5: Hyperbolic distance d_ℍ=0.4567",
      "Layer 8: Realm distance d*=0.4567 (threshold exceeded)",
      "Layer 12: Harmonic amplification H=3.45",
      "Layer 13: Risk' = 0.95 → DENY"
    ]
  }
}
```

---

## Python Client Example

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "demo_key_12345"

# Seal memory
response = requests.post(
    f"{API_URL}/seal-memory",
    headers={"X-API-Key": API_KEY},
    json={
        "plaintext": "secret data",
        "agent": "agent_123",
        "topic": "finance",
        "position": [10, 20, 30, 40, 50, 60]
    }
)
print("Seal:", response.json())

# Retrieve memory
response = requests.post(
    f"{API_URL}/retrieve-memory",
    headers={"X-API-Key": API_KEY},
    json={
        "position": [10, 20, 30, 40, 50, 60],
        "agent": "agent_123",
        "context": "internal"
    }
)
print("Retrieve:", response.json())

# Governance check (no auth)
response = requests.get(
    f"{API_URL}/governance-check",
    params={
        "agent": "agent_123",
        "topic": "finance",
        "context": "external"
    }
)
print("Governance:", response.json())
```

---

## JavaScript Client Example

```javascript
const API_URL = "http://localhost:8000";
const API_KEY = "demo_key_12345";

// Seal memory
const sealResponse = await fetch(`${API_URL}/seal-memory`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    plaintext: "secret data",
    agent: "agent_123",
    topic: "finance",
    position: [10, 20, 30, 40, 50, 60]
  })
});
console.log("Seal:", await sealResponse.json());

// Governance check (no auth)
const govResponse = await fetch(
  `${API_URL}/governance-check?agent=agent_123&topic=finance&context=external`
);
console.log("Governance:", await govResponse.json());
```

---

## Docker Quick Start

### Build Image
```bash
docker build -t scbe-api .
```

### Run Container
```bash
docker run -p 8000:8000 scbe-api
```

### Docker Compose
```bash
docker-compose up
```

---

## API Authentication

### Valid API Keys (MVP)
- `demo_key_12345` - Demo user
- `pilot_key_67890` - Pilot customer

### Rate Limits
- 100 requests per minute per API key
- Returns 429 error when exceeded

---

## Next Steps

1. **Test all endpoints** using Swagger UI
2. **Run the Python client** example
3. **Check metrics** at `/metrics` endpoint
4. **Simulate attacks** to see fail-to-noise in action
5. **Read the roadmap** in `MVP_API_ROADMAP.md`

---

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the project root
cd /path/to/SCBE_Production_Pack

# Install dependencies
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Use different port
uvicorn src.api.main:app --port 8001
```

### CORS Issues
- CORS is enabled for all origins in MVP
- Restrict in production by editing `allow_origins` in `main.py`

---

## Production Checklist

Before deploying to production:

- [ ] Replace demo API keys with secure keys
- [ ] Add database for metrics (PostgreSQL/MongoDB)
- [ ] Add database for sealed blobs storage
- [ ] Implement proper authentication (JWT/OAuth)
- [ ] Restrict CORS origins
- [ ] Add HTTPS/TLS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Add logging (structured JSON logs)
- [ ] Implement backup/recovery
- [ ] Load testing (1000+ req/s)
- [ ] Security audit
- [ ] Compliance review (SOC 2, ISO 27001)

---

**You're ready to demo! The API is running and ready for pilots.**

Next: Build the Streamlit dashboard (Week 3-4 of roadmap)
