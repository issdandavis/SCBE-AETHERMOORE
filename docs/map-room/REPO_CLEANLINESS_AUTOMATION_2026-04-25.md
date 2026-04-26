# Repository Cleanliness Automation

This repo is cleaned by routing changes into stable buckets, not by deleting
unknown files.

## Current Rule

- Source, tests, config, and canonical docs can be staged after review.
- Generated outputs, caches, local state, and model artifacts stay ignored or
  are offloaded.
- Private proposal/legal packets stay local/private unless explicitly promoted.
- Deletions are reviewed before commit.
- Secrets are blocked before push; leaked secrets are rotated instead of merely
  removed from the latest working tree.

## Automation Lanes

1. `python scripts/system/repo_cleanliness_audit.py --json`
   - Read-only cleanliness report.
   - Buckets dirty paths into source, docs, config, training, generated output,
     local state, private proposal, and manual classification lanes.

2. `python scripts/check_secrets.py`
   - Local secret scan over tracked and untracked non-ignored files.
   - Runs as the default pre-commit hook.

3. `python scripts/system/local_git_hygiene.py status --json`
   - Local-only skip-worktree and `.git/info/exclude` status.
   - Use for operator-local paths that should not become shared repo policy.

4. `python scripts/system/cleanup_local_github_hygiene.py --dry-run --json`
   - Safe generated-artifact cleanup preview plus remote branch prune check.
   - Only run without `--dry-run` after the preview is acceptable.

## Hook Setup

Install hooks locally:

```powershell
python -m pip install pre-commit
pre-commit install
```

Run the manual hygiene gates:

```powershell
pre-commit run scbe-repo-cleanliness-audit --hook-stage manual
pre-commit run scbe-release-cleanliness-audit --hook-stage manual
```

The normal commit hook only runs the secret scan. The full cleanliness audit is
manual because this working tree intentionally carries active multi-lane work.

## Methods Researched

- Use a local pre-commit framework for fast checks before commits.
- Keep heavyweight tests and full cleanup reports in manual or CI lanes.
- Use secret scanning locally and in GitHub, because removing a secret from a
  later commit does not remove it from history.
- Separate generated artifacts from source, and prefer offload or ignore rules
  over destructive cleanup.
- Use scheduled CI reports for repo health, but do not let CI auto-commit broad
  rewrites onto active feature branches.

## Release Clean Target

A release branch should reach:

- `git status --short` has no unreviewed paths.
- `python scripts/check_secrets.py` passes.
- `python scripts/system/repo_cleanliness_audit.py --max-dirty 0 --max-unclassified 0` passes.
- Targeted tests for changed subsystems pass.
- Generated artifacts are rebuilt in CI or stored in a named release artifact
  lane, not mixed into source commits.
