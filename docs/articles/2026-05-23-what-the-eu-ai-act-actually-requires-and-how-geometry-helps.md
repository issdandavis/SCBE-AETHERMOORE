---
title: "What the EU AI Act Actually Requires for High-Risk Systems (And How Geometry Helps)"
slug: what-the-eu-ai-act-actually-requires-and-how-geometry-helps
date: 2026-05-23
author: Issac Daniel Davis
tags: [eu-ai-act, compliance, ai-governance, audit-trail, scbe, article-9, article-15]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# What the EU AI Act Actually Requires for High-Risk Systems (And How Geometry Helps)

The EU AI Act is being described as either civilization-ending regulation or toothless theater depending on who you ask. Neither is accurate. For the specific category of high-risk AI systems — medical devices, critical infrastructure, employment decisions, biometric identification — the actual requirements are specific and not unreasonable. The hard part is the implementation.

Let me walk through the two requirements that most teams miss, and why a deterministic pipeline helps satisfy them.

---

## Article 9: Risk management system

Article 9 requires a risk management system that is "a continuous iterative process run throughout the entire lifecycle of a high-risk AI system." The key word is continuous. Not a one-time audit. Not a pre-launch review. A documented, ongoing process that identifies, analyzes, and mitigates risks as the system evolves.

Practically, this means:
- You need a system that can identify when a risk level has changed.
- You need to document the identification, analysis, and response.
- The documentation needs to be verifiable — not just notes in a Confluence page, but auditable records tied to specific system states.

With a model-based classifier, "continuous risk monitoring" is hard to operationalize. The model's behavior drifts between training runs. You can run periodic evaluations, but between evaluations, the system's actual risk level is unknown. The gap between evaluations is a compliance gap.

With a deterministic pipeline, you can run the Article 9 evaluation on every request. Every decision is a risk assessment. Every receipt is a documented outcome of that assessment. The pipeline is the continuous risk management system, not a separate audit tool.

---

## Article 15: Accuracy, robustness, and cybersecurity

Article 15 requires high-risk AI systems to be "resilient against attempts by unauthorized third parties to alter their use, outputs or performance through the exploitation of system vulnerabilities." It specifically mentions adversarial attacks.

The standard approach to satisfying Article 15 is an adversarial evaluation report: you run a test suite of adversarial attacks, report the detection rate, and attest that the system is robust. This gets you the document.

What it doesn't get you is the mathematical guarantee. A neural classifier has unknown failure modes — it might score 98% on your test suite and fail in ways you didn't anticipate on inputs in the tail of the distribution. You can't prove robustness, only demonstrate it on a sample.

The Poincaré ball geometry provides something closer to a mathematical guarantee. For a specific class of attack — adversarial inputs that work by moving semantic content in the embedding space — the cost of the attack is governed by the hyperbolic distance function, which grows exponentially as the attack tries to push toward the boundary while staying coherent. The defense isn't probabilistic; it's structural.

This doesn't cover all attack classes. But for the attacks it does cover, you can write the defense proof rather than just the benchmark result.

---

## The audit trail requirement

Both Article 9 and Article 15 require logging. Article 12 (transparency) requires that high-risk systems "automatically record events" in a way that allows post-hoc reconstruction of what the system did and why.

The SCBE pipeline produces a deterministic receipt for every decision: input hash, pipeline version, score components (d_H and pd separately), final H score, tier decision (ALLOW / QUARANTINE / ESCALATE / DENY), and cryptographic signature. The receipt is verifiable independently — you don't have to trust the pipeline operator's word that the decision was X; you can verify the receipt against the public key.

That's what Article 12 is actually asking for. Not just "we logged it," but "the log is verifiable."

---

## What this doesn't solve

The EU AI Act also requires conformity assessments, technical documentation (Article 11), human oversight provisions (Article 14), and registration in the EU AI database (Article 71) for certain high-risk categories. A governance pipeline doesn't substitute for any of those. It's the "resilience against adversarial attacks" and "continuous risk management" piece, not the whole compliance picture.

For teams that already have compliance processes in place and need the technical layer to satisfy Articles 9 and 15: that's where deterministic geometric governance fits.

---

The pipeline is open source. [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE). MIT OR Apache-2.0. The audit receipt format is in `src/governance/`. The adversarial test suite is in `tests/harmonic/`.

*This is not legal advice. EU AI Act interpretation is still evolving.*
