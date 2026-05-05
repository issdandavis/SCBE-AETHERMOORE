---
language:
- en
license: cc-by-4.0
pretty_name: SCBE Spine-Overlay Proof v1
size_categories:
- n<1K
tags:
- scbe
- sacred-tongues
- multi-domain
- code
- chemistry
- robotics
- motion
---

# SCBE Spine-Overlay Proof v1

Tiny demonstration bundle (18 rows = 3 domains x 6 tongues)
proving that the SCBE 12+ lane code-packet spine handles **code**,
**chemistry**, and **mechanical motion** as overlays on a single tokenizer
substrate, without forking the system.

## Why this exists

Every row carries the same baseline lanes (binary, tokenizer, transport,
labels, language_views, braille_lane, stisa, structural_parse,
scip_symbol_index, semantic_token_bridge, route_ir, execution_lane,
native_tokenization, atomic_states, ternary_semantics, semantic_expression).

Domain differentiation lives **inside** ``semantic_expression`` as a
nested overlay:

- **Code rows** carry no extra overlay — the 16 lanes already encode
  code structure.
- **Chemistry rows** add ``chemistry_overlay`` (equation, reactants,
  products, reaction_class, stability, atoms_conserved, metaphor).
- **Motion rows** add ``motion_assembly`` (platform_id, role,
  morphology_state, pilot_layers, comm_graph, embodiment_passport,
  invariants). Schema spec: ``docs/specs/MOTION_ASSEMBLY_SCHEMA.md``.

## Hard rules enforced

- **Both ``anchor_runtime`` and ``anchor_spirit`` are present on every
  row.** Per-tongue map: KO=python, AV=typescript/javascript, RU=rust,
  CA=c/mathematica, UM=julia/haskell, DR=haskell/markdown.
- **ASCII-only field names and values.** No Greek glyphs. CTBR vectors
  use ``omega_x``/``omega_y``/``omega_z``, not Greek letters.
- **No branding or theming.** Validated by
  ``tests/coding_spine/test_motion_assembly_schema.py``.

## Breakdown

- domains: {'chemistry': 6, 'code': 6, 'motion': 6}
- tongues: {'AV': 3, 'CA': 3, 'DR': 3, 'KO': 3, 'RU': 3, 'UM': 3}
- row_count: 18

## Files

- ``data.jsonl`` — one JSON row per line, sorted keys, ASCII-encoded
- ``manifest.json`` — counts, row ids, schema version
- ``README.md`` — this file

## Loading

```python
from datasets import load_dataset
ds = load_dataset("issdandavis/scbe-spine-overlay-proof-v1")
```

## Push

```bash
hf upload issdandavis/scbe-spine-overlay-proof-v1 \
  training-data/proofs/spine_overlay_proof_v1
```

## Schema reference

- ``docs/specs/MOTION_ASSEMBLY_SCHEMA.md`` — motion overlay spec
- ``tests/coding_spine/test_motion_assembly_schema.py`` — schema test (28 cases)

## License

CC-BY-4.0
