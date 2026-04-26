# Layered Geometry Semantic Packing Note

Date: 2026-04-25

## Core Idea

Polygon packing suggests a useful semantic-token design pattern: a token can keep a stable outer shape while carrying a richer inner geometry that does not need to match the outer shape. The outside shape preserves the word's recognizable semantic boundary. The inside shape carries scale, role, modality, lineage, and harmonic links to other cells.

This makes the token act like a nested semantic container instead of a flat embedding. A word can remain the same word at the boundary while its interior geometry changes to reflect task context, coding role, governance state, or relation to neighboring tokens.

## Design Rule

Each token has two geometry layers:

1. Outer hull: stable semantic identity.
2. Inner packing: context-dependent latent structure.

The outer hull must remain invariant during transport and interpretation. The inner packing can rotate, subdivide, resonate, or re-pack as long as it does not violate the hull and does not collide with other required invariants.

## Non-Contact Nesting

Cells do not need to touch to be related. A natural octree can represent relationships by harmonic distance instead of physical contact:

- Same octave: sibling cells share scale and comparable role.
- Octave above: parent cell summarizes or governs child cells.
- Octave below: child cell specializes or operationalizes parent meaning.
- Non-touch harmonic link: cells remain separated but phase-aligned by ratio, resonance, or route.

This matters because semantic systems often break when everything is forced into direct adjacency. Meaning can be linked by scale, rhythm, phase, or route without collapsing the shapes together.

## Tokenizer Application

For the atomic tokenizer, use the periodic or Sacred Tongues label as the outer hull and a small packed inner geometry as the context layer.

Candidate fields:

- `outer_id`: stable token, element, concept, or code-primary label.
- `outer_hull_hash`: deterministic identity fingerprint.
- `inner_cells`: packed subfeatures such as syntax role, operation type, resource cost, modality, and lineage.
- `octave_level`: scale of the cell in the semantic tree.
- `phase_links`: non-contact relationships to other tokens.
- `collision_score`: whether packed meanings overlap illegally.
- `semantic_loss`: measured drift from the original label after packing and unpacking.

## Coding Model Application

Code tokens can keep their recognizable role while carrying inner structure:

- A function name keeps its outer hull as `CALLABLE`.
- Its inner cells encode language, side effects, argument shape, resource profile, test coverage, and failure mode.
- Two functions do not need to touch in sequence to be related; they can be linked by call graph, dataflow, or shared invariant.
- The model can learn routeable structure without forcing every relationship into the next-token surface order.

## Experiment

Build a small benchmark around code identifiers and short functions:

1. Encode each token as an outer hull plus inner packed cells.
2. Decode back to the original token class and context role.
3. Compare against a flat feature vector baseline.
4. Score semantic recovery, context recovery, and collision rate.
5. Run label-shuffle null control before calling any lift real.

Success criteria:

- Outer hull recovery stays at or above the existing tokenizer baseline.
- Inner context recovery beats the flat baseline.
- Collision rate remains bounded as token count grows.
- Shuffle-null performance collapses toward chance.

## Boundary

This is not a claim that geometry is semantics by itself. Geometry is the routing and compression scaffold. The result only counts if it improves held-out recovery, lowers collision, or improves downstream coding-task behavior under a pre-registered eval.

