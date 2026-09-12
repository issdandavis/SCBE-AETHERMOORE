# Repository readiness review — 2026-09-10

Reviewed GitHub `main` at `fa054f3aa`. The latest nightly Python checks passed.
On Windows, Git's CRLF checkout caused 648 TypeScript files to fail Prettier's LF
rule. The tracked contents were already formatted; `.gitattributes` now pins
TypeScript line endings without a bulk source rewrite.
Python local commands now run the same scopes and
linters as CI, with pinned tool versions. Workflow-only pushes also run CI.

The repository contains about 86.8 MiB across 7,094 tracked files. Its purpose
is broader than any one download. The authoritative product boundaries remain
[SYSTEM_MAP.md](../SYSTEM_MAP.md), [START_HERE.md](../START_HERE.md), and
[release_surfaces.v1.json](../config/release_surfaces.v1.json).

## Product contents

| Keep in a release | Keep for development, outside the SDK release |
| --- | --- |
| Compiled SDK exports and declared CLI entry points | Tests, CI, build scripts, compiler inputs |
| License, API docs, minimal runnable examples | Research, patent evidence, books, historical notes |
| Python packages explicitly selected by `setup.py` | Training corpora, experiment outputs, checkpoint archives |

The npm `files` allowlist already excludes the broad repository tree. The
release guard checks the actual pack manifest; CI now runs it after building.
The Python wheel and source archive have their own manifest and guard. Use
those package artifacts for distribution instead of a ZIP of the whole repo.

The inspected Python artifacts initially contained eight embedded test files.
They are now excluded from packaging, and the release guard treats test payloads
as errors. A dedicated CI job builds the wheel from the source distribution and
checks both archives, without installing the full training environment.

## Verification commands

```sh
npm ci
python -m pip install -r requirements-lint.txt
npm run lint
npm run format:python:check
npm run lint:python
npm run typecheck
npm run build
npm test
npm run publish:check:strict
python -m build --outdir artifacts/pypi-dist
npm run publish:pypi:check
npm run release:surface-audit
```

Run packaging in a clean checkout. None of these checks publishes a package.
The full release process additionally requires the named surface's consumer,
security, and integration gates. Passing lint is not a security certification.

## Next cleanup, preserving project history

1. Select the downloadable product being released: SDK/GeoSeal, Agent Bus,
   Python package, or a named application. Test its install and first task.
2. Keep runtime, tests, build configuration, and user-facing documentation close
   together. Preserve research and patent records, with links from the system map.
3. Inventory archive payloads before migration. The two approximately 4 MiB
   `cloud-archive/.../prompt-data/.../prompt_text*.txt` exports are candidates for
   private, checksum-verified archival; their contents were not inspected in this
   review. Do not include conversational exports in product downloads.
4. Handle dependency PRs individually after their checks pass. A green nightly
   on `main` does not validate a different PR head or an uncommitted worktree.

No research files, weights, local changes, or existing branches were removed by
this review. Moving tracked files later requires a named destination, references
checked, and a verified copy. Deleting a file from the current tree alone does
not erase its Git history or make sensitive history private.
