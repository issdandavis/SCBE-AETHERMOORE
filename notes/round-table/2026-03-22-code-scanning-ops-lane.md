# 2026-03-22 Code Scanning Ops Lane

## What Changed

- Added a dedicated CodeQL workflow at `.github/workflows/codeql-analysis.yml`.
- Added a repo-local skill mirror at `skills/codex-mirror/scbe-code-scanning-ops/`.
- Added an offline-testable alert summarizer at `skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py`.

## Why

The repo already had `security-checks.yml`, but that lane is broad. Code scanning needs:
- its own workflow
- its own fix taxonomy
- a repeatable alert triage command

## Current Fix Classes

The active high-severity classes on `main` include:
- incomplete URL substring sanitization
- bad HTML filtering regexp
- uncontrolled path expression
- clear-text logging or storage of sensitive information
- DOM text reinterpreted as HTML
- missing rate limiting
- resource exhaustion
- biased random mapping from cryptographic randomness

## Operator Commands

```powershell
python skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py --repo issdandavis/SCBE-AETHERMOORE
python skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py --alerts-file artifacts/security/code_scanning_alerts.json --json
gh workflow run codeql-analysis.yml
```
