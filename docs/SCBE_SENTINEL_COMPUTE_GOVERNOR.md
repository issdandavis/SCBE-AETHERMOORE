# SCBE Sentinel -- Compute Governor

## One-Liner

A hardware-aware compute authorization layer that prevents unnecessary AI inference, enforces thermal safety limits, and optimizes energy spend across edge, on-premise, and cloud deployments.

## Problem

- **Unsustainable power growth.** The U.S. DOE projects data center electricity consumption to rise from 4.4% to 12% of national demand by 2028, driven primarily by AI workloads. Current inference pipelines have no built-in power budget enforcement.
- **GPU thermal events and hardware loss.** Unmonitored GPU clusters experience thermal throttling, silent degradation, and premature failure. Facilities without active cooling monitoring have no automated mechanism to deny or defer high-wattage inference jobs.
- **Wasted compute on low-value inference.** Studies consistently show that 60-80% of production inference requests can be handled by sub-1B parameter models. Organizations running every request through full-scale models are burning capital on unnecessary GPU cycles.

## Solution

SCBE Sentinel is a tiered compute authorization system that sits between the inference request and the execution backend. Every incoming workload is classified by complexity, matched against the current energy budget and thermal state, and routed to the smallest model tier that can satisfy the request. High-cost jobs require explicit budget authorization. Jobs that would violate thermal or energy constraints are automatically deferred or denied.

## How It Works

Every inference request passes through a 4-tier authorization gate before execution begins.

| Tier | Model Size | Power Draw | Latency Target | Use Case |
|------|-----------|------------|----------------|----------|
| TINY | < 1B params | 5-15 W | < 50 ms | Classification, routing, keyword extraction |
| MEDIUM | 1B-7B params | 50-120 W | < 500 ms | Summarization, structured output, RAG retrieval |
| FULL | 7B-70B+ params | 200-700 W | < 5 s | Complex reasoning, code generation, multi-step agents |
| DENY | N/A | 0 W | Immediate | Thermal limit exceeded, budget exhausted, policy block |

### Example API Payload

```json
{
  "request_id": "req_a8c3f901",
  "prompt_hash": "sha256:4e2f...",
  "estimated_complexity": 0.23,
  "energy_budget_remaining_wh": 840.5,
  "thermal_state": {
    "gpu_temp_c": 71,
    "ambient_temp_c": 24,
    "cooling_active": true
  },
  "authorization": {
    "tier_assigned": "TINY",
    "model_target": "phi-3-mini",
    "max_tokens": 512,
    "cost_multiplier": 1.0
  }
}
```

When complexity exceeds the TINY threshold, the governor re-evaluates against MEDIUM and FULL tiers. Each escalation applies an exponential cost multiplier derived from the harmonic cost function, ensuring that high-resource jobs are never approved silently.

## Key Features

- **Energy-aware workload scheduling.** Each request is scored against real-time energy availability before a tier is assigned.
- **Solar, battery, and grid cost optimization.** The governor reads energy source mix and prioritizes renewable availability windows for batch workloads.
- **Thermal protection.** If cooling systems are offline or GPU temperature exceeds safe thresholds, GPU-bound tiers are automatically denied.
- **Priority-based batch scheduling.** Low-priority jobs are deferred to off-peak windows. High-priority jobs preempt the queue within budget limits.
- **Harmonic cost function.** Escalation from TINY to FULL follows an exponential cost curve, making wasteful over-provisioning economically visible and auditable.
- **Real-time energy budget tracking.** Per-tenant and per-workload energy consumption is metered and surfaced through the dashboard and API.

## Integration

```python
import requests

response = requests.post(
    "https://sentinel.your-domain.com/v1/authorize",
    json={"prompt": "Summarize this report.", "priority": "standard"},
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
tier = response.json()["authorization"]["tier_assigned"]
print(f"Authorized tier: {tier}")
```

## Deployment Options

| Mode | Description |
|------|-------------|
| **Edge** | ARM / RISC-V agent running on-device. Sub-10 ms authorization latency. Suitable for IoT gateways, field sensors, and embedded inference endpoints. |
| **On-Premise** | Kubernetes sidecar injected alongside inference pods. Intercepts requests at the service mesh layer. No application code changes required. |
| **Cloud API (SaaS)** | Managed multi-tenant endpoint. Includes dashboard, alerting, and audit log retention. |
| **Hybrid** | Edge monitor handles TINY/DENY decisions locally. MEDIUM and FULL requests escalate to a central cloud governor for budget validation. |

## Compliance and Standards

| Standard | Relevance |
|----------|-----------|
| **NIST AI RMF** (AI 100-1) | Governs risk identification and mitigation in AI systems. Sentinel provides measurable compute governance controls for MAP, MEASURE, and MANAGE functions. |
| **DoD Directive 3000.09** | Autonomous systems oversight. Sentinel enforces human-reviewable authorization tiers for high-consequence inference in defense applications. |
| **DOE Speed to Power** | Data center energy efficiency targets. Sentinel provides per-workload energy metering and automated demand reduction aligned with DOE reporting requirements. |
| **FERC Order 2222** | DER aggregation and grid participation. Sentinel's energy-aware scheduling enables AI workloads to participate as controllable loads in Virtual Power Plant (VPP) demand response programs. |

## Pricing

| Plan | Price | Included |
|------|-------|----------|
| **Starter** | $29/mo | Up to 100K authorizations/mo, 1 deployment target, email support, 7-day audit log |
| **Growth** | $99/mo | Up to 1M authorizations/mo, 5 deployment targets, priority support, 90-day audit log, batch scheduler |
| **Enterprise** | Custom | Unlimited authorizations, dedicated tenancy, SLA, on-premise deployment support, FERC/NIST compliance reporting, custom cost functions |

## Contact

**Issac Daniel Davis** -- Creator, SCBE-AETHERMOORE

- GitHub: [issdandavis](https://github.com/issdandavis)
- Site: [aethermoore.com](https://aethermoore.com)
