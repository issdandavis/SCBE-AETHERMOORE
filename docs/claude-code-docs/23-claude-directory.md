# Explore the .claude directory

> Source: https://code.claude.com/docs/en/claude-directory

> Where Claude Code reads CLAUDE.md, settings.json, hooks, skills, commands, subagents, rules, and auto memory. Explore the .claude directory in your project and ~/.claude in your home directory.

This page is an interactive explorer on the web. Below is the reference content for each file and directory in the .claude structure.

## Project directory: your-project/

#### CLAUDE.md `committed`

*Project instructions Claude reads every session*

**When**: Loaded into context at the start of every session

Project-specific instructions that shape how Claude works in this repository. Put your conventions, common commands, and architectural context here so Claude operates with the same assumptions your team does.


```
# Project conventions

## Commands
- Build: \
```

#### .mcp.json `committed`

*Project-scoped MCP servers, shared with your team*


```
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "\${GITHUB_TOKEN}"
      }
    }
  }
}
```

#### .worktreeinclude `committed`

*Gitignored files to copy into new worktrees*


```
# Local environment
.env
.env.local

# API credentials
config/secrets.json
```

### .claude/

*Project-level configuration, rules, and extensions*

Everything Claude Code reads that is specific to this project. If you use git, commit most files here so your team shares them; a few, like settings.local.json, are automatically gitignored. Each file badge shows which.

#### settings.json `committed`

*Permissions, hooks, and configuration*

Settings that Claude Code applies directly. Permissions control which commands and tools Claude can use; hooks run your scripts at specific points in a session. Unlike CLAUDE.md, which Claude reads as guidance, these are enforced whether Claude follows them or not.


```
{
  "permissions": {
    "allow": [
      "Bash(npm test *)",
      "Bash(npm run *)"
    ],
    "deny": [
      "Bash(rm -rf *)"
    ]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
      }]
    }]
  }
}
```

#### settings.local.json `gitignored`

*Your personal settings overrides for this project*

**When**: Highest of the user-editable settings files; CLI flags and managed settings still take precedence

Personal settings that take precedence over the project defaults. Same JSON format as settings.json, but not committed. Use this when you need different permissions or defaults than the team config.


```
{
  "permissions": {
    "allow": [
      "Bash(docker *)"
    ]
  }
}
```

### rules/

*Topic-scoped instructions, optionally gated by file paths*

#### testing.md `committed`

*Test conventions scoped to test files*


```
---
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Testing Rules

- Use descriptive test names: "should [expected] when [condition]"
- Mock external dependencies, not internal modules
- Clean up side effects in afterEach
```

#### api-design.md `committed`

*API conventions scoped to backend code*


```
---
paths:
  - "src/api/**/*.ts"
---

# API Design Rules

- All endpoints must validate input with Zod schemas
- Return shape: { data: T } | { error: string }
- Rate limit all public endpoints
```

### skills/

*Reusable prompts you or Claude invoke by name*

### security-review/

*A skill bundling SKILL.md with supporting files*

#### SKILL.md `committed`

*Entrypoint: trigger, invocability, instructions*


```
---
description: Reviews code changes for security vulnerabilities, authentication gaps, and injection risks
disable-model-invocation: true
argument-hint: <branch-or-path>
---

## Diff to review

!\
```

#### checklist.md `committed`

*Supporting file bundled with the skill*

**When**: Claude reads it on demand while running the skill


```
# Security Review Checklist

## Input Validation
- [ ] All user input sanitized before DB queries
- [ ] File upload MIME types validated
- [ ] Path traversal prevented on file operations

## Authentication
- [ ] JWT tokens expire after 24 hours
- [ ] API keys stored in environment variables
- [ ] Passwords hashed with bcrypt or argon2
```

### commands/

#### fix-issue.md `committed`


```
---
argument-hint: <issue-number>
---

!\
```

### output-styles/

*Project-scoped output styles, if your team shares any*

**When**: Applied at session start when selected via the outputStyle setting

### agents/

*Specialized subagents with their own context window*

**When**: Runs in its own context window when you or Claude invoke it

Each markdown file defines a subagent with its own system prompt, tool access, and optionally its own model. Subagents run in a fresh context window, keeping the main conversation clean. Useful for parallel work or isolated tasks.

#### code-reviewer.md `committed`

*Subagent for isolated code review*

**When**: Claude spawns it for review tasks, or you @-mention it from the autocomplete


```
---
name: code-reviewer
description: Reviews code for correctness, security, and maintainability
tools: Read, Grep, Glob
---

You are a senior code reviewer. Review for:

1. Correctness: logic errors, edge cases, null handling
2. Security: injection, auth bypass, data exposure
3. Maintainability: naming, complexity, duplication

Every finding must include a concrete fix.
```

### agent-memory/ `committed`

*Subagent persistent memory, separate from your main session auto memory*

**When**: First 200 lines (capped at 25KB) of MEMORY.md loaded into the subagent system prompt when it runs

### <agent-name>/

#### MEMORY.md `committed`

*The subagent writes and maintains this file automatically*

**When**: Loaded into the subagent system prompt when the subagent starts


```
# code-reviewer memory

## Patterns seen
- Project uses custom Result<T, E> type, not exceptions
- Auth middleware expects Bearer token in Authorization header
- Tests use factory functions in test/factories/

## Recurring issues
- Missing null checks on API responses (src/api/*)
- Unhandled promise rejections in background jobs
```

#### .claude.json `local`

*App state and UI preferences*


```
{
  "editorMode": "vim",
  "showTurnDuration": false,
  "mcpServers": {
    "my-tools": {
      "command": "npx",
      "args": ["-y", "@example/mcp-server"]
    }
  }
}
```

### .claude/

*Your personal configuration across all projects*

The global counterpart to your project .claude/ directory. Files here apply to every project you work in and are never committed to any repository.

#### CLAUDE.md `local`

*Personal preferences across every project*

**When**: Loaded at the start of every session, in every project

Your global instruction file. Loaded alongside the project CLAUDE.md at session start, so both are in context together. When instructions conflict, project-level instructions take priority. Keep this to preferences that apply everywhere: response style, commit format, personal conventions.


```
# Global preferences

- Keep explanations concise
- Use conventional commit format
- Show the terminal command to verify changes
- Prefer composition over inheritance
```

#### settings.json `local`

*Default settings for all projects*

**When**: Your defaults. Project and local settings.json override any keys you also set there


```
{
  "permissions": {
    "allow": [
      "Bash(git log *)",
      "Bash(git diff *)"
    ]
  }
}
```

#### keybindings.json `local`

*Custom keyboard shortcuts*

**When**: Read at session start and hot-reloaded when you edit the file


```
{
  "$schema": "https://www.schemastore.org/claude-code-keybindings.json",
  "$docs": "https://code.claude.com/docs/en/keybindings",
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "ctrl+e": "chat:externalEditor",
        "ctrl+u": null
      }
    }
  ]
}
```

### projects/

**When**: MEMORY.md loaded at session start; topic files read on demand

Auto memory lets Claude accumulate knowledge across sessions without you writing anything. Claude saves notes as it works: build commands, debugging insights, architecture notes. Each project gets its own memory directory keyed by the repository path.

### <project>/memory/

#### MEMORY.md `local`

*Claude writes and maintains this file automatically*

**When**: First 200 lines (capped at 25KB) loaded at session start

Claude creates and updates this file as it works; you do not write it yourself. It acts as an index that Claude reads at the start of every session, pointing to topic files for detail. You can edit or delete it, but Claude will keep updating it.


```
# Memory Index

## Project
- [build-and-test.md](build-and-test.md): npm run build (~45s), Vitest, dev server on 3001
- [architecture.md](architecture.md): API client singleton, refresh-token auth

## Reference
- [debugging.md](debugging.md): auth token rotation and DB connection troubleshooting
```

#### debugging.md `local`

*Topic notes Claude writes when MEMORY.md gets long*

**When**: Claude reads this when a related task comes up

An example of a topic file Claude creates when MEMORY.md grows too long. Claude picks the filename based on what it splits out: debugging.md, architecture.md, build-commands.md, or similar. You never create these yourself. Claude reads a topic file back only when the current task relates to it.


```
---
name: Debugging patterns
description: Auth token rotation and database connection troubleshooting for this project
type: reference
---

## Auth Token Issues
- Refresh token rotation: old token invalidated immediately
- If 401 after refresh: check clock skew between client and server

## Database Connection Drops
- Connection pool: max 10 in dev, 50 in prod
- Always check \
```

### rules/

*User-level rules that apply to every project*

Same as project .claude/rules/ but applies everywhere. Use this for conventions you want across all your work, like personal code style or commit message format.

### skills/

*Personal skills available in every project*

Skills you built for yourself that work everywhere. Same structure as project skills: each is a folder with SKILL.md, scoped to your user account instead of a single project.

### commands/

*Personal single-file commands available in every project*

Same as project commands/ but scoped to your user account. Each markdown file becomes a command available everywhere.

### output-styles/

*Custom system-prompt sections that adjust how Claude works*

**When**: Applied at session start when selected via the outputStyle setting

#### teaching.md `local`

*Example style that adds explanations and leaves small changes for you*


```
---
description: Explains reasoning and asks you to implement small pieces
keep-coding-instructions: true
---

After completing each task, add a brief "Why this approach" note
explaining the key design decision.

When a change is under 10 lines, ask the user to implement it
themselves by leaving a TODO(human) marker instead of writing it.
```

### agents/

*Personal subagents available in every project*

**When**: Claude delegates or you @-mention in any project

Subagents defined here are available across all your projects. Same format as project agents.

### agent-memory/

**When**: Loaded into the subagent system prompt when the subagent starts
