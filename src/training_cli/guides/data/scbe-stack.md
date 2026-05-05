# SCBE Training Stack

SCBE-specific patterns: must-pass gates, scaffold dependency, the stage6 contract.

## The frozen gate

Every Stage 6 run is evaluated against `stage6_atomic_workflow_unseen_eval_v1`:

- 5 prompts total.
- `must_pass_all_ok` requires the 3 must-pass markers all PASS:
  - `stage6_unseen_resource_jump_cancel`
  - `stage6_unseen_lane_separation`
  - `stage6_unseen_hex_trace`
- `overall_pass` requires ALL 5 PASS.
- `pass_rate` = n_pass / 5.

Verdict shape:

```json
{
  "job_id": "...",
  "report": {
    "n_pass": 5, "n_total": 5,
    "must_pass_all_ok": true,
    "overall_pass": true,
    "constrained_gate_scaffold": false
  }
}
```

## constrained_gate_scaffold flag

If true, the harness prepended `required-items: A | B | C | ... ::` to every response. This guarantees canonical vocabulary appears in the substring check **regardless of what the model emits**. A scaffold-only PASS means:

- The model paired with the harness produces correct outputs.
- The model on its own does not.

A clean ship requires PASS with `constrained_gate_scaffold: false`. A harness-only PASS still ships if the deployed runtime always uses the harness (current SCBE production path).

## Recommended training cycle

1. Build SFT dataset via existing builders or new one.
2. Run preflight: `python scripts/system/preflight_zero_cost_training.py`.
3. Dispatch SFT HF Job.
4. Wait, then check `training status`.
5. If verdict fails: read the per-marker missing fields, build a DPO dataset that targets the failures.
6. Dispatch DPO on top of the SFT adapter.
7. Verify with AND without scaffold.
8. If scaffold-only PASS is acceptable for your deployment surface, ship.
9. If not, iterate on raw quality: more SFT echo data, lower LoRA rank, or a fresh base.

## Important read

`artifacts/colab_snapshots/local_runs_status_*.md` is the running scoreboard. Every run lands there, with the honest verdict (gate-pass vs scaffold-only-pass vs fail). Always update it when you push a new run; it is your one-stop "what has been tried, what worked" view.
