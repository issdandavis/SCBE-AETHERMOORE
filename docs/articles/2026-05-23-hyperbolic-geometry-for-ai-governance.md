---
title: "Hyperbolic Geometry for AI Governance: Why Distance Grows Exponentially When You Drift"
slug: hyperbolic-geometry-for-ai-governance
date: 2026-05-23
author: Issac Daniel Davis
tags: [hyperbolic-geometry, poincare-ball, ai-governance, adversarial-ai, scbe, math]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# Hyperbolic Geometry for AI Governance: Why Distance Grows Exponentially When You Drift

I'm going to explain hyperbolic geometry in about 600 words. I don't have a math degree. I came to this through a different door. So this is going to be the version that I wish someone had handed me when I started.

---

## Flat space has a problem

In ordinary Euclidean space — the space of flat surfaces, of school geometry — if you move away from a point, distance grows linearly. Move twice as far, cost doubles. Move ten times as far, cost multiplies by ten.

For AI governance, that's a weak property. If adversarial inputs cost linearly more to process than safe inputs, an adversary just needs to be moderately adversarial. The cost is manageable. The attack is worth it.

What you want is a space where the cost of being adversarial grows faster than the adversary's ability to compensate. You want a geometry where moving away from the trusted center becomes exponentially expensive.

Hyperbolic geometry has that property.

---

## The basic idea

Imagine a disk. The boundary of the disk is infinitely far away — you can walk toward it forever and never reach it. The interior is finite in space but infinite in distance from any center point as you approach the edge.

In this space, two points near the center are close together. Two points near the edge are very far apart, even if they look adjacent to an outside observer. The geometry is curved inward.

The formula for distance between two points `u` and `v` in the Poincaré ball model:

```
d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
```

The denominators `(1-‖u‖²)` and `(1-‖v‖²)` approach zero as points approach the boundary. The distance blows up. That's the hyperbolic property — points near the boundary are geometrically very far from each other even when they're Euclidean-close.

---

## How this applies to adversarial inputs

We embed token inputs into a six-dimensional Poincaré ball using the Six Sacred Tongues as coordinate dimensions. The trusted semantic center is near the origin. Safe, expected inputs cluster near the center. Low hyperbolic distance. Low cost.

An adversarial input — one that's trying to push the model into unsafe behavior — drifts. It doesn't look like normal inputs. Its tongue-dimension distribution is unusual. Its phase alignment is off. In the hyperbolic embedding, that drift translates to distance from the trusted center.

The harmonic wall score at Layer 12:

```
H(d, pd) = 1 / (1 + d_H + 2·pd)
```

As `d_H` (hyperbolic distance) grows, the score shrinks. But the growth isn't linear — because hyperbolic distance near the boundary is compounded by the denominator terms. Moving from 0.5 to 0.8 radius in the Poincaré ball costs more than moving from 0.0 to 0.5, even though the Euclidean step sizes are smaller.

This means adversarial inputs have to work against their own drift. The further they try to push, the more expensive their position becomes. The attack's cost function grows faster than linearly with adversarial intent. That's the property we're after.

---

## The numbers

From the adversarial test suite (91 attacks, 10 attack classes):

- F1 score: 0.813
- Detection rate: 74.2%
- Full pipeline latency: under 8ms on commodity hardware

The latency is low because there's no model call. The pipeline is deterministic geometry from Layer 1 through Layer 13. Same input, same output, every time. You can run it in CI. You can diff outputs. That's not something you can do with a model-based classifier.

---

## Why exponential cost matters for real adversaries

The common objection: adversaries will just try many slightly-adversarial prompts until one gets through.

True. But the hyperbolic geometry makes that harder in a specific way: inputs near the trusted center are cheap to process and land in ALLOW. Inputs far from the center get caught early (high d_H → low H score → DENY or ESCALATE). The middle zone — moderately adversarial inputs that are expensive to catch — is narrow in hyperbolic space because the distance function accelerates as you leave the center.

This isn't a complete defense. The 74.2% detection rate means 25.8% of attack attempts aren't caught at the geometry level. For those, the temporal coherence layers (L9–L11) accumulate signal across conversation history, and the phase deviation term `pd` grows as the input pattern diverges from legitimate tongue routing. Evasion is possible. It's just expensive, and gets more expensive with each evasive step.

---

## Further reading

The Poincaré ball implementation is in `src/harmonic/hyperbolic.ts`. The Layer 12 scoring is in `src/harmonic/harmonicScaling.ts`. The full 14-layer pipeline test suite is in `tests/harmonic/`.

The codebase: [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE). MIT OR Apache-2.0. No server required.

---

*Related: [The Six Sacred Tongues as a coordinate system](2026-05-23-the-six-sacred-tongues-coordinate-system.md)*
