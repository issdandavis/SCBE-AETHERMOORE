# AetherDesk Operator Shell v0 (+ v0.1 Provider Status)

Local-only operator console for the SCBE-AETHERMOORE backend. Implements the
v0 slice of [`docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md`](../docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md):
the **Terminal Task Pane**, the **GeoSeal Receipt Pane**, and the **Provider
Status Pane** (v0.1, read-only).

## Run it

```
npm run aetherdesk
```

Open `http://127.0.0.1:5717` in any browser. The server binds to 127.0.0.1
only — there is no remote attack surface.

Override port with `AETHERDESK_PORT=NNNN` if 5717 collides with something.

## What it does (v0)

- Lists the five known-good commands from the spec as runnable buttons.
- Spawns each via `npm run <script>` against the existing repo.
- Captures exit code, stdout/stderr tails (8 KB each), and timing.
- Writes a `aetherdesk_receipt_v0` JSON to
  `artifacts/aetherdesk_receipts/` per run.
- Lists recent receipts in the right pane; click to expand.

## What v0.1 added

The Provider Status Pane (right column) shows whether the practical model
routes are usable — refreshes every 30s, click "Refresh" to re-probe:

- **local-http** (Ollama, LM Studio): GET against the provider's local URL
  with a hard 1.5s timeout. Reports reachable + latency_ms.
- **env-var** (HuggingFace, Anthropic, OpenAI, xAI, Groq): checks whether
  the relevant env var is present. **Never exposes the value** — only the
  matched env-var name (e.g., "via ANTHROPIC_API_KEY").

API endpoint: `GET /api/providers` returns `aetherdesk_providers_v0` schema.

## What it intentionally still does NOT do

- No arbitrary command execution. The allowlist in `server.js` is the
  security boundary — anything not on it returns HTTP 400.
- No file-write access from the UI. The Diff/Patch Pane is still pending.
- No agent-bus invocation from the UI. The Agent Bus Pane is still pending.

## Receipt schema

```json
{
  "schema": "aetherdesk_receipt_v0",
  "task_id": "20260510T180000Z_typecheck",
  "command_id": "typecheck",
  "command_label": "Typecheck (TypeScript)",
  "command": "npm run typecheck",
  "command_digest": "<sha256 of command string>",
  "risk_tier": "read-only",
  "allowed_paths": ["<repo-readonly>"],
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 12345,
  "exit_code": 0,
  "result": "pass",
  "stdout_tail": "...",
  "stderr_tail": "...",
  "artifact_path": "artifacts/aetherdesk_receipts/20260510T180000Z_typecheck.json"
}
```

## Test surface

```
npx vitest run tests/aetherdesk/server.test.ts
```

17 tests cover allowlist enforcement, receipt schema, on-disk round-trip,
and path-traversal rejection.

## SCBE multi-swarm router

OpenClaw is one router/bootstrap surface, not the whole system. The headless
SCBE multi-swarm router can route OpenClaw, OpenCode, Hermes, Codex, Copilot,
Droid, Pi, raw Ollama models, and additional free/open agent surfaces through
one artifact and governance layer:

```powershell
python scripts/system/scbe_swarm_router.py --task "Find one safe next improvement for AetherDesk. Proposal only, no edits." --agents openclaw,opencode,codex,hermes,pi,aider,openhands --timeout 120 --max-workers 2
```

It writes proposals to `artifacts/scbe_swarm_router/latest/` and never mutates
the repo. Agent aliases preserve their launch command, swarm surface, geometry
role, and local model candidates in `agents.json`. `routing.json` records the
free-first escalation decision: local/free lanes run first, and bigger paid
models should only be used as critic, planner, or final integrator after local
lanes fail quality gates. A lane is only promotable when it has no quality
flags. Promotable diffs still go through:

Ollama cloud models are opt-in:

```powershell
python scripts/system/scbe_swarm_router.py --task "Find one safe improvement. Proposal only, no edits." --agents opencode,codex --allow-ollama-cloud --prefer-ollama-cloud --timeout 90 --max-workers 1 --constraint-mode relaxed
```

Cloud lanes are labeled with `execution_surface=ollama_cloud` and
`cost_tier=ollama_cloud` in the artifacts.

```powershell
python scripts/agents/safe_apply.py --patch-file path\to\proposal.diff --smoke "npm test"
```

That is the intended boundary for parallel coding: many local model lanes can
propose work, but only one reviewed diff crosses into the project at a time.

Benchmark the router contract with:

```powershell
python scripts/benchmark/openclaw_swarm_benchmark.py --mode quick
```

Compare local-first against Ollama cloud-preferred routing with:

```powershell
python scripts/benchmark/openclaw_swarm_benchmark.py --mode ollama-cloud
```

## Known v0 limitation

The `Coding-agent benchmark` button will run but cannot fully score the
TypeScript scenarios — the harness expects `scripts/run_typescript_debug_scenario.cjs`
which does not exist yet. See the spec's "Immediate Technical Debt" section.
