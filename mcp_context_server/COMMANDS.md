# SCBE MCP Context Server — Command List

Quick-reference for running, benchmarking, and connecting agents to
the SCBE MCP context server.

---

## Local server (operator)

```powershell
# Start the server (default: http://127.0.0.1:5719/mcp, no auth)
npm run mcp:context-server

# Bind a different port
$env:MCP_CONTEXT_PORT = 6000; npm run mcp:context-server

# Require bearer auth (recommended if tunneling)
$env:MCP_CONTEXT_TOKEN = (New-Guid).Guid
npm run mcp:context-server

# Bind all interfaces (only behind a reverse proxy)
$env:MCP_CONTEXT_HOST = "0.0.0.0"; npm run mcp:context-server
```

Health check:

```powershell
curl http://127.0.0.1:5719/health
```

---

## Bench + tests

```powershell
# Run benchmark (writes report to artifacts/mcp_context_bench/)
npm run mcp:context-bench

# Run benchmark with custom iteration count
node mcp_context_server/bench.js --iters 200 --warmup 20

# Run tests (21 tests)
npx vitest run tests/mcp_context_server/server.test.ts
```

---

## MCP tools exposed

| Tool | Args | Returns |
|---|---|---|
| `list_docs` | `prefix?: string` | `{ count, files: string[] }` |
| `read_doc` | `path: string` | `{ path, bytes, modified, content }` |
| `search_docs` | `query: string`, `limit?: number` (1–100, default 25) | `{ query, count, hits: [{path, offset, snippet}] }` |
| `get_one_pager` | (none) | One-pager content (string) |

Doc roots exposed: `docs/`, `book/`, `notes/` (Obsidian vault).

---

## Connect from agent clients

### Claude Code (this CLI)

Add to `.mcp.json` or `~/.claude.json`:

```json
{
  "mcpServers": {
    "scbe-context": {
      "type": "http",
      "url": "http://127.0.0.1:5719/mcp"
    }
  }
}
```

With auth:

```json
{
  "mcpServers": {
    "scbe-context": {
      "type": "http",
      "url": "http://127.0.0.1:5719/mcp",
      "headers": { "Authorization": "Bearer YOUR_TOKEN" }
    }
  }
}
```

### Claude Desktop / Cursor / Continue

Same shape — point the client at `http://127.0.0.1:5719/mcp`. The server speaks Streamable HTTP (POST `/mcp`).

### Claude.ai (Custom Connector)

Requires a public HTTPS URL. Tunnel via cloudflared:

```powershell
# In a second terminal, after starting the server with a token
cloudflared tunnel --url http://127.0.0.1:5719
```

Cloudflared prints `https://random-words.trycloudflare.com`. In the Claude.ai Custom Connector form:

- **Server URL**: `https://random-words.trycloudflare.com/mcp`
- **Auth**: Bearer + your `MCP_CONTEXT_TOKEN`

Or via ngrok:

```powershell
ngrok http 5719
```

Use the printed `https://...ngrok-free.app/mcp`.

---

## Direct HTTP (debugging)

```powershell
# initialize
curl -X POST http://127.0.0.1:5719/mcp `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'

# tools/list
curl -X POST http://127.0.0.1:5719/mcp `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# call get_one_pager
curl -X POST http://127.0.0.1:5719/mcp `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_one_pager","arguments":{}}}'
```

---

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `MCP_CONTEXT_PORT` | `5719` | TCP port |
| `MCP_CONTEXT_HOST` | `127.0.0.1` | Bind address |
| `MCP_CONTEXT_TOKEN` | (unset) | Bearer token. Unset = open (only safe on localhost) |

---

## File locations

| Path | What |
|---|---|
| `mcp_context_server/server.js` | Server entrypoint |
| `mcp_context_server/bench.js` | Benchmark harness |
| `mcp_context_server/README.md` | Full README |
| `mcp_context_server/COMMANDS.md` | This file |
| `tests/mcp_context_server/server.test.ts` | Tests |
| `artifacts/mcp_context_bench/` | Bench reports (JSON, UTC-stamped) |
