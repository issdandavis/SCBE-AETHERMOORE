# GitHub Issue Maintenance

This repository uses issues for actionable exceptions, not for successful
scheduled-run receipts. Normal results remain in the workflow summary and its
retained artifact. An automated issue opens only when a maintainer action is
needed, updates in place while the condition persists, and closes after a
verified clean run.

## Control flow

| Input | Workflow | Issue lifecycle |
|---|---|---|
| Full Python test result | `nightly-python-full.yml` | One `nightly-failure` issue; replace the body on failure, close on success |
| Dependency and secret reports | `weekly-security-scan.yml` | One `security-scan` issue while findings or scanner errors exist |
| Latest result per workflow | `weekly-repo-health.yml` | One `repo-health` issue while a workflow's latest run is failed |
| Hugging Face drift and access evidence | `weekly-hf-sync.yml` | One `hf-sync` issue for drift, unsynced files, or scanner/access errors |
| SAM.gov results and query evidence | `weekly-gov-contracts-check.yml` | One `gov-contracts` issue for opportunities or incomplete queries |
| Workflow governance findings | `workflow-audit.yml` | One CI/security issue while high-risk findings exist |

The shared implementation is `.github/scripts/issue-lifecycle.cjs`. It embeds a
hidden ownership marker in managed issue bodies, paginates label searches, and
can adopt explicitly named legacy issues only when GitHub Actions authored them.

## Invariants

- A human-authored issue is never closed because it happens to share an
  automation label or title.
- A missing report, inaccessible repository, or failed query is `UNKNOWN` and
  actionable; it is never reported as a clean zero.
- Scheduled checks publish a workflow summary even when no issue is open.
- Security, active/blocked work, leads, and rolling action issues are exempt
  from generic stale closure.
- Issue intake uses high-confidence title rules. Issue forms remain authoritative,
  and only the first-interaction workflow posts a welcome comment.
- No workflow body may contain credentials, private lead details, or full secret
  scanner matches.

## Verification

Run the deterministic helper tests and validate workflow syntax:

```bash
node --test tests/github/test_issue_automation.cjs
python -m pytest tests/site/test_github_map.py -q
python scripts/workflow_audit.py --workspace . --report artifacts/workflow-audit.json --summary artifacts/workflow-audit.md
```

After merge, dispatch each changed scheduled workflow once. Confirm that a
clean run closes only its marked legacy/rolling issue and that an actionable
run updates one issue instead of creating a duplicate.

## Rollback and stop conditions

Revert the maintenance commit to restore the prior workflow behavior. Closed
issues remain recoverable through GitHub and can be reopened. Stop automated
cleanup and investigate if a human-authored issue is selected, report evidence
is absent, the helper cannot identify its ownership marker, or GitHub project
permissions are unavailable. Project-board fields are a separate control plane
and must not be guessed from issue labels.
