# Patent Claims Tree: Machine-Science Control Framework

## Technical Framing
- `control hyperspace` is a logical computational state space for governance decisions, not a simulation of physical spacetime.
- `machine constants` are configurable software/firmware invariants that constrain deterministic behavior.
- `policy fields` are executable decision functions over machine state vectors and constants.

## Element Labels For Cross-Reference

### Independent Claim 1 (System)
- `C1[a]` token ingest interface
- `C1[b]` hyperspace projection engine over axes `t, i, p, u, r, c`
- `C1[c]` versioned machine-constant registry (`k_tick, k_decay, k_gate, k_route, k_crypto, k_stability`)
- `C1[d]` policy-field evaluator producing `(cost_j, permit_j, reason_j)`
- `C1[e]` deterministic score aggregator
- `C1[f]` governance mapper to `ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY`
- `C1[g]` action execution membrane
- `C1[h]` trust and telemetry update engine
- `C1[i]` deterministic audit recorder with constants-version binding

### Independent Claim 13 (Method)
- `C13[a]` ingest token and runtime context
- `C13[b]` project into control hyperspace state
- `C13[c]` evaluate policy fields against constants
- `C13[d]` aggregate score and penalty terms
- `C13[e]` map score to governance decision interval
- `C13[f]` execute or constrain action path
- `C13[g]` update trust state and route cost state
- `C13[h]` emit deterministic audit record

### Independent Claim 25 (Non-Transitory Medium)
- `C25[a]` instructions for token/context ingestion
- `C25[b]` instructions for hyperspace projection
- `C25[c]` instructions for policy-field evaluation
- `C25[d]` instructions for deterministic scoring and threshold mapping
- `C25[e]` instructions for execution gating
- `C25[f]` instructions for trust/telemetry updates
- `C25[g]` instructions for deterministic audit persistence

## Claims Tree

### Independent Claim 1 (System)
1. A deterministic machine-science governance system for controlling computational actions, comprising: a token ingest interface (`C1[a]`) configured to receive a token envelope and runtime context; a hyperspace projection engine (`C1[b]`) configured to project the token envelope into a logical state vector comprising at least time `t`, intention `i`, policy `p`, trust `u`, risk `r`, and context `c`; a versioned machine-constant registry (`C1[c]`) storing constants including decision thresholds and stability bounds; a policy-field evaluator (`C1[d]`) configured to apply multiple policy fields to the logical state vector and output field costs and permit indicators; a deterministic score aggregator (`C1[e]`) configured to compute a composite governance score from the field outputs; a governance mapper (`C1[f]`) configured to map the composite governance score to one of `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`; an action execution membrane (`C1[g]`) configured to apply the mapped governance result to a proposed action; a trust and telemetry update engine (`C1[h]`); and a deterministic audit recorder (`C1[i]`) configured to persist a decision trace bound to a constants version.

Dependent claim candidates for Claim 1:
2. The system of claim 1, wherein the hyperspace projection engine supports additional domain axes while preserving the six base axes `t, i, p, u, r, c`.
3. The system of claim 1, wherein deterministic score computation uses fixed-point or bounded-precision arithmetic with configured clipping bounds.
4. The system of claim 1, wherein policy-field evaluation order is stable and explicitly versioned.
5. The system of claim 1, wherein unresolved context commitment causes fail-closed transition to `QUARANTINE` or `DENY`.
6. The system of claim 1, wherein invalid signature or envelope authentication causes `DENY`.
7. The system of claim 1, wherein missing policy metadata causes `ESCALATE`.
8. The system of claim 1, wherein critical action classes are gated by role-diverse quorum validation before an `ALLOW` result can be executed.
9. The system of claim 1, wherein route costs are dynamically weighted using risk and trust state before action execution.
10. The system of claim 1, wherein trust state updates include decay parameters and divergence-triggered self-exclusion behavior.
11. The system of claim 1, wherein replay defense is enforced using nonce and monotonic time-window validation.
12. The system of claim 1, wherein each audit record includes token identifier, projected axes, field outputs, composite score, governance decision, and constants version.

### Independent Claim 13 (Method)
13. A deterministic machine-science governance method for controlling computational actions, the method comprising: ingesting (`C13[a]`) a token envelope and runtime context; projecting (`C13[b]`) the token envelope and runtime context into a logical control hyperspace state vector including at least `t, i, p, u, r, c`; evaluating (`C13[c]`) multiple policy fields over the state vector using a machine-constant set; aggregating (`C13[d]`) field outputs into a composite governance score; mapping (`C13[e]`) the composite governance score to one of `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`; executing or constraining (`C13[f]`) a proposed action according to the mapped governance result; updating (`C13[g]`) trust state and telemetry state; and emitting (`C13[h]`) a deterministic audit trace bound to the machine-constant set version.

Dependent claim candidates for Claim 13:
14. The method of claim 13, wherein ingesting includes normalizing heterogeneous connector events into a common token schema.
15. The method of claim 13, wherein projecting includes computing a context commitment hash from runtime posture data.
16. The method of claim 13, wherein evaluating includes at least safety, compliance, resource, trust, route, and quorum policy fields.
17. The method of claim 13, wherein aggregating applies weighted field costs and explicit penalties for context mismatch and intent conflict.
18. The method of claim 13, wherein mapping applies threshold intervals `theta_allow`, `theta_escalate`, and `theta_deny` from the machine-constant set.
19. The method of claim 13, wherein executing or constraining includes action-class routing for read, write, execute, destructive, and sensitive-transfer classes.
20. The method of claim 13, wherein updating trust state includes six-domain weighting for orchestration, messaging, policy-binding, computation, security, and ledger domains.
21. The method of claim 13, wherein emitting includes writing a deterministic record with a hash-linked sequence number.
22. The method of claim 13, further comprising auditing machine-constant updates as signed version transitions.
23. The method of claim 13, wherein token ordering uses a monotonic clock source and deterministic scheduler tick configuration.
24. The method of claim 13, wherein context-lock validation occurs before permitting write, execute, destructive, or sensitive-transfer actions.

### Independent Claim 25 (Non-Transitory Medium)
25. A non-transitory computer-readable medium storing instructions that, when executed by one or more processors, cause the one or more processors to perform operations comprising: ingesting token and context inputs (`C25[a]`); projecting the inputs into a logical control hyperspace representation (`C25[b]`); evaluating policy-field functions using versioned machine constants (`C25[c]`); computing a deterministic governance score and mapping the score to a governance decision (`C25[d]`); gating execution according to the governance decision (`C25[e]`); updating trust and telemetry state (`C25[f]`); and persisting a deterministic audit trace bound to constants version metadata (`C25[g]`).

Dependent claim candidates for Claim 25:
26. The non-transitory computer-readable medium of claim 25, wherein the instructions enforce bounded-precision arithmetic settings in a critical decision loop.
27. The non-transitory computer-readable medium of claim 25, wherein the instructions serialize deterministic audit records in a canonical schema.
28. The non-transitory computer-readable medium of claim 25, wherein the instructions expose a plugin interface for policy fields while preserving deterministic evaluation order.
29. The non-transitory computer-readable medium of claim 25, wherein the instructions include replay routines that reproduce governance outcomes for identical inputs and constant versions.
30. The non-transitory computer-readable medium of claim 25, wherein the instructions integrate a queue manager that applies decision-specific routing and quarantine handling.
31. The non-transitory computer-readable medium of claim 25, wherein the instructions invoke quorum validation services for high-risk action classes.
32. The non-transitory computer-readable medium of claim 25, wherein the instructions enforce context-bound cryptographic envelope checks with nonce-window verification.
33. The non-transitory computer-readable medium of claim 25, wherein the instructions maintain threshold profiles with version rollback controls.
34. The non-transitory computer-readable medium of claim 25, wherein the instructions default to fail-closed behavior when policy or signature metadata is missing.
35. The non-transitory computer-readable medium of claim 25, wherein the instructions emit telemetry artifacts associating governance decisions with route-cost adjustments.
36. The non-transitory computer-readable medium of claim 25, wherein digital-twin-derived threshold proposals are applied only after creation of a new auditable constant version.

## Implementation Hooks (Drafting Anchors)
- Token schema hook: `token_id`, `issued_at`, `context_commitment`, `intent_class`, `policy_vector`, `trust_vector`, `risk_score`, `proposed_action`.
- Runtime pipeline hook: ingest -> project -> evaluate fields -> aggregate -> map decision -> apply membrane -> update trust -> audit.
- Determinism hook: monotonic ordering, stable field order, bounded precision, constants-version pinning.
- Platform hook: execution on general-purpose processors, accelerators, and mixed distributed infrastructure without changing governance semantics.
