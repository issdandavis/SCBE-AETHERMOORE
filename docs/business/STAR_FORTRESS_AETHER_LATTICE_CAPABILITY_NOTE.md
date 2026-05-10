# Star Fortress Aether-Lattice Capability Note

## Offer

SCBE-AETHERMOORE can run a bounded multi-agent failure-propagation simulation
for a customer workflow and return a short governance snapshot: how failures
spread in a flat queue, how much containment improves under pocket workcells,
and what receipt metadata should be captured at each private-to-public boundary.

This is a practical entry point for buyers who are not ready to adopt the full
14-layer stack but need evidence that an agent workflow can be isolated,
audited, and retried without poisoning shared state.

## What The Harness Tests

The simulator compares two execution shapes under the same fault rate:

- **Flat queue baseline:** agents share global mutable state. One bad write can
  poison downstream operations.
- **Aether-Lattice:** operations run inside phi-indexed octree pockets. Outputs
  must pass a boundary check before appending to the spinal ledger.

The claim is deliberately narrow:

> Recursive bounded workcells reduce failure propagation and improve
> traceability compared with a flat shared-state queue under the same
> faulty-agent rate.

## Star Fortress Receipts

Each lattice boundary now emits a triadic Star Fortress receipt:

| Ring | Use |
| --- | --- |
| `outer-lattice` | Verified exits, modeled with `ML-KEM-1024` + `ML-DSA-87` |
| `middle-hash` | Contained exits / fail-to-noise receipts, modeled with `SLH-DSA-256s` and LMS/XMSS fallback semantics |
| `inner-dev-fallback` | Local-only deterministic test fallback; never positioned as production PQ security |

The receipt also carries Sacred Egg vocabulary:

- `shell`: public-safe routing handle
- `albumen_label`: context-bound operational key label
- `yolk_emitted: false`: the simulator never emits CORE secret material
- `fail_to_noise`: true for contained exits

## Current Evidence

Command:

```powershell
npm run research:aether-lattice
```

Latest local run:

```text
trials: 25
flat_mean_throughput: 0.1696
lattice_mean_throughput: 1.0
flat_mean_public_corruptions: 83.04
lattice_mean_public_corruptions: 0
mean_failure_spread_reduction_percent: 98.73
mean_trace_cost_reduction_percent: 92.08
claim_supported_trials: 25
```

Artifacts:

- `artifacts/aether_lattice/aether_lattice_sim_trials.json`
- `artifacts/aether_lattice/aether_lattice_sim_trials.csv`

## Buyer-Ready Deliverable

For a paid Governance Snapshot, this can be delivered as:

1. A scoped workflow model from the customer's agent architecture.
2. A flat-queue baseline run.
3. An Aether-Lattice containment run.
4. A one-page summary of failure spread, trace cost, route load, and retry behavior.
5. A receipt schema recommendation for their logs or SIEM.

## Boundaries

This is not a hardware simulator, not a claim of infinite scalability, and not a
replacement for production PQC libraries. It is a falsifiable routing and
containment harness that produces concrete metrics from a customer's workflow
shape.
