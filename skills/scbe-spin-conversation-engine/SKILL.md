---
name: scbe-spin-conversation-engine
description: Generate SFT training data via radial matrix conversation pivots with D&D-style combat research mode. Produces diverse, cost-effective training pairs with Sacred Tongue encoding, golden spiral problem distribution, and harmonic re-attunement.
---

# SCBE Spin Conversation Engine

Generate high-quality SFT training data through conversation simulation with radial matrix topic pivoting and combat research mode.

## When to Use

- User says "generate training data", "spin conversations", "run the conversation engine"
- When producing SFT/DPO pairs from simulated dialogues
- When testing Sacred Tongue encoding on conversation flows
- When running the nightly research pipeline's synthesis phase
- When building diverse, topically-connected training corpora

## Architecture

### Radial Matrix Array

35 topics across 3 concentric rings in polar coordinates:

| Ring | Radius | Count | Topics |
|------|--------|-------|--------|
| Core | r=1.0 | 6 | philosophy, mathematics, physics, psychology, history, culture |
| Inner | r=2.0 | 12 | programming, astronomy, chemistry, music, cooking, economics, art, politics, technology, emotions, creativity, time |
| Outer | r=3.0 | 17 | algorithms, databases, web_development, AI, cybersecurity, nutrition, food_science, + 10 more |

**Connection weight formula:**
```
weight = resonance * exp(-0.5 * d)
d = sqrt(r1^2 + r2^2 - 2*r1*r2*cos(delta_theta))
```

- Same-ring: 1.2x resonance boost
- Adjacent-ring: 1.0x
- Cross-ring: 0.6x attenuation

### Two Modes (D&D Pattern)

**DIALOG MODE** — Normal conversation flow through the radial matrix
- 70% pivot probability per turn
- 15 turns single / 20 turns batch
- Spiral movement tracked as OUTWARD, INWARD, LATERAL

**RESEARCH MODE (Combat)** — Deep problem-solving encounter
- Triggered by topic complexity, contradiction, or depth requirement
- 7 phases per encounter: IDENTIFY → DECOMPOSE → HYPOTHESIZE → INVESTIGATE → SYNTHESIZE → VALIDATE → ATTUNE
- Exits back to DIALOG with enriched context

### Golden Spiral Problem Distribution (Fermat)

13 research problem domains on golden angle spiral:
```
position(n) = (r = sqrt(n), theta = n * 137.508 deg)
```

**Individual problems (6):** root_cause_analysis, pattern_recognition, edge_case_explore, abstraction_ladder, inversion_test, scale_invariance

**Group problems (7):** analogy_mapping, contradiction_resolve, synthesis_bridge, constraint_mapping, emergent_property, temporal_dynamics, harmonic_resonance

**Cross-type synergy:** 1.15x boost when individual and group problems connect

### Harmonic Re-attunement

On exit from RESEARCH → DIALOG: **1.25x context enrichment multiplier** applied. Research gains carry back into conversation, deepening harmonic quality.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pivot_probability` | 0.70 | Chance of topic pivot per turn |
| `single_turns` | 15 | Turns per single conversation |
| `batch_turns` | 20 | Turns per batch conversation |
| `batch_size` | 50 | Conversations per batch |
| `research_phases` | 7 | Phases per combat research encounter |
| `synergy_boost` | 1.15 | Cross-type problem synergy multiplier |
| `enrichment_multiplier` | 1.25 | Context boost on research exit |

## Sacred Tongue Encoding

Each topic and research problem maps to a Sacred Tongue affinity:
- **KO** (Intent) — "What is the question really asking?"
- **AV** (Metadata) — "What data exists about this?"
- **RU** (Binding) — "How does this connect to what we know?"
- **CA** (Compute) — "Can we run an experiment to test this?"
- **UM** (Security) — "What could go wrong with this conclusion?"
- **DR** (Structure) — "How do we organize the answer?"

## Output Format

```json
{
  "instruction": "Conversation about [topic] with [N] pivots",
  "response": "[generated dialogue with research interludes]",
  "mode_transitions": ["dialog", "research", "dialog"],
  "ring_movements": ["outward", "lateral", "inward"],
  "tongue_sequence": ["KO", "AV", "CA", "RU", "UM", "DR"],
  "attunement_score": 1.15,
  "research_encounters": 3,
  "total_turns": 20
}
```

## Usage

### From Colab (primary)
The Radial Matrix Array and Combat Research subsystem live in the Colab notebook:
`https://colab.research.google.com/gist/issdandavis/dcf0260083f8570815e33e0262e7a4c7/spiralverse-protocol-ai-training-data-generator.ipynb`

### From local
```bash
# Pivot Knowledge NPC dialogue system
python demo/pivot_knowledge.py

# Nightly research pipeline (scheduled combat encounters)
python scripts/system/nightly_research_pipeline.py --dry-run
python scripts/system/nightly_research_pipeline.py --phase synthesis
```

### From Claude Code
Ask: "generate 50 spin conversations about AI safety" or "run combat research on the PhaseTunnelGate findings"

## Cost Analysis

- **Human labeling:** ~$2/turn
- **Spin engine:** ~$0.0004/turn (5000x cheaper)
- **50 batch x 20 turns = 1,000 examples in <1 second**
- **Cryptographic verification built in for data integrity**

## Connection to Other Systems

| System | Connection |
|--------|-----------|
| PhaseTunnelGate | Research combat uses T coefficient for path selection |
| Davis Formula | Factorial context scaling applies to research depth |
| Sacred Tongues | 6D encoding on every training pair |
| Nightly Pipeline | Scheduled combat encounters against daily unknowns |
| Obsidian Vault | Research findings written to round-table notes |
| HuggingFace | Training data pushed to issdandavis/scbe-aethermoore-training-data |

## Research Notes

- Concept: `notes/round-table/2026-03-20-spin-conversation-combat-research-mode.md`
- Implementation: Colab notebook (Gemini-built cells)
- Existing dialogue system: `demo/pivot_knowledge.py`
