# Workflow Template Map

Use this map to synthesize end-to-end internet workflows.

## Local SCBE Templates (Primary)

- `workflows/scbe_ai_kernel/manager_agent_prompt.md`
  - Governance-first manager contract for multi-agent browsing tasks.
- `scripts/web_research_training_pipeline.py`
  - Baseline internet ingest and gating pipeline.
- `docs/WEB_RESEARCH_TRAINING_PIPELINE.md`
  - Baseline run modes, outputs, and flags for web research ingestion.
- `workflows/n8n/scbe_n8n_bridge.py`
  - n8n integration layer and API surface for task submission and status polling.
- `workflows/n8n/scbe_web_agent_tasks.workflow.json`
  - Orchestrated n8n task flow with polling loop and webhook response.
- `scripts/workflow_audit.py`
  - CI workflow governance scanning and issue severity reporting.
- `.github/workflows/workflow-audit.yml`
  - Scheduled CI governance enforcement and issue creation pattern.
- `training/cloud_kernel_pipeline.json`
  - Threshold baseline used by post-run variable tuning.
- `src/ai_orchestration/autonomous_workflows.py`
  - Queue, handoff, and retry/escalation architecture for autonomous pipelines.

## GitHub Templates (Fallback + Cross-Pattern)

Repository: `https://github.com/issdandavis/AI-Workflow-Architect`

- `README.md`
  - End-to-end deployment and operations framing.
- `docs/PROJECT_DOCUMENTATION.md`
  - Full architecture, API, and operational decomposition.
- `server/services/orchestrator.ts`
  - Queue concurrency, approval gates, retry/fallback behavior.
- `.github/workflows/deploy.yml`
  - Deployment workflow with guard checks and conditional execution.

## Discovery Commands

```bash
# Local template scan
rg --files --hidden -g "*workflow*" -g "*pipeline*" -g "*architect*" C:/Users/issda/SCBE-AETHERMOORE

# Remote template scan (GitHub)
gh api repos/issdandavis/AI-Workflow-Architect/git/trees/main?recursive=1 --jq '.tree[] | select(.type=="blob") | .path'
```

## Selection Rule

1. Prefer local SCBE templates when an equivalent exists.
2. Use GitHub templates only to fill gaps (approval gating, deploy wiring, adapter patterns).
3. Keep a deterministic map of selected files in the generated profile.

