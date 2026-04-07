# Extend Claude with Skills

> Source: https://code.claude.com/docs/en/skills

Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with `/skill-name`.

> Custom commands have been merged into skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way.

## Bundled skills

| Skill                       | Purpose                                                                                              |
| :-------------------------- | :--------------------------------------------------------------------------------------------------- |
| `/batch <instruction>`      | Orchestrate large-scale changes across a codebase in parallel using git worktrees                    |
| `/claude-api`               | Load Claude API reference material for your project's language                                        |
| `/debug [description]`      | Enable debug logging and troubleshoot issues                                                          |
| `/loop [interval] <prompt>` | Run a prompt repeatedly on an interval                                                                |
| `/simplify [focus]`         | Review recently changed files for code reuse, quality, and efficiency issues                          |

## Getting started

### Create your first skill

Create `~/.claude/skills/explain-code/SKILL.md`:

```yaml
---
name: explain-code
description: Explains code with visual diagrams and analogies
---

When explaining code, always include:
1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show the flow
3. **Walk through the code**: Explain step-by-step
4. **Highlight a gotcha**: What's a common mistake?
```

### Where skills live

| Location   | Path                                                | Applies to                     |
| :--------- | :-------------------------------------------------- | :----------------------------- |
| Enterprise | See managed settings                                | All users in your organization |
| Personal   | `~/.claude/skills/<skill-name>/SKILL.md`            | All your projects              |
| Project    | `.claude/skills/<skill-name>/SKILL.md`              | This project only              |
| Plugin     | `<plugin>/skills/<skill-name>/SKILL.md`             | Where plugin is enabled        |

Each skill is a directory with `SKILL.md` as the entrypoint:

```text
my-skill/
├── SKILL.md           # Main instructions (required)
├── template.md        # Template for Claude to fill in
├── examples/
│   └── sample.md      # Example output
└── scripts/
    └── validate.sh    # Script Claude can execute
```

## Configure skills

### Frontmatter reference

| Field                      | Required    | Description                                                          |
| :------------------------- | :---------- | :------------------------------------------------------------------- |
| `name`                     | No          | Display name for the skill                                           |
| `description`              | Recommended | What the skill does and when to use it                               |
| `argument-hint`            | No          | Hint for expected arguments                                          |
| `disable-model-invocation` | No          | Set `true` to prevent automatic loading                              |
| `user-invocable`           | No          | Set `false` to hide from `/` menu                                    |
| `allowed-tools`            | No          | Tools Claude can use without asking permission                       |
| `model`                    | No          | Model to use when active                                             |
| `effort`                   | No          | Effort level when active                                             |
| `context`                  | No          | Set to `fork` to run in a forked subagent context                    |
| `agent`                    | No          | Which subagent type to use with `context: fork`                      |
| `hooks`                    | No          | Hooks scoped to this skill's lifecycle                               |
| `paths`                    | No          | Glob patterns that limit when this skill is activated                |
| `shell`                    | No          | Shell for inline commands: `bash` (default) or `powershell`          |

### String substitutions

| Variable               | Description                                          |
| :--------------------- | :--------------------------------------------------- |
| `$ARGUMENTS`           | All arguments passed when invoking the skill         |
| `$ARGUMENTS[N]`        | Specific argument by 0-based index                   |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`                        |
| `${CLAUDE_SESSION_ID}` | The current session ID                               |
| `${CLAUDE_SKILL_DIR}`  | Directory containing the skill's SKILL.md file       |

### Control who invokes a skill

| Frontmatter                      | You can invoke | Claude can invoke |
| :------------------------------- | :------------- | :---------------- |
| (default)                        | Yes            | Yes               |
| `disable-model-invocation: true` | Yes            | No                |
| `user-invocable: false`          | No             | Yes               |

### Inject dynamic context

The `` !`<command>` `` syntax runs shell commands before the skill content is sent to Claude:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

### Run skills in a subagent

Add `context: fork` to run in isolation:

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

### Restrict Claude's skill access

```text
# In deny rules:
Skill(deploy *)

# In allow rules:
Skill(commit)
Skill(review-pr *)
```

## Share skills

- **Project skills**: Commit `.claude/skills/` to version control
- **Plugins**: Create a `skills/` directory in your plugin
- **Managed**: Deploy organization-wide through managed settings
