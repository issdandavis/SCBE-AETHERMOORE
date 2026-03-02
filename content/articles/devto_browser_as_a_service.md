---
title: "Building a Governed Browser-as-a-Service: How We Route AI Agents Through Hyperbolic Space"
published: true
tags: [webdev, ai, python, opensource]
---

# Building a Governed Browser-as-a-Service: How We Route AI Agents Through Hyperbolic Space

Most AI browser automation is a liability. You point an agent at a website, hope it does the right thing, and pray it doesn't click "Confirm Purchase" on something you didn't authorize.

We built something different: a **governed browser swarm** where every agent action passes through a 14-layer security pipeline, and different agents literally see different shortest paths through the web because their mathematical personalities warp the geometry.

## The Architecture

```
User Request
    ↓
FastAPI Gateway (port 8000)
    ↓
Governance Membrane (14 layers)
    ↓
TongueRouter (Dijkstra on Poincare Ball)
    ↓
Agent Pool (scout, infiltrator, auditor, ...)
    ↓
Playwright Wrapper (action validation)
    ↓
Training Tap (every interaction → SFT pair)
```

### The Tongue Router

This is the interesting part. Every URL gets expanded into a 6D vector using what we call Sacred Tongue space — six dimensions weighted by the golden ratio:

```python
# Simplified from src/browser/tongue_router.py
class TongueObserver:
    TONGUE_WEIGHTS = {
        'KO': 1.000,   # Intent
        'AV': 1.618,   # Context
        'RU': 2.618,   # Policy
        'CA': 4.236,   # Execution
        'UM': 6.854,   # Security
        'DR': 11.090,  # Attestation
    }

    def expand_url(self, url: str) -> np.ndarray:
        """Expand URL into 6D tongue space."""
        features = self._extract_features(url)
        return np.array([
            features[t] * w
            for t, w in self.TONGUE_WEIGHTS.items()
        ])
```

### Agent Personalities

Different agents have different tongue weightings, which means they see different edge costs in the navigation graph:

```python
AGENT_PROFILES = {
    'scout': {
        'tongues': {'KO': 2.0, 'AV': 1.5, 'RU': 0.5},
        'description': 'Fast recon, low policy overhead'
    },
    'auditor': {
        'tongues': {'RU': 2.0, 'UM': 1.5, 'DR': 1.5},
        'description': 'High policy, security-focused'
    },
    'infiltrator': {
        'tongues': {'KO': 1.5, 'CA': 2.0, 'UM': 1.0},
        'description': 'Execution-heavy, moderate security'
    }
}
```

The math: `g_ij(x, agent) = (4/(1-|x|^2)^2) * T_ij(agent)`

The Poincare ball metric is modified by the agent's tongue tensor. Two agents looking at the same graph see different shortest paths. A scout finds the fastest route. An auditor finds the safest route. Same web, different geometry.

### Governance at Every Step

Every browser action goes through:

1. **Semantic antivirus** — checks intent against known malicious patterns
2. **Action validation** — confirms the action matches the approved task
3. **Governance scan** — 14-layer pipeline produces ALLOW/DENY/QUARANTINE
4. **Training tap** — every interaction becomes an SFT training pair

```python
# From agents/browser/action_validator.py
class ActionValidator:
    async def validate(self, action: BrowserAction) -> GovernanceDecision:
        scan = await self.governance.scan(action.to_event())
        if scan.decision == "DENY":
            await self.training_tap.record_denied(action, scan)
            raise GovernanceDenied(scan.reason)
        return scan
```

### The Training Flywheel

Here's the part that compounds: every browser session generates training data. Good actions become positive SFT pairs. Denied actions become negative DPO pairs. The system literally teaches itself to be better at browsing.

```
Session → Actions → Governance Decisions → Training Pairs → Better Agent → Better Sessions
```

14,654 training pairs and counting, all pushed to HuggingFace.

## Running It Yourself

```bash
# Clone
git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
cd SCBE-AETHERMOORE

# Install
pip install -r requirements.txt
npm install

# Start the BaaS gateway
python -m uvicorn src.api.browser_saas:app --port 8000

# Or use Docker
docker-compose -f docker-compose.baas-gateway.yml up
```

The governance API endpoint:
```bash
curl -X POST http://localhost:8000/v1/session/create \
  -H "X-API-Key: your-key" \
  -d '{"task": "research AI safety papers", "agent": "scout"}'
```

## Why Open Source?

AI governance is too important to be proprietary. If the system that decides what AI can and can't do is closed, you're just trusting a different black box.

The full codebase: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)

Patent pending (USPTO #63/961,403) — the math is protected, the code is free.

---

*If you're building AI agents that touch the web, I'd love to hear how you handle governance. What does your "allowed actions" list look like? Drop a comment.*
