# Release Readiness Tracker - 2026-04-23

This tracker applies the current GitHub release standard to the repo as it exists today.

Authority:

- [docs/specs/GITHUB_RELEASE_STANDARD.md](../specs/GITHUB_RELEASE_STANDARD.md)

## Scope

Current public release objects:

1. `npm package`
2. `GitHub Pages / docs`
3. `backend API`
4. `frontend app`

## Status Summary

| Object | Status | Notes |
| --- | --- | --- |
| npm package | `partial` | install/build path is now working, but public surface is still broader than ideal |
| GitHub Pages / docs | `partial` | canonical workflow and publish-surface checks exist, but docs warnings and overall release discipline remain |
| backend API | `partial` | secret boot path and auth fallback were hardened, but middleware/runtime deployment shape still needs tightening |
| frontend app | `partial` | API target is now deploy-configurable, but the app is still a CDN-first prototype without a production asset pipeline |

## Open Blockers

### 1. Backend runtime hardening follow-through

- file: `src/api/main.py`
- previous blocker: startup auto-loaded `.secrets/env.local`
- current state: fixed; local secret loading now requires explicit `SCBE_LOAD_LOCAL_SECRETS=1`
- remaining work: document deploy env requirements and replace in-memory limiter for multi-instance use

### 2. Backend auth deployment discipline

- file: `src/api/auth_config.py`
- previous blocker: demo keys could activate when environment mode was not pinned correctly
- current state: fixed; demo keys now require explicit `SCBE_ALLOW_DEMO_KEYS=1`
- remaining work: remove any ambiguity between local test/demo use and deploy-time key provisioning in release docs

### 3. Frontend production packaging

- files:
  - `app/index.html`
  - `app/server.ts`
- previous blocker: hardcoded `http://localhost:3000`
- current state: fixed; app target now resolves from query param, window config, meta tag, same-origin, or file fallback
- remaining work: convert the frontend into an intentional build artifact with pinned assets instead of CDN-first prototype delivery

### 4. npm public surface minimization

- files:
  - `package.json`
  - `src/index.ts`
- blocker: current package ships broad compiled internals to satisfy runtime dependencies
- required fix: define a minimal intended SDK surface and stop shipping extra internals by accident

### 5. Middleware and multi-surface deployment consistency

- files:
  - `src/api/main.py`
  - `agents/browser_agent.py`
  - `agents/browsers/base.py`
  - `agents/browser/main.py`
- current state: API and browser clients now accept and emit the same primary `x-api-key` contract, with legacy `SCBE_api_key` compatibility kept for transition
- remaining work: add one documented end-to-end browser-to-API smoke path and decide which legacy lanes remain supported versus frozen

## Verified Good So Far

### npm

- `npm run publish:check:strict` passes
- `npm run typecheck` passes
- `npm pack` passes
- fresh install smoke works from a generated tarball

### docs

- Pages workflow is consolidated around `.github/workflows/docs.yml`
- publish surface validator exists
- missing support/redteam pages were added

### backend and frontend hardening

- `src/api/main.py` no longer auto-loads `.secrets/env.local` unless `SCBE_LOAD_LOCAL_SECRETS=1`
- `src/api/auth_config.py` now fails closed by default and only enables demo keys with `SCBE_ALLOW_DEMO_KEYS=1`
- `src/api/main.py` accepts `x-api-key` and legacy `SCBE_api_key`, and exposes both `/health` and `/v1/health`
- `agents/browser_agent.py` and `agents/browsers/base.py` now use `x-api-key`, fail fast when no API key is configured, and try versioned/non-versioned endpoints
- `agents/browser/main.py` no longer ships baked-in browser test keys
- `app/index.html` now resolves its API base from deploy config instead of hardcoded localhost
- focused verification passed:
  - `python -m pytest tests/contracts/test_auth_config.py tests/contracts/test_src_api_header_compat.py tests/smoke/test_app_deploy_config.py tests/integration/test_cli_api_consistency.py tests/test_mobile_goal_api.py -q`
  - `15 passed`
  - `npm run build`
  - `npm run typecheck`

## Exit Criteria For First Real GitHub Release

The repo can be called `release ready` only when all of these are true:

- backend no longer auto-loads local secret files
- backend auth fails closed outside local development
- frontend points to a deploy-configured backend target
- one documented app-to-backend smoke path passes
- public npm surface is intentionally scoped
- release issue has exact command evidence attached
