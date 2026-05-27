---
title: "How a D&D Campaign Became an AI Governance Framework"
slug: how-a-dnd-campaign-became-an-ai-governance-framework
date: 2026-05-23
author: Issac Daniel Davis
tags: [origin-story, ai-governance, scbe, six-sacred-tongues, hyperbolic-geometry, worldbuilding]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# How a D&D Campaign Became an AI Governance Framework

This is going to sound like I'm lying. I'm not.

The coordinate system at the heart of SCBE — the one that uses six fictional languages to score AI inputs for safety violations in real time — came from a tabletop roleplaying campaign. 528 pages of session logs, lore documents, world maps, magic system rules. Five years of Everweave. Not a paper. Not a research project. A game.

The languages were already there. We'd been playing them for years without knowing they were a coordinate system.

---

## What Everweave was

Everweave started as a homebrewed D&D 5e campaign and drifted somewhere stranger. The magic system wasn't Vancian. It was linguistic. Different traditions spoke different tongues, and the tongues weren't interchangeable — each had its own semantic domain, its own constraints, things it could and couldn't name.

Six traditions. Six Sacred Tongues:

| Tongue | What it governed |
|--------|-----------------|
| Kor'aelin | Intent, origin, what something is trying to do |
| Avali | Messaging, transit, what moves between nodes |
| Runethic | Policy, constraint, what's binding and permanent |
| Cassisivadan | Computation, transformation, what performs operations |
| Umbroth | Containment, shadow, what's kept private |
| Draumric | Record, proof, chain of custody, authentication |

The game's magic system had a rule: you couldn't just use any tongue for any purpose. Draumric couldn't write transport. Avali couldn't bind permanently. The domains were enforced.

That's a coordinate system. Six orthogonal axes. Every action in the world maps to a point in the space they define.

I didn't see it for years. Then in 2023, while trying to solve a real problem — how do you detect adversarial AI inputs without a model call, deterministically, with auditable receipts? — I kept coming back to the tongues.

---

## The problem the tongues solved

The problem is this: existing safety classifiers are either model-based (slow, probabilistic, not auditable) or rule-based (fast, brittle, easy to evade with slight rephrasing). Neither gives you a geometry.

Geometry is what I wanted. Something where moving further from safe behavior has an actual cost — not just a probability threshold you can walk up to without triggering, but a space where the distance function itself punishes drift.

Hyperbolic geometry has that property. In the Poincaré ball model, the distance between two points grows exponentially as they approach the boundary. A safe input near the center is cheap to classify. An adversarial input drifting toward the edge pays an exponentially higher cost on every step.

The tongues became the six dimensions. Kor'aelin for intent signals. Draumric for authentication signals. The rest in between. Weights scaled by the golden ratio — φ^0 through φ^5, so governance-layer drift (toward high-weight Draumric) costs proportionally more than transport-layer drift (toward low-weight Avali). That wasn't a math decision first. It was a game design decision first. The tongues were always weighted differently in Everweave because authentication and record-keeping were supposed to be harder to fake than message routing.

I just finally understood why.

---

## Where it is now

The tokenizer vocabulary is 1,536 tokens — 256 per tongue, each in a 16×16 grid. Every input to the pipeline gets projected into six-dimensional hyperbolic space. The harmonic wall formula:

```
H(d, pd) = 1 / (1 + d_H + 2·pd)
```

Where `d_H` is the Poincaré ball distance from the trusted center, and `pd` is phase deviation — how far the input's tongue-pattern distribution is from the expected routing for its claimed type.

Against 91 adversarial attacks across 10 attack classes: F1 of 0.813, detection rate 74.2%, full pipeline latency under 8ms on commodity hardware. No model call. No inference. Deterministic geometry from Layer 1 through Layer 13.

The code is at [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE). The tokenizer source is in `src/tokenizer/`. The 14-layer pipeline is in `src/harmonic/pipeline14.ts`. MIT OR Apache-2.0.

---

## What I'd tell someone who asked

The lore didn't produce the math by accident. 528 pages of Everweave forced me to be consistent. If Draumric couldn't do what Avali does, that rule had to hold for five years of sessions without falling apart. That kind of constraint pressure — sustained over time, socially enforced at the table — produces stable semantic distinctions that a quick brainstorm doesn't.

The game taught me what the dimensions were. The math just named them properly.

---

*Related: [The Six Sacred Tongues as a coordinate system](2026-05-23-the-six-sacred-tongues-coordinate-system.md) | [Hyperbolic geometry for AI governance](2026-05-23-hyperbolic-geometry-for-ai-governance.md)*
