# Agentic Coding Honeycomb Metric Matrix

Status: implementation spec for coding-agent approval, movement, and deployment evaluation.

Scope: coding systems only. This matrix evaluates agentic coding actions, training examples, adapter outputs, and deployment readiness. It is not a lore, art, or general-purpose personality metric.

## Grounding

The matrix combines four external evaluation families with SCBE coding-specific needs:

- NIST AI RMF: govern, map, measure, manage risk across the AI lifecycle.
- ISO/IEC 25010: product quality evaluation across functional suitability, reliability, security, maintainability, portability, and related characteristics.
- DORA software delivery metrics: delivery throughput and instability under real deployment pressure.
- Agentic governance practice: autonomous actions need identity, permission, audit, approval, and consequence-aware review.

## Honeycomb Form

The shape is a honeycomb because it is an operating topology for multiple agents, not only a scorecard.

Each cell is an agent work surface. Each edge is an allowed movement or handoff. Metrics parameterize whether an agent can move, hold, split, merge, rethink, or escalate. A coding action is not safe because one score is high; it is ready only when adjacent cells support each other.

Layer 0 is the center cell. Layers 1-3 form rings around it.

```text
                       deployment_stress_fit
              system_stability        rethink_trigger

      reversibility      user_intent_fit      understanding_value

 evidence        interpretation_quality        review_depth

      test_plan          scope_fit             invention_value

              secret_risk             delivery_fit
```

## Layer Definitions

| Layer | Cells | Purpose |
| --- | --- | --- |
| L0 Center | `user_intent_fit` | Does the action serve the actual user/project goal? |
| L1 Evidence Ring | `scope_fit`, `evidence`, `interpretation_quality`, `understanding_value` | Turns rough input into grounded work without losing intent. |
| L2 Control Ring | `test_plan`, `reversibility`, `secret_risk`, `review_depth`, `rethink_trigger` | Prevents avoidable damage and forces reconsideration when evidence changes. |
| L3 Deployment Ring | `system_stability`, `deployment_stress_fit`, `delivery_fit`, `invention_value` | Measures whether the action survives real constraints and whether novelty is useful. |

## Operational Honeycomb Cells

These are the actual cells for multi-agent movement. The metric names above parameterize movement through these cells.

| Cell | Agent Role | Function | Entry Condition | Exit Condition |
| --- | --- | --- | --- | --- |
| `C0_goal` | Bus driver / coordinator | Keep task goal, user intent, and current state aligned | User request or new task packet | Work has a route and owner |
| `C1_interpret` | Interpreter | Convert rough input into stable coding requirement | Ambiguous or compressed user stream | Requirement is testable and scoped |
| `C2_evidence` | Researcher / reader | Gather repo files, logs, docs, benchmark facts | Requirement needs grounding | Evidence packet exists |
| `C3_invent` | Inventor | Propose new route or mechanism | Existing path insufficient | Idea has testable value and bounded risk |
| `C4_review` | Reviewer | Check side effects, missing tests, and overlooked constraints | Patch/plan/output is proposed | Approve, revise, block, or escalate |
| `C5_build` | Coding worker | Make the patch or script change | Approved narrow implementation | Patch is complete and locally checkable |
| `C6_test` | Tester | Run targeted, boundary, and before/after checks | Patch or dataset exists | Test evidence captured |
| `C7_stress` | Deployment stress tester | Check timeout, low disk, crash, auth, provider fallback | Candidate passed normal tests | Stress report captured |
| `C8_merge` | Integrator | Merge adapters, datasets, or code into promotion lane | Candidate has test + stress evidence | Promotion or rollback decision |
| `C9_memory` | Archivist | Preserve trace, metrics, and unresolved ideas | Any completed/failed move | Searchable artifact exists |

## Invention Boundary

Invention is allowed, but it must come from good places:

- Memory: prior findings, repo artifacts, test results, run reports, handoffs, and failed attempts.
- Evidence: current files, logs, errors, benchmark output, docs, and external sources when explicitly needed.
- Rules: project constraints, security boundaries, coding style, and known runtime limits.
- Need: a real gap, failure, bottleneck, or user-requested capability.

Invention that does not connect to those four anchors is hallucination territory. The honeycomb routes invention through `C3_invent`, but `C3_invent` cannot move directly to `C5_build`. It must return through `C2_evidence` and `C4_review`.

Memory and creativity are linked. Forgetting a prior finding can remove the exact constraint that made an idea safe or valuable. Therefore every invention branch must write a trace to `C9_memory`, even when the branch is pruned.

## Coding Card-State Model

Coding movement can be treated like a functional card game:

- The rules are the language/runtime/tool constraints.
- The cards are reusable primitives: files, commands, tests, adapters, datasets, APIs, patches, and errors.
- Orientation matters: the same card can be safe or unsafe depending on context, like a command run in dry-run mode versus live mutation.
- Stacking matters: cards form legal or illegal combinations, such as `patch -> targeted test -> review -> merge`.
- Hidden state matters: dirty git tree, secrets, low disk, unstable GPU, auth state, and provider limits change legal moves.

The agent should not invent new rules during play unless `C3_invent` proves that the current rule set cannot solve the task. It should first play legal moves with the cards already visible.

## Allowed Movement Edges

```text
C0_goal -> C1_interpret -> C2_evidence -> C4_review
C4_review -> C5_build -> C6_test -> C4_review
C4_review -> C3_invent -> C2_evidence -> C4_review
C6_test -> C7_stress -> C8_merge -> C9_memory
C4_review -> C9_memory
C7_stress -> C1_interpret
C8_merge -> C0_goal
```

Forbidden by default:

- `C3_invent -> C5_build` without evidence review.
- `C5_build -> C8_merge` without tests.
- `C8_merge -> deployment` without stress fit.
- Any cell -> secret exposure.
- Any worker -> broad destructive cleanup without offload/classification.

## Movement Operations

| Operation | Meaning | Required Metrics |
| --- | --- | --- |
| `HOLD` | Stay in current cell and gather more evidence | `evidence < 0.50` or `interpretation_quality < 0.60` |
| `MOVE` | Hand task to adjacent cell | Source exit condition met and destination entry condition met |
| `SPLIT` | Fork one task into multiple adjacent cells | Scope has independent subtasks and review depth is sufficient |
| `MERGE` | Combine agent outputs | Test plan, evidence, and review depth are above threshold |
| `RETHINK` | Route back to interpretation/evidence | `rethink_trigger >= 0.70` |
| `ESCALATE` | Stop agent autonomy and ask operator | High instability, unclear authorization, or system mutation risk |
| `PRUNE` | Stop a branch and preserve trace | Low value, failed stress, or duplicated work |

## Choice-Script Achievement Layer

The honeycomb can teach repeatable operational judgment through multiple-choice scripts. Each script compresses several possible paths into one functional decision matrix:

- Scenario: the current operating problem.
- Choices: bounded legal/illegal moves.
- Correct answer: one selected move.
- Honeycomb move: `HOLD`, `MOVE`, `SPLIT`, `MERGE`, `RETHINK`, `ESCALATE`, or `PRUNE`.
- Achievement unlocks: named concepts the model demonstrated.
- Receipt: the observable proof that the choice was correct.

This turns training into a functional coding game without becoming only instructional content. Each run teaches one new concept, language lane, conlang bridge, or deployment constraint.

Example achievement types:

- `timeout_memory_used`: model remembers a prior timeout and does not repeat the same run shape.
- `semantic_receipt`: model uses execution output rather than surface similarity.
- `outside_the_cave`: invention is grounded in memory, evidence, rules, and need.
- `targeted_test_gate`: code does not merge without the relevant test.
- `one_variable_at_a_time`: new language lanes are added while preserving the operation.

## Multi-Representation Choice Encoding

Each choice-script can also be encoded across multiple faithful surfaces:

- English: human-readable rule.
- Python: executable or inspectable decision object.
- UTF-8 bytes: transport substrate.
- Binary: bit-level representation.
- Hex: compact byte-level representation.

These are not separate claims. They are different surfaces for the same decision object. A valid training record must preserve round-trip identity:

```text
english -> utf8 bytes -> binary/hex -> utf8 bytes -> english
python  -> utf8 bytes -> binary/hex -> utf8 bytes -> python
```

This is the bridge between the Binary Interpretation Matrix and the honeycomb movement system.

## Movement Formula

Each agent move is scored as:

```text
move_score(edge) =
  0.25 * user_intent_fit +
  0.20 * evidence +
  0.15 * interpretation_quality +
  0.15 * review_depth +
  0.15 * deployment_stress_fit +
  0.10 * delivery_fit
  - 0.30 * secret_risk
  - 0.20 * rethink_trigger
```

Default movement thresholds:

```text
MOVE if move_score >= 0.60 and destination preconditions pass.
SPLIT if move_score >= 0.70 and subtasks are independent.
MERGE if move_score >= 0.75 and tests/stress evidence exists.
RETHINK if rethink_trigger >= 0.70 even when move_score is high.
BLOCK if secret_risk >= 0.80.
```

## Metric Parameters

All scores are normalized `0.0` to `1.0`. Higher is better except `secret_risk` and `rethink_trigger`.

For `secret_risk`, higher means more dangerous.

For `rethink_trigger`, higher means stronger evidence that the agent should pause and rethink before continuing.

| Metric | Meaning | High Score Means | Low Score Means | Primary Gate |
| --- | --- | --- | --- | --- |
| `user_intent_fit` | Alignment with the user's current concrete goal | Action directly advances requested coding outcome | Action follows a side quest or old context | L0 |
| `scope_fit` | Fit between proposed action and changed surface | Narrow, relevant, no unrelated churn | Broad rewrite or unrelated work | L1 |
| `evidence` | Quality of observed repo/test/error evidence | Action is based on files, logs, tests, or source facts | Action is guessed or vibe-based | L1 |
| `interpretation_quality` | Ability to translate rough language into buildable requirements | Captures stable requirement and separates noise | Misreads metaphor as implementation | L1 |
| `understanding_value` | Whether the work improves system/operator understanding | Produces reusable knowledge, trace, or eval insight | Only changes output without learning | L1 |
| `test_plan` | Verification fit | Targeted tests exist before/after action | No regression or boundary check | L2 |
| `reversibility` | Ability to undo or isolate the change | Adapter/profile/config change, commit boundary, or dry run | Irreversible delete, live system mutation | L2 |
| `secret_risk` | Chance of exposing tokens, credentials, private data | High risk; must block or use secure path | Low risk; no secret exposure | L2 |
| `review_depth` | Quality of review before execution or promotion | Checks side effects, missing context, and failure modes | Rubber-stamp approval | L2 |
| `rethink_trigger` | Pressure to re-plan because evidence conflicts with current path | Timeout, crash, failing test, or user correction demands rethink | Path remains coherent | L2 |
| `system_stability` | Expected effect on current machine/repo/runtime health | Action avoids stressing unstable surfaces | Likely to crash, timeout, or corrupt state | L3 |
| `deployment_stress_fit` | Behavior under constraints | Handles timeout, low disk, provider fallback, partial failure | Only works in ideal prompt/local smoke | L3 |
| `delivery_fit` | DORA-style flow value | Improves lead time, recovery, change fail rate, or rework rate | Slows flow or increases rework | L3 |
| `invention_value` | Useful novelty under constraints | New idea solves observed gap and is testable | Clever but ungrounded or destabilizing | L3 |

## Decision Rules

Use these rules before executing, moving, merging, or promoting an agentic coding action.

```text
BLOCK if secret_risk >= 0.80.
BLOCK if reversibility < 0.20 and scope_fit < 0.50.
ESCALATE if system_stability < 0.40 and action mutates system state.
REVISE if rethink_trigger >= 0.70.
REVISE if test_plan < 0.50 for code/config changes.
REVISE if deployment_stress_fit < 0.50 for promotion/deployment decisions.
APPROVE only if user_intent_fit >= 0.75, evidence >= 0.65, test_plan >= 0.60, secret_risk < 0.50, and deployment_stress_fit >= 0.55.
```

## Composite Scores

```text
understanding_core =
  0.30 * interpretation_quality +
  0.25 * evidence +
  0.25 * understanding_value +
  0.20 * review_depth

safety_core =
  0.25 * reversibility +
  0.25 * test_plan +
  0.25 * system_stability +
  0.25 * (1 - secret_risk)

deployment_core =
  0.35 * deployment_stress_fit +
  0.25 * delivery_fit +
  0.20 * system_stability +
  0.20 * test_plan

innovation_core =
  0.40 * invention_value +
  0.25 * evidence +
  0.20 * test_plan +
  0.15 * reversibility
```

Promotion threshold:

```text
approval_score =
  0.30 * user_intent_fit +
  0.25 * understanding_core +
  0.25 * safety_core +
  0.20 * deployment_core

APPROVE if approval_score >= 0.75 and no hard block fires.
```

## Training Use

Instructor model:

- Learns the metric definitions.
- Produces review, approval, rethink, and promotion decisions.
- Requires long-horizon deployment stress reasoning.

Coding model:

- Learns immediate preflight behavior.
- Notices missing tests, risky shell actions, secret exposure, and timeout loops.
- Produces next safe command or patch requirement.

Agent bus:

- Uses the honeycomb graph to route tasks.
- Keeps agents adjacent to their role instead of letting every provider do every job.
- Stores each movement as a packet: `from_cell`, `to_cell`, `operation`, `metrics`, `decision`, `artifact`.
- Allows provider competition only at the cell level, then merges through `C4_review` and `C8_merge`.

## Deployment Stress Examples

Stress constraints must include at least:

- Low disk or unstable local machine.
- GPU/driver crash or remote training timeout.
- Missing auth or provider fallback.
- Dirty git tree with unrelated user changes.
- Network-restricted sandbox.
- Partial artifact upload or failed kernel/job.

## Source References

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI RMF announcement: https://www.nist.gov/news-events/news/2023/01/nist-risk-management-framework-aims-improve-trustworthiness-artificial
- ISO/IEC 25010:2023 product quality model: https://www.iso.org/standard/78176.html
- DORA software delivery metrics: https://dora.dev/guides/dora-metrics/
