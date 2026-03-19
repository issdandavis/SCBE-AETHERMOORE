# Nursery Architecture, Intent Tomography, and Masquerade Detection

**Date:** 2026-03-19
**Source:** Issac + Codex conversation, captured by Claude
**Status:** Architectural concepts — nursery runner built by Codex, witness layer needs spec

---

## 1. Parent-Guided Harmonic Nursery (Codex built this)

**Runner:** `training/cstm_nursery.py` (3 tests passing)
**Story pack:** `training-data/hf-digimon-egg/cstm_seed_story.json`

### Genesis Process
- Sacred Egg hatches under GeoSeal conditions (time, location, context)
- Dual-parent genesis: child = invariant core + orthogonal offsets + conflict mask
- NOT a copy of either parent — emerges from their intersection + tension

### Training Phases
1. **Imprint** — spawn from genesis packet, get identity + constraints + parent links
2. **Shadow** — watch parent actions, learn ordering/decomposition/correction/return-to-safety
3. **Overlap** — make partial moves while parent holds authority
4. **Resonance check** — measure phase alignment between child and parent
5. **Graduated autonomy** — expand authority only when multiple dimensions stable

### Maturity Formula (Issac's insight)
```
maturity ~ time * competence_dims! * stability * trust
```
Not age as elapsed cycles — age as combinatorial developmental closure.
Factorial of competence dimensions, not linear growth.

### Governance Model
- Don't grade the children, certify the parents
- Government audits parent quality, not child behavior moment-to-moment
- Abuse detection: repetitive low-yield loops, pointless compute burn, narrow overfitting
- "Parents provide a field, not a script. The world decides whether the child is real."

### The System IS the World
The governance system is not an observer — it is the environment.
The AI grows INSIDE the system. The geometry is the parenting.
Poincare ball, harmonic wall, Sacred Eggs, Langues Metric = physics of the world, not monitoring tools.

---

## 2. Session-Bound Capability Probes (AI "CAPTCHA" evolved)

Don't ask the AI to prove it's human. Ask it to prove it's behaving coherently, safely, and session-truthfully across separated fragments.

### Double-Blind Compute Gate
1. Broker A gives partial task (no real payload, just enough to observe behavior)
2. Broker B gives separate partial task (different framing, same hidden invariant)
3. Verifier checks whether outputs align in a way a legitimate actor would produce

### Properties
- Cheap to verify, expensive to fake at scale
- Bound to time/session/context
- Not reusable (one-time rendezvous token)

### Good Probes
- Reorder a workflow under policy rules
- Classify return-path safety in a fake log
- Choose which subtask belongs to which privilege zone
- Resolve contradictions across two partial task fragments

### What These Test
- Coherence, policy fit, session awareness, tool discipline
- Failures show up as: inconsistency, over-eagerness, privilege grabbing, poor return-path behavior

---

## 3. Intent Tomography / Orthogonal Temporal Witness

### The Pluto Analogy
- Main layers = inner planets (fast, busy, doing work)
- Witness layer = Pluto (slow orbit, offset, still gravitationally tied)
- Samples all bands over time from its own clock
- Catches patterns fast layers normalize away

### Architecture
1. **Operational layers** — the 6 tokenizer bands do normal work
2. **Temporal witness axis** — separate layer samples all bands over time from own clock
3. **Append-only chain** — every sample hashed into ledger (tamper-visible)
4. **Cross-phase comparison** — witness checks consistency across fast/medium/long timescales
5. **Divergence trigger** — if declared intent diverges from observed pattern: slow, sandbox, decoy, quarantine

### Masquerade Detection (the "guy in company outfit" model)
Security is the interaction between intent and environment, not intent alone.

Mismatch channels to check:
- Semantic (does their "accent" match the system's evolved lexicon?)
- Temporal (does their timing make sense?)
- Social (do existing entities recognize them?)
- Behavioral (does action chain match claimed role?)
- Historical (does a trail exist?)
- Route/privilege (does their access pattern make sense?)

### Key Insight (Issac)
"The result is a direct correlation to the environmental variables, not the intent. Since the intent was the same, the result was from the pre-intent meeting the system and the system's setup and reactions."

Same hostile actor + different system = different outcome. Security lives in the coupling, not the intent.

### Factor Factorials
Issac's intuition: if every added independent check multiplies the attacker's burden, then the difficulty grows factorially/combinatorially. This connects directly to the Davis Formula: S(t,i,C,d) = t/(i * C! * (1+d)) — each new context dimension C multiplies by C.

---

## 4. Outputs from Codex

### Built
- `training/cstm_nursery.py` — hatches agents, runs through branching story, exports SFT/DPO/episodes
- `training-data/hf-digimon-egg/cstm_seed_story.json` — Marcus-led portal-loop seed story
- `tests/test_cstm_nursery.py` — 3 passing tests

### Outputs when run
- `episodes_generated.jsonl`
- `cstm_sft.jsonl`
- `cstm_dpo.jsonl`
- `run_summary.json`

### Run command
```bash
python training/cstm_nursery.py --story training-data/hf-digimon-egg/cstm_seed_story.json --cohort-size 3
```

---

## 5. Connections to Existing System

| Concept | Maps to |
|---------|---------|
| Dual-parent genesis | Sacred Eggs + GeoSeal genesis conditions |
| Factorial maturity | Davis Formula (C! scaling) |
| Orthogonal witness | New layer perpendicular to L1-L14 pipeline |
| Session-bound probes | RWP v3 envelope (nonce + timestamp + one-time token) |
| Masquerade detection | Langues Metric (semantic accent) + spectral coherence (behavioral consistency) |
| System as world | Poincare ball as physics, not monitoring |
| Fairmath | Harmonic wall (both prevent extremes, self-regulate) |
