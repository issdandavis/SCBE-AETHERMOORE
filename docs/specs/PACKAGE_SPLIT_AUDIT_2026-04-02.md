# Package Split Audit — 2026-04-02

## Sync State

- Current branch: `site-publish-v4`
- `git fetch origin` succeeded after retrying outside the sandbox
- Branch relation against `origin/main`: `1992 behind`, `2021 ahead`
- Worktree is dirty across source, docs, scripts, tests, training, and content
- Conclusion: a blind `git pull` is not safe on this branch

## First-Party Publish Surfaces

### Candidate npm packages

| Path | Current identity | Status | Notes |
| --- | --- | --- | --- |
| `package.json` | `scbe-aethermoore` | Canonical candidate | Already has `files` allowlist and publish guard scripts |
| `packages/scbe-aethermoore-cli/package.json` | `scbe-aethermoore-cli` | Canonical candidate | Clean standalone CLI wrapper around the root package |
| `packages/kernel/package.json` | `@scbe/kernel` | Internal only | Marked `private`, no build/test/publish pipeline |

### Candidate PyPI packages

| Path | Current identity | Status | Notes |
| --- | --- | --- | --- |
| `pyproject.toml` | `scbe-aethermoore` | Canonical candidate | Needs package scope tightening before public publish |
| `python/pqc/pyproject.toml` | `pypqc` | Vendor/fork | Not a first-party SCBE publish target |
| `src/pyproject.toml` | `scbe-aethermoore` | Duplicate/stale | Conflicts with root package identity and should not remain publishable |

## Internal App Surfaces

These should stay out of npm/PyPI package payloads and be handled as apps, demos, or services:

- `app/`
- `ai-ide/`
- `desktop/`
- `conference-app/`
- `kindle-app/`
- `scbe-visual-system/`
- `apps/scbe-github-app/`
- `mcp/apps/cymatic-voxel-app/`
- `spaces/`
- `demo/`
- `prototype/`
- `examples/`

## Non-Ship Surfaces

These should be excluded from package payloads unless explicitly needed by a package-specific release:

- `artifacts/`
- `training-data/`
- `training/`
- `notebooks/`
- `notes/`
- `content/`
- `docs/`
- `external/`
- `external_repos/`
- `backups/`
- `dist/`
- `node_modules/`

## Overshipping Risks Found

### 1. Duplicate package identity

The repo currently defines `scbe-aethermoore` in both:

- `package.json`
- `pyproject.toml`
- `src/package.json`
- `src/pyproject.toml`

Only one npm root and one PyPI root should remain authoritative.

### 2. Root PyPI package scope is too broad

`pyproject.toml` currently includes package discovery across mixed surfaces such as:

- `scripts*`
- `api*`
- `storage*`
- `flow_router*`

That is too much for a public library release and increases overshipping risk.

### 3. Root repo still mixes library, app, and research concerns

The first-party manifest inventory shows package manifests under:

- root
- `src/`
- `packages/`
- `app/`
- `desktop/`
- `conference-app/`
- `kindle-app/`
- `apps/`
- `spaces/`

That needs a declared separation between libraries, apps, and experiments.

## Recommended Canonical Split

### Publishable npm lane

- Keep `package.json` as the only canonical npm library release root
- Keep `packages/scbe-aethermoore-cli` as the CLI release package
- Keep `packages/kernel` private until it has its own build, exports, and tests

### Publishable PyPI lane

- Keep root `pyproject.toml` as the only canonical Python release root
- Remove `src/pyproject.toml` from publish consideration
- Narrow package discovery to the true Python library surfaces only

### Internal monorepo lane

- Treat app and service directories as internal deployables, not package release roots
- Keep demos, notebooks, spaces, and training corpora in repo but out of package payloads

## Best-Version Push Recommendation

The best version to push right now is not a blind merge of the whole dirty tree.

The safe push order is:

1. Push only audit/planning work that clarifies package boundaries
2. Isolate library-release changes from docs/content/training changes
3. Add package payload smoke checks for npm and PyPI
4. Only then stage a package-split branch for sync/merge

## Immediate Next Steps

1. Freeze canonical release roots:
   - npm: `package.json`, `packages/scbe-aethermoore-cli/package.json`
   - PyPI: `pyproject.toml`
2. Remove duplicate `src/` package identities from release consideration
3. Add a package manifest guard that fails if app/demo/training paths leak into package payloads
4. Create one follow-up branch focused only on package extraction and release boundaries
