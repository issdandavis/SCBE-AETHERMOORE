# 12 — Parallel-Universes Experiment (the Crusader Kings analogy)

**Analogy:** In *Crusader Kings*, the game speed setting changes how much real time
the AI gets between events, so the same world plays out differently at different
speeds. In our system, the game-speed variable maps to **latency** and
**reconciliation cadence**.

## Design
- Two instances share the **same seed, the same venues and the same starting
  liquidity**.
- Instance **F** (fast) runs at real-time cadence.
- Instance **S** (slow) runs on a compressed or stretched clock, and **deliberately
  skips sync ticks** to simulate a venue going dark.
- At each sync point, **diff the decision logs**. Both are hash-chained, so the diff
  is tamper-evident.

## Question it answers
Does the topology field's value come from its **geometry** (the map's structure) or
just from **fresher data**?
- If S, working on stale data but with the same geometry, matches F's decisions, then
  the geometry is carrying the value.
- If S diverges in proportion to how stale its data is, then freshness is doing the
  work and the geometry is decoration.

## Metrics
- Decision agreement rate per sync window.
- PnL divergence, normalized by staleness.
- Break counts by type (07) in each instance.
