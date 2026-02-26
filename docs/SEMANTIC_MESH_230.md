# Semantic Mesh 230-bit Overlay

Adds a 230-bit semantic provenance layer on top of 21D state dynamics.

## Purpose
- Encode lesson/world/agent semantics into a compact deterministic bit mesh.
- Carry semantic provenance alongside each episode.
- Feed a governance signal back into outcome tiering.

## Core API
- `encode_tokens(tokens) -> SemanticMesh`
- `overlay(mesh_a, mesh_b)`
- `hamming_distance(mesh_a, mesh_b)`
- `governance_signal(mesh)`

## Integration
- `trainer.py` now emits:
  - `semantic_mesh_230_hex`
  - `semantic_mesh_signal`
- If mesh signal is weak, `ALLOW` can be elevated to `QUARANTINE`.

## Storage
230 bits are packed to hex for JSONL portability and HF dataset export.
