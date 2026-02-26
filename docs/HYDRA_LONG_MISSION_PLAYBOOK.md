# HYDRA Long-Mission Playbook (1000-step Browser Swarms)

This playbook defines how to run long-horizon, multi-browser missions with SCBE governance and HYDRA-style coordination.

## 1) Execution model

- Use a **mission graph** (phases + dependencies) instead of one flat 1000-step script.
- Each job owns a unique `page_lock` to avoid duplicate actions against the same target.
- Run actions in bounded chunks (`--max-actions-per-request`) for checkpointable progress.

## 2) Governance gates

- **Capability gate**: DELIBERATION jobs require capability token.
- **PQC metadata gate**: DELIBERATION jobs with `pqc` metadata are quarantined if key IDs are missing or rotation age exceeds policy.
- **Verification gate**: each response is scored and mapped to `ALLOW`/`QUARANTINE`/`DENY|NOISE`.

## 3) Job payload recommendations

```json
{
  "job_id": "recon-001",
  "agent_id": "pilot-1",
  "risk_tier": "DELIBERATION",
  "page_lock": "example.com:pricing",
  "capability_token": "...",
  "pqc": {
    "kyber_id": "kyb-prod-01",
    "dilithium_id": "dil-prod-01",
    "last_rotated_hours": 24,
    "rotation_hours": 720
  },
  "actions": [
    {"action": "navigate", "target": "https://example.com"},
    {"action": "extract", "target": "h1"}
  ],
  "verify": {
    "must_contain": ["example"],
    "max_redirects": 2
  }
}
```

## 4) CLI usage

```bash
python scripts/aetherbrowse_swarm_runner.py \
  --jobs-file jobs/multi_browser.json \
  --concurrency 8 \
  --max-actions-per-request 40 \
  --artifact-root artifacts/aetherbrowse_runs
```

## 5) Reliability patterns

- Keep job chunks <= 50 actions to reduce blast radius and make replay deterministic.
- Reserve role lanes by convention:
  - `pilot-*` executes browser actions.
  - `copilot-*` verifies extraction quality.
  - `judge-*` handles disposition/escalation only.
- Route all mission traces and decision records into immutable artifact storage.

## 6) Definition of done for “1000-step ready”

- At least one mission with 1000+ primitive actions completes via chunked requests.
- No duplicate `page_lock` assignments within a run.
- All DELIBERATION jobs include capability token + PQC metadata checks.
- Decision records and trace hashes available for every job.
