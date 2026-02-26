# Launch SKU: Agent Governance for Regulated Workflows

## Ideal Customer Profile (ICP)

**Primary ICP:** Mid-market and enterprise product teams deploying LLM agents into regulated workflows where decisions must be explainable, controllable, and exportable for compliance.

### Target segments
- Fintech, insurance, healthcare, and public-sector vendors operating under audit obligations.
- B2B SaaS platforms embedding agentic automation into customer-facing operations.
- Platform/security teams responsible for production guardrails across multiple agents and tools.

### Buying triggers
- Need to prevent unsafe tool calls before execution.
- Need to block or quarantine sensitive data egress in real time.
- Need machine-readable audit logs for internal controls and external regulators.

## Top 3 Launch Use Cases

1. **Tool-call control**
   - Enforce allow/deny policy on agent tool invocations (by tool, argument class, identity, and context).
   - Support deterministic authorize/deny/quarantine outcomes before execution.

2. **Data egress guard**
   - Inspect outbound payloads and tool arguments for regulated/sensitive content classes.
   - Quarantine or redact risky outputs to reduce exfiltration and policy breaches.

3. **Audit export**
   - Export decision and policy events to SIEM/data-lake destinations.
   - Preserve evidence chain for compliance reviews and incident postmortems.

## Pricing Unit (Launch Recommendation)

Use a **hybrid model** to align value with both usage and organizational footprint:

- **Primary meter:** **Per 1,000 decisions** (authorize/deny/quarantine evaluations).
- **Platform floor:** **Per tenant** base fee (control plane, policy lifecycle, retention).
- **Optional packaging:** **Per agent** bundles for customers that prefer predictable budgeting.

### Why this works
- Per-1k decisions tracks variable risk-screening load and scales with adoption.
- Per-tenant floor captures fixed compliance and governance value.
- Per-agent option simplifies procurement for teams with stable agent counts.

## Success SLOs (Launch)

1. **p95 authorize latency:** ≤ **120 ms** at launch, with target ≤ 80 ms by end of quarter.
2. **False quarantine rate:** ≤ **1.5%** for approved policy packs on reference traffic.
3. **Audit export SLA:** **99.9%** successful delivery within **5 minutes** of decision event creation.

## 12-Week Roadmap Tied to Revenue

| Timeline | Deliverable | Revenue Link | Monetization Impact |
|---|---|---|---|
| **Week 1–4** | **API + gateway** | Fastest path to production enforcement in customer pilots. | Unlock paid design partners billed per 1k decisions; start usage revenue immediately once traffic is routed. |
| **Week 5–8** | **Policy lifecycle + audit export** | Converts pilots to compliance-ready deployments. | Enables per-tenant platform fee and expansion from security buyer to compliance budget owner. |
| **Week 9–12** | **SDK + 2 reference integrations (OpenAI agent + browser agent)** | Reduces integration friction and broadens addressable agent stack. | Drives seat/agent expansion inside existing tenants and shortens sales cycles for new logos. |

## Commercial Packaging (Suggested)

- **Launch (Design Partner):** discounted per-1k decision rate + limited per-tenant fee, with implementation support.
- **Growth:** standard per-tenant platform fee + tiered per-1k decision pricing.
- **Enterprise:** volume-committed per-1k pricing, advanced retention/export controls, and custom SLA addenda.

## Definition of Launch Readiness

Launch SKU is ready when:
- API + gateway are GA for enforcement in at least two production-like customer environments.
- Policy lifecycle supports versioning, staged rollout, and rollback.
- Audit exports meet 99.9% / 5-minute SLA for two consecutive weeks.
- Reference integrations demonstrate end-to-end value on both OpenAI and browser-agent workflows.
