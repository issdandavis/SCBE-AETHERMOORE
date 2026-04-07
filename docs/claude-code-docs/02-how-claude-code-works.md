# How Claude Code Works

> Source: https://code.claude.com/docs/en/how-claude-code-works

Claude Code is an agentic assistant that runs in your terminal. While it excels at coding, it can help with anything you can do from the command line: writing docs, running builds, searching files, researching topics, and more.

## The agentic loop

When you give Claude a task, it works through three phases: **gather context**, **take action**, and **verify results**. These phases blend together. Claude uses tools throughout, whether searching files to understand your code, editing to make changes, or running tests to check its work.

The loop adapts to what you ask. A question about your codebase might only need context gathering. A bug fix cycles through all three phases repeatedly. A refactor might involve extensive verification. Claude decides what each step requires based on what it learned from the previous step, chaining dozens of actions together and course-correcting along the way.

You're part of this loop too. You can interrupt at any point to steer Claude in a different direction, provide additional context, or ask it to try a different approach. Claude works autonomously but stays responsive to your input.

The agentic loop is powered by two components: models that reason and tools that act. Claude Code serves as the **agentic harness** around Claude: it provides the tools, context management, and execution environment that turn a language model into a capable coding agent.

### Models

Claude Code uses Claude models to understand your code and reason about tasks. Multiple models are available with different tradeoffs. Sonnet handles most coding tasks well. Opus provides stronger reasoning for complex architectural decisions. Switch with `/model` during a session or start with `claude --model <name>`.

### Tools

Tools are what make Claude Code agentic. Without tools, Claude can only respond with text. With tools, Claude can act: read your code, edit files, run commands, search the web, and interact with external services.

| Category              | What Claude can do                                                                |
| --------------------- | --------------------------------------------------------------------------------- |
| **File operations**   | Read files, edit code, create new files, rename and reorganize                    |
| **Search**            | Find files by pattern, search content with regex, explore codebases               |
| **Execution**         | Run shell commands, start servers, run tests, use git                             |
| **Web**               | Search the web, fetch documentation, look up error messages                       |
| **Code intelligence** | See type errors and warnings after edits, jump to definitions, find references    |

**Extending the base capabilities:** You can extend what Claude knows with skills, connect to external services with MCP, automate workflows with hooks, and offload tasks to subagents.

## What Claude can access

When you run `claude` in a directory, Claude Code gains access to:

* **Your project.** Files in your directory and subdirectories, plus files elsewhere with your permission.
* **Your terminal.** Any command you could run: build tools, git, package managers, system utilities, scripts.
* **Your git state.** Current branch, uncommitted changes, and recent commit history.
* **Your CLAUDE.md.** A markdown file where you store project-specific instructions.
* **Auto memory.** Learnings Claude saves automatically as you work. The first 200 lines or 25KB of MEMORY.md load at the start of each session.
* **Extensions you configure.** MCP servers, skills, subagents, and Claude in Chrome.

## Environments and interfaces

### Execution environments

| Environment        | Where code runs                         | Use case                                                   |
| ------------------ | --------------------------------------- | ---------------------------------------------------------- |
| **Local**          | Your machine                            | Default. Full access to your files, tools, and environment |
| **Cloud**          | Anthropic-managed VMs                   | Offload tasks, work on repos you don't have locally        |
| **Remote Control** | Your machine, controlled from a browser | Use the web UI while keeping everything local              |

### Interfaces

You can access Claude Code through the terminal, the desktop app, IDE extensions, claude.ai/code, Remote Control, Slack, and CI/CD pipelines.

## Work with sessions

Claude Code saves your conversation locally as you work. Each message, tool use, and result is stored.

**Sessions are independent.** Each new session starts with a fresh context window, without the conversation history from previous sessions.

### Work across branches

Each Claude Code conversation is a session tied to your current directory. Claude sees your current branch's files.

Since sessions are tied to directories, you can run parallel Claude sessions by using git worktrees.

### Resume or fork sessions

When you resume a session with `claude --continue` or `claude --resume`, you pick up where you left off using the same session ID.

To branch off and try a different approach without affecting the original session, use the `--fork-session` flag:

```bash
claude --continue --fork-session
```

### The context window

Claude's context window holds your conversation history, file contents, command outputs, CLAUDE.md, auto memory, loaded skills, and system instructions. As you work, context fills up. Claude compacts automatically, but instructions from early in the conversation can get lost.

Run `/context` to see what's using space.

#### When context fills up

Claude Code manages context automatically as you approach the limit. It clears older tool outputs first, then summarizes the conversation if needed.

To control what's preserved during compaction, add a "Compact Instructions" section to CLAUDE.md or run `/compact` with a focus (like `/compact focus on the API changes`).

#### Manage context with skills and subagents

Skills load on demand. Subagents get their own fresh context, completely separate from your main conversation.

## Stay safe with checkpoints and permissions

### Undo changes with checkpoints

**Every file edit is reversible.** Before Claude edits any file, it snapshots the current contents. Press `Esc` twice to rewind to a previous state.

### Control what Claude can do

Press `Shift+Tab` to cycle through permission modes:

* **Default**: Claude asks before file edits and shell commands
* **Auto-accept edits**: Claude edits files without asking, still asks for commands
* **Plan mode**: Claude uses read-only tools only
* **Auto mode**: Claude evaluates all actions with background safety checks (research preview)

## Work effectively with Claude Code

### Ask Claude Code for help

Built-in commands guide you through setup:
* `/init` walks you through creating a CLAUDE.md
* `/agents` helps you configure custom subagents
* `/doctor` diagnoses common issues

### It's a conversation

Start with what you want, then refine. You can interrupt Claude at any point.

### Be specific upfront

```text
The checkout flow is broken for users with expired cards.
Check src/payments/ for the issue, especially token refresh.
Write a failing test first, then fix it.
```

### Give Claude something to verify against

Include test cases, paste screenshots of expected UI, or define the output you want.

### Explore before implementing

Use plan mode (`Shift+Tab` twice) to analyze the codebase first:

```text
Read src/auth/ and understand how we handle sessions.
Then create a plan for adding OAuth support.
```

### Delegate, don't dictate

Give context and direction, then trust Claude to figure out the details.
