# SCBE Local SWE-Style Benchmark

Status: executable offline benchmark lane.

This is not an official SWE-bench Verified score. It is a repo-native,
SWE-style functional coding benchmark that checks issue triage, patch status,
terminal recovery, context budgeting, claim guarding, and related coding-agent
control behavior through executable TypeScript `evaluate(input, state)` tasks.

## Commands

```bash
npm run benchmark:swe-local
npm run benchmark:swe-local-fixtures
npm run benchmark:swe-verified:readiness
```

## Latest Local Result

Command:

```bash
npm run benchmark:swe-local
```

Result:

```json
{
  "ok": true,
  "claim_boundary": "local_swe_style_not_official_swe_bench_verified",
  "results": [
    {
      "adapter": "stub-null-control",
      "tasks": 12,
      "passed": 12,
      "pass_rate": 1.0
    }
  ],
  "mechanical_ensemble": {
    "tasks": 12,
    "passed": 12,
    "pass_rate": 1.0,
    "unresolved_tasks": []
  }
}
```

Report artifacts:

- `artifacts/swe_local_benchmark/latest/report.json`
- `artifacts/swe_local_benchmark/latest/report.md`
- `artifacts/swe_local_benchmark/latest_summary.json`
- `artifacts/swe_local_benchmark/latest_summary.md`

## Local Real-Patch Fixture Lane

Command:

```bash
# Deterministic harness only (default, no API key required)
npm run benchmark:swe-local-fixtures

# Live agent lane — Cerebras llama-3.3-70b (requires CEREBRAS_API_KEY)
npm run benchmark:swe-local-fixtures:cerebras

# Live agent lane — Groq llama-3.3-70b-versatile (requires GROQ_API_KEY)
npm run benchmark:swe-local-fixtures:groq
```

Or directly with `--provider`:

```bash
python scripts/benchmark/real_patch_task_benchmark.py --provider cerebras
python scripts/benchmark/real_patch_task_benchmark.py --provider groq
```

This lane creates isolated broken mini-repositories, executes a no-repair
baseline, applies the repair harness, runs task-local pytest suites, and
records unified patch receipts plus edit-scope checks.

There are two repair modes:

| Mode | Description | Requires |
|---|---|---|
| `scbe_repair` (default) | Deterministic harness — hardcoded correct fixes for each task. Proves the harness wiring works. | Nothing |
| `agent_repair` (`--provider`) | Live AI model call via OpenAI-compatible API. The model is given the issue, broken source, and test content and asked to return the repaired file. | `CEREBRAS_API_KEY` or `GROQ_API_KEY` |

**Note**: The agent lane provides test content in the prompt. Pass rate may overstate
generalization to held-out tests where test expectations are not visible.

Current expected bracket (deterministic lane):

```text
direct no-repair baseline: 0 / 5 tests pass
SCBE repair harness: 5 / 5 tests pass
```

Report artifacts:

- `artifacts/benchmarks/real_patch_tasks/latest_report.json`
- `artifacts/benchmarks/real_patch_tasks/LATEST.md`

## Official SWE-bench Verified Readiness

Command:

```bash
npm run benchmark:swe-verified:readiness
```

Current local readiness:

```json
{
  "official_swe_bench_verified_local_ready": false,
  "missing_or_failed": ["docker", "swebench_harness"]
}
```

That means official SWE-bench Verified parity is not claimed from this machine
yet. The next route is either installing Docker plus the SWE-bench harness
locally or using a Linux/GitHub Actions runner with Docker.
