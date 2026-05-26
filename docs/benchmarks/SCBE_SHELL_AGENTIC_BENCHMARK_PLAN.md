# SCBE Shell Agentic Benchmark Plan

Status: R&D benchmark lane, not a public leaderboard claim.

## Research Grounding

The strongest public agent benchmarks converge on the same requirement: the model is only part of the system. The agent-computer interface, tool routing, feedback loop, and verification harness determine whether the model can finish work.

- Terminal-Bench tests agents on real terminal tasks in isolated environments.
- SWE-bench and SWE-bench Verified test issue-to-patch workflows against repository tests.
- SWE-agent's published interface design emphasizes concise file viewing, syntax-gated editing, repository search, explicit feedback for empty output, and controlled command execution.
- OSWorld and WebArena/BrowserGym test computer and web operation rather than raw chat.
- Tau-bench tests tool-use agents through realistic transactional workflows.

For SCBE, the comparable object is not "does the chat answer sound smart." It is: can `scbe shell` turn user or agent intent into a bounded operation, execute the right tool, and return evidence without unsafe drift.

## What SCBE Can Beat Now

SCBE can compete immediately on:

- Local/free-first operation: default Ollama/local config, no cloud key required.
- Governed command execution: destructive commands are blocked by the shell gate before dispatch.
- Dual user mode: plain English and direct command input share one shell surface.
- Agent-readable evidence: commands can be run with JSON receipts through existing `scbe run --json` and agent-bus routes.
- Packaging portability: the TUI runtime is included in the npm package dry run.

## Where SCBE Is Still Behind

SCBE is behind mature coding assistants on:

- Repository retrieval: no full Sourcegraph-style semantic index in the shell yet.
- Patch editing ergonomics: no syntax-aware edit/apply command inside the TUI.
- Benchmark adapters: no direct Terminal-Bench/SWE-bench runner yet.
- Long-running task observation: the shell can run commands, but does not yet supervise multi-step workflows with resumable state inside the TUI.
- Structured agent protocol: agents still have to drive a terminal transcript instead of a stable request/response JSON protocol.

## Benchmark Ladder

### Level 0: Shell ACI Smoke

Command:

```bash
cd packages/cli
npm run bench:shell
```

Measures:

- mode discoverability
- scriptable minimal shell
- rich-shell config
- config persistence in isolated home
- PowerShell passthrough without AI routing
- governance block on a destructive command
- TUI module import/export
- npm package inclusion

Pass condition: 100%.

### Level 1: Agentic Workflow Smoke

Use the existing DCP and Tetris-tree route tests:

```bash
python -m pytest tests/agentic/test_dcp.py tests/agentic/test_dcp_routes.py -q
```

Measures:

- approved tool bucket
- GitHub/Copilot route construction
- tetris-tree lock/reject behavior
- watcher receipt before dispatch
- completion gates

### Level 2: Functional Coding Micro-Benchmark

Use the existing local functional coding harness:

```bash
python scripts/eval/functional_coding_agent_benchmark.py --candidate-file <file> --min-pass-rate 1.0
```

Measures:

- generated code behavior
- state mutation correctness
- repair loop effectiveness
- compiler receipt integrity

### Level 3: External Benchmark Adapters

Add thin adapters, not custom score claims:

- Terminal-Bench adapter: package `scbe shell --agent-json` as the agent command.
- SWE-bench Lite/Verified adapter: use shell/agent-bus to inspect issue, patch, run tests, and emit a patch.
- Aider Polyglot adapter: compare SCBE shell as harness around an existing model, not as a model.
- Tau-bench adapter: map tool calls through GeoSeal policy decisions.
- WebArena/BrowserGym adapter: later, after browser action receipts are stable.

## Immediate Improvements

1. Add `scbe shell --agent-json` for stable machine control.
2. Add `scbe shell --script <file>` to replay workflows deterministically.
3. Add a repository retrieval primitive: `:files <query>` backed first by ripgrep, later by SCIP/tree-sitter.
4. Add patch commands: `:patch apply`, `:patch show`, `:patch revert-last`.
5. Add workflow receipts: each multi-step run should emit `artifacts/benchmarks/scbe-shell/<run>.json`.
6. Add Terminal-Bench/SWE-bench adapters only after Level 0 and Level 1 are green.

## Readiness Score

Current target scoring:

- Shell ACI smoke: 40 points
- Agentic route smoke: 20 points
- Functional coding micro-benchmark: 20 points
- External benchmark adapter readiness: 20 points

Do not publish the external score until the adapter exists and has run against public tasks.

## Current Local Evidence

Run on branch `feat/ink-tui` after adding the shell benchmark lane:

```bash
cd packages/cli
npm run bench:shell
```

Result:

- Shell ACI smoke: 9/9, 100%
- Artifact: `artifacts/benchmarks/scbe-shell/2026-05-26T21-21-43-734Z-shell-agentic-benchmark.json`

Agentic route smoke:

```bash
python -m pytest tests/agentic/test_dcp.py tests/agentic/test_dcp_routes.py -q
```

Result:

- 53 passed

CLI package tests:

```bash
cd packages/cli
npm test
```

Result:

- 4 passed

Finding from the first benchmark run: scripted rich-shell passthrough initially allowed child command stdin handling to interfere with the transcript. The shell now detects non-interactive input and captures command output, so agent-driven transcripts can continue through `:exit` instead of hanging.
