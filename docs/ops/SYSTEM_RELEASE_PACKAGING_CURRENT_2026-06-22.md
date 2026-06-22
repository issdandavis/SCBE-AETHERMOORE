# Current Release Packaging Map - 2026-06-22

## Purpose

SCBE-AETHERMOORE has become a multi-product repo. The failure mode is not "no packaging"; the failure mode is too many working surfaces with no single release contract. This note defines the current release objects and the gate that keeps them from drifting.

The machine-readable contract is `config/release_surfaces.v1.json`. Validate it with:

```powershell
npm run release:surface-audit
```

## Current Shipping Surfaces

| Surface | Status | Build | Gate |
|---|---|---|---|
| npm SDK / GeoSeal CLI | ship | `npm run publish:prepare` | `npm run publish:check:strict`, `npm run publish:smoke:consumer` |
| Python package | ship | `npm run publish:pypi:build` | `npm run publish:pypi:check` |
| Buyer product ZIPs | ship | `npm run writing:package:all` | `python -m pytest tests/test_package_products.py -q` |
| Workcell download | ship | `npm run release:workcell` | verified temp install transcript from `scripts/system/build_workcell_download.py` |
| Black Box download | ship | `npm run release:blackbox` | verified sample run transcript from `scripts/system/build_black_box_download.py` |
| Docs / public site | ship | GitHub Pages workflows | `npm run docs:check` |
| Docker/API | preview | `npm run docker:remote:api` | `npm run docker:doctor:api` |
| Training/eval | internal | `npm run training:hub` | held-out benchmark or promotion report, not a public release by default |
| AetherDesk standalone | ship in separate repo | `npm test`, `npm run build:react` | AetherDesk repo CI/release gate |

## Packaging Rule

Do not release "the repo." Release one surface at a time:

1. Pick the surface id from `config/release_surfaces.v1.json`.
2. Run its build command.
3. Run its verification command.
4. Attach the manifest, transcript, checksum, or GitHub Actions run to the release notes.
5. Keep training runs, generated artifacts, browser profiles, private OAuth config, and archives out of public release packages.

## What Needs Improvement Next

1. AetherDesk should get its own release workflow in the standalone repo: test, React build, package a desktop ZIP or installer, upload artifact, and attach release notes.
2. SCBE should add a release checklist generator that reads `config/release_surfaces.v1.json` and prints the exact commands for a chosen surface.
3. Docker/API should stay preview until one black-box health/auth/action smoke is the canonical gate.
4. Training/eval outputs should remain internal unless they have a manifest, source bucket, train/eval split, and held-out result.
5. Buyer product ZIPs need a current inventory file per ZIP, not just a root inventory.

## Why This Helps

This turns release work from archaeology into a contract. A model or human can now ask:

- What is the product?
- Which files own it?
- Which command builds it?
- Which gate proves it?
- Is it public, preview, or internal?

If a branch cannot answer those questions, it should not go to `main` as a release branch.
