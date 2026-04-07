# Quickstart

> Source: https://code.claude.com/docs/en/quickstart

This quickstart guide will have you using AI-powered coding assistance in a few minutes. By the end, you'll understand how to use Claude Code for common development tasks.

## Before you begin

Make sure you have:

* A terminal or command prompt open
* A code project to work with
* A Claude subscription (Pro, Max, Team, or Enterprise), Claude Console account, or access through a supported cloud provider

## Step 1: Install Claude Code

**macOS, Linux, WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows PowerShell:**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**Windows CMD:**
```batch
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

If you see `The token '&&' is not a valid statement separator`, you're in PowerShell, not CMD. Use the PowerShell command above instead.

**Windows requires Git for Windows.** Install it first if you don't have it.

**Homebrew:**
```bash
brew install --cask claude-code
```

**WinGet:**
```powershell
winget install Anthropic.ClaudeCode
```

> Native installations automatically update in the background. Homebrew and WinGet installations do not auto-update.

## Step 2: Log in to your account

```bash
claude
# You'll be prompted to log in on first use
```

```bash
/login
# Follow the prompts to log in with your account
```

You can log in using:
* Claude Pro, Max, Team, or Enterprise (recommended)
* Claude Console (API access with pre-paid credits)
* Amazon Bedrock, Google Vertex AI, or Microsoft Foundry

## Step 3: Start your first session

```bash
cd /path/to/your/project
claude
```

Type `/help` for available commands or `/resume` to continue a previous conversation.

## Step 4: Ask your first question

```text
what does this project do?
```

```text
what technologies does this project use?
```

```text
where is the main entry point?
```

```text
explain the folder structure
```

You can also ask Claude about its own capabilities:

```text
what can Claude Code do?
```

> Claude Code reads your project files as needed. You don't have to manually add context.

## Step 5: Make your first code change

```text
add a hello world function to the main file
```

Claude Code will:
1. Find the appropriate file
2. Show you the proposed changes
3. Ask for your approval
4. Make the edit

> Claude Code always asks for permission before modifying files.

## Step 6: Use Git with Claude Code

```text
what files have I changed?
```

```text
commit my changes with a descriptive message
```

```text
create a new branch called feature/quickstart
```

```text
show me the last 5 commits
```

```text
help me resolve merge conflicts
```

## Step 7: Fix a bug or add a feature

```text
add input validation to the user registration form
```

```text
there's a bug where users can submit empty forms - fix it
```

Claude Code will:
* Locate the relevant code
* Understand the context
* Implement a solution
* Run tests if available

## Step 8: Test out other common workflows

**Refactor code**
```text
refactor the authentication module to use async/await instead of callbacks
```

**Write tests**
```text
write unit tests for the calculator functions
```

**Update documentation**
```text
update the README with installation instructions
```

**Code review**
```text
review my changes and suggest improvements
```

## Essential commands

| Command             | What it does                                           | Example                             |
| ------------------- | ------------------------------------------------------ | ----------------------------------- |
| `claude`            | Start interactive mode                                 | `claude`                            |
| `claude "task"`     | Run a one-time task                                    | `claude "fix the build error"`      |
| `claude -p "query"` | Run one-off query, then exit                           | `claude -p "explain this function"` |
| `claude -c`         | Continue most recent conversation in current directory | `claude -c`                         |
| `claude -r`         | Resume a previous conversation                         | `claude -r`                         |
| `/clear`            | Clear conversation history                             | `/clear`                            |
| `/help`             | Show available commands                                | `/help`                             |
| `exit` or Ctrl+D    | Exit Claude Code                                       | `exit`                              |

## Pro tips for beginners

**Be specific with your requests**: Instead of "fix the bug", try "fix the login bug where users see a blank screen after entering wrong credentials"

**Use step-by-step instructions**: Break complex tasks into steps.

**Let Claude explore first**: Before making changes, let Claude understand your code.

**Save time with shortcuts**:
* Press `?` to see all available keyboard shortcuts
* Use Tab for command completion
* Press up arrow for command history
* Type `/` to see all commands and skills

## What's next?

- How Claude Code works
- Best practices
- Common workflows
- Extend Claude Code (CLAUDE.md, skills, hooks, MCP)

## Getting help

* **In Claude Code**: Type `/help` or ask "how do I..."
* **Documentation**: Browse other guides
* **Community**: Join the Anthropic Discord for tips and support
