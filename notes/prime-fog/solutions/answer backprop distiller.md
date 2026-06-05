---
tags: [solution, diagnostic, calibration-only]
---

# answer backprop distiller

**Type:** diagnostic / lane attribution tool
**Scope:** calibration only — uses known anchor truth, not valid during flight

## What it does

Given the known anchor set for a ring, reverse-attributes which sensor lane (frozen, centroid, lambda, graph, CMPSSZ) scored each anchor highest in the top-20. Tells you which controller "owned" each anchor.

## Results

Confirms lane winners:
- [[frozen gate]] owns most of its 11 B-anchors
- [[centroid_a]] owns its 3–5 new B-anchors that frozen misses
- [[lambda shadow]] owns its 10 B-anchors (zero overlap with frozen)

## Key limitation

The quota selector (how you pick 20 rows from multiple ranked lists) introduces competition. When the distiller tries to build a net-positive ensemble selector, it loses frozen hits because the quota fills with lambda rows that displaced frozen's picks. Making 20 slots serve 3+ independent lanes simultaneously is the unsolved problem.

## What it does NOT do

Does not generalize across boards. It is a postmortem instrument. Running it on C to find a C-optimal selector would be in-sample overfitting.

## Related

- [[frozen gate]] — primary contributor diagnosed
- [[centroid_a]] — secondary contributor
- [[lambda shadow]], [[CMPSSZ]], [[graph map]] — scout contributors
