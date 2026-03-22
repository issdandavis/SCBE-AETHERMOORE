# Runtime Entrypoints

## First Commands

Use these to get oriented without changing code.

```powershell
Get-ChildItem -Name
Get-ChildItem -Name src
Get-ChildItem -Name scripts
Get-Content -Head 120 package.json
```

## Main Run Lanes

### TypeScript Package

```powershell
npm run build
npm run typecheck
npm test
```

Use this lane for:

- exported library surface
- harmonic and crypto modules
- TypeScript regressions

### Newer Python Control Plane

```powershell
python -m uvicorn src.api.main:app --reload --port 8000
```

Use this lane for:

- HYDRA router
- SaaS routes
- memory sealing MVP
- newer additive control-plane work

### Older Governance API

```powershell
python -m uvicorn api.main:app --reload --port 8080
```

Use this lane for:

- `/v1/authorize`
- agent registration
- audit, persistence, billing-adjacent flows

## Tests

```powershell
python -m pytest tests -q
python -m pytest tests\test_webtoon_quality_gate.py -q
python -m pytest tests\test_saas_api.py -q
```

Use targeted tests before broad suites.

## Operator Surface

```powershell
issac-help
hstatus
hdoctor
scbe-api
scbe-bridge
octo-serve
```

These aliases are defined through `scripts/hydra_command_center.ps1`.

## Webtoon Lane

```powershell
python scripts\webtoon_quality_gate.py --packet artifacts\webtoon\panel_prompts\ch01_prompts.json --auto-fix --rewrite-prompts --strict
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json --dry-run
python scripts\assemble_manhwa_strip.py --chapter ch01 --prefer-hq
```

## Interpretation Rules

- If the user wants product code, start in `src/`, `api/`, and `scripts/`.
- If the user wants the package surface, start in `package.json`, `src/index.ts`, and `dist/`.
- If the user wants runtime behavior, verify in the active Python or PowerShell entrypoint, not just in docs.
- If the repo feels contradictory, explain the lane split rather than pretending there is one canonical runtime for everything.
