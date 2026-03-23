# From Six Tongues to Zero Trust: A Domain-Separated Pattern for AI Governance

**Issac Davis**  
SCBE-AETHERMOORE research draft  
March 19, 2026

## Abstract

This article frames the Six Sacred Tongues in SCBE-AETHERMOORE as a domain-separated governance pattern for AI systems. The core argument is modest: if modern security architecture already treats trust as contextual and resource-specific, then AI control planes should stop treating all model actions as if they belong to one flat policy surface. SCBE's tongue model proposes six explicit semantic lanes for intent, transport, policy, compute, privacy, and attestation. This does not replace standards work from NIST. It offers a way to operationalize it.

## Why this pattern matters

NIST's AI RMF Playbook states that trustworthiness considerations must be incorporated across the design, development, deployment, and use of AI systems. NIST's Zero Trust Architecture guidance makes a parallel point in cybersecurity: no implicit trust should be granted based on location alone, and protection should narrow from broad perimeters down to specific resources.

Those two ideas are directly compatible with a multi-lane AI control model.

Most model governance still behaves as though there is one policy domain:

- prompt in
- model output out
- safety layer after the fact

That shape is easy to deploy, but it collapses qualitatively different operations into one stream. A routing decision, a policy assertion, a transformation step, a redaction step, and an attestation step are not the same kind of action. SCBE's Six Tongues treat them as distinct.

## The SCBE pattern

In the SCBE system, the six tongues are:

- `KO`: intent and orchestration
- `AV`: transport and context flow
- `RU`: policy and binding
- `CA`: compute and transformation
- `UM`: privacy and concealment
- `DR`: schema and attestation

The important design choice is not the names. It is the separation.

The repo already defines a mathematical contract for weighted tongue behavior in [docs/LANGUES_WEIGHTING_SYSTEM.md](C:/Users/issda/SCBE-AETHERMOORE/docs/LANGUES_WEIGHTING_SYSTEM.md). That contract specifies positive weighted costs, bounded temporal variation, and explicit profile labeling for different operating modes. The tokenizer and language-security scaffolds already exist in:

- [src/crypto/sacred_tongues.py](C:/Users/issda/SCBE-AETHERMOORE/src/crypto/sacred_tongues.py)
- [src/integrations/six-tongues.ts](C:/Users/issda/SCBE-AETHERMOORE/src/integrations/six-tongues.ts)
- [docs/sacred-tongue-tutorials.md](C:/Users/issda/SCBE-AETHERMOORE/docs/sacred-tongue-tutorials.md)

That means the article is not arguing from fiction alone. The fiction supplied the vocabulary, but the implementation effort made the separation testable.

## What domain separation changes

Domain separation changes governance in three useful ways.

First, it clarifies which failures matter. If a model drifts in `KO`, that is a problem of intent selection. If it drifts in `RU`, that is a policy problem. If it drifts in `DR`, that is an integrity problem. Flat guardrails tend to report all of those as generic safety events.

Second, it supports weighted response instead of binary refusal. A system can allow low-cost `KO` or `AV` movement while requiring stronger `RU`, `UM`, or `DR` conditions before committing to sensitive actions. That is structurally similar to how zero-trust systems gate access by resource sensitivity instead of network location.

Third, it makes audits easier. If every major decision can be described as a composition across known domains, traceability improves. That aligns with the NIST AI RMF emphasis on governing, mapping, measuring, and managing risk rather than pretending risk can be removed by one universal filter.

## Why the book matters here

The published novel manuscript in [content/book/reader-edition/the-six-tongues-protocol-full.md](C:/Users/issda/SCBE-AETHERMOORE/content/book/reader-edition/the-six-tongues-protocol-full.md) describes the Six Tongues as "domain-separated authorization channels." That line is useful because it compresses the architecture into a narrative form a non-specialist can remember.

The book is not proof. It is a teaching layer.

That matters because one of the hardest problems in AI governance is not inventing a new control primitive. It is teaching operators, developers, and decision-makers to think in separable control domains at all.

## What is implemented versus proposed

Implemented in the repo today:

- explicit tongue domains and weighting profiles
- deterministic tokenizer examples and tutorials
- multiple code paths that already treat trust as structured rather than flat

Still proposed, not externally validated:

- cross-model benchmarking showing domain-separated routing beats conventional guardrails
- controlled studies on operator usability
- standards mapping beyond internal experiments

That distinction matters. The responsible claim is not that SCBE has already solved AI governance. The responsible claim is that it provides a concrete domain-separated architecture worth testing against existing governance baselines.

## Research direction

The next credible experiment is to map one production workflow onto tongue-separated events and compare it against a flat moderation layer on three measures:

- auditability
- false positive burden
- policy precision on sensitive actions

If the separated lanes improve those without unacceptable latency, then the system has moved from an internal language system to a practical governance pattern.

## Sources

### Official external sources

- NIST AI RMF Playbook: https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/ipd

### Internal SCBE sources

- [docs/LANGUES_WEIGHTING_SYSTEM.md](C:/Users/issda/SCBE-AETHERMOORE/docs/LANGUES_WEIGHTING_SYSTEM.md)
- [docs/sacred-tongue-tutorials.md](C:/Users/issda/SCBE-AETHERMOORE/docs/sacred-tongue-tutorials.md)
- [src/crypto/sacred_tongues.py](C:/Users/issda/SCBE-AETHERMOORE/src/crypto/sacred_tongues.py)
- [content/book/reader-edition/the-six-tongues-protocol-full.md](C:/Users/issda/SCBE-AETHERMOORE/content/book/reader-edition/the-six-tongues-protocol-full.md)
