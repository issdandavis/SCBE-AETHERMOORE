# Workflow Lane

The dedicated code-scanning workflow lives at:

- `.github/workflows/codeql-analysis.yml`

The companion configuration file lives at:

- `.github/codeql/codeql-config.yml`

## Why This Exists

`security-checks.yml` is a broad security hygiene lane. Code scanning deserves its own run surface because:
- CodeQL has different runtime and permissions needs
- alert remediation needs deterministic rescans
- path filters should be explicit so generated/runtime clutter does not dominate the analysis

## Recommended Run Order

1. Triage alerts locally with `inspect_code_scanning_alerts.py`.
2. Patch the specific alert class.
3. Run the narrow local test lane.
4. Push to a branch or PR.
5. Let `codeql-analysis.yml` rescan.

## Manual Trigger

From GitHub UI:
- Actions
- `CodeQL Analysis`
- `Run workflow`

From CLI:

```powershell
gh workflow run codeql-analysis.yml
```

## Auth Caveat

If `gh api repos/<owner>/<repo>/code-scanning/alerts` returns `404`, do not assume there are no alerts. Check:
- repo Advanced Security settings
- token scopes / account permissions
- whether the workflow has produced alerts yet
