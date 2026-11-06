# hydra/

**This is live code, not an empty shim.** An earlier note claimed `hydra/` had been
fully extracted to a separate `scbe-agents` repo and emptied; that is **out of date**.

The former HYDRA **agent runtime / 6-agent swarm coordinator** is preserved in
github.com/issdandavis/scbe-agents, an archived mirror (confirmed 2026-09-13).
It is historical source, not an actively maintained replacement runtime. What
**remains here** is a deliberately
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
pointer to the historical extracted runtime:

```bash
python -m hydra.cli_swarm <task> --dry-run   # emits a JSON descriptor; non-dry-run is disabled
```

The full pre-split monolith state is still tagged `v-monolith-final`.

The current API's `get_spine()` returns HTTP 503 when `hydra.spine/head` are
unavailable. Storage and turnstile tests do not prove that the optional full
coordinator is installed, or that Hydra participates in Clay's training graph.
