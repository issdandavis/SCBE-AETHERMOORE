# Repo Path Dependency Matrix (Phase 0)

This matrix inventories path-sensitive launch/build/test surfaces that must be updated together during migration.

## Core Entry Surface

| owner file | dependency type | current path assumptions | risk if moved |
| --- | --- | --- | --- |
| `package.json` | npm scripts | `scripts/`, `src/`, `tests/`, `artifacts/`, `workflows/n8n/`, `config/`, `dist/` | high |
| `scripts/scbe_bootstrap.mjs` | bootstrap | `requirements.txt`, `node_modules`, root `npm run build` | medium |
| `scripts/system/run_core_python_checks.py` | python test gate | rooted `tests/...` lanes and `artifacts/system-audit` output | high |
| `.github/workflows/ci.yml` | CI gate | root commands + fixed path checks | high |
| `.github/workflows/scbe-tests.yml` | CI gate | `symphonic_cipher/tests/...` and root python setup | high |
| `.github/workflows/scbe.yml` | CI gate | root runtime and python command paths | high |

## Launch Surface

| owner file | launch role | path assumptions | port assumptions |
| --- | --- | --- | --- |
| `scripts/system/start_aetherbrowser_extension_service.mjs` | browser lane start | `src/extension`, `artifacts/system`, `scripts/verify_aetherbrowser_extension_service.py` | 8002, 9222 |
| `scripts/system/stop_aetherbrowser_extension_service.mjs` | browser lane stop | `artifacts/system/aetherbrowser_extension_service_pids.json` | n/a |
| `scripts/verify_aetherbrowser_extension_service.py` | browser lane verify | `artifacts/smokes/...` report output | 8002, 9222 |
| `scripts/system/start_aether_native_stack.ps1` | local stack start | `aetherbrowse/`, `artifacts/system`, python module entrypoints | 8400, 8401 |
| `scripts/system/start_aether_phone_mode.ps1` | phone mode start | `kindle-app/www`, `scripts/system/serve_kindle_www.mjs`, `artifacts/system` | 8088, 8400 |

## Policy-Critical Paths for Scanner Coverage

The path scanner must detect hardcoded references to:

- `artifacts/`
- `deploy/`
- `k8s/`
- `training-data/`
- `scripts/`
- `docs/`
- `.github/workflows/`
- absolute `C:\Users\issda\...` patterns

## Freeze Contract Reference

See `docs/architecture/REPO_RESTRUCTURE_PHASE0_PHASE1_CONTRACT.md` for do-not-move roots and migration gating criteria.
