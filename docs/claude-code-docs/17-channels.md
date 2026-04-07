# Push events into a running session with channels

> Source: https://code.claude.com/docs/en/channels

> Use channels to push messages, alerts, and webhooks into your Claude Code session from an MCP server. Forward CI results, chat messages, and monitoring events so Claude can react while you're away.

Channels are in research preview and require Claude Code v2.1.80 or later. They require claude.ai login. Console and API key authentication is not supported. Team and Enterprise organizations must explicitly enable them.

A channel is an MCP server that pushes events into your running Claude Code session, so Claude can react to things that happen while you're not at the terminal. Channels can be two-way: Claude reads the event and replies back through the same channel, like a chat bridge. Events only arrive while the session is open, so for an always-on setup you run Claude in a background process or persistent terminal.

Unlike integrations that spawn a fresh cloud session or wait to be polled, the event arrives in the session you already have open.

You install a channel as a plugin and configure it with your own credentials. Telegram, Discord, and iMessage are included in the research preview.

When Claude replies through a channel, you see the inbound message in your terminal but not the reply text. The terminal shows the tool call and a confirmation, and the actual reply appears on the other platform.

## Supported channels

Each supported channel is a plugin that requires Bun.

### Telegram

1. Create a Telegram bot via BotFather and copy the token
2. Install the plugin: `/plugin install telegram@claude-plugins-official`
3. Configure your token: `/telegram:configure <token>`
4. Restart with channels enabled: `claude --channels plugin:telegram@claude-plugins-official`
5. Pair your account by messaging the bot and running `/telegram:access pair <code>`
6. Lock access: `/telegram:access policy allowlist`

### Discord

1. Create a Discord bot in the Developer Portal
2. Enable Message Content Intent
3. Invite the bot with appropriate permissions
4. Install: `/plugin install discord@claude-plugins-official`
5. Configure: `/discord:configure <token>`
6. Restart with channels: `claude --channels plugin:discord@claude-plugins-official`
7. Pair by DMing the bot and running `/discord:access pair <code>`

### iMessage

1. Grant Full Disk Access to your terminal (macOS only)
2. Install: `/plugin install imessage@claude-plugins-official`
3. Restart with channels: `claude --channels plugin:imessage@claude-plugins-official`
4. Text yourself to test (self-chat bypasses access control)
5. Allow other senders: `/imessage:access allow +15551234567`

You can also build your own channel.

## Quickstart

Fakechat is an officially supported demo channel that runs a chat UI on localhost:

1. Install: `/plugin install fakechat@claude-plugins-official`
2. Restart: `claude --channels plugin:fakechat@claude-plugins-official`
3. Open http://localhost:8787 and type a message

## Security

Every approved channel plugin maintains a sender allowlist: only IDs you've added can push messages, and everyone else is silently dropped.

Telegram and Discord bootstrap the list by pairing. iMessage detects your own addresses automatically.

You control which servers are enabled each session with `--channels`, and on Team and Enterprise plans your organization controls availability with `channelsEnabled`.

## Enterprise controls

On Team and Enterprise plans, channels are off by default.

| Setting                 | Purpose                                           | When not configured            |
| :---------------------- | :------------------------------------------------ | :----------------------------- |
| `channelsEnabled`       | Master switch. Must be `true` for channels.       | Channels blocked               |
| `allowedChannelPlugins` | Which plugins can register once channels enabled. | Anthropic default list applies |

Pro and Max users without an organization skip these checks entirely.

### Restrict which channel plugins can run

```json
{
  "channelsEnabled": true,
  "allowedChannelPlugins": [
    { "marketplace": "claude-plugins-official", "plugin": "telegram" },
    { "marketplace": "claude-plugins-official", "plugin": "discord" },
    { "marketplace": "acme-corp-plugins", "plugin": "internal-alerts" }
  ]
}
```

## Research preview

Channels are a research preview feature. `--channels` only accepts plugins from an Anthropic-maintained allowlist, or from your organization's allowlist. To test a channel you're building, use `--dangerously-load-development-channels`.

## How channels compare

| Feature                   | What it does                                                | Good for                                          |
| ------------------------- | ----------------------------------------------------------- | ------------------------------------------------- |
| Claude Code on the web    | Runs tasks in a fresh cloud sandbox, cloned from GitHub     | Delegating self-contained async work              |
| Claude in Slack           | Spawns a web session from an @Claude mention                | Starting tasks from team conversation context     |
| Standard MCP server       | Claude queries it during a task; nothing is pushed          | On-demand access to read or query a system        |
| Remote Control            | You drive your local session from claude.ai or mobile       | Steering an in-progress session while away        |

Channels fill the gap by pushing events from non-Claude sources into your already-running local session.

## Next steps

* Build your own channel via the Channels reference
* Remote Control to drive a local session from your phone
* Scheduled tasks to poll on a timer instead of reacting to pushed events
