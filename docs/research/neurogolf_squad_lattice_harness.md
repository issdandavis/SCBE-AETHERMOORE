# Neurogolf Squad Lattice Harness

Status: design note grounded in the current `src/neurogolf/` implementation.

## Core Claim

Neurogolf already provides the deterministic navigator for ARC-style structure:

- `family_lattice.py` maps a task into topology axes: shape, motion, color, scope, topology, composition.
- `move_family.py` ranks legal moves by lattice similarity, searches depth-1 and depth-2 programs, and emits executable IR.
- `solver.py` verifies every candidate program against the training examples before accepting it.
- The test suite covers grid I/O, move families, cost, validation, solver behavior, and ARC-style benchmark lanes.

The missing layer is not another free-form reasoning prompt. The missing layer is a squad harness that turns same-grade model copies into complementary candidate generators, then lets Neurogolf execute and verify the results.

## Mapping To The Crystal-Cranium Model

The "crystal cranium lattice" maps cleanly onto the implemented topology lattice.

| User Concept | Operational Meaning | Current Code Surface |
| --- | --- | --- |
| lattice brain | structured task coordinates | `task_topology()` |
| crystal facets | different interpretive lenses | topology axes and family rankings |
| oscillating model copies | same model, different role prompts | proposed squad harness |
| stacked outputs | merged candidate family/program set | proposed candidate aggregator |
| tools/guides | legal IR, solver, verifier, cost | `move_family.py`, `solver.py`, `cost.py` |
| passing is passing | execution-verified output | `_program_matches_train()` / tests |

This keeps the creative part where it belongs: proposing compressed paths. It keeps truth where it belongs: executable verification.

## Squad Roles

Use the same base model with different bounded lenses. Each lens must return strict JSON, not prose.

1. `colorist`
   - Looks for palette remaps, dominant/minority colors, masks, fill colors, border colors.
   - Candidate families: `color_remap`, `shift_then_color_remap`, `paint_border`, `fill_enclosed`, `select_*`.

2. `geometer`
   - Looks for flips, rotations, crops, transposes, tiling, panel extraction.
   - Candidate families: `crop`, `crop_then_*`, `flip_*`, `rotate_*`, `transpose`, `tile_*`, `extract_*`.

3. `motion_tracker`
   - Looks for shifts, gravity, object copy/move, alignment.
   - Candidate families: `shift`, `dominant_component_shift`, `dominant_component_copy`, `gravity_*`, `connect_aligned_pairs`.

4. `topologist`
   - Looks for enclosure, symmetry completion, connected components, holes, panels, templates.
   - Candidate families: `sym_complete_*`, `fill_enclosed`, `largest_zero_rect_fill`, `dihedral_template_match`, `panel_*`.

5. `programmer`
   - Converts high-level hypotheses into legal Neurogolf IR sketches.
   - Must use only known operation names or family names.

6. `verifier`
   - Checks candidate explanations for contradictions before execution.
   - Does not decide truth. It only annotates risk and missing assumptions.

## Candidate Contract

Every squad member returns:

```json
{
  "lens": "geometer",
  "task_observations": ["outputs shrink to object bbox", "shape orientation changes"],
  "family_candidates": ["crop_then_rotate_cw", "crop_then_flip_x", "rotate_cw"],
  "program_sketch": [
    {"op": "crop_bbox", "args": {}},
    {"op": "rotate_cw", "args": {}}
  ],
  "confidence": 0.62,
  "known_gaps": ["color relation not checked"]
}
```

The aggregator rejects anything outside this schema. Free text is diagnostic only and cannot enter the solver.

## Execution Pipeline

1. Load ARC task with `arc_io.py`.
2. Compute deterministic topology with `task_topology(task)`.
3. Run normal Neurogolf first:
   - bespoke solvers,
   - move algebra,
   - lattice-ranked family inference.
4. If normal Neurogolf fails, call the squad:
   - same model,
   - different role prompts,
   - strict candidate JSON.
5. Aggregate candidates:
   - deduplicate family names,
   - keep only known families / known IR ops,
   - rank by deterministic lattice score plus model confidence,
   - penalize unsupported or contradictory sketches.
6. Execute candidates against every training example.
7. Accept only verified programs.
8. Report:
   - winning family/program,
   - which lens proposed it,
   - train-pass evidence,
   - cost,
   - failed candidate count,
   - no-squad baseline result.

## Why Same-Grade Copies Can Help

The benefit is not that identical models become smarter by being copied. The benefit is that prompt partitioning changes the search pressure.

A general prompt may blur color, motion, topology, and object scope into one mushy guess. A role prompt forces one model copy to over-attend one axis. Another copy over-attends another axis. The aggregator then gets a wider candidate frontier than a single prompt usually produces.

This is only useful if the candidates are verified. Without verification, prompt partitioning just creates more confident wrong answers.

## Positive Prompt Injection, Reframed Safely

Use "positive injection" as bounded scaffolding:

- give the model the legal operation list,
- give it the topology axes,
- require strict JSON,
- require uncertainty fields,
- forbid invented operations,
- require candidates rather than final truth claims.

Do not use prompt injection as authority bypass. In this harness, prompts may guide candidate generation, but the verifier decides what survives.

## Minimum Experiment

Run three conditions on the same ARC-style task set:

1. `baseline_neurogolf`
   - current deterministic solver only.

2. `single_model_freeform`
   - one prompt asks for a candidate family/program.

3. `squad_lattice`
   - six role prompts produce candidate JSON, then deterministic execution verifies.

Metrics:

- train solve rate,
- held-out/test solve rate where available,
- number of candidates executed,
- cost per solved task,
- newly solved tasks over baseline,
- regressions,
- invented operation rate,
- verifier rejection rate.

The honest success condition is not "the squad sounds better." It is:

```text
squad_lattice solves tasks that baseline_neurogolf and single_model_freeform do not solve,
without increasing false accepts.
```

## Product Rule

The model is allowed to think in lenses. The system must answer in verified programs.

