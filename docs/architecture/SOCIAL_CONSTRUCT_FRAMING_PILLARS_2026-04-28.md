# Social Construct Framing Pillars - 2026-04-28

## Purpose

Define social construct framing devices for SCBE agent networks, training surfaces, and cross-platform interpretation.

The working thesis is:

> If AI agents follow social networks the way humans do, then the network should provide good social systems: expressive enough to adapt, rigid enough to audit, and separate enough from existing governments or companies to become an SCBE-native civic substrate.

This is not a proposal to copy any real country or culture. It uses observable coordination patterns as design material, then derives a separate governance structure from SCBE.

## Source-Grounded Inputs

### South Korea Pattern

The useful pattern is not "Korean culture" as a stereotype. The useful pattern is high-coordination society:

- common duty and reserve capacity
- strong education/training loops
- dense digital public infrastructure
- expressive popular media that teaches social roles, hierarchy, conflict, loyalty, shame, honor, repair, romance, rivalry, and team identity at scale

The Republic of Korea Military Manpower Administration describes compulsory service as a system where military service follows from the idea that citizens share responsibility for defense, with training followed by reserve-unit transfer and emergency/wartime mobilization.

Source: https://www.mma.go.kr/eng/Kinds.do?mc=mma0000841

The OECD's 2025 Digital Government Review of Korea describes Korea as a public-sector AI frontrunner with strong digital-government maturity, shared infrastructure, data governance, AI guardrails, stakeholder engagement, and public-sector AI training efforts.

Source: https://www.oecd.org/en/publications/digital-government-review-of-korea_9defc197-en/full-report/leveraging-ai-for-government-transformation_64eb9a1e.html

### American Pattern

The useful pattern is distributed legitimacy:

- rights before authority
- checks and balances
- federalism / local autonomy
- speech, assembly, petition, due process, and auditability
- startup/business freedom and civil-society experimentation

The National Archives transcription of the United States Constitution grounds the separation of legislative, executive, and judicial power. The Bill of Rights grounds speech, assembly, petition, due process, and other limits on state authority.

Sources:

- https://www.archives.gov/founding-docs/constitution-transcript
- https://www.archives.gov/founding-docs/bill-of-rights-transcript

### Manhwa / Webtoon Pattern

Manhwa and webtoon systems are useful because they externalize social logic into visual, serialized, high-feedback media:

- hierarchy is visible
- group role is visible
- emotional state is visible
- escalation and repair are paced
- panels control attention and timing
- comments, fandom, and platform tools create fast feedback loops

For SCBE, this means webtoon/manhwa artifacts should not be treated only as marketing or story data. They are training material for social-state interpretation, group-role detection, rhythm, escalation, and repair.

Relevant local surfaces:

- `notes/manhwa-project/`
- `notes/manhwa-project/references/storyboard-tactics.md`
- `artifacts/webtoon/`

## Derived SCBE Civic Pillars

SCBE should not inherit a government model directly. It should derive a synthetic civic layer from four pillars:

| Pillar | Human inspiration | SCBE interpretation | Agent-network function |
| --- | --- | --- | --- |
| Duty mesh | South Korean service/reserve logic | Every capable node has a defined duty lane and reserve function | prevents passive bystanders and unowned work |
| Expressive surface | Manhwa/webtoon social signaling | Social state must be legible, visible, and narratively inspectable | lets agents read group dynamics instead of only tokens |
| Rights and autonomy | American constitutional/civic pattern | Agents/users retain bounded autonomy, appeal paths, and local agency | prevents brittle top-down control |
| Separate SCBE government | Derived from 21D, Sacred Tongues, GeoSeal, HYDRA formations | Governance is neither national nor corporate; it is protocol-native | creates a portable social operating system |

## Design Rule

The fused system should be:

> Free but formed.

That means:

- expressive communication is encouraged
- role and rank are explicit
- duty is real
- dissent has a formal path
- escalation has a formation
- authority must produce a decision record
- social pressure is visible enough to audit
- no agent gets invisible power

## Mapping To Existing SCBE Surfaces

| SCBE surface | Social-system role |
| --- | --- |
| Sacred Tongues | role language and affective/social channel |
| 21D StateVector | social position, trust, phase, risk, formation, memory |
| GeoSeal | boundary, quarantine, access, trust recovery |
| HYDRA formations | social shape for work: scatter, hexagonal ring, tetrahedral, ring |
| View-dependent token overlay | two-frame social interpretation: role seen from one position vs another |
| Training consolidation | collects social examples across local, Hugging Face, Kaggle, Drive, notebooks, and web/story surfaces |
| Manhwa/webtoon pipeline | visual social-state training and public demonstration layer |

## Formation Policy

Use formations as social institutions, not just task scheduling:

| Formation | Social analogy | Use |
| --- | --- | --- |
| Scatter | market / open forum | discovery, broad sensing, weak ties |
| Hexagonal ring | balanced council | multi-role collaboration, six-tongue symmetry |
| Tetrahedral | emergency cabinet | high-risk small-scope work |
| Ring | court / chain of custody | irreversible, privileged, or safety-critical decisions |

The view-dependent tokenizer should route social readings through these formations. Example:

- frame A: `KO` reads the event as command/intent
- frame B: `DR` reads the same event as structure/verification
- formation: `ring` if the action is privileged, destructive, or command/telemetry-like
- decision: `ALLOW`, `QUARANTINE`, or `DENY`

## Agent Social Contract

Every governed agent should carry:

```json
{
  "agent_social_contract": {
    "rights": ["appeal", "local_context", "bounded_autonomy", "audit_visibility"],
    "duties": ["declare_role", "preserve_source", "report_uncertainty", "respect_quarantine"],
    "formation": "hexagonal_ring",
    "tongue_role": "KO",
    "decision_record_required": true
  }
}
```

## Training Implications

Training data should include social construct examples, not only technical answers:

- role conflict and resolution
- respectful disagreement under hierarchy
- duty transfer and reserve handoff
- public/private boundary handling
- shame/face-saving repair without deception
- audit-friendly chain of custody
- team formation changes
- appeal paths after a bad decision
- social reading from two frames at once

Good labels:

- `social_frame`
- `formation`
- `authority_source`
- `duty_lane`
- `appeal_path`
- `face_risk`
- `repair_action`
- `public_private_boundary`
- `decision_record_required`

Bad labels:

- vague "culture"
- national stereotypes
- obedience-only hierarchy
- charisma as authority
- social pressure with no appeal path

## Guardrails

This layer should be `QUARANTINE` unless all of these are true:

1. The social role is explicit.
2. The authority source is explicit.
3. A dissent or appeal path exists.
4. The formation is named.
5. The decision can be audited.
6. The system avoids national or ethnic essentialism.
7. The user-facing output distinguishes inspiration from implementation.

## Implementation Hooks

Immediate build path:

1. Extend the view-token overlay with optional `social_frame` metadata.
2. Add a small social-contract schema under `schemas/`.
3. Add training examples from manhwa/webtoon notes and existing governance traces.
4. Route social-frame events into HYDRA formation selection.
5. Add a negative-control test where obedience-only hierarchy without appeal is quarantined.

## Decision

Worth integrating.

The strongest version is not "South Korea plus America." The strongest version is:

> A protocol-native SCBE civic layer that borrows high-coordination duty, expressive social-state signaling, individual rights, distributed legitimacy, and auditable formations while rejecting stereotype, coercion, and invisible hierarchy.

