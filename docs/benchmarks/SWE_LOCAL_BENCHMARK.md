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
npm run benchmark:swe-local-fixtures
```

This lane creates isolated broken mini-repositories, executes a no-repair
baseline, applies the SCBE repair harness, runs task-local pytest suites, and
records unified patch receipts plus edit-scope checks.

Current expected bracket:

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
