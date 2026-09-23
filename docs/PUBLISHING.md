# Publishing SCBE packages

The root npm and PyPI packages are both named `scbe-aethermoore`. Google Cloud
Build and Cloud Run deployments are separate surfaces; their configuration is
not a prerequisite for registry releases. A package release does not publish the
desktop app, model weights, private datasets or the other packages in this repo.

## Release gates

1. Use a clean checkout. Update root package.json, its lockfile, pyproject.toml
   and src/scbe_aethermoore/__init__.py to the same unused version. Add release notes.
2. Run CI on the exact proposed commit. The protected Node 20 check builds/tests
   on Node 24 (required by Vitest 5), then exercises the installed package on Node 20.
   The runtime minimum is 20.19.0. Python consumers require Python 3.11+.
3. Inspect package contents and install the actual tarball/wheel in a clean consumer.
   Python's wheel is built from the sdist, not independently from the checkout.
   Imports and CLI commands run outside the repository with PYTHONPATH removed.
4. Merge with passing required checks. Tag that exact commit. Wait for the release
   workflow's native liboqs gate; it checks backend behavior, not FIPS certification.
5. Run the registry workflows. Their default is a dry run. Set `dry_run=false`
   only for an authorized release after the gates pass.
6. Verify both public registries serve the new version and test a fresh installation.
   Registry versions cannot be overwritten; correct a bad release with a new version.

Local package checks:

```sh
npm ci
npm run build
npm run publish:smoke:consumer -- --root-only
python -m build --outdir artifacts/pypi-dist
python -m twine check artifacts/pypi-dist/*
python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist
python scripts/check_wheel_entrypoints.py --dist-dir artifacts/pypi-dist
```

Use a new/empty output directory for each version. The wheel checker requires
exactly one wheel and one source distribution, and never deletes supplied artifacts.

Authorized publication after a verified tag, for example:

```sh
gh workflow run npm-publish.yml -f tag=v4.3.2 -f dry_run=false
gh workflow run pypi-publish.yml -f tag=v4.3.2 -f dry_run=false
```

npm publishes the tarball produced and tested by its consumer step. PyPI publishes
the same artifacts passed to the wheel checker. The workflows use repository
secrets NPM_TOKEN and PYPI_API_TOKEN where configured; secret presence alone does
not prove they are valid. npm also supports configured OIDC trusted publishing on
Node 24. Never print authentication material into logs. The GitHub Packages mirror
is separate and opt-in through `github_packages=true`.

References: [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/),
[PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/).
