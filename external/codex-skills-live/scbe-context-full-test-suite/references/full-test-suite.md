# SCBE Full Test Suite

Choose the narrowest lane that proves the work.

## Targeted Lane

Use when one feature, file, or alert family changed.

Common commands:

```powershell
npx vitest run <ts-test-files>
python -m pytest <py-test-files> -q
npm run typecheck
python -m py_compile <python-files>
```

## Core Lane

Use when the branch needs a safe repo-wide gate.

Primary command:

```powershell
pwsh -File .\scripts\branch_validation.ps1 -Branch <branch> -Profile core
```

Core currently means:

- root `npm run typecheck`
- root `npm test`
- root `python run_tests.py release --preflight`

## Full Lane

Use when broader regression coverage is worth the time.

Primary command:

```powershell
pwsh -File .\scripts\branch_validation.ps1 -Branch <branch> -Profile full
```

The exact steps come from `scripts/branch_validation.ps1` and may include subproject typecheck and vitest lanes.

## Fallback If Branch Validator Is Missing

Run from repo root:

```powershell
npm run typecheck
npm test
python run_tests.py release --preflight
```

Then add targeted subproject commands only if the change touched those areas.

## Reporting Format

- command
- result
- scope
- blockers or pre-existing failures
