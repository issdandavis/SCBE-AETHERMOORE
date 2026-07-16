# Package Release Control

SCBE is one project graph with multiple package surfaces. Some surfaces are
published registries, some are local repos, and some are mirrors or worktrees.
Release control keeps those lanes coordinated without publishing accidentally.

## Current Rule

Publish public SCBE packages only from:

```text
C:\Users\issda\SCBE-AETHERMOORE
```

Do not publish from audit worktrees, mirrors, generated folders, or package
experiments unless they have their own explicit release plan.

## Read-Only Inventory

```powershell
node C:\Users\issda\SCBE-AETHERMOORE\bin\geoseal.cjs package-registry --json
node C:\Users\issda\SCBE-AETHERMOORE\bin\geoseal.cjs package-registry --include-roster --json
```

The command writes:

```text
artifacts/package_registry_control/latest/package_registry_control.json
artifacts/package_registry_control/latest/package_registry_control.md
```

It checks:

- local `package.json` and `pyproject.toml` package names and versions
- public npm metadata
- public PyPI metadata
- local npm auth state
- duplicate local package names across worktrees
- read-only release blockers

It does not bump, build, upload, or publish.

## Known Guard Commands

For npm:

```powershell
npm run publish:check:strict
npm run publish:smoke:consumer
npm publish --dry-run
```

Only after reviewing those outputs:

```powershell
npm publish
```

For PyPI:

```powershell
npm run publish:pypi:build
npm run publish:pypi:check
python -m twine check artifacts/pypi-dist/*
```

Only after reviewing those outputs:

```powershell
python -m twine upload artifacts/pypi-dist/*
```

## Release Sequence

1. Run `geoseal package-registry --include-roster --json`.
2. Confirm the canonical root is ahead of registry versions.
3. Fix registry authentication if blocked.
4. Run guard commands for one registry only.
5. Inspect generated tarball/wheel contents.
6. Publish npm or PyPI, not both at once.
7. Re-run registry inventory.
8. Commit the release ledger and changelog after the registry confirms.

## Current Expected SCBE State

At the time this lane was added, local manifests reported
`scbe-aethermoore` version `4.2.1`. Public registries were behind:

- npm: `4.1.3`
- PyPI: `4.2.0`

That means the next controlled release target is to publish `4.2.1` from the
canonical root after guard checks pass and auth is repaired.
