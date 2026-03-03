# GitHub Sectioning + Dual-Tentacle Model

## What You Asked For
- Split GitHub work into:
  - things you sell
  - things you keep public for trust/learning
  - things that should not be public
- Run dual-side operations:
  - one AI connected to webhook/page side
  - one AI connected to CLI/Git side
  - optional third hand in Codespaces/CI lane

## Repo Sectioning Model

### Tiers
1. `private_restricted`
- Contains secrets, client-sensitive workflows, internal strategy, or exploit surfaces.
- Never expose through public webhooks or public docs.

2. `public_sellable`
- Product/service repos you actively monetize.
- Keep public but add pricing, onboarding CTA, and support lane.

3. `public_open`
- General open-source credibility surfaces.
- Good for trust, hiring, and technical authority.

4. `public_education`
- Demos/tutorials/research that feed top-of-funnel.

### Automation Added
- Policy file: `config/governance/repo_sectioning_policy.json`
- Sectioning script: `scripts/system/github_repo_sectioning.py`

Run it:
```powershell
python scripts/system/github_repo_sectioning.py
```

Outputs:
- `artifacts/governance/github_repo_sectioning_<owner>_<timestamp>.csv`
- `artifacts/governance/github_repo_sectioning_<owner>_<timestamp>.md`

## Dual-Tentacle GitHub Operation

### Lanes
1. `webhook_lane`
- Inbound events from GitHub webhooks/pages/workflows.

2. `cli_lane`
- Deterministic git/gh operations (merge, branch, rebase, release, tagging).

3. `codespaces_lane`
- Heavy cloud dev tasks (integration tests, build, devcontainer, CI reruns).

### Automation Added
- Router script: `scripts/system/github_dual_tentacle_router.py`

Run examples:
```powershell
python scripts/system/github_dual_tentacle_router.py --event-type pull_request --task "triage PR #42"
python scripts/system/github_dual_tentacle_router.py --event-type workflow_run --task "rerun failed pipeline in codespace"
```

Artifacts:
- `artifacts/agent_comm/github_lanes/webhook_lane.jsonl`
- `artifacts/agent_comm/github_lanes/cli_lane.jsonl`
- `artifacts/agent_comm/github_lanes/codespaces_lane.jsonl`
- `artifacts/agent_comm/github_lanes/cross_talk.jsonl`

## Recommended Team Pattern
1. Webhook Agent
- Reads webhook lane, extracts event intent, routes required execution.

2. CLI Agent
- Executes git/gh tasks from CLI lane and emits completion packets.

3. Codespaces Agent
- Handles long builds/tests and pushes status back to cross-talk log.

4. Cross-Talk Contract
- Every lane action writes a packet and ack in `cross_talk.jsonl`.

## Guardrails
- Do not expose tokens/secrets in lane payloads.
- Do not auto-merge from webhook lane without CLI lane confirmation.
- Keep `private_restricted` repos out of public automations by policy.
