# Machine-Science Taxonomy Map

This document formalizes:

`axes -> constants -> fields -> actions`

for SCBE-AETHERMOORE machine-science governance.

## 1. Axes

| Axis ID | Axis Name | Description | Typical Source |
|---|---|---|---|
| `t` | Time | Tick phase, sequence order, freshness, decay window | monotonic clock, scheduler |
| `i` | Intention | Requested objective class and confidence | planner, user command parser |
| `p` | Policy | Active policy regime and scope | governance profile, route policy |
| `u` | Trust | Actor trust state and role weights | agent trust engine, quorum state |
| `r` | Risk | Composite risk estimate | anomaly detector, rule engine |
| `c` | Context | Device/load/entropy/posture commitment | runtime state, context hash |

## 2. Machine Constants

| Constant Family | Examples | Purpose |
|---|---|---|
| `k_tick` | `tick_hz`, `window_size` | deterministic update cadence |
| `k_decay` | `trust_decay`, `reinforcement_decay` | bounded state drift and forgetting |
| `k_gate` | `theta_allow`, `theta_escalate`, `theta_deny` | governance decision boundaries |
| `k_route` | `risk_latency_multiplier`, `quarantine_path_cost` | risk-weighted route shaping |
| `k_crypto` | `context_lock_strength`, `nonce_window` | context-bound crypto envelope behavior |
| `k_stability` | `max_update_step`, `clip_bounds` | numerical stability in loops |

## 3. Policy Fields

Each field reads axis state and constants, then emits cost/permit signals.

| Field ID | Inputs | Outputs | Behavior |
|---|---|---|---|
| `F_safety` | `i, r, c` | risk cost, allow bit | blocks unsafe intent-risk pairings |
| `F_compliance` | `p, c, t` | policy cost, reason | enforces jurisdiction and procedural rules |
| `F_resource` | `t, c, r` | pressure cost | throttles under load or anomaly pressure |
| `F_trust` | `u, i, t` | trust cost | penalizes divergence from expected actor behavior |
| `F_route` | `r, u, c` | path cost | increases path cost for suspicious trajectories |
| `F_quorum` | `u, p, i` | quorum permit | requires role-diverse signatures for critical actions |

## 4. Action Classes

| Action Class | Trigger Pattern | Default Governance |
|---|---|---|
| `A_read` | search, fetch, inspect, snapshot | `ALLOW` unless policy conflict |
| `A_write` | update content, post message, modify state | `QUARANTINE` or `ESCALATE` by policy |
| `A_execute` | run task, invoke connector, deploy | `ESCALATE` for medium/high risk |
| `A_destructive` | delete, revoke, reset, terminate | quorum-gated, often `DENY` without quorum |
| `A_sensitive_transfer` | key material, credentialed publish, privileged routing | context-lock + quorum |

## 5. Mapping: Axes -> Constants -> Fields -> Actions

| Axis | Primary Constants | Primary Fields | Dominant Action Impact |
|---|---|---|---|
| `t` | `k_tick`, `k_decay` | `F_resource`, `F_compliance` | throttling, expiry, replay gating |
| `i` | `k_gate` | `F_safety`, `F_trust` | intent-risk decision boundaries |
| `p` | `k_gate`, `k_route` | `F_compliance`, `F_quorum` | required approvals and route restrictions |
| `u` | `k_decay`, `k_gate` | `F_trust`, `F_quorum` | trust-based allow/quarantine/escalate |
| `r` | `k_gate`, `k_route` | `F_safety`, `F_route` | routing penalties and deny thresholds |
| `c` | `k_crypto`, `k_stability` | `F_safety`, `F_compliance` | context-lock validity and fail-closed behavior |

## 6. Six Tongues Alignment (Policy Weight Layer)

Treat Six Tongues as a structured trust-policy weighting vector, not a narrative-only artifact.

| Tongue | Domain Role | Typical Field Weighting Emphasis |
|---|---|---|
| `KO` | orchestration/control | `F_quorum`, `F_compliance` |
| `AV` | messaging/io | `F_safety`, `F_resource` |
| `RU` | constraints/policy binding | `F_compliance`, `F_trust` |
| `CA` | computation/logic | `F_route`, `F_safety` |
| `UM` | security/privacy | `F_safety`, `F_quorum`, `F_crypto` |
| `DR` | structure/ledger | `F_compliance`, deterministic audit |

## 7. Minimal Deterministic Record Schema

```json
{
  "token_id": "uuid",
  "axes": {"t": 0.0, "i": 0.0, "p": 0.0, "u": 0.0, "r": 0.0, "c": 0.0},
  "constants_version": "vX.Y.Z",
  "field_outputs": {
    "F_safety": {"cost": 0.0, "permit": true},
    "F_compliance": {"cost": 0.0, "permit": true}
  },
  "decision_score": 0.0,
  "governance_decision": "ALLOW",
  "action_class": "A_read",
  "timestamp": "iso8601"
}
```

## 8. Operational Rule of Thumb

- If context commitment or signature checks fail: prefer `QUARANTINE` or `DENY`.
- If risk rises with low trust: increase route and execution costs before hard deny where safe.
- If action class is destructive or sensitive: require quorum and explicit policy-field pass.

