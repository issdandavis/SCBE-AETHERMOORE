# Claude Code on the web

> Source: https://code.claude.com/docs/en/claude-code-on-the-web

> Run Claude Code tasks asynchronously on secure cloud infrastructure.

Claude Code on the web is currently in research preview.

## What is Claude Code on the web?

Claude Code on the web lets developers kick off Claude Code from the Claude app. This is perfect for:

* **Answering questions**: Ask about code architecture and how features are implemented
* **Bug fixes and routine tasks**: Well-defined tasks that don't require frequent steering
* **Parallel work**: Tackle multiple bug fixes in parallel
* **Repositories not on your local machine**: Work on code you don't have checked out locally
* **Backend changes**: Where Claude Code can write tests and then write code to pass those tests

Also available on the Claude app for iOS and Android.

You can kick off new tasks on the web from your terminal with `--remote`, or teleport web sessions back to your terminal to continue locally.

## Who can use Claude Code on the web?

Available in research preview to Pro, Max, Team, and Enterprise users (Enterprise requires premium seats or Chat + Claude Code seats).

## Getting started

### From the browser

1. Visit [claude.ai/code](https://claude.ai/code)
2. Connect your GitHub account
3. Install the Claude GitHub App in your repositories
4. Select your default environment
5. Submit your coding task
6. Review changes in diff view, iterate with comments, then create a pull request

### From the terminal

Run `/web-setup` inside Claude Code to connect GitHub using your local `gh` CLI credentials. This requires the `gh` CLI to be installed and authenticated with `gh auth login`.

## How it works

1. **Repository cloning**: Your repository is cloned to an Anthropic-managed virtual machine
2. **Environment setup**: Claude prepares a secure cloud environment, then runs your setup script
3. **Network configuration**: Internet access is configured based on your settings
4. **Task execution**: Claude analyzes code, makes changes, runs tests, and checks its work
5. **Completion**: You're notified when finished and can create a PR
6. **Results**: Changes are pushed to a branch, ready for pull request creation

## Review changes with diff view

Diff view lets you see exactly what Claude changed before creating a pull request. Select the diff stats indicator to open the diff viewer.

From the diff view, you can:
* Review changes file by file
* Comment on specific changes to request modifications
* Continue iterating with Claude based on what you see

## Auto-fix pull requests

Claude can watch a pull request and automatically respond to CI failures and review comments. Requires the Claude GitHub App.

Ways to enable auto-fix:
* **PRs created in Claude Code on the web**: open the CI status bar and select Auto-fix
* **From the mobile app**: tell Claude to auto-fix the PR
* **Any existing PR**: paste the PR URL into a session and tell Claude to auto-fix it

### How Claude responds to PR activity

* **Clear fixes**: Claude makes the change and pushes it
* **Ambiguous requests**: Claude asks you before acting
* **Duplicate or no-action events**: Claude notes it and moves on

Claude may reply to review comment threads on GitHub using your GitHub account, but each reply is labeled as coming from Claude Code.

## Moving tasks between web and terminal

### From terminal to web

```bash
claude --remote "Fix the authentication bug in src/auth/login.ts"
```

#### Tips for remote tasks

**Plan locally, execute remotely**: Start in plan mode, then send to web:

```bash
claude --permission-mode plan
# After planning:
claude --remote "Execute the migration plan in docs/migration-plan.md"
```

**Run tasks in parallel**: Each `--remote` command creates its own session:

```bash
claude --remote "Fix the flaky test in auth.spec.ts"
claude --remote "Update the API documentation"
claude --remote "Refactor the logger to use structured output"
```

### From web to terminal

* **Using `/teleport`**: Run `/teleport` (or `/tp`) for an interactive picker
* **Using `--teleport`**: Run `claude --teleport` or `claude --teleport <session-id>`
* **From `/tasks`**: Press `t` to teleport into a session
* **From the web interface**: Click "Open in CLI"

#### Requirements for teleporting

| Requirement        | Details                                                           |
| ------------------ | ----------------------------------------------------------------- |
| Clean git state    | No uncommitted changes                                            |
| Correct repository | Must be the same repo, not a fork                                 |
| Branch available   | Branch must have been pushed to remote                            |
| Same account       | Same Claude.ai account as the web session                         |

### Sharing sessions

Toggle visibility between Private and Team/Public depending on your account type.

## Schedule recurring tasks

See Schedule tasks on the web for the full guide.

## Cloud environment

### Default image

A universal image with common toolchains pre-installed including popular programming languages, build tools, package managers, testing frameworks, and linters.

Run `check-tools` to see what's pre-installed.

#### Language-specific setups

* **Python**: Python 3.x with pip, poetry
* **Node.js**: Latest LTS with npm, yarn, pnpm, bun
* **Ruby**: Versions 3.1.6, 3.2.6, 3.3.6 with rbenv
* **PHP**: Version 8.4.14
* **Java**: OpenJDK with Maven and Gradle
* **Go**: Latest stable
* **Rust**: Rust toolchain with cargo
* **C++**: GCC and Clang

#### Databases

* **PostgreSQL**: Version 16
* **Redis**: Version 7.0

### Environment configuration

**To add a new environment:** Select environment -> "Add environment" and specify name, network access, env vars, and setup script.

**To select default from terminal:** Run `/remote-env`.

### Setup scripts

Bash scripts that run when a new cloud session starts, before Claude Code launches. Run as root on Ubuntu 24.04.

Example:

```bash
#!/bin/bash
apt update && apt install -y gh
```

Setup scripts run only when creating a new session, not when resuming.

|               | Setup scripts              | SessionStart hooks                    |
| ------------- | -------------------------- | ------------------------------------- |
| Attached to   | Cloud environment          | Your repository                       |
| Runs          | Before Claude Code, new only | After Claude Code, every session    |
| Scope         | Cloud only                 | Both local and cloud                  |

### Dependency management

Use setup scripts or SessionStart hooks to install packages:

```bash
#!/bin/bash
npm install
pip install -r requirements.txt
```

## Network access and security

### GitHub proxy

All GitHub operations go through a dedicated proxy that manages authentication securely using scoped credentials.

### Security proxy

All outbound internet traffic passes through an HTTP/HTTPS proxy for security and abuse prevention.

### Access levels

Default: limited to allowlisted domains. Configurable to no internet or full internet access.

### Default allowed domains

When using "Limited" network access, common domains are allowed including:

* **Anthropic Services**: api.anthropic.com, claude.ai
* **Version Control**: github.com, gitlab.com, bitbucket.org
* **Container Registries**: Docker, GCR, GHCR, ECR
* **Cloud Platforms**: GCP, Azure, AWS, Oracle
* **Package Managers**: npm, PyPI, RubyGems, crates.io, Go, Maven, NuGet, pub.dev, Cocoapods, Hackage
* **Linux Distributions**: Ubuntu
* **Development Tools**: Kubernetes, HashiCorp, Conda, Apache, Node.js
* **MCP**: modelcontextprotocol.io

## Security and isolation

* **Isolated virtual machines**: Each session runs in an isolated VM
* **Network access controls**: Limited by default, configurable
* **Credential protection**: Sensitive credentials are never inside the sandbox
* **Secure analysis**: Code analyzed within isolated VMs

## Pricing and rate limits

Shares rate limits with all other Claude usage within your account. Multiple parallel tasks consume proportionately more.

## Limitations

* **Repository authentication**: Same account required for web-to-local session transfer
* **Platform restrictions**: GitHub only. GitHub Enterprise Server supported for Team and Enterprise. GitLab and other platforms not supported.

## Best practices

1. **Automate environment setup**: Use setup scripts and SessionStart hooks
2. **Document requirements**: Specify dependencies in CLAUDE.md

## Related resources

* Hooks configuration
* Settings reference
* Security
* Data usage
