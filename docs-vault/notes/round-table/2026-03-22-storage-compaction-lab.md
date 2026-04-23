# 2026-03-22 Storage Compaction Lab

## Why

The goal of this pass was to test whether SCBE storage behavior can improve by
changing a small number of storage variables before rewriting any storage
subsystem.

Instead of changing storage logic broadly, this pass introduced a bounded lab:

- `scripts/system/storage_compaction_lab.py`
- `src/crypto/octree.py` stats surface

The lab uses deterministic synthetic workloads and sweeps one variable at a
time.

## What Was Tested

### 1. Hyperbolic Octree

Sweep:

- system: `hyperbolic-octree`
- knob: `max_depth`
- values: `3, 4, 5, 6`

Artifact:

- `artifacts/system_audit/storage_compaction_lab/20260322T162628Z-hyperbolic-octree-max_depth.json`

Result:

- `max_depth = 3` produced the strongest compaction score on the current lab
  workload.
- As depth increased, occupied voxels and storage units increased quickly.
- By `max_depth = 6`, the workload was effectively one-point-per-voxel.

Key numbers:

- `depth 3`: `43` occupied voxels, `116` storage units, compaction `0.758621`
- `depth 6`: `88` occupied voxels, `406` storage units, compaction `0.216749`

Interpretation:

- For clustered/overlapping workloads, deeper sparse-octree splitting can
  destroy packing efficiency.
- If the goal is compaction rather than maximum separation, the current lab
  suggests a shallower depth is better.

### 2. Lattice25D Hybrid

Sweep:

- system: `lattice25d`
- knob: `cell_size`
- values: `0.2, 0.25, 0.333333, 0.5`

Artifact:

- `artifacts/system_audit/storage_compaction_lab/20260322T162628Z-lattice25d-cell_size.json`

Result:

- `cell_size = 0.5` produced the strongest compaction score on the clustered
  lattice workload.
- Larger cells reduced occupied-cell count and total storage units.
- The tradeoff is hotter overlap inside each occupied cell.

Key numbers:

- `cell_size 0.5`: `5` occupied cells, `134` storage units, compaction `0.537313`
- `cell_size 0.2`: `12` occupied cells, `141` storage units, compaction `0.510638`

Interpretation:

- Coarser lattice cells increase packing density.
- That is good for compaction, but query precision and conflict isolation may
  get worse if overlap becomes too hot.

### 3. Lattice25D Quadtree Capacity

Sweep:

- system: `lattice25d`
- knob: `quadtree_capacity`
- values: `2, 4, 8, 12`

Artifact:

- `artifacts/system_audit/storage_compaction_lab/20260322T162628Z-lattice25d-quadtree_capacity.json`

Result:

- `quadtree_capacity = 12` compacted best on this workload.
- Lower capacities caused rapid node growth and much weaker compaction.

Key numbers:

- `capacity 12`: `41` quadtree nodes, compaction `0.590164`
- `capacity 2`: `173` quadtree nodes, compaction `0.283465`

Interpretation:

- The quadtree is currently over-eager when capacity is low.
- For clustered workloads, raising capacity reduces node explosion without
  changing bundle count.

## Testing

Commands run:

```powershell
python -m pytest tests/test_hyperbolic_octree_stats.py tests/test_storage_compaction_lab.py tests/test_octree_sphere_grid.py tests/test_quadtree25d.py -q
python scripts/system/storage_compaction_lab.py --system hyperbolic-octree --knob max_depth
python scripts/system/storage_compaction_lab.py --system lattice25d --knob cell_size
python scripts/system/storage_compaction_lab.py --system lattice25d --knob quadtree_capacity
```

Result:

- `143 passed`

## Immediate Recommendation

If the current goal is packing efficiency rather than finest-grain isolation:

- octree lab default: try `max_depth = 3` first
- lattice hybrid: try `cell_size = 0.5`
- lattice quadtree: try `quadtree_capacity = 12`

These are not universal truths. They are the best current settings for the
bounded deterministic lab workload. The next step is to run the same lab
against a real repo-derived memory/training payload.
