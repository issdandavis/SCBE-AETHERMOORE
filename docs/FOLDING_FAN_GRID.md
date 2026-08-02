# Folding Fan Grid

Relational grid for **folding-fan shapes**: hinge + blades (angle) + rings (radius), with default adjacency and **custom cell relationships**.

Module: `python/scbe/folding_fan_grid.py`

## Shapes

| Name | Idea |
|---|---|
| `semicircle` | Open fan, blade mirror folds |
| `full_circle` | Closed circular fan (wrap blades) |
| `accordion` | Linear mountain/valley creases (origami strip) |
| `nested_rings` | Concentric shells around one hinge |
| `half_board` | 7×6 half-board (Connect-X style columns×rows) |
| `sector_grid` | Plain polar lattice |
| `multi_hinge` | Several fans chained by hinge index |

## Coordinates

`FanCell(blade, ring, slot=0, hinge=0)`

- **blade** — sector around the hinge  
- **ring** — distance from hinge  
- **slot** — optional arc subdivision  
- **hinge** — multi-fan id  

## Default relations

- `adjacent_blade` — next sector  
- `adjacent_ring` — outward along a ray (accordion tags M/V folds)  
- `same_ray` — same blade, consecutive rings  
- `fold_mirror` — blade `i` ↔ `blades-1-i`  
- `hinge_shared` — all ring-0 cells on a hinge  
- `diagonal` — blade±1 and ring+1  
- `custom` / named — `add_relation(..., name="support")`  

## Usage

```python
from python.scbe.folding_fan_grid import FoldingFanGrid, RelationKind, list_fan_shapes

g = FoldingFanGrid("semicircle", blades=8, rings=4)
g.add_relation((0, 1), (3, 2), name="support", weight=1.5)

for neighbor, edge in g.neighbors((0, 1), kinds=["support", RelationKind.ADJACENT_BLADE]):
    print(neighbor.label(), edge.kind, edge.weight)

path = g.shortest_path((0, 0), (4, 3))
cells, edges, incidence = g.incidence()
print(g.summary())
print(list_fan_shapes())
```

## Tests

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
pytest tests/test_folding_fan_grid.py -v
```
