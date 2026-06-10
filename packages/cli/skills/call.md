# Agent / Tool Call Skill Card

summary: Invoke Claude, Codex, local models, or SCBE tools through explicit lanes.
triggers: call, invoke, agent, claude, codex, tool

## Worksheet

- Decide which lane owns the task: local shell, `/claude`, `/codex`, agent-bus, or model chat.
- Pass a scoped prompt with the current objective and verification rule.
- Do not claim completion unless the called lane returns evidence.
- Keep the command printable and receipt-backed.
