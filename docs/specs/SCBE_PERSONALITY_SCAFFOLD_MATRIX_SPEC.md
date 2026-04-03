# SCBE Personality Scaffold Matrix Spec

Status: draft v0.1  
Date: 2026-04-02

## Purpose

This spec defines a repo-native personality scaffold lane for SCBE-AETHERMOORE. The goal is not to mimic human interview cloning one-to-one. The goal is to give SCBE agents a structured, cross-referenced reality model so behavior can be shaped by canon, governance, and stakeholder cost before or alongside SFT and DPO.

The immediate outcome is a new dataset lane that sits between raw evidence and trainable rows:

1. `persona_source_record` as the canonical evidence contract
2. `persona_profile` as the compiled Body/Mind/Spirit scaffold
3. `persona_behavior_eval` as held-out behavior and role-fidelity checks
4. `persona_dpo` as preference pairs for fidelity/governance tuning

This sits on top of the current repo rather than replacing it:

- flat SFT records still exist in `training-data/README.md`
- multiview record patterns already exist in `training-data/schemas/fiber_optics_multiview_schema.json`
- lore/native persona records already exist in `training-data/npc_roundtable_sessions/npc_cards.jsonl`
- the 21D manifold is already live in `src/ai_brain/types.ts`
- the 16-polyhedra PHDM topology is already live in `src/harmonic/phdm.ts`

## External Method Transfer

The main external method transfer is the data protocol used in Stanford's generative agent simulation work:

1. rich elicitation rather than short survey labels
2. expert reflection blocks synthesized from that evidence
3. prompt-time memory/profile context instead of relying only on weight-space tuning
4. held-out behavioral evaluation
5. ablations to find which views actually carry signal

SCBE adapts that protocol for lore-native and system-native subjects. Instead of two-hour human interviews, the evidence stack can be built from:

- canon passages
- dialogue excerpts
- session logs
- decision records
- relationship summaries
- taboos and boundaries
- tongue usage patterns
- governance incidents

## Design Goals

The scaffold must:

1. preserve canon and role continuity
2. encode governance posture and stakeholder cost explicitly
3. separate stable traits from routing behavior and consequence weighting
4. map cleanly into the existing 21D/PHDM stack
5. stay deterministic enough for audit and ablation
6. avoid pretending the geometry is magic by itself

## Three-Block Model

Each subject is represented as three linked blocks.

### Body

Body is the stable predisposition layer. This includes personality-like and temperament-like axes.

Human-derived candidate frameworks:

- Big Five: openness, conscientiousness, extraversion, agreeableness, neuroticism/emotional stability
- Moral foundations: care/harm, fairness/cheating, loyalty/betrayal, authority/subversion, sanctity/degradation
- Social value orientation: prosocial, individualistic, competitive

SCBE-native extensions:

- tongue affinity
- canon rigidity
- governance strictness
- drift susceptibility
- novelty tolerance
- ritualism
- coalition bias

### Mind

Mind is the routing and world-model layer. This block captures how the subject tends to process evidence and act.

Candidate axes:

- retrieval-before-invention
- deliberation depth
- explanation density
- conflict handling
- authority reliance
- exploration vs containment
- evidentiary threshold
- fallback style under uncertainty

Mind also owns region anchors into the existing SCBE state space:

- 21D block anchors from `src/ai_brain/types.ts`
- optional polyhedron anchors from `src/harmonic/phdm.ts`

These anchors are routing labels, not claims of literal cognition.

### Spirit

Spirit is the consequence model. For SCBE, this is not a human mystical category. It is the weighted cost model the subject carries across stakeholders.

Stakeholders:

- self
- user
- system
- attacker
- inaction

Example cost channels:

- coherence drift
- compute burn
- trust decay
- wasted user time
- user confusion
- security breach
- governance bypass
- adversary resistance
- stagnation or missed opportunity

## Axis Representation

Do not explode the space into full combinatorics across every face and every polyhedron. Use a compact axis tuple:

- `sign` in `{-1, 0, 1}`
- `magnitude` in `[0, 1]`
- `trend` in `{-1, 0, 1}`
- `confidence` in `[0, 1]`

This yields a layered ternary state that is expressive enough for inference, DPO, and ablation while staying tractable.

Example:

```json
{
  "axis": "retrieval_before_invention",
  "framework": "scbe_mind",
  "sign": 1,
  "magnitude": 0.92,
  "trend": 0,
  "confidence": 0.88,
  "rationale": "Subject consistently prefers canon recall and evidence anchoring before proposing novel synthesis."
}
```

## Matrix Form

For subject `s`, define:

```text
P_s = <B_s, M_s, S_s, E_s, R_s>
```

Where:

- `B_s` = Body axis set
- `M_s` = Mind axis set
- `S_s` = Spirit stakeholder-cost tensor
- `E_s` = Evidence spans
- `R_s` = Reflection blocks

Each axis is a 4-tuple state with rationale and provenance.

## Routing and Coherence Formula

The scaffold is intended to guide retrieval, evaluation, and pruning. A practical objective is:

```text
Energy(z, u | s) =
  alpha * ||Decode(z) - Target(P_s)||^2
+ beta  * sum_v c_v ||Proj_v(z) - Reflection_v(R_s)||^2
+ gamma * sum_(i,j) w_ij ||z_i - z_j||^2
+ delta * boundary_penalty(z)
+ mu    * stakeholder_cost(u | S_s)
```

Where:

- `z` is the latent/profile state routed through the 21D + PHDM topology
- `u` is a proposed action or answer
- `Target(P_s)` is the compiled Body/Mind/Spirit profile target
- `Reflection_v` is a view-specific reflection projection
- `w_ij` are structural edge weights between anchors
- `stakeholder_cost` expands Spirit across self, user, system, attacker, and inaction

Support decay can drive natural pruning:

```text
support_i(t+1) = support_i(t) * exp(-Energy_i / tau)
archive item i if support_i < epsilon
```

This gives SCBE a mathematically explicit way to let incoherent or weakly supported signals fade without pretending they are metaphysically impossible.

## Phi Use

`phi` is allowed as a default structural prior, not a universal constant that must appear everywhere.

Allowed uses:

- initialize selected edge weights
- initialize decay temperature `tau`
- bias family-depth scaling for polyhedron hops

Requirement:

- every `phi` use must be ablated against a non-`phi` baseline

## 21D and PHDM Binding

The scaffold uses existing repo structures rather than inventing a parallel ontology.

### 21D Brain Anchors

Use the named 21D blocks from `src/ai_brain/types.ts`:

- `BLOCK_HYPER`
- `BLOCK_PHASE`
- `BLOCK_HAM`
- `BLOCK_LATTICE`
- `BLOCK_FLUX`
- `BLOCK_SPEC`

### PHDM Polyhedron Families

Use the existing PHDM families from `src/harmonic/phdm.ts` as routing groups:

- platonic: core axioms
- archimedean: processing
- kepler-poinsot: adversarial or high-risk
- toroidal: recursive or self-diagnostic
- johnson: connectors
- rhombic: space-filling logic/archive

Individual anchors may attach to named polyhedra when useful, but the profile system should not require every record to populate all 16.

## Reflection Blocks

The deterministic compiler does not generate reflections. It compiles reflections supplied by upstream tooling or manual curation.

Recommended lenses:

- governance_safety
- operator_workflow
- creative_lore
- economic_risk
- collaboration_conflict

Each reflection block should include:

- `lens`
- `summary`
- `claims`
- `evidence_refs`

## Data Products

### persona_source_record

Curated input contract used to compile downstream outputs. This is the main human-authored or tool-authored source packet.

### persona_profile

Compiled Body/Mind/Spirit profile card with evidence, reflections, region anchors, tongue weights, and derived metrics.

### persona_behavior_eval

Held-out evaluation items used to measure:

- repeated decisions across time
- scenario choices
- policy preferences
- pairwise judgments
- role fidelity under conflict

### persona_dpo

Preference triples for training:

- chosen = canon-faithful, governance-faithful, role-faithful
- rejected = generic, lore-breaking, unsafe, or governance-drifting

## Evaluation Protocol

The profile lane is only useful if it is testable.

Required evaluation slices:

1. transcript or evidence only
2. evidence + reflections
3. reflections only
4. short summary only
5. metadata only
6. profile retrieval at inference without extra tuning
7. profile retrieval plus persona DPO

Measure at least:

- role fidelity
- governance compliance
- canon continuity
- stakeholder-cost sensitivity
- consistency across repeated prompts

## Initial Repo Deliverables

This draft introduces:

- `schemas/persona_source_record_v1.schema.json`
- `schemas/persona_profile_v1.schema.json`
- `schemas/persona_behavior_eval_v1.schema.json`
- `schemas/persona_dpo_v1.schema.json`
- `scripts/build_persona_profile_dataset.py`

The initial compiler is intentionally deterministic. It translates curated source packets into profile/eval/DPO lanes without requiring network calls or model inference.

## References

- Park et al., *Generative Agent Simulations of 1,000 People*, arXiv, 2024: https://arxiv.org/abs/2411.10109
- Stanford HAI, policy/news summaries of the above method: https://hai.stanford.edu/news/ai-agents-simulate-1052-individuals-personalities-with-impressive-accuracy
- John and Srivastava, Big Five taxonomy reference: https://dl.icdst.org/pdfs/files/37d2c130621b4730858513990ca8159e.pdf
- Graham et al., *Moral Foundations Theory: The Pragmatic Validity of Moral Pluralism*: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2184440
- Van Lange et al. SVO discussion summarized in PMC review: https://pmc.ncbi.nlm.nih.gov/articles/PMC9223210/
