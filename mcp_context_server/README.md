# SCBE MCP Context Server

Tiny MCP (Model Context Protocol) server that exposes the curated
`docs/`, `book/`, and `notes/` trees so agents — Claude.ai Custom
Connectors, Claude Desktop, Cursor, Continue, etc. — can pull
SCBE-AETHERMOORE context in the structured form the docs already
define. `notes/` is the Obsidian vault; the full thing is sourced.

Transport: **Streamable HTTP** (one POST `/mcp` endpoint, stateless).

## Run it

```powershell
npm run mcp:context-server
```

The server prints:

```
SCBE MCP Context Server — http://127.0.0.1:5719/mcp
Auth: OPEN (no token; localhost only)
Docs roots: docs, book
```

Override:

- `MCP_CONTEXT_PORT=NNNN` — bind a different port (default 5719)
- `MCP_CONTEXT_HOST=0.0.0.0` — bind all interfaces (only do this behind a reverse proxy)
- `MCP_CONTEXT_TOKEN=somesecret` — require `Authorization: Bearer somesecret` on every request

## Tools exposed

| Tool                         | Purpose                                                                                       |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| `list_docs(prefix?)`         | List `.md`/`.mdx` files under `docs/` and `book/`, optionally filtered by path prefix         |
| `read_doc(path)`             | Read one file by repo-relative path; rejected if path doesn't resolve under the allowed roots |
| `search_docs(query, limit?)` | Case-insensitive substring search; returns up to `limit` hits with snippets                   |
| `get_one_pager()`            | Return `docs/SCBE_AETHERMOORE_ONE_PAGER.md` directly — best place to start                    |

## Connecting from Claude.ai (Custom Connector)

Claude.ai requires a **public HTTPS** URL for Custom Connectors. The
server binds to `127.0.0.1` for safety, so you need a tunnel:

### Option A — Cloudflare Tunnel (free, no signup needed for quick tunnel)

```powershell
# Install once: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://127.0.0.1:5719
```

Cloudflared prints a URL like `https://random-words.trycloudflare.com`. Use:

```
Server URL: https://random-words.trycloudflare.com/mcp
```

Add a token first if you tunnel:

```powershell
$env:MCP_CONTEXT_TOKEN = (New-Guid).Guid
npm run mcp:context-server
```

…and paste the token into Claude.ai's Custom Connector auth field.

### Option B — ngrok

```powershell
ngrok http 5719
```

Use the `https://...ngrok-free.app/mcp` URL ngrok prints.

### Option C — Deploy

Wrap `mcp_context_server/server.js` in any Node host (Cloud Run, Render,
Fly.io, Vercel — though Vercel's serverless model isn't ideal for
streaming). Set `MCP_CONTEXT_HOST=0.0.0.0` and `MCP_CONTEXT_PORT=$PORT`
in the environment, plus `MCP_CONTEXT_TOKEN` for auth.

## Connecting from Claude Desktop

Add to `claude_desktop_config.json` (Desktop uses stdio, not HTTP — this
server only does HTTP, so wrap it via a small shim or use the Python
`src/mcp_server/semantic_mesh.py` server which already speaks stdio).

## Performance

In-process bench (`npm run mcp:context-bench`) on a 767-file corpus
(`docs/` + `book/` + `notes/`):

| Tool                                | p50      | p95     |
| ----------------------------------- | -------- | ------- |
| `list_docs`                         | ~3 ms    | ~4 ms   |
| `read_doc`                          | ~0.06 ms | ~0.1 ms |
| `search_docs` (early-exit at limit) | ~3 ms    | ~5 ms   |
| `search_docs` (full scan, no match) | ~125 ms  | ~155 ms |

Mtime-keyed listing + body cache (with cached lowercase) keeps the
hot path in memory. First call after a file edit pays the disk read
once; subsequent queries hit RAM.

## Security

- Path traversal: `read_doc` rejects anything that resolves outside `docs/`, `book/`, or `notes/`.
- File-name regex: only `[A-Za-z0-9_./ -]` allowed; spaces are permitted because the Obsidian vault has dirs like `System Library/`, but `;`, `$`, `|`, `()` etc. stay rejected. The hard security check is the resolved-path-startsWith-allowed-root test, not the regex.
- Size cap: 256 KB per file. Larger files return an error suggesting `search_docs` first.
- No write tools. Read-only by design. Never exposes `src/`, `tests/`, `.git/`, secrets, or env values.
- Bearer auth is opt-in but **strongly recommended** if you tunnel the server beyond localhost.

## Testing

```powershell
npx vitest run tests/mcp_context_server/server.test.ts
```
