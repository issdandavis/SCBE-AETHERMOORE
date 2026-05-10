# AetherDesk Operator Shell v0

Status: proposed implementation slice

Purpose: turn SCBE's existing agent bus, GeoSeal receipts, local benchmark
lanes, and provider routing into a desktop-style operator surface.

This spec is informed by the Terax AI terminal review in
`docs/research/TERAX_AI_TERMINAL_REFERENCE.md`, but it is not a clone. Terax is
an AI terminal. AetherDesk should be a governed coding-agent workbench.

## Goal

Make the offline/local coding-agent workflow usable enough to test, sell, and
improve:

```text
task -> route -> propose patch -> show receipt -> run tests -> learn from result
```

The user should not need to know which script, benchmark, or agent bus endpoint
to call. AetherDesk should expose the current system as a simple operator
console.

## Non-Goals

- Do not build a full VS Code replacement.
- Do not claim SWE-bench or Terminal-Bench readiness before adapters are real.
- Do not let the AI directly write files without an explicit patch/diff gate.
- Do not move secrets into frontend storage.

## v0 Panels

### 1. Terminal Task Pane

Runs bounded commands through the existing repo scripts.

Initial buttons:

- `Typecheck`: `npm run typecheck`
- `TS tests`: `npm test`
- `CLI benchmark`: `npm run benchmark:cli`
- `Aether-Lattice`: `npm run research:aether-lattice`
- `Coding benchmark`: `npm run benchmark:coding-agents`

Output must be captured as an artifact path plus a short pass/fail summary.

### 2. Agent Bus Pane

Thin UI over current Agent Bus task semantics.

Inputs:

- task description
- allowed write scope
- max runtime
- provider preference: local / HF / cloud / no-model

Outputs:

- selected route
- generated plan
- proposed commands
- proposed patch path or diff
- status

### 3. GeoSeal Receipt Pane

Every command or patch attempt gets a receipt.

Minimum receipt fields:

- task id
- timestamp
- command or patch digest
- allowed paths
- risk tier
- tests run
- pass/fail result
- artifact path

### 4. Diff / Patch Pane

The agent may propose edits, but v0 should require a visible diff before write.

States:

- proposed
- approved
- applied
- rejected
- reverted

### 5. Provider Status Pane

Show whether the practical model routes are usable.

Initial checks:

- Ollama reachable
- LM Studio/OpenAI-compatible endpoint reachable
- HF token present in environment
- cloud providers configured or unavailable

This panel should not expose secret values.

## Backend Shape

Use the existing repo first:

- Agent Bus: `scripts/agents/run_agent_task.py`
- benchmark scripts: `scripts/benchmark/*`, `scripts/eval/*`,
  `scripts/research/aether_lattice_sim.py`
- GeoSeal / governance CLI surfaces already in tests and scripts

Add a new adapter only if the existing script cannot be called safely.

## Immediate Technical Debt To Clear

The functional coding-agent benchmark currently fails because the harness looks
for:

```text
scripts/run_typescript_debug_scenario.cjs
```

That file is missing. This blocks honest scoring of the offline coding-agent
lane. Fix this before claiming AetherDesk coding-agent readiness.

## Success Criteria

v0 is ready when:

- a user can submit one coding task from the UI
- the task produces a GeoSeal receipt
- any proposed file change appears as a diff before write
- at least one local benchmark can run from the UI and display its artifact
- the coding-agent benchmark harness no longer fails from missing runner files

## Why This Is Sellable

Terax proves that developers understand and want an AI-native terminal surface.
SCBE's wedge is different:

- Terax: AI terminal with tools
- AetherDesk: governed agent workbench with receipts, routing, benchmarks, and
  training capture

That lets SCBE sell governance and repeatability instead of competing only on
chat UX.

