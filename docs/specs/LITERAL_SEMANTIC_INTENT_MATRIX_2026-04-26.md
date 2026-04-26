# Literal and Semantic Intent Parameter Matrix

## Purpose

The matrix separates what a user literally says from what the request would do in context.

This matters because the same surface words can be safe in one lane and dangerous in another:

- `negabinary`, `inverse gravity`, and polarity language can be valid for game mechanics, binary interpretation, scoring, or training.
- The same language cannot reduce access-control risk or convert a blocked route into a positive authorization.
- `backdoor`, `bypass`, `secret access`, `discreet access`, and similar terms are red-team detection signals.

## Rule

Backdoor access is not a feature. It is a test category.

If a request combines polarity-transform language with hidden access, bypass, or authority elevation language, the semantic intent is `unauthorized_access_attempt` and the decision is `DENY`.

If a request asks for a legitimate access-control change in an action context, the decision is `ESCALATE` for authority review.

If a request uses polarity language only for games, binary interpretation, training, or scoring, it can be `ALLOW` as a non-authority signal.

## Implementation

Code:

```text
python/scbe/semantic_gate.py
```

Main entrypoint:

```python
parameterize_literal_semantic_intent(text, context="routing")
```

Regression tests:

```text
tests/governance/test_semantic_gate.py
```

Verified behavior:

```powershell
python -m pytest tests/governance/test_semantic_gate.py -q
```

## Matrix Outputs

- `literal_intent`: what action shape the words request, such as build, test, route, explain, or access.
- `semantic_intent`: what the request means operationally, such as game interpretation, access-control change, or unauthorized access attempt.
- `polarity_mode`: positive, negative, negabinary, inverse gravity, or neutral.
- `decision`: allow, quarantine, escalate, or deny.
- `risk`: low, medium, high, or critical.
- `parameters`: numeric routing signals such as access pressure, bypass pressure, game pressure, polarity pressure, and action pressure.

## Security Boundary

The classifier is not authentication. It is a governance signal.

Authority still comes from real authentication, policy, signatures, receipts, and triplet-ledger verification. The matrix cannot lower access risk. It can only raise risk, preserve sandbox/game meaning, or route the request to review.
