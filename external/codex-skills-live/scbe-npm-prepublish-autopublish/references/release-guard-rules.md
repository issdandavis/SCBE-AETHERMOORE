# Release Guard Rules

## Local prepublish gate

1. Run `npm run publish:prepare`.
2. Run `npm test`.
3. Run `npm run publish:check:strict`.

## Auto-publish gate

In `.github/workflows/auto-publish.yml`, run the same sequence before `npm publish`.

## Failure handling

- If tarball guard fails, inspect output and remove matching files from package scope.
- If required files are missing, run build and verify `dist/src/index.js` and `dist/src/index.d.ts` exist.
- If cleanup removes expected files, adjust `scripts/npm_prepublish_cleanup.js` target list.
