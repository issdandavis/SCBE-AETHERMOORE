# Dependency maintenance

SCBE owns its governance rules, tokenizer, and orchestration code. Third-party
libraries support those components; maintaining a private replacement also
means owning its compatibility tests, security fixes, and release process.

## Security update boundaries

The September 2026 dependency review identified these installed paths with
`npm explain`. Development tools can affect developer machines even when they
are absent from a deployed runtime.

| Dependency      | Consumer                                                | Role                             | Current maintenance choice                                                     |
| --------------- | ------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| Hono            | MCP SDK in the root package and CLI                     | Runtime HTTP transport           | Keep protocol compatibility; pin the tested patched release in both overrides. |
| Sharp           | Wrangler's Miniflare dependency in `services/scbe-shim` | Local development image handling | Update the native decoder; it is not imported by the Worker source.            |
| js-yaml         | Electron builder in `scbe-visual-system`                | Build configuration parsing      | Keep the patched parser in build tooling.                                      |
| Vitest / mocker | Agent bus, desktop shell, and other test suites         | Development and tests            | Update the runner and its matching internal packages together.                 |

September 10 fixes: Hono 4.13.5, Sharp 0.35.4 (bundled libheif 1.23.2),
js-yaml 4.3.2, and Vitest 4.1.11. These versions address the reviewed advisories;
they are not a permanent guarantee against future vulnerabilities.

- [Hono query parser advisory](https://github.com/advisories/GHSA-crvj-82cr-hjcx)
- [Hono body parser advisory](https://github.com/advisories/GHSA-g6gw-c38x-mqfc)
- [Hono static output advisory](https://github.com/advisories/GHSA-gqvv-2mrq-wpjv)
- [Sharp decoder advisory](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c)
- [YAML merge budget advisory](https://github.com/advisories/GHSA-2883-xcg3-v3hh)
- [Vitest mocker advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9)

## When an in-house implementation helps

Start with a narrow interface that SCBE already understands and can test: a
small formatting helper, a policy rule, or a product-specific adapter. First
look for existing implementations in the repository. Compare the replacement
against normal inputs, invalid inputs, resource limits, and the old behavior.
Remove the dependency only when its callers and transitive consumers no longer
need it.

Replacing an entire image decoder, YAML parser, protocol SDK, or cryptographic
library requires a separate compatibility and security review. A private fork
retains upstream bugs until someone fixes them. Copying code into the tree does
not remove the maintenance obligation or its license requirements.

## Repeatable update procedure

1. Inspect each affected manifest and `npm explain <package>` in that directory.
2. Update the compatible security floor or explicit override and regenerate its
   lockfile with install scripts disabled. Avoid unrelated major upgrades.
3. Run `npm ci --ignore-scripts` and the affected package's tests and build.
   Exercise native dependencies and protocol connections with local fixtures.
4. Run `npm audit --package-lock-only` for every affected lockfile, including
   nested applications. A successful root audit does not cover those apps.
5. Merge the tested change, then verify GitHub closes the original alerts on the
   default branch. Do not dismiss an alert as a substitute for fixing it.

For runtime images, install production dependencies only where supported by the
deployment. Keep the full development toolchain available in the build/test
stage and review the actual release contents before publishing.

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
