# Explore the context window

> Source: https://code.claude.com/docs/en/context-window

> An interactive simulation of how Claude Code's context window fills during a session. See what loads automatically, what each file read costs, and when rules and hooks fire.

This page is an interactive simulation on the web. Below is the reference content showing each event in a typical session and its impact on context.

## Session phases

### Phase 1: Startup (automatic)

These items load automatically before you type anything.

| Item | Tokens | Visibility | Description |
|------|--------|------------|-------------|
| System prompt | 4,200 | Hidden from you | Core instructions for behavior, tool use, and response formatting. Always loaded first. You never see it. |
| Auto memory (MEMORY.md) | 680 | Hidden from you | Claude |
| Environment info | 280 | Hidden from you | Working directory, platform, shell, OS version, and whether this is a git repo. Git branch, status, and recent commits l... |
| MCP tools (deferred) | 120 | Hidden from you | MCP tool names listed so Claude knows what is available. By default, full schemas stay deferred and Claude loads specifi... |
| Skill descriptions | 450 | Hidden from you | One-line descriptions of available skills so Claude knows what it can invoke. Full skill content loads only when Claude ... |
| ~/.claude/CLAUDE.md | 320 | Hidden from you | Your global preferences. Applies to every project. Loaded alongside project instructions at the start of every conversat... |
| Project CLAUDE.md | 1,800 | Hidden from you | Project conventions, build commands, architecture notes. The most important file you can create. Lives in your project r... |
| Rule: api-conventions.md | 380 | Brief notice | This rule in `.claude/rules/` has a `paths:` pattern matching `src/api/**`. It loaded automatically when Claude read a f... |
| Rule: testing.md | 290 | Brief notice | Another path-scoped rule, this one matching `*.test.ts` files. Triggered when Claude read auth.test.ts. Shown as a one-l... |

### Phase 2: Your task

What happens when you give Claude a task.

**Your prompt** (45 tokens) — *visible*

**Read src/api/auth.ts** (2,400 tokens) — *brief notice*
: Main auth file. You see 

> **Tip**: File reads dominate context usage. Be specific in prompts ("fix the bug in auth.ts") so Claude reads fewer files. For research-heavy tasks, use a subagent.

**Read src/lib/tokens.ts** (1,100 tokens) — *brief notice*
: Following imports to the token module. Shown as a one-liner in your terminal.

**Read middleware.ts** (1,800 tokens) — *brief notice*
: Tracing the auth flow deeper.

**Read auth.test.ts** (1,600 tokens) — *brief notice*
: Checking existing tests for expected behavior.

**grep "refreshToken"** (600 tokens) — *brief notice*
: Search results across the codebase. You see the command ran, not the full output.

**Edit auth.ts** (400 tokens) — *visible*
: Fixes the token rotation order. The diff appears in your terminal.

**Hook: prettier** (120 tokens) — *hidden*
: A PostToolUse hook in `settings.json` runs prettier after every file edit and reports back via `hookSpecificOutput.additionalContext`. That field enters Claude\

> **Tip**: Output JSON with `additionalContext` to send info to Claude. For PostToolUse hooks, exit code 2 surfaces stderr as an error but cannot block since the tool already ran. Keep output concise since it enters context without truncation.

**Edit auth.test.ts** (600 tokens) — *visible*
: Adds a regression test for the fix. The diff appears in your terminal.

**Hook: prettier** (100 tokens) — *hidden*
: The same hook fires again for the test file. Every matching tool event triggers it.

**npm test output** (1,200 tokens) — *brief notice*
: Runs the test suite. You see 

**Summary** (400 tokens) — *visible*

**Your follow-up** (40 tokens) — *visible*

> **Tip**: Follow-ups add to the same context. Delegating research to a subagent keeps large file reads out of your main window.

**Spawn research subagent** (80 tokens) — *brief notice*
: Claude delegates the research to a subagent with a fresh, separate context window. It loads CLAUDE.md and the same MCP and skill setup, but starts without your conversation history or the main session

**Subagent returns summary** (420 tokens) — *brief notice*
: Only the subagent

**!git status** (180 tokens) — *visible*
: You ran a shell command with the ! prefix to see which files Claude modified. The command and its output both enter context as part of your message. Useful for grounding Claude in command output without Claude running it.

**/commit-push** (620 tokens) — *brief notice*
: You invoked a skill that has `disable-model-invocation: true`. Its description was not in the skill index at startup, so it cost zero context until this moment. Now the full skill content loads and Claude follows its instructions to stage, commit, and push your changes.

> **Tip**: Set `disable-model-invocation: true` on skills with side effects like committing, deploying, or sending messages. They stay out of context entirely until you need them.

### Phase 3: Subagent delegation

When Claude delegates to a subagent, the subagent gets its own context window.

**System prompt** (900 sub-tokens)
: The subagent gets its own system prompt, shorter than the main session

**Project CLAUDE.md (own copy)** (1,800 sub-tokens)
: The subagent loads CLAUDE.md too. Same file, same content, but it counts against the subagent

**MCP tools + skills** (970 sub-tokens)
: The subagent has access to the same MCP servers and skills. It gets most of the parent

**Task prompt from main** (120 sub-tokens)
: Instead of a user prompt, the subagent receives the task Claude wrote for it: 

**Read session.ts** (2,200 sub-tokens)
: Now the subagent does its work. This file read fills the subagent

**Read timeouts.ts** (800 sub-tokens)
: Another file read in the subagent

**Read config/*.ts** (3,100 sub-tokens)
: The subagent can read as many files as it needs. None of this touches your main context.
