# Handoff: HYDRA Formation Alias Lane Fix

## Status
- Current phase: implemented and verified
- Completion: first runtime lane fix complete

## Context
- The HYDRA skill surfaces and external OctoArms dispatcher used formation names that did not match the repo runtime.
- Skill/operator language:
  - `hexagonal-ring`
  - `ring`
  - `scatter`
- Repo runtime previously accepted only:
  - `hexagonal`
  - `tetrahedral`
  - `concentric`
  - `adaptive-scatter`
- This caused drift between the skills, the external wrapper, and `scripts/scbe-system-cli.py flow plan`.

## Decisions
- Fixed the repo runtime first instead of editing more notes or only patching the external Codex-home skill wrapper.
- Added alias normalization inside `scripts/scbe-system-cli.py` so the planner accepts both canonical and skill-level names.
- Added a repo-owned dispatcher at `scripts/system/octoarms_dispatch.py` so OctoArms lane dispatch is no longer trapped outside the repo.
- Kept packet outputs canonical while preserving the original operator input as `requested_name` or `requested_formation`.

## Files Touched
- [scripts/scbe-system-cli.py](C:\Users\issda\SCBE-AETHERMOORE\scripts\scbe-system-cli.py)
  - Added `FLOW_FORMATION_ALIASES`
  - Added `_normalize_flow_formation()`
  - Normalized `flow plan` inputs before agent/packet generation
  - Expanded CLI choices to include skill-facing aliases
  - Stored both canonical and requested formation names in the flow packet/result
- [scripts/system/octoarms_dispatch.py](C:\Users\issda\SCBE-AETHERMOORE\scripts\system\octoarms_dispatch.py)
  - New repo-owned OctoArms/HYDRA dispatcher
  - Accepts skill-facing formation aliases
  - Runs flow plan + packetize and selected lane
  - Writes summary under `artifacts/octoarms_dispatch/`
- [tests/test_scbe_system_cli_flow.py](C:\Users\issda\SCBE-AETHERMOORE\tests\test_scbe_system_cli_flow.py)
  - Added regression coverage for `hexagonal-ring`, `ring`, and `scatter`
- [tests/test_octoarms_dispatch.py](C:\Users\issda\SCBE-AETHERMOORE\tests\test_octoarms_dispatch.py)
  - Added regression test for repo-owned dispatcher alias handling

## Verification
- Command run:
```powershell
pytest tests/test_scbe_system_cli_flow.py tests/test_octoarms_dispatch.py -q
```
- Result:
  - `4 passed`

## Smoke Run
- Command run:
```powershell
python scripts/system/octoarms_dispatch.py --task "lane alias smoke" --formation hexagonal-ring --lane octoarmor-triage --no-action-map --json
```
- Confirmed behavior:
  - accepted `hexagonal-ring`
  - normalized runtime formation to `hexagonal`
  - preserved `requested_formation` in output
  - wrote OctoArms summary/artifacts into repo

## Open Questions
- The external skill wrapper at `C:\Users\issda\.codex\skills\octoarms-hydra-model-swarm\scripts\octoarms_dispatch.py` still has the old parser choices and should be updated or pointed at the repo-owned dispatcher.
- `ring -> concentric` is the safest first mapping, but if a strict ordered attestation ring needs different runtime geometry later, add a distinct canonical formation instead of overloading `concentric`.
- The next likely runtime improvement is adding explicit mode support on top of formation, not more alias work.

## Next Steps
1. Point the OctoArms skill or quick aliases at `scripts/system/octoarms_dispatch.py`.
2. Add explicit `mode` handling to the repo dispatcher and planner if you want skill/runtime parity for formation + mode together.
3. Decide whether the external Codex-home skill script should be patched or deprecated in favor of the repo-owned dispatcher.
4. Keep future lane work scoped to runtime improvements first, note work second.
