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
npm run product:ship:quick
```

This does two things:
1. Runs product readiness gates (`product:readiness`)
2. Builds SHA-256 download manifests (`product:manifest`)

Outputs:
- `artifacts/releases/product_readiness_latest.json`
- `artifacts/releases/download_manifest_latest.json`
- `artifacts/releases/SHA256SUMS.txt`

## Full gate (slower)

Run this before public announcements:

```powershell
npm run product:readiness:full
```

This adds:
- PyPI build + guard
- GeoShell Electron packaging (`electron:pack`)

## Publish-safe checklist

- [ ] `npm run product:ship:quick` passes.
- [ ] `artifacts/releases/product_readiness_latest.json` says `"all_passed": true`.
- [ ] `artifacts/releases/SHA256SUMS.txt` exists and is attached with download links.
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

