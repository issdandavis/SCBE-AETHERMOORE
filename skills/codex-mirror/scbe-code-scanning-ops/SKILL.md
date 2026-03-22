---
name: scbe-code-scanning-ops
description: Operate GitHub code scanning and CodeQL remediation for SCBE repositories. Use when triaging code-scanning alerts, mapping alert classes to fix patterns, validating targeted regressions, or wiring dedicated CodeQL workflows and runbooks into the repo.
---

# SCBE Code Scanning Ops

Use this skill when GitHub code scanning or CodeQL becomes a real work lane instead of a vague security backlog.

Pair this skill with:
- `gh-fix-ci` when a PR or workflow run is already failing
- `scbe-github-sweep-sorter` when security alerts need to be split into owned lanes before implementation

## Quick Start

1. Fetch or load the alert surface.
   - Live GitHub: `python skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py --repo issdandavis/SCBE-AETHERMOORE`
   - Offline snapshot: `python skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py --alerts-file artifacts/security/code_scanning_alerts.json`
2. Read `references/solution-logic.md` for the fix class that matches the alert.
3. Patch the code and add at least one deterministic regression test.
4. Re-run targeted tests locally.
5. Push or open a PR, then let `.github/workflows/codeql-analysis.yml` rescan.

## Workflow

### 1. Collect

Get the live alerts first when possible. If GitHub returns `404`, treat that as one of:
- code scanning is not enabled for the repo
- the current token lacks the necessary security scope
- the authenticated account cannot read security alerts for that repo

Do not guess. Capture the error and continue with an offline alert snapshot if one exists.

### 2. Classify

Sort alerts by fix class, not just by file path.

Common classes in this repo:
- `incomplete-url-substring-sanitization`
- `bad-html-filtering-regexp`
- `uncontrolled-path-expression`
- `clear-text-logging-or-storage`
- `dom-text-reinterpreted-as-html`
- `missing-rate-limiting`
- `resource-exhaustion`
- `biased-crypto-random-mapping`

Use `references/solution-logic.md` for the concrete repair patterns.

### 3. Fix

Prefer structural fixes over suppressions.

Examples:
- Replace URL substring checks with parsed URL validation and normalized host allowlists.
- Replace HTML regex filtering with escaping or parser-driven logic.
- Replace dynamic path joins with fixed-root resolution and `relative_to` checks.
- Replace secret logging with redacted fingerprints.

### 4. Verify

Every code-scanning fix should add:
- one deterministic regression test for the bad input
- one boundary or allowed-input test proving the safe path still works

Keep verification targeted. Do not wait on the entire repo when the alert class is local.

### 5. Promote

The dedicated workflow is:
- `.github/workflows/codeql-analysis.yml`

The CodeQL config is:
- `.github/codeql/codeql-config.yml`

Use the workflow to keep code scanning separate from the broader `security-checks.yml` lane.

## Output Contract

Minimum triage output:

```json
{
  "repo": "issdandavis/SCBE-AETHERMOORE",
  "alert_count": 3,
  "rules": {
    "py/incomplete-url-substring-sanitization": 2,
    "js/bad-tag-filter": 1
  },
  "top_paths": [
    "src/aetherbrowser/page_analyzer.py",
    "src/browser/toolkit.py"
  ],
  "next_action": "patch URL validation helpers and rerun targeted tests"
}
```

## References

- `references/solution-logic.md`
- `references/workflow-lane.md`

## Scripts

- `scripts/inspect_code_scanning_alerts.py`
