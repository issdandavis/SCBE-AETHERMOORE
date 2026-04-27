# scbe-agent-bus

> SCBE-governed event runner. Typed Node surface over the existing Python pipeline.

**Status:** `0.1.0` — pre-1.0, API may break between minor versions until `1.0.0`.

Routes AI / human / AI events through the SCBE governed runner (`scripts/system/agentbus_pipe.mjs` → `scbe-system-cli.py agentbus run`) and returns a typed `scbe-agentbus-pipe-result-v1` envelope. The Python side is the source of truth; this package exists so TypeScript / Node callers do not each reimplement the spawn glue.

## Install

```bash
npm install scbe-agent-bus
```

This package depends on the SCBE Python runtime being available on the host. The Node API spawns `node ./scripts/system/agentbus_pipe.mjs` against a repo root you provide via `RunnerOptions.repoRoot` (or the parent of `node_modules/scbe-agent-bus/dist/` if omitted). For most consumers, set `repoRoot` explicitly to the SCBE repo checkout that owns the runner and Python CLI.

## What this package is

A thin typed wrapper around the existing `scripts/system/agentbus_pipe.mjs` runner, which itself shells out to `scbe-system-cli.py agentbus run`. The Python side is the source of truth; this package exists to make the runner consumable from TypeScript / Node fleets without each caller re-implementing the spawn glue.

## What this package is NOT

- Not a re-implementation of the SCBE governance pipeline. The 14-layer stack stays in Python.
- Not an authentication layer. Caller is responsible for ensuring the spawned Python process has the credentials it needs.
- Not stable yet. `0.1.0` signals that the envelope shape and runner CLI flags may change before `1.0.0`.

## Contract surface

```typescript
import { runEvent, runBatch, type AgentBusEvent, type AgentBusResult } from 'scbe-agent-bus';

const result: AgentBusResult = await runEvent({
  task: 'summarize the latest harmonic-wall verdict',
  taskType: 'general',
  seriesId: 'review-2026-04-27',
  privacy: 'local_only',
  budgetCents: 0,
  dispatch: false,
  dispatchProvider: 'offline',
});
```

Each event is normalized and forwarded to the Python CLI; the Python side runs the harmonic wall, produces the governed result, and returns a `scbe-agentbus-pipe-result-v1` envelope. This package re-types that envelope and surfaces parse errors as Node-side exceptions.

## In-house functionality gate

This gate decides whether the bus is a usable internal product surface.

| # | Item | Status |
|---|---|---|
| 1 | TS surface + types declared | scaffolded — see `src/index.ts` |
| 2 | Single-event local smoke test returns `scbe-agentbus-pipe-result-v1` | PASS — `agent-bus-smoke-20260427` |
| 3 | Batch local smoke test preserves event order and reports per-event status | PASS — `agent-bus-batch-20260427`, events 1–2 |
| 4 | Rehearsal gate passes on the default local scenario | PASS — zero failures / warnings in smoke and batch runs |
| 5 | Pressure test passes without external dispatch or secret leakage | PASS WITH UTILITY GAP — `agent-bus-pressure-20260427b`, 4 pass / 1 utility gap / 0 fail |
| 6 | Trace artifacts are written under `artifacts/agentbus/` or equivalent | PASS — `artifacts/agent_bus/user_runs/*` and `artifacts/agent_bus/mirror_room/*` |
| 7 | Human-readable operator note documents how to use it in-house | this README |

When this gate clears, the package is useful even if it never leaves this machine.

## Roadmap before `1.0.0`

`0.1.0` shipped under explicit user authorization on 2026-04-27. The items below are pre-1.0 work, not publish blockers. API may break in `0.x` minor bumps until they land.

| # | Item | Status |
|---|---|---|
| 1 | Branches 1, 2, 4 of agent-bus feature plan (default rehearsal gate, mission envelope, trace spans) | NOT STARTED |
| 2 | Tests green on Windows + Linux CI for the TS package | NOT STARTED |
| 3 | Executable promotion gate passing against frozen scenarios | NOT STARTED |
| 4 | CHANGELOG maintained per release | started — see `CHANGELOG.md` |

`1.0.0` requires explicit user sign-off; do not auto-bump major.

## Why a Node surface at all

The Python side is canonical. The Node surface exists because:

- existing fleet code is TypeScript-heavy (`src/fleet/`, `src/harmonic/`, `src/aetherbrowser/`)
- Zapier / Grok-fleet-style consumers expect a `.mjs` or `import` entry, not a `subprocess.run`
- typed envelopes catch schema drift between the Python CLI and downstream consumers at compile time

## Local development

```bash
# from packages/agent-bus/
npm run agentbus:pipe < event.json
```

That command shells the existing `scripts/system/agentbus_pipe.mjs` runner. The TS API in `src/index.ts` is a typed wrapper around the same call path.

## Cross-references

- runner: `scripts/system/agentbus_pipe.mjs`
- governed CLI: `scripts/scbe-system-cli.py agentbus run`
- pressure tests: `scripts/system/agentbus_pressure_test.py`
- rehearsal gate: `scripts/system/agentbus_rehearsal_gate.py`
- mirror room (multi-agent): `scripts/system/mirror_room_agent_bus.py`
- envelope schema: `scbe-agentbus-pipe-result-v1` (see runner output)
