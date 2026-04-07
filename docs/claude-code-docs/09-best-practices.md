# Best Practices for Claude Code

> Source: https://code.claude.com/docs/en/best-practices

Tips and patterns for getting the most out of Claude Code.

## Core principle: Context management

Most best practices stem from one constraint: Claude's context window fills up fast, and performance degrades as it fills.

## Give Claude a way to verify its work

Include tests, screenshots, or expected outputs so Claude can check itself. This is the single highest-leverage thing you can do.

| Strategy | Before | After |
| --- | --- | --- |
| **Provide verification criteria** | "implement a function that validates email addresses" | "write a validateEmail function. test cases: user@example.com is true, invalid is false, user@.com is false. run the tests after implementing" |
| **Verify UI changes visually** | "make the dashboard look better" | "[paste screenshot] implement this design. take a screenshot and compare" |
| **Address root causes** | "the build is failing" | "the build fails with this error: [paste]. fix it and verify the build succeeds" |

## Explore first, then plan, then code

1. **Explore**: Enter Plan Mode. Claude reads files without making changes.
2. **Plan**: Ask Claude to create a detailed implementation plan.
3. **Implement**: Switch to Normal Mode and let Claude code.
4. **Commit**: Ask Claude to commit and create a PR.

> Skip planning for tasks where the scope is clear and the fix is small.

## Provide specific context in your prompts

| Strategy | Before | After |
| --- | --- | --- |
| **Scope the task** | "add tests for foo.py" | "write a test for foo.py covering the edge case where the user is logged out" |
| **Point to sources** | "why does ExecutionFactory have a weird api?" | "look through ExecutionFactory's git history and summarize how its api came to be" |
| **Reference patterns** | "add a calendar widget" | "look at how existing widgets are implemented. HotDogWidget.php is a good example. follow the pattern" |
| **Describe the symptom** | "fix the login bug" | "users report login fails after session timeout. check src/auth/, especially token refresh" |

### Provide rich content

- Reference files with `@` instead of describing where code lives
- Paste images directly (copy/paste or drag and drop)
- Give URLs for documentation
- Pipe in data with `cat error.log | claude`
- Let Claude fetch what it needs

## Configure your environment

### Write an effective CLAUDE.md

Run `/init` to generate a starter file.

| Include | Exclude |
| --- | --- |
| Bash commands Claude can't guess | Anything Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions |
| Testing instructions | Detailed API documentation |
| Repository etiquette | Information that changes frequently |
| Architectural decisions | File-by-file descriptions |
| Developer environment quirks | Self-evident practices |
| Common gotchas | Long explanations or tutorials |

### Configure permissions

- **Auto mode**: classifier handles approvals
- **Permission allowlists**: permit specific safe tools
- **Sandboxing**: OS-level isolation

### Use CLI tools

Tell Claude to use `gh`, `aws`, `gcloud`, `sentry-cli` etc.

### Connect MCP servers

Run `claude mcp add` to connect external tools.

### Set up hooks

Use hooks for actions that must happen every time with zero exceptions.

### Create skills

Create `SKILL.md` files in `.claude/skills/` for domain knowledge and reusable workflows.

### Create custom subagents

Define specialized assistants in `.claude/agents/`.

### Install plugins

Run `/plugin` to browse the marketplace.

## Communicate effectively

### Ask codebase questions

Ask Claude the same questions you'd ask another engineer.

### Let Claude interview you

```text
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.
Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs.
Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

## Manage your session

### Course-correct early and often

- **`Esc`**: stop Claude mid-action
- **`Esc + Esc` or `/rewind`**: restore previous state
- **`/clear`**: reset context between unrelated tasks

### Manage context aggressively

- Use `/clear` frequently between tasks
- Run `/compact <instructions>` for controlled compaction
- Use `/btw` for quick questions that don't enter context
- Use `Esc + Esc` > Summarize from here for partial compaction

### Use subagents for investigation

```text
Use subagents to investigate how our authentication system handles token refresh
```

### Rewind with checkpoints

Double-tap Escape or run `/rewind`. Checkpoints persist across sessions.

### Resume conversations

```bash
claude --continue    # Resume most recent
claude --resume      # Select from recent
```

## Automate and scale

### Run non-interactive mode

```bash
claude -p "Explain what this project does"
claude -p "List all API endpoints" --output-format json
```

### Run multiple Claude sessions

- Desktop app for visual management
- Claude Code on the web for cloud VMs
- Agent teams for automated coordination

### Fan out across files

```bash
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue." --allowedTools "Edit,Bash(git commit *)"
done
```

## Avoid common failure patterns

- **Kitchen sink session**: `/clear` between unrelated tasks
- **Correcting over and over**: After two fails, `/clear` and write a better prompt
- **Over-specified CLAUDE.md**: Prune ruthlessly
- **Trust-then-verify gap**: Always provide verification
- **Infinite exploration**: Scope narrowly or use subagents
