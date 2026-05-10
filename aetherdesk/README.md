# AetherDesk Operator Shell v0

Local-only operator console for the SCBE-AETHERMOORE backend. Implements the
v0 slice of [`docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md`](../docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md):
the **Terminal Task Pane** + the **GeoSeal Receipt Pane**.

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

## What it intentionally does NOT do (v0)

- No arbitrary command execution. The allowlist in `server.js` is the
  security boundary — anything not on it returns HTTP 400.
- No file-write access from the UI. The Diff/Patch Pane is v0.1.
- No agent-bus invocation from the UI. The Agent Bus Pane is v0.1.
- No provider status checks. The Provider Status Pane is v0.1.

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

## Known v0 limitation

The `Coding-agent benchmark` button will run but cannot fully score the
TypeScript scenarios — the harness expects `scripts/run_typescript_debug_scenario.cjs`
which does not exist yet. See the spec's "Immediate Technical Debt" section.
