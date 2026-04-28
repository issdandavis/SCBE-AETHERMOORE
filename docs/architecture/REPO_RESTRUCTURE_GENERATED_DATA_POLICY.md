# Repo Restructure Generated Data Policy

## Intent

Define what is canonical source-controlled material versus local/generated data before any path migration.

## Policy Decisions

### `generated/`

- `generated/` is local-first and ignored by default.
- Files can be promoted to source control only with explicit canonical rationale.

### `artifacts/`

`artifacts/` is not a single class of data and must be handled in two lanes:

1. **Disposable runtime outputs**
   - smokes
   - temporary reports
   - machine-local diagnostics
2. **Canonical evidence/proposal records**
   - proposal evidence bundles
   - audit-linked artifacts required for traceability

Do not blanket-move or blanket-ignore `artifacts/` without lane tagging.

### `training-data/`

- `training-data/` includes canonical corpora and must not be auto-moved into `generated/`.
- Non-canonical local experiments should be separated with explicit naming/manifests.

## Migration Guard

Before moving data-heavy roots:

1. classify canonical vs disposable
2. record decisions in `docs/architecture/REPO_RESTRUCTURE_MIGRATION_MAP.md`
3. verify ignore policy and CI references still align

## Enforcement Hooks

- path reference scan (`scripts/system/repo_path_reference_scan.py`)
- launch preflight (`scripts/system/repo_launch_preflight.py`)
- secret sweep (`python scripts/check_secrets.py`)
- markdown link/path check (`python scripts/system/check_markdown_links.py`)
