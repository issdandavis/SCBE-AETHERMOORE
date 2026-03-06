# SCBE Pilot Conversion Packet

Date: 2026-03-06  
Owner: Issac Daniel Davis  
Status: execution-ready

## Objective

Turn technical proof into paid pilot conversations by shipping a compact packet
that buyers can evaluate in one pass.

## Packet Contents

1. Target pipeline (ranked): `docs/market/2026-03-06-target-pipeline.csv`
2. Outreach cadence + templates: `docs/market/2026-03-06-outreach-cadence.md`
3. Demo-to-decision evidence runner: `scripts/system/pilot_demo_to_decision.py`

## 60-90 Day Pilot Scope (Template)

### Phase 1 (Days 1-15): Integration Discovery
- Confirm API boundary and auth model.
- Wire SCBE lattice route into one customer workflow.
- Define decision metrics and pass/fail criteria.

### Phase 2 (Days 16-45): Controlled Prototype
- Run 2.5D lattice ingestion and branch execution on customer-like inputs.
- Apply governance decisions (ALLOW/QUARANTINE/DEFER/DENY) in pre-production.
- Produce deterministic replay artifacts for each run.

### Phase 3 (Days 46-75): Operational Validation
- Stress test route and queue behavior under burst traffic.
- Validate route-level failure handling and governance escalation.
- Compare baseline workflow vs SCBE-governed workflow.

### Phase 4 (Days 76-90): Decision Package
- Deliver evidence index, metrics summary, and rollout recommendation.
- Define follow-on scope (production lane or expanded mission lane).

## Buyer-Facing Acceptance Gates

1. Reproducibility: same input packet yields stable decision path.
2. Safety posture: no unresolved critical findings in pilot scope.
3. Performance: pilot SLA threshold met for designated workflow.
4. Auditability: each decision links to traceable evidence output.

## Demo-to-Decision Command Path

```bash
python scripts/system/pilot_demo_to_decision.py
```

Output artifacts:
- `artifacts/pilot_demo/<run_id>/evidence_index.json`
- `artifacts/pilot_demo/<run_id>/evidence_index.md`
- `artifacts/pilot_demo/<run_id>/steps/*`

## Positioning Statement (Short)

SCBE is a governed interoperability layer for autonomous workflows. It does not
replace customer models; it constrains, routes, and audits model behavior across
multi-agent execution paths.
