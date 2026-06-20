# WHY_HERE

Files in this folder were moved here during the 2026-04 repo-shape reorg.
They are kept for history but are no longer referenced by tests, CI, npm
scripts, or the active scbe dispatcher (`scripts/windows/scbe.bat`).

Active root entry points that intentionally stayed at the repo root:

- `scbe.py` (used by CI: nightly-ops, overnight-pipeline)
- `scbe-cli.py` (used by `npm run cli` and `tests/test_turning_lane.py`)
- `scbe-agent.py` (used by `scripts/windows/scbe.bat agent`)
- `six-tongues-cli.py` (used by `tests/test_six_tongues_cli.py`,
  `tests/test_spiralverse_canonical_registry.py`)
- `enhanced_scbe_cli.py` (used by `tests/test_enhanced_scbe_cli.py`)

If you are bringing one of these files back to active use, restore the
original location and add a test or npm script that exercises it.
