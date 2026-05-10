# M5 Mesh Foundry Product and Service Blueprint

Status: active sellable surface

## Purpose

M5 Mesh Foundry is the practical product layer for SCBE-AETHERMOORE: governance-aware data ingestion, routing, audit, and intelligence operations for teams using AI tools.

It packages the existing SCBE agent bus, governance logs, training capture, and report generation into a buyer-facing service that can start small and expand.

## Buyer Problem

Teams are adopting AI tools faster than they can document, audit, and govern them. Their common gaps are:

- no durable record of prompts, outputs, decisions, and follow-up actions
- no clean separation between local/private work and cloud/provider work
- no repeatable evidence packet for internal review, clients, or regulators
- no clear way to turn operational traces into training/evaluation data

## Offers

### Launch Pack

Fixed implementation sprint for one workflow.

Deliverables:

- intake interview and workflow map
- governed folder / bus formation
- first dataset or trace capture
- one short governance report
- recommended next actions

### Monthly Ops

Managed ingestion and governance heartbeat.

Deliverables:

- monthly scan of one workflow
- delta report
- risk/change summary
- action list
- optional training capture

### Enterprise License

Dedicated deployment and support path for a team or regulated buyer.

Deliverables:

- private deployment plan
- policy and role mapping
- audit/export workflow
- optional blockchain/notarization adapter
- support and integration backlog

## System Components

- Agent bus workspace formation: `.aethermoor-bus/workspaces/<workspace-id>/`
- Intake and lead capture: `/hire`, `/v1/polly/lead`
- Commerce routing: `/v1/polly/chat`, `docs/offers.json`
- Training capture: Hugging Face dataset path and SFT consolidation
- Governance overlays: bijective tamper, identifier canonicality, Tree of Escalation
- Reports: snapshot and heartbeat deliverables

## Minimal Delivery Loop

1. Buyer purchases or requests a workflow review.
2. Intake collects workflow, artifacts, risk concerns, and desired output.
3. SCBE creates a workspace formation and records inputs.
4. Governance checks run over the supplied workflow or artifact set.
5. Buyer receives a short report with findings, fixes, and next steps.
6. Approved traces can be added to training/evaluation data.

## Pricing Surface

- Governance Snapshot: $500 fixed scope
- Governance Heartbeat: $99/month
- Toolkit / Training Vault: $29 each
- Service credits: $5+ pay-as-you-go for hosted routing/provider usage

Provider/model costs should be passed through with a small 2-5% coordination fee only where hosted usage is billable.

## Boundaries

M5 is not a promise to replace a buyer's compliance team, legal counsel, or security program. It is a workflow evidence and governance package that makes AI usage easier to inspect, improve, and operationalize.

