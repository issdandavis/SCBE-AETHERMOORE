---
title: Hyperbolic Terrain Mapping Intro
layout: default
nav_exclude: true
---

# Hyperbolic Terrain Mapping: Practical Intro

## Poincare disk model (fast mental model)

The Poincare disk maps an infinite hyperbolic plane into a finite circle.

- Points inside the unit disk are valid states (`x^2 + y^2 < 1`).
- Geodesics (shortest paths) are arcs orthogonal to the disk boundary.
- Distances grow rapidly near the edge, so hierarchical structure fits naturally.

This is why hyperbolic mapping is useful for tree-like terrains and route graphs:
branching can grow exponentially while staying representable in a finite view.

## Hyperbolic geometry in games

In Euclidean terrain, scale eventually repeats or requires very large worlds.
In hyperbolic terrain:

- local neighborhoods stay readable
- global expansion can continue without visible hard boundaries
- branching paths diverge faster, which helps non-repetitive exploration

For gameplay systems, this is useful for procedural worlds, routing puzzles,
swarm navigation arenas, and semantic map visualization.

## Interactive examples

Use the local playground here:

- [Hyperbolic Terrain Playground](./hyperbolic-terrain-playground.html)

It includes:

1. Poincare distance visualizer (two-point distance)
2. Geodesic arc visualizer (endpoint to endpoint)
3. Hyperbolic branching terrain toy model (depth + branching sliders)

## SCBE linkage

The same geometry idea maps cleanly to SCBE routing:

- 2.5D lattice (`x`, `y`, cyclic `phase`)
- adaptive quadtree partitioning for variable local detail
- projection into signed octree for 3D-compatible operations

Relevant code:

- `hydra/octree_sphere_grid.py`
- `hydra/lattice25d_ops.py`
- `workflows/n8n/scbe_n8n_bridge.py`
