# Distributed Agentic Workflow Service

This document outlines a practical path from governance-only operation to a distributed workflow execution model where small/tiny LLMs can be plugged in and inherit SCBE controls immediately.

## System Mind Map

```mermaid
mindmap
  root((SCBE Distributed Agentic Service))
    Governance Foundation
      14-Layer risk scoring
      Sacred Tongues trust alignment
      ALLOW QUARANTINE DENY gate
    Distributed Runtime
      Workflow templates
      Step-level capability routing
      Adapter selection by context window
      Tenant-isolated execution IDs
    Tiny LLM Integration
      Adapter interface generate input output
      Local on-device models
      Cloud model fallback
      Capability registry
    Cross Branding
      Brand profiles
      Prompt prefix per tenant
      Voice and output tagline
      White-label output formatting
    Agent Roles
      Architect planning
      Coder implementation
      Tester validation
      Security hardening
    Enterprise Outcomes
      Faster onboarding of partner brands
      Lower inference cost with tiny models
      Auditable step outputs
      Immediate portability across systems
```

## Execution Flow

1. Register one or more `BrandProfile` records for tenant/partner identities.
2. Register tiny-LLM adapters with capabilities (planning, implementation, testing, security, etc.).
3. Register a workflow template that defines ordered steps.
4. Execute the workflow for a tenant prompt.
5. Collect step outputs with adapter IDs and token usage for auditability.

## Why this helps your stated goal

- **Beyond governance only:** the service executes multi-step workflows, not just policy decisions.
- **Tiny LLM ready:** each step routes to lightweight adapters with explicit capability matching.
- **Cross-branded:** tenant prompt-prefix/voice/tagline enables white-label reuse across partner systems.
- **Composable:** existing SCBE agent roles map directly to distributed workflow steps.
