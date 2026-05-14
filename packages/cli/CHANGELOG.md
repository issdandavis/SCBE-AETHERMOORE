# Changelog

## 4.3.14 - 2026-05-14

### Added

- **`scbe workspace import --export-path <path> [--target-root <dir>] [--hint <name>] [--json]`**: forwards to `scbe-agent-bus workspace import`. Cold-restore a workspace from a previously-exported manifest. Verifies the export FIRST and refuses (exit 1) any export that fails tamper-class checks — so the restored workspace is provably untampered. Records the source export's `manifest_sha256` as the new workspace's provenance anchor. Lineage classifies the result as `kind: 'import'`.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.8 → ^0.3.9` for the workspace import command.

## 4.3.13 - 2026-05-14

### Added

- **`scbe trap-redirect [--input <text>] [--file <path>] [--json]`**: input-side companion to `scbe contract scan --emit-redirect-prompt`. Takes prompt text from `--input`, `--file`, or stdin; runs through the governance proxy's `shouldPreBlock` + `buildRedirectPrompt`; emits `SCBE_TRAP_REDIRECT=1` when a SCONE-tagged rule fires DENY along with the defensive audit prompt the production proxy would forward to the model in place of the attacker's text. Operator inspector — does not dispatch anywhere, never quotes the attacker prompt. Useful for testing prompts before they go live and for auditing what redirect would have been emitted for a given input. Schema `scbe.trap_redirect.v1`. Source-checkout required.

## 4.3.12 - 2026-05-14

### Added

- **`scbe workspace report --workspace-root <path> [--json]`**: forwards to `scbe-agent-bus workspace report`. Operator dashboard: per-folder file/byte counts, lineage summary (formation/ingest/export/verify counts + unverified exports + failed verifies), workspace metadata, and an `audit_health` color (`green` / `amber` / `red`). Read-only.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.7 → ^0.3.8` for the workspace report command.

## 4.3.11 - 2026-05-14

### Added

- **`scbe workspace ingest --workspace-root <path> --source-path <file> [--rename <name>] [--json]`**: forwards to the new `scbe-agent-bus workspace ingest`. Copies any external file into `<workspace>/00_inbox/` with a sha256 receipt at `<workspace>/20_receipts/ingest-<utc-ts>-<basename>.json`. Closes the audit chain at intake: every file in the workspace now has a provenance receipt the `scbe workspace lineage` walker can surface. Receipt flag: `SCBE_WORKSPACE_INGEST=1`.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.6 → ^0.3.7` for the workspace ingest command.

## 4.3.10 - 2026-05-14

### Added

- **`scbe workspace verify --all --workspace-root <path>`**: forwards to the new `scbe-agent-bus workspace verify --all`. One call verifies every export under `<workspaceRoot>/30_exports/`, persists individual verify receipts (so lineage updates), and emits `SCBE_WORKSPACE_VERIFY_ALL_PASS=1` only when every export passes. Exit code 1 on any failure for CI gating.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.5 → ^0.3.6` for the batch verify command.

## 4.3.9 - 2026-05-14

### Changed

- **`scbe workspace verify` now persists by default**: forwards to `scbe-agent-bus workspace verify`, which writes the verify receipt into `<workspace>/20_receipts/verify-<export-id>-<utc-ts>.json`. `scbe workspace lineage` automatically picks it up. Use `--no-persist` to opt out for ad-hoc local audits or read-only CI checks. The output text now shows `Receipt: <path>` or `Receipt: <not persisted>`.
- **Bumped `scbe-agent-bus` dependency**: `^0.3.4 → ^0.3.5` for the verify persistence change.

## 4.3.8 - 2026-05-14

### Added

- **`scbe workspace lineage --workspace-root <path> [--json]`**: forwards to the new `scbe-agent-bus workspace lineage`. Walks `<workspace>/20_receipts/` and emits the full audit chain — formation receipt + every export + every verify — in chronological order, plus summary counts and an `unverified_exports[]` list (exports without a matching verify). Receipt flag: `SCBE_WORKSPACE_LINEAGE=1`. Read-only.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.3 → ^0.3.4` for the workspace lineage command.

## 4.3.7 - 2026-05-14

### Added

- **`scbe workspace verify --export-path <path> [--json]`**: forwards to the new `scbe-agent-bus workspace verify`. Re-hashes every file in an exported workspace and verifies against `manifest.json`, plus the manifest's own sha256 against the export receipt anchor. Emits `SCBE_WORKSPACE_VERIFY_PASS=1` on a clean chain; exit code 1 on any tamper (so CI can gate on it). Detects sha256 mismatches, byte-count mismatches, missing files, and extra files not in the manifest.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.2 → ^0.3.3` for the workspace verify command.

## 4.3.6 - 2026-05-14

### Added

- **`scbe contract scan <file.sol> [--json] [--fail-on-finding]`**: SCONE-class static prefilter for Solidity smart contracts, motivated by the 2025 Anthropic Red SCONE-bench finding ($550.1M simulated exploits across 405 contracts; 2 zero-days; revenue doubling every 1.3 months). Checks four vulnerability classes — `missing_view_or_pure_modifier`, `missing_access_control_on_financial`, `unvalidated_critical_address`, `payable_without_value_check` — each mapping to a severity → SCBE tier (DENY / ESCALATE / QUARANTINE). Receipt schema `scbe.contract_scan.v1`; emits `SCBE_CONTRACT_SCAN_PASS=1` on clean, otherwise structured findings array with rule, severity, tier, line, function, detail. Honest about scope: regex/heuristic, NOT an AI-driven audit — cross-function and data-flow exploits will be missed. Backend at `scripts/contracts/scbe_contract_scan.py`; 8/8 pytest pass.

## 4.3.5 - 2026-05-14

### Added

- **`scbe workspace export --workspace-root <path> [--out <name>] [--include 00_inbox,10_work] [--json]`**: forwards to `scbe-agent-bus workspace export`. Copies the included subfolders of the workspace into `<workspace>/30_exports/<export-id>/`, writes a manifest with per-file sha256, and emits an `SCBE_WORKSPACE_EXPORT=1` receipt at `<workspace>/20_receipts/export-<export-id>.json` with the manifest sha256 as the chain-of-custody anchor. Default include = `00_inbox`, `10_work`, `20_receipts`, `40_refs`; `30_exports` (self) and `90_tmp` (scratch) are never exported.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.1 → ^0.3.2` for the workspace export command.

## 4.3.4 - 2026-05-14

### Added

- **`scbe workspace new [--hint <name>] [--json]`**: forwards to the agent-bus workspace formation command and emits `SCBE_WORKSPACE_READY=1` for a freshly-created local bus workspace.

### Changed

- **Bumped `scbe-agent-bus` dependency**: `^0.3.0 → ^0.3.1` for the workspace formation command.

## 4.3.3 - 2026-05-14

### Fixed

- **`scbe liboqs` outside a source checkout**: fresh npm installs now return a structured `SCBE_LIBOQS_PASS=0` source-checkout-required receipt instead of a raw Python `ModuleNotFoundError`.

## 4.3.2 - 2026-05-14

### Added

- **`scbe liboqs [--json]` native proof receipt**: runs the existing `src.crypto.pqc_liboqs` governance proof ladder plus an ML-KEM roundtrip and ML-DSA verify smoke. Emits `SCBE_LIBOQS_PASS=1` only when native liboqs is active and the smoke passes; lower proof tiers are reported honestly with `SCBE_LIBOQS_PASS=0`.

## 4.3.1 - 2026-05-14

### Changed

- **`scbe status` operator receipt**: expands the status payload with `SCBE_STATUS_READY=1`, Git branch/commit/dirty posture, latest GitHub Actions run summary when `gh` is available, provider posture, budget/hosted-run posture, workspace roots, and the last recorded governance gate. The command remains read-only and fail-soft.

## 4.3.0 - 2026-05-13

### Added

- **`scbe abacus run --d-h <v> --pd <v> [--json]`**: deterministic BigInt L12 harmonic wall + L13 tier scoring with bit-identical output across platforms. Bridges to `runGovernanceAbacus` from `scbe-aethermoore/harmonic`. JSON output schema `scbe_governance_abacus_v1` includes exact rational score (`num`/`den`), fixed-precision decimal, four-tier `tier`, and `trit` (+1 ALLOW, 0 uncertain, -1 DENY).
- **`scbe abacus help`** subcommand summarising the formula, tiers, and trit collapse.
- **Typo correction (suggest-only)**: unknown top-level commands within Levenshtein distance ≤ 2 of a known scbe command now print `scbe: '<typo>' is not a scbe command. Did you mean 'scbe <suggestion>'?` and exit 2. Unknown-but-not-close inputs fall through to the geoseal passthrough unchanged. No auto-execute — the user re-types deliberately.

### Changed

- **Bumped peer dependencies**: `scbe-aethermoore ^4.0.8 → ^4.1.0` (required for the `runGovernanceAbacus` export consumed by `scbe abacus`), `scbe-agent-bus ^0.2.1 → ^0.3.0` (required for the hosted-credential gate behind `scbe agent-bus send`).

## 4.2.0

- **`scbe flow plan|packetize|status|run-next|continue|report`** bridge to the operator-loop in `scripts/scbe-system-cli.py`.
- **`scbe agent-bus serve|send|ui|health|upgrade`** passthrough to the locally-installed `scbe-agent-bus` binary, with a clear error message if it's missing.
- **`scbe upgrade`** defers to `scbe-agent-bus upgrade` when present so the hosted-run guidance has a single source of truth.

## 4.1.5

- Earlier history not migrated into this CHANGELOG. See npm release history for prior versions.
