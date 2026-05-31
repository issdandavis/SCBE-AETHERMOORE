# Precommit Lint and Format Guide

This repo installs a local pre-commit hook from `scripts/hooks/pre-commit`.
Install or refresh it with:

```powershell
npm run hooks:install
```

The hook also installs automatically through the `prepare` script when running
`npm install`.

## Before Committing

Run the narrow checks that match the main CI lint gate:

```powershell
node node_modules\prettier\bin\prettier.cjs --check "src/**/*.ts" "tests/**/*.ts"
python -m black --check --target-version py311 --line-length 120 src tests
python -m ruff check --config ruff.toml
```

To apply formatting:

```powershell
npm run format
npm run format:python
```

Then rerun the checks above before committing.

## Wider Local Checks

`npm run lint` is stricter than the current CI lint gate because it also checks
`packages/**/*.ts`. Use it before broad package work, but treat existing package
format drift separately from focused CI fixes.

For dependency or release-adjacent changes, run:

```powershell
npm run typecheck
npm run build
npm test
python scripts/system/run_core_python_checks.py
```

If Python coverage upload behavior is being changed, generate the same report
CI expects:

```powershell
python scripts/system/run_core_python_checks.py -- --cov=src --cov-report=xml
```

Codecov upload in CI is advisory and only runs when both `coverage.xml` exists
and the `CODECOV_TOKEN` secret is configured.
