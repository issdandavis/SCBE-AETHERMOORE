# UPG governance seed set

This folder contains a first seed dataset for Universal Propagation Grammar (UPG) applied to real governance-gated agent loops.

File:
- `governance_agent_loops_upg_seed.jsonl`

What is in the seed:
- 10 source-traceable examples pulled from recent repo artifacts
- both failure and pass cases
- UPG-mapped fields using the repo's current governance language

Primary artifact sources:
- `artifacts/security/audit_20260329.json`
- `artifacts/system-audit/workflow_audit.json`
- `artifacts/agent_comm/...cross-talk...json`
- `artifacts/github-control/github_control_latest.json`
- `artifacts/task_logs/workflow_test_20260323_183955.json`
- `artifacts/publish_campaigns/latest/claim_gate_report.json`

Intended use:
- SFT seed data for UPG diagnosis
- benchmark prompts for cross-domain reasoning
- ground-truth examples for future failed-merge / gate-repair logging

Current coverage:
- security gate failures
- workflow substrate mismatches
- token-scope failures
- branch-protection interference
- dry-run versus live worker states
- positive resonance examples

Next recommended expansion:
- convert real failed PR diffs plus CI logs into the same schema
- add long-session attenuation cases where constraints are forgotten
- add reconstruction payload targets for retry-agent training
