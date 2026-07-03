# AI Brain Claims Matrix - 2026-06-27

Purpose: keep SCBE/PHDM/AetherBrain claims honest by requiring a code path, test path, and result artifact before anything becomes a release/public claim.

Status terms:

- `release-ready`: code path + test path + current result artifact exist.
- `implemented-unverified`: code exists, but this pass did not verify current test/artifact status.
- `prototype`: useful implementation exists, but API/behavior is not canonical yet.
- `research-only`: design/theory/documentation only, or not enough local evidence yet.
- `reframe`: claim is directionally useful but phrased too strongly.

No tests, builds, training, or cloud jobs were run while creating this matrix.

## Matrix

| Public claim candidate | Status | Code path | Test path | Result artifact | Release wording |
|---|---:|---|---|---|---|
| SCBE has a 21D unified AI state vector | implemented-unverified | `src/ai_brain/unified-state.ts`; `python/scbe/brain.py`; `python/scbe/phdm_embedding.py` | `tests/ai_brain/unified-state.test.ts` | missing/current not attached | "Implements a 21D state model used by SCBE brain components." |
| The system uses Poincare/hyperbolic containment | implemented-unverified | `src/ai_brain/unified-state.ts`; `python/scbe/brain.py`; `agents/browser/phdm_brain.py`; `agents/browser/bounds_checker.py` | `tests/ai_brain/unified-state.test.ts`; browser tests TBD | missing/current not attached | "Uses hyperbolic distance and containment thresholds for action gating." |
| Conservation laws / RefactorAlign enforce valid state | implemented-unverified | `src/ai_brain/conservation.ts` | `tests/ai_brain/conservation.test.ts` | missing/current not attached | "Projects invalid 21D states back toward valid constraints and records violations." |
| Phase, curvature, threat Lissajous, drift, and six-tonic detectors are implemented | implemented-unverified | `src/ai_brain/detection.ts` | integration/detection tests TBD | missing/current not attached | "Provides five orthogonal detector mechanisms for trajectory risk scoring." |
| End-to-end mixed-agent brain integration reaches perfect separation | prototype | `src/ai_brain/brain-integration.ts` | `tests/ai_brain/brain-integration.test.ts` | missing/current not attached | Do not claim externally until exact result artifact exists. |
| GeoSeal-style immune quarantine is implemented | implemented-unverified | `src/ai_brain/immune-response.ts`; `agents/browser/action_validator.py`; `api/main.py` | tests TBD/current not attached | missing/current not attached | "Implements suspicion, quarantine, and release mechanics for agent/action states." |
| PHDM 16-polyhedra thought routing exists | prototype | `python/scbe/brain.py`; `python/scbe/phdm_polyhedra.py`; `src/ai_brain/phdm-core.ts` | `tests/ai_brain/phdm-core.test.ts` | missing/current not attached | "Prototype polyhedral routing model for structured reasoning and audit." |
| Flux states POLLY/QUASI/DEMI exist | implemented-unverified | `src/ai_brain/flux-states.ts`; `python/scbe/brain.py` | integration tests TBD/current not attached | missing/current not attached | "Implements normal, defensive, and emergency runtime modes." |
| Quasicrystal / sparse octree scaffold exists | prototype | `src/ai_brain/quasi-space.ts` | `tests/ai_brain/quasi-space.test.ts` | missing/current not attached | "Prototype quasi-space and sparse voxel scaffold for state visualization/routing." |
| Swarm formations and consensus exist | prototype | `src/ai_brain/swarm-formation.ts`; `agents/agent_bus.py`; `api/main.py` | `tests/ai_brain/swarm-formation.test.ts` | missing/current not attached | "Implements swarm coordination and voting primitives." |
| Sacred Tongues / STIB can compile or map coding expressions | prototype | `agents/agent_bus.py`; `python/scbe/tongue_isa.py`; `python/scbe/tongue_isa_binary.py`; `scripts/system/mixed_expression_lane.py` | tests TBD | missing/current not attached | "Prototype conlang/ISA lane for translating structured coding packets." |
| Symphonic/audio verifier is part of the runtime | prototype | `agents/browser/action_validator.py`; `src/symphonic_cipher/*` | tests TBD | missing/current not attached | "Prototype optional telemetry/verifier axis." |
| Geometry makes unsafe actions impossible | reframe | Multiple threshold/projection/quarantine gates | N/A | N/A | Use: "Invalid states are projected, quarantined, denied, or made high-cost by runtime gates." |
| Tongue multipliers provide security hardness | reframe | Sacred tongue weighting implementations | N/A | N/A | Use: "Tongue weights are routing, priority, and cost signals, not standalone cryptographic hardness." |
| Swarm voting is BFT/PBFT | reframe | `src/ai_brain/swarm-formation.ts`; `agents/agent_bus.py` | N/A | N/A | Use: "Majority/consensus primitives unless full PBFT is implemented and tested." |

## Release rule

A claim graduates only when it has:

1. A canonical code path.
2. A test or executable demo path.
3. A saved result artifact.
4. Safe wording that does not exceed the evidence.

## Artifact naming convention

Save future result artifacts under `artifacts/ai_brain/` with names like:

- `brain-integration-100trials-20agents-YYYYMMDD.json`
- `detectors-ablation-YYYYMMDD.json`
- `conservation-refactoralign-YYYYMMDD.json`
- `aetherdesk-action-gate-smoke-YYYYMMDD.json`

Each artifact should include command, git/ref state if available, inputs, metrics, and pass/fail summary.
