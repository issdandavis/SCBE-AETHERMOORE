# Hardware–Software–AI Interchange Map

Status: DESIGN MAP; REFERENCE ROUTER IMPLEMENTED; CROSS-SUBSTRATE CAPABILITY UNPROVEN
Date: 2026-11-07

This map supplements, but does not override,
`docs/CANONICAL_SYSTEM_STATE.md`. Runtime behavior remains authoritative only
for the named profile and tested code path.

## Layer and Edge Map

```text
L0 physical state
  CPU | GPU | FPGA | sensor | future fluidic/ionic adapter
    |
    | measured device contract: units, timing, energy, error, availability
    v
L1 transport and transducer
  driver | kernel | codec | pressure/voltage/flow converter
    |
    | typed conversion; no analogy-only crossing
    v
L2 interchange operation
  exact operation + input/output types + invariants + hard constraints
    |
    +--> direct route -----------------------------------+
    |                                                   |
    +--> adapter -> specialist backend -> verified merge+
                                                        v
L3 provenance hyper-token
  exact occurrence + source bundle + evidence links + mixture trace
    |
    v
L4 governance and discernment
  claim type + evidence trit + confidence + policy + rights + risk
    |
    v
L5 AI control
  deterministic eligibility -> bounded preference -> retrieval/model/sidecar
    |
    v
L6 output
  text | code | interface | deployment | actuator
    |
    v
L7 receipt and feedback
  observed output + route + counterfactual + retention + rollback pointer
```

## Implemented Reference Surface

- `python/scbe/interchange_router.py`
  - typed operation contracts;
  - CPU/GPU/FPGA/fluidic/ionic/software/simulator/backend capability records;
  - direct and at-most-two-adapter path enumeration;
  - fail-closed operation, type, output, privacy, determinism, policy, latency,
    energy, and fidelity gates;
  - deterministic eligible-route ranking and canonical receipt hash;
  - provenance-preserving hyper-token mixture traces;
  - fact/opinion/forecast/command/preference/normative claim types;
  - evidence trit with confidence and source observations kept separate.
- `tests/system/test_interchange_router.py`
  - direct versus adapter path;
  - privacy cannot be waived by a higher score;
  - no invented untyped crossing;
  - conflicting evidence remains unresolved;
  - subjective content is not mislabeled as external fact;
  - mixture source order remains visible;
  - route receipt is independent of capability enumeration order.

The router selects a declared path; it does not execute hardware. A future
backend adapter must return a measured conformance receipt before it may be
described as interchangeable.

## Existing Nodes to Connect

| Layer | Existing SCBE node | Connection rule |
| --- | --- | --- |
| Token identity | Six Tongues and Prime Token Catalog | Preserve exact byte/span and mapping hashes. |
| Retrieval | Six-view search | Lexical evidence remains authoritative until controlled gain exists. |
| Topology | AetherBrowser topology engine | Semantic distance and trust/evidence must remain separate fields. |
| Model routing | OctoArmor and TriLane | Use interchange eligibility before model preference. |
| AI side layer | Clay frozen-core adapters | Input access, output margin, retention, and multi-seed controls required. |
| Governance | GeoSeal and agent-bus receipts | Bind route contract, backend version, source bundle IDs, and result hash. |
| Product | npm/PyPI packages | Ship conformance fixtures, examples, replay, and upgrade/failure behavior. |

## Non-Promotion Boundary

The current implementation proves contract mechanics only. It does not prove a
fluidic computer, improved model output, better retrieval, hardware energy
savings, or production readiness. Those claims require measured backends and
the controls in
`docs/research/hardware_software_ai_interchange_20261107/research_brief.md`.
