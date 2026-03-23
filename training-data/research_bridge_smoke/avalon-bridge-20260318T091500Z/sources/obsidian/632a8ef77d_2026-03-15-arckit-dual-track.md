# ArcKit Dual-Track Scan

Date: 2026-03-15

This note tracks two unrelated projects with the same or similar name:

1. Enterprise ArcKit
2. ARC / ARC-AGI `arckit`

They are not substitutes for each other.

## Live Forks

- Enterprise ArcKit fork:
  - Upstream: `https://github.com/tractorjuice/arckit-codex`
  - Fork: `https://github.com/issdandavis/arckit-codex`
- ARC / ARC-AGI fork:
  - Upstream: `https://github.com/mxbi/arckit`
  - Fork: `https://github.com/issdandavis/arckit`

No local clone was created in this pass. This was kept cloud-first to avoid unnecessary disk use.

## What Each One Is

### Enterprise ArcKit

Public surface currently observed:
- `tractorjuice/arckit-codex`
- `tractorjuice/arckit-gemini`

Why it matters:
- Enterprise architecture governance
- vendor procurement and traceability
- AI-assisted command flows
- design/review/audit artifact production

Best SCBE fit:
- governance shell around multi-agent systems
- policy, procurement, architecture, and evidence workflows
- UK-facing architecture and AI governance positioning

Not its job:
- image generation
- panel rendering
- LoRA training

### ARC `arckit`

Public surface currently observed:
- `mxbi/arckit`
- PyPI package `arckit`

Why it matters:
- ARC / ARC-AGI dataset loading
- puzzle/reasoning task tooling
- scoring and evaluation harnesses

Best SCBE fit:
- symbolic reasoning lane
- rule-transform validation
- benchmark-style evaluation for agent reasoning

Not its job:
- enterprise governance shell
- runtime procurement workflow
- webtoon render orchestration

## SCBE Opportunity

The interesting business angle is not to replace Enterprise ArcKit.

The stronger position is:
- ArcKit handles architecture governance, procurement, and pre-runtime decisions
- SCBE handles runtime multi-agent execution governance
- SCBE can provide the operational layer ArcKit users run after the design artifacts are approved

That means:
- policy to execution traceability
- model routing with evidence
- source verification before action
- governed generation / publish pipelines
- audit packets from live runs instead of only design-time docs

## Next Useful Reads

- Read the forked Enterprise ArcKit repo first:
  - `https://github.com/issdandavis/arckit-codex`
- Then inspect the ARC toolkit:
  - `https://github.com/issdandavis/arckit`

## Recommendation

If this turns into a real product lane, position SCBE as:
- an AI runtime governance layer
- an agent execution fabric
- a verification and evidence engine

That complements Enterprise ArcKit instead of competing head-on with its document-centric governance workflow.
