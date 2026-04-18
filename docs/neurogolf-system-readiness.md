# NeuroGolf System Readiness

This document maps the existing SCBE-AETHERMOORE codebase to the Kaggle
`neurogolf-2026` competition target:

- static-shape ONNX only
- no dynamic loops in the final graph
- tiny parameter / memory / MAC cost
- one network per ARC task

It is not a high-level manifesto. It is a concrete readiness map.

## Confirmed Reusable Components

### 1. Bijective tokenizer exists

File:
- `src/crypto/sacred_tongues.py`
- `src/tokenizer/sacred_tongues_hf.py`

What is confirmed:
- `SacredTongueTokenizer` is deterministic and bijective.
- Each tongue has a `16 x 16 = 256` token table.
- The implementation already supports exact `byte -> token` and `token -> byte`
  round-trips.
- The HF wrapper proves the tokenizer is already treated as a fixed-ID
  computation layer, not just lore.

Why it matters for NeuroGolf:
- ARC colors, local shape classes, component labels, or structural tags can be
  encoded into a compact reversible alphabet.
- The tokenizer should be used as a deterministic structural codebook, not as
  NLP tokenization.

### 2. GeoSeal exists

File:
- `src/geoseal.py`
- `src/crypto/geo_seal.py`

What is confirmed:
- Poincare-ball projection exists.
- Hyperbolic distance exists.
- Phase deviation / anomaly scoring exists.
- Trust / suspicion / quarantine logic exists.
- Fixed-dimensional context vectors exist.

Why it matters for NeuroGolf:
- GeoSeal is usable as a projection and pruning discipline.
- It is not the final runtime graph. It is a search-space reducer and cost-aware
  filter for candidate structural codes and transforms.

### 3. Compiler seed exists

File:
- `src/symphonic/multipath/fnir.py`
- `src/code_prism/parser.py`
- `src/code_prism/builder.py`
- `src/code_prism/emitter.py`

What is confirmed:
- The repo already has IR-oriented code.
- `FnIR` and Prism IR prove the stack already thinks in compiler terms.
- Current emitters target source code, not ONNX.

Why it matters for NeuroGolf:
- The missing step is an ONNX backend and a restricted static sub-IR.
- This is a compiler problem, not a syntax-training problem.

### 4. Fixed grid topology exists

File:
- `src/m4mesh/mesh_graph.py`

What is confirmed:
- Deterministic 2D adjacency exists.
- Row-stochastic propagation exists.
- Normalized Laplacian exists.
- The operators are precomputed for fixed grid sizes.

Why it matters for NeuroGolf:
- ARC is a 2D grid benchmark.
- These operators are much closer to ARC structure than generic LLM or
  text-first training code.

## Strong Theory Notes Worth Keeping

These notes contain math or executable framing that can become NeuroGolf
primitives:

- `notes/theory/binary-parental-tree-nodal-topology.md`
- `notes/theory/history-as-state-transition-reducer.md`
- `notes/theory/nullspace-legal-interpretation.md`
- `notes/theory/fun_energy_governance_gate.md`

Practical extraction:
- nodal bundles and offset bundles -> local/global reconstruction views
- reducer semantics -> straight-line rewrite / fold mindset
- nullspace projection -> invariant extraction / basis pruning
- fun-energy gate -> explicit satisficing / cost stopping criterion

## What Is Missing

The repo does not yet contain a NeuroGolf-ready pipeline. Specifically missing:

1. ARC task loader
2. ARC grid encoder
3. task-specific structural feature extraction
4. restricted static IR for ARC transforms
5. ONNX graph emitter
6. ONNX validator for banned ops / static shapes
7. params + bytes + MAC cost model
8. submission zip builder

## Current Implemented State

The repo now has the first real end-to-end NeuroGolf lane under `src/neurogolf/`.

What is implemented:

- ARC task loading and static `30 x 30` padding
- one-hot color conversion
- deterministic structural encoding using Sacred Tongues and GeoSeal surfaces
- deterministic connected-component extraction on the compiler/search side
- restricted straight-line IR
- local cost helpers
- ONNX export for restricted straight-line programs
- local ONNX validation for banned ops, static shapes, file size, and cost summary
- Kaggle-style `submission.zip` assembly

Currently synthesized transform families:

- identity
- global color remap
- rigid shift
- dominant-component translation when the dominant object is uniquely identified by color
- dominant-component copy/paste when the dominant object is uniquely identified by color
- multi-object per-color translation when multiple unique colors each identify a single component
- rigid shift then color remap
- flip-x
- flip-y
- transpose
- orientation transform then color remap

Current limitation:

- synthesis is still global-grid and single-family; it does not yet handle
  general multi-component reasoning, crop/paste composition, or more complex ARC object
  interaction patterns in the final single-input ONNX graph.
- component labeling now exists in Python-side search/encoding, but it is not yet
  lowered as a general-purpose component operator into the final static ONNX artifact.

## Why These Steps Came Next

The next implementation choices were:

- multi-object per-color translation
- a hard local ONNX validator/scorer

They were chosen because they improve the lane in two different ways without
breaking the single-input static-graph target.

Multi-object per-color translation:

- extends the solver beyond one-object motion
- stays in the existing straight-line primitive family
- compiles cleanly as repeated `shift_color` steps
- avoids premature general crop/paste logic that would add search complexity
  faster than it adds solved tasks

Local validator/scorer:

- makes exported artifacts auditable before submission
- catches banned operators and shape mistakes locally
- provides a repo-native cost summary so primitive choices can be judged against
  NeuroGolf's metric instead of intuition

This is intentionally narrow. The current lane favors solver families that are:

- easy to synthesize from train pairs
- easy to lower into static ONNX
- easy to score and prune

The next boundary after this is anchor-based or crop/paste composition for
multiple components, but only if it survives the same cost discipline.

## Correct Role Of Each Existing Piece

### Sacred Tongues

Use for:
- reversible structural encoding
- fixed codebooks
- discrete feature routing

Do not use for:
- text generation
- broad semantic reasoning during final inference

### GeoSeal

Use for:
- candidate projection
- distance-based pruning
- anomaly rejection
- cost-aware selection

Do not use for:
- swarm runtime inside the final ONNX graph
- unconstrained dynamic search at inference time

### FnIR / Code Prism

Use for:
- defining the compiler target
- building a restricted ARC transform IR
- lowering symbolic transforms into a static graph

Do not use for:
- treating Python source emission as the final artifact

### M4 Mesh

Use for:
- local adjacency
- fixed neighborhood propagation
- lightweight structural smoothing / diffusion

Do not use for:
- assuming a generic graph pass alone solves ARC

## Recommended NeuroGolf Pipeline

Use the existing system as a compiler:

`ARC examples -> structural encoding -> candidate transform search -> prune ->
restricted IR -> static tensor graph -> ONNX -> score`

Concrete repo-native interpretation:

1. `encode`
   - Start from ARC color grids.
   - Build a compact structural code per cell or component.
   - Route those codes through 6 fixed tongue lanes.

2. `project`
   - Use GeoSeal-style projection / distance / anomaly filters.
   - Drop all feature lanes and candidate transforms that do not improve
     correctness per unit cost.

3. `solve`
   - Search only within a tiny primitive basis.
   - Represent the candidate solution as a straight-line program, not a dynamic
     planner.

4. `compile`
   - Lower the straight-line program into a static tensor graph.
   - Emit ONNX-safe ops only.

5. `prune`
   - Remove every feature lane, weight, and op that is not required for exact
     task correctness.

## Minimal Primitive Set To Build First

The first useful ARC primitive basis should stay small:

- color remap
- equality mask
- neighborhood count
- boundary detection
- connectedness proxy
- rigid shift
- crop / paste
- component-wise translate
- symmetry test
- select / where
- fixed reduction

If a primitive does not reduce final ONNX cost, remove it.

## Best Immediate Build Order

1. Create `src/neurogolf/arc_io.py`
   - load ARC train task JSON
   - normalize to fixed `30 x 30`
   - one-hot color planes

2. Create `src/neurogolf/structural_encode.py`
   - map colors/components into a tiny reversible code space
   - experiment with 6-lane tongue routing

3. Create `src/neurogolf/ir.py`
   - restricted straight-line transform IR
   - no runtime loops
   - no runtime recursion

4. Create `src/neurogolf/search.py`
   - candidate transform search
   - GeoSeal-inspired projection / pruning
   - satisficing stop rule

5. Create `src/neurogolf/onnx_emit.py`
   - lower restricted IR into static ONNX subset

6. Create `src/neurogolf/cost.py`
   - parameter count
   - bytes
   - MAC count

7. Create `src/neurogolf/package.py`
   - write `taskXYZ.onnx`
   - assemble `submission.zip`

## Bottom Line

The system is not starting from zero.

The two most important claims are now confirmed in-code:

- the bijective tokenizer is already built
- GeoSeal is already built

The remaining work is to bind them to ARC through a restricted compiler path.

The winning object is likely not a normal neural network. It is a compiled
micro-program disguised as a tiny static tensor graph.
