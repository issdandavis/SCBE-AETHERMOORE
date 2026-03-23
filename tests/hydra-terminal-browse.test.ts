import { describe, expect, it } from 'vitest';
import {
  decodeEntities,
  extractLinks,
  isBlockedHref,
  stripHtml,
} from '../external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs';

describe('hydra_terminal_browse', () => {
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
    expect(extractLinks(html, 'https://example.com/base', 10)).toEqual(['https://example.com/safe']);
  });
});
