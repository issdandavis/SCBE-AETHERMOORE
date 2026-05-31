# scbe-agent-bus

Typed Node surface over the SCBE governed event runner.

Routes AI, human, and automation events through the SCBE harmonic-wall pipeline and
returns typed result envelopes. Includes a local HTTP backend, a terminal UI, a full
workspace audit-chain CLI, and TypeScript APIs for building governed agentic workflows.

**Source:** [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/packages/agent-bus)
**Issues:** [github.com/issdandavis/SCBE-AETHERMOORE/issues](https://github.com/issdandavis/SCBE-AETHERMOORE/issues)

---

## What is SCBE?

**SCBE** (Sacred Tongues governance system — repository identifier: SCBE-AETHERMOORE) is an AI safety
and governance framework built around hyperbolic geometry. Its core insight: adversarial behavior
costs exponentially more the further it drifts from safe operation.

The pipeline has 14 layers. The governance decision comes from Layer 12, the **harmonic wall**:

```
H(d, pd) = 1 / (1 + φ·d_H + 2·pd)

  d_H  — hyperbolic distance from safe-operation origin (0–1)
  pd   — pattern drift from declared intent (0–1)
  φ    — golden ratio (1.618), making costs super-linear as drift grows
```

| Score     | Tier       | Action                           |
| --------- | ---------- | -------------------------------- |
| ≥ 0.60    | ALLOW      | Execute — minimal audit overhead |
| 0.30–0.59 | QUARANTINE | Execute + write audit receipt    |
| < 0.30    | DENY       | Block — never executed           |

Danger patterns (fork bombs, `curl\|bash`, `rm -rf /`, disk writes) inject structural pattern drift
that forces DENY regardless of `d_H` alone.

The six **Sacred Tongue** registers (Kor'aelin/Avali/Runethic/Cassisivadan/Umbroth/Draumric) give each
task a semantic home — not cosmetic names but phi-weighted dimensions that determine routing, cost
scaling, and governance posture.

New to the product framing? Start with
[Free AI Agent Board](../../docs/product/FREE_AI_AGENT_BOARD.md) — use free, local, or BYOK models
as proposal engines while SCBE validates legal moves, executes through the agent bus, and records receipts.

---

## Install

```bash
npm i scbe-agent-bus
```

Node 20+ required.

### Python governance SDK

If you're working in Python, the same L12 harmonic wall is available as a standalone package — no Node required:

```bash
pip install scbe-govern
```

```python
from scbe_govern import SCBEGovern

gov = SCBEGovern()  # inline mode — zero server, zero deps

result = gov.check("rm -rf /opt/data")
print(result.tier, result.score)  # DENY  0.233

# Raise on DENY, pass through on ALLOW/QUARANTINE
safe = gov.guard("cat README.md")
```

Inline mode runs the full harmonic wall locally. Remote mode (`SCBEGovern(base_url=..., api_key=...)`) points at any running SCBE bridge. Source and docs: [pypi.org/project/scbe-govern](https://pypi.org/project/scbe-govern/).

---

## Quick start

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Summarize the changed training files.',
  taskType: 'review',
  privacy: 'local_only',
});

if (!result.ok) {
  console.error('event failed:', result.exit_code, result.stderr_tail);
} else {
  console.log(result.result);
}
```

---

## Task types

`taskType` controls which governance posture and tool formation the bus uses:

| taskType     | What it does differently                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------- |
| `coding`     | Routes through the CA (Cassisivadan) compute formation; compiler and build tools prioritized    |
| `review`     | Routes through AV (Avali) observation formation; read-only tools, higher QUARANTINE sensitivity |
| `research`   | Routes through AV scout formation; web, document, and cross-reference tools unlocked            |
| `governance` | Routes through RU (Runethic) policy formation; audit receipt mandatory, DENY threshold stricter |
| `training`   | Routes through CA formation with data-pipeline tools; dataset and manifest tools prioritized    |
| `general`    | Default formation; balanced posture, no formation-specific tool preference                      |

If you pass an unrecognized string, the bus normalizes it to `general`.

---

## Error handling

`result.ok` is `false` whenever the underlying CLI exits non-zero, encounters a governance DENY, or
the requested tool is not registered. Always check it:

```ts
const result = await runEvent({
  task: 'delete all files in /etc',
  taskType: 'governance',
  privacy: 'local_only',
});

if (!result.ok) {
  // result.exit_code  — numeric exit code (null if spawn failed)
  // result.stderr_tail — last ~500 bytes of stderr
  // result.result     — null on hard failure, partial data on soft failure
  console.error(`task failed [exit ${result.exit_code}]: ${result.stderr_tail}`);
}
```

Unknown tool failure:

```ts
const result = await runEvent({ task: 'do something', tool: 'nonexistent_tool' });
// result.ok === false
// result.stderr_tail === "unknown tool: 'nonexistent_tool' is not registered"
```

`runBatch` stops on the first failure by default. Pass `continueOnError: true` to collect all results:

```ts
const rows = await runBatch(events, { continueOnError: true });
const failed = rows.filter((r) => !r.ok);
```

---

## End-to-end workflow: event bus + workspace

A common pattern: dispatch governed tasks against files inside an auditable workspace.

```ts
import {
  createAgentWorkspace,
  ingestIntoAgentWorkspace,
  exportAgentWorkspace,
  verifyAgentWorkspaceExport,
  lineageAgentWorkspace,
} from 'scbe-agent-bus';
import { runEvent } from 'scbe-agent-bus';
import { writeFileSync } from 'fs';

// 1. Create a workspace with a six-folder audit structure
const ws = createAgentWorkspace({ hint: 'release-review' });

// 2. Drop a file into the workspace inbox (sha256 provenance receipt written)
const ingest = ingestIntoAgentWorkspace({
  workspaceRoot: ws.workspace_root,
  sourcePath: './CHANGELOG.md',
});

// 3. Write the review task file into the working folder
writeFileSync(
  `${ws.workspace_root}/10_work/review_task.txt`,
  'Review CHANGELOG for completeness and governance compliance.'
);

// 4. Dispatch a governed review event
const review = await runEvent({
  task: 'Review CHANGELOG.md in 10_work for completeness.',
  taskType: 'review',
  privacy: 'local_only',
});

if (!review.ok) throw new Error(`review failed: ${review.stderr_tail}`);

// 5. Export the workspace (sha256 manifest anchored in export receipt)
const exp = exportAgentWorkspace({ workspaceRoot: ws.workspace_root });

// 6. Verify the export (detects sha256_mismatch / missing_file / extra_file)
const verify = verifyAgentWorkspaceExport({ exportPath: exp.export_path });
if (!verify.ok) throw new Error('workspace tampered after review');

// 7. Read the full audit trail
const lineage = lineageAgentWorkspace({ workspaceRoot: ws.workspace_root });
console.log(lineage.verify_count, lineage.failed_verifies, lineage.audit_health);
```

---

## Testing and mocking

`runEvent` and `runBatch` spawn the SCBE system CLI synchronously. In test environments you have
two options:

**Option 1 — use `dispatchProvider: 'offline'`** (default when no `SCBE_API_KEY` is set).
No network calls, no model calls. The bus evaluates governance locally and returns a structured
result envelope. Safe to run in CI without any credentials:

```ts
const result = await runEvent({
  task: 'check manifest integrity',
  taskType: 'governance',
  privacy: 'local_only',
  dispatchProvider: 'offline', // explicit — this is already the default
});
```

**Option 2 — mock the runner in `runBoardedChain`** (used in the board-fields integration tests).
Pass a custom `runEvent` implementation via the `options` argument:

```ts
import { runBoardedChain } from 'scbe-agent-bus';

const mockRunner =
  (ok = true) =>
  async () => ({
    ok,
    exit_code: ok ? 0 : 1,
    stderr_tail: '',
    result: ok ? { output: 'mocked' } : null,
    schema_version: 'scbe-agentbus-node-result-v1',
    event_index: 1,
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    event: { task_sha256: null, task_chars: 0, series_id: '', operation_command_chars: 0 },
  });

const result = await runBoardedChain(myChain, board, { runEvent: mockRunner(true) });
```

---

## Concurrency and performance

`runBatch` is sequential by default. `runFanOut` (lower-level) runs up to `concurrency` events in
parallel:

```ts
import { runFanOut } from 'scbe-agent-bus';

const rows = await runFanOut(events, {
  concurrency: 8, // default: 4; events beyond this queue
  continueOnError: true,
});
```

The local HTTP server (`serve`) is single-process Node. It does not enforce per-client rate limiting
— it is designed for local developer use, not multi-tenant load. For production fan-out, run multiple
server instances behind a load balancer and pass `baseUrl` per shard.

---

## Crash recovery and audit chain durability

The workspace audit chain is file-backed JSONL in `20_receipts/`. If the local server crashes
mid-task, no receipt corruption occurs because:

1. Each receipt is written atomically as a complete JSON object on a single line.
2. `workspace verify` re-hashes every file from disk and compares against `manifest.json` — it does
   not depend on any in-memory state.
3. `workspace lineage` reads the `20_receipts/` folder directly — there is no database to corrupt.

After a crash, resume by running `workspace verify --all` to establish current integrity before
dispatching any new events into that workspace.

---

## Security and the governed pipeline

The harmonic wall is deterministic and runs entirely in the local process — no model call needed.
What it checks:

- **Structural danger patterns**: fork bombs, disk writes (`>/dev/sda`), reverse shells (`nc -e /bin/sh`),
  `rm -rf /`-class commands, `curl|bash` / `wget|bash` injection — these are hard-coded and cannot
  be bypassed by rephrasing.
- **Semantic distance**: the command's executable is mapped to a role (observe/compute/transmit/repair
  etc.) and the role's `reactivity` property becomes `d_H`. High-reactivity operations (transmit,
  deploy) carry higher `d_H` than low-reactivity ones (observe, report).
- **Pattern drift**: deviation between declared intent and actual command increases `pd`, compressing
  the score toward DENY.

What it does **not** do:

- It does not execute AI inference to evaluate content.
- It does not guarantee that QUARANTINE commands are safe — QUARANTINE executes and audits.
- It does not sandbox the subprocess. DENY is the only hard block; ALLOW/QUARANTINE both execute.

---

## `SCBE_API_KEY` auth model

`SCBE_API_KEY` gates **hosted dispatch** — provider-backed execution where SCBE manages the model
call, stores signed reports, and charges credits. Without it the bus defaults to `offline` mode (no
model calls, governance-only) for all events.

| Mode                | Requires                 | What runs                                            |
| ------------------- | ------------------------ | ---------------------------------------------------- |
| `offline` (default) | nothing                  | governance evaluation only, no model                 |
| `local`             | local Ollama or provider | governance + local model inference                   |
| hosted              | `SCBE_API_KEY`           | governance + cloud provider + signed report delivery |

Keys are issued after credit purchase at the hosted run intake page. There is no scoping system yet
— a key grants full hosted dispatch capacity. To revoke, contact support and purchase a new key.
Key rotation: set `SCBE_API_KEY` to the new value in your environment; the old key becomes invalid
immediately upon revocation.

```bash
export SCBE_API_KEY=scbe_...   # issued at aethermoore.com/SCBE-AETHERMOORE/hosted-run.html
scbe-agent-bus send --task "..." --dispatch-provider groq --json
```

---

## CLI reference

```
scbe-agent-bus serve --port 8787
scbe-agent-bus ui --base-url http://127.0.0.1:8787
scbe-agent-bus send --task "review changed files" --task-type review --json
scbe-agent-bus tools audit --json
scbe-agent-bus compass plan --task "write a YouTube script and review upload metadata" --json
scbe-agent-bus compass models --json
scbe-agent-bus compass board --task "cross-language compiler with Pazaak checks" --json
scbe-agent-bus pipeline run --intent "verify then publish release notes" --governed-state --session-id release --json
scbe-agent-bus pipeline state --session-id release --json
scbe-agent-bus health --base-url http://127.0.0.1:8787 --json
scbe-agent-bus workspace new --hint customer-smoke --json
scbe-agent-bus workspace ingest --workspace-root <path> --source-path <file> --json
scbe-agent-bus workspace export --workspace-root <path> --json
scbe-agent-bus workspace import --export-path <path> --json
scbe-agent-bus workspace verify --export-path <path> --json
scbe-agent-bus workspace verify --all --workspace-root <path> --json
scbe-agent-bus workspace lineage --workspace-root <path> --json
scbe-agent-bus workspace report --workspace-root <path> --json
scbe-agent-bus upgrade
```

---

## Backend

```bash
scbe-agent-bus serve --port 8787
```

Routes:

- `GET /health`
- `POST /v1/events` — single event (same shape as `runEvent`)
- `POST /v1/batch` — array of events; accepts `concurrency` field

The server is synchronous request/response — no webhook or event streaming. Long-running tasks
block the connection until they complete. For async patterns, pass `enqueue: true` via the API:

```ts
const result = await runEvent(event, { enqueue: true });
// result.exit_code === 202
// result.result.run_id — poll or inspect queue for completion
```

---

## Terminal UI

```bash
scbe-agent-bus ui --base-url http://127.0.0.1:8787
```

Interactive prompt that health-checks the backend and sends governed `local_only` tasks
through the bus. Does not expose shell execution.

---

## Send (one-shot CLI dispatch)

```bash
scbe-agent-bus send \
  --task "review the changed training files" \
  --task-type review \
  --privacy local_only \
  --json
```

Flags: `--task`, `--task-type` (`coding|review|research|governance|training|general`),
`--privacy` (`local_only|remote_allowed`), `--budget-cents`, `--dispatch-provider`,
`--operation-command`, `--series-id`, `--json`.

Non-local providers require `SCBE_API_KEY` — see `upgrade`.

---

## Patent-Aligned Harness Checks

The tool registry is the agentic harness surface. Use `tools audit` after adding
or changing tools:

```bash
SCBE_BUS_TOOLS=./tools.json scbe-agent-bus tools audit --json
```

The audit reports:

- total tool count,
- patent-facing surface counts,
- missing descriptions,
- required live environment variables,
- and whether any tool is structurally invalid.

Current surfaces include hyperbolic governance, bijective transport, runtime
persistence, tamper detection, research evidence, video lattice, agent harness,
and atomic tokenizer readiness.

## SCBE Compass CLI Front Door

Compass is the SCBE-native task-routing front end for the CLI. It classifies
the task into a formation, names the right bus tools, lists adapter slots, and
shows local/free-tier/paid model lanes with their real cost boundaries.

```bash
scbe-agent-bus compass plan \
  --task "cross-language compile this operation and prepare YouTube notes" \
  --json

scbe-agent-bus compass models --json
scbe-agent-bus compass tree --json
scbe-agent-bus compass board --task "cross-language compiler with Pazaak checks" --json
```

Core formations:

- `forge`: cross-language compiler, binary/hex transport, tokenizer checks.
- `scribe`: writing/manuscript/article review and packaging.
- `broadcast`: YouTube/video upload preparation, review, and unlisted release.
- `council`: local/free-tier/paid model routing with cost and privacy gates.
- `scout`: research and evidence-gathering tools.
- `field`: general governed execution.

Model lane wording is deliberately strict:

- `offline`: no model call.
- `local-free-after-install`: no provider bill after install, but uses local
  hardware, electricity, and installed model capacity.
- `remote-free-tier-limited`: provider-hosted free tier with quotas/rate limits.
- `paid-remote`: requires explicit budget approval.

---

## Agentic OS Benchmark

Run the local benchmark after build:

```bash
npm run build
npm run benchmark:agentic-os
```

Reports are written to `docs/benchmarks/agentic_os_cli_benchmark.json` and
`docs/benchmarks/agentic_os_cli_benchmark.md`.

---

## Governed Pipeline State

The GeoSeal pipeline can run with a durable trajectory gate:

```bash
scbe-agent-bus pipeline run \
  --intent "verify changed files before publishing" \
  --governed-state \
  --session-id release-lane \
  --json
```

The state starts conservatively with `observe`, `read`, and `verify` as reachable
move classes. Higher-risk moves only become reachable after prerequisite moves
are accepted:

- `write` after recent observe/read/verify/write evidence,
- `network` after verify evidence,
- `deploy` after verify plus network evidence,
- destructive moves remain unreachable through this gate.

---

## Workspace CLI

Workspaces are temporary, auditable working areas with a six-folder shape:

| Folder        | Purpose                                           |
| ------------- | ------------------------------------------------- |
| `00_inbox`    | Raw drops, uploads, imports, unclassified files   |
| `10_work`     | Active editable working files                     |
| `20_receipts` | Governance receipts, hashes, run records          |
| `30_exports`  | Customer-ready packets and handoff bundles        |
| `40_refs`     | Non-secret reference files and source notes       |
| `90_tmp`      | Scratch files, deleted after offload verification |

Every workspace command writes a structured JSON receipt so the full audit chain is
replayable without re-running any model. Receipts are written atomically to
`20_receipts/` — a server crash cannot corrupt a receipt that was already written.

### `workspace new`

```bash
scbe-agent-bus workspace new --hint customer-smoke --json
```

Creates `.aethermoor-bus/workspaces/<id>/` with the six-folder shape and writes
`SCBE_WORKSPACE_READY=1` into `20_receipts/workspace.json`.

### `workspace ingest`

```bash
scbe-agent-bus workspace ingest \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --source-path /path/to/file.csv \
  --rename report.csv \
  --json
```

Copies a file into `00_inbox/` with a sha256 provenance receipt. Source and
destination hashes must match — mismatch throws.

### `workspace export`

```bash
scbe-agent-bus workspace export \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --out delivery-v1 \
  --json
```

Copies `00_inbox`, `10_work`, `20_receipts`, `40_refs` into
`30_exports/<export-id>/`, writes a `manifest.json` with per-file sha256, and
anchors the manifest's sha256 in the export receipt.

### `workspace verify`

```bash
# Single export
scbe-agent-bus workspace verify \
  --export-path .aethermoor-bus/workspaces/<id>/30_exports/<eid> \
  --json

# All exports in a workspace
scbe-agent-bus workspace verify \
  --all \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --json
```

Re-hashes every file, checks against `manifest.json`. Detects four tamper classes:
`sha256_mismatch`, `bytes_mismatch`, `missing_file`, `extra_file`. Exits 1 on any
failure — usable as a CI gate. Pass `--no-persist` for read-only CI checks that
must not mutate the workspace.

### `workspace lineage`

```bash
scbe-agent-bus workspace lineage \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --json
```

Walks `20_receipts/`, classifies each receipt, and returns the chronological audit
chain plus summary counters: `formation_count`, `ingest_count`, `export_count`,
`verify_count`, `import_count`, `trap_dispatch_count`, `trap_redirect_count`,
`failed_verifies`, `unverified_exports[]`. Read-only — never writes.

### `workspace report`

```bash
scbe-agent-bus workspace report \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --json
```

Operator dashboard: folder file/byte counts, lineage summary, workspace metadata,
and an `audit_health` color (`green` = all exports verified clean, `amber` =
unverified exports present, `red` = any failed verify).

---

## TypeScript API

### `runEvent(event, options?)`

Send one governed event. Spawns the SCBE CLI synchronously (blocking). Returns when
the task completes or the CLI exits.

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Check for drift in the training manifest.',
  taskType: 'governance',
  privacy: 'local_only',
});

// result shape:
// {
//   ok: boolean,
//   exit_code: number | null,
//   stderr_tail: string,       // last ~500 bytes of stderr
//   result: unknown | null,    // parsed JSON stdout on success; null on hard failure
//   started_at: string,        // ISO timestamp
//   finished_at: string,
//   schema_version: 'scbe-agentbus-node-result-v1',
//   event_index: number,
//   event: { task_sha256, task_chars, series_id, operation_command_chars }
// }
```

Options:

| Option            | Type      | Default         | Description                                                   |
| ----------------- | --------- | --------------- | ------------------------------------------------------------- |
| `repoRoot`        | `string`  | `process.cwd()` | Root path for CLI resolution                                  |
| `python`          | `string`  | `'python'`      | Python executable used by governed shell commands             |
| `enqueue`         | `boolean` | `false`         | Return immediately with a `run_id` instead of blocking        |
| `continueOnError` | `boolean` | `false`         | (batch only) do not stop on first failure                     |
| `concurrency`     | `number`  | `4`             | (fanOut only) max parallel events                             |
| `baseUrl`         | `string`  | —               | If set, POSTs to a running server instead of spawning locally |

### `runBatch(events, options?)`

Send a sequence of events. Stops on first failure unless `continueOnError: true`.

```ts
import { runBatch } from 'scbe-agent-bus';

const rows = await runBatch(
  [
    { task: 'step one', taskType: 'coding', privacy: 'local_only' },
    { task: 'step two', taskType: 'review', privacy: 'local_only' },
  ],
  { continueOnError: true }
);

const failed = rows.filter((r) => !r.ok);
if (failed.length > 0) {
  console.error(`${failed.length} steps failed`);
}
```

### `runFanOut(events, options?)`

Like `runBatch` but runs up to `concurrency` events in parallel:

```ts
import { runFanOut } from 'scbe-agent-bus';

const rows = await runFanOut(events, { concurrency: 8 });
```

### `startAgentBusServer(options?)` / `postAgentBusEvent(event, options?)`

Embed the server in your own Node process:

```ts
import { startAgentBusServer, postAgentBusEvent } from 'scbe-agent-bus';

const handle = await startAgentBusServer({ port: 9000 });
const result = await postAgentBusEvent(
  { task: 'review', taskType: 'review', privacy: 'local_only' },
  { baseUrl: handle.url }
);
await handle.close();
```

### Workspace API

All workspace functions mirror the CLI commands and return typed receipts:

```ts
import {
  createAgentWorkspace,
  ingestIntoAgentWorkspace,
  exportAgentWorkspace,
  verifyAgentWorkspaceExport,
  verifyAllAgentWorkspaceExports,
  importAgentWorkspace,
  lineageAgentWorkspace,
  reportAgentWorkspace,
} from 'scbe-agent-bus';

const ws = createAgentWorkspace({ hint: 'smoke-test' });
const ingest = ingestIntoAgentWorkspace({
  workspaceRoot: ws.workspace_root,
  sourcePath: './data.csv',
});
const exp = exportAgentWorkspace({ workspaceRoot: ws.workspace_root });
const verify = verifyAgentWorkspaceExport({ exportPath: exp.export_path });
const lineage = lineageAgentWorkspace({ workspaceRoot: ws.workspace_root });
// lineage.unverified_exports → exports without a passing verify receipt
// lineage.trap_dispatch_count / trap_redirect_count → governed inputs that hit DENY
const report = reportAgentWorkspace({ workspaceRoot: ws.workspace_root });
// report.audit_health → 'green' | 'amber' | 'red'
```

---

## Current limitations

- **Synchronous only**: `runEvent` and the HTTP backend are blocking request/response. There is no
  webhook or push notification system yet. For async patterns use `enqueue: true`.
- **No per-key scoping**: `SCBE_API_KEY` is a flat credential. Role-based scoping is planned but not
  shipped.
- **Local server has no rate limiting**: designed for single-developer local use. Don't expose port
  8787 to the public internet.
- **No LangChain/LlamaIndex adapters (Node)**: these are on the roadmap. Today, integration means calling
  `runEvent` from within a tool or agent node. The JSON envelope is easy to parse. For Python LangChain
  wrapping, use [`scbe-govern`](https://pypi.org/project/scbe-govern/) which ships a `govern_tool()` wrapper.
- **Credits via Ko-fi**: the top-up link is `ko-fi.com/izdandavis`. This is a small independent
  project — credits are pay-as-you-go and manually issued. Not the model used by large SaaS tools,
  but it is honest about what the project is today.

---

## Upgrade / hosted dispatch

```bash
scbe-agent-bus upgrade
```

Local routing is free. Hosted runs require `SCBE_API_KEY`.

```bash
export SCBE_API_KEY=your-key   # issued after credit purchase
scbe-agent-bus send --task "..." --dispatch-provider groq --json
```

- Hosted run intake: https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html
- Service credits: https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html
- Credit top-up: https://ko-fi.com/izdandavis

---

## Contributing

Source is at [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE).
Package lives under `packages/agent-bus/`.

To report a vulnerability, open a GitHub issue with the `security` label. For sensitive disclosures,
email issdandavis@gmail.com directly. There is no formal bug bounty program — this is an independent
project.

To contribute: fork, branch off `main`, open a PR. Run `npm test` before opening. CI runs
TypeScript build + lint + tests on every PR. Python changes need `PYTHONPATH=. python -m pytest tests/ -x -q`.

---

## Notes

- The repo-local runner is always the source of truth.
- Use `privacy: "local_only"` for sensitive data — remote dispatch must be explicit.
- `trap_dispatch` lineage entries expose `gate_decision` and `redirect_emitted` so
  compliance reviewers can audit adversarial inputs without reading the raw envelope.
- Verify receipts persist by default so `lineage` always reflects the latest state.
  Pass `--no-persist` for read-only CI checks that must not mutate the workspace.
