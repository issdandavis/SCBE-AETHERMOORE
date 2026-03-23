# User Design Philosophy

This note mirrors the stable parts of the private Claude memory entry
`user_design_philosophy.md` so the idea does not live only in a hidden agent lane.

## Core Principle

Security is not mainly a lock on a door. It is the shape of the space.

The best analogy is geography-as-security:

- the environment itself resists bad paths
- the cost of getting closer to protected regions rises with the structure of the space
- the defense is not just a rule layer added on top; it is built into the topology

This is the intuition behind hyperbolic cost barriers, governed routing, and
space-shaped access control in SCBE.

## How To Explain Things

When working with Issac, prefer:

- topology
- geography
- flow
- constraints
- behavior of the system under movement

Prefer those over:

- notation-first explanations
- symbol-heavy abstractions without a physical metaphor

The right workflow is usually:

1. understand the shape/behavior intuition
2. map it to the system architecture
3. only then formalize the math

## Resource Thinking

The design mindset is strongly constraint-aware:

- hardware is limited
- disk and memory pressure are real
- efficiency matters as much as raw capability

This means system design should prefer:

- local-first workflows when possible
- small governed lanes over sprawling stacks
- structural defenses over expensive bolt-on products

## Dynamic Defense Intuition

Static defenses are predictable.

The preferred intuition is:

- oscillating or aperiodic barriers
- breathing walls instead of flat walls
- interference patterns instead of simple fixed gates

That design language maps well onto SCBE ideas like drift, phase coherence,
temporal legality, and geometry-based cost surfaces.

## What This Is Good For

This philosophy is especially useful when writing or explaining:

- SCBE security architecture
- governed routing systems
- browser/agent autonomy with safety constraints
- patent and research framing for geometry-native defense
