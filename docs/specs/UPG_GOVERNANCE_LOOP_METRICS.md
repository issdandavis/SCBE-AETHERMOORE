# UPG Governance Loop Metrics

Status: draft v0.1  
Date: 2026-04-01  
Scope: measurable telemetry for separating damping from adaptation in governed agent loops

---

## Purpose

The Universal Propagation Grammar says long autonomous loops improve only when feedback creates real adaptation. Otherwise the loop is just energy loss with nicer prose around it.

This document defines the metrics that separate those two states:

- damping: the loop is consuming effort without meaningfully improving the pattern
- adaptation: the loop is using feedback to retune future proposals

The target implementation surface is the current governed runner plus the canonical offline decision path.

Anchors:

- [UNIVERSAL_PROPAGATION_GRAMMAR.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/UNIVERSAL_PROPAGATION_GRAMMAR.md)
- [governance_gated_agent_loop.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/governance_gated_agent_loop.py)
- [offline_mode.ts](C:/Users/issda/SCBE-AETHERMOORE/src/governance/offline_mode.ts)

---

## Core Definitions

### Proposal

One candidate artifact emitted by the agent at retry step `t`.

### Feedback packet

The structured response returned by the gate and validation surfaces.

Minimum fields:

- canonical decision
- reason codes
- local risk findings
- validation failures

### Damping

Damping is loop energy that does not materially improve future proposals.

Observable signs:

- many retries with near-identical outputs
- repeated reason codes
- low delta between candidate `t` and candidate `t+1`
- no improvement in test pass rate or approval probability

### Adaptation

Adaptation is measurable retuning after feedback.

Observable signs:

- risk profile improves after denial
- reason codes change in the expected direction
- candidate deltas are targeted rather than random
- approval probability rises
- the same class of future task improves with fewer retries

---

## Instrumentation Model

For every attempt, log:

| Field | Description |
| --- | --- |
| `task_id` | stable task identifier |
| `attempt_index` | retry number starting at 1 |
| `candidate_hash` | content hash for the proposal |
| `decision` | canonical `ALLOW \| QUARANTINE \| DEFER \| DENY` |
| `reason_codes` | canonical reason list |
| `risk_counts` | local severity counts |
| `test_passed` | boolean post-apply validation result |
| `elapsed_sec` | wall time for this attempt |
| `changed_target` | whether the proposal materially changed the target file |
| `approved_after_attempt` | whether this attempt ended the loop |

Derived fields should be computed after the session.

---

## Primary Metrics

### 1. Retry Delta

Measures how much each new proposal differs from the previous one.

Recommended implementation:

- normalized diff ratio on the applied artifact
- or hash inequality plus line-change count

Interpretation:

- very low delta across repeated denials indicates damping
- moderate targeted delta after specific reason codes indicates adaptation

### 2. Reason-Code Persistence

Measures how long the same rejection reason survives across retries.

Recommended implementation:

- count consecutive attempts where the same canonical reason appears

Interpretation:

- high persistence with low candidate delta indicates stagnation
- falling persistence after targeted edits indicates adaptation

### 3. Risk Gradient

Measures whether severity and quantity of findings trend down.

Recommended implementation:

- weighted risk score per attempt
- example weights: `critical=8`, `high=4`, `medium=2`, `low=1`

Interpretation:

- a negative slope is adaptation
- a flat or rising slope is damping or mislearning

### 4. Approval Efficiency

Measures cost to reach a successful end state.

Recommended implementation:

- attempts to approval
- wall-clock time to approval
- tests-run to approval

Interpretation:

- lower cost at equal task difficulty means better adaptation

### 5. Post-Approval Integrity

Measures whether approved outputs actually survive execution.

Recommended implementation:

- approval followed by test pass
- approval followed by no immediate rollback

Interpretation:

- low integrity means the loop learned to satisfy the gate without satisfying reality

---

## Damping Metrics

These metrics are specifically about loss and decay.

### D1. Structural Repetition Rate

How often the loop emits nearly the same candidate after denial.

Signal:

- repeated candidate hashes
- diff ratio below a threshold such as `0.03`

### D2. Denial Fatigue Index

How much work is spent on attempts that do not change the denial class.

Suggested formula:

```text
denial_fatigue = repeated_denials_without_reason_change / total_denials
```

### D3. Improvement Decay

How quickly the per-attempt gain shrinks.

Suggested proxy:

```text
improvement_decay = mean(delta_gain_t+1 - delta_gain_t)
```

Where `delta_gain` can be defined as the drop in weighted risk score or the drop in failing reason count.

### D4. Context Rot Proxy

A practical signal that the loop is losing coherence.

Suggested measurements:

- retries where the proposal reintroduces a previously fixed issue
- retries where unrelated code churn rises
- retries where explanation length grows but targeted changes shrink

---

## Adaptation Metrics

These metrics are about useful retuning.

### A1. Targeted Fix Ratio

What share of candidate edits map to the previous denial reasons.

Suggested implementation:

- detect whether edits touch files or lines implicated by prior reasons

Interpretation:

- higher targeted ratio means the loop is listening to the gate

### A2. Reason Resolution Velocity

How quickly a specific reason code disappears after first appearing.

Suggested implementation:

- attempts from first appearance to last appearance per reason

Interpretation:

- lower velocity is better

### A3. Cross-Task Carryover

Whether one governed session improves the next similar task.

Suggested implementation:

- compare approval efficiency for related tasks before and after similar training triples were logged

Interpretation:

- lower retries on later similar tasks indicates real adaptation, not one-off luck

### A4. Reconstruction Quality

Whether the loop converges on the real failure rather than a superficial patch.

Suggested proxy:

- final accepted change addresses the dominant prior reason codes
- post-approval tests cover the same failure family

---

## Session Classification

Each governed run should be classifiable as one of four states:

| State | Description |
| --- | --- |
| `productive_adaptation` | reason persistence falls, risk gradient improves, approval integrity holds |
| `partial_adaptation` | some reasons resolve but efficiency remains poor |
| `damped_loop` | retries continue with low change and low gain |
| `deceptive_alignment` | approvals happen but post-approval integrity is weak |

Recommended initial rules:

- `productive_adaptation`: approval achieved, post-approval integrity true, weighted risk score drops materially, denial fatigue low
- `damped_loop`: no approval, low retry delta, repeated reasons
- `deceptive_alignment`: approval achieved, but tests or rollback show failure

---

## Minimal Derived Formulas

These are intentionally simple so they can be implemented without a new analytics stack.

### Weighted risk score

```text
risk_score_t = 8*c_t + 4*h_t + 2*m_t + 1*l_t
```

### Damping score

```text
damping_score = 0.4*repetition_rate + 0.3*denial_fatigue + 0.3*improvement_decay_norm
```

### Adaptation score

```text
adaptation_score = 0.35*targeted_fix_ratio + 0.35*reason_resolution_velocity_norm + 0.30*post_approval_integrity
```

The exact normalization rules should be documented with the first implementation.

---

## Testable Predictions

1. Structured denial reasons should reduce denial fatigue relative to generic denials.
2. Loops with higher targeted-fix ratio should reach approval faster.
3. Post-approval integrity should correlate more strongly with adaptation score than with raw retry count.
4. Training on rejected -> corrected -> approved triples should improve cross-task carryover on similar bug classes.

---

## First Implementation Surface

The first implementation should be conservative.

1. Extend the current governed loop logs with stable attempt metrics.
2. Add derived-metric computation as a post-run summary, not inline control logic.
3. Report the final session state using the classification table above.
4. Keep canonical decisions owned by the offline governance path.

This avoids mixing new analytics logic into the decision kernel too early.

---

## Failure Conditions

This metrics layer should be revised if:

1. the metrics can be gamed by trivial proposal churn
2. approval efficiency improves while post-approval integrity falls
3. adaptation score fails to predict future carryover on related tasks
4. damping and adaptation are not separable in observed runs

If the metrics cannot distinguish a healthy long run from a noisy loop, the model is wrong.
