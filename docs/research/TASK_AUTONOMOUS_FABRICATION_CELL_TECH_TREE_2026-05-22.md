# Task-Autonomous Fabrication Cell Tech Tree

Status: R&D stepping-stone note / build queue seed; not canonical SCBE architecture  
Date: 2026-05-22  
Scope: agentic fabrication, robotics, embodied AI safety, GeoSeal runtime assurance  
Canonical constraint: task-autonomous within a human-specified goal and safety envelope  
Audience: internal R&D triage; not a patent claim, proposal claim, or production commitment

## 0. Status Boundary

This note is adjacent to SCBE-AETHERMOORE. It shares the governance principle: every embodied action stays inside a deterministic envelope and leaves an audit receipt. It is not part of the canonical SCBE architecture unless later promoted through a separate review.

The win preserved here is the method, not just the conclusion:

```text
vivid idea -> stress test -> fenced overreach -> kept core
```

If a later draft carries only the kept core and drops the fence, the claim is unsafe. The correction travels with the claim.

## 0.1 Provenance Ledger

| Vivid idea | Stress test | Fence that must travel with it | Kept core |
|---|---|---|---|
| Spin voxels / magnetics | Physical spin claims were asserted, not derived | Do not claim Heisenberg physics, topological crypto, magnonics, or Grover resistance | Vector-field coherence and angular disorder are useful read-side drift signals |
| Tesseract build orchestration | No fourth spatial dimension was specified | Use 3D plus build-time only; do not imply real 4D spatial machinery | Build sequence can be modeled as a time-indexed state space |
| Printer builds itself smaller | The first machine was built by an external supply chain | Do not claim total self-fabrication; silicon/controllers remain sourced until a real semiconductor process exists | Raise the self-fabricable fraction one capability at a time |
| Full autonomy by stacked tasks | Subtask generation still traces back to a root goal | Do not claim unbounded or self-originating autonomy | Use task-autonomy inside a human-specified goal-and-constraint envelope |
| Private crash testing | Concealment framing is wrong and harmful | Do not frame safety testing as hiding failures | Dangerous failures belong in simulation/closed environments, with audit logs that survive review |

Every section below should be read through this ledger.

## 1. One-Sentence Mechanism

A task-autonomous fabrication cell receives a human-specified target artifact, decomposes it into build steps, dispatches fabrication tools as governed tool calls, senses the result, corrects its model, and emits receipts proving every physical action stayed inside a bounded safety envelope.

Short form:

```text
task-autonomous, human-specified goal-and-constraint envelope, unmanned execution
```

Do not shorten this to bare "autonomous fabrication cell" in technical, proposal, patent, or customer-facing materials.

## 2. What This Is Not

This is not a claim of unbounded autonomy.

This is not a claim that a 3D printer can fabricate every component needed to replicate itself.

This is not a claim that simulation removes the need for physical testing.

This is not a claim that a kiln, foundry, or printer is the key invention. Those are possible test articles. The key invention candidate is the governed build-sense-correct loop.

The honest scope is:

```text
human specifies the target
system owns the how
governance owns the envelope
receipts prove the path
```

That is task autonomy, and it is the useful level for this adjacent R&D line.

## 3. The Senku Step

The generative step is not the kiln, the foundry, or the printer.

The generative step is the closed build-sense-correct loop:

```text
plan -> act -> sense -> compare -> correct -> receipt
```

This is the "kiln" of the system because it produces a reusable capability rather than a one-off artifact. Once the loop is reliable, harder build targets become a schedule instead of a guess.

Fence: this does not make self-fabrication solved. It only makes future fabrication claims measurable because the system can compare intended action against observed result.

## 4. Capability Ladder

| Rung | Capability | Why it matters | Status target |
|---|---|---|---|
| 0 | Digital twin / simulator | Failure is cheap; test policies before hardware | software-first |
| 1 | Tool-call registry | Printers, cameras, scales, heaters, arms become typed operations | buildable now |
| 2 | Self-modeling sensor loop | System measures its own tool/body state and calibration drift | first hard rung |
| 3 | Closed-loop trivial build | Make/assemble a simple bracket or block stack, verify tolerance | first demo |
| 4 | Multi-step thermal artifact | Kiln-like target with heat schedule and crack/failure checks | first real target |
| 5 | Output becomes tool | Built artifact extends the cell's capability, e.g. kiln used for next material step | first recursion |
| 6 | Collaborative machine buddies | Multiple tools hold, hand off, inspect, and correct each other | robotics expansion |
| 7 | Continual learning under rate limits | Online adaptation without catastrophic forgetting | controlled R&D |
| 8 | Fabrication fraction increases | Structure + conductors + coils + simple actuators | capability curve |
| 9 | Silicon remains sourced | Chips/controllers remain bought-in until a real fab process exists | hard boundary |

The self-fabrication question becomes measurable:

```text
self-fabricable fraction = components made in-cell / components required by target
```

The goal is to raise that fraction honestly, not claim total self-replication.

Boundary: if a target depends on chips, controllers, sensors, precision bearings, or materials the cell cannot make, those components are sourced. Sourced components are allowed, but they must be named.

## 5. Tool Calls For Physical Fabrication

Treat each physical machine as a governed tool surface.

| Tool class | Example operations | Required gate |
|---|---|---|
| 3D printer | slice, print, pause, resume, cancel | thermal/workspace safety |
| CNC / subtractive | cut, drill, surface, deburr | material + collision gate |
| camera / scanner | capture, measure, compare | read-only provenance |
| scale / caliper | weigh, measure, tolerance check | read-only provenance |
| kiln / heater | ramp, hold, cool, emergency stop | high-risk thermal gate |
| robot arm | grasp, hold, move, handoff | collision + human-zone gate |
| winder | wind coil, count turns, tension check | actuator fabrication gate |
| human interface | approve, reject, abort, re-scope | explicit envelope boundary |

Every tool call should produce a receipt:

```json
{
  "schema_version": "scbe-fab-receipt-v0.1",
  "tool": "printer.main",
  "operation": "print",
  "target": "calibration_bracket_v1",
  "decision": "ALLOW",
  "pre_state_hash": "sha256:...",
  "post_state_hash": "sha256:...",
  "sensor_refs": [],
  "risk": {
    "thermal": "low",
    "collision": "none",
    "human_zone": "clear"
  }
}
```

## 6. Safety Envelope

Constraints are not the weakness of the system. They are the safety case.

They are also the liability case: the system should be able to show what was requested, what was allowed or denied, why the decision was made, and which sensor evidence supported the decision.

The envelope must make the following impossible or fail-closed:

- tool motion outside workspace bounds
- heater/kiln runaway
- robot arm entering human exclusion zone
- printer continuing after thermal fault
- destructive operation without a dry-run or explicit authorization
- model-generated command reaching actuator without deterministic gate
- post-release learning changing actuator policy without rate limits and rollback

Minimum decision tiers:

| Tier | Meaning | Physical action |
|---|---|---|
| ALLOW | within bounds, low risk | execute |
| PROBE | uncertain but safe to simulate/test | dry-run or sensor-only |
| ATTENUATE | allowed only at reduced speed/power/scope | execute bounded |
| ESCALATE | needs human approval | stop and request |
| DENY | unsafe or out of envelope | stop and receipt |

Fence: the envelope is not optional polish. Removing it does not produce a more advanced system; it removes the system's safety case.

## 7. Training And Learning Boundary

The system can learn during use, but only in controlled lanes.

Allowed first:

- update calibration offsets
- update sensor-noise estimates
- update tool wear estimates
- store failure cases for offline replay
- train small adapters in a sandbox

Not allowed first:

- live weight updates to actuator-control policy
- irreversible changes to safety thresholds without review
- model-originated expansion of allowed operations
- hidden "goal" creation outside human target and envelope
- task generation that detaches from the human-specified root goal

Safe architecture:

```text
fast actor: executes bounded task plan
slow learner: consolidates logs offline
gate: promotes changes only after tests
rollback: restores previous policy on regression
```

## 8. Cross-Platform Transfer

The transferable asset is not the hardware. It is the abstract governance loop.

The same state-vector gate can support:

- fabrication cell
- wheelchair / adaptive mobility platform
- drone / aerial platform
- robot arm / lab automation platform

Shared state fields:

```json
{
  "pose": [],
  "velocity": [],
  "energy": 0.0,
  "thermal_state": {},
  "tool_state": {},
  "human_zone_clear": true,
  "risk_scalar": 0.0,
  "intent": "human-specified-target",
  "workspace": "bounded-volume-id"
}
```

Vehicle/platform-specific testing still remains required. The shared gate can be validated once as logic; actuators and dynamics are validated per platform.

Fence: cross-platform transfer applies to the abstract governance loop and representation. It does not transfer vehicle dynamics, actuator safety, certification evidence, or physical hazard testing.

## 9. First Demo

Do not begin with kiln-to-foundry.

Begin with:

```text
task: make and verify a calibration bracket
tools: printer + camera/scanner + caliper/scale if available
loop: plan -> print -> inspect -> compare -> reprint/correct -> receipt
```

Acceptance:

- target dimensions specified before print
- printer command generated as a governed operation packet
- sensor inspection produces a measured error vector
- system chooses either accept, adjust, or reject
- all steps emit receipts
- no live dangerous action occurs without a deterministic gate

This is the first demonstrable milestone because it proves the method:

```text
the loop closes unmanned on a trivial task
```

It is more important than the artifact being impressive.

## 10. Later Demo: Kiln-To-Foundry

The kiln/foundry path is a strong later target because controlled heat unlocks many downstream capabilities.

Frame it as:

```text
the closed loop builds a tool that expands the closed loop's future toolset
```

not:

```text
the machine is self-replicating
```

Milestones:

1. simulate kiln build and thermal ramp
2. build passive refractory test piece
3. measure cracks/deformation after firing
4. close thermal feedback loop
5. use kiln output in a second controlled build

Fence: kiln-to-foundry is a later integration target, not the first milestone and not evidence of full autonomy or self-replication.

## 11. Claims Safe For External Use

Safe:

- task-autonomous fabrication workflow
- governed physical tool calls
- digital twin before hardware
- closed-loop self-modeling and calibration
- auditable safety receipts
- platform-agnostic runtime assurance for embodied AI
- increasing self-fabricable fraction over time

Avoid:

- fully autonomous self-originating goals
- self-replicating machine without component-boundary disclosure
- no-human-input without specifying level of autonomy
- hiding failures to avoid liability
- claims that simulation replaces physical validation

## 11.1 Audience Split

This note should not be copied unchanged into proposals, patent material, or public pages.

| Destination | Use | Required rewrite |
|---|---|---|
| internal R&D | Preserve the whole correction ledger | keep fences and dead ends visible |
| implementation build card | Simulated bracket loop only | remove kiln/foundry except as deferred target |
| SBIR/capability statement | Platform-agnostic runtime assurance | lead with bounded autonomy and audit receipts |
| patent counsel packet | Mechanism disclosure | identify human root goal, envelope, receipts, and sourced components |
| public demo | Safe visual proof | no self-replication or full-autonomy language |

If this idea feeds the SBIR/capability-statement track, the phrase to carry forward is:

```text
platform-agnostic runtime assurance for embodied AI systems
```

not:

```text
self-replicating autonomous fabrication
```

## 12. Build Card

```json
{
  "schema_version": "scbe-doc-build-card-v1",
  "title": "Task-Autonomous Fabrication Cell",
  "status": "research-only/design",
  "not_canonical_scbe": true,
  "do_not_build_yet": [
    "live hardware actuation",
    "autonomous goal origination",
    "self-replication claims",
    "kiln/foundry endpoint"
  ],
  "core_claim": "A bounded agentic system can dispatch physical fabrication tools as governed operations, close the build-sense-correct loop, and emit auditable receipts while remaining under a human-specified goal envelope.",
  "repo_anchors": [
    "docs/research/TASK_AUTONOMOUS_FABRICATION_CELL_TECH_TREE_2026-05-22.md",
    "docs/specs/AETHERFAB_PUF_NEGATIVE_RESULT.md",
    "docs/research/drone_autonomy_training_patterns_2026-05-02.md",
    "docs/ops/REGENERATIVE_AI_MOBILITY_OPEN_SOURCE_STACK_2026-05-21.md",
    "docs/superpowers/specs/2026-05-22-geoseed-infinity-box-runtime.md"
  ],
  "risk_class": "physical-action",
  "first_slice": {
    "goal": "simulate a governed build-sense-correct loop for a calibration bracket with no real hardware actuation",
    "files": [
      "scripts/system/fab_cell_sim.py",
      "tests/system/test_fab_cell_sim.py",
      "artifacts/fab_cell/"
    ],
    "tests": [
      "safe print plan emits ALLOW receipt",
      "out-of-bounds tool path emits DENY receipt",
      "measured error triggers adjust/retry decision",
      "no hardware command is emitted in simulation mode"
    ],
    "acceptance": [
      "deterministic JSON receipts",
      "human target remains root of task tree",
      "all physical action stays simulated"
    ]
  }
}
```
