# Agent Bus — Architecture & Future Work

The agent bus is the **thin coordination layer** for SCBE-AETHERMOORE: a spinal
cord that routes tasks across LLMs, browsers, training, and team consensus,
while every decision lands in a tamper-evident audit trail.

This file documents what is in place and what is staged for later work.

## What ships in this PR

| Module | Purpose |
|---|---|
| `agent_bus.py` | Core bus — orchestrates ask / summarize / analyze / monitor / team_decide / generate_tool / maybe_train |
| `agent_bus_browser.py` | 3-mode browser backend: `headless`, `headed`, `swarm` (lazy-loaded) |
| `agent_bus_signing.py` | ML-DSA-65 (FIPS 204) event signing — every BusEvent signed before logging |
| `agent_bus_ledger.py` | Bridge to HYDRA central ledger (SQLite) — events also written there |
| `agent_bus_team.py` | Roundtable consensus + solo→swarm escalation (decompose-first, fail-second) |
| `agent_bus_extensions.py` | Tool registry + LLM-driven tool generator with AST-level safety checks |
| `agent_bus_training.py` | Performance window measurement + perf-triggered training run |
| `agent_bus_cli.py` | CLI matching 2026 SOTA (`run`, `analyze`, `perf`, `train`, `generate-tool`, `decide`) |

## Architectural principles

1. **Bus = nervous system, not the brain.** Smarts live in the organs (LLM, browser, swarm). The bus only routes and logs.
2. **Three swappable backends per organ.** Pick at construction time, lazy-load.
3. **Append-only signed audit trail.** JSONL + HYDRA ledger; ML-DSA-65 signatures.
4. **Bounded everything.** Retries capped, breakers cap consecutive failures, training cooldown, validator caps.
5. **Decompose-first, escalate-on-failure-second.** Solo by default, swarm when confidence drops or fails repeatedly.

## Future work (ordered by space-grade priority)

### Tier 1 — needed for production / NASA-SpaceX bar

- [ ] **Schema versioning enforcement** — `_schema_version` is written, but the reader currently doesn't gate on it. Add a migration table and reject events with unknown future versions.
- [ ] **Store-and-forward for deep-space comms** — local queue with priority lanes, sync when uplink is available. DTN-compatible. Build on top of existing JSONL.
- [ ] **Bandwidth-aware compression** — compress `events.jsonl` deltas with zstd before transmit; protobuf encoding for the ledger sync wire format.
- [ ] **Time discipline** — split monotonic clock for ordering vs. wall clock for display. Already mostly in place; add explicit field separation.
- [ ] **Crypto identity rotation** — currently the agent's ML-DSA key is generated once. Add rotation policy + ledger entries for key rollover.
- [ ] **Distributed ledger sync** — multiple agents sync their HYDRA ledgers via Merkle proofs. Plug into the existing `hub_replica_paths` pattern in `swarm_browser.py`.

### Tier 2 — capability expansion

- [ ] **Browser modes auto-escalation** — currently the user picks the mode. Add an auto-mode that starts headless, escalates to swarm on confidence drops (uses `TeamCoordinator.should_escalate`).
- [ ] **Tool generator: live test harness** — generated tools currently pass static validation only. Add a sandboxed dry-run before registration (input fixtures from spec, assert output shape).
- [ ] **Self-training: failure-driven SFT mining** — currently calls `codebase_to_sft.py` blindly. Mine failed BusEvents from `events.jsonl` and turn them into corrective SFT pairs.
- [ ] **Team coordination: leader/worker mode** — add a third coordination pattern (currently roundtable + solo→swarm). Useful for parallelizable browser work per the SkyVern pattern.
- [ ] **MCP server mode** — `agent_bus_cli serve --mcp` exposes bus operations as Model Context Protocol tools so other AI clients can use the bus directly.

### Tier 3 — observability and ops

- [ ] **Trace export** — Playwright traces uploaded as Tier-1 audit substrate per 2026 SOTA. Wrap each browser action in `tracing.start()/stop()` and link to the BusEvent.
- [ ] **Metrics endpoint** — Prometheus-format metrics: requests, success rate, latency p50/p99, tokens, breaker state, by-task-type.
- [ ] **Replay tool** — read `events.jsonl`, deterministically replay any operation. Critical for postmortems and for training replayability.
- [ ] **Cost tracking** — populate USD-equivalent cost per call; the `--budget` flag is currently advisory.

### Tier 4 — research-y / nice-to-have

- [ ] **Hyperbolic state vector on every event** — feed each BusEvent's `xi` (9D state) into the SCBE governance gate before execution, not just after.
- [ ] **Sacred Tongues weighting per task** — different task types get different tongue weights (KO for navigation, RU for reading, DR for safety calls).
- [ ] **Swarm member training affinity** — Each of the 6 swarm agents trains on its specialty's failed events only.
- [ ] **Audio-axis intent encoding** — encode task intent as phase-modulated audio using `scbe-audio-intent` skill. Demodulate at receiver. Useful for steganographic ops + robust comms.

## Known limitations

- **No live test of generated tools** — only static validation. Don't expose `generate_tool` to untrusted callers.
- **Training trigger is conservative** — by design, but means perf can degrade for up to one cooldown window before retraining kicks in.
- **HYDRA ledger uses HMAC, not PQC** — the existing ledger signs with HMAC-SHA256. Bus events ride on top with ML-DSA-65 signatures, so they're double-protected, but the ledger itself isn't quantum-resistant. Tier 1 future work.
- **Schema versioning not enforced on read** — `SCHEMA_VERSION = "1.0.0"` is written; the reader doesn't yet reject unknown versions.

## Pre-flight before each release

```bash
# Smoke test the bus boots and writes a signed event
python -c "import asyncio; from agents.agent_bus import AgentBus; \
    asyncio.run((lambda: __import__('agents.agent_bus_cli'))())"

# Verify a known event signature
python -c "from agents.agent_bus_signing import EventSigner; \
    print('signing module imports cleanly')"

# Show the 5 most recent events
tail -5 artifacts/agent-bus/events.jsonl | jq -r '._sig_alg + " " + .task_type'
```
