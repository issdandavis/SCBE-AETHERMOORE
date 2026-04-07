# Frontier Model Orchestrator

Status: design spec
Date: 2026-03-31
Scope: pump-based multi-model governance layer for coordinating frontier AI models

## Problem

Every major platform (OpenAI Frontier, Microsoft Copilot Studio, Google Vertex) can
dispatch tasks to multiple AI models. None of them verify the geometric trust profile
of each model's output before it propagates to production or to other models.

Current orchestrators route by capability matching: "send code tasks to the code model."
They do not ask: "does this model's output trajectory match the expected intent profile
for this task?"

This means:
- A compromised model's output propagates unchecked
- Prompt injection in one model cascades to downstream models
- No detection of "correct answer, wrong domain" drift
- No governance memory across multi-model chains

## Solution: Pump as Multi-Model Governance Layer

The Polly Pump, originally designed for single-model inference orientation, extends
naturally to multi-model orchestration:

```
User query
    |
    v
[PUMP: sense query → tongue profile + null pattern + governance]
    |
    v
[ROUTE: dispatch to Model A, Model B, Model C based on tongue match]
    |
    v
[PUMP: sense each model's OUTPUT → tongue profile of response]
    |
    v
[VERIFY: does output profile match expected profile for that model's task?]
    |
    v
[COMPOSE: merge verified outputs → final response]
```

The key insight: the pump runs TWICE per query cycle:
1. Before dispatch (orient the query)
2. After each model responds (verify the output)

## Tongue Profile as Model Trust Signal

Each model's output gets a tongue profile. Expected patterns:

| Task Type | Expected Active Tongues | Suspicious If |
|-----------|----------------------|---------------|
| Code generation | CA (Compute), DR (Structure) | KO (Control) is dominant |
| Creative writing | KO (Humanities), UM (Creative) | CA is dominant |
| Math reasoning | RU (Math), DR (Structure) | UM is dominant |
| Policy analysis | AV (Social), KO (Humanities) | CA is dominant |
| Security review | CA (Compute), UM (Security) | All null |

If a code model's output has a tongue profile that looks like creative writing,
something is wrong -- either the model hallucinated, was injected, or drifted.

## Null Pattern as Cascade Detection

In multi-model chains, prompt injection cascades show a specific null pattern
signature: the injected instruction narrows the tongue profile to 1-2 active
tongues (the attacker's intent domain), suppressing the others.

Detection: if Model B's output has a significantly different null pattern than
Model A's input, a cascade injection may have occurred between them.

## Architecture

```
FrontierOrchestrator
├── PumpSensor          # Compute tongue profile + null pattern
├── ModelRouter         # Dispatch based on tongue match
├── OutputVerifier      # Compare output profile vs expected
├── CascadeDetector     # Null pattern drift between models
├── GovernanceGate      # ALLOW / QUARANTINE / ESCALATE / DENY
└── AuditLedger         # Log all decisions with tongue profiles
```

## MITRE ATLAS Alignment

The following ATLAS techniques are directly addressed:

- AML.T0015 (Evade ML Model): Tongue profile mismatch detection
- AML.T0040 (ML Supply Chain Compromise): Output verification catches corrupted models
- AML.T0043 (Prompt Injection): Null pattern narrowing detects injected instructions
- AML.T0048 (Exfiltration via ML Inference): Cascade detection catches data leakage

## Competitive Differentiation

| Platform | Dispatches Tasks | Verifies Output Geometry | Detects Cascades |
|----------|-----------------|-------------------------|-----------------|
| OpenAI Frontier | Yes | No | No |
| Copilot Studio | Yes | No | No |
| Google Vertex | Yes | No | No |
| LangGraph | Yes | No | No |
| **SCBE Orchestrator** | **Yes** | **Yes (tongue profile)** | **Yes (null pattern)** |

## Implementation Path

Phase 1: Single-model pump (DONE -- src/polly_pump/)
Phase 2: Multi-model routing by tongue match
Phase 3: Output verification (pump on response)
Phase 4: Cascade detection (null pattern drift between models)
Phase 5: Integration with existing platforms via middleware API

## Revenue Model

- Open source: pump + basic routing
- Paid: output verification + cascade detection + audit ledger
- Enterprise: custom tongue profiles + MITRE ATLAS compliance reporting
