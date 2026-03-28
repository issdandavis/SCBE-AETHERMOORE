# AI Governance Starter Kit

**Ship governed AI agents in production -- not someday, today.**

Published by Issac Daniel Davis | SCBE-AETHERMOORE
Version 1.0 | March 2026

---

## Table of Contents

1. Why AI Governance Matters Now
2. What SCBE-AETHERMOORE Actually Does
3. The 14-Layer Pipeline -- Plain English
4. Installation and Quick Start
5. Your First Agent Flock
6. Configuring Governance Rules
7. Connecting Stripe for Billing
8. EU AI Act Compliance Checklist
9. API Reference Cheat Sheet
10. Troubleshooting and FAQ
11. Next Steps and Resources

---

## 1. Why AI Governance Matters Now

Every company deploying AI agents faces the same question: *how do you prove your agents are safe?*

Regulators are not waiting. The EU AI Act entered force in 2024 with staggered compliance deadlines through 2027. NIST released its AI Risk Management Framework. Insurance underwriters are adding AI liability clauses. Your customers are asking for audit trails.

Meanwhile, the real threat is not external regulation -- it is internal chaos. Multi-agent systems without governance produce unpredictable behavior. An LLM agent with write access to production databases and no oversight is not innovation. It is a liability.

SCBE-AETHERMOORE solves this with mathematics, not hope. Every agent action passes through a 14-layer security pipeline backed by hyperbolic geometry. Safe actions cost nothing. Adversarial actions cost exponentially more the further they drift from safe operation. This is not a policy document -- it is a provable mathematical constraint.

**What you get from this kit:**
- A working governance layer you can deploy today
- Multi-agent fleet management with built-in consensus voting
- Stripe-integrated billing so you can charge your own customers
- A compliance checklist mapped to the EU AI Act
- Every API endpoint documented with copy-paste examples

---

## 2. What SCBE-AETHERMOORE Actually Does

SCBE-AETHERMOORE is a governance framework for AI agent fleets. Think of it as a security layer that sits between your AI agents and the actions they want to take.

When an agent requests permission to do something -- read a database, call an external API, modify a record -- SCBE runs that request through 14 mathematical transformations. The output is one of four decisions:

| Decision | Meaning | What Happens |
|----------|---------|--------------|
| **ALLOW** | Safe operation | Agent proceeds normally |
| **QUARANTINE** | Suspicious | Action is logged, flagged for human review |
| **ESCALATE** | High risk | Requires governance committee approval |
| **DENY** | Adversarial/dangerous | Action blocked, agent receives random noise instead of real data |

The key insight: this is not rule-based filtering. It is geometric. Every agent and every action exists as a point in a 6-dimensional hyperbolic space (the Poincare ball). Safe operations cluster near the center. Risky operations drift toward the boundary. The math makes it exponentially harder for an adversarial agent to fake a safe position.

**Public benchmark results:**
- SCBE-AETHERMOORE: 91/91 adversarial attacks blocked across 10 categories
- Clean-prompt false positives: 0/15 on the current public suite
- ProtectAI DeBERTa v2 baseline: 62/91 blocked on the same comparison page

**Use the benchmark wording exactly.** Public sales copy should use the counted suite above, not floating percentage claims without a linked methodology page.

---

## 3. The 14-Layer Pipeline -- Plain English

You do not need to understand the math to use SCBE. But understanding what each layer does helps you configure it properly and explain it to auditors.

### Layers 1-2: Context Encoding

Your input (agent ID, action, target, sensitivity) gets converted from a complex-valued context vector into real numbers. Think of this as normalizing every request into a common mathematical language.

### Layers 3-4: Weighted Transform and Poincare Embedding

The real-valued vector gets weighted by the Six Sacred Tongues -- six dimensions that correspond to different security concerns (Control, I/O, Policy, Logic, Security, Structure). Each dimension has a weight based on the golden ratio, giving higher weight to security and structure concerns. The weighted vector then gets embedded into hyperbolic space using the Poincare ball model.

### Layer 5: Hyperbolic Distance

This is the core invariant. The system calculates the hyperbolic distance between the request and the safe origin:

```
d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
```

Near the center, distances are small. Near the boundary, distances explode. This is what makes adversarial behavior exponentially expensive.

### Layers 6-7: Breathing Transform and Phase

The system applies a "breathing" oscillation (Mobius addition in hyperbolic space) that makes it impossible to find a static bypass. Even if an attacker discovers a safe-looking position, the breathing transform moves the goalposts continuously.

### Layer 8: Multi-Well Realms

A Hamiltonian energy function creates "wells" -- stable zones of safe operation. Agents naturally fall into these wells. Moving out of a well costs energy, making unauthorized transitions detectable.

### Layers 9-10: Spectral and Spin Coherence

FFT-based frequency analysis detects coordination anomalies. If agents that should be synchronized are out of phase, or if a rogue agent is not oscillating at the expected frequency, these layers catch it.

### Layer 11: Triadic Temporal Distance

Time-based causality checking. Actions must happen in a valid causal order. An agent cannot claim to have completed step 3 before step 2 ran.

### Layer 12: Harmonic Scaling

The harmonic wall formula combines hyperbolic distance and phase deviation into a single safety score between 0 and 1:

```
score = 1 / (1 + d_H + 2 * phaseDeviation)
```

A score near 1.0 means safe. A score near 0.0 means adversarial.

### Layer 13: Risk Decision

The safety score maps to a governance decision: ALLOW, QUARANTINE, ESCALATE, or DENY. Thresholds are configurable per deployment.

### Layer 14: Audio Axis (Telemetry)

FFT-based telemetry feed for monitoring. This layer does not affect decisions -- it provides a real-time signal you can pipe into dashboards, alerting systems, or audit logs.

---

## 4. Installation and Quick Start

### Prerequisites

- Node.js >= 18.0.0
- Python >= 3.11
- A Stripe account (for billing integration)

### Option A: npm + pip (Recommended)

```bash
# Install the TypeScript package
npm install scbe-aethermoore

# Install the Python package
pip install scbe-aethermoore
```

### Option B: Clone and Build

```bash
git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
cd SCBE-AETHERMOORE
npm install
pip install -r requirements.txt
```

### Option C: Docker (Fastest for evaluation)

```bash
docker run -p 8080:8080 -e SCBE_API_KEY=your-key ghcr.io/issdandavis/scbe-aethermoore
```

### Start the API Server

```bash
# Set your API key
export SCBE_API_KEY="your-secret-key-here"

# Set storage path for sealed blobs
export SCBE_STORAGE_PATH="./sealed_blobs"

# Start FastAPI
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify It Works

```bash
# Health check
curl http://localhost:8000/docs

# Quick governance check (no auth required)
curl "http://localhost:8000/governance-check?agent=test-agent&topic=read-db&context=internal"
```

You should see a JSON response with a governance decision (ALLOW, QUARANTINE, or DENY), a risk score, and coherence metrics. If you see that, the 14-layer pipeline is running.

---

## 5. Your First Agent Flock

A flock is a managed group of AI agents with built-in governance. The Flock Shepherd handles agent lifecycle, task distribution, health monitoring, and consensus voting.

### Step 1: Create a Tenant

Every organization using SCBE is a tenant. Tenants have plans that control how many flocks and agents they can run.

```bash
curl -X POST http://localhost:8000/saas/tenants \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "plan": "starter",
    "governance_profile": "balanced",
    "region": "us"
  }'
```

Save the `tenant_id` from the response. You will need it for everything else.

**Plan limits:**

| Plan | Flocks | Agents | Governance Checks/Month |
|------|--------|--------|------------------------|
| Starter ($49/mo) | 1 | 8 | 5,000 |
| Growth ($149/mo) | 5 | 40 | 25,000 |
| Enterprise ($499/mo) | 25 | 250 | 100,000 |

### Step 2: Create a Flock

```bash
curl -X POST http://localhost:8000/saas/tenants/{tenant_id}/flocks \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fraud Detection Fleet",
    "mission": "Monitor transactions and flag anomalies",
    "heartbeat_timeout_seconds": 60,
    "freeze_after_missed_heartbeats": 2
  }'
```

Save the `flock_id` from the response.

### Step 3: Spawn Agents

Each agent (called a "sheep" in SCBE terminology) has a role and training track:

**Roles:**
- `leader` -- Orchestrates other agents (Sacred Tongue: KO)
- `validator` -- Votes on governance decisions (Sacred Tongue: AV)
- `executor` -- Performs work tasks (Sacred Tongue: RU)
- `observer` -- Monitors without acting (Sacred Tongue: UM)

**Training Tracks:**
- `system` -- Infrastructure and orchestration (default role: leader)
- `governance` -- Policy enforcement (default role: validator)
- `functions` -- Task execution (default role: executor)

```bash
# Spawn a leader
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/sheep \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Commander", "track": "system", "role": "leader"}'

# Spawn two validators
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/sheep \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Policy Guard A", "track": "governance"}'

curl -X POST http://localhost:8000/saas/flocks/{flock_id}/sheep \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Policy Guard B", "track": "governance"}'

# Spawn an executor
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/sheep \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Worker Bee", "track": "functions"}'
```

### Step 4: Submit and Assign Tasks

```bash
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/tasks \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Analyze last 24h of transactions for anomalies",
    "track": "functions",
    "priority": 3,
    "auto_assign": true
  }'
```

The flock automatically assigns the task to the best available agent (highest coherence score, matching training track).

### Step 5: Run a Governance Vote

```bash
curl -X POST http://localhost:8000/saas/governance/check \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "{tenant_id}",
    "flock_id": "{flock_id}",
    "action": "Write flagged transactions to external audit DB"
  }'
```

The response includes the consensus decision, individual votes from each validator, and a balanced ternary packed result. The flock uses Byzantine Fault Tolerance: with `n` active agents (excluding frozen), the flock tolerates up to `(n-1)/3` malicious agents.

### Step 6: Monitor Health

Send heartbeats from each agent to keep them alive:

```bash
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/heartbeat/{sheep_id} \
  -H "x-api-key: demo_key_12345"
```

If an agent misses heartbeats (default: 2 missed within 60 seconds), it gets frozen. Frozen agents' tasks become orphaned and are automatically redistributed to healthy agents.

Refresh the flock to trigger health evaluation and task redistribution:

```bash
curl -X POST http://localhost:8000/saas/flocks/{flock_id}/refresh \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"auto_redistribute": true}'
```

---

## 6. Configuring Governance Rules

### Governance Profiles

When creating a tenant, you choose a governance profile. The profile determines how strict the 14-layer pipeline is when evaluating requests.

| Profile | Behavior | Use Case |
|---------|----------|----------|
| `balanced` | Default thresholds | General purpose |
| `strict` | Lower ALLOW threshold | Finance, healthcare |
| `permissive` | Higher ALLOW threshold | Internal dev/test |

### Context-Aware Weights

The pipeline adjusts its sensitivity based on the request context. These weights control how much each coherence dimension matters:

**Internal context** (trusted network):
```json
{"w_d": 0.20, "w_c": 0.20, "w_s": 0.20, "w_tau": 0.20, "w_a": 0.20}
```

**External context** (partner API):
```json
{"w_d": 0.30, "w_c": 0.15, "w_s": 0.15, "w_tau": 0.30, "w_a": 0.10}
```

**Untrusted context** (public internet):
```json
{"w_d": 0.35, "w_c": 0.10, "w_s": 0.10, "w_tau": 0.35, "w_a": 0.10}
```

In untrusted contexts, distance (`w_d`) and trust (`w_tau`) weights are highest -- the system is most suspicious of requests from unknown sources.

### Coherence Thresholds

Each agent has a coherence score (0.0 to 1.0) that degrades on errors and recovers on successes:

| Threshold | Value | Effect |
|-----------|-------|--------|
| HEALTHY | >= 0.70 | Agent votes ALLOW in governance |
| WARNING | >= 0.50 | Agent votes QUARANTINE |
| ISOLATE | < 0.30 | Agent is quarantined automatically |

### Policy Levels (Sacred Tongues)

For critical operations, you can require specific tongue dimensions to be satisfied:

| Level | Required Tongues | When to Use |
|-------|-----------------|-------------|
| `standard` | KO (Control) | Normal operations |
| `strict` | RU (Policy) | Regulated data access |
| `critical` | RU + UM + DR (Policy + Security + Structure) | Financial transactions, PII access |

### Risk Decision Thresholds

Configure the Layer 13 decision boundaries:

```python
# Default thresholds
theta1 = 0.6   # Below this -> ALLOW
theta2 = 0.8   # Below this -> QUARANTINE, above -> DENY
```

Lowering `theta1` makes the system more permissive. Raising `theta2` makes DENY harder to trigger. Adjust based on your risk tolerance.

---

## 7. Connecting Stripe for Billing

SCBE includes a complete Stripe billing integration so you can charge your own customers for governed AI operations.

### Step 1: Set Environment Variables

```bash
export STRIPE_SECRET_KEY="sk_live_your_stripe_secret_key"
export STRIPE_WEBHOOK_SECRET="whsec_your_webhook_signing_secret"
export SCBE_BILLING_BASE_URL="https://your-domain.com"
```

### Step 2: Create Stripe Products

The billing module expects three Stripe products with these price IDs (create them in your Stripe dashboard):

| Plan | Monthly Price | Stripe Price ID |
|------|--------------|-----------------|
| Starter | $49 | Configure in `stripe_billing.py` PLANS dict |
| Growth | $149 | Configure in `stripe_billing.py` PLANS dict |
| Enterprise | $499 | Configure in `stripe_billing.py` PLANS dict |

Each plan includes overage pricing for governance checks beyond the monthly limit:
- Starter: $0.01 per extra check
- Growth: $0.005 per extra check
- Enterprise: $0.0025 per extra check

### Step 3: Create a Checkout Session

```bash
curl -X POST http://localhost:8000/billing/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "starter",
    "email": "customer@example.com"
  }'
```

The response contains a `checkout_url`. Redirect your customer to that URL. Stripe handles the payment form.

### Step 4: Set Up the Webhook

In your Stripe dashboard, add a webhook endpoint:
- URL: `https://your-domain.com/billing/webhook`
- Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

When a customer completes checkout, SCBE automatically:
1. Generates a unique API key (`scbe_live_...`)
2. Registers the key in the SaaS tenant system
3. Applies plan limits (flock count, agent count, monthly governance checks)

When a subscription is canceled, the API key is automatically revoked.

### Step 5: Check Billing Status

```bash
# List available plans
curl http://localhost:8000/billing/plans

# Check a customer's billing status
curl http://localhost:8000/billing/status/{api_key}
```

### Step 6: Usage Tracking

Pull usage reports per tenant per month:

```bash
curl http://localhost:8000/saas/tenants/{tenant_id}/usage?year=2026&month=3 \
  -H "x-api-key: {api_key}"
```

The response includes counts for:
- `governance_evaluations` -- governance vote calls
- `workflow_executions` -- completed tasks
- `audit_report_generations` -- audit report pulls

Use these numbers to calculate overage charges in Stripe.

---

## 8. EU AI Act Compliance Checklist

The EU AI Act (Regulation 2024/1689) classifies AI systems by risk level. SCBE-AETHERMOORE provides technical controls that map to specific articles. This checklist is not legal advice -- consult your compliance team -- but it gives you a concrete starting point.

### Risk Classification (Article 6)

- [ ] Determine your AI system's risk category (Minimal / Limited / High / Unacceptable)
- [ ] Document classification rationale
- [ ] SCBE maps: governance decisions (ALLOW/QUARANTINE/ESCALATE/DENY) provide the enforcement layer for any risk category

### Transparency Requirements (Article 52)

- [ ] Users are informed they are interacting with AI
- [ ] AI-generated content is labeled
- [ ] SCBE maps: every governance decision includes `decision_id`, `risk_score`, `explanation`, and `trace` fields for full transparency

### Technical Documentation (Article 11)

- [ ] System architecture documented
- [ ] Training data documented
- [ ] SCBE maps: the 14-layer pipeline is fully documented with mathematical proofs; audit reports generate automatically via `/saas/tenants/{id}/audit-report`

### Risk Management System (Article 9)

- [ ] Risk identification process established
- [ ] Risk estimation and evaluation performed
- [ ] Risk mitigation measures implemented
- [ ] SCBE maps: the hyperbolic distance metric provides continuous risk estimation; coherence scores provide per-agent risk monitoring; governance voting provides collective risk evaluation

### Data Governance (Article 10)

- [ ] Training data quality measures in place
- [ ] Bias detection and mitigation
- [ ] SCBE maps: the Sacred Tongues tokenizer provides 6-dimensional bias detection across Control, I/O, Policy, Logic, Security, and Structure dimensions

### Human Oversight (Article 14)

- [ ] Human can understand AI system capabilities/limitations
- [ ] Human can monitor system operation
- [ ] Human can intervene or override
- [ ] SCBE maps: QUARANTINE and ESCALATE decisions require human review; the `require_human_for_high_risk` flag on mobile goals enforces human-in-the-loop for high-risk steps

### Accuracy, Robustness, Cybersecurity (Article 15)

- [ ] Accuracy metrics established and monitored
- [ ] Resilience to attacks (adversarial robustness)
- [ ] Cybersecurity measures in place
- [ ] SCBE maps: public adversarial suite shows 91/91 blocked with 0/15 clean false positives; post-quantum cryptography (ML-KEM-768, ML-DSA-65, AES-256-GCM) protects all sealed data; fail-to-noise on DENY prevents data exfiltration

### Record Keeping (Article 12)

- [ ] Automatic logging of system events
- [ ] Logs retained for appropriate period
- [ ] Logs accessible for audit
- [ ] SCBE maps: flock event logs capture every spawn, retire, isolate, assign, vote, and task completion; usage reports track all governance evaluations per month

### Registration (Article 51)

- [ ] High-risk AI systems registered in EU database
- [ ] SCBE maps: tenant and flock IDs provide the unique system identifiers required for registration

### Conformity Assessment (Article 43)

- [ ] Internal conformity assessment completed (for non-Annex III systems)
- [ ] Third-party assessment scheduled (if required)
- [ ] SCBE maps: audit reports provide the technical evidence package for conformity assessments

---

## 9. API Reference Cheat Sheet

All endpoints assume the API is running at `http://localhost:8000`. Add `-H "x-api-key: YOUR_KEY"` where auth is required.

### Core Pipeline

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/seal-memory` | Yes | Seal data into 6D hyperbolic memory shard |
| POST | `/retrieve-memory` | Yes | Retrieve sealed data (governance-gated) |
| GET | `/governance-check` | No | Check governance decision without sealing |
| POST | `/simulate-attack` | No | Demo: simulate adversarial access attempt |

**Seal memory:**
```bash
curl -X POST http://localhost:8000/seal-memory \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "plaintext": "sensitive data here",
    "agent": "fraud-detector-001",
    "topic": "transactions",
    "position": [10, 20, 30, 40, 50, 60]
  }'
```

**Retrieve memory:**
```bash
curl -X POST http://localhost:8000/retrieve-memory \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "position": [10, 20, 30, 40, 50, 60],
    "agent": "fraud-detector-001",
    "context": "internal"
  }'
```

### SaaS Tenant Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/saas/tenants` | Create a new tenant |
| GET | `/saas/tenants` | List your tenants |
| GET | `/saas/tenants/{id}` | Get tenant details |
| GET | `/saas/tenants/{id}/audit-report` | Generate audit report |
| GET | `/saas/tenants/{id}/usage` | Monthly usage report |

### Flock Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/saas/tenants/{tenant_id}/flocks` | Create a flock |
| GET | `/saas/tenants/{tenant_id}/flocks` | List flocks for tenant |
| GET | `/saas/flocks/{flock_id}` | Get flock details + dashboard |
| POST | `/saas/flocks/{flock_id}/sheep` | Spawn an agent |
| POST | `/saas/flocks/{flock_id}/heartbeat/{sheep_id}` | Agent heartbeat |
| POST | `/saas/flocks/{flock_id}/refresh` | Health check + redistribute |

### Task Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/saas/flocks/{flock_id}/tasks` | Create and optionally assign a task |
| POST | `/saas/flocks/{flock_id}/tasks/{task_id}/assign` | Assign task to agent |
| POST | `/saas/flocks/{flock_id}/tasks/{task_id}/complete` | Mark task complete |

### Governance

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/saas/governance/check` | Run governance vote on an action |

### Billing

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/billing/plans` | No | List subscription plans |
| POST | `/billing/checkout` | No | Create Stripe checkout session |
| GET | `/billing/success` | No | Post-checkout landing (returns API key) |
| GET | `/billing/cancel` | No | Canceled checkout landing |
| POST | `/billing/webhook` | Stripe sig | Handle Stripe lifecycle events |
| GET | `/billing/status/{api_key}` | No | Check billing status for a key |

### Mobile Autonomy / Connectors

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mobile/connectors` | Register external connector (Zapier, n8n, Shopify) |
| GET | `/mobile/connectors` | List your connectors |
| GET | `/mobile/connectors/templates` | Get pre-built connector profiles |
| GET | `/mobile/connectors/{id}` | Get connector details |

### Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Both provide interactive request builders with full schema documentation.

---

## 10. Troubleshooting and FAQ

### "Rate limit exceeded (100 req/min)"

The default rate limiter allows 100 requests per minute per API key. For higher throughput, deploy multiple API instances behind a load balancer, or modify `RateLimiter` in `src/api/main.py`.

### "Invalid API key"

The demo keys are `demo_key_12345` and `pilot_key_67890`. In production, API keys are provisioned automatically through Stripe checkout. Check `/billing/status/{key}` to verify a key is active.

### "Plan flock limit reached"

Your tenant's plan restricts the number of flocks. Upgrade the plan (Starter: 1 flock, Growth: 5, Enterprise: 25) or delete unused flocks.

### "Plan agent limit reached"

Same as above but for agents within flocks. Starter allows 8 agents total, Growth 40, Enterprise 250.

### Governance always returns QUARANTINE

If you have no active validators in your flock, the default decision is QUARANTINE with the reason "No active validators." Spawn at least one agent with `track: governance` and ensure it has sent a recent heartbeat.

### Agents keep getting frozen

Agents are frozen when they miss heartbeats. The default timeout is 60 seconds with freeze after 2 missed heartbeats. Either increase `heartbeat_timeout_seconds` when creating the flock, or ensure your agent clients send heartbeats more frequently.

### How do I connect to my own LLM?

SCBE is model-agnostic. It governs the actions agents take, not the model that generates them. Wrap your LLM calls in an agent that checks governance before executing:

```python
# Pseudocode
decision = call_governance_check(action="write_to_db", context="external")
if decision["consensus"] == "ALLOW":
    execute_llm_action()
elif decision["consensus"] == "QUARANTINE":
    log_for_review(action)
else:
    block_action()
```

### Can I use this without the SaaS layer?

Yes. The core 14-layer pipeline works standalone. Install the npm or pip package and call the pipeline directly:

```bash
npm install scbe-aethermoore
```

```typescript
import { pipeline14 } from 'scbe-aethermoore/harmonic';
const result = pipeline14({ trust: 0.8, sensitivity: 0.3 });
console.log(result.decision); // "ALLOW"
```

---

## 11. Next Steps and Resources

### Starter Fleet Templates

The repository includes pre-built fleet configurations in `examples/npm/agents/`:

- **`fraud_detection_fleet.json`** -- Banking fraud workflow with detector, scorer, and audit notary agents
- **`research_browser_fleet.json`** -- Web research fleet with governed browser automation

And use-case scenarios in `examples/npm/use-cases/`:

- **`financial_fraud_triage.json`** -- End-to-end fraud detection scenario
- **`autonomous_research_review.json`** -- Autonomous research with governance checkpoints

### Documentation

| Resource | Location |
|----------|----------|
| Kernel Spec | `SPEC.md` |
| Langues Weighting System | `docs/LANGUES_WEIGHTING_SYSTEM.md` |
| HYDRA Orchestration | `docs/hydra/ARCHITECTURE.md` |
| HYDRA CLI Guide | `docs/HYDRA_CLI_USER_GUIDE.md` |
| Publishing Guide | `docs/PUBLISHING.md` |

### Live Demos

- **Streamlit Dashboard**: [scbe-aethermoore-ezaociw8wy6t5rnaynzvzc.streamlit.app](https://scbe-aethermoore-ezaociw8wy6t5rnaynzvzc.streamlit.app/)
- **npm Package**: [npmjs.com/package/scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore)
- **PyPI Package**: [pypi.org/project/scbe-aethermoore](https://pypi.org/project/scbe-aethermoore/)

### Get Help

- **GitHub Issues**: [github.com/issdandavis/SCBE-AETHERMOORE/issues](https://github.com/issdandavis/SCBE-AETHERMOORE/issues)
- **Email**: issdandavis@gmail.com
- **X/Twitter**: [@davisissac](https://x.com/davisissac)

### License

Open-source core: MIT License. Commercial terms apply to enterprise delivery packages. See `COMMERCIAL.md` and `CUSTOMER_LICENSE_AGREEMENT.md` in the repository.

---

*Built with hyperbolic geometry. Secured by mathematics. Ready for production.*

Copyright 2026 Issac Daniel Davis. All rights reserved.
