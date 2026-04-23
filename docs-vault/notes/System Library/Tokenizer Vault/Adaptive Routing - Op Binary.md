---
title: Adaptive Routing - Op Binary
type: reference
updated: 2026-04-11
source: repo_snapshot
tags:
  - op-binary
  - adaptive-routing
  - inverse-complexity
  - phi-cost
---

# Adaptive Routing - Op Binary

This is the adaptive path-width and remap layer built on top of the atomic op tables.

It is not the tokenizer itself. It is the layer that changes cost and promotion behavior as usage accumulates.

## Runtime Source

- `src/symphonic/multipath/op_binary.py`

## Main Elements

- `TONGUE_PROMOTION_ORDER`
- `OP_BINARY`
- `UsageLedger`
- `effective_cost`
- `remap_tongue_table`

## Core Behavior

- tracks observed usage
- discounts frequent paths with phi-shaped cost behavior
- supports remap-by-usage instead of frozen-width coding
- acts like a worn-path / inverse-complexity surface

## Related Notes

- [[Atomic Op Features - 8 Vector]]
- [[Langues and Related Fields]]
- [[SCBE-AETHERMOORE AI Mind Map]]
