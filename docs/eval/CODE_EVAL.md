# SCBE Code Evaluation Harness

This harness measures whether a governance pass improves generated code outcomes relative to a baseline output.

## What it does

For each prompt case:

1. Generate a baseline code sample.
2. Run a governance decision over that code.
3. If the code is not allowed, issue one governed retry.
4. Score both baseline and final outputs with:
   - syntax check
   - runtime execution check
   - prompt-specific assertions
   - simple unsafe-pattern flags

## Current implementation status

The first version is intentionally lightweight and offline-first:

- Prompt fixtures live in `tests/fixtures/code_eval_prompts.json`
- Harness logic lives in `scripts/benchmark/scbe_code_eval.py`
- Smoke coverage lives in `tests/benchmark/test_scbe_code_eval_smoke.py`

To keep the harness usable without a running API server, the current version uses an **offline approximation** of the `/v1/authorize` decision contract. That means it preserves the same core fields:

- `decision`
- `score`
- `explanation`

but does not yet send real HTTP requests to `api.main`.

## Why this still helps

This gets a repeatable evaluation loop into the repo immediately so you can:

- compare baseline vs governed pass rates
- verify prompt fixtures and scoring logic
- plug in a real model provider later
- replace the offline authorize approximation with the real API surface in a small follow-up patch

## Run it

Dry-run summary:

```bash
python scripts/benchmark/scbe_code_eval.py --dry-run
```

Write results to JSON:

```bash
python scripts/benchmark/scbe_code_eval.py \
  --prompts tests/fixtures/code_eval_prompts.json \
  --output artifacts/scbe_code_eval_results.json
```

Run the smoke test:

```bash
pytest tests/benchmark/test_scbe_code_eval_smoke.py -v
```

## Metrics to watch

- `baseline_pass_rate`
- `final_pass_rate`
- `retry_rate`
- decision counts by `ALLOW` / `QUARANTINE` / `DENY`
- security flag count changes between baseline and final outputs

## Best follow-up patch

The next recommended step is to swap `authorize_generated_code()` from offline logic to one of these repo-native options:

1. direct call into the validated governance path already used by `/v1/authorize`
2. live request against a running local API server

That would turn this from a harness scaffold into a true SCBE-vs-baseline benchmark lane.
