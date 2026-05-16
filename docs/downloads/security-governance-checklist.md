# AetherMoore AI Security Governance Checklist

The model is not the security boundary.

## Reference Monitor

- Is every dangerous action forced through a deterministic gate?
- Can the model bypass the gate by changing wording?
- Does the gate live at the tool/runtime boundary, not inside model persuasion?

## Action Contract

For each risky tool, define:

- Allowed paths, accounts, projects, or scopes.
- Required evidence before action.
- Reversibility and rollback plan.
- Secret-exfiltration constraints.
- Human approval threshold.
- Failure behavior.

## Receipts

Log enough to audit:

- Requested action.
- Allowed or blocked decision.
- Evidence used.
- Policy rule triggered.
- Final artifact or command result.

## Practical Rule

Start with one tool. Prove one contract. Measure false allows and false blocks before adding a learned risk score.
