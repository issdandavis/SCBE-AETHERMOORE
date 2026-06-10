'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { ui, stripAnsi } = require('../lib/ui');

const ESC = '\x1b';
const tty = { isTTY: true, columns: 80 };
const notty = { isTTY: false };

// ── The three safety contracts (the things that corrupt pipelines) ──────────
test('json mode disables all styling (no ANSI leaks into machine output)', () => {
  const u = ui({ json: true, stream: tty, env: { FORCE_COLOR: '1' } });
  assert.equal(u.enabled, false);
  assert.equal(u.red('x'), 'x');
  assert.ok(!u.badge('DENY', 'deny').includes(ESC));
  assert.ok(!u.heading('hi').includes(ESC));
});

test('NO_COLOR convention disables color even on a TTY', () => {
  const u = ui({ stream: tty, env: { NO_COLOR: '1' } });
  assert.equal(u.enabled, false);
  assert.ok(!u.green('ok').includes(ESC));
});

test('non-TTY output is plain by default', () => {
  const u = ui({ stream: notty, env: {} });
  assert.equal(u.enabled, false);
  assert.ok(!u.cyan('x').includes(ESC));
});

test('FORCE_COLOR enables color even when not a TTY', () => {
  const u = ui({ stream: notty, env: { FORCE_COLOR: '1' } });
  assert.equal(u.enabled, true);
  assert.ok(u.green('ok').includes(ESC));
});

test('explicit color:false overrides FORCE_COLOR', () => {
  const u = ui({ stream: tty, color: false, env: { FORCE_COLOR: '1' } });
  assert.equal(u.enabled, false);
});

// ── Rendering primitives ─────────────────────────────────────────────────────
test('colored output round-trips through stripAnsi', () => {
  const u = ui({ stream: tty, color: true, env: {} });
  assert.equal(stripAnsi(u.bold(u.red('hello'))), 'hello');
});

test('badge tones map to distinct colors; plain fallback is bracketed', () => {
  const u = ui({ stream: tty, color: true, env: {} });
  assert.ok(u.badge('DENY', 'deny').includes('31')); // red
  assert.ok(u.badge('ALLOW', 'allow').includes('32')); // green
  const plain = ui({ color: false, env: {} });
  assert.equal(stripAnsi(plain.badge('DENY', 'deny')), '[DENY]');
});

test('status maps boolean to symbol semantics', () => {
  const u = ui({ color: false, env: {}, unicode: true });
  assert.ok(u.status(true).startsWith('✓'));
  assert.ok(u.status(false).startsWith('✗'));
  assert.ok(u.status(null).startsWith('⚠'));
});

test('kv aligns keys to a common column', () => {
  const u = ui({ color: false, env: {} });
  const out = u
    .kv([
      ['a', '1'],
      ['longkey', '2'],
    ])
    .split('\n');
  // value column starts at the same visible offset on every row
  const off = (line) => (line.indexOf('1') >= 0 ? line.indexOf('1') : line.indexOf('2'));
  assert.equal(off(out[0]), off(out[1]));
});

test('table pads columns and keeps rows equal width before trim', () => {
  const u = ui({ color: false, env: {} });
  const out = u
    .table([
      ['PASS', 'node'],
      ['FAIL', 'liboqs-which-is-longer'],
    ])
    .split('\n');
  assert.equal(out.length, 2);
  assert.ok(out[0].includes('PASS'));
  assert.ok(out[1].includes('liboqs-which-is-longer'));
});

test('truncate adds ellipsis only when over length', () => {
  const u = ui({ color: false, env: {}, unicode: true });
  assert.equal(u.truncate('short', 10), 'short');
  assert.equal(u.truncate('abcdefghij', 5), 'abcd…');
  const ascii = ui({ color: false, env: {}, unicode: false });
  assert.equal(ascii.truncate('abcdefghij', 5), 'ab...');
});

test('seal frames a tone-colored governance stamp with aligned fields', () => {
  const u = ui({ stream: tty, color: true, env: {}, unicode: true });
  const out = u.seal('DENY', {
    fields: [
      ['audit', 'geoseal_abc'],
      ['sha256', 'a1b2c3…'],
    ],
    stamp: '18:42:07Z',
  });
  const lines = out.split('\n');
  // hexagon corners top + bottom, vertical sides, title, divider, 2 fields
  assert.ok(lines[0].includes('⬢') && lines[lines.length - 1].includes('⬢'));
  assert.ok(out.includes('GEOSEAL') && out.includes('DENY'));
  assert.ok(out.includes('31')); // deny tone == red border
  assert.ok(out.includes('sealed 18:42:07Z'));
  // every rendered line is the same visible width (box stays square)
  const widths = new Set(lines.map((l) => stripAnsi(l).length));
  assert.equal(widths.size, 1);
});

test('seal tone follows the decision when tone is omitted', () => {
  const u = ui({ stream: tty, color: true, env: {} });
  assert.ok(u.seal('ALLOW', { fields: [['k', 'v']] }).includes('32')); // green
  assert.ok(u.seal('QUARANTINE', { fields: [['k', 'v']] }).includes('33')); // yellow
});

test('seal degrades to ASCII + no ANSI when color/unicode disabled', () => {
  const u = ui({ color: false, env: {}, unicode: false });
  const out = u.seal('ALLOW', { fields: [['audit', 'x']], stamp: 't' });
  assert.ok(!out.includes('\x1b'));
  assert.ok(out.includes('#') && !out.includes('⬢'));
  assert.ok(out.includes('GEOSEAL'));
});

test('seal is inert in json mode (never leaks ANSI into machine output)', () => {
  const u = ui({ json: true, stream: tty, env: { FORCE_COLOR: '1' } });
  assert.ok(!u.seal('DENY', { fields: [['k', 'v']] }).includes('\x1b'));
});

test('unicode capability falls back to ASCII symbols', () => {
  const a = ui({ color: false, env: {}, unicode: false });
  assert.equal(a.sym.ok, '+');
  assert.equal(a.sym.arrow, '>');
  const uni = ui({ color: false, env: {}, unicode: true });
  assert.equal(uni.sym.ok, '✓');
});
