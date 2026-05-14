# Changelog

## 0.3.6

- **Batch verify command**: adds `scbe-agent-bus workspace verify --all --workspace-root <path> [--no-persist] [--json]`. Walks every subdirectory of `<workspaceRoot>/30_exports/` that contains a `manifest.json` and runs the single-export verifier on each, aggregating pass/fail counts. Emits `SCBE_WORKSPACE_VERIFY_ALL_PASS=1` only when every export passes. Individual verify receipts are still persisted under `20_receipts/` so `lineageAgentWorkspace()` reflects the new state. Exit code 1 on any failure so CI can gate on it.
- **New public API**: `verifyAllAgentWorkspaceExports(options)` (TypeScript), schema `aethermoor.bus.workspace_verify_all.v1` with per-export `results[]`.

## 0.3.5

- **Verify now persists a receipt by default**: `verifyAgentWorkspaceExport()` writes `<workspaceRoot>/20_receipts/verify-<export-id>-<utc-ts>.json` so that `lineageAgentWorkspace()` can pick it up without a manual stdout redirect. The on-disk JSON is bit-identical to the in-memory return value. Best-effort: if the receipts directory is missing or the write fails, the verify result is still returned and `receipt_path` is empty.
- **Opt-out flag**: `scbe-agent-bus workspace verify --no-persist` skips the write — useful for ad-hoc local audits or read-only CI checks that shouldn't mutate the workspace.
- **New field**: `AgentWorkspaceVerifyReceipt.receipt_path` (absolute path of the written receipt, or empty string when persistence was skipped). Schema version unchanged (`aethermoor.bus.workspace_verify.v1`).

## 0.3.4

- **Workspace lineage command**: adds `scbe-agent-bus workspace lineage --workspace-root <path> [--json]`. Walks `<workspace>/20_receipts/`, classifies each receipt by `schema_version` (formation / export / verify), and returns the chronological audit chain plus a summary: `formation_count`, `export_count`, `verify_count`, `failed_verifies`, and `unverified_exports[]` (exports without a matching verify receipt). Read-only — never writes to the workspace.
- **New public API**: `lineageAgentWorkspace(options)` (TypeScript), schema `aethermoor.bus.workspace_lineage.v1`. Receipt flag: `SCBE_WORKSPACE_LINEAGE=1`.
- **Use case**: compliance reviewer asks "has every export been audited?" — `unverified_exports` answers in one call.

## 0.3.3

- **Workspace verify command**: adds `scbe-agent-bus workspace verify --export-path <path> [--json]`. Walks the export folder, re-hashes every file, compares against `manifest.json`, and re-hashes `manifest.json` itself against the export receipt's `manifest_sha256` anchor. Detects four classes of tampering: `sha256_mismatch`, `bytes_mismatch`, `missing_file`, `extra_file`. Emits `SCBE_WORKSPACE_VERIFY_PASS=1` only when all per-file sha256s match AND the manifest sha256 chain anchor matches.
- **New public API**: `verifyAgentWorkspaceExport(options)` (TypeScript), with schema `aethermoor.bus.workspace_verify.v1`. Returns a structured receipt with `manifest_intact`, `mismatches[]`, claimed vs actual counts.
- **Exit code 1 on verify failure** so the command is usable in CI pipelines as a tamper gate.

## 0.3.2

- **Workspace export command**: adds `scbe-agent-bus workspace export --workspace-root <path> [--out <name>] [--include <comma-separated>] [--json]`. Copies the included folders (default `00_inbox`, `10_work`, `20_receipts`, `40_refs`) into `<workspace>/30_exports/<export-id>/`, writes a `manifest.json` with per-file sha256, and emits an `SCBE_WORKSPACE_EXPORT=1` receipt at `<workspace>/20_receipts/export-<export-id>.json` including the manifest's sha256 as a chain-of-custody anchor. `30_exports` (self) and `90_tmp` (scratch) are never exported.
- **New public API**: `exportAgentWorkspace(options)` (TypeScript), with schemas `aethermoor.bus.workspace_export.v1` and `aethermoor.bus.workspace_export_manifest.v1`.

## 0.3.1

- **Workspace formation command**: adds `scbe-agent-bus workspace new [--root <path>] [--hint <name>] [--json]`, creating the canonical `.aethermoor-bus/workspaces/<workspace-id>/` folder shape and writing a `SCBE_WORKSPACE_READY=1` receipt into `20_receipts/workspace.json`.

## 0.3.0

- **Hosted-credential gate on `send`**: requests with `--dispatch-provider` set to a non-local provider (anything other than `offline`, `local`, `ollama`, `local_only`, empty) now require `SCBE_API_KEY` in the environment. Without a key, `send` prints a hosted-intake notice (intake URL, service-credits URL, Ko-fi top-up URL, fee policy: provider/model cost passed through with 2-5% SCBE coordination fee) and exits with code 2.
- **New `upgrade` command**: prints the hosted-run path — service-credit policy, intake URL, credit top-up — and detects whether `SCBE_API_KEY` is set so the user knows whether hosted dispatch is currently unlocked.
- **Help text updated** to call out the local-first default and link the `upgrade` flow.
- **Documented constants**: `HOSTED_INTAKE_URL` (`https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html`), `SERVICE_CREDITS_URL` (`https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html`), `CREDIT_TOPUP_URL` (`https://ko-fi.com/izdandavis`).

## 0.2.2

- Restore the Node package source, TypeScript config, and generated `dist/`
  build path so fresh npm installs expose working API and CLI entrypoints.
- Keep the local-first server, terminal UI, send, and health commands
  self-contained for downloader smoke tests.

## 0.1.1

- Restore package source files on the release branch.
- Update TypeScript build settings for the current TypeScript 6 toolchain.

## 0.1.0

- Initial typed Node wrapper for the SCBE agent-bus pipe runner.
