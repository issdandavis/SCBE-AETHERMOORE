# Modified Condition Decision Coverage Application Plan

Date: 2026-04-30

## Why This Matters

Modified Condition Decision Coverage, or MC/DC, is the coverage discipline used in high-assurance aviation and space software when ordinary line or branch coverage is not enough. The practical idea is simple: for every important Boolean decision, prove that each individual condition can independently change the decision outcome.

For SCBE-AETHERMOORE, this maps directly onto our governance problem. We have a lot of gates that combine trust, risk, authentication, tool capability, verification score, browser side effects, model fallback, and policy state. High line coverage can still miss a broken gate if one condition is always masked by another. MC/DC gives us a way to test the gate logic itself.

## Source-Grounded Definition

NASA SWE-219 requires 100 percent MC/DC coverage for identified safety-critical software components and describes the core obligations: entry and exit points invoked, each decision taking each outcome, each condition taking true and false, and each condition independently affecting the outcome.

NIST summarizes MC/DC as a strong criterion required by the FAA for catastrophic-failure consequence software, requiring every condition in a decision to take all outcomes and independently affect the decision outcome.

FAA/NASA tutorial material distinguishes MC/DC from plain decision coverage: the structural element is the logical condition inside a decision, not just the branch as a whole. The tutorial also separates unique-cause MC/DC, where only one condition changes in the independence pair, from masking MC/DC, where Boolean masking can prove independent effect even if more than one raw value changes.

## What We Should Not Claim

We should not claim DO-178C compliance or certified MC/DC. That requires tool qualification, requirements traceability, safety classification, and audit evidence beyond this repo.

The correct claim for now is narrower:

SCBE uses MC/DC-inspired decision-gate tests for high-risk governance and agent-routing logic.

## Where It Fits In Our System

Use MC/DC on deterministic gate code first:

- Browser and command routing risk gates.
- Agent-bus allow, quarantine, deny, and noise decisions.
- Safe-apply patch gates.
- Payment, billing, and webhook hardening decisions.
- GeoSeal and Layer 13 / Layer 14 governance thresholds.
- Colab and remote-compute worker state transitions.

Do not start with generated training data, notebooks, UI styling, or experimental math demos. MC/DC is most valuable where a Boolean decision protects a side effect.

## SCBE Test Pattern

For each high-risk decision function:

1. Name each Boolean condition.
2. Build a truth table or reduced MC/DC matrix.
3. Add independence pairs where changing one condition changes the decision while the others are fixed or logically masked.
4. Assert the decision and the reason string.
5. Store the matrix in the test docstring or adjacent Markdown when the gate is complex.

Example gate:

```text
decision = high_risk_keyword OR auth_keyword OR side_effect_keyword OR unclear_browser_action
```

Minimal MC/DC-style rows:

```text
baseline: all false -> low
auth only -> medium
side effect only -> medium
high risk only -> high
browser action without read-only -> medium
browser action with read-only -> low
```

## Initial Repo Application

The first executable application is in:

- `tests/aetherbrowser/test_command_planner.py`

The new test is:

- `test_risk_gate_mcdc_condition_independence`

It locks the independence behavior for:

- Authentication keywords.
- State-changing keywords.
- High-impact keywords.
- Browser-action ambiguity.
- Read-only masking of browser-action ambiguity.

## Next High-Value Targets

1. `scripts/aetherbrowse_swarm_runner.py::_decide`

   Conditions: capability valid, verification score greater than or equal to 0.90, verification score greater than or equal to 0.60, noise-on-deny.

2. `scripts/agents/safe_apply.py`

   Conditions: path allowed, patch parses, write target inside workspace, dry-run versus apply, forbidden patterns absent.

3. `src/api/stripe_billing.py` and billing tests

   Conditions: event verified, customer/subscription present, idempotency state, price/product match, signature accepted.

4. `scripts/system/colab_worker_lease.py`

   Conditions: authenticated, notebook loaded, runtime connected or connect attempted, run-all requested, trust warning dismissed, secret prompts granted.

5. `src/geoseal_cli.py` and `src/api/geoseal_cli_bridge.py`

   Conditions: command allowed, packet verified, route exists, policy tier allows action, artifact path safe.

## Training Data Use

MC/DC tables are useful training records because they pair:

- natural-language requirement,
- condition matrix,
- executable tests,
- expected gate decision,
- failure reason.

That fits the agentic coding model better than generic code snippets. It teaches the model to preserve the invariants behind a decision, not just rewrite syntax.

## One-Line Operating Rule

If a gate can block, permit, spend, publish, delete, deploy, authenticate, or execute tools, it should eventually have an MC/DC matrix.
