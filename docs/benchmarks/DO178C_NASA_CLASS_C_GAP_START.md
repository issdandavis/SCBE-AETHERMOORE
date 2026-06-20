# DO-178C / NASA Class C Gap Start

Generated: 2026-05-29

Purpose: define the first practical target lane for moving SCBE from strong repo-level tests toward aerospace-style assurance discipline. This is not a certification claim. It is a gap map and work queue.

## Source Baseline

- FAA software/airborne electronic hardware pages identify airborne software policy and guidance for systems such as autopilots, flight controls, and engine controls, and list AC 20-115D for airborne software assurance using EUROCAE ED-12 and RTCA DO-178.
- NASA NPR 7150.2 establishes software engineering requirements for acquisition, development, maintenance, operations, and management. It uses `shall` statements with SWE requirement numbers, requirements mapping matrices, approved tailoring, software assurance, IV&V, and safety-critical software handling.
- NASA-STD-8739.8 is the software assurance and software safety standard referenced by NASA software engineering requirements.

Primary references:

- FAA Aircraft Certification Software and Airborne Electronic Hardware: https://www.faa.gov/aircraft/air_cert/design_approvals/air_software
- FAA Software and Airborne Electronic Hardware guidance list: https://www.faa.gov/aircraft/air_cert/design_approvals/air_software/software_regs
- NASA NPR 7150.2C: https://nodis3.gsfc.nasa.gov/displayAll.cfm?Internal_ID=N_PR_7150_002C_
- NASA software assurance resources: https://www.nasa.gov/intelligent-systems-division/software-management-office/nasa-software-engineering-procedural-requirements-standards-and-related-resources/

## Current SCBE Position

SCBE has strong ingredients:

- deterministic governance gates and receipts
- high-volume TypeScript/Python/Rust tests
- adversarial and ordered-stack benchmark artifacts
- agent-bus tool registry audit
- benchmark scorecards with explicit known flags
- runtime state persistence and allow/quarantine/deny decisions

But it is not yet DAL C / NASA Class C ready because the evidence is not organized as an assurance case.

## Gap Matrix

| Area | Current State | Gap | First Target |
| --- | --- | --- | --- |
| Requirements traceability | Tests and docs exist across many surfaces | No requirements-to-code-to-test matrix | Generate `requirements_trace_matrix.json` from curated requirements, modules, tests, and artifacts |
| Safety classification | Runtime gate has risk tiers | No NASA-style software class, safety-critical flag, or hazard link per component | Add `safety_classification_map.json` for agent-bus, runtime gate, tokenizer, video/control lanes |
| Verification independence | Tests are local and automated | No IV&V-style independent review record | Add review packet template with reviewer, evidence, finding, disposition, closure |
| Certification planning | Benchmark docs exist | No PSAC-style plan or tailoring rationale | Draft `software_assurance_plan.md` with scope, non-scope, lifecycle, verification methods |
| Low-level requirements | Code has behavior tests | No low-level requirement IDs tied to exact test assertions | Add `LLR-*` IDs for gate decisions, tool registry audit, runtime persistence, and DAA-lite targets |
| Structural coverage | TS/Python/Rust suites run | No statement of coverage objective or uncovered safety paths | Add coverage objective table before chasing percentages |
| Tool qualification | Benchmarks/tools generate evidence | No tool confidence/qualification boundary | Mark each script as evidence-generator, test-oracle, or operational tool |
| L13 latency | `scripts/benchmark/l13_runtime_fast_path.py` measures in-process RuntimeGate fast lanes | Agentic OS CLI p95 is still dominated by Python subprocess startup in cross-build cases | Keep L13 p95 under 100 ms and add separate cross-build batch/subprocess hardening |
| Runtime assurance | Gate can allow/deny/quarantine | No control-signal substitution proof against dynamics | Add proposed-control vs filtered-control benchmark fixture |
| Configuration management | Git and artifacts exist | Dirty tree and generated artifacts are mixed | Add release evidence manifest keyed by commit, commands, and artifact hashes |

## L13 Fast-Path Evidence

Command:

```bash
python scripts/benchmark/l13_runtime_fast_path.py --json
```

Latest local result:

```text
schema: scbe.l13_runtime_fast_path_benchmark.v1
cases: 240
decisions: ALLOW=60, REROUTE=120, DENY=60
p95: 0.1095 ms
threshold: 100 ms
status: PASS
```

Scope note: this validates the in-process runtime governance fast path only. The current Agentic OS CLI benchmark has a separate p95 problem because `geoseal cross-build` cases spawn Python processes for each sample; that needs batching or a resident worker and should not be conflated with L13 gate latency.

## First Four Build Targets

1. Requirements trace matrix

Output:

```text
artifacts/assurance/requirements_trace_matrix.json
docs/assurance/REQUIREMENTS_TRACE_MATRIX.md
```

Minimum fields:

```json
{
  "requirement_id": "HLR-GOV-001",
  "level": "HLR",
  "text": "The system shall prevent execution when the governance gate returns DENY.",
  "safety_relevance": "control-flow",
  "implementation_paths": ["packages/agent-bus/src/pipeline.ts"],
  "verification_paths": ["packages/agent-bus/tests/pipeline.test.ts"],
  "evidence_artifacts": ["packages/agent-bus/docs/benchmarks/agentic_os_cli_benchmark.json"],
  "status": "partial"
}
```

2. DAA-lite ownship/traffic benchmark

Output:

```text
scripts/benchmark/daa_lite_encounter_benchmark.py
tests/benchmark/test_daa_lite_encounter_benchmark.py
docs/benchmarks/DAA_LITE_ENCOUNTER_BENCHMARK.md
```

Minimum behaviors:

- ownship state
- intruder state
- time-to-boundary
- alert tier
- recovery maneuver
- batch fixture replay

3. Runtime assurance substitution fixture

Output:

```text
scripts/benchmark/runtime_assurance_control_filter.py
tests/benchmark/test_runtime_assurance_control_filter.py
```

Minimum behaviors:

- proposed control
- safety-filtered control
- substituted fallback control
- environment state before/after
- hazard avoided or not avoided
- signed decision receipt

4. SCBE Autonomy Reference Interface

Output:

```text
docs/specs/SCBE_AUTONOMY_REFERENCE_INTERFACE.md
tests/benchmark/test_autonomy_reference_interface.py
```

Minimum messages:

- `observe`
- `plan`
- `command`
- `veto`
- `explain`
- `receipt`

## Do Not Claim Yet

Do not claim:

- DO-178C compliance
- DAL C compliance
- NASA Class C compliance
- flight readiness
- drone deployment readiness
- detect-and-avoid equivalence to DAIDALUS

Allowed claim:

SCBE now has a reproducible target matrix and a first assurance gap plan for aerospace-style autonomy benchmarks.

## Immediate Next Command

Start with the trace matrix. It has the highest evidence leverage because it organizes existing tests before adding new control physics.
