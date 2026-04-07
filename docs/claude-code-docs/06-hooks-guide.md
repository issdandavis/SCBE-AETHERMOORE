# Automate Workflows with Hooks

> Source: https://code.claude.com/docs/en/hooks-guide

Hooks are user-defined shell commands that execute at specific points in Claude Code's lifecycle. They provide deterministic control over Claude Code's behavior, ensuring certain actions always happen rather than relying on the LLM to choose to run them.

## Set up your first hook

Add a `hooks` block to a settings file. Example desktop notification hook for macOS:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

Verify with `/hooks`. Test by triggering a permission prompt.

## What you can automate

### Get notified when Claude needs input

**macOS:**
```json
"command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
```

**Linux:**
```json
"command": "notify-send 'Claude Code' 'Claude Code needs your attention'"
```

**Windows (PowerShell):**
```json
"command": "powershell.exe -Command \"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('Claude Code needs your attention', 'Claude Code')\""
```

### Auto-format code after edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

### Block edits to protected files

Create `.claude/hooks/protect-files.sh`:

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

Register as a PreToolUse hook with matcher `Edit|Write`.

### Re-inject context after compaction

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use Bun, not npm. Run bun test before committing.'"
          }
        ]
      }
    ]
  }
}
```

### Audit configuration changes

```json
{
  "hooks": {
    "ConfigChange": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jq -c '{timestamp: now | todate, source: .source, file: .file_path}' >> ~/claude-config-audit.log"
          }
        ]
      }
    ]
  }
}
```

### Reload environment when directory or files change

```json
{
  "hooks": {
    "CwdChanged": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "direnv export bash >> \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ]
  }
}
```

### Auto-approve specific permission prompts

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"PermissionRequest\", \"decision\": {\"behavior\": \"allow\"}}}'"
          }
        ]
      }
    ]
  }
}
```

## How hooks work

### Hook events

| Event                | When it fires                                                          |
| :------------------- | :--------------------------------------------------------------------- |
| `SessionStart`       | When a session begins or resumes                                       |
| `UserPromptSubmit`   | When you submit a prompt                                               |
| `PreToolUse`         | Before a tool call executes. Can block it                              |
| `PermissionRequest`  | When a permission dialog appears                                       |
| `PermissionDenied`   | When a tool call is denied by auto mode                                |
| `PostToolUse`        | After a tool call succeeds                                             |
| `PostToolUseFailure` | After a tool call fails                                                |
| `Notification`       | When Claude Code sends a notification                                  |
| `SubagentStart`      | When a subagent is spawned                                             |
| `SubagentStop`       | When a subagent finishes                                               |
| `TaskCreated`        | When a task is created                                                 |
| `TaskCompleted`      | When a task is completed                                               |
| `Stop`               | When Claude finishes responding                                        |
| `StopFailure`        | When the turn ends due to an API error                                 |
| `TeammateIdle`       | When an agent team teammate is about to go idle                        |
| `InstructionsLoaded` | When a CLAUDE.md or rules file is loaded                               |
| `ConfigChange`       | When a configuration file changes                                      |
| `CwdChanged`         | When the working directory changes                                     |
| `FileChanged`        | When a watched file changes on disk                                    |
| `WorktreeCreate`     | When a worktree is being created                                       |
| `WorktreeRemove`     | When a worktree is being removed                                       |
| `PreCompact`         | Before context compaction                                              |
| `PostCompact`        | After context compaction completes                                     |
| `Elicitation`        | When an MCP server requests user input                                 |
| `ElicitationResult`  | After a user responds to an MCP elicitation                            |
| `SessionEnd`         | When a session terminates                                              |

### Hook input and output

Hooks communicate through stdin, stdout, stderr, and exit codes.

**Exit codes:**
- **Exit 0**: action proceeds
- **Exit 2**: action is blocked (stderr becomes Claude's feedback)
- **Any other**: action proceeds, stderr logged

### Hook types

- `"type": "command"`: runs a shell command
- `"type": "http"`: POST event data to a URL
- `"type": "prompt"`: single-turn LLM evaluation
- `"type": "agent"`: multi-turn verification with tool access

### Filter hooks with matchers

Matchers use regex patterns to filter which events trigger the hook:

| Event type | What matcher filters | Example values |
| :--- | :--- | :--- |
| PreToolUse, PostToolUse, etc. | tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| SessionStart | how session started | `startup`, `resume`, `clear`, `compact` |
| Notification | notification type | `permission_prompt`, `idle_prompt` |
| ConfigChange | configuration source | `user_settings`, `project_settings` |

### The `if` field

Filter by tool name AND arguments:

```json
{
  "type": "command",
  "if": "Bash(git *)",
  "command": ".claude/hooks/check-git-policy.sh"
}
```

### Configure hook location

| Location | Scope | Shareable |
| :--- | :--- | :--- |
| `~/.claude/settings.json` | All your projects | No |
| `.claude/settings.json` | Single project | Yes |
| `.claude/settings.local.json` | Single project | No |
| Managed policy settings | Organization-wide | Yes |
| Plugin `hooks/hooks.json` | When plugin is enabled | Yes |
| Skill or agent frontmatter | While active | Yes |

## Prompt-based hooks

Use `type: "prompt"` for decisions requiring judgment:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains\"}."
          }
        ]
      }
    ]
  }
}
```

## Agent-based hooks

Use `type: "agent"` when verification requires inspecting files or running commands:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite and check the results.",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

## HTTP hooks

POST event data to an HTTP endpoint:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "http",
            "url": "http://localhost:8080/hooks/tool-use",
            "headers": {
              "Authorization": "Bearer $MY_TOKEN"
            },
            "allowedEnvVars": ["MY_TOKEN"]
          }
        ]
      }
    ]
  }
}
```

## Limitations

- Command hooks communicate through stdout, stderr, and exit codes only
- Hook timeout is 10 minutes by default
- PostToolUse hooks cannot undo actions
- PermissionRequest hooks don't fire in non-interactive mode
- Stop hooks fire whenever Claude finishes responding, not only at task completion

## Troubleshooting

- **Hook not firing**: Check `/hooks`, verify matcher, check event type
- **Hook error**: Test script manually with piped JSON
- **Stop hook runs forever**: Check `stop_hook_active` field and exit early if true
- **JSON validation failed**: Wrap shell profile echo statements in interactive-only checks
- **Debug**: Use `Ctrl+O` for verbose mode or `claude --debug`
