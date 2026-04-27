# DSL Synthesis v2 Failure And v3 Fix

Date: 2026-04-26

## Failure

Kaggle stopped `issacizrealdavis/polly-auto-dsl-syn-v2` with:

```text
Your notebook was stopped because it exceeded the max allowed execution duration.
```

The logs show the run fell back to CPU:

```text
WARNING: No GPU
No GPU - CPU tiny-run (200 records, 1 epoch)
```

But the CPU fallback still honored the original `max_steps=460`. That meant the "tiny" fallback was not actually bounded. The run reached only about 70 percent after roughly 12 hours, so it could not finish inside Kaggle's wall-clock limit.

## Root Causes

- The launcher requested GPU through metadata but did not pass Kaggle CLI's `--accelerator` flag.
- The DSL lane was too large for a fallback path: `max_length=1024`, `max_steps=460`, `max_records=4900`.
- CPU fallback capped records but did not cap `MAX_STEPS`.
- The v2 lane had no dedicated eval files or early-stopping config.

## Fix

Added `dsl-synthesis-v3-fast`:

- `max_length=512`
- `max_steps=90`
- `max_records=1500`
- `lora_r=8`, `lora_alpha=16`, `lora_dropout=0.1`
- eval files configured
- early stopping configured with patience 2
- eval/save cadence every 10 steps

Also patched the shared Kaggle template:

- configurable eval/save steps
- CPU fallback now hard-caps `MAX_STEPS` to 30

Also patched the launcher:

- `push_kernel(..., gpu)` now passes Kaggle CLI `--accelerator gpu` for GPU runs.

## Rule

Do not relaunch `dsl-synthesis-v1` / `polly-auto-dsl-syn-v2` unchanged. Use `dsl-synthesis-v3-fast` when a GPU slot is free.
