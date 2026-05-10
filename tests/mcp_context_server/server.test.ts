import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as path from 'path';
import * as http from 'http';
import { AddressInfo } from 'net';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const ctx = require('../../mcp_context_server/server.js');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

let server: http.Server;
let baseUrl: string;

function fetchJson(url: string, init?: RequestInit) {
  return fetch(url, init).then((r) => r.json().then((b) => ({ status: r.status, body: b })));
}

beforeEach(async () => {
  delete process.env.MCP_CONTEXT_TOKEN;
  const app = ctx.buildApp();
  await new Promise<void>((resolve) => {
    server = app.listen(0, '127.0.0.1', () => resolve());
  });
  const addr = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${addr.port}`;
});

afterEach(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

describe('mcp-context — health', () => {
  it('GET /health returns schema + name + version', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/health`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('mcp_context_health_v0');
    expect(body.name).toBe('scbe-context');
    expect(body.version).toMatch(/^\d+\.\d+\.\d+/);
  });
});

describe('mcp-context — path security (security boundary)', () => {
  it('isAllowedDocPath accepts docs/ paths', () => {
    expect(ctx.isAllowedDocPath('docs/SCBE_AETHERMOORE_ONE_PAGER.md')).toBe(true);
    expect(ctx.isAllowedDocPath('book/ai-governance-fundamentals/chapter-01.md')).toBe(true);
  });

  it('isAllowedDocPath rejects path traversal attempts', () => {
    expect(ctx.isAllowedDocPath('../etc/passwd')).toBe(false);
    expect(ctx.isAllowedDocPath('docs/../../etc/passwd')).toBe(false);
    expect(ctx.isAllowedDocPath('..\\windows\\system32')).toBe(false);
  });

  it('isAllowedDocPath rejects paths outside docs/ and book/', () => {
    expect(ctx.isAllowedDocPath('src/harmonic/pipeline14.ts')).toBe(false);
    expect(ctx.isAllowedDocPath('package.json')).toBe(false);
    expect(ctx.isAllowedDocPath('.git/config')).toBe(false);
  });

  it('isAllowedDocPath rejects paths with shell metacharacters', () => {
    expect(ctx.isAllowedDocPath('docs/file;rm.md')).toBe(false);
    expect(ctx.isAllowedDocPath('docs/file$(whoami).md')).toBe(false);
    expect(ctx.isAllowedDocPath('docs/file with space.md')).toBe(false);
    expect(ctx.isAllowedDocPath('docs/file|pipe.md')).toBe(false);
  });

  it('readDocStrict throws on paths outside allowed roots', () => {
    expect(() => ctx.readDocStrict('package.json')).toThrow(/not in allowed/);
    expect(() => ctx.readDocStrict('../etc/passwd')).toThrow();
  });

  it('readDocStrict throws on traversal attempts', () => {
    expect(() => ctx.readDocStrict('docs/../package.json')).toThrow();
  });
});

describe('mcp-context — listing + reading + searching', () => {
  it('listMarkdownFiles returns relative paths under docs/', () => {
    const files = ctx.listMarkdownFiles(path.join(REPO_ROOT, 'docs'));
    expect(Array.isArray(files)).toBe(true);
    expect(files.length).toBeGreaterThan(0);
    for (const f of files) {
      expect(f.startsWith('docs/')).toBe(true);
      expect(f.endsWith('.md') || f.endsWith('.mdx')).toBe(true);
    }
  });

  it('readDocStrict reads a known doc and returns metadata', () => {
    const doc = ctx.readDocStrict('docs/SCBE_AETHERMOORE_ONE_PAGER.md');
    expect(doc.path).toBe('docs/SCBE_AETHERMOORE_ONE_PAGER.md');
    expect(typeof doc.content).toBe('string');
    expect(doc.bytes).toBeGreaterThan(0);
    expect(doc.modified).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(doc.content).toMatch(/SCBE-AETHERMOORE/);
  });

  it('searchDocs finds a known string with snippet', () => {
    const hits = ctx.searchDocs('Poincare', 5);
    expect(Array.isArray(hits)).toBe(true);
    expect(hits.length).toBeGreaterThan(0);
    for (const h of hits) {
      expect(h.path).toMatch(/\.(md|mdx)$/);
      expect(typeof h.offset).toBe('number');
      expect(typeof h.snippet).toBe('string');
      expect(h.snippet.toLowerCase()).toContain('poincare');
    }
  });

  it('searchDocs throws on too-short query', () => {
    expect(() => ctx.searchDocs('a', 5)).toThrow(/>= 2/);
    expect(() => ctx.searchDocs('', 5)).toThrow();
  });

  it('searchDocs respects limit', () => {
    const hits = ctx.searchDocs('the', 3);
    expect(hits.length).toBeLessThanOrEqual(3);
  });
});

describe('mcp-context — HTTP method enforcement', () => {
  it('GET /mcp returns 405', async () => {
    const r = await fetch(`${baseUrl}/mcp`);
    expect(r.status).toBe(405);
  });

  it('DELETE /mcp returns 405', async () => {
    const r = await fetch(`${baseUrl}/mcp`, { method: 'DELETE' });
    expect(r.status).toBe(405);
  });
});

describe('mcp-context — bearer auth (when MCP_CONTEXT_TOKEN set)', () => {
  let altServer: http.Server;
  let altUrl: string;

  beforeEach(async () => {
    process.env.MCP_CONTEXT_TOKEN = 'test-token-xyz';
    // Re-require the module to pick up the new env. Express middleware
    // binds at app build time, so we need a fresh app.
    delete require.cache[require.resolve('../../mcp_context_server/server.js')];
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const ctxAuth = require('../../mcp_context_server/server.js');
    const app = ctxAuth.buildApp();
    await new Promise<void>((resolve) => {
      altServer = app.listen(0, '127.0.0.1', () => resolve());
    });
    const addr = altServer.address() as AddressInfo;
    altUrl = `http://127.0.0.1:${addr.port}`;
  });

  afterEach(async () => {
    await new Promise<void>((resolve) => altServer.close(() => resolve()));
    delete process.env.MCP_CONTEXT_TOKEN;
    delete require.cache[require.resolve('../../mcp_context_server/server.js')];
  });

  it('POST /mcp without token returns 401', async () => {
    const r = await fetch(`${altUrl}/mcp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {} }),
    });
    expect(r.status).toBe(401);
  });

  it('POST /mcp with wrong token returns 401', async () => {
    const r = await fetch(`${altUrl}/mcp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer WRONG' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {} }),
    });
    expect(r.status).toBe(401);
  });

  it('GET /health works without token (health is open)', async () => {
    const r = await fetch(`${altUrl}/health`);
    expect(r.status).toBe(200);
    const body = await r.json();
    expect(body.auth_required).toBe(true);
  });
});
