# RFC-0001: Machine-Science Control Framework Core Spec

Status: Draft  
Version: 0.1  
Authoring scope: SCBE-AETHERMOORE core

## 1. Abstract

This document defines the core behavior of SCBE-AETHERMOORE as a machine-science control framework.
The framework does not model real-world physics. It uses tunable, physics-style invariants as machine constants
to enforce deterministic behavior across heterogeneous systems.

Time, intention, trust, risk, policy, and operational context are modeled as explicit dimensions in a shared
control hyperspace. Tokens, agents, and actions are evaluated as state transitions in that space.

## 2. Normative Language

The keywords MUST, SHOULD, and MAY are normative.

## 3. Scope

This RFC specifies:

- shared hyperspace axes
- machine constants and update rules
- policy fields and overlap behavior
- token lifecycle and governance decisions
- deterministic execution requirements

This RFC does not specify:

- UI or narrative presentation layers
- specific cloud vendor deployment layouts
- proprietary training data

## 4. Core Definitions

- Hyperspace: the multi-dimensional control space used for governance decisions.
- Axis: one coordinate dimension in hyperspace.
- Machine constant: a configurable invariant used to keep behavior stable across platforms.
- Policy field: a function over hyperspace that adds cost, permission, or penalty.
- Token: a stateful unit of work (request, packet, event, action, task).
- Trajectory: a token's movement through hyperspace over time.
- Governance result: `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`.

## 5. Hyperspace Axes (Minimum Set)

Implementations MUST expose these axes:

1. `t`: time phase and sequence position
2. `i`: intention class and confidence
3. `p`: active policy vector
4. `u`: trust state (agent/user/system)
5. `r`: risk state
6. `c`: context commitment (device, load, entropy, posture)

Implementations MAY add domain axes (for example throughput pressure or jurisdiction domain), but MUST preserve
the base six axes.

## 6. Machine Constants

Machine constants are framework-controlled values that define stable behavior and deterministic transitions.

Minimum constant families:

- `k_tick`: control loop tick rate
- `k_decay`: trust and reinforcement decay rates
- `k_gate`: decision thresholds for policy fields
- `k_route`: cost multipliers for path selection
- `k_crypto`: context-lock envelope parameters
- `k_stability`: numeric stability bounds for iterative control

Requirements:

- Constants MUST be explicit and versioned.
- Constant updates MUST be audited.
- Runtime behavior MUST be reproducible for the same input stream and constant set.

## 7. Policy Field Model

Each policy field is a function:

`F_j(x, k) -> (cost_j, permit_j, reason_j)`

where:

- `x` is current hyperspace state
- `k` is current machine constant set

Composite decision score:

`S = sum(w_j * cost_j) + penalty(context_mismatch) + penalty(intent_conflict)`

Decision mapping:

- `ALLOW` when `S < theta_allow`
- `QUARANTINE` when `theta_allow <= S < theta_escalate`
- `ESCALATE` when `theta_escalate <= S < theta_deny`
- `DENY` when `S >= theta_deny`

Thresholds (`theta_*`) are machine constants.

## 8. Token Model

Minimum token envelope:

```json
{
  "token_id": "uuid",
  "issued_at": "iso8601",
  "context_commitment": "hash",
  "intent_class": "string",
  "policy_vector": ["safety", "compliance", "resource"],
  "trust_vector": {"ko": 0.0, "av": 0.0, "ru": 0.0, "ca": 0.0, "um": 0.0, "dr": 0.0},
  "risk_score": 0.0,
  "proposed_action": "string"
}
```

Token processing MUST be fail-closed:

- unresolved context commitment -> `QUARANTINE` or `DENY`
- invalid signature -> `DENY`
- missing policy metadata -> `ESCALATE`

## 9. Control Loop

Per tick, implementations MUST execute:

1. Ingest token and current system context.
2. Project token into hyperspace state.
3. Evaluate policy fields.
4. Compute decision score and governance result.
5. Execute or constrain action path.
6. Update trust and telemetry.
7. Emit deterministic audit record.

Pseudo-flow:

```text
for token in stream:
  x = embed(token, context, constants)
  fields = eval_fields(x, constants)
  S = aggregate(fields, constants)
  decision = map_score(S, constants)
  apply(decision, token)
  update_trust(token, decision, constants)
  log(token, x, fields, S, decision, constants_version)
```

## 10. Determinism Requirements

- Numeric operations SHOULD use fixed-point or deterministic bounded-precision mode in critical loops.
- Time source MUST be monotonic for ordering.
- Policy evaluation order MUST be stable.
- Audit logs MUST include constants version and decision trace.

## 11. Security Considerations

- Context-bound cryptography SHOULD avoid oracle-style rejection signals when possible.
- Quorum-protected actions SHOULD require role diversity for critical operations.
- Trust decay and self-exclusion SHOULD be automatic under repeated divergence.
- Replay defense MUST include nonce/time-window checks.

## 12. Reference Surface (Current Repo Mapping)

- Runtime governance and planning: `aetherbrowse/runtime/`
- Worker execution membrane: `aetherbrowse/worker/`
- Policy and trust logic: `src/` and `policies/`
- Telemetry and artifacts: `artifacts/`

This mapping is informative, not normative.

