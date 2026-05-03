# Public Agentic CLI Benchmark Plan

This plan defines how GeoSeal can make public benchmark claims without
overstating local harness results.

## Current Claim

GeoSeal currently has publishable local evidence for command-line interface
governance and control-plane coverage. The local competitive harness score is
not a public coding-agent leaderboard result.

## Required Tracks

| Track | Purpose | Current Status | Public Claim Allowed |
| --- | --- | --- | --- |
| GeoSeal command-line interface competitive harness | Proves local command surface, machine JSON, permissions, custom commands, session state, and benchmark artifacts. | Wired | Local control-plane evidence |
| Terminal-Bench | Proves end-to-end terminal task completion through a public benchmark harness. | Adapter planned | No |
| SWE-bench Lite or Verified | Proves repository-level issue repair against public issue-to-patch tasks. | Adapter planned | No |
| Aider Polyglot | Proves multi-language code editing across C++, Go, Java, JavaScript, Python, and Rust. | Adapter planned | No |

## Run Commands

Validate the public benchmark plan:

```powershell
python scripts/benchmark/public_agentic_cli_suite.py --validate-only
```

Run the current executable public-evidence smoke:

```powershell
python scripts/benchmark/public_agentic_cli_suite.py --execute
```

Check whether the public benchmark harnesses are installed:

```powershell
python scripts/benchmark/setup_public_agentic_benchmarks.py --dry-run
```

Shallow-clone the public harness repositories without downloading benchmark
datasets:

```powershell
python scripts/benchmark/setup_public_agentic_benchmarks.py --download --dry-run
```

Run the local GeoSeal command-line interface competitive harness directly:

```powershell
python scripts/benchmark/cli_competitive_benchmark.py --json
```

## Evidence Bundle

The public suite writes:

- `artifacts/public_agentic_cli_suite/latest_report.json`
- `artifacts/public_agentic_cli_suite/latest_report.md`

The public benchmark setup script writes:

- `artifacts/public_agentic_benchmark_setup/latest_setup.json`
- `artifacts/public_agentic_benchmark_setup/latest_setup.md`

The local command-line interface harness writes:

- `artifacts/benchmarks/cli_competitive/cli_competitive_benchmark_latest.json`
- `artifacts/benchmarks/cli_competitive/cli_competitive_benchmark_latest.md`

## Claim Guardrails

Do not claim any of the following until the official public benchmark adapters
run and produce complete evidence packets:

- public Terminal-Bench leaderboard parity
- public SWE-bench leaderboard parity
- public Aider Polyglot leaderboard parity
- all-around best coding agent

## Next Implementation Steps

1. Terminal-Bench adapter: expose GeoSeal through the benchmark's agent runtime
   interface and run a small public task subset.
2. SWE-bench adapter: emit patches, logs, model/provider metadata, resolved
   rate, cost, and failure cases.
3. Aider Polyglot adapter: run the public Exercism-derived editing suite with a
   fixed model/provider budget.
4. Publish the resulting JSON, Markdown, patches, trajectories, and exact
   command lines.
