# SCBE Cube Pipeline

Status: executable reference

## Mechanic boundary

**SOURCE:** The official Rubik's 3x3 guide describes fixed center pieces,
multi-color pieces whose colors move together, legal face turns, inverse turns,
and a solved state in which each piece matches its center:
<https://rubiks.com/solve-guide>.

**INFERENCE:** Those mechanics are useful for workflow projections when the
canonical operation keeps its identity while its execution view changes.
They do not make pipeline scheduling equivalent to solving a physical cube.

**IMPLEMENTED MAPPING:**

| Cube mechanic   | SCBE pipeline mechanic            | Preserved invariant                                              |
| --------------- | --------------------------------- | ---------------------------------------------------------------- |
| Fixed centers   | Canonical pipeline JSON           | Step IDs, argv, dependency edges, command hashes                 |
| Attached colors | One step across every projection  | A projection cannot change a command's identity                  |
| Face turn       | Deterministic projection/repair   | Only generated GitHub and n8-style files change                  |
| Legal move      | Schema-checked rotation           | No shell program, forward dependency, or host path is introduced |
| Inverse/check   | Git plus before/after hashes      | Every generated face can be compared with its center             |
| Solved cube     | `validate` reports `solved: true` | All projections exactly match the canonical digest               |

The analogy stops there. This is a small DAG runner and projection engine, not
a claim that cube-solving algorithms optimize arbitrary workflows.

## Six faces

1. `canonical`: versioned pipeline spec and fixed operation identity.
2. `github`: GitHub Actions YAML.
3. `n8`: an n8-style queue with typed `argv`, dependencies, and hashes.
4. `windows`: direct Python subprocess execution selected through `pwsh`.
5. `posix`: direct Python subprocess execution selected through `bash`.
6. `receipt`: per-step status, duration, return code, and stdout/stderr hashes.

The Windows and POSIX faces use the same direct runner. The shell is used only
to start that runner from a generated GitHub step; canonical commands execute
with `shell=False`.

## Files

- Engine: `scripts/system/scbe_cube_pipeline.py`
- Operator integration: `scripts/scbe-system-cli.py workflow ...`
- Nightly center: `workflows/pipelines/nightly-ops.pipeline.json`
- GitHub projection: `.github/workflows/nightly-ops.yml`
- n8 projection: `workflows/n8n/nightly-ops.queue.json`
- Manual operator cube: `workflows/pipelines/cli-nightly-ops.pipeline.json`
- Tests: `tests/system/test_scbe_cube_pipeline.py`

## Commands

Generate all three persistent artifacts together:

```text
python scripts/scbe-system-cli.py workflow styleize ...
```

Check whether the cube is solved without changing files:

```text
python scripts/scbe-system-cli.py workflow validate \
  --spec-path workflows/pipelines/nightly-ops.pipeline.json
```

Repair drifted projections from the canonical center:

```text
python scripts/scbe-system-cli.py workflow repair \
  --spec-path workflows/pipelines/nightly-ops.pipeline.json --apply
```

Preview or execute locally:

```text
python scripts/scbe-system-cli.py workflow run \
  --spec-path workflows/pipelines/nightly-ops.pipeline.json --dry-run
```

Remove `--dry-run` to execute. Local runs receive a unique run ID and write
receipts below the operating-system temporary directory unless an explicit
receipt directory is supplied.

## Auto-fix boundary

The deterministic repair lane may:

- replace missing or stale GitHub/n8 projections with exact canonical output;
- select `bash` for Linux and `pwsh` for Windows when shell selection is auto;
- replace user-specific absolute metadata with portable repository paths;
- restore current action versions, step IDs, dependencies, and hashes.

It may not:

- change canonical command argv or dependency edges;
- invoke a command through `shell=True`;
- skip a failing test or rewrite its expected result;
- lower a security or integrity gate;
- stage, commit, push, or merge unrelated files.

A failed prerequisite writes a `blocked` receipt for its dependent step. It
does not run that dependent command.

## Current measured result

**RESULT (2026-11-26):** 27 focused tests passed across the engine, operator
CLI, zero-job detector, deterministic auto-fixer, workflow audit, and committed
projection guards. They exercise projection parity, stale-file repair and
idempotence, Windows shell selection, YAML-field injection rejection, path
traversal rejection, CRLF/LF portability, direct subprocess execution, hashed
receipts, and dependency blocking.

Both committed cubes report `solved: true` with exact generated-file hashes:

- `nightly-ops` pipeline:
  `e0b43351bbe6a31a2f58eecb21c1ea217bf567c72f37d89a68b2bb2a30297659`
- `cli-nightly-ops` pipeline:
  `8384daccac56324a9a7d4ff45a41892075cb1dbb6ca810cec08872b7566d27ca`

Historical zero-job run `45901528309` now classifies as
`cube_pipeline_repair` and resolves to the correct nightly spec path. Treat
execution of the generated workflow on GitHub as proposed until this revision
completes on a real runner.
