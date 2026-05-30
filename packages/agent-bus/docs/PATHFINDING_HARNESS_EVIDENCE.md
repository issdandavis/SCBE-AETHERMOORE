# Pathfinding Harness Evidence

Status: executable local benchmark lane for the agent-bus.

This benchmark family tests pathfinding as governed execution, not plan-only
reasoning. A valid result must emit a receipt hash, an execution trace, and
machine-checkable evidence for the path policy under test.

## Research Inputs Folded In

- `docs/specs/SCBE_AGENT_PATH_POLICY.md`: non-optimal correct path finding,
  ko-ban/revisit pressure, verification before completion.
- `docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md`: spin-vector coherence and
  disorder as a reranking channel.
- `exports/obsidian/notion_mcp_ingest_2026-02-24/GeoSeal_Geometric_Access_Control_Kernel.md`:
  access/risk/quarantine fields as path constraints.
- `notes/sphere-grid/AV-Transport/T2-Navigation/pattern.md`: sense, plan,
  steer, decide loop.

## Current Lanes

| Lane             | Command                               | Evidence target                                                                 |
| ---------------- | ------------------------------------- | ------------------------------------------------------------------------------- |
| Roll-stack maze  | `npm run benchmark:roll-stack-maze`   | BFS execution, output contract, receipt hashes                                  |
| Worm adapter     | `npm run benchmark:worm-adapter`      | Local sensing, penetration ratio, loop rate, greedy delta                       |
| Projection board | `npm run benchmark:projection-board`  | Fog-of-war board, hidden lattice fields, 3x3 kernel convolution, spin coherence |
| Vector-field nav | `npm run benchmark:vector-field-nav`  | Seeded mazes, A\*/greedy/random baselines, receipt chain, ablations             |
| Suite            | `npm run benchmark:pathfinding-suite` | Combined scorecard across all current lanes                                     |

## Latest Focused Result

Command:

```bash
npm run benchmark:pathfinding-suite
```

Result:

```json
{
  "ok": true,
  "evidence_failed": 0,
  "benchmark_process_failures": 0,
  "avg_primary_score": 0.75,
  "max_p95_ms": 41
}
```

Breakdown:

- Roll-stack maze: 4/4 evidence passed, primary score 1.00.
- Worm environmental adapter: 4/4 evidence passed, solved rate 0.75,
  primary score 0.25. This is intentionally honest: the lane measures depth of
  penetration and loop behavior under local sensing, not guaranteed success.
- Projection board: 4/4 evidence passed, solved rate 1.00, primary score 1.00.
- Vector-field nav: 20/20 receipt chains complete, multi-lattice solve rate
  0.75, random solve rate 0.00.

## Kernel Convolution Lattice

The projection board uses a local 3x3 kernel over hidden base fields:

```text
0.4  0.7  0.4
0.7  1.0  0.7
0.4  0.7  0.4
```

Convolved fields:

- unknown frontier
- wall pressure
- security risk
- permission key
- locked gate
- importance/depth checkpoint
- goal pressure

Each projected move also carries a three-axis spin vector:

- goal trajectory
- frontier/permission/importance pull
- risk/revisit/lock pressure

The benchmark records spin coherence as `|sum_i S_i| / n` and spin disorder as
`1 - coherence`, then applies a bounded disorder penalty to the next move.

The TypeScript vector-field navigation module also exposes the same 3x3 kernel
as `VECTOR_KERNEL_3X3` and uses it as an eighth local field in `computeVTotal`.
The `no-kernel` ablation keeps this measurable.

## Caveat

This is a local synthetic benchmark suite, not an external hidden benchmark yet.
The next hardening step is seeded randomized maze generation with hidden
fixtures, followed by a Kaggle-style task adapter that preserves the same
receipt and evidence contract.
