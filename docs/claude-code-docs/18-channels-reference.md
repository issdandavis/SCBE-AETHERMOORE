# Channels reference

> Source: https://code.claude.com/docs/en/channels-reference

> Build an MCP server that pushes webhooks, alerts, and chat messages into a Claude Code session. Reference for the channel contract: capability declaration, notification events, reply tools, sender gating, and permission relay.

Channels are in research preview and require Claude Code v2.1.80 or later.

A channel is an MCP server that pushes events into a Claude Code session so Claude can react to things happening outside the terminal.

You can build a one-way or two-way channel. One-way channels forward alerts, webhooks, or monitoring events. Two-way channels also expose a reply tool so Claude can send messages back. A channel with a trusted sender path can also opt in to relay permission prompts so you can approve or deny tool use remotely.

## Overview

A channel is an MCP server that runs on the same machine as Claude Code. Claude Code spawns it as a subprocess and communicates over stdio. Your channel server bridges external systems and the Claude Code session:

* **Chat platforms** (Telegram, Discord): your plugin runs locally and polls the platform's API for new messages.
* **Webhooks** (CI, monitoring): your server listens on a local HTTP port. External systems POST to that port.

## What you need

The only hard requirement is the `@modelcontextprotocol/sdk` package and a Node.js-compatible runtime (Bun, Node, or Deno).

Your server needs to:

1. Declare the `claude/channel` capability so Claude Code registers a notification listener
2. Emit `notifications/claude/channel` events when something happens
3. Connect over stdio transport

During the research preview, custom channels need `--dangerously-load-development-channels` to test locally.

## Example: build a webhook receiver

Create a single-file server that listens for HTTP requests and forwards them into your Claude Code session.

### 1. Create the project

```bash
mkdir webhook-channel && cd webhook-channel
bun add @modelcontextprotocol/sdk
```

### 2. Write the channel server

Create `webhook.ts`:

```ts
#!/usr/bin/env bun
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: { experimental: { 'claude/channel': {} } },
    instructions: 'Events from the webhook channel arrive as <channel source="webhook" ...>. They are one-way.',
  },
)

await mcp.connect(new StdioServerTransport())

Bun.serve({
  port: 8788,
  hostname: '127.0.0.1',
  async fetch(req) {
    const body = await req.text()
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: {
        content: body,
        meta: { path: new URL(req.url).pathname, method: req.method },
      },
    })
    return new Response('ok')
  },
})
```

### 3. Register your server

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "webhook": { "command": "bun", "args": ["./webhook.ts"] }
  }
}
```

### 4. Test it

```bash
claude --dangerously-load-development-channels server:webhook
```

Then in another terminal:

```bash
curl -X POST localhost:8788 -d "build failed on main: https://ci.example.com/run/1234"
```

## Test during the research preview

```bash
# Testing a plugin you're developing
claude --dangerously-load-development-channels plugin:yourplugin@yourmarketplace

# Testing a bare .mcp.json server
claude --dangerously-load-development-channels server:webhook
```

## Server options

| Field                                                    | Type     | Description                                                    |
| :------------------------------------------------------- | :------- | :------------------------------------------------------------- |
| `capabilities.experimental['claude/channel']`            | `object` | Required. Always `{}`. Registers the notification listener.    |
| `capabilities.experimental['claude/channel/permission']` | `object` | Optional. Declares permission relay support.                   |
| `capabilities.tools`                                     | `object` | Two-way only. Always `{}`. Standard MCP tool capability.       |
| `instructions`                                           | `string` | Recommended. Added to Claude's system prompt.                  |

## Notification format

Your server emits `notifications/claude/channel` with two params:

| Field     | Type                     | Description                                                 |
| :-------- | :----------------------- | :---------------------------------------------------------- |
| `content` | `string`                 | The event body. Delivered as the body of the `<channel>` tag. |
| `meta`    | `Record<string, string>` | Optional. Each entry becomes an attribute on the tag.       |

## Expose a reply tool

For two-way channels, expose a standard MCP tool that Claude can call to send messages back:

1. Add `tools: {}` to capabilities
2. Register tool handlers with `ListToolsRequestSchema` and `CallToolRequestSchema`
3. Update instructions to tell Claude when and how to use the reply tool

## Gate inbound messages

An ungated channel is a prompt injection vector. Check the sender against an allowlist before calling `mcp.notification()`:

```ts
const allowed = new Set(loadAllowlist())
if (!allowed.has(message.from.id)) return  // drop silently
await mcp.notification({ ... })
```

Gate on the sender's identity, not the chat or room identity.

## Relay permission prompts

Permission relay requires Claude Code v2.1.81 or later.

When Claude calls a tool that needs approval, the local terminal dialog opens and the session waits. A two-way channel can opt in to receive the same prompt in parallel and relay it to you on another device.

### How relay works

1. Claude Code generates a short request ID and notifies your server
2. Your server forwards the prompt and ID to your chat app
3. The remote user replies with a yes or no and that ID
4. Your inbound handler parses the reply into a verdict

### Permission request fields

| Field           | Description                                              |
| --------------- | -------------------------------------------------------- |
| `request_id`    | Five lowercase letters (a-z minus l)                     |
| `tool_name`     | Name of the tool Claude wants to use                     |
| `description`   | Human-readable summary of the tool call                  |
| `input_preview` | Tool arguments as JSON, truncated to 200 characters      |

The verdict notification uses `notifications/claude/channel/permission` with `request_id` and `behavior` (`'allow'` or `'deny'`).

### Add relay to a chat bridge

1. Declare `claude/channel/permission: {}` in capabilities
2. Handle `notifications/claude/channel/permission_request` notifications
3. Intercept `yes <id>` / `no <id>` replies in your inbound handler

## Package as a plugin

To make your channel installable, wrap it in a plugin and publish it to a marketplace. Users install with `/plugin install`, then enable with `--channels plugin:<name>@<marketplace>`.

## See also

* [Channels](/en/channels) to install and use Telegram, Discord, iMessage, or fakechat
* [Working channel implementations](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins)
* [MCP](/en/mcp) for the underlying protocol
* [Plugins](/en/plugins) to package your channel
