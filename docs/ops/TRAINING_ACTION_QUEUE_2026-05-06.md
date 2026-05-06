# Training Action Queue - 2026-05-06

Status: live operator snapshot after launch-route cleanup and topology harness parking.

## Current Live Run

HF job `69fb7223317220dbbd1a53da` is running:

- Profile: `scbe-coding-primary-7b-qlora-v6f`
- Flavor: `l4x1`
- Adapter repo: `issdandavis/scbe-coding-primary-7b-qlora-v6f`
- Packet: `artifacts/hf_coding_agent_jobs/scbe-coding-primary-7b-qlora-v6f/20260506T165343Z/job_packet.json`
- Idempotency key: `a038fa1580932da5ba047e2c6349d027b63fa3116eb7610f60065e84e7ea4eae`

Observed log tail:

```text
auth passed as issdandavis
trainable_parameters: 10,092,544 / 7,625,709,056 = 0.1323%
loss 3.299 -> 0.0489 by epoch 8.972
```

Do not dispatch another HF coding-primary run until this job reaches a final
state and its gate report is scored.

Monitor:

```powershell
python scripts/system/dispatch_coding_agent_hf_job.py status --job-id 69fb7223317220dbbd1a53da --json
hf jobs logs 69fb7223317220dbbd1a53da
```

After completion:

```powershell
python scripts/eval/score_agentic_training_system.py --hf-job-id 69fb7223317220dbbd1a53da --write --json
python scripts/system/night_training_watch.py --json --skip-kaggle-pull --test-timeout 300
```

## Merge / Promotion Decisions

Do not flat-merge adapters. Current evidence supports route-specific promotion:

1. `aligned-foundations-qwen-primary` is production-useful only with the
   constrained-decoding shim. Evidence: 257/257 with shim; no-shim failures are
   bias-bound.
2. `coding-approval-metrics-v3-marker-focus-scaffold-hf` remains the coding
   gate scaffold baseline. Evidence: pushed adapter and 5/5 scaffolded gate.
3. `coding-approval-metrics-v3-marker-dpo-hf` is promising but still hold-only
   until a larger frozen eval beats the scaffold route.
4. Failed no-shim runs become repair rows, not model promotion evidence.

## Kaggle Lane

Kaggle kernel `issacizrealdavis/polly-auto-coding-approval-metrics-v1` is in
`KernelWorkerStatus.ERROR`.

Local `ERROR.json` says the assigned GPU was `Tesla P100-PCIE-16GB` (`sm_60`),
but the round requires a modern CUDA worker. This is an infrastructure miss, not
a model-quality failure.

Retry only when ready to spend a Kaggle slot:

```powershell
python scripts/kaggle_auto/launch.py --round coding-approval-metrics-v3 --gpu t4 --poll --retry-modern-gpu 4
```

## Generated PR Queue

Queued for GitHub auto-merge, not admin-forced:

- PR #1379: research feed outputs
- PR #1380: daily stats badges
- PR #1382: latest agent monitor data

Closed as stale duplicate:

- PR #1381: older agent monitor data superseded by #1382

## Scorecard Read

`scripts/system/build_model_score_coordination_matrix.py --json` is healthy and
refreshes:

- `artifacts/training_hub/model_score_coordination_matrix.json`
- `artifacts/training_hub/model_score_coordination_matrix.md`

Night watch with the active HF job reports:

- HF: running
- Kaggle: attention required
- Bijective focused tests: 69/69 pass
- Rank: `Dungeon Clear`
- Overall: `72.4`
- Model promotion score: `76.9`

The score is dragged down by release-clean-board / dirty-tree state and packet
trace determinism, not by the focused bijective tests.

## Next Move

Wait for HF job `69fb7223317220dbbd1a53da` to finish, score it, then decide:

- promote if gate report passes and adapter push succeeds;
- mine residues if gate fails;
- do not rerun blindly if failure is continuation/scaffold mismatch rather than
  data floor.
