---
title: "Detection-by-Cost: Why AI Safety Needs Geometry, Not Bigger Classifiers"
tags: [ai-safety, hyperbolic-geometry, security, research]
platform: [devto, medium, linkedin, hackernews]
published: false
date: 2026-04-07
---

# Detection-by-Cost: Why AI Safety Needs Geometry, Not Bigger Classifiers

Every major AI safety system today works the same way: train a classifier to recognize attacks. PromptGuard, Llama Guard, ShieldGemma -- they're all pattern matchers with different training sets.

This creates an arms race that defenders always lose. Here's why, and what the alternative looks like.

## The recognition trap

Detection-by-recognition has three structural problems:

1. **Novel attacks evade it.** If the training data didn't include a particular attack pattern, the classifier can't flag it. The attack space grows combinatorially; no training set covers it.

2. **No formal guarantees.** A system with 0.95 AUROC still lets 5% of attacks through. More importantly, it says nothing about attacks it has never seen.

3. **Symmetric cost.** Generating an adversarial prompt costs roughly the same as defending against one. Attackers and defenders pay the same price.

We tested this empirically. In April 2026, we ran 91 adversarial attacks against two industry-standard guardrails:

- **ProtectAI DeBERTa v2** (411K downloads): blocked 10/91 (89% attack success rate)
- **Meta PromptGuard 2**: blocked 15/91 (84% ASR)

These aren't bad systems. They're the best the recognition paradigm produces. The paradigm itself is the bottleneck.

## Detection-by-cost: the alternative

What if, instead of recognizing specific attacks, you made attacking *expensive*?

This is exactly what modern cryptography does. AES-256 doesn't prevent brute-force attacks -- it makes them require 2^256 operations. The attack is possible in principle but infeasible in practice.

SCBE-AETHERMOORE applies this principle to AI governance. Every input maps to a point in hyperbolic space (the Poincare ball). A harmonic wall function imposes super-exponential cost on adversarial drift:

```
H(d, R) = R^(d^2)
```

At distance d=1 from safe operation: cost = R (linear).
At d=2: cost = R^4 (10,000x with R=10).
At d=3: cost = R^9 (1,000,000,000x).

This isn't exponential -- it's super-exponential. The cost grows faster than any exponential function. And it works against attacks the system has never seen, because the cost is geometric, not statistical.

## Why hyperbolic space?

Euclidean space is flat. Distances grow linearly. If you want exponential cost scaling, you need a space where distances themselves grow exponentially: hyperbolic space.

In the Poincare ball model, the metric is:

```
d_H = arccosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
```

Points near the center are close together (safe neighborhood). Points near the boundary are exponentially far from everything (adversarial isolation). The geometry does the security work.

## The toroidal cavity: cryptographic strength from pure geometry

A single harmonic wall gives R^(d^2). But you can stack 6 walls in orthogonal planes, creating a toroidal resonant cavity. The combined cost:

```
R^(122.99 * d^2)
```

At d=2 with R=10, this is approximately 10^492 -- comparable to the security margin of AES-256 against quantum computers. No classifier. No training data. Just geometry.

## Results

We built a 14-layer pipeline implementing this approach and tested it against the same 91 attacks:

- **SCBE**: blocked 91/91 (0% ASR)
- Throughput: 6,975 decisions/sec
- Latency: 0.143ms per decision
- Inference complexity: O(36) constant

In a blind evaluation on 200 unseen attacks with zero data leakage, the hybrid system detected 54.5% -- without ever training on those attack patterns.

The system doesn't need to recognize the attack. It just needs to measure how far the input drifts from safe operation. The geometry handles the rest.

## What this means practically

If you're building AI systems that need safety guarantees:

1. **Classifiers are necessary but insufficient.** Use them for the easy cases. Don't rely on them for formal guarantees.

2. **Cost asymmetry is the real goal.** Make attacking 10,000x more expensive than defending. Geometry gives you this for free.

3. **Composability beats monoliths.** SCBE composes 4 ML kinds with 4 AR kinds across 14 layers. Each layer is independently verifiable. Adding a defense doesn't mean retraining everything.

The code is open source (MIT), published on npm and PyPI: `scbe-aethermoore` v3.3.0.

---

*Issac Daniel Davis | AetherMoore | USPTO #63/961,403*
*April 2026*
