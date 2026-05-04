# Productization Runbook

This is the non-coder path to ship SCBE safely as downloadable products.

## What we ship first

Ship only the stable trunk:
- GeoSeal CLI package lane
- Python runtime package lane
- GeoShell app artifacts lane
- Docs/website lane

Do not bundle every experimental subsystem in first release messaging.

## One-command quick gate

Run:

```powershell
npm run publish:check:strict && npm run connector:health
```

This does two things:
1. Runs strict npm package publish guards (`publish:check:strict`)
2. Verifies connector/runtime readiness (`connector:health`)

Outputs:
- `artifacts/npm-pack/pack.json`
- connector health summary in terminal output

## Full gate (slower)

Run this before public announcements:

```powershell
npm run publish:check:strict && npm run publish:pypi:build && npm run publish:pypi:check && npm run test:all
```

This adds:
- PyPI build + dist guard
- Full TS + Python test lane (`test:all`)

## Publish-safe checklist

- [ ] `npm run publish:check:strict && npm run connector:health` passes.
- [ ] `artifacts/pypi-dist/` contains fresh build artifacts when shipping Python package lanes.
- [ ] `artifacts/npm-pack/pack.json` exists and passed guard checks.
- [ ] Release notes clearly state what is in scope (`CLI + packages + app artifacts + docs`).
- [ ] No secrets or private proposal materials are in artifact bundles.

## Download security posture

For each downloadable file:
- publish file URL
- publish SHA-256 from `SHA256SUMS.txt`
- provide verification command for users:

```powershell
Get-FileHash .\downloaded_file.ext -Algorithm SHA256
```

Match the resulting hash with the posted checksum.

## Suggested public product naming

- `GeoSeal CLI` (command line product)
- `GeoShell` (desktop/app shell product)
- `SCBE Runtime SDK` (npm/Python package surfaces)

## Operator rule

If any readiness gate fails, do not publish. Fix gate, rerun, then ship.

