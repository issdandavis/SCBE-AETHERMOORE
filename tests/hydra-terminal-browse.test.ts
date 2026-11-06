import { describe, expect, it } from 'vitest';
import { execFile } from 'node:child_process';
import { mkdtemp, readFile, rmdir, unlink } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import {
  decodeEntities,
  extractLinks,
  isBlockedHref,
  stripHtml,
} from '../scripts/hydra/hydra_terminal_browse.mjs';

describe('hydra_terminal_browse', () => {
  it('runs the tracked CLI and writes the fetched evidence', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'hydra-evidence-'));
    const output = join(directory, 'page.json');
    const server = createServer((_request, response) => {
      response.writeHead(200, { 'Content-Type': 'text/html' });
      response.end(
        '<title>Clay fixture</title><p>Hello Clay.</p>' +
          '<script>hiddenPayload()</script><a href="/safe">Read</a>' +
          '<a href="javascript:alert(1)">Blocked</a>'
      );
    });
    try {
      await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
      });
      const address = server.address();
      if (!address || typeof address === 'string') throw new Error('Missing fixture port');
      const url = `http://127.0.0.1:${address.port}/`;
      const script = fileURLToPath(
        new URL('../scripts/hydra/hydra_terminal_browse.mjs', import.meta.url)
      );
      const { stdout } = await promisify(execFile)(
        process.execPath,
        [script, '--url', url, '--out', output],
        { timeout: 10000 }
      );
      const receipt = JSON.parse(stdout);
      expect(JSON.parse(await readFile(output, 'utf8'))).toEqual(receipt);
      expect(receipt.status).toBe(200);
      expect(receipt.title).toBe('Clay fixture');
      expect(receipt.text_excerpt).toContain('Hello Clay.');
      expect(receipt.text_excerpt).not.toContain('hiddenPayload');
      expect(receipt.links).toEqual([`${url}safe`]);
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
      await unlink(output).catch((error) => {
        if (error.code !== 'ENOENT') throw error;
      });
      await rmdir(directory);
    }
  }, 15000);

  it('decodes ampersands last to avoid double unescaping', () => {
    expect(decodeEntities('&amp;quot;')).toBe('&quot;');
    expect(decodeEntities('&lt;safe&gt;')).toBe('<safe>');
  });

  it('strips blocked elements even with permissive closing tags', () => {
    const html = `
      <div>Keep</div>
      <script>alert('x')</script foo="bar">
      <style>body { color: red; }</style media="all">
      <noscript>fallback</noscript bogus>
      <p>After</p>
    `;

    expect(stripHtml(html)).toBe('Keep After');
  });

  it('rejects executable link schemes during extraction', () => {
    const html = `
      <a href="javascript:alert(1)">bad-js</a>
      <a href="data:text/html,<script>alert(1)</script>">bad-data</a>
      <a href="vbscript:msgbox(1)">bad-vbs</a>
      <a href="/safe">safe</a>
    `;

    expect(isBlockedHref('javascript:alert(1)')).toBe(true);
    expect(isBlockedHref('data:text/html,<p>x</p>')).toBe(true);
    expect(isBlockedHref('vbscript:msgbox(1)')).toBe(true);
    expect(extractLinks(html, 'https://example.com/base', 10)).toEqual([
      'https://example.com/safe',
    ]);
  });
});
