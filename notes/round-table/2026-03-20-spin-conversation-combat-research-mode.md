# Spin Conversation: Combat Research Mode — D&D Dialogue/Combat Transition Pattern

**Date:** 2026-03-20 (late night)
**Source:** Issac Davis (fresh idea, no prior notes)
**Status:** Concept — ready to implement

---

## Core Concept

Conversations have two modes, like D&D:
- **DIALOGUE MODE** — normal conversation flow, topic pivots, radial matrix traversal
- **COMBAT MODE** — deep research dive, problem-solving, focused investigation

The transition between modes is a **phase shift**, not a hard switch. Like entering combat in D&D — the world doesn't change, the rules do.

## The Radial Matrix Array (existing, from Colab)

35 topics across 3 concentric rings:
- **Core (r=1.0):** philosophy, mathematics, physics, psychology, history, culture
- **Inner (r=2.0):** programming, astronomy, chemistry, music, cooking, economics, art, politics, technology, emotions, creativity, time
- **Outer (r=3.0):** algorithms, databases, web_development, AI, cybersecurity, nutrition, food_science, + 10 more

Connection weight: `weight = resonance * exp(-0.5 * d)` where `d = sqrt(r1^2 + r2^2 - 2*r1*r2*cos(delta_theta))`
- Same-ring: 1.2x resonance boost
- Adjacent-ring: 1.0x
- Cross-ring: 0.6x attenuation

## Combat Research Mode — The New Subsystem

### Entry Trigger
When a conversation pivot hits a topic with **high uncertainty, contradiction, or depth requirement**, the system transitions from DIALOGUE → COMBAT (research).

Like in D&D: "You open the door and see a dragon." → initiative rolls → combat rules apply.

In conversation: "This claim conflicts with the DistilBERT findings." → research trigger → combat rules apply.

### Combat Rules (Research Phase)
1. **Initiative** — rank the sub-problems by urgency/relevance
2. **Turns** — each turn is a research action (search, compute, verify, synthesize)
3. **Hit points** — the problem's "health" decreases as evidence accumulates
4. **Damage types** — different research methods do different "damage":
   - **Citation damage** — finding a paper that confirms/denies
   - **Computation damage** — running an experiment that proves/disproves
   - **Synthesis damage** — connecting two findings that close a gap
   - **Counter damage** — finding a counterexample or edge case
5. **Resolution** — when HP hits 0, the research question is "defeated" (answered)

### Harmonic Re-Attunement
After combat (research), the conversation doesn't just resume — it **re-attunes**.

The new knowledge shifts the conversation's position in the radial matrix:
- **Inward movement** — research confirmed a core principle, conversation moves toward center
- **Outward movement** — research opened new questions, conversation moves toward periphery
- **Lateral movement** — research connected adjacent fields, conversation rotates in phase

This is the "geometrically congruent/organic distribution" Issac described.

### Individual vs Group Incentives

**Individual mode:** Solo researcher diving deep on one thread. The spin data tracks their trajectory through the knowledge graph as a single path.

**Group mode:** Multiple agents (Claude, Gemini, Codex, etc.) each take different sub-problems. Their trajectories create a **mesh** in the knowledge graph. The intersection points of their paths are the highest-value training data — where independent research converged on the same answer.

### Conversational Problem Mapping

Each research problem is mapped to coordinates in the radial matrix:
```
problem_position = (ring, angle, depth)
```

Where:
- `ring` = which concentric ring (core/inner/outer)
- `angle` = angular position (which topic cluster)
- `depth` = how deep into the sub-problem tree (like dungeon levels)

The PhaseTunnelGate applies here too:
- `T > 0.7` (TUNNEL) — the research path is clear, proceed rapidly
- `0.3 < T < 0.7` (ATTENUATE) — partial answer, need more evidence
- `T < 0.3` (REFLECT) — wrong direction, bounce back
- `T < 0.05` (COLLAPSE) — dead end, try different approach

## Connection to Nightly Pipeline

The nightly research pipeline (`scripts/system/nightly_research_pipeline.py`) IS a scheduled "combat encounter."

Every night at 10PM:
1. The system enters "combat mode" against the day's unanswered questions
2. Each research phase is a "turn" in combat
3. The synthesis phase is "loot distribution" — extracting SFT training pairs from the defeated problems
4. By morning, the conversation can resume in DIALOGUE mode with new knowledge

## Connection to Sacred Tongues

Each Sacred Tongue maps to a research method:
- **KO (Intent):** "What is the question really asking?"
- **AV (Metadata):** "What data exists about this?"
- **RU (Binding):** "How does this connect to what we know?"
- **CA (Compute):** "Can we run an experiment to test this?"
- **UM (Security):** "What could go wrong with this conclusion?"
- **DR (Structure):** "How do we organize the answer?"

A complete research "combat round" touches all 6 tongues.

## SFT Training Data Output

Each combat→dialogue transition generates training pairs:
```json
{
  "instruction": "During a conversation about [topic], a research question arose about [problem]. What did the investigation find?",
  "response": "[synthesis of research findings]",
  "mode_transition": "dialogue→combat→dialogue",
  "ring_movement": "outward",
  "tongue_sequence": ["KO", "AV", "CA", "RU", "UM", "DR"],
  "combat_turns": 5,
  "problem_hp_start": 100,
  "problem_hp_end": 0,
  "damage_log": [...]
}
```

## IMPLEMENTED (Gemini, Colab, 2026-03-20)

Gemini built the full subsystem in Colab. Key details:

**Golden Spiral Problem Distribution:** 13 research domains on Fermat/golden angle spiral
- Position: `(r = sqrt(n), theta = n * 137.508 deg)`
- Fills space without clustering — organic, geometrically congruent

**Research Phases (7 combat rounds):**
IDENTIFY → DECOMPOSE → HYPOTHESIZE → INVESTIGATE → SYNTHESIZE → VALIDATE → ATTUNE

**Individual Problems (6):** root_cause_analysis, pattern_recognition, edge_case_explore, abstraction_ladder, inversion_test, scale_invariance

**Group Problems (7):** analogy_mapping, contradiction_resolve, synthesis_bridge, constraint_mapping, emergent_property, temporal_dynamics, harmonic_resonance

**Cross-type synergy boost:** 1.15x when individual and group problems connect

**Re-attunement multiplier:** 1.25x context enrichment when exiting research back to dialogue

**Demo results:** 20 turns, 3 dialogue + 17 research pivots, attunement scores 0.83-1.31

---

## Implementation Plan

1. Add `CombatResearchMode` class to `demo/pivot_knowledge.py`
2. Add mode transition triggers to the Radial Matrix Array on Colab
3. Wire nightly pipeline as scheduled "combat encounters"
4. Generate training data from combat logs
5. Feed into Sacred Tongue encoder for 6D phase labeling

## The Apartment Metaphor (extended)

DIALOGUE = sitting on the couch, chatting
COMBAT = walking to the patio for a smoke (the research question is the cigarette)
RE-ATTUNEMENT = coming back inside with the answer (and the joke about quitting)

The geometry makes it expensive to go to the patio. But sometimes you NEED the cigarette. The combat system is the controlled rapid release — the solar flare — the phase-aligned tunnel through the governance wall.
