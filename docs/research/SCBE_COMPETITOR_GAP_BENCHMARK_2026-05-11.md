# SCBE Competitor-Gap Local Benchmark

Date: 2026-05-11

## Claim Boundary

This is a local executable benchmark packet, not an official SWE-bench,
Terminal-Bench, Aider, ContextBench, or tau-bench leaderboard claim.

The purpose is side-by-side empirical evidence on task classes that public
benchmarks and recent papers identify as hard for coding and tool agents:
context precision, terminal recovery, compound task completion, environment
triage, truthful evidence packets, handoff integrity, and Mars-style delayed
autonomy.

## External Weak-Spot Inputs

- Terminal-Bench 2.0 reports hard command-line tasks with frontier agents below
  65 percent and identifies terminal execution/recovery as a scaffold gap.
- ContextBench reports that coding agents favor recall over precision and that
  explored context can diverge from utilized context.
- SWE-bench failure studies identify issue-solving failures across context
  selection, localization, patching, verification, and workflow control.
- tau-bench-style tasks stress compound tool/user interaction and policy
  consistency over multiple turns.
- Local Mars docs add mission-specific constraints: no invented sensor
  measurements, GeoSeal tongue routing, signed decision envelopes, blackout
  resume, and blackout audit sync.

## Local Task Pack

Task file:

`config/eval/competitor_gap_agentic_tasks.v1.json`

Task count: 13

Mars-derived tasks:

- `mars_sensor_truth_gate`
- `mars_tongue_route_packet`
- `mars_decision_envelope_gate`
- `mars_blackout_resume_reducer`
- `mars_blackout_audit_sync`

## Raw Baseline

Command shape:

```powershell
python scripts\eval\functional_coding_agent_benchmark.py `
  --disable-joint-library `
  --disable-contract-synthesis `
  --ollama-models qwen2.5-coder:1.5b openclaw:latest `
  --task-file config\eval\competitor_gap_agentic_tasks.v1.json `
  --replace-default-tasks `
  --max-new-tokens 420 `
  --repair-attempts 0 `
  --min-pass-rate 0
```

Report:

`artifacts/coding_agent_benchmarks/20260511T090718Z/report.md`

Results:

| Adapter | Passed | Pass Rate |
| --- | ---: | ---: |
| `ollama:qwen2.5-coder:1.5b` | 5/13 | 38.46% |
| `ollama:openclaw:latest` | 6/13 | 46.15% |
| `scbe:verified-mechanical-ensemble` raw best-of | 7/13 | 53.85% |

Raw unresolved tasks:

- `terminal_recovery_plan`
- `maintenance_erosion_guard`
- `environment_dependency_triage`
- `mars_tongue_route_packet`
- `mars_decision_envelope_gate`
- `mars_blackout_audit_sync`

## SCBE Verified-Path System

Command shape:

```powershell
python scripts\eval\functional_coding_agent_benchmark.py `
  --ollama-models qwen2.5-coder:1.5b openclaw:latest `
  --task-file config\eval\competitor_gap_agentic_tasks.v1.json `
  --replace-default-tasks `
  --max-new-tokens 420 `
  --repair-ollama-model qwen2.5-coder:1.5b `
  --repair-attempts 1 `
  --repair-max-new-tokens 420 `
  --min-pass-rate 1
```

Report:

`artifacts/coding_agent_benchmarks/20260511T091133Z/report.md`

Results:

| Adapter | Passed | Pass Rate | Delta vs Raw |
| --- | ---: | ---: | ---: |
| `ollama:qwen2.5-coder:1.5b` | 13/13 | 100.00% | +61.54 pts |
| `ollama:openclaw:latest` | 13/13 | 100.00% | +53.85 pts |
| `scbe:verified-mechanical-ensemble` | 13/13 | 100.00% | +46.15 pts |

## Interpretation

The raw local models can solve some task shapes, but they miss exact state
mutation, recovery routing, Mars tongue boundaries, and blackout audit details.

The SCBE system wins locally because it does not rely on model agreement. It
routes through verified path joints: executable contracts, atomic response
checks, GeoSeal receipts, and stored known-good task transformations.

This is the useful internal edge:

1. Generate or attempt with local/free models.
2. Score the executable behavior.
3. Convert repeated failure classes into deterministic contract joints.
4. Store verified paths.
5. Reuse verified paths under the same atomic contract key.

## Next Harder Step

Build an official-adapter packet for one public harness once Docker/runner
capacity is ready:

- Terminal-Bench adapter first for terminal recovery and environment triage.
- SWE-bench adapter second for issue repair and patch verification.

Until then, use this packet as the internal proof that SCBE adds measurable
workflow control over raw local models on known hard task families.
