# Configure Permissions

> Source: https://code.claude.com/docs/en/permissions

Control what Claude Code can access and do with fine-grained permission rules, modes, and managed policies.

## Permission system

| Tool type         | Example          | Approval required | "Yes, don't ask again" behavior               |
| :---------------- | :--------------- | :---------------- | :-------------------------------------------- |
| Read-only         | File reads, Grep | No                | N/A                                           |
| Bash commands     | Shell execution  | Yes               | Permanently per project directory and command |
| File modification | Edit/write files | Yes               | Until session end                             |

## Manage permissions

Use `/permissions` to view and manage tool permissions.

* **Allow** rules let Claude Code use the specified tool without manual approval.
* **Ask** rules prompt for confirmation.
* **Deny** rules prevent Claude Code from using the specified tool.

Rules are evaluated in order: **deny -> ask -> allow**. The first matching rule wins.

## Permission modes

| Mode                | Description                                                                  |
| :------------------ | :--------------------------------------------------------------------------- |
| `default`           | Prompts for permission on first use of each tool                             |
| `acceptEdits`       | Automatically accepts file edit permissions for the session                  |
| `plan`              | Plan Mode: Claude can analyze but not modify files or execute commands        |
| `auto`              | Auto-approves tool calls with background safety checks (research preview)    |
| `dontAsk`           | Auto-denies tools unless pre-approved via `/permissions` or allow rules      |
| `bypassPermissions` | Skips permission prompts except for writes to protected directories          |

> `bypassPermissions` mode: Writes to `.git`, `.claude`, `.vscode`, `.idea`, and `.husky` directories still prompt. Only use in isolated environments.

## Permission rule syntax

### Match all uses of a tool

| Rule       | Effect                         |
| :--------- | :----------------------------- |
| `Bash`     | Matches all Bash commands      |
| `WebFetch` | Matches all web fetch requests |
| `Read`     | Matches all file reads         |

### Use specifiers for fine-grained control

| Rule                           | Effect                                                   |
| :----------------------------- | :------------------------------------------------------- |
| `Bash(npm run build)`          | Matches the exact command `npm run build`                |
| `Read(./.env)`                 | Matches reading the `.env` file                          |
| `WebFetch(domain:example.com)` | Matches fetch requests to example.com                    |

### Wildcard patterns

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git commit *)",
      "Bash(git * main)",
      "Bash(* --version)",
      "Bash(* --help *)"
    ],
    "deny": [
      "Bash(git push *)"
    ]
  }
}
```

## Tool-specific permission rules

### Bash

* `Bash(npm run build)` matches the exact command
* `Bash(npm run test *)` matches commands starting with `npm run test`
* `Bash(* install)` matches commands ending with `install`
* `Bash(ls *)` matches `ls -la` but not `lsof` (word boundary)
* `Bash(ls*)` matches both `ls -la` and `lsof`

> Claude Code is aware of shell operators (like `&&`) so a prefix match rule like `Bash(safe-cmd *)` won't give permission to run `safe-cmd && other-cmd`.

### Read and Edit

Read and Edit rules follow the gitignore specification:

| Pattern            | Meaning                                | Example                          |
| ------------------ | -------------------------------------- | -------------------------------- |
| `//path`           | **Absolute** path from filesystem root | `Read(//Users/alice/secrets/**)` |
| `~/path`           | Path from **home** directory           | `Read(~/Documents/*.pdf)`        |
| `/path`            | Path **relative to project root**      | `Edit(/src/**/*.ts)`             |
| `path` or `./path` | Path **relative to current directory** | `Read(*.env)`                    |

> On Windows, paths are normalized to POSIX form. `C:\Users\alice` becomes `/c/Users/alice`.

> Read and Edit deny rules apply to Claude's built-in file tools, not to Bash subprocesses.

### WebFetch

* `WebFetch(domain:example.com)` matches fetch requests to example.com

### MCP

* `mcp__puppeteer` matches any tool provided by the `puppeteer` server
* `mcp__puppeteer__puppeteer_navigate` matches a specific tool

### Agent (subagents)

```json
{
  "permissions": {
    "deny": ["Agent(Explore)"]
  }
}
```

## Extend permissions with hooks

PreToolUse hooks run before the permission prompt. The hook output can deny the tool call, force a prompt, or skip the prompt.

## Working directories

Extend access with:
* `--add-dir <path>` CLI argument
* `/add-dir` command during session
* `additionalDirectories` in settings files

### Additional directories grant file access, not configuration

| Configuration                                      | Loaded from `--add-dir`                                           |
| :------------------------------------------------- | :---------------------------------------------------------------- |
| Skills in `.claude/skills/`                        | Yes, with live reload                                             |
| Plugin settings in `.claude/settings.json`         | `enabledPlugins` and `extraKnownMarketplaces` only                |
| CLAUDE.md files and `.claude/rules/`               | Only when `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` is set |

## How permissions interact with sandboxing

* **Permissions** control which tools Claude Code can use
* **Sandboxing** provides OS-level enforcement for the Bash tool

When sandboxing is enabled with `autoAllowBashIfSandboxed: true` (default), sandboxed Bash commands run without prompting.

## Managed settings

For organizations needing centralized control.

### Managed-only settings

| Setting                                        | Description                                                                          |
| :--------------------------------------------- | :----------------------------------------------------------------------------------- |
| `allowedChannelPlugins`                        | Allowlist of channel plugins                                                         |
| `allowManagedHooksOnly`                        | Only managed and SDK hooks allowed                                                   |
| `allowManagedMcpServersOnly`                   | Only managed MCP servers                                                             |
| `allowManagedPermissionRulesOnly`              | Only managed permission rules                                                        |
| `blockedMarketplaces`                          | Blocklist of marketplace sources                                                     |
| `channelsEnabled`                              | Allow channels for Team and Enterprise users                                         |
| `forceRemoteSettingsRefresh`                   | Blocks CLI startup until remote managed settings are fetched                         |
| `pluginTrustMessage`                           | Custom message appended to plugin trust warning                                      |
| `sandbox.filesystem.allowManagedReadPathsOnly` | Only managed filesystem read paths                                                   |
| `sandbox.network.allowManagedDomainsOnly`      | Only managed network domains                                                         |
| `strictKnownMarketplaces`                      | Controls which plugin marketplaces users can add                                     |

## Configure the auto mode classifier

The `autoMode` settings block tells the classifier which infrastructure your organization trusts.

### Define trusted infrastructure

```json
{
  "autoMode": {
    "environment": [
      "Source control: github.example.com/acme-corp and all repos under it",
      "Trusted cloud buckets: s3://acme-build-artifacts, gs://acme-ml-datasets",
      "Trusted internal domains: *.corp.example.com, api.internal.example.com"
    ]
  }
}
```

### Override the block and allow rules

```json
{
  "autoMode": {
    "environment": ["..."],
    "allow": ["Deploying to staging is allowed..."],
    "soft_deny": ["Never run database migrations outside the migrations CLI..."]
  }
}
```

> Setting `allow` or `soft_deny` replaces the entire default list. Run `claude auto-mode defaults` first.

### Inspect defaults and effective config

```bash
claude auto-mode defaults  # built-in rules
claude auto-mode config    # effective rules with your settings
claude auto-mode critique  # AI feedback on your custom rules
```

## Settings precedence

1. **Managed settings**: cannot be overridden
2. **Command line arguments**: temporary session overrides
3. **Local project settings** (`.claude/settings.local.json`)
4. **Shared project settings** (`.claude/settings.json`)
5. **User settings** (`~/.claude/settings.json`)

If a tool is denied at any level, no other level can allow it.
