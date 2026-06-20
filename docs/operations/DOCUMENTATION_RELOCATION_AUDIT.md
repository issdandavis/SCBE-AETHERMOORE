# Documentation Relocation Audit

Date: 2026-05-26

## Reason

The repo has documentation scattered through root files, package folders,
agent-skill folders, examples, plugins, generated workspaces, and `docs/`.
The target state is cleaner separation between runtime code and documents.

## Current Count

Tracked Markdown files outside `docs/` at audit time: 1,260.

That count includes files that cannot be moved blindly:

- root landing/package files: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `RELEASING.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
- package metadata files used by npm/PyPI/GitHub: package `README.md` files,
  license notices, release notes
- installed agent and plugin skill files under `.agents/`, `.claude/`, `.home/`
- examples that are intentionally self-contained
- generated or archived run notes under `.scbe/`

## Decision

Do not move every Markdown file in one mechanical pass.

A repo-wide Markdown relocation would break installed agents, package metadata,
GitHub landing pages, npm package file lists, PyPI readmes, and local plugin
discovery. The correct migration is staged.

## Safe Target Layout

Use `docs/` as the documentation folder and keep only operational shims at the
repo/package roots.

Recommended channels:

| Channel | Destination | Rule |
|---|---|---|
| Canonical architecture | `docs/architecture/` or `docs/specs/` | Authoritative system truth |
| User guides | `docs/guides/` | Human setup, demos, quickstarts |
| Operator docs | `docs/operations/` | Runbooks, release, CI, support |
| Research notes | `docs/research/` | Exploratory or evidence-linked notes |
| Product docs | `docs/product/` | Buyer and package positioning |
| Historical docs | `docs/archive/` | Preserved but not current authority |
| Root shims | repo/package root | Tiny pointers only when package tooling requires them |

## Migration Rules

1. Keep root `README.md` because GitHub, npm, PyPI, and humans expect it.
2. Keep license and contribution files at root unless packaging is updated.
3. Keep `AGENTS.md` at root because agents load it from the working tree.
4. Do not move `.agents/**/SKILL.md`, `.claude/**/SKILL.md`, or plugin command
   Markdown without updating the agent/plugin loader.
5. Move package guides only after updating `package.json.files`,
   pyproject metadata, and links.
6. Leave a pointer shim at the old path for any moved public entrypoint.
7. Run link checks and package dry-runs after each batch.

## First Safe Batch

Start with standalone, non-loader docs that are not root metadata and not used
as package readmes:

```bash
git ls-files "*.md" |
  findstr /v /r "^docs/ ^README.md$ ^AGENTS.md$ ^CHANGELOG.md$ ^CONTRIBUTING.md$ ^RELEASING.md$ ^LICENSE-NOTICE.md$ ^\\.agents/ ^\\.claude/ ^\\.home/"
```

Each move should be reviewed for:

- inbound links
- package inclusion
- agent/plugin loader dependency
- generated-vs-source status
- whether a shim is needed

## Verification Required Per Batch

```bash
npm run lint
npm run typecheck
npm test
python -m pytest tests/test_beginner_demo.py -q
npm pack --dry-run --json
npm pack --dry-run --json --prefix packages/cli
```

For a package-doc move, also verify the published package still includes the
intended README or replacement doc.
