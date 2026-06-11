---
name: clean
description: 'Safely clean repo artifacts: dry-run first, targeted deletes only, never tracked files'
argument-hint: '[deep]'
allowed-tools: Bash(git clean:*), Bash(git status:*), Bash(npm run clean:*), Bash(rm -rf .benchmarks:*), Bash(rm -rf .pytest_cache:*), Bash(rm -rf coverage:*), Bash(rm -rf htmlcov:*), Bash(rm -rf dist-gateway:*), Bash(find . -name __pycache__:*)
---

## Context (live dry-run)

- Untracked files git would remove: !`git clean -nd`
- Working tree status: !`git status --short`

## Task

Clean the repository working tree, safety-first. Arguments: `$ARGUMENTS`

### Rules (non-negotiable)

1. **Targeted deletes only.** Remove ONLY these known artifact paths if present:
   - `.benchmarks/` (pytest-benchmark)
   - `__pycache__/` dirs and `.pytest_cache/`
   - `coverage/`, `htmlcov/`, `.coverage`, `coverage.json`
   - `dist/` — via the existing `npm run clean` script, not rm
   - `dist-gateway/`
   - `*.log` files at repo root (NOT `config/tor/tor.log` paths inside tracked config)
2. **NEVER run blanket `git clean -fd` or `git clean -fdx`.** That would delete
   `node_modules/`, `.env`, local configs, and any in-progress untracked work.
3. **Protect in-progress work.** If the dry-run above lists untracked files that are
   not on the artifact list (source files, docs, notes), list them and ASK before
   touching anything — default is leave them alone.
4. **`deep` argument** (`$ARGUMENTS` contains `deep`): additionally clear
   `node_modules/.cache/`, `.ruff_cache/`, and stale `*.tsbuildinfo` files.
5. **Report.** End with exactly what was deleted (paths + approximate space freed)
   and what was intentionally left alone.

If the dry-run shows nothing removable, say so and stop — do not invent work.
