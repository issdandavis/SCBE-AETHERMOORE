# Authentication

> Source: https://code.claude.com/docs/en/authentication

> Log in to Claude Code and configure authentication for individuals, teams, and organizations.

Claude Code supports multiple authentication methods depending on your setup. Individual users can log in with a Claude.ai account, while teams can use Claude for Teams or Enterprise, the Claude Console, or a cloud provider like Amazon Bedrock, Google Vertex AI, or Microsoft Foundry.

## Log in to Claude Code

After installing Claude Code, run `claude` in your terminal. On first launch, Claude Code opens a browser window for you to log in.

If the browser doesn't open automatically, press `c` to copy the login URL to your clipboard, then paste it into your browser.

You can authenticate with any of these account types:

* **Claude Pro or Max subscription**: log in with your Claude.ai account.
* **Claude for Teams or Enterprise**: log in with the Claude.ai account your team admin invited you to.
* **Claude Console**: log in with your Console credentials. Your admin must have invited you first.
* **Cloud providers**: if your organization uses Amazon Bedrock, Google Vertex AI, or Microsoft Foundry, set the required environment variables before running `claude`. No browser login is needed.

To log out and re-authenticate, type `/logout` at the Claude Code prompt.

## Set up team authentication

For teams and organizations, you can configure Claude Code access in one of these ways:

* Claude for Teams or Enterprise (recommended for most teams)
* Claude Console
* Amazon Bedrock
* Google Vertex AI
* Microsoft Foundry

### Claude for Teams or Enterprise

Claude for Teams and Claude for Enterprise provide the best experience for organizations using Claude Code. Team members get access to both Claude Code and Claude on the web with centralized billing and team management.

* **Claude for Teams**: self-service plan with collaboration features, admin tools, and billing management.
* **Claude for Enterprise**: adds SSO, domain capture, role-based permissions, compliance API, and managed policy settings.

1. Subscribe to Claude for Teams or contact sales for Claude for Enterprise.
2. Invite team members from the admin dashboard.
3. Team members install Claude Code and log in with their Claude.ai accounts.

### Claude Console authentication

For organizations that prefer API-based billing:

1. Create or use a Console account.
2. Add users via bulk invite (Settings -> Members -> Invite) or set up SSO.
3. Assign roles: **Claude Code** role (can only create Claude Code API keys) or **Developer** role (can create any kind of API key).
4. Each invited user accepts the invite, installs Claude Code, and logs in with Console credentials.

### Cloud provider authentication

For teams using Amazon Bedrock, Google Vertex AI, or Microsoft Foundry:

1. Follow the provider-specific setup docs.
2. Distribute the environment variables and instructions for generating cloud credentials.
3. Users install Claude Code.

## Credential management

Claude Code securely manages your authentication credentials:

* **Storage location**: on macOS, credentials are stored in the encrypted macOS Keychain. On Linux and Windows, credentials are stored in `~/.claude/.credentials.json`, or under `$CLAUDE_CONFIG_DIR` if that variable is set. On Linux, the file is written with mode `0600`; on Windows, it inherits the access controls of your user profile directory.
* **Supported authentication types**: Claude.ai credentials, Claude API credentials, Azure Auth, Bedrock Auth, and Vertex Auth.
* **Custom credential scripts**: the `apiKeyHelper` setting can be configured to run a shell script that returns an API key.
* **Refresh intervals**: by default, `apiKeyHelper` is called after 5 minutes or on HTTP 401 response. Set `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` environment variable for custom refresh intervals.
* **Slow helper notice**: if `apiKeyHelper` takes longer than 10 seconds to return a key, Claude Code displays a warning notice.

`apiKeyHelper`, `ANTHROPIC_API_KEY`, and `ANTHROPIC_AUTH_TOKEN` apply to terminal CLI sessions only. Claude Desktop and remote sessions use OAuth exclusively.

### Authentication precedence

When multiple credentials are present, Claude Code chooses one in this order:

1. Cloud provider credentials, when `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, or `CLAUDE_CODE_USE_FOUNDRY` is set.
2. `ANTHROPIC_AUTH_TOKEN` environment variable. Sent as the `Authorization: Bearer` header.
3. `ANTHROPIC_API_KEY` environment variable. Sent as the `X-Api-Key` header.
4. `apiKeyHelper` script output. Use this for dynamic or rotating credentials.
5. Subscription OAuth credentials from `/login`. This is the default for Claude Pro, Max, Team, and Enterprise users.

If you have an active Claude subscription but also have `ANTHROPIC_API_KEY` set in your environment, the API key takes precedence once approved. Run `unset ANTHROPIC_API_KEY` to fall back to your subscription, and check `/status` to confirm which method is active.

Claude Code on the Web always uses your subscription credentials. `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` in the sandbox environment do not override them.
