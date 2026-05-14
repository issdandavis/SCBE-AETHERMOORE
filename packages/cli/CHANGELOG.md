# Changelog

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
