# AI Browser Access (Local Validation)

This guide shows how to validate browser access to the SCBE visual system in a reproducible way.

## Goal

Confirm an automated browser can reach the local UI and render the app shell.

## Steps

1. Start the visual system dev server:

```bash
npm --prefix scbe-visual-system run dev -- --host 0.0.0.0 --port 4173
```

2. Run browser automation (Playwright/MCP) against:

```text
http://127.0.0.1:4173/
```

3. Capture evidence (title + screenshot).

## Expected Signals

- Page title resolves (example: `Gemini Ink`).
- Screenshot shows the desktop/app shell loaded.

## Troubleshooting

- If tests fail with PQC runtime errors (`liboqs` missing), keep browser validation independent from PQC tests.
- If you see `Unknown option `--runInBand`` from Vitest, use one of:
  - `npm --prefix scbe-visual-system run test:run`
  - `npm --prefix scbe-visual-system run test:serial`
  Vitest does not support Jest's `--runInBand` flag.
- Prefer backend fallback strategy for PQC in CI:
  1. `liboqs` (primary)
  2. `pypqc` / `pqcrypto` (fallback)
  3. deterministic mock backend for non-crypto test lanes

## Artifact Policy

Treat browser artifacts as operational validation only. They do not define canonical protocol behavior.
