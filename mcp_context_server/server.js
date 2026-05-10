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
// `read_doc` with anything outside these roots is rejected.
const DOC_ROOTS = [path.join(REPO_ROOT, 'docs'), path.join(REPO_ROOT, 'book')];

const SAFE_NAME_RE = /^[A-Za-z0-9_./-]+$/;

function listMarkdownFiles(root) {
  const out = [];
  if (!fs.existsSync(root)) return out;
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
  return out.sort();
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
  const full = path.resolve(REPO_ROOT, rel);
  if (!fs.existsSync(full) || !fs.statSync(full).isFile()) {
    throw new Error(`doc not found: ${rel}`);
  }
  const stat = fs.statSync(full);
  if (stat.size > MAX_DOC_BYTES) {
    throw new Error(
      `doc too large (${stat.size} bytes; cap is ${MAX_DOC_BYTES}); fetch a section instead`
    );
  }
  return {
    path: rel,
    bytes: stat.size,
    modified: stat.mtime.toISOString(),
    content: fs.readFileSync(full, 'utf8'),
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
      const full = path.join(REPO_ROOT, rel);
      let body;
      try {
        body = fs.readFileSync(full, 'utf8');
      } catch (_err) {
        continue;
      }
      const idx = body.toLowerCase().indexOf(ql);
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
      const files = [
        ...listMarkdownFiles(path.join(REPO_ROOT, 'docs')),
        ...listMarkdownFiles(path.join(REPO_ROOT, 'book')),
      ];
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
  DOC_ROOTS,
  REPO_ROOT,
  HOST,
  PORT,
};
