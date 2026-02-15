# Publishing to npm (Human + AI Workflow)

This repo supports an AI-assisted release flow with human-controlled credentials.

## Recommended flow

1. Ask AI to prepare release changes and update docs/changelog.
2. Run publish preflight checks locally/CI.
3. Verify package contents with `npm pack --dry-run`.
4. Authenticate with npm token (`NPM_TOKEN`) in CI or local shell.
5. Publish once version is confirmed unique.

## Commands

```bash
# 1) Validate package and tests
npm ci
npm test
npm run build

# 2) Validate packaging scope
npm run publish:check
npm run publish:dryrun

# 3) Authenticate (if local)
npm whoami || npm adduser

# 4) Publish
npm publish --access public
```

## AI-safe model

- Let AI handle code/tests/docs and dry-run validation.
- Keep npm credentials outside AI context using CI secrets (`NPM_TOKEN`).
- Require a human approval step before publish.

## Common failure modes

- `ENEEDAUTH`: not logged in (`npm adduser` or set `NPM_TOKEN`).
- version already exists: bump `package.json` version and republish.
- unexpected files: update `package.json > files` and rerun `npm pack --dry-run`.
