# SCBE Self-Improvement Loop - 2026-02-17

## Path Chosen
- `Knowledge propagation to another AI system`

## Completed Work Captured
- Added and shipped encoded SCBE token acceptance in `agents/browser/main.py`.
- Preserved raw-token compatibility for existing clients.
- Added decoder modes for bridge compatibility: `raw`, `base64url`, `base64`, `hex`, `xor`.

## Pattern Extracted
- Repeated workflow:
1. Add gateway compatibility at service boundary.
2. Keep legacy contract stable.
3. Emit explicit operational docs for non-coder operators.
4. Package machine-readable context so other agents can execute without drift.

## Reusable Operations Contract
- Canonical wall formula (unchanged): `H(d*,R) = R * pi^(phi * d*)`
- Required dual output for agent tasks:
1. `state_vector` JSON: `coherence`, `energy`, `drift`
2. `decision_record` JSON: `action`, `signature`, `timestamp`

## Candidate Skill (Draft Only, Not Installed)
- Proposed name: `scbe-aetherbrowse-auth-ops`
- Purpose: Standardize token/header/env handling for SCBE browser services and n8n/Asana bridges.
- Trigger examples:
1. "encoded API key"
2. "browser webhook auth"
3. "n8n headers for SCBE"
4. "service says missing API key"

## Approval Gate Status
- No new skill installed in this loop.
- Candidate documented only.

