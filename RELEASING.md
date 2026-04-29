# Releasing SCBE-AETHERMOORE

This repo ships three publishable artifacts:

| Artifact | Registry | Version source |
|----------|----------|----------------|
| `scbe-aethermoore` (npm) | <https://registry.npmjs.org> | `package.json#version` |
| `@issdandavis/scbe-aethermoore` (mirror) | <https://npm.pkg.github.com> | `package.json#version` (rewritten in CI) |
| `scbe-aethermoore` (PyPI) | <https://pypi.org> | `pyproject.toml#project.version` |

## Workflow

Releases are tag-driven. Pushing a tag of the form `vMAJOR.MINOR.PATCH` triggers
the chain in `.github/workflows/`:

1. **`release.yml`** — on tag push, creates a GitHub Release with auto-generated
   notes (commit log between the previous and current tag).
2. **`npm-publish.yml`** — fires on `release: published`. Publishes to
   `npmjs.org` (job `npmjs`) and to `npm.pkg.github.com` (job `github-packages`,
   which rewrites the package name to the scoped form `@issdandavis/scbe-aethermoore`
   in the build artifact only).
3. **`python-publish.yml`** — fires on `release: published`. Builds sdist+wheel
   and publishes to PyPI via OIDC Trusted Publishing. If `pyproject.toml`
   version doesn't match the tag, the publish step is skipped with a warning
   so a tag for an npm-only release doesn't try to push the wrong Python
   version.

## How to cut a release

1. Decide the version. Conventional rules apply: bump MAJOR for breaking
   changes, MINOR for backwards-compatible features, PATCH for fixes.
2. Update `package.json#version` (always) and `pyproject.toml#project.version`
   (only if the Python package is changing). Add a CHANGELOG.md entry under
   the new version heading.
3. Commit on a release branch and merge to `main` via PR.
4. Tag and push:

   ```bash
   git tag -a v<MAJOR>.<MINOR>.<PATCH> -m "Release v<MAJOR>.<MINOR>.<PATCH>"
   git push origin v<MAJOR>.<MINOR>.<PATCH>
   ```

5. The `release` workflow will create the GitHub Release. Once it's published,
   the `npm-publish` and `python-publish` workflows fire automatically.

## Required secrets / configuration

| Name | Used by | Purpose |
|------|---------|---------|
| `NPM_TOKEN` | `npm-publish.yml` (npmjs job) | npm registry auth (an automation token with publish access). |
| `GITHUB_TOKEN` | `npm-publish.yml` (github-packages job) | Provided by Actions; needs `packages: write` (set at workflow level). |
| PyPI Trusted Publisher binding | `python-publish.yml` | Configured at <https://pypi.org/manage/project/scbe-aethermoore/settings/publishing/>. Map this repo + the `python-publish.yml` workflow + the `release` environment (or none) to the project. |

If PyPI Trusted Publishing is not configured, swap the `pypa/gh-action-pypi-publish`
step to use a `password: ${{ secrets.PYPI_API_TOKEN }}` input and add the
secret.

## Manual / one-shot publishes

All three workflows expose `workflow_dispatch` with an optional `tag` input
so you can re-run a publish for an existing tag from the Actions UI.

## Catching GitHub Releases up to npm

If npm has versions that GitHub Releases doesn't (this happened around the
3.x → 4.x transition), the safe procedure is:

1. Find the commit that bumped `package.json` to that version
   (`git log -S '"version": "<X.Y.Z>"' -- package.json`).
2. Create the tag at that commit and push it.
3. The `release` workflow generates the Release. If the npm artifact is
   already published, you can either:
   - Skip `npm-publish` for that tag (delete the `release` event handler
     run from Actions, or manually mark it "Skip"),
   - Or re-publish the tarball from the tagged commit and let the version
     compare in `npmjs` job catch any mismatch.

## Version skew policy

`scbe-aethermoore`'s npm and PyPI versions have drifted in the past
(`CLAUDE.md` says "3.3.0 (npm + PyPI synced)" but as of the current `main`
that's npm `4.0.3` vs PyPI `3.3.0`). The publish workflows do not enforce
lockstep — each language publishes only when its version matches the tag.
This lets you ship a TS-only patch as `vX.Y.Z+1` without dragging the Python
package along.
