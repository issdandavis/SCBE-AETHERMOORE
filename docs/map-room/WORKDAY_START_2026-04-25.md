# Workday Start Tracker - 2026-04-25

## Current Operating State

- Time context: morning work-start pass, April 25, 2026.
- Branch: `feature/cli-code-tongues`.
- Live npm package: `scbe-aethermoore@4.0.3`.
- Published CLI bins verified from a fresh install: `geoseal` and `scbe-geoseal`.
- Continuous cash sprint state: cycle `1`, completed `1`, blocked `0`, remaining `5`.
- Disk headroom: about `27 GB` free on `C:`.

## Release Proof Already Landed

Recent pushed commits:

- `901b2a30 feat(geoseal): add CLI agent bus cash loop`
- `d87658c5 chore(npm): refresh lockfile for geoseal release`
- `e586d218 test(npm): accept normalized geoseal bin path`
- `a471d2e8 feat(revenue): cycle cash sprint state machine`

Verified commands:

- `npm view scbe-aethermoore version bin dist-tags --json`
- fresh install smoke: `npx geoseal --help`, `npx scbe-geoseal --help`, `npx geoseal version`
- `python -m pytest tests/revenue/test_daily_cash_sprint.py tests/smoke/test_npm_geoseal_bin.py -q`
- `npm run publish:check:strict`
- `npm run cash:sprint:watch -- --offer local_ai_command_center_setup`

## Worktree Reality

Current dirty tree shape from `git status --short`:

- Total changed entries: `426`
- Modified: `243`
- Untracked: `156`
- Deleted: `27`

Largest buckets:

- `notes/`: `120`
- `docs/`: `85`
- `tests/`: `62`
- `src/`: `49`
- `scripts/`: `45`
- `config/`: `12`
- `.github/`: `11`

## Cleanup Rule For Today

Do not run broad reset, checkout, or clean commands. The tree contains mixed product, notes, proposal separation, tokenizer research, and generated training work. Use narrow commits only.

Safe operating pattern:

1. Pick one lane.
2. Run targeted status for that lane.
3. Commit only files from that lane.
4. Leave unrelated dirty files untouched.

## High-Risk Items To Preserve

- `docs/proposals/DARPA_MATHBAC/` has many deleted entries because MATHBAC material was moved/private-separated. Do not restore or remove blindly; use `docs/proposals/DARPA_MATHBAC/README.md` and `PRIVATE_PACKET_LOCATION.json` as the pointer lane.
- `src/geoseal_cli.py` is heavily modified and mixed. Do not stage the whole file casually.
- `tests/smoke/test_geoseal_service.py` depends on the current service-command work and should wait until the matching `src/geoseal_cli.py` hunks are isolated.
- `notes/` and `training-data/` include useful research/corpus material; do not clean as cache.

## Today Priority Stack

1. Keep the live CLI useful: continue using `npm run cash:sprint:watch` as the never-stop local wave.
2. Isolate the GeoSeal service CLI hunk and land its smoke test.
3. Convert the EML/operator research into source-faithful experiments, not claims.
4. Use the agent bus for actual repo tasks: publish readiness, file triage, test failure diagnosis, outreach drafts.
5. Defer broad doc cleanup until each lane has one authority note.

## Next Commands

```powershell
npm run cash:sprint:watch -- --offer local_ai_command_center_setup
git status --short -- src/geoseal_cli.py tests/smoke/test_geoseal_service.py
python -m pytest tests/revenue/test_daily_cash_sprint.py tests/smoke/test_npm_geoseal_bin.py -q
```

