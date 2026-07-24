# Governed Task Package Release Checkpoint

Date: 2026-07-24

## Scope

This change connects the local Clay Parallel Task Lab to the four public SCBE
packages through one fail-closed task-run contract:

| Package | Previous | Prepared |
| --- | ---: | ---: |
| `scbe-aethermoore` | 4.2.1 | 4.3.0 |
| `scbe-agent-bus` | 0.4.1 | 0.5.0 |
| `scbe-aethermoore-cli` | 4.4.0 | 4.5.0 |
| `scbe-polly-pad-cli` | 0.1.0 | 0.2.0 |

No npm or PyPI publication was performed.

## Contract

- Schema: `scbe.governed-task-run.v1`
- Completed output with citations remains `review_required`.
- Completed output without citations becomes `failed_evidence_check`.
- Failed and cancelled runs remain negative examples.
- Every disposition keeps `do_not_promote_to_fact: true`.
- Agent Bus and Polly reject public task endpoints by default. Loopback,
  RFC1918, link-local, and Tailscale address literals are allowed. Public
  routing requires explicit opt-in and HTTPS.
- The core package can canonicalize, SHA-256 seal, and verify task records.

## Package Surfaces

- Core: `scbe-aethermoore/agentic`
- Agent Bus: `TaskApiClient`, Zod schemas, parsing, polling, basis, cancel,
  group, and interaction methods
- CLI: `scbe-task`
- Polly: `polly task submit`, `status`, and `wait`, with the remote
  disposition persisted in the local pad and audit chain

## Verification

- Core build: passed.
- Core Vitest: 213 files passed, 3 skipped; 6,725 tests passed, 20 skipped.
- Python version regression: 3 passed.
- Agent Bus build: passed.
- Agent Bus Vitest: 28 files and 708 tests passed.
- CLI governed-task tests: 3 passed.
- Polly governed-task tests: 4 passed.
- Node syntax checks: 6 files passed.
- New-file Prettier check: passed.
- `git diff --check`: passed.
- Scoped secret-pattern scan: zero findings.
- Four `npm pack --dry-run --json --ignore-scripts` checks confirmed the new
  compiled/client/CLI files are present. No tarball was created.
- Compiled core and Agent Bus exports loaded with the same schema.

The full CLI suite reported 171 passes, 3 skips, and 7 failures in untouched
desktop, browser, React, and TUI lanes. The checkout intentionally did not
install their missing React/Ink or Playwright browser runtime just to alter the
machine for this package change.

The full Polly suite reported 39 passes and one terminal-router fixture
failure. That same failure was reproduced on the untouched base commit
`5cd27da7b`, proving it is not caused by this change.

## Live Evidence

- Existing Clay Spatial service on `127.0.0.1:8765` was identified and left
  untouched.
- Clay Parallel Task Lab on `127.0.0.1:8766` returned healthy capabilities.
- Live CLI run:
  `trun_e6988f623b554fc0a5a86ea4a04673c0`
- The live no-evidence claim completed with:
  `failed_evidence_check`, `negative_example: true`, and
  `do_not_promote_to_fact: true`.

## Release Order

Publish only after explicit authorization, in this order:

1. `scbe-aethermoore@4.3.0`
2. `scbe-agent-bus@0.5.0`
3. `scbe-aethermoore-cli@4.5.0`
4. `scbe-polly-pad-cli@0.2.0`

Agent Bus must precede the CLI because `scbe-task` consumes its new exported
client. Re-run each package dry-run and authentication check immediately before
publication.

## Post-Merge CI Closure

The repository's auto-merge workflow merged the feature PR before its format
jobs completed. The follow-up exposed a real tooling mismatch: root CI resolved
Prettier 3.9.5 while `packages/agent-bus` resolved 3.8.3, causing two formatter
workflows to rewrite the same syntax in opposite directions.

- PR #2712 merged the governed task package surfaces.
- PR #2714 retained the first automated formatter output.
- PR #2715 pinned Agent Bus to Prettier 3.9.5, restored one shared format, and
  merged as main commit `d40f6f2ac`.
- Both Prettier jobs, root lint, Node 20 tests, Python component tests, unit
  tests, product delivery smoke, no-fakes, coherence, and policy gates passed
  after the version alignment.
- Agent Bus also passed a clean LF-checkout verification locally: full-package
  format check, build, and 708 tests.

Package publication remains intentionally unperformed.
