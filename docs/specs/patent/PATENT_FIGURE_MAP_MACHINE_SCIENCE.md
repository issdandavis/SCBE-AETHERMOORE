# Patent Figure Map: Machine-Science Control Framework

## Figure Framing
- All figures depict computational governance structures and dataflow components.
- Figures do not depict or require simulation of physical laws; the `control hyperspace` is a logical machine-state coordinate model.

## Figure Set (10 Figures)

| Figure | Title | Purpose | Supported Claim Elements | Implementation Hook |
|---|---|---|---|---|
| FIG. 1 | End-to-End Governance System Architecture | Shows primary modules from token ingress through decisioning, execution membrane, trust update, and audit trace. | `C1[a]-C1[i]`, `C13[a]-C13[h]`, `C25[a]-C25[g]` | Service/module layout for runtime governance engine. |
| FIG. 2 | Logical Control Hyperspace Projection | Illustrates projection of token + runtime context into axes `t, i, p, u, r, c` with optional extension axes. | `C1[b]`, Claim 2, `C13[b]`, `C25[b]` | State-vector encoder and normalization pipeline. |
| FIG. 3 | Machine-Constant Registry and Version Lifecycle | Depicts constant families (`k_tick`, `k_decay`, `k_gate`, `k_route`, `k_crypto`, `k_stability`) and auditable version transitions. | `C1[c]`, Claims 22, 33, `C25[c]` | Config registry, signed updates, rollback control. |
| FIG. 4 | Policy-Field Evaluation and Composite Scoring | Shows field functions emitting `(cost, permit, reason)` and deterministic score aggregation with penalties. | `C1[d]-C1[e]`, Claims 3, 4, 16, 17, `C13[c]-C13[d]`, `C25[c]-C25[d]` | Deterministic evaluator pipeline and weighted aggregation function. |
| FIG. 5 | Governance Threshold Mapping and Action Membrane | Illustrates mapping score intervals to `ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY` and action-class routing outcomes. | `C1[f]-C1[g]`, Claims 18, 19, 30, `C13[e]-C13[f]`, `C25[d]-C25[e]` | Decision state machine and route controller. |
| FIG. 6 | Token Envelope and Context-Lock Validation | Defines token schema fields and fail-closed handling for invalid signature, missing metadata, or context mismatch. | Claims 5, 6, 7, 12, 15, 24, 32, 34 | Validation middleware, schema checks, crypto envelope verifier. |
| FIG. 7 | Quorum-Gated High-Risk Action Flow | Shows role-diverse quorum checks for destructive and sensitive-transfer action classes before final execution. | Claim 8, Claims 19, 24, 31, `C13[f]`, `C25[e]` | Multi-agent approval service and policy gate integration. |
| FIG. 8 | Deterministic Control Loop Timing | Illustrates per-tick sequence: ingest, project, evaluate, score, map, apply, update, audit with monotonic ordering. | Claims 3, 4, 23, 26, `C13[a]-C13[h]`, `C25[a]-C25[g]` | Scheduler tick loop, stable operation order, bounded precision settings. |
| FIG. 9 | Deterministic Audit Record and Replay | Shows canonical decision trace schema and replay path proving identical outcomes for identical inputs and constants versions. | `C1[i]`, Claims 11, 12, 21, 27, 29, `C13[h]`, `C25[g]` | Audit log schema, replay executor, nonce/time-window verification. |
| FIG. 10 | Adaptive Threshold Proposals via Digital Twin | Depicts twin-generated policy-threshold proposals constrained by auditable version promotion workflow. | Claim 9, Claim 36, `C1[c]`, `C13[g]`, `C25[c]` | Offline/online feedback channel with gated constant promotion. |

## Drafting Notes For Figure Captions
- Use "logical state coordinates" and "machine-governance dimensions" instead of physics language.
- Tie every caption to concrete software components: registry, evaluator, mapper, membrane, scheduler, and audit store.
- Keep caption verbs implementation-facing: ingest, project, evaluate, aggregate, map, gate, update, persist, replay.
