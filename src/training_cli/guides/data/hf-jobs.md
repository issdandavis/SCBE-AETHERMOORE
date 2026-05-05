# HuggingFace Jobs

Cloud GPU dispatch via the HF `jobs` API. Where most SCBE training actually runs.

## When to use HF Jobs
- The model is too big for a local GPU (>= 1B params, batch > 1).
- You want reproducibility: the job script is captured in the repo, and the run lands as `training/runs/<run-name>/`.
- You want to run multiple specialists in parallel on different jobs.

## Don't use HF Jobs when
- The dataset has secrets that haven't been redacted.
- The base model is local-only (custom weights you haven't pushed).

## Dispatch pattern

The pattern lives in `scripts/system/dispatch_*_hf_job.py`. Each script:

1. Validates the dataset shape.
2. Uploads dataset (or references an existing repo).
3. Constructs the inline UV PEP-723 script with hardware + deps.
4. Calls `huggingface_hub.run_uv_job(...)` and prints the job_id.
5. Writes the run config to `training/runs/<run-name>/`.

After dispatch, the job_id is the handle for everything downstream:

```
python scripts/system/night_training_watch.py --hf-job-id <job-id> --json
```

## Verdict landing

When the job's regression eval finishes, it writes:

- `training/runs/<run-name>/eval/<job-id>.log` -- full job log
- `training/runs/<run-name>/eval/<job-id>_verdict.json` -- structured verdict (must_pass_all_ok, pass_rate, scaffold flag)

`training verdicts` reads these.

## Cost guardrails

Set `--max-cost-cents` if your dispatch script supports it. The default training jobs run ~50c-300c each. Always check `training status` after dispatch in case the job stalled.

## Common failure modes

| Symptom | Cause |
|---|---|
| Job exits in seconds | Bad UV script header / missing deps. Read the .log. |
| 0/5 must_pass after PASS during training | Dataset leakage; you trained on the eval set. |
| 5/5 PASS only with scaffold | The harness is carrying the gate; see DPO guide. |
| Never finishes / quota | HF account paid? Check at https://huggingface.co/settings/billing |
