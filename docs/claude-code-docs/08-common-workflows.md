# Common Workflows

> Source: https://code.claude.com/docs/en/common-workflows

Step-by-step guides for exploring codebases, fixing bugs, refactoring, testing, and other everyday tasks with Claude Code.

## Understand new codebases

```text
give me an overview of this codebase
```
```text
explain the main architecture patterns used here
```
```text
what are the key data models?
```

### Find relevant code

```text
find the files that handle user authentication
```
```text
how do these authentication files work together?
```
```text
trace the login process from front-end to database
```

## Fix bugs efficiently

```text
I'm seeing an error when I run npm test
```
```text
suggest a few ways to fix the @ts-ignore in user.ts
```
```text
update user.ts to add the null check you suggested
```

## Refactor code

```text
find deprecated API usage in our codebase
```
```text
suggest how to refactor utils.js to use modern JavaScript features
```
```text
refactor utils.js to use ES2024 features while maintaining the same behavior
```
```text
run tests for the refactored code
```

## Use specialized subagents

```text
/agents
```

Claude Code automatically delegates tasks to specialized subagents. You can also request them explicitly or create custom ones.

## Use Plan Mode for safe code analysis

Press **Shift+Tab** to cycle into Plan Mode, or start with:

```bash
claude --permission-mode plan
```

Example planning workflow:
```text
I need to refactor our authentication system to use OAuth2. Create a detailed migration plan.
```

Press `Ctrl+G` to open the plan in your text editor.

## Work with tests

```text
find functions in NotificationsService.swift that are not covered by tests
```
```text
add tests for the notification service
```
```text
add test cases for edge conditions in the notification service
```
```text
run the new tests and fix any failures
```

## Create pull requests

```text
summarize the changes I've made to the authentication module
```
```text
create a pr
```

When you create a PR using `gh pr create`, the session is automatically linked to that PR.

## Handle documentation

```text
find functions without proper JSDoc comments in the auth module
```
```text
add JSDoc comments to the undocumented functions in auth.js
```

## Work with images

Methods to add images:
1. Drag and drop into the Claude Code window
2. Copy and paste with ctrl+v
3. Provide an image path

## Reference files and directories

Use `@` to quickly include files or directories:
```text
Explain the logic in @src/utils/auth.js
```
```text
What's the structure of @src/components?
```

## Use extended thinking (thinking mode)

Extended thinking is enabled by default. Toggle with `Option+T` (macOS) or `Alt+T` (Windows/Linux).

Include "ultrathink" in your prompt for one-off deep reasoning.

| Scope | How to configure |
| --- | --- |
| **Effort level** | Run `/effort`, adjust in `/model`, or set `CLAUDE_CODE_EFFORT_LEVEL` |
| **`ultrathink` keyword** | Include "ultrathink" anywhere in your prompt |
| **Toggle shortcut** | `Option+T` (macOS) or `Alt+T` (Windows/Linux) |
| **Global default** | Use `/config` to toggle thinking mode |
| **Limit token budget** | Set `MAX_THINKING_TOKENS` environment variable |

## Resume previous conversations

- `claude --continue` continues the most recent conversation
- `claude --resume` opens a conversation picker
- `claude --from-pr 123` resumes sessions linked to a PR

### Name your sessions

```bash
claude -n auth-refactor
```

Or use `/rename` during a session.

### Session picker shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Up/Down` | Navigate between sessions |
| `Right/Left` | Expand or collapse grouped sessions |
| `Enter` | Select and resume |
| `P` | Preview the session |
| `R` | Rename the session |
| `/` | Search to filter |
| `A` | Toggle between current directory and all projects |
| `B` | Filter to current git branch |
| `Esc` | Exit picker or search mode |

## Run parallel Claude Code sessions with Git worktrees

```bash
claude --worktree feature-auth
claude --worktree bugfix-123
claude --worktree  # auto-generates a name
```

Worktrees are created at `<repo>/.claude/worktrees/<name>`.

### Worktree cleanup

- **No changes**: worktree and branch removed automatically
- **Changes exist**: Claude prompts to keep or remove

Add `.worktreeinclude` to copy gitignored files (like `.env`) to worktrees.

## Get notified when Claude needs your attention

Set up `Notification` hooks in `~/.claude/settings.json` for your platform.

## Use Claude as a unix-style utility

```bash
# Add to build scripts
"lint:claude": "claude -p 'you are a linter. look at changes vs. main and report issues.'"

# Pipe data
cat build-error.txt | claude -p 'explain the root cause' > output.txt

# Output formats
claude -p 'analyze this code' --output-format json
claude -p 'parse this log' --output-format stream-json
```

## Run Claude on a schedule

| Option | Where it runs | Best for |
| :--- | :--- | :--- |
| Cloud scheduled tasks | Anthropic infrastructure | Tasks when computer is off |
| Desktop scheduled tasks | Your machine | Local file access |
| GitHub Actions | CI pipeline | Repo events |
| `/loop` | Current CLI session | Quick polling |

## Ask Claude about its capabilities

```text
can Claude Code create pull requests?
how does Claude Code handle permissions?
what skills are available?
how do I use MCP with Claude Code?
```
