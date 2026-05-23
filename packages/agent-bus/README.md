# scbe-agent-bus

Typed Node surface over the SCBE governed event runner.

Routes AI, human, and automation events through the SCBE harmonic-wall pipeline and
returns typed result envelopes. Includes a local HTTP backend, a terminal UI, a full
workspace audit-chain CLI, and TypeScript APIs for building governed agentic workflows.

New to SCBE? Start with the product framing: [Free AI Agent Board](../../docs/product/FREE_AI_AGENT_BOARD.md) — use free, local, or BYOK models as proposal engines while SCBE validates legal moves, executes through the agent bus, and records receipts.

## Install

```bash
npm i scbe-agent-bus
```

## Quick start

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Summarize the changed training files.',
  taskType: 'review',
  privacy: 'local_only',
});

console.log(result.ok, result.result);
```

## CLI reference

```
scbe-agent-bus serve --port 8787
scbe-agent-bus ui --base-url http://127.0.0.1:8787
scbe-agent-bus send --task "review changed files" --task-type review --json
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
- `POST /v1/events`
- `POST /v1/batch`

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

## Workspace CLI

Workspaces are temporary, auditable working areas with a six-folder shape:

| Folder | Purpose |
|---|---|
| `00_inbox` | Raw drops, uploads, imports, unclassified files |
| `10_work` | Active editable working files |
| `20_receipts` | Governance receipts, hashes, run records |
| `30_exports` | Customer-ready packets and handoff bundles |
| `40_refs` | Non-secret reference files and source notes |
| `90_tmp` | Scratch files, deleted after offload verification |

Every workspace command writes a structured JSON receipt so the full audit chain is
replayable without re-running any model.

### `workspace new`

```bash
scbe-agent-bus workspace new --hint customer-smoke --json
```

Creates `.aethermoor-bus/workspaces/<id>/` with the six-folder shape and writes
`SCBE_WORKSPACE_READY=1` into `20_receipts/workspace.json`.

Flags: `--root <parent-dir>`, `--hint <label>`, `--json`.

### `workspace ingest`

```bash
scbe-agent-bus workspace ingest \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --source-path /path/to/file.csv \
  --rename report.csv \
  --json
```

Copies a file into `00_inbox/` with a sha256 provenance receipt. Source and
destination hashes must match — mismatch throws. Closes the audit chain at the
entry point.

Flags: `--workspace-root`, `--source-path`, `--rename`, `--json`.

### `workspace export`

```bash
scbe-agent-bus workspace export \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --out delivery-v1 \
  --json
```

Copies `00_inbox`, `10_work`, `20_receipts`, `40_refs` into
`30_exports/<export-id>/`, writes a `manifest.json` with per-file sha256, and
anchors the manifest's sha256 in the export receipt. `30_exports` and `90_tmp`
are never exported.

Flags: `--workspace-root`, `--out <name>`, `--include <comma-separated>`, `--json`.

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

Re-hashes every file, checks against `manifest.json`, and re-anchors the manifest
against the export receipt. Detects four tamper classes: `sha256_mismatch`,
`bytes_mismatch`, `missing_file`, `extra_file`. Exits 1 on any failure — usable as
a CI gate. Persists a verify receipt so `lineage` picks it up automatically.

Flags: `--export-path` (single) or `--all --workspace-root` (batch), `--no-persist`,
`--json`.

### `workspace import`

```bash
scbe-agent-bus workspace import \
  --export-path .aethermoor-bus/workspaces/<id>/30_exports/<eid> \
  --target-root /other/dir \
  --hint restored \
  --json
```

Cold-restores a workspace from a previously-exported manifest. Runs verify FIRST and
refuses (exits 1) to import any export that fails any tamper class. The source's
`20_receipts/` is not replayed — the new workspace has its own audit chain anchored
by the import receipt's `source_manifest_sha256`.

Flags: `--export-path`, `--target-root`, `--hint`, `--json`.

### `workspace lineage`

```bash
scbe-agent-bus workspace lineage \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --json
```

Walks `20_receipts/`, classifies each receipt by schema, and returns the
chronological audit chain plus summary counters: `formation_count`, `ingest_count`,
`export_count`, `verify_count`, `import_count`, `trap_dispatch_count`,
`trap_redirect_count`, `failed_verifies`, `unverified_exports[]`.

Read-only — never writes.

### `workspace report`

```bash
scbe-agent-bus workspace report \
  --workspace-root .aethermoor-bus/workspaces/<id> \
  --json
```

Operator dashboard: folder file/byte counts, lineage summary, workspace metadata,
and an `audit_health` color (`green` = all exports verified clean, `amber` =
unverified exports present, `red` = any failed verify). Read-only.

---

## Upgrade / hosted dispatch

```bash
scbe-agent-bus upgrade
```

Local routing is free. Hosted runs (provider/model-backed, signed reports, stored
history) require `SCBE_API_KEY`. The `upgrade` command prints the intake path and
detects whether the key is currently set.

```bash
export SCBE_API_KEY=your-key   # issued after credit purchase
scbe-agent-bus send --task "..." --dispatch-provider groq --json
```

- Hosted run intake: https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html
- Service credits: https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html
- Credit top-up: https://ko-fi.com/izdandavis

Credits cover hosted capacity, report delivery, storage, and provider/model usage.
Billable provider/model cost is passed through with a 2–5% SCBE coordination fee.

---

## TypeScript API

### `runEvent(event, options?)`

Send one governed event. Spawns the SCBE system CLI synchronously.

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Check for drift in the training manifest.',
  taskType: 'governance',
  privacy: 'local_only',
});
// result.ok, result.result, result.exit_code, result.stderr_tail
```

### `runBatch(events, options?)`

Send a sequence of events. Stops on first failure unless `continueOnError: true`.

```ts
import { runBatch } from 'scbe-agent-bus';

const rows = await runBatch([
  { task: 'step one', taskType: 'coding', privacy: 'local_only' },
  { task: 'step two', taskType: 'review', privacy: 'local_only' },
]);
```

### `startAgentBusServer(options?)` / `postAgentBusEvent(event, options?)`

Embed the server in your own Node process.

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

All workspace functions mirror the CLI commands and return typed receipts.

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

// Create
const ws = createAgentWorkspace({ hint: 'smoke-test' });

// Ingest
const ingest = ingestIntoAgentWorkspace({
  workspaceRoot: ws.workspace_root,
  sourcePath: './data.csv',
});

// Export
const exp = exportAgentWorkspace({ workspaceRoot: ws.workspace_root });

// Verify (single)
const verify = verifyAgentWorkspaceExport({ exportPath: exp.export_path });

// Verify (all)
const verifyAll = verifyAllAgentWorkspaceExports({ workspaceRoot: ws.workspace_root });

// Import (cold-restore from an export)
const imported = importAgentWorkspace({ exportPath: exp.export_path });

// Lineage
const lineage = lineageAgentWorkspace({ workspaceRoot: ws.workspace_root });
// lineage.unverified_exports → exports without a passing verify receipt
// lineage.trap_dispatch_count / trap_redirect_count → governed inputs that hit DENY

// Report (dashboard)
const report = reportAgentWorkspace({ workspaceRoot: ws.workspace_root });
// report.audit_health → 'green' | 'amber' | 'red'
```

---

## Notes

- The repo-local runner remains the source of truth.
- `privacy: "local_only"` should be used for sensitive data.
- Remote dispatch must be explicit with `dispatchProvider` and a valid `SCBE_API_KEY`.
- Verify receipts persist by default so `lineage` always reflects the latest state;
  pass `--no-persist` for read-only CI checks that must not mutate the workspace.
- `trap_dispatch` lineage entries expose `gate_decision` and `redirect_emitted` so
  compliance reviewers can spot adversarial inputs without reading the raw envelope.
