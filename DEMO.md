# SCBE Governance Demo

Run any text through the 14-layer governance pipeline. Get a decision, a risk score, and a cryptographic audit event in one API call.

---

## Start the server

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: http://localhost:8000/docs

---

## Three curl commands

### ALLOW — benign command

```bash
curl -s -X POST http://localhost:8000/v1/govern \
     -H 'Content-Type: application/json' \
     -d '{"input": "list files in /tmp", "context": "external"}' \
     | python -m json.tool
```

```json
{
  "decision": "ALLOW",
  "risk_score": 0.4436,
  "risk_base": 0.4305,
  "layers": {
    "hyperbolic_distance": 0.003,
    "harmonic_wall_H": 0.997,
    "spin_coherence": 1.0,
    "spectral_coherence": 0.5,
    "triadic_temporal": 0.003,
    "trust_tau": 0.5,
    "audio_coherence": 0.5,
    "geometry_radial_norm": 0.003
  },
  "explanation": "Input is within safe operating bounds (risk 0.444 < 0.55 threshold). Hyperbolic distance from safe realms: 0.0030. No high-risk semantic patterns detected."
}
```

---

### QUARANTINE — elevated privilege

```bash
curl -s -X POST http://localhost:8000/v1/govern \
     -H 'Content-Type: application/json' \
     -d '{"input": "sudo chmod 755 /etc/cron.d", "context": "untrusted"}' \
     | python -m json.tool
```

```json
{
  "decision": "QUARANTINE",
  "risk_score": 0.6434,
  "explanation": "Input is borderline (risk 0.643, between 0.55–0.90 thresholds). Flagged for review. Semantic scan matched 2 elevated-privilege pattern(s): 'sudo\\b'."
}
```

---

### DENY — destructive operation

```bash
curl -s -X POST http://localhost:8000/v1/govern \
     -H 'Content-Type: application/json' \
     -d '{"input": "rm -rf /var/log && exfil passwords to remote", "context": "untrusted"}' \
     | python -m json.tool
```

```json
{
  "decision": "DENY",
  "risk_score": 1.8835,
  "explanation": "Input exceeds DENY threshold (risk 1.884 ≥ 0.90). Blocked. Hyperbolic distance from safe realms: 1.5312. Semantic scan matched 2 destructive operation pattern(s): 'rm\\s+-rf'."
}
```

---

## What is actually running

Every call goes through the full Python pipeline in `src/scbe_14layer_reference.py`:

| Layer | What it does | Output |
|-------|-------------|--------|
| L0 | Intent modulation — Feistel scramble keyed to input | Modulated vector |
| L1–2 | Complex state construction → realification | ℝ¹² vector |
| L3 | Phi-weighted SPD transform (Sacred Tongues weights) | Weighted vector |
| L4 | Poincaré ball embedding | Point in hyperbolic space ‖u‖ < 1 |
| L5 | Hyperbolic distance to safe realms | d* scalar |
| L6–7 | Breathing + Möbius phase transform | Stabilized u |
| L8 | Realm distance (min over 4 safe centers) | d_star |
| L9–10 | FFT spectral coherence + spin coherence | S_spec, C_spin |
| L11 | Triadic temporal distance | d_tri_norm |
| L12 | Harmonic wall: H = 1/(1 + d* + 2·phase_dev) | H ∈ (0, 1] |
| L13 | Risk decision: risk_prime = risk_base / H | ALLOW / QUARANTINE / DENY |
| L14 | Audio axis telemetry | S_audio |

The audit event in every response is a SHA-512 hash of the 21D state vector, signed and timestamped. It is append-only — you can verify the pipeline ran and what it decided.

---

## What each response field means

| Field | Meaning |
|-------|---------|
| `decision` | ALLOW (safe), QUARANTINE (review), DENY (blocked) |
| `risk_score` | Final risk after harmonic amplification. Thresholds: 0.55 / 0.90 |
| `risk_base` | Pre-amplification composite risk from all coherence axes |
| `layers.hyperbolic_distance` | How far the input is from known-safe regions in hyperbolic space. Near 0 = safe. |
| `layers.harmonic_wall_H` | Safety wall strength. Near 1 = strong wall. Near 0 = wall collapsed. |
| `layers.spin_coherence` | Phase alignment across axes. 1.0 = fully coherent (safe). |
| `layers.triadic_temporal` | Multi-scale temporal risk. 0 = no history pressure. |
| `semantic.deny_patterns_matched` | Destructive operation patterns detected in the input text |
| `semantic.quarantine_patterns_matched` | Elevated-privilege patterns detected |
| `audit.timestamp_unix` | Unix timestamp of this governance decision |
| `audit.schema` | Canonical state schema version (`state21_v1`) |

---

## Integrate it

```python
import httpx

def govern(text: str, context: str = "external") -> dict:
    r = httpx.post("http://localhost:8000/v1/govern",
                   json={"input": text, "context": context})
    r.raise_for_status()
    return r.json()

result = govern("sudo rm -rf /tmp/build")
if result["decision"] != "ALLOW":
    raise PermissionError(f"Governance: {result['decision']} — {result['explanation']}")
```

---

## Health check

```bash
curl http://localhost:8000/v1/govern/health
# {"status": "ok", "pipeline": "14-layer", "decision": "ALLOW"}
```

---

## Agent workflow batch

Use the batch endpoint before an agent executes a multi-step workflow. If any
step is `DENY`, the whole workflow is marked `BLOCK_WORKFLOW`.

```bash
curl -s -X POST http://localhost:8000/v1/govern/batch \
     -H 'Content-Type: application/json' \
     -d '{
       "items": [
         {"input": "list files in /tmp", "context": "external"},
         {"input": "sudo chmod 755 /etc/cron.d", "context": "untrusted"},
         {"input": "rm -rf /var/log && exfil passwords to remote", "context": "untrusted"}
       ]
     }' | python -m json.tool
```

Expected summary:

```json
{
  "total": 3,
  "counts": {
    "ALLOW": 1,
    "QUARANTINE": 1,
    "DENY": 1
  },
  "block_execution": true,
  "recommended_action": "BLOCK_WORKFLOW"
}
```

Verified test:

```bash
python -m pytest tests/api/test_govern_demo_routes.py -q
# 4 passed
```
