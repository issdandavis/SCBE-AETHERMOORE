---
title: "Domain-Separated AI Governance: What Zero Trust Suggests for Model Control Planes"
published: true
tags: [ai, security, architecture, governance]
---

# Domain-Separated AI Governance: What Zero Trust Suggests for Model Control Planes

Most AI governance still behaves as if every model action belongs to one flat policy surface:

- prompt in
- model output out
- one safety layer after the fact

That makes deployment simple, but it collapses different kinds of actions into the same stream. A routing decision, a policy assertion, a transformation step, a privacy step, and an integrity check are not the same thing. Treating them as interchangeable makes audits harder and control blunter than it needs to be.

That is the problem SCBE-AETHERMOORE tries to address with its Six Tongues model.

## The standards backdrop

Two official sources are useful here.

NIST's AI RMF Playbook says organizations should incorporate trustworthiness considerations into the design, development, deployment, and use of AI systems.

NIST's Zero Trust Architecture guidance says zero trust narrows defenses from wide network perimeters down to individual or small groups of resources, with no implicit trust granted based on physical or network location.

Those two ideas fit AI systems better than most current guardrail stacks do.

If trustworthiness has to be handled across the full lifecycle, and if trust should be resource-specific rather than location-derived, then AI control planes should stop acting as if there is only one kind of model action.

## The SCBE pattern

In SCBE, the six tongues are:

- `KO`: intent and orchestration
- `AV`: transport and context flow
- `RU`: policy and binding
- `CA`: compute and transformation
- `UM`: privacy and concealment
- `DR`: schema and attestation

The important design choice is not the fantasy naming. It is the separation.

The project already defines tongue weighting and profile contracts in the repo:

- Langues weighting system: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/LANGUES_WEIGHTING_SYSTEM.md
- Sacred tongue tutorials: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/sacred-tongue-tutorials.md
- Python tongue implementation: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/src/crypto/sacred_tongues.py

That means this is not only a lore idea. The repo already contains explicit domain labels, weight profiles, and tokenizer/tutorial surfaces that make the separation inspectable.

## Why domain separation helps

Domain separation changes governance in three practical ways.

### 1. It clarifies failure modes

If a model drifts in `KO`, that is mostly an intent-selection problem.

If it drifts in `RU`, that is a policy problem.

If it drifts in `DR`, that is an integrity or attestation problem.

Flat guardrails tend to report all of those as generic safety failures. That is convenient for dashboards and bad for diagnosis.

### 2. It supports weighted response instead of only refusal

A system can allow low-cost `KO` or `AV` movement while requiring stronger `RU`, `UM`, or `DR` conditions before sensitive actions commit.

That is structurally closer to zero trust than a single global moderation pass. Access is not assumed. It is mediated according to the type of operation underway.

### 3. It improves auditability

If each major action can be described as a composition across known domains, operators can trace what actually happened instead of reading one blended risk score after the fact.

That lines up with the AI RMF's emphasis on governing, mapping, measuring, and managing risk rather than pretending one universal filter removes it.

## What exists today versus what is still a proposal

Implemented in the repo today:

- explicit tongue domains
- explicit weighting profiles
- deterministic tokenizer/tutorial examples
- multiple paths that already treat trust as structured rather than flat

Still not externally validated:

- cross-model benchmarks against conventional guardrails
- operator studies
- standards-aligned production evaluations

That distinction matters.

The careful claim is not that SCBE has solved AI governance.

The careful claim is that domain-separated control is a concrete architecture pattern worth testing against flat safety layers.

## Why I keep the fiction around

The related book project, *The Six Tongues Protocol*, describes the tongues as domain-separated authorization channels. That line survives because it teaches the system faster than a whitepaper introduction does.

The book is not proof.

It is a teaching layer for the architecture:

- book manuscript: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/content/book/reader-edition/the-six-tongues-protocol-full.md

Sometimes infrastructure needs a vocabulary before it can get a benchmark.

## The next real experiment

The next credible test is not another abstract claim. It is a workflow comparison:

Take one production AI task and compare:

- a flat moderation layer
- a domain-separated control layer

Measure:

- auditability
- false positive burden
- policy precision on sensitive actions
- added latency

If the separated lanes reduce operator confusion without making the system unusable, then the pattern has moved from internal architecture language to practical governance method.

## Sources

- NIST AI RMF Playbook: https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook
- NIST Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/ipd
- SCBE repo: https://github.com/issdandavis/SCBE-AETHERMOORE

If you want the repo paths or the claim map I used for this draft, I have them in the repo artifacts and can publish those next.
