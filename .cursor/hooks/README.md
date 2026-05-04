# Cursor Hook Framework

This directory contains a practical, fail-open-by-default hook framework for
Cursor project events.

## Design goals

- Reduce accidental destructive actions.
- Surface risky network or secret-leak patterns early.
- Add lightweight audit trails for shell, MCP, tools, edits, and subagents.
- Avoid brittle assumptions about payload shape.

## Hook map

- `sessionStart` -> `session_start.py`
- `sessionEnd` -> `session_end.py`
- `beforeShellExecution` -> `shell_guard.py`
- `afterShellExecution` -> `after_shell_execution.py`
- `beforeMCPExecution` -> `before_mcp_execution.py`
- `afterMCPExecution` -> `after_mcp_execution.py`
- `preToolUse` -> `pre_tool_use.py`
- `postToolUse` -> `post_tool_use.py`
- `postToolUseFailure` -> `post_tool_use_failure.py`
- `beforeSubmitPrompt` -> `before_submit_prompt.py`
- `afterFileEdit` -> `after_file_edit.py`
- `subagentStart` -> `subagent_start.py`
- `subagentStop` -> `subagent_stop.py`

## Script purposes

- `shell_guard.py`
  - Asks on destructive shell patterns.
  - Asks on potential network exfil commands.
  - Denies clearly dangerous host-impact commands (`format`, `shutdown`).
- `before_mcp_execution.py`
  - Asks for confirmation when MCP tool names look high-risk.
  - Asks when payload text appears to contain secrets.
- `pre_tool_use.py`
  - Secret-leak heuristic for tool input.
  - Confirmation on high-impact tool names.
- `post_tool_use.py` and `post_tool_use_failure.py`
  - Append tool call audit records (`success` and `failure` paths).
- `after_shell_execution.py` and `after_mcp_execution.py`
  - Write post-run summaries with command/tool and status hints.
- `after_file_edit.py`
  - Logs file edit summary.
  - Returns `additional_context` reminder text where event support exists.
- `subagent_start.py`
  - Asks on high-risk subagent types or broad prompts.
- `subagent_stop.py`
  - Logs subagent completion metadata.
- `session_start.py` and `session_end.py`
  - Session lifecycle audit envelope.

## Shared modules

- `_common.py`
  - Payload parsing and extraction helpers.
  - Hook response builders (`allow`, `ask`, `deny`).
  - JSONL audit writers and timestamp helpers.
- `_policy.py`
  - Reusable regex policy packs for destructive actions, exfil, secrets, MCP
    risk patterns, and broad subagent prompts.

## Audit output

Logs are written under:

- `.cursor/logs/hooks/events.jsonl`
- `.cursor/logs/hooks/summaries.jsonl`

All logs are ASCII-safe JSONL for easy grep/jq usage.

## Tuning and policy updates

- Add or remove regex rules in `_policy.py`.
- Adjust deny-only markers in `shell_guard.py` if your team wants stricter or
  looser host protection.
- Modify `timeout` and `failClosed` values in `.cursor/hooks.json`.
- If your environment emits different payload keys, update `pick_first(...)`
  candidate paths in each hook script.

## Fail-open vs fail-closed rationale

- Current default is `failClosed: false` to avoid blocking normal workflows
  when hook scripts crash, payloads change, or Python is unavailable.
- Explicit danger checks still use `ask`/`deny` responses inside scripts.
- Recommended fail-closed use is narrow and deliberate (for example, in
  high-assurance environments with managed Python runtime and tested hooks).

## Limitations

- Event payload formats can vary across Cursor versions and tool types.
- `additional_context` is returned by `after_file_edit.py`, but this field is
  only effective in events where Cursor supports injecting extra context.
