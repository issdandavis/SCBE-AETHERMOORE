# Night Wrap and Tomorrow Queue - 2026-04-25

## Current Branch State

- Branch: `feature/cli-code-tongues`
- Recent committed work is safe and durable:
  - `734c05a3 feat(tokenizer): add accelerator route operator script`
  - `514733d5 feat(tokenizer): add photonic accelerator simulator lane`
  - `75adbb6f feat(training): add rule based stage eval rewards`
  - `35cc1305 fix(training): harden stage6 hf job for t4 memory`
  - `307bd461 feat(training): add stage6 atomic workflow lane`
- Worktree remains intentionally dirty. Do not run `git clean`, `git reset --hard`, or broad file moves.
- Snapshot files for this handoff were generated under:
  - `artifacts/worktree_snapshots/20260425_night_wrap/git_status_short.txt`
  - `artifacts/worktree_snapshots/20260425_night_wrap/git_diff_stat.txt`
  - `artifacts/worktree_snapshots/20260425_night_wrap/recent_commits.txt`

## High-Risk Worktree Buckets

- Private DARPA/MATHBAC packet removal is visible as tracked deletions under `docs/proposals/DARPA_MATHBAC/`.
- The private packet pointer is present at `docs/proposals/DARPA_MATHBAC/PRIVATE_PACKET_LOCATION.json`.
- Verified private packet root exists:
  - `C:\Users\issda\SCBE_PRIVATE\DARPA_MATHBAC\packet_20260424T194838`
  - 122 files, about 22.9 MB
- Tomorrow, before committing the MATHBAC deletion set, verify the private manifest and policy docs again:
  - `C:\Users\issda\SCBE_PRIVATE\DARPA_MATHBAC\packet_20260424T194838\PRIVATE_PACKET_MANIFEST.json`
  - `docs/proposals/DARPA_MATHBAC/README.md`
  - `docs/proposals/DARPA_MATHBAC/PRIVATE_PACKET_LOCATION.json`

## Training Status

- Stage 6 HF training job completed:
  - Job ID: `69ec604dd70108f37acde0d2`
  - URL: `https://huggingface.co/jobs/issdandavis/69ec604dd70108f37acde0d2`
  - Adapter repo: `issdandavis/scbe-coding-agent-qwen-atomic-workflow-stage6`
  - Dataset repo: `issdandavis/scbe-coding-agent-sft-stage6`
  - Base model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
  - Train rows used: 3,752
  - Eval rows used: 160
  - Global step: 320
  - Training loss: `0.6414492961019278`
  - Adapter pushed: `true`
- Do not call this successful until frozen smoke eval and reward scoring run.

## Tomorrow's First Commands

```powershell
python scripts\system\geoseal_coding_training_system.py dispatch-smoke-eval --profile-id coding-agent-qwen-atomic-workflow-stage6 --timeout 30m
```

Then score the produced report:

```powershell
python scripts\system\geoseal_coding_training_system.py score-smoke-report --report <report.json>
python scripts\system\geoseal_coding_training_system.py reward-smoke-report --report <report.json>
```

Use the frozen Stage 6 eval contract. Do not move thresholds after seeing outputs.

## Photonic Accelerator Lane

- Current working surface:
  - `src/tokenizer/accelerator_routing.py`
  - `scripts/system/accelerator_route.py`
  - `tests/tokenizer/test_accelerator_routing.py`
  - `docs/specs/PHOTONIC_ACCELERATOR_LANE.md`
- Verified:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests\tokenizer\test_accelerator_routing.py -q
python -m py_compile src\tokenizer\accelerator_routing.py scripts\system\accelerator_route.py
```

- Operator example:

```powershell
python scripts\system\accelerator_route.py --task-id lidar_phase_filter --workload optical_preprocess --matmul-fraction 0.35 --nonlinear-op-fraction 0.55 --precision-required-bits 12 --input-is-optical-signal --provider-optical-input-native --branching-density 0.02 --memory-access-density 0.08
```

## Dirty Tree Triage Order

1. Finish Stage 6 smoke eval and reward scoring before more training.
2. Commit MATHBAC private-packet relocation only after verifying the private manifest and repo README/pointer.
3. Separately review the huge `src/geoseal_cli.py` diff. Its import path timed out during accelerator CLI testing, so do not add more subcommands there until the import path is split or profiled.
4. Group tokenizer/code-lane untracked modules together, with focused tests before commit.
5. Group GitHub/docs/website changes separately from runtime code.
6. Leave generated artifacts and local snapshots uncommitted unless they are required evidence.

## Do Not Do Tonight

- Do not delete untracked files.
- Do not run broad formatting over the repo.
- Do not commit all dirty files together.
- Do not publish DARPA packet contents back into the open-source repository.
- Do not run another training job until Stage 6 eval tells us whether the adapter learned the frozen behaviors.
