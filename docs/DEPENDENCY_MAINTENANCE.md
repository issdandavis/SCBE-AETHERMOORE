# Dependency maintenance

Keep compatibility checks attached to the exact pull-request head. A clean main
branch and a failed dependency branch can coexist; inspect the failing job before
changing application code or relaxing a gate.

## Vitest and coverage move together

The September 20 Vitest 5 proposals failed `npm ci` because one package moved
while the other remained on version 4. `@vitest/coverage-v8@4.1.11` requires
`vitest@4.1.11`. The reverse one-package update has the same problem.

The `vitest-toolchain` version-update group in `.github/dependabot.yml` matches
`vitest` and `@vitest/*`, including majors, before the general minor/patch group.
This follows [GitHub's first-matching-group rule](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups).
Security updates retain their existing group.

Grouping prepares a coherent proposal; it does not approve a major upgrade.
Check the candidate packages' Node engine requirements, lockfile resolution,
type checking, tests, coverage, and affected nested-app builds. Root CI does not
exercise every nested package. Never use `--force` or `--legacy-peer-deps` to
hide a version mismatch, or merge red checks as cosmetic failures.

Existing individual major-version PRs remain review items until replaced by a
tested combined proposal. Do not close unrelated user feature work or drafts.

## Routine update procedure

1. Inspect changed manifests and lockfiles, including nested directories.
2. Bring a reviewed routine dependency branch up to date without force-pushing.
3. Wait for required checks and relevant app builds on that new head.
4. Merge with a head-SHA guard, then verify the resulting default-branch commit.
5. Record merged/pending/failed outcomes and exact verification links.

Generated badge PRs can have only their explicit conflict guard because events
created with the workflow token do not necessarily start other workflows. The
repository CI supports `workflow_dispatch`; run it on the reviewed badge branch
to obtain the normal checks. Preserve main's branch protection.

## Local maintenance while training

Use clean maintenance checkouts for integration work. Leave active trainer code,
datasets, checkpoints and source pins in their training workspace. Reclaim only
identified generated caches after checking paths, Git tracking and live users.
Record the worktree inventory and unresolved local work rather than resetting a
dirty research directory to make its status look clean.
