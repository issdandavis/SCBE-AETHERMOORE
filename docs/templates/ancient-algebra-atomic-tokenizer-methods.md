# Ancient Algebra Atomic Tokenizer Method Templates

Status: working templates for tokenizer experiments and small-model math rails.

Source seed: `docs/research/tokenizer-notes/ancient_algebra_atomic_tokenizer_bridge_vBwaWRZyIBM.md`

Boundary: these are representation templates, not security gates. Governance,
crypto, policy, and verification remain separate SCBE layers.

## Template 1: Quantity-Species Atomization

Use when converting a word problem, equation, or instruction into typed atomic
terms.

### Input

```text
<rhetorical math phrase or word problem>
```

### Output Shape

```json
{
  "method": "quantity_species_atomization",
  "source_text": "",
  "atoms": [
    {
      "surface": "",
      "quantity": null,
      "species": "UNIT|ROOT|SQUARE|CUBE|MAGNITUDE|UNKNOWN|OTHER",
      "degree": 0,
      "domain_mode": "DISCRETE_COUNT|CONTINUOUS_MAGNITUDE|BRIDGE_OPERATION",
      "operation_role": "TERM|COEFFICIENT|UNKNOWN|CONSTANT",
      "proof_role": "GIVEN|DERIVED|TARGET",
      "geometry_role": "NONE|LENGTH|AREA|VOLUME|ARC|ANGLE",
      "semantic_class": "ENTITY|ACTION|RELATION|MODIFIER|TEMPORAL|NEGATION|INERT_WITNESS",
      "tongue_hint": "KO|AV|RU|CA|UM|DR"
    }
  ],
  "notes": []
}
```

### Rules

1. Keep `quantity` and `species` separate.
2. Do not normalize to modern symbolic notation until atomization is complete.
3. Preserve unknown species as typed terms, not generic scalar variables.
4. Mark uncertain parses in `notes` instead of forcing a clean atom.

### Example

Input:

```text
A square and ten roots equal thirty-nine units.
```

Output:

```json
{
  "method": "quantity_species_atomization",
  "source_text": "A square and ten roots equal thirty-nine units.",
  "atoms": [
    {
      "surface": "a square",
      "quantity": 1,
      "species": "SQUARE",
      "degree": 2,
      "domain_mode": "BRIDGE_OPERATION",
      "operation_role": "TERM",
      "proof_role": "GIVEN",
      "geometry_role": "AREA",
      "semantic_class": "ENTITY",
      "tongue_hint": "CA"
    },
    {
      "surface": "ten roots",
      "quantity": 10,
      "species": "ROOT",
      "degree": 1,
      "domain_mode": "DISCRETE_COUNT",
      "operation_role": "TERM",
      "proof_role": "GIVEN",
      "geometry_role": "LENGTH",
      "semantic_class": "ENTITY",
      "tongue_hint": "AV"
    },
    {
      "surface": "thirty-nine units",
      "quantity": 39,
      "species": "UNIT",
      "degree": 0,
      "domain_mode": "DISCRETE_COUNT",
      "operation_role": "CONSTANT",
      "proof_role": "GIVEN",
      "geometry_role": "AREA",
      "semantic_class": "ENTITY",
      "tongue_hint": "KO"
    }
  ],
  "notes": []
}
```

## Template 2: Restoration Rewrite

Use when repairing an equation state by moving, adding, or restoring missing
terms while preserving equality.

### Input

```json
{
  "left": [],
  "right": [],
  "defect": "negative_term|missing_balance|subtracted_quantity"
}
```

### Output Shape

```json
{
  "method": "restoration_rewrite",
  "before": {},
  "operation": {
    "name": "RESTORE",
    "target_species": "",
    "quantity_delta": null,
    "applied_to": "left|right|both",
    "equality_preserved": true
  },
  "after": {},
  "proof_trace": []
}
```

### Rules

1. Every restoration must preserve equality.
2. Record the target species. Do not restore a naked quantity.
3. If the same change is applied to both sides, mark `applied_to` as `both`.
4. If a term crosses the equality boundary, record its sign/species change.

## Template 3: Confrontation Rewrite

Use when canceling or combining like species across an equality boundary.

### Input

```json
{
  "left": [],
  "right": []
}
```

### Output Shape

```json
{
  "method": "confrontation_rewrite",
  "before": {},
  "matched_species": "",
  "matched_degree": null,
  "operation": {
    "name": "CONFRONT",
    "left_quantity": null,
    "right_quantity": null,
    "result_side": "left|right|none",
    "result_quantity": null
  },
  "after": {},
  "proof_trace": []
}
```

### Rules

1. Only like species of the same degree may be confronted directly.
2. If species differ, insert a conversion or bridge operation first.
3. If the result quantity is zero, remove the term and record cancellation.
4. Keep a proof trace so the simplification is reversible.

## Template 4: Cut-and-Paste Geometry Trace

Use when solving a quadratic or geometric quantity-species problem through
concrete spatial operations.

### Input

```json
{
  "equation_atoms": [],
  "target_species": "ROOT",
  "target_degree": 1
}
```

### Output Shape

```json
{
  "method": "cut_paste_geometry_trace",
  "initial_geometry": [],
  "steps": [
    {
      "step": 1,
      "operation": "SPLIT|MOVE|COPY|COMPLETE|MEASURE|SOLVE",
      "object": "",
      "quantity": null,
      "species": "",
      "geometry_effect": "",
      "invariant_preserved": "area|length|equality|shape_similarity"
    }
  ],
  "derived_values": [],
  "solution": {}
}
```

### Rules

1. Every move must name the preserved invariant.
2. `COMPLETE` must state what missing geometric object is added.
3. `MEASURE` must produce a derived quantity/species atom.
4. Normalize to modern notation only after the geometry trace is complete.

### Example Trace

```json
{
  "method": "cut_paste_geometry_trace",
  "initial_geometry": [
    "1*SQUARE",
    "10*ROOT rectangle",
    "39*UNIT area"
  ],
  "steps": [
    {
      "step": 1,
      "operation": "SPLIT",
      "object": "10*ROOT rectangle",
      "quantity": 2,
      "species": "RECTANGLE",
      "geometry_effect": "two 5*ROOT rectangles",
      "invariant_preserved": "area"
    },
    {
      "step": 2,
      "operation": "MOVE",
      "object": "one 5*ROOT rectangle",
      "quantity": 1,
      "species": "RECTANGLE",
      "geometry_effect": "forms an L-shape around the square",
      "invariant_preserved": "area"
    },
    {
      "step": 3,
      "operation": "COMPLETE",
      "object": "missing corner",
      "quantity": 25,
      "species": "UNIT",
      "geometry_effect": "completes an 8-by-8 square",
      "invariant_preserved": "equality"
    },
    {
      "step": 4,
      "operation": "MEASURE",
      "object": "completed square",
      "quantity": 64,
      "species": "UNIT",
      "geometry_effect": "side length is 8",
      "invariant_preserved": "area"
    },
    {
      "step": 5,
      "operation": "SOLVE",
      "object": "root side",
      "quantity": 3,
      "species": "ROOT",
      "geometry_effect": "8 minus added side 5",
      "invariant_preserved": "length"
    }
  ],
  "derived_values": [
    {"quantity": 25, "species": "UNIT"},
    {"quantity": 64, "species": "UNIT"},
    {"quantity": 8, "species": "LENGTH"}
  ],
  "solution": {"quantity": 3, "species": "ROOT"}
}
```

## Template 5: Domain-Mode Guard

Use when a problem mixes discrete numbers and continuous geometry.

### Output Shape

```json
{
  "method": "domain_mode_guard",
  "input_atoms": [],
  "domain_modes_detected": [],
  "bridge_required": true,
  "bridge_operations": [],
  "illegal_mixes": []
}
```

### Rules

1. `DISCRETE_COUNT` atoms may combine with matching species.
2. `CONTINUOUS_MAGNITUDE` atoms require geometric or measurement rules.
3. `BRIDGE_OPERATION` must explicitly say how count becomes magnitude or
   magnitude becomes count.
4. If no bridge exists, stop instead of guessing.

## Template 6: Rhetorical-Metric-Transport Split

Use for every tokenizer experiment that touches math, code, conlang, or agent
workflow data.

### Output Shape

```json
{
  "method": "rhetorical_metric_transport_split",
  "semantic_phrase": "",
  "metric_payload": {},
  "transport_packet": {
    "format": "SS1|JSONL|binary|hex|other",
    "value": "",
    "reversible": true
  },
  "boundary_checks": {
    "semantic_not_collapsed_into_transport": true,
    "metric_payload_present": true,
    "transport_marked_downstream": true
  }
}
```

### Rules

1. Do not display transport spelltext as canonical human language.
2. Do not treat reversibility as authorization.
3. Preserve source hash, route id, and transform trace where available.
4. If the transport packet changes but the semantic phrase does not, keep both.

## Small-Model Prompt Template

```text
You are solving through quantity-species atoms, not raw symbolic guessing.

Task:
<problem>

Required process:
1. Extract quantity-species atoms.
2. Build the equality graph.
3. Apply only legal restoration or confrontation transforms.
4. If geometry is needed, emit a cut-paste geometry trace.
5. Normalize to modern notation only after the trace is valid.
6. Give the final answer and the reversible step list.

Return JSON using the method templates.
```

## Benchmark Template

```json
{
  "benchmark_id": "ancient_algebra_atomic_v1",
  "task": "",
  "baseline_prompt": "",
  "atomic_prompt": "",
  "expected_atoms": [],
  "expected_transforms": [],
  "expected_solution": {},
  "scores": {
    "atom_recall": 0.0,
    "species_accuracy": 0.0,
    "legal_transform_rate": 0.0,
    "solution_correct": false,
    "explanation_fidelity": 0.0
  }
}
```

