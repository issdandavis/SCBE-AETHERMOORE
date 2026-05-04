# Agent Hook Parity Pack

This parity pack maps the Cursor hook controls in `.cursor/hooks.json` to
equivalent policy intents for Claude and GPT style agent runtimes.

## Purpose

- Keep the same guardrails across agent surfaces.
- Preserve safety posture even when exact event contracts differ.
- Provide template configs that teams can adapt without losing policy intent.

## Core policy intents

- Destructive command safety gate.
- Network and exfil awareness for outbound uploads and remote transfer.
- Secret leak guard for prompts and tool arguments.
- High-risk MCP/tool confirmation.
- Tool, shell, MCP, file-edit, subagent, and session audit logging.
- Post-edit reminder context where runtime supports context injection.

## Event mapping table

| Policy intent | Cursor event | Claude equivalent intent | GPT equivalent intent |
| --- | --- | --- | --- |
| Session lifecycle audit | `sessionStart`, `sessionEnd` | Session init/teardown interceptors | Agent start/end middleware |
| Shell precheck | `beforeShellExecution` | Pre-command guard policy | Pre-shell tool validator |
| Shell post summary | `afterShellExecution` | Command completion logger | Post-shell middleware logger |
| MCP precheck | `beforeMCPExecution` | MCP request policy gate | MCP request validator |
| MCP post summary | `afterMCPExecution` | MCP completion logger | MCP post-call logger |
| Tool precheck | `preToolUse` | Tool input policy filter | Tool-call preflight |
| Tool audit success | `postToolUse` | Tool success logger | Tool result middleware |
| Tool audit failure | `postToolUseFailure` | Tool error logger | Tool failure middleware |
| Prompt secret guard | `beforeSubmitPrompt` | Prompt pre-send policy | Message pre-send validator |
| Edit postcheck hint | `afterFileEdit` | File-write posthook + note | File edit observer + reminder |
| Subagent guardrails | `subagentStart`, `subagentStop` | Child-agent launch/stop gate | Child-run orchestration guard |

## Runtime differences and limitations

- Cursor supports hook-level `ask`/`deny` permissions directly.
- Claude and GPT runtimes often express this as middleware return states or
  policy engine decisions.
- `additional_context` support is runtime-specific. Treat it as best-effort:
  apply it only where platform allows augmenting user-visible context.
- Payload shapes vary widely. Match by intent, not strict field names.

## Fail-open vs fail-closed guidance

- Default recommendation: fail-open for infrastructure resilience.
- Explicitly dangerous checks should still ask or deny when matched.
- Move to fail-closed only after hook reliability is validated in your runtime.

## Quick adoption flow

1. Start from `config/agent-hooks/claude-hooks.example.json` and
   `config/agent-hooks/gpt-hooks.example.json`.
2. Map your runtime's event keys to the same intents.
3. Verify `ask` behavior in a non-production environment.
4. Keep a shared regex policy source to avoid drift between agents.
