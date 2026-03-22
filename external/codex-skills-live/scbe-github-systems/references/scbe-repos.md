# SCBE Repos (Local)

Assume Windows paths under `C:\Users\issda\...`. If paths differ, search for these folder names.

## SCBE-AETHERMOORE-working

Purpose: main development monorepo for SCBE-AETHERMOORE. TypeScript is canonical; Python is a reference/validation implementation.

Key docs and instructions:
- `SCBE-AETHERMOORE-working/CLAUDE.md` (AI/developer instructions, commands, conventions)
- `SCBE-AETHERMOORE-working/INSTRUCTIONS.md` (quick start, API endpoints, layer reference)
- `SCBE-AETHERMOORE-working/.cursorrules` (high-level architecture + patterns)
- `SCBE-AETHERMOORE-working/README.md`
- `SCBE-AETHERMOORE-working/SCBE_SYSTEM_OVERVIEW.md`
- `SCBE-AETHERMOORE-working/SYSTEM_ARCHITECTURE.md`
- `SCBE-AETHERMOORE-working/STRUCTURE.md`

Where code tends to live:
- `SCBE-AETHERMOORE-working/src/harmonic/` (14-layer pipeline)
- `SCBE-AETHERMOORE-working/src/crypto/` (envelope/PQC/etc.)
- `SCBE-AETHERMOORE-working/src/fleet/` (multi-agent orchestration)
- `SCBE-AETHERMOORE-working/src/api/` (FastAPI)
- `SCBE-AETHERMOORE-working/symphonic_cipher/` (Python reference implementations)

Common commands (prefer what the repo says if it differs):
- `npm install`
- `npm run build`
- `npm run typecheck`
- `npm test`
- `python -m pytest tests/ -v`
- `python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`

CI and automation:
- `SCBE-AETHERMOORE-working/.github/workflows/`
- `SCBE-AETHERMOORE-working/docker-compose.yml`
- `SCBE-AETHERMOORE-working/k8s/`

## scbe-ultimate

Purpose: smaller TypeScript repo centered around the `scbe-aethermoore` NPM package workflow (see its `README.md`).

Key files:
- `scbe-ultimate/README.md`
- `scbe-ultimate/package.json`
- `scbe-ultimate/src/`

Notes:
- If you need the full architecture, prefer `SCBE-AETHERMOORE-working` as the primary reference.
