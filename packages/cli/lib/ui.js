/**
 * @file ui.js
 * @module cli/lib/ui
 * @description Zero-dependency terminal UI kit for the scbe CLI.
 *
 * Brings everyday `scbe` output up to the bar set by modern published CLIs
 * (gh, vercel, vite, ruff, poetry): semantic color, status symbols, aligned
 * key/value summaries, simple tables, governance-tier badges, and a spinner —
 * with NO new dependencies.
 *
 * Safety contract (the things that bite CLIs):
 *   - Honors the NO_COLOR convention (https://no-color.org) and FORCE_COLOR.
 *   - Auto-disables color when the target stream is not a TTY (piped / file).
 *   - Auto-disables color in `--json` mode: a styled UI must NEVER leak ANSI
 *     bytes into machine-parsed JSON. Callers pass { json: true }.
 *   - ASCII fallback for status symbols on terminals without Unicode.
 *
 * Usage:
 *   const { ui } = require('../lib/ui');
 *   const u = ui({ json: flags.json });           // resolves color/unicode once
 *   console.log(u.heading('Doctor'));
 *   console.log(u.ok('liboqs bindings present'));
 *   console.log(u.kv([['node', 'v20.11.0'], ['platform', 'win32']]));
 *   console.log(u.badge('ALLOW', 'allow'));
 */

'use strict';

// ── Raw SGR codes (kept tiny; only what the kit uses) ───────────────────────
const SGR = {
  reset: 0,
  bold: 1,
  dim: 2,
  italic: 3,
  underline: 4,
  // foreground
  red: 31,
  green: 32,
  yellow: 33,
  blue: 34,
  magenta: 35,
  cyan: 36,
  white: 37,
  gray: 90,
  brightGreen: 92,
  brightYellow: 93,
  brightRed: 91,
};

const ANSI_RE = /\x1b\[[0-9;]*m/g;

function stripAnsi(s) {
  return String(s).replace(ANSI_RE, '');
}

/** Visible width (ignores ANSI). Good enough for ASCII + common BMP text. */
function visLen(s) {
  return stripAnsi(s).length;
}

/** Truncate to n visible chars with an ellipsis, ANSI-unaware (plain text in). */
function truncate(s, n, ellipsis = '…') {
  const str = String(s);
  if (str.length <= n) return str;
  const ell = n >= 1 ? ellipsis : '';
  return str.slice(0, Math.max(0, n - ell.length)) + ell;
}

// ── Capability detection ────────────────────────────────────────────────────
function resolveColor({ json, color, stream, env }) {
  if (json) return false; // hard rule: never colorize machine output
  if (typeof color === 'boolean') return color; // explicit override wins
  if (env.NO_COLOR !== undefined && env.NO_COLOR !== '') return false;
  if (env.FORCE_COLOR !== undefined && env.FORCE_COLOR !== '0' && env.FORCE_COLOR !== 'false') {
    return true;
  }
  return Boolean(stream && stream.isTTY);
}

function resolveUnicode({ unicode, env }) {
  if (typeof unicode === 'boolean') return unicode;
  if (process.platform !== 'win32') return true;
  // Modern Windows terminals advertise themselves; legacy conhost does not.
  return Boolean(env.WT_SESSION || env.TERM_PROGRAM || env.ConEmuTask || env.TERM);
}

const SYMBOLS_UNICODE = {
  ok: '✓',
  warn: '⚠',
  err: '✗',
  info: 'ℹ',
  bullet: '•',
  arrow: '▸',
  dot: '·',
  spinnerFrames: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
};
const SYMBOLS_ASCII = {
  ok: '+',
  warn: '!',
  err: 'x',
  info: 'i',
  bullet: '*',
  arrow: '>',
  dot: '.',
  spinnerFrames: ['|', '/', '-', '\\'],
};

/**
 * Build a UI instance with color/unicode capability resolved once.
 * @param {object} [opts]
 * @param {boolean} [opts.json]    machine-output mode -> styling fully inert
 * @param {boolean} [opts.color]   explicit color override (skips auto-detect)
 * @param {boolean} [opts.unicode] explicit unicode override
 * @param {WritableStream} [opts.stream] target stream (default process.stdout)
 */
function ui(opts = {}) {
  const env = opts.env || process.env;
  const stream = opts.stream || process.stdout;
  const enabled = resolveColor({ json: opts.json, color: opts.color, stream, env });
  const unicode = resolveUnicode({ unicode: opts.unicode, env });
  const SYM = unicode ? SYMBOLS_UNICODE : SYMBOLS_ASCII;

  const wrap = (code) => (s) => (enabled ? `\x1b[${code}m${s}\x1b[${SGR.reset}m` : String(s));

  const bold = wrap(SGR.bold);
  const dim = wrap(SGR.dim);
  const italic = wrap(SGR.italic);
  const underline = wrap(SGR.underline);
  const red = wrap(SGR.red);
  const green = wrap(SGR.green);
  const yellow = wrap(SGR.yellow);
  const blue = wrap(SGR.blue);
  const cyan = wrap(SGR.cyan);
  const magenta = wrap(SGR.magenta);
  const gray = wrap(SGR.gray);

  // ── Semantic status lines ────────────────────────────────────────────────
  const ok = (s) => `${green(SYM.ok)} ${s}`;
  const warn = (s) => `${yellow(SYM.warn)} ${s}`;
  const err = (s) => `${red(SYM.err)} ${s}`;
  const info = (s) => `${cyan(SYM.info)} ${s}`;
  const bullet = (s) => `${dim(SYM.bullet)} ${s}`;
  const arrow = (s) => `${cyan(SYM.arrow)} ${s}`;

  /** Map a boolean / pass-fail to a colored status symbol. */
  const status = (good, labels = {}) => {
    if (good === true) return ok(labels.ok || 'ok');
    if (good === false) return err(labels.err || 'fail');
    return warn(labels.warn || 'n/a');
  };

  // ── Section heading + horizontal rule (colorized version of the existing
  //    box-divider style the CLI already uses) ────────────────────────────────
  const RULE_CH = unicode ? '─' : '-';
  const rule = (width) => {
    const w = width || Math.min(stream.columns || 79, 79);
    return dim(RULE_CH.repeat(w));
  };
  const heading = (title, width) => {
    const w = width || Math.min(stream.columns || 79, 79);
    return [rule(w), `  ${bold(cyan(String(title).toUpperCase()))}`, rule(w)].join('\n');
  };

  // ── Aligned key/value summary ─────────────────────────────────────────────
  const kv = (pairs, { indent = 2, gap = 2, keyColor = gray } = {}) => {
    const rows = pairs.filter(Boolean);
    const keyW = rows.reduce((m, [k]) => Math.max(m, visLen(String(k))), 0);
    const pad = ' '.repeat(indent);
    return rows
      .map(([k, v]) => {
        const key = String(k);
        const fill = ' '.repeat(keyW - visLen(key) + gap);
        return `${pad}${keyColor(key)}${fill}${v == null ? '' : String(v)}`;
      })
      .join('\n');
  };

  // ── Simple left-aligned table with a dim header ───────────────────────────
  const table = (rows, { head = null, indent = 2, gap = 2 } = {}) => {
    const body = rows.map((r) => r.map((c) => (c == null ? '' : String(c))));
    const cols = body.reduce((m, r) => Math.max(m, r.length), head ? head.length : 0);
    const widths = [];
    for (let c = 0; c < cols; c += 1) {
      let w = head ? visLen(String(head[c] || '')) : 0;
      for (const r of body) w = Math.max(w, visLen(r[c] || ''));
      widths[c] = w;
    }
    const pad = ' '.repeat(indent);
    const sep = ' '.repeat(gap);
    const line = (cells, styler) =>
      pad +
      cells
        .map((cell, c) => {
          const text = cell || '';
          const fill = ' '.repeat(widths[c] - visLen(text));
          return (styler ? styler(text) : text) + fill;
        })
        .join(sep)
        .replace(/\s+$/, '');
    const out = [];
    if (head) out.push(line(head, (t) => dim(bold(t))));
    for (const r of body) out.push(line(r));
    return out.join('\n');
  };

  // ── Governance-tier / state badge ─────────────────────────────────────────
  const TONE = {
    allow: green,
    ok: green,
    pass: green,
    quarantine: yellow,
    warn: yellow,
    escalate: magenta,
    deny: red,
    fail: red,
    error: red,
    info: cyan,
    neutral: gray,
  };
  const badge = (text, tone = 'neutral') => {
    const styler = TONE[String(tone).toLowerCase()] || gray;
    const label = ` ${String(text).toUpperCase()} `;
    return enabled ? bold(styler(label.replace(/ /g, ' '))) : `[${String(text).toUpperCase()}]`;
  };

  // ── Boxed summary panel ───────────────────────────────────────────────────
  const box = (lines, { title = '', pad = 1, color: bColor = gray } = {}) => {
    const arr = (Array.isArray(lines) ? lines : String(lines).split('\n')).map(String);
    const inner = arr.reduce((m, l) => Math.max(m, visLen(l)), visLen(title));
    const w = inner + pad * 2;
    const tl = unicode ? '╭' : '+';
    const tr = unicode ? '╮' : '+';
    const bl = unicode ? '╰' : '+';
    const br = unicode ? '╯' : '+';
    const hz = unicode ? '─' : '-';
    const vt = unicode ? '│' : '|';
    const top = title
      ? `${tl}${hz} ${bold(title)} ${hz.repeat(Math.max(0, w - visLen(title) - 3))}${tr}`
      : `${tl}${hz.repeat(w)}${tr}`;
    const padS = ' '.repeat(pad);
    const mid = arr.map(
      (l) => `${bColor(vt)}${padS}${l}${' '.repeat(inner - visLen(l))}${padS}${bColor(vt)}`
    );
    const bot = `${bl}${hz.repeat(w)}${br}`;
    return [bColor(top), ...mid, bColor(bot)].join('\n');
  };

  // ── Spinner (no-op-friendly; silent when not a TTY / json) ─────────────────
  const spinner = (label = '') => {
    let i = 0;
    let timer = null;
    const active = enabled && Boolean(stream.isTTY);
    const frames = SYM.spinnerFrames;
    return {
      start() {
        if (!active) {
          if (label) stream.write(`${label}\n`);
          return this;
        }
        timer = setInterval(() => {
          stream.write(`\r${cyan(frames[(i = (i + 1) % frames.length)])} ${label}`);
        }, 80);
        if (timer.unref) timer.unref();
        return this;
      },
      stop(finalLine) {
        if (timer) clearInterval(timer);
        if (active) stream.write('\r\x1b[K');
        if (finalLine) stream.write(`${finalLine}\n`);
        return this;
      },
    };
  };

  return {
    enabled,
    unicode,
    sym: SYM,
    stripAnsi,
    visLen,
    truncate: (s, n) => truncate(s, n, unicode ? '…' : '...'),
    // styles
    bold,
    dim,
    italic,
    underline,
    red,
    green,
    yellow,
    blue,
    cyan,
    magenta,
    gray,
    // semantics
    ok,
    warn,
    err,
    info,
    bullet,
    arrow,
    status,
    // structure
    heading,
    rule,
    kv,
    table,
    badge,
    box,
    spinner,
  };
}

module.exports = { ui, stripAnsi, visLen };
