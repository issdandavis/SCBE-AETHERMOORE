---
title: "The Problem with Probability in AI Safety"
slug: the-problem-with-probability-in-ai-safety
date: 2026-05-23
author: Issac Daniel Davis
tags: [ai-safety, probability, determinism, governance, scbe, philosophy]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# The Problem with Probability in AI Safety

Every neural safety classifier returns a probability. "This input has a 0.94 probability of being safe." The number sounds authoritative. It isn't quite.

Here's the problem: the probability is a property of the model's internal state, not a property of the input. If you retrain the model, the probability changes. If the model's context window handles the input differently in a batch versus alone, the probability changes. If the softmax temperature is tuned differently, the probability changes. The input hasn't changed. The number has.

For most ML applications, this is fine. You're not making safety decisions. You're trying to maximize a reward signal, and probabilistic outputs are the right tool.

For governance — for the systems that decide whether an AI agent's actions are permitted — probabilistic outputs have a structural problem: they're not auditable.

---

## What auditable means

An auditable decision is one where you can reconstruct, after the fact, exactly what computation produced it. Given the inputs and the system version, you should be able to reproduce the output.

With a neural classifier: you can't. The output depends on floating-point arithmetic that may vary across hardware, across batch sizes, across framework versions. Two runs of the same input through the same model weights may produce different outputs in bit-exact comparison. More importantly: the model weights themselves change when you retrain. The "same" classifier that produced last week's decisions is not the same classifier that produces this week's decisions.

For compliance purposes, this means you can't verify a past governance decision against the current system. The system that made the decision may no longer exist in its original form.

---

## The alternative

Deterministic geometry.

The SCBE pipeline computes a fixed-point score for every input using mathematical operations that are reproducible across hardware, across time, and across system versions. The Poincaré distance formula:

```
d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
```

...is the same formula on any processor, in any language, in any year. The result for a specific input doesn't drift between runs. The score for an input from six months ago, run against the same pipeline version, returns the same score.

This doesn't mean the system is perfect. The 74.2% detection rate means 25.8% of adversarial attacks pass the geometry layer. That's a known, documented limitation. But the 74.2% that are caught are caught with a score that you can verify, an audit receipt that you can sign, and a decision that you can reproduce.

---

## The cost

Giving up probabilistic outputs means giving up generalization. A fine-tuned neural classifier can potentially catch novel attack patterns that the geometry layer wouldn't recognize — if the patterns show up in its training data and generalize. The geometry layer catches only what the geometric model captures.

This is a real cost. Novel adversarial patterns that don't map to tongue-dimension drift, that evade the Poincaré ball geometry, require the temporal coherence layers (L9–L11) for detection. And some fraction won't be caught at all.

The question is whether the auditability benefit outweighs the coverage cost for the specific use case. For high-stakes governance decisions in regulated environments — EU AI Act compliance, US federal procurement, critical infrastructure — auditable records are often a hard requirement. A system that catches 74.2% of attacks with verifiable receipts may satisfy compliance requirements that a system catching 95% without verifiable records doesn't.

---

## What changes when decisions are verifiable

When a governance decision is deterministic and signed, you can do things that probabilistic systems don't support:

**Run governance in CI.** The score for a test input is stable. You can include fixed-score assertions in your test suite. A governance regression is a CI failure.

**Diff versions.** When you update the pipeline, you can compare scores for the same inputs before and after. Changes are visible and documented.

**Verify receipts externally.** A third party — a regulator, an auditor, a customer — can verify a governance receipt without having access to the pipeline itself. They just need the signed receipt and the public key.

**Make commitments about behavior.** "This input will always produce this decision, against this pipeline version." That's a claim you can test and falsify. You can't make the same claim about a probabilistic system without hedging until the claim is meaningless.

---

The SCBE pipeline is open source. The determinism is testable. [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) — run `npm test` and watch the fixed-score assertions pass.

*Related: [Deterministic AI governance: what it means to diff safety](/articles/deterministic-ai-governance-what-it-means-to-diff-safety)*
