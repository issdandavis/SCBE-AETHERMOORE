# Claude Code Overview

> Source: https://code.claude.com/docs/en/overview

Claude Code is an agentic coding tool that reads your codebase, edits files, runs commands, and integrates with your development tools. Available in your terminal, IDE, desktop app, and browser.

## Get Started

Choose your environment to get started. Most surfaces require a Claude subscription or Anthropic Console account.

### Terminal

The full-featured CLI for working with Claude Code directly in your terminal.

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

**Homebrew:**
```bash
brew install --cask claude-code
```

**WinGet:**
```powershell
winget install Anthropic.ClaudeCode
```

Then start Claude Code in any project:
```bash
cd your-project
claude
```

### VS Code

Install for VS Code or Cursor, or search for "Claude Code" in the Extensions view.

### Desktop App

Download and install:
- macOS (Intel and Apple Silicon)
- Windows (x64)
- Windows ARM64 (remote sessions only)

### Web

Run Claude Code in your browser at claude.ai/code with no local setup.

### JetBrains

Install the Claude Code plugin from the JetBrains Marketplace.

## What You Can Do

- **Automate tedious tasks**: writing tests, fixing lint errors, resolving merge conflicts, updating dependencies
- **Build features and fix bugs**: describe what you want in plain language
- **Create commits and pull requests**: works directly with git
- **Connect your tools with MCP**: Model Context Protocol for external data sources
- **Customize with instructions, skills, and hooks**: CLAUDE.md, custom commands, shell hooks
- **Run agent teams**: spawn multiple Claude Code agents working simultaneously
- **Pipe, script, and automate with the CLI**: composable Unix-style usage
- **Schedule recurring tasks**: cloud or desktop scheduled tasks, /loop command
- **Work from anywhere**: Remote Control, Dispatch, web, iOS app, teleport

## Use Claude Code Everywhere

| I want to... | Best option |
|---|---|
| Continue a local session from my phone or another device | Remote Control |
| Push events from Telegram, Discord, iMessage, or webhooks | Channels |
| Start a task locally, continue on mobile | Web or Claude iOS app |
| Run Claude on a recurring schedule | Cloud or Desktop scheduled tasks |
| Automate PR reviews and issue triage | GitHub Actions or GitLab CI/CD |
| Get automatic code review on every PR | GitHub Code Review |
| Route bug reports from Slack to pull requests | Slack |
| Debug live web applications | Chrome |
| Build custom agents for your own workflows | Agent SDK |

## Next Steps

- Quickstart: walk through your first real task
- Store instructions and memories with CLAUDE.md files and auto memory
- Common workflows and best practices
- Settings: customize Claude Code
- Troubleshooting: solutions for common issues
