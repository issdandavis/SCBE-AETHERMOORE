# SCBE Agentic Benchmark v1 (repo-native tasks)

This directory holds **Level 1** tasks for `scripts/benchmark/agentic_benchmark_ladder.py`.

## Layout

```text
benchmarks/scbe_agentic_v1/
  README.md
  tasks/
    <task_id>/
      task.json
```

## `task.json` schema

| Field | Required | Description |
| --- | --- | --- |
| `id` | yes | Stable task id (snake_case). |
| `level` | no | Ladder level (default `1`). Tasks with `level` > current `--max-level` are skipped. |
| `title` | no | Human title. |
| `verify.command` | yes | List of strings: command to run from repo root (or `verify.cwd`). Non-zero exit = failure. |
| `verify.cwd` | no | Relative path from repo root for the subprocess cwd (default `.`). |
| `verify.timeout_sec` | no | Timeout in seconds (default 120). |
| `metrics_hint` | no | Hints for reporting; e.g. `{"evidence_quality": "artifact"}`. |

## Representation consistency (Level 1)

The **`representation_consistency`** task is a *representation* gate, not a training merge gate. It answers:

> Can the same concept keep identity across code languages, Sacred Tongue lanes, tokenizer rows, binary transport, and workflow metadata?

- **Canonical builder / refresh** (optional, manual or scheduled): `npm run benchmark:representation-kaleidoscope`  
  (runs `python scripts/benchmark/build_representation_kaleidoscope.py` and updates under `artifacts/benchmarks/representation_kaleidoscope/`.)
- **Agentic ladder check** (no artifact freshness required): runs  
  `python -m pytest tests/benchmark/test_representation_kaleidoscope.py -q`  
  so CI and the ladder can pass when tests and deterministic checks succeed, without requiring a just-generated JSON/MD bundle. Stricter “fresh artifact” policy can be added later.

## Roadmap (ladder)

- **Level 0**: `agent_router_smoke` coding + system_build (see `scripts/system/agent_router_smoke.py`).
- **Level 1**: This folder.
- **Levels 2–5**: Documented in ladder output as `external_ladder_targets` until Terminal-Bench / SWE-bench / GAIA / governance gates are wired.
- **Level 6**: CLI / GeoSeal *surface* readiness — `python scripts/benchmark/agentic_benchmark_ladder.py run --max-level 6` runs focused pytest (`tests/benchmark/test_cli_competitive_benchmark.py`, `tests/smoke/test_npm_geoseal_bin.py`) with `PYTHONPATH` set to the repo root. Peer feature scoring / artifact refresh remains **`npm run benchmark:cli`** (not required for this gate).
- **Build bijection**: `src/crypto/sacred_tongue_payload_bijection.py` proves canonical JSON for harness artifacts round-trips through **all six** SS1 byte codecs. Wired into `npm run agent:task` (see `build_bijection` on the JSON report) and external eval reports (`sacred_tongue_bijection`). CLI: `npm run agent:prove-build-bijection`.
