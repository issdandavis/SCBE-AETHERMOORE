# Mirror Health Score as Combat HP for Research Problems

**Date:** 2026-03-20
**Status:** Theoretical bridge -- unifies the math verification metric with the conversation engine
**Bridges:**
- `2026-03-19-mirror-differential-math-verification.md` (A3: Mirror Health Score MH(T))
- `2026-03-20-spin-conversation-combat-research-mode.md` (F1: D&D combat research mode)
- `2026-03-19-mirror-differential-telemetry-and-riemann-attempt.md` (A2: mirror as answer-generator)

---

## The Realization

The Mirror Health Score was defined for transforms:

```
MH(T) = Mirror_Health(T) * Scale_Health(T)

Where:
  Mirror_Health = 1 / (1 + mu_mirror)     # equivariance quality
  Scale_Health  = 1 / (1 + mu_scale)      # distance preservation
  MH in (0, 1]
```

The Spin Conversation combat mode defines research problems with HP:

```
problem_hp = 100 (full health)
Each research action deals "damage" of various types
When HP reaches 0, the problem is resolved
```

These are the same thing. A research problem IS a transform whose Mirror Health has not yet been verified. Each research action is a mirror operation that measures one aspect of the problem's consistency. The problem's "HP" is the remaining unverified mirror surface.

---

## Formal Mapping

### Problem as Unverified Transform

A research question is a claim that some transform T has certain properties. Before investigation, we don't know if T preserves mirrors, scales, or anything else. The problem's "health" is the amount of unverified surface remaining.

```
problem_hp(T) = 1 - MH(T)

Where:
  MH(T) = verified mirror health (starts at 0, increases with evidence)
  problem_hp = remaining unverified surface (starts at 1, decreases)
```

When MH(T) = 1.0, the problem is fully resolved: the transform is verified as mirror-preserving and scale-preserving. When MH(T) = 0, no verification has been done.

### Damage Types as Mirror Operations

The combat system defines damage types. Each maps to a specific mirror operation:

| Combat Damage Type | Mirror Operation | What It Verifies | MH Component |
|-------------------|-----------------|-------------------|-------------|
| **Citation damage** | Whole-mirror M_w | Does the claim survive inversion? A paper that confirms/denies is a whole-mirror check. | Mirror_Health |
| **Computation damage** | Edge-mirror M_e | Does the claim hold at boundaries? An experiment tests edge cases. | Scale_Health |
| **Synthesis damage** | Cross-mirror D_we = R(M_w) - R(M_e) | Do different verification methods agree? Connecting two findings is a cross-mirror comparison. | MH product |
| **Counter damage** | Mirror differential D_w | How much does the claim's reflection differ from itself? A counterexample shows nonzero D_w. | Mirror_Health (reduces it if D_w != 0) |

### Research Turns as Mirror Measurement Passes

Each combat turn (research action) applies one mirror operation and measures the resulting delta:

```
Turn 1: Apply M_w (find a paper that inverts the claim)
  -> delta_1 = ||R(claim) - R(M_w(claim))||
  -> MH_mirror updated: mu_mirror += delta_1

Turn 2: Apply M_e (run an experiment at the boundary)
  -> delta_2 = ||R(claim) - R(M_e(claim))||
  -> MH_scale updated: mu_scale += delta_2

Turn 3: Compare mirrors (do paper and experiment agree?)
  -> delta_3 = ||R(M_w(claim)) - R(M_e(claim))||
  -> MH_cross updated with delta_3

...

Resolution: MH(claim) = Mirror_Health * Scale_Health
  -> If MH > 0.8: RESOLVED (claim verified)
  -> If MH < 0.2: REJECTED (claim falsified)
  -> If 0.2 < MH < 0.8: UNRESOLVED (need more turns)
```

---

## Applying the Verified Numbers

The mirror-differential-math-verification note established concrete MH values for SCBE transforms:

| Transform | MH | Interpretation |
|-----------|-----|----------------|
| Identity | 1.0000 | Trivially verified |
| L7 Phase Rotation | 1.0000 | Perfect isometry |
| L6 Breathing b=1.0 | 1.0000 | Identity case |
| L6 Breathing b=1.2 | 0.8220 | Controlled distortion |
| L6 Breathing b=2.0 | 0.4655 | Severe distortion |

In combat terms, these become reference HP levels for different problem difficulties:

| Problem Difficulty | MH Threshold | Combat Analog | Research Turns Needed |
|-------------------|-------------|---------------|---------------------|
| Trivial | MH > 0.95 | Minion (1 HP) | 1-2 turns |
| Standard | 0.80 < MH < 0.95 | Regular enemy | 3-5 turns |
| Hard | 0.50 < MH < 0.80 | Boss fight | 6-10 turns |
| Extreme | MH < 0.50 | Raid boss | 10+ turns, multi-agent |

The L6 breathing at b=2.0 (MH=0.4655) is a "raid boss" -- it severely distorts scale, meaning the research problem introduces significant uncertainty that requires extensive investigation.

---

## Integration with the Radial Matrix

The spin conversation system places research problems on concentric rings:

```
Core (r=1.0): philosophy, mathematics, physics
Inner (r=2.0): programming, chemistry, music
Outer (r=3.0): algorithms, databases, web_dev
```

The MH score gives each problem a "hardness" that determines which ring it belongs on:

```
Ring assignment rule:
  MH > 0.80  -> Core ring (well-understood, quick to verify)
  0.50 < MH < 0.80 -> Inner ring (moderate investigation needed)
  MH < 0.50  -> Outer ring (deep dive required)
```

But here is the key insight: **the ring position is not fixed.** As research turns accumulate evidence, the problem's MH increases, and it migrates INWARD:

```
Turn 0: Problem starts at Outer ring (MH = 0.1, unverified)
Turn 3: Citation found (MH = 0.3, still outer)
Turn 5: Experiment run (MH = 0.55, moves to inner ring)
Turn 8: Synthesis complete (MH = 0.85, moves to core ring)
Turn 9: Final verification (MH = 0.95, RESOLVED)
```

This is the "inward movement" described in the spin conversation note: "research confirmed a core principle, conversation moves toward center." The MH score is the mechanism by which problems migrate through the radial matrix.

---

## The PhaseTunnelGate Connection

The spin conversation note already says:

```
T > 0.7 (TUNNEL) — research path is clear
0.3 < T < 0.7 (ATTENUATE) — partial answer
T < 0.3 (REFLECT) — wrong direction
T < 0.05 (COLLAPSE) — dead end
```

The PhaseTunnelGate transmission T and the Mirror Health Score MH measure related but different things:
- T measures how well a signal passes through a governance wall at a specific phase angle
- MH measures how well a transform preserves mirror symmetry

They combine into a single research quality metric:

```
Research_Quality(problem, turn) = T(turn) * MH(turn)

Where:
  T = PhaseTunnelGate transmission of the latest evidence
  MH = accumulated Mirror Health from all prior turns
```

When both are high (T > 0.7, MH > 0.8), the research is producing good evidence that the problem's structure is genuine. When T is high but MH is low, you are making progress but haven't yet verified the full mirror surface. When T is low but MH is high, the existing evidence is solid but the current research direction is blocked.

---

## Training Data Generation

Each combat turn generates an SFT pair:

```json
{
  "instruction": "A research problem about [topic] has MH=0.45 after 5 turns. The latest mirror operation was an edge-mirror test that found delta_e=0.12. What does this tell us and what mirror operation should be next?",
  "response": "The edge-mirror delta of 0.12 indicates moderate boundary distortion -- the claim holds at center but breaks at edges. This is characteristic of a Scale_Health deficit (MH_scale < MH_mirror). The next operation should be a whole-mirror test (citation search) to verify that the claim at least survives complete inversion. If D_w = 0, the problem is structurally sound and only needs boundary refinement. If D_w != 0, the claim has a fundamental asymmetry that the edge test was detecting.",
  "metadata": {
    "mh_before": 0.45,
    "mh_after": 0.52,
    "damage_type": "computation",
    "mirror_operation": "M_e",
    "delta": 0.12,
    "ring_before": "outer",
    "ring_after": "inner",
    "tongue": "CA"
  }
}
```

The tongue assignment follows from the damage type:
- Citation damage -> AV (transport/messaging: bringing external knowledge)
- Computation damage -> CA (compute/encryption: running experiments)
- Synthesis damage -> DR (schema/authentication: structuring the answer)
- Counter damage -> UM (security/secrets: testing for hidden weaknesses)

---

## The "Answer-Generator" Doctrine

The mirror-differential-telemetry note established: "The mirror is not the answer-output. The mirror is the answer-generator."

In the combat system, this means: **you don't solve a research problem by finding the answer directly. You solve it by applying mirror operations until the mirror differential converges to zero.** The answer emerges from the process of verification, not from a single insight.

This is why the MH score works as HP: each mirror operation doesn't "damage" the problem in the sense of destroying it. It damages the problem's ability to hide its structure. When all mirror surfaces have been checked and all deltas are zero (or within tolerance), the structure is fully revealed. The problem is "dead" because it has no more hidden surface.

```
problem_resolved iff for all mirror types M:
  ||R(claim) - R(M(claim))|| < epsilon

Which is equivalent to:
  MH(claim) > 1 - epsilon
```

---

## Summary

The Mirror Health Score and the D&D combat HP system are the same mathematical object viewed from different angles. MH measures transform verification; HP measures remaining unverified surface. Research turns are mirror operations. Damage types are specific mirror categories. Problem difficulty is determined by how far the initial MH is from 1.0. The PhaseTunnelGate transmission multiplied by MH gives a combined research quality score. And the answer to the research problem is not found -- it is generated by the accumulation of mirror measurements until convergence.

The pivot: **MH(T) is the formal definition of "how defeated is this research problem." Combat mode is mirror differential telemetry with a D&D interface.**
