# GeoSeal npm/PyPI Release Order - 2026-06-27

Status: release-prep note, not a publish record.

## Current comparison

### Local vs GitHub

Current local branch:

```text
lane/tool-trajectory-harvester
```

Local commit:

```text
7663958f975700d6561d5ff101ab5bdb4cc7f060
```

Remote tracking branch:

```text
origin/lane/tool-trajectory-harvester
```

Tracking comparison:

```text
origin/lane/tool-trajectory-harvester...HEAD = 0 behind / 0 ahead
```

Main comparison:

```text
origin/main...HEAD = 111 behind / 18 ahead
origin/main = 16ee6a3774577208da5a85caf49a3de4c0619a15
```

Interpretation:

- Local matches its GitHub lane branch exactly.
- The lane branch is heavily divergent from `origin/main`.
- Do not publish from the assumption that this is current main.
- Use a dedicated release branch or reconcile with `main` before publishing.

## Registry comparison

Local package metadata:

```text
npm package name: scbe-aethermoore
local npm version: 4.2.1
PyPI package name: scbe-aethermoore
local PyPI version: 4.2.1
```

Current public registry state observed:

```text
npm latest: 4.1.3
PyPI latest: 4.2.0
```

Interpretation:

- `4.2.1` is a valid next version for both registries.
- npm is behind PyPI, so npm needs the larger catch-up.
- PyPI only needs a `4.2.1` follow-up if the package contents are ready.

## GeoSeal surface found locally

npm already exposes direct GeoSeal binaries:

```json
{
  "geoseal": "bin/geoseal.cjs",
  "scbe-geoseal": "bin/geoseal.cjs"
}
```

Node-side GeoSeal wrapper currently includes:

- `providers`
- `lanes`
- `product-lanes`
- `ask`
- `do`
- `service`
- `service-status`
- `service-stop`
- `doctor`
- `code-cube`
- `tokenizer-code-lanes`
- `verify-code-lanes`
- `decode-code-lanes`
- custom `.geoseal.yaml` command loading
- service bridge into Python `src.api.geoseal_service`

Python-side GeoSeal CLI exists at:

```text
src/geoseal_cli.py
```

Python-side GeoSeal service exists at:

```text
src/api/geoseal_service.py
src/api/geoseal_cli_bridge.py
```

Important packaging gap:

- PyPI metadata currently exposes `scbe`, `scbe-scan`, `scbe-system`, `scbe-convert-to-sft`, and `scbe-code-prism`.
- PyPI does not currently expose a direct `geoseal` or `scbe-geoseal` console entry.
- Treat npm as the primary direct GeoSeal CLI release surface unless/until a clean PyPI GeoSeal wrapper is added and checked.

## Clean release order

### Phase 0 - Freeze the branch decision

Pick one:

1. Release from a dedicated branch based on `lane/tool-trajectory-harvester`.
2. Rebase/merge the lane into current `main`, then release from a release branch.
3. Cherry-pick only GeoSeal/package changes onto a fresh release branch from `origin/main`.

Recommended:

```text
Create a fresh release branch, then intentionally decide whether to carry the 18 lane commits or cherry-pick only release-safe changes.
```

Reason:

```text
The branch has 18 commits not on main, while main has 111 commits not here.
```

### Phase 1 - Lock release metadata

Confirm these stay aligned:

```text
package.json       version = 4.2.1
pyproject.toml     version = 4.2.1
npm package        scbe-aethermoore
PyPI package       scbe-aethermoore
license            MIT OR Apache-2.0
```

If any package contents change after this point, keep `4.2.1` only if it has not been published yet. Once either registry publishes `4.2.1`, future fixes must become `4.2.2`.

### Phase 2 - GeoSeal smoke targets

Do not run these as proof yet unless explicitly requested. These are the intended gates:

```powershell
node bin/geoseal.cjs doctor --json
node bin/geoseal.cjs providers --json
node bin/geoseal.cjs lanes --json
node bin/geoseal.cjs service-status --json
node bin/geoseal.cjs tokenizer-code-lanes --command shl --tongues all --json
```

Python GeoSeal import/help probes should use:

```powershell
$env:SCBE_FORCE_SKIP_LIBOQS='1'
python -m src.geoseal_cli --help
python -m src.geoseal_cli mars-mission --json
```

Reason:

```text
src.geoseal_cli can trigger optional liboqs bootstrap on import; use SCBE_FORCE_SKIP_LIBOQS=1 for deterministic CLI probes.
```

### Phase 3 - npm package gate

Existing scripts:

```powershell
npm run publish:prepare
npm run publish:check:strict
npm run publish:smoke:consumer
npm publish --dry-run
```

Publish command, only after explicit approval:

```powershell
npm publish
```

npm release expectation:

```text
latest should move from 4.1.3 to 4.2.1
```

### Phase 4 - PyPI package gate

Existing scripts:

```powershell
npm run publish:pypi:build
npm run publish:pypi:check
```

Additional standard guard:

```powershell
python -m twine check artifacts/pypi-dist/*
```

TestPyPI, only if credentials are configured and explicitly approved:

```powershell
python -m twine upload --repository testpypi artifacts/pypi-dist/*
```

PyPI, only after explicit approval:

```powershell
python -m twine upload artifacts/pypi-dist/*
```

PyPI release expectation:

```text
latest should move from 4.2.0 to 4.2.1
```

### Phase 5 - PyPI GeoSeal console decision

Before claiming PyPI has a direct `geoseal` command, choose and implement one of these:

1. Add a proper packaged GeoSeal wrapper under `scbe_aethermoore`, then expose:

```toml
geoseal = "scbe_aethermoore.geoseal_cli:main"
scbe-geoseal = "scbe_aethermoore.geoseal_cli:main"
```

2. Keep PyPI as the Python library/package surface and document npm as the direct GeoSeal CLI surface.

Recommended for the next release:

```text
Publish npm as the direct GeoSeal CLI. Publish PyPI as the Python SCBE package only if its current console scripts pass the build/check gates. Add direct PyPI GeoSeal console commands in a separate, verified patch.
```

Reason:

```text
The current Python GeoSeal CLI is a large repo-root source file at src/geoseal_cli.py. It should not be exposed as a PyPI entry point until its installed-module path is confirmed.
```

## Publication rule

Do not publish to npm or PyPI until all are true:

- release branch choice is explicit;
- package version is frozen;
- npm pack guard passes;
- npm consumer smoke passes;
- PyPI build/check passes if publishing PyPI;
- GeoSeal smoke gates pass for the intended surface;
- the user explicitly says to publish.

## Summary recommendation

Clean order:

1. Resolve branch/release-base decision.
2. Run npm GeoSeal gates.
3. Publish npm `scbe-aethermoore@4.2.1`.
4. Run PyPI build/check gates.
5. Publish PyPI `scbe-aethermoore==4.2.1` only if current Python package checks pass.
6. Add direct PyPI `geoseal` console entry in a follow-up patch, unless we decide to make that part of `4.2.1` before either registry is published.
