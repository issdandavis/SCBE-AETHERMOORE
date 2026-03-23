# HYDRA Parallel Browser Comms Lattice

Date: 2026-03-17

## Goal

Enable HYDRA tentacles to do independent but symbiotic work in parallel across multiple headless browser sessions, including remote/free compute lanes such as Colab, while keeping all action, context, and verification inside one governed communication ledger.

This should not be "many browsers doing random things."

It should be:

- many browser workers
- one shared ledger
- one governed packet format
- one fold-through path across the 14 layers
- one recomposition step that turns parallel work back into coherent state

## Existing Repo Seams

The current repo already has most of the pieces:

- `scripts/aetherbrowse_swarm_runner.py`
  - multi-job browser execution with verification and DecisionRecords
- `agents/swarm_browser.py`
  - six Sacred Tongue agents with message passing, votes, and hub replication
- `scripts/system/crosstalk_relay.py`
  - append-only multi-lane communication relay
- `packages/kernel/src/audioAxis.ts`
  - live Layer 14 telemetry seam
- `src/harmonic/voxelRecord.ts`
  - discrete governance plus continuous spectrum overlay
- `agents/aetherbrowse_cli.py`
  - main governed browser entrypoint
- `agents/browser/session_manager.py`
  - per-session validation and audit

These do not yet form one full browser swarm lattice, but the seam is already there.

## Important Clarification About Layer 14

There is a split in the repo history:

- some older architecture/training descriptions still call Layer 14 the PQC envelope
- live code in `audioAxis.ts` treats Layer 14 as audio-axis telemetry

For this design, Layer 14 should be treated as the **communication and telemetry surface**.

That fits your intent better:

- Layer 14 is where all worker states become measurable signals
- not just "did the task pass"
- but how the swarm sounded, drifted, synchronized, hesitated, or diverged

PQC still matters, but it should wrap the ledger and the packets, not own the meaning of Layer 14.

## System Shape

Use a four-tier structure:

1. `Conductor`
- local DR/Polly authority
- owns task decomposition
- owns worker lease assignment
- owns ledger recomposition

2. `Tentacle Workers`
- one browser session per worker
- local headless Playwright/CDP or remote browser lane
- each worker gets a bounded role and capability token

3. `Remote Compute Leases`
- optional worker hosts on Colab/free VMs/other browser-connected machines
- these should run as disposable execution pods, not as authorities

4. `Comms Lattice`
- append-only packet ledger
- internal + external communication records
- every packet folds through the 14-layer path before promotion

## Parallelism Model

Each user task becomes a `mission`.

A mission splits into:

- `scout`
- `reader`
- `vision`
- `operator`
- `verifier`
- `judge`

These can run in parallel where safe.

Examples:

- one worker reads and extracts page structure
- one worker captures screenshots or visual checkpoints
- one worker executes form fills in a sandboxed lane
- one worker verifies that the result matches goal constraints
- the judge lane only resolves after receiving all required packets

The existing `scripts/aetherbrowse_swarm_runner.py` is already close to this shape, but it needs stronger session identity and recomposition.

## Remote Compute Model

Treat Colab and similar free compute as `leased browser workers`, not as orchestration roots.

That means:

- local machine remains authority
- remote workers receive bounded mission packets
- remote workers do not hold final trust
- remote workers return signed result packets and evidence

Recommended lease packet:

- `mission_id`
- `worker_id`
- `session_id`
- `role`
- `allowed_domains`
- `allowed_actions`
- `capability_token`
- `time_budget_s`
- `max_steps`
- `return_channels`

This prevents Colab from becoming a chaos source.

## Communication Ledger

You asked for a communication ledger for internal and external comms. The clean move is one unified schema with audience tags, not two separate systems.

Ledger classes:

- `internal`
  - worker-to-worker
  - worker-to-conductor
  - agent-to-agent

- `external`
  - browser-visible outbound actions
  - user-facing messages
  - third-party API or site interactions

- `evidence`
  - screenshots
  - DOM packets
  - extracted text
  - timing traces

- `governance`
  - votes
  - risk gates
  - escalation markers
  - final decision

The current `crosstalk_relay.py` can be extended into this instead of replaced.

## Four-Rail Split

Your "negative and positive path in both directions" idea can be made concrete as a four-rail braid.

Each mission packet forks into four rails:

1. `P+` Positive Primal
- intended action path
- the worker's best constructive plan

2. `P-` Negative Primal
- local failure, anomaly, obstacle, friction
- what blocks the direct action path

3. `D+` Positive Dual
- attestation, verification, confirmation
- evidence that the action is correct, safe, or complete

4. `D-` Negative Dual
- dissent, contradiction, risk, spoofing signal, mismatch
- evidence that the action should not be trusted as-is

Then recomposition happens after all four rails report or timeout.

That gives you a DNA-like split/reform pattern:

- action strand
- friction strand
- confirmation strand
- contradiction strand

The conductor recombines them into one governed state.

## Why This Works

Without this split, browser agents only report:

- what they tried
- whether they think they succeeded

With the four rails, they report:

- what they intended
- what resisted
- what confirms
- what contradicts

That is much closer to how robust systems actually parse reality.

## Four-Rail Packet Draft

```json
{
  "mission_id": "mission-20260317-001",
  "worker_id": "tentacle-av-03",
  "session_id": "sess-av-03-abc123",
  "layer_path": ["L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12","L13","L14"],
  "rails": {
    "P+": {
      "summary": "Found target button and prepared click plan",
      "artifacts": ["dom_map.json"],
      "confidence": 0.82
    },
    "P-": {
      "summary": "Encountered modal overlap and lazy-loaded layout shift",
      "artifacts": ["layout_shift.json"],
      "confidence": 0.76
    },
    "D+": {
      "summary": "Button text, selector, and screenshot agree",
      "artifacts": ["button_crop.png", "selector_check.json"],
      "confidence": 0.87
    },
    "D-": {
      "summary": "Possible prompt-injection banner detected in page body",
      "artifacts": ["risk_scan.json"],
      "confidence": 0.64
    }
  },
  "layer14": {
    "energy": 0.44,
    "centroid": 1420.3,
    "flux": 0.08,
    "hf_ratio": 0.11,
    "stability": 0.89
  },
  "decision_hint": "QUARANTINE",
  "next_request": "Need RU+DR review before execution"
}
```

## Fold Through the 14 Layers

The packet should move through the stack like this:

1. `L1-L3`
- encode mission, role, and packet identity

2. `L4-L5`
- embed into context space and measure distance from safe center

3. `L6-L8`
- choose path, role alignment, and recovery posture

4. `L9-L10`
- coherence, contradiction, and pattern shape across the four rails

5. `L11`
- temporal ordering across workers
- which packets are stale, racing, or late

6. `L12`
- harmonic pressure / wall cost on the recomposed mission state

7. `L13`
- final governance decision

8. `L14`
- emit telemetry for the whole mission braid

Layer 14 should carry the swarm's communication signature, not just audio in the narrow sense.

Suggested Layer 14 mission metrics:

- `energy`
  - how much action pressure exists across the swarm
- `centroid`
  - where the mission’s attention mass is concentrated
- `flux`
  - how rapidly the swarm state is changing
- `hf_ratio`
  - how much noisy/high-frequency thrash is present
- `stability`
  - how well the workers are converging

That makes `audioAxis.ts` a general communication telemetry model, not just a voice feature.

## Quasicrystal / Lattice Mapping

The quasicrystal part makes sense if used as a routing constraint, not as decoration.

Use it for:

- non-periodic worker assignment
- anti-loop traversal
- bounded but non-repetitive retry paths
- preventing swarm workers from collapsing into identical failure cycles

In plain terms:

- browser workers should not all retry the same dead path
- the lattice should distribute retries and alternate probes

This fits the repo's broader PHDM / lattice language and avoids brittle loop behavior.

## Mission Lifecycle

1. Conductor receives user task
2. Task becomes mission packet
3. Mission splits into subtasks
4. Each subtask forks into 4 rails
5. Rails run across local and remote workers in parallel
6. Each worker writes packets to the shared ledger
7. Conductor waits for quorum or timeout
8. Recomposition computes:
   - coherence
   - contradiction load
   - temporal freshness
   - wall pressure
9. L13 decides:
   - `ALLOW`
   - `QUARANTINE`
   - `ESCALATE`
   - `DENY`
10. L14 emits mission telemetry
11. Final packet is stored and optionally converted into training data

## What To Build Next

The shortest path is:

1. Extend `crosstalk_relay.py` into a real ledger record format with packet classes
2. Add mission/session/worker ids into `aetherbrowse_swarm_runner.py`
3. Add a four-rail packet schema
4. Add Layer 14 mission telemetry emission using `audioAxis.ts` semantics
5. Add remote worker lease format for Colab/browser workers
6. Add recomposition logic at the conductor

## Recommended Names

If you want a stable name for this subsystem:

- `HYDRA Comms Lattice`
- `Four-Rail Mission Braid`
- `Layer 14 Mission Telemetry`
- `Primal/Dual Browser Ledger`

The cleanest pair is probably:

- `HYDRA Comms Lattice`
- `Four-Rail Mission Braid`

## Blunt Read

Yes, the DNA split/reform idea makes sense.

But it only becomes useful if it is treated as:

- four explicit rails
- parallel worker outputs
- one recomposition function
- one ledger

If you keep it at the metaphor level, it will stay fuzzy.
If you make the four rails first-class packet fields, it becomes buildable.
