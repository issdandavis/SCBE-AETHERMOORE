# 3D Spatial Engine

> Terminal-native 3D rendering for code arrays and spatial data structures. No other CLI has this.

## What It Is

A pure-stdlib Python module (`spatial_engine.py`) that gives AI agents **spatial perception** — the ability to organize code and data in 3D structures instead of flat text.

## Core Classes

| Class | Purpose |
|-------|---------|
| `Vec3` | 3D vector with full math (add, sub, dot, cross, normalize, rotate) |
| `Mat4` | 4x4 transform matrix (rotate, translate, scale, perspective) |
| `Mesh` | Vertices + edges + faces with per-vertex tongue coloring |
| `SpatialArray` | 3D-addressed data grid with tongue ownership |
| `AsciiRenderer` | Perspective projection to terminal (wireframe/solid/points) |
| `TongueSpatialMapper` | Maps 6 tongues to 3D axes via paired projection |

## Tongue -> 3D Axis Mapping

The mapper pairs tongues into 3 axes:
- **KO + AV -> X axis** (Control + Transport)
- **RU + CA -> Y axis** (Policy + Compute)
- **UM + DR -> Z axis** (Security + Schema)

Each tongue gets a primary direction vector; space is divided into 6 Voronoi regions.

## SpatialArray: The Key Innovation

Data stored at (x, y, z) coordinates instead of flat indexes:
```python
arr = SpatialArray(8, 8, 8)
arr.set(2, 3, 1, {"tongue": "KO", "token": "kor'vel"})
arr.slice_plane("z", 1)    # 2D slice
arr.spiral_traverse()       # 3D spiral iteration
arr.tongue_region("KO")    # All cells in KO's region
```

## CLI Commands

```bash
python six-tongues-cli.py spatial-view cube --rotate 30,45,0
python six-tongues-cli.py spatial-array --dims 4,4,4 --fill tongue --view
python six-tongues-cli.py spatial-encode --tongue KO --text "hello" --view
python six-tongues-cli.py spatial-navigate --from 0,0,0 --to 7,7,7 --path spiral
```

## Rendering Modes
- **Wireframe**: Bresenham line drawing with depth-interpolated shading
- **Solid**: Scanline fill with painter's algorithm + block characters
- **Points**: Depth-sorted point cloud with tongue colors

## Cross-References
- [[Six Sacred Tongues]] — Color and axis assignments
- [[Tongue Domain Mappings]] — CDDM integration
- [[CDDM Framework]] — SpatialArray uses tongue ownership from CDDM domains

## Status
- **v1.0.0** — Implemented 2026-02-22
- 6-section selftest: all passing
- Auto-detects Unicode support (ASCII fallback on Windows cp1252)
