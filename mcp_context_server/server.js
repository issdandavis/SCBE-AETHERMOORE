'use strict';

/**
 * SCBE-AETHERMOORE MCP Context Server (Streamable HTTP)
 *
 * Exposes the curated docs/ and book/ trees as an MCP server so any
 * MCP client (Claude Desktop, Claude.ai Custom Connectors, Cursor,
 * Continue, etc.) can pull repo context in the structured form the
 * docs already define.
 *
 * Transport: Streamable HTTP (one POST /mcp endpoint, stateless).
 * Bind:      127.0.0.1:5719 by default. Override with MCP_CONTEXT_PORT.
 * Auth:      Optional bearer token via MCP_CONTEXT_TOKEN env var. If
 *            unset, the server is open (only safe on localhost).
 *
 * Surfaces (tools):
 *   list_docs(prefix?)       — list .md files under the curated tree
 *   read_doc(path)           — return one file's contents (path-jailed)
 *   search_docs(query, limit?) — case-insensitive substring search
 *   get_one_pager()          — return the canonical project briefing
 *
 * Hard scope: only docs/ and book/. No src/, no tests/, no secrets.
 */

const express = require('express');
const fs = require('fs');
const path = require('path');
const { z } = require('zod');
const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');
const {
  StreamableHTTPServerTransport,
} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');

const REPO_ROOT = path.resolve(__dirname, '..');
const PORT = Number(process.env.MCP_CONTEXT_PORT || 5719);
const HOST = process.env.MCP_CONTEXT_HOST || '127.0.0.1';
const BEARER = process.env.MCP_CONTEXT_TOKEN || null;
const MAX_DOC_BYTES = 256 * 1024; // 256 KB per doc

// The allowed-roots list is the security boundary. A request for
// `read_doc` with anything outside these roots is rejected. `notes/` is the
// Obsidian vault — exposing the full thing was an explicit user request.
const DOC_ROOTS = [
  path.join(REPO_ROOT, 'docs'),
  path.join(REPO_ROOT, 'book'),
  path.join(REPO_ROOT, 'notes'),
];

// Spaces allowed because the Obsidian vault has dirs like "System Library/".
// Shell metacharacters (`;$|()` etc.) stay rejected — we never shell out, but
// it's still a cheap defense-in-depth filter.
const SAFE_NAME_RE = /^[A-Za-z0-9_./ -]+$/;

// Listing cache: { root => { mtime_ns: dirMtimeMs, files: string[], cached_at: ms } }
// Invalidated when any directory in the root subtree has a newer mtime than the
// recorded `dirMtimeMs`. TTL keeps us from stat-walking on every call when the
// tree is stable.
const LISTING_TTL_MS = 5000;
const _listingCache = new Map();

// Content cache: { rel => { mtimeMs, size, body } }. Invalidated by mtime.
// Capped by entry count to bound memory on long-lived processes.
const CONTENT_CACHE_MAX = 512;
const _contentCache = new Map();

function _rootMtimeFingerprint(root) {
  // Cheap fingerprint: max mtime across the top of the subtree. We don't
  // walk every leaf — directory mtimes change when files are added/removed,
  // so root-level + one nested level is enough to invalidate on edits.
  if (!fs.existsSync(root)) return 0;
  let max = fs.statSync(root).mtimeMs;
  try {
    for (const e of fs.readdirSync(root, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      if (e.name.startsWith('.') || e.name === 'node_modules') continue;
      try {
        const m = fs.statSync(path.join(root, e.name)).mtimeMs;
        if (m > max) max = m;
      } catch (_err) {
        /* skip */
      }
    }
  } catch (_err) {
    /* skip */
  }
  return max;
}

function listMarkdownFiles(root) {
  const now = Date.now();
  const cached = _listingCache.get(root);
  if (cached && now - cached.cached_at < LISTING_TTL_MS) {
    const fp = _rootMtimeFingerprint(root);
    if (fp === cached.fingerprint) return cached.files;
  }

  const out = [];
  if (!fs.existsSync(root)) {
    _listingCache.set(root, { fingerprint: 0, files: out, cached_at: now });
    return out;
  }
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch (_err) {
      continue;
    }
    for (const e of entries) {
      const full = path.join(current, e.name);
      if (e.isDirectory()) {
        // Skip dot-dirs and node_modules to keep the listing clean.
        if (e.name.startsWith('.') || e.name === 'node_modules') continue;
        stack.push(full);
      } else if (e.isFile() && /\.(md|mdx)$/i.test(e.name)) {
        out.push(path.relative(REPO_ROOT, full).replace(/\\/g, '/'));
      }
    }
  }
  out.sort();
  _listingCache.set(root, {
    fingerprint: _rootMtimeFingerprint(root),
    files: out,
    cached_at: now,
  });
  return out;
}

function _readCached(rel) {
  const full = path.resolve(REPO_ROOT, rel);
  let stat;
  try {
    stat = fs.statSync(full);
  } catch (_err) {
    return null;
  }
  if (!stat.isFile()) return null;
  const cached = _contentCache.get(rel);
  if (cached && cached.mtimeMs === stat.mtimeMs && cached.size === stat.size) {
    return { stat, body: cached.body, bodyLower: cached.bodyLower };
  }
  let body;
  try {
    body = fs.readFileSync(full, 'utf8');
  } catch (_err) {
    return null;
  }
  if (_contentCache.size >= CONTENT_CACHE_MAX) {
    // Drop oldest insertion-order entry — Map preserves insertion order.
    const firstKey = _contentCache.keys().next().value;
    if (firstKey !== undefined) _contentCache.delete(firstKey);
  }
  const bodyLower = body.toLowerCase();
  _contentCache.set(rel, { mtimeMs: stat.mtimeMs, size: stat.size, body, bodyLower });
  return { stat, body, bodyLower };
}

function _resetCachesForTests() {
  _listingCache.clear();
  _contentCache.clear();
}

function isAllowedDocPath(rel) {
  if (!SAFE_NAME_RE.test(rel)) return false;
  if (rel.includes('..')) return false;
  // Must resolve under one of the DOC_ROOTS.
  const resolved = path.resolve(REPO_ROOT, rel);
  return DOC_ROOTS.some((root) => resolved === root || resolved.startsWith(root + path.sep));
}

function readDocStrict(rel) {
  if (!isAllowedDocPath(rel)) {
    throw new Error(`path not in allowed docs roots: ${rel}`);
  }
  const cached = _readCached(rel);
  if (!cached) {
    throw new Error(`doc not found: ${rel}`);
  }
  const { stat, body } = cached;
  if (stat.size > MAX_DOC_BYTES) {
    throw new Error(
      `doc too large (${stat.size} bytes; cap is ${MAX_DOC_BYTES}); fetch a section instead`
    );
  }
  return {
    path: rel,
    bytes: stat.size,
    modified: stat.mtime.toISOString(),
    content: body,
  };
}

function searchDocs(query, limit = 25) {
  if (!query || query.length < 2) {
    throw new Error('query must be >= 2 characters');
  }
  const ql = query.toLowerCase();
  const hits = [];
  for (const root of DOC_ROOTS) {
    for (const rel of listMarkdownFiles(root)) {
      const cached = _readCached(rel);
      if (!cached) continue;
      const { body, bodyLower } = cached;
      const idx = bodyLower.indexOf(ql);
      if (idx === -1) continue;
      const start = Math.max(0, idx - 80);
      const end = Math.min(body.length, idx + 80 + ql.length);
      hits.push({
        path: rel,
        offset: idx,
        snippet: body.slice(start, end).replace(/\s+/g, ' ').trim(),
      });
      if (hits.length >= limit) return hits;
    }
  }
  return hits;
}

function buildMcpServer() {
  const server = new McpServer(
    {
      name: 'scbe-context',
      version: '0.1.0',
    },
    {
      capabilities: { tools: {}, logging: {} },
    }
  );

  server.registerTool(
    'list_docs',
    {
      description:
        'List Markdown files in the curated docs/ and book/ trees. Optional prefix filters by path.',
      inputSchema: {
        prefix: z.string().optional().describe('Optional path prefix filter (e.g. "docs/specs/").'),
      },
    },
    async ({ prefix }) => {
      const files = DOC_ROOTS.flatMap((root) => listMarkdownFiles(root));
      const filtered = prefix ? files.filter((f) => f.startsWith(prefix)) : files;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ count: filtered.length, files: filtered }, null, 2),
          },
        ],
      };
    }
  );

  server.registerTool(
    'read_doc',
    {
      description:
        'Read one Markdown file by repo-relative path. Path must resolve under docs/ or book/.',
      inputSchema: {
        path: z.string().describe('Repo-relative path, e.g. "docs/SCBE_AETHERMOORE_ONE_PAGER.md".'),
      },
    },
    async ({ path: docPath }) => {
      try {
        const doc = readDocStrict(docPath);
        return { content: [{ type: 'text', text: JSON.stringify(doc, null, 2) }] };
      } catch (err) {
        return {
          isError: true,
          content: [{ type: 'text', text: `error: ${err.message}` }],
        };
      }
    }
  );

  server.registerTool(
    'search_docs',
    {
      description:
        'Case-insensitive substring search across the curated docs/ and book/ trees. Returns up to N hits with a snippet around each match.',
      inputSchema: {
        query: z.string().min(2).describe('Search string (>=2 chars).'),
        limit: z.number().int().min(1).max(100).default(25).describe('Max hits.'),
      },
    },
    async ({ query, limit }) => {
      try {
        const hits = searchDocs(query, limit);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ query, count: hits.length, hits }, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          isError: true,
          content: [{ type: 'text', text: `error: ${err.message}` }],
        };
      }
    }
  );

  server.registerTool(
    'get_one_pager',
    {
      description:
        'Return the canonical SCBE-AETHERMOORE one-pager (docs/SCBE_AETHERMOORE_ONE_PAGER.md). Best place to start.',
      inputSchema: {},
    },
    async () => {
      try {
        const doc = readDocStrict('docs/SCBE_AETHERMOORE_ONE_PAGER.md');
        return { content: [{ type: 'text', text: doc.content }] };
      } catch (err) {
        return {
          isError: true,
          content: [{ type: 'text', text: `error: ${err.message}` }],
        };
      }
    }
  );

  return server;
}

function bearerAuthMiddleware(req, res, next) {
  if (!BEARER) return next();
  const auth = req.headers.authorization || '';
  if (auth === `Bearer ${BEARER}`) return next();
  return res.status(401).json({
    jsonrpc: '2.0',
    error: { code: -32001, message: 'unauthorized' },
    id: null,
  });
}

function buildApp() {
  const app = express();
  app.use(express.json({ limit: '256kb' }));

  app.get('/health', (_req, res) => {
    res.json({
      ok: true,
      schema: 'mcp_context_health_v0',
      name: 'scbe-context',
      version: '0.1.0',
      auth_required: Boolean(BEARER),
    });
  });

  app.post('/mcp', bearerAuthMiddleware, async (req, res) => {
    let server;
    try {
      server = buildMcpServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined, // stateless — one server per request
      });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
      res.on('close', () => {
        try {
          transport.close();
        } catch (_err) {
          /* swallow */
        }
        try {
          server.close();
        } catch (_err) {
          /* swallow */
        }
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[mcp-context] error handling /mcp:', err);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: '2.0',
          error: { code: -32603, message: 'internal server error' },
          id: null,
        });
      }
      try {
        if (server) server.close();
      } catch (_err) {
        /* swallow */
      }
    }
  });

  // GET/DELETE on /mcp aren't supported by the stateless transport.
  app.get('/mcp', (_req, res) => {
    res.status(405).json({
      jsonrpc: '2.0',
      error: { code: -32000, message: 'method not allowed' },
      id: null,
    });
  });
  app.delete('/mcp', (_req, res) => {
    res.status(405).json({
      jsonrpc: '2.0',
      error: { code: -32000, message: 'method not allowed' },
      id: null,
    });
  });

  return app;
}

function main() {
  const app = buildApp();
  const server = app.listen(PORT, HOST, () => {
    // eslint-disable-next-line no-console
    console.log(`SCBE MCP Context Server — http://${HOST}:${PORT}/mcp`);
    // eslint-disable-next-line no-console
    console.log(
      `Auth: ${BEARER ? 'Bearer token required (MCP_CONTEXT_TOKEN set)' : 'OPEN (no token; localhost only)'}`
    );
    // eslint-disable-next-line no-console
    console.log(`Docs roots: ${DOC_ROOTS.map((r) => path.relative(REPO_ROOT, r)).join(', ')}`);
  });
  return server;
}

if (require.main === module) {
  main();
}

module.exports = {
  buildApp,
  buildMcpServer,
  listMarkdownFiles,
  isAllowedDocPath,
  readDocStrict,
  searchDocs,
  _resetCachesForTests,
  DOC_ROOTS,
  REPO_ROOT,
  HOST,
  PORT,
};
