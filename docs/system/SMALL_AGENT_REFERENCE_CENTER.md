# Small Agent Reference Center

Build a compact command center for smaller task agents.

## Build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\reference_center_build.ps1 `
  -Agents "agent.mini.research,agent.mini.writer,agent.mini.qa" `
  -Tasks "Summarize latest research artifacts,Draft product copy from findings,Validate links and claims"
```

## Output

- `artifacts/agent_reference_center/index.json`
- `artifacts/agent_reference_center/small_agents_overview.md`
- `artifacts/agent_reference_center/cards/*.md`
- `artifacts/agent_reference_center/task_queue.jsonl`

## How It Works

1. Creates lane cards with codename + run loop.
2. Pulls recent cross-talk packet samples for context.
3. Builds initial task queue for small task agents.
4. Keeps references anchored to SCBE runbooks and handoff docs.
