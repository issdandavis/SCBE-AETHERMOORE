---
name: publish
description: Publish SCBE-AETHERMOORE to npm and/or PyPI. Handles tarball verification, version bumping, OTP/token auth, and pyproject.toml generation. Use when the user says "publish", "ship it", "push to npm", or "upload to PyPI".
user_invocable: true
---

# Publish SCBE-AETHERMOORE

Pre-publish cleanup + publish to npm and/or PyPI.

## Pre-Publish Checklist (always run first)

### 1. Tarball Audit
```bash
npm pack --dry-run 2>&1 | tail -15
```
Verify:
- **Zero** `.py`, `.pyc`, `.pyo`, `.zip` files
- **Zero** `.js.map` or `.d.ts.map` files
- **Zero** `vitest.config.*` files
- **No** `__pycache__/`, `.hypothesis/`, `.env*` directories
- Total files < 500 (flag if over)
- Packed size < 1 MB (flag if over)

### 2. Secret Scan
```bash
npm pack --dry-run 2>&1 | grep -iE '\.env|secret|credential|token|\.pem|\.key'
```
Must return empty. If any match, **STOP** and fix `.npmignore` or `files` field.

### 3. Version Check
Read `package.json` version. Compare with:
```bash
npm view scbe-aethermoore version 2>/dev/null
```
Ensure local version > published version.

### 4. Build Verification
```bash
npm run build
npm run typecheck
```
Both must exit 0.

### 5. Test Gate
```bash
npm test
python -m pytest tests/test_canonical_state.py tests/test_phdm_conservation.py -v --tb=short
```

## Publish Commands

### npm
```bash
npm publish --access public
```
If OTP required, prompt user.

### PyPI (optional)
Check if `pyproject.toml` exists. If not:
```bash
python -m build
python -m twine upload dist/*
```

## Post-Publish Verification
```bash
npm view scbe-aethermoore version
npm view scbe-aethermoore dist.unpackedSize
```

## Fix Patterns

### Source maps leaking
Add to `package.json` `files` field:
```json
"!dist/src/**/*.js.map",
"!dist/src/**/*.d.ts.map"
```

### Python files leaking
Add to `.npmignore`:
```
*.py
*.pyc
__pycache__/
```

### `files` vs `.npmignore` precedence
When `files` is set in `package.json`, it is the whitelist. `.npmignore` exclusions within whitelisted directories may not apply. Use negation patterns in `files` instead:
```json
"files": [
  "dist/src/**/*.js",
  "dist/src/**/*.d.ts",
  "!dist/src/**/*.js.map",
  "!dist/src/**/*.d.ts.map",
  "README.md",
  "LICENSE"
]
```
