---
title: Atomic Op Features - 8 Vector
type: reference
updated: 2026-04-11
source: repo_snapshot
tags:
  - atomic
  - 8-vector
  - multipath
  - trit-table
  - tokenizer-adjacent
---

# Atomic Op Features - 8 Vector

This is the atomic op-feature layer used by the multipath system.

It is adjacent to the tokenizer stack, but it is not the byte/token transport itself.

## Runtime Source

- `src/symphonic/multipath/_trit_common.py`

## What Exists

- `build_trit_table(...)`
- `(64, 8)` feature matrix allocation
- per-op trit vectors
- `atomic_stream(...)`

## 8-Vector Layout

1. `op_id + 1`
2. `group`
3. `period`
4. `valence`
5. `chi`
6. `band`
7. `tongue_id`
8. reserved `0.0`

## Why It Matters

This is where the system stops being just transport and becomes a typed atomic operation surface.

- same structural role can carry different weight
- `chi` changes behavior without changing broad shape
- this is the closest runtime match to the “glucose string” argument: small unit, clean composition, large-scale behavior

## Related Notes

- [[Transport Tokenizer - SS1 and Sacred Tongues]]
- [[Adaptive Routing - Op Binary]]
- [[Langues and Related Fields]]
