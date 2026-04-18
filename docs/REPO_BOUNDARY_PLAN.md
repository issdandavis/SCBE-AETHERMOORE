# SCBE-AETHERMOORE Repo Boundary Plan

**Last Updated:** 2026-04-08

## Goal

Get the system into a usable, maintainable state without trying to split every repo at once.

## Current Position

This repository currently contains multiple system roles in one tree:

- governance core
- product / MVP API surface
- research and experimental math
- training data and corpus tooling
- deployment and infrastructure
- demos and packaging work

That is workable for active development, but it creates authority drift and makes the public story harder to defend.

## Decision

Do **not** split repos yet.

First make this repository internally coherent:

1. one authority order
2. one canonical runtime formula surface
3. one status language
4. one release-oriented entry map

After that, split only when a boundary is already stable in practice.

## Phase 1 — Stabilize This Repo

Keep all work here while cleaning the system surface.

### Required outputs

- `CANONICAL_SYSTEM_STATE.md`
- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
- one release/readme path for public users
- one runtime map for developers

### Success condition

A new contributor can answer these questions in under 10 minutes:

- what is canonical?
- what is runtime?
- what is experimental?
- what is public?

## Phase 2 — Logical Boundaries

When the repo surface is stable, use these as the target boundaries:

### 1. `scbe-core`

Contains:

- 14-layer governance engine
- canonical math and crypto
- audit / authorize APIs
- deterministic tests

### 2. `scbe-product`

Contains:

- product API surface
- UI / MVP flows
- agent execution adapters
- demos intended for users

### 3. `scbe-training`

Contains:

- corpora
- bundle generation
- tokenizer experiments
- eval harnesses
- training pipelines

### 4. `scbe-research`

Contains:

- phi / fractal / M4NMM / mesh notes
- proofs in progress
- notebooks and experiments
- non-canonical theory branches

## Split Criteria

Only split a boundary when all of these are true:

- the module has a stable purpose
- ownership is clear
- tests for that area already exist
- moving it will reduce confusion more than it creates

If those are not true, keep it here.

## Immediate Recommendation

The next usable-state milestone is **not** a repo split.

It is:

1. authority cleanup
2. release surface cleanup
3. runtime map
4. targeted validation plan

Only after that should repo extraction start.
