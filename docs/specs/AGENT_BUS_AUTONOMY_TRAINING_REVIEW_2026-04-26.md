# Agent Bus Autonomy Training Review

Date: 2026-04-26

## Scope

This review covers the SCBE agent bus, HYDRA packet rails, and drone-inspired coordination notes as software orchestration patterns. It does not define weapon behavior, targeting, evasion, or field tactics. The useful transfer is: train and gate autonomous software like safety-critical autonomy, with rehearsal before live action, telemetry, holdouts, and abort rules.

## Current SCBE Surfaces

- `scripts/system/mirror_room_agent_bus.py` schedules providers as player, watcher, and rest lanes using privacy, cost, capability, and fatigue.
- `scripts/system/agentbus_pipe.mjs` exposes the bus as a pipeable event-in/result-out endpoint.
- `scripts/scbe-system-cli.py agentbus run` is the current user-facing route that writes `latest_round.json`, watcher state, tracker snapshots, and dispatch summaries.
- `schemas/hydra_comms_packet_v1.schema.json` already has fields for `mission_id`, `intent`, `status`, `rails`, `ledger`, `lease`, `gates`, and optional Layer 14 signal metadata.
- `tests/test_agentbus_user_e2e.py` and `tests/test_mirror_room_agent_bus.py` already prove routing, watcher, dispatch, and operation-shape behavior.

## Findings

1. The bus is routeable and testable, but it does not yet enforce a mission rehearsal gate before dispatch.
2. HYDRA packet schema has the right control vocabulary, but the agent bus runtime does not yet require mission envelope fields such as telemetry sinks, abort rules, leases, or independent holdout status.
3. The mirror-room scheduler correctly prevents watcher recursion, but it does not yet produce a pass/fail readiness label that can feed the operator-agent-bus training lane.
4. Provider selection is cost/privacy aware, but it is not yet outcome-aware across a mission series beyond simple fatigue.
5. The current design is strongest as a command-and-control bus for AI work, not as a physical drone-control system.

## Public Research Patterns To Transfer

- NASA trusted autonomy work emphasizes onboard autonomy when communication windows and decision cadence make constant human control impractical. Transfer: the bus needs bounded local decision authority when remote providers are unavailable.
- NASA Resilient Autonomy uses runtime monitors and safe abort/return behavior around untrusted guidance logic. Transfer: every nonlocal bus round should declare telemetry and abort conditions before execution.
- NASA near-real-time verification and validation for autonomous flight uses standardized data attributes plus automated real-time or post-run verification. Transfer: every bus run should emit standardized telemetry that can be replayed and scored.
- DARPA OFFSET emphasized human-swarm teaming and a virtual environment where swarm behaviors can be explored and evaluated before use. Transfer: run simulated bus rounds and score formations before spending remote tokens.
- PX4 uses Software-in-the-Loop and Hardware-in-the-Loop simulation before real-world flight. Transfer: SCBE should use local dry-run and strict rehearsal gates before remote/live agent dispatch.
- DoD AI-enabled autonomy test guidance separates training, validation, test, and independent test data, and requires operationally representative data and integrated system evaluation. Transfer: agent-bus adapters should be trained on route records, validated on similar records, and promoted only after independent frozen tests.
- NIST AI TEVV notes that measurement depends on operating context. Transfer: coding, research, governance, and training lanes need different pass/fail metrics instead of one global score.

## Improvement Added

`scripts/system/agentbus_rehearsal_gate.py` now evaluates agent-bus rounds before treating them as ready. It checks:

- task presence and task type,
- selected provider and primary lane,
- watcher/rest lane availability,
- anti-amplification policy,
- budget conformance,
- privacy versus provider class,
- deterministic operation-shape binary and hex signatures,
- telemetry sink and abort condition for strict or remote/live rounds.

The output is a compact pass/fail report with labeled checks. This creates training records from real bus operations without exposing raw prompts.

The gate is also available directly through the user-facing endpoint:

```powershell
python scripts\scbe-system-cli.py agentbus run --task "<goal>" --operation-command "korah aelin dahru" --task-type coding --privacy local_only --budget-cents 0 --dispatch --rehearsal-gate --json
```

For remote/live-style rehearsals, use `--strict-rehearsal-gate` with `--telemetry-path` and `--abort-condition`.

## How This Helps The System

- It makes the bus safer: remote/live dispatch can be blocked if it lacks telemetry or an abort rule.
- It makes the bus more trainable: every round gets a readiness label and check vector.
- It makes provider routing measurable: future routing can use pass rate, failure class, latency, and cost rather than static strengths only.
- It maps drone autonomy training into AI operations without copying dangerous physical tactics.
- It creates a direct bridge from bus execution to `operator_agent_bus` datasets.

## Next Build Steps

1. Wire `agentbus_rehearsal_gate.py` into `scripts/scbe-system-cli.py agentbus run` behind `--rehearsal-gate`.
2. Add `mission_id`, `telemetry`, `abort_condition`, and `lease_seconds` flags to the agentbus CLI.
3. Write gate reports beside `run_summary.json` under `artifacts/agent_bus/user_runs/<series_id>/`.
4. Add a dataset exporter that converts gate reports into SFT and multiple-choice records.
5. Add a mission-series scoreboard that updates provider route weights from gate pass rate, executable result score, latency, and cost.

## Sources

- NASA NESC, "Verification and Validation Challenges for Autonomous GNC Technology for NASA's Next-Generation Missions": https://www.nasa.gov/centers-and-facilities/nesc/verification-and-validation-challenges-for-autonomous-gnc-technology-for-nasas-next-generation-missions/
- NASA Armstrong, "Autonomous Systems": https://www.nasa.gov/centers-and-facilities/armstrong/autonomous-systems/
- NASA Technology Transfer, "Near-Real Time Verification and Validation of Autonomous Flight Operations": https://technology.nasa.gov/patent/TOP2-320
- DARPA OFFSET program page: https://www.darpa.mil/research/programs/offensive-swarm-enabled-tactics
- PX4 Simulation documentation: https://docs.px4.io/main/en/simulation/
- PX4 Hardware Simulation documentation: https://docs.px4.io/main/en/simulation/hardware
- NIST AI Test, Evaluation, Validation and Verification: https://www.nist.gov/ai-test-evaluation-validation-and-verification-tevv
- DoD Manual 5000.101, "Operational Test and Evaluation and Live Fire Test and Evaluation of Artificial Intelligence-Enabled and Autonomous Systems": https://www.esd.whs.mil/Portals/54/Documents/DD/issuances/dodm/5000101p.PDF?ver=FfOR56lIK5S1LDFfSlYwYQ%3D%3D
