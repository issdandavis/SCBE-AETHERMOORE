# Release Readiness - 2026-04-27

Status: in-progress, package guards restored.

## GitHub / CI

- PR #1221 merged: route-first evaluation controls and agent-router Pages deployment wiring.
- PR #1222 merged: Python release-gate fixes for formatting and choral render compatibility.
- Latest `main` dependency-submission runs are passing. The earlier dependency-submission failure was a GitHub API snapshot submission error after local dependency discovery had succeeded.
- The remaining PR-check failure observed on #1222 was Ruff lint. Local fixes were staged for the same lint class:
  - unused variables/imports in research, tokenizer, API, security, and browser tests;
  - unused loop variables renamed;
  - Black formatting re-applied after Ruff fixes.

## npm

Readiness: pass.

Command:

```powershell
npm run publish:check:strict
```

Result:

- `npm pack --dry-run --json` succeeds.
- `scripts/npm_pack_guard.js` reports clean package contents.
- Tarball observed: `scbe-aethermoore-4.0.3.tgz`, 1275 entries, about 1.65 MB.

No npm publish was run.

## PyPI

Readiness: guarded build path restored.

Commands:

```powershell
npm run publish:pypi:build
npm run publish:pypi:check
```

Result:

- Clean build now removes stale `build/`, `src/build/`, and `src/scbe_aethermoore.egg-info` before creating artifacts.
- `scripts/pypi_dist_guard.py` validates the wheel and source distribution for generated build trees, cache files, secret/config paths, repo artifacts, and missing wheel metadata.
- Built artifacts:
  - `artifacts/pypi-dist/scbe_aethermoore-4.0.3-py3-none-any.whl`
  - `artifacts/pypi-dist/scbe_aethermoore-4.0.3.tar.gz`
- Guard result: upload-safe.

Known warnings to resolve before a polished public release:

- Setuptools still warns that `scbe` is configured as a root `py-module` while the active package discovery expects `src/scbe.py`.
- Setuptools warns that `api.darpa_prep` is importable but not explicitly declared in package configuration.
- The wheel contains three validation-named modules under `symphonic_cipher/scbe_aethermoore/`: `layer_tests.py`, `patent_validation_tests.py`, and `test_scbe_system.py`. The guard reports these as warnings, not blockers.

No PyPI upload was run.

## Docker

Readiness: local build not verified in this pass; remote build path added after local storage constraint was confirmed.

Command:

```powershell
npm run docker:doctor:api
```

Result:

- Blocked locally because Docker Desktop / Docker Engine is not reachable.
- Local blocker is expected on this machine because Docker is not set up and there is not enough local disk headroom.

Remote fallback:

```powershell
npm run docker:remote:api
```

This dispatches the `Remote Docker Build` GitHub Actions workflow. It builds `Dockerfile.api` on a GitHub-hosted runner and runs the API health smoke test without using local disk. It does not push an image by default.

Optional GHCR push, only when explicitly wanted:

```powershell
npm run docker:remote:api:push
```

Packaging note:

- `Dockerfile.api` remains the safer production-facing container path and is now the remote-build target.
- The root `Dockerfile` still contains `npm run build || true`, which can hide TypeScript build failures. This should be removed or split into an explicit best-effort development image before treating the root image as release-grade.

## GitHub Pages

Readiness: live site reachable; agent-data deployment path improved.

- Main Pages site and `agents.html` were reachable during this pass.
- Agent Router now includes direct Pages deployment wiring so router-published data does not depend on a separate push-triggered Pages workflow from `GITHUB_TOKEN`.
- Needs next Agent Router run or manual workflow run to verify the direct Pages artifact deploy end-to-end.

## Training / Model Release

Readiness: not a release artifact yet.

- Training outputs remain gate-based and should not be flattened, quantized, pushed, or merged without frozen-eval proof.
- Route-first evaluation remains the safer current operating model until the adapters pass executable and frozen-eval gates.

## Current Recommendation

Treat npm and PyPI as package-ready after the current release-guard branch lands. Treat Docker and model-release channels as blocked until Docker Engine is available and model gates pass. Do not publish externally from this report alone.
