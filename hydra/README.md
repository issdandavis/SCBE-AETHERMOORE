# hydra/

**This is live code, not an empty shim.** An earlier note claimed `hydra/` had been
fully extracted to a separate `scbe-agents` repo and emptied; that is **out of date**.

What's true: the full HYDRA **agent runtime / 6-agent swarm coordinator** does live in
its own repo (github.com/issdandavis/scbe-agents). What **remains here** is a deliberately
kept ~5,200 LOC **storage-geometry subset** plus the shared governance turnstile — both
import cleanly and are live dependencies of `src/api`, `agents/agent_bus_ledger`, the n8n
bridge, and notebooks.

## What's here (retained, working)

| Module | Purpose |
|--------|---------|
| `octree_sphere_grid.py` | Octree sphere-grid spatial index |
| `quadtree25d.py`, `lattice25d_ops.py` | 2.5D quad/lattice geometry ops |
| `voxel_storage.py` | Voxel storage backend |
| `color_dimension.py` | Color-dimension encoding |
| `ledger.py` | Append ledger used by the agent bus |
| `turnstile.py` | Domain-aware turnstile (`ThreatScan` + domain → `TurnstileOutcome`); the choke-point shared by all gates |

Related lattice/voxel/octree suites (≈51 tests) pass.

## Compatibility stub

`cli_swarm.py` (and `llm_providers.py`) is the **only** genuine stub here — a
backward-compatibility CLI that supports `--dry-run` only and otherwise exits with a
pointer to the extracted runtime:

```bash
python -m hydra.cli_swarm <task> --dry-run   # emits a JSON descriptor; non-dry-run is disabled
```

The full pre-split monolith state is still tagged `v-monolith-final`.
