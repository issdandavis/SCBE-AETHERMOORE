# Machine Crystal Dual/Fano Bridge

Date: 2026-06-27
Status: Implemented as `python/scbe/machine_crystal_dual.py`

## Result

The Machine Crystal now has a bridge receipt tying together:

- cube corners,
- octahedron faces,
- `GF(2)^3` 3-bit addresses,
- the 8 Machine Crystal tape ops,
- and the 7-point Fano plane.

## Core distinction

`GF(2)^3` has 8 elements:

```text
0..7
```

The Fano plane uses only the 7 nonzero elements:

```text
1..7
```

So vertex/face `0` is still a real Machine Crystal operation, but it is not a
Fano point.

## Invariants validated

- 8 cube vertices.
- 8 octahedron faces.
- 12 cube edges.
- 12 dual octa-face adjacency edges.
- 7 nonzero Fano points.
- 7 Fano lines.
- each Fano point appears on exactly 3 lines.
- every Fano line XORs to zero.
- the Machine Crystal still executes `+++. -> output_hex 03`.

## Command

```powershell
python scripts\benchmarks\bench_machine_crystal_dual.py
```

Receipt:

```text
artifacts/machine_crystal/dual_fano_receipt.json
```

## Full adjacent-surface review command

Use this after changing any Machine Crystal surface:

```powershell
python scripts\system\review_machine_crystal_area.py
```

It reviews:

- primitive octahedral runtime,
- higher shape macros,
- PHDM path-state injection,
- cube/octahedron/Fano bridge,
- benchmark scripts,
- docs/specs/research files,
- artifact receipt paths.

Receipt:

```text
artifacts/machine_crystal/area_review.json
```

## Product meaning

The object now has three levels:

```text
8-address machine crystal     = executable tape ops
7-point Fano plane            = nonzero algebra/incidence layer
PHDM/path-state higher shapes = governed macro injection layer
```

This keeps the runtime honest while giving the geometry enough structure for
language routing, Fano/octonion-style incidence, and visual AetherDesk control.
