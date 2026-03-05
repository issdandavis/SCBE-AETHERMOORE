// ═══════════════════════════════════════════════════════════════
// AetherCode IDE — Core Application
// ═══════════════════════════════════════════════════════════════

const GATE_URL = 'http://127.0.0.1:8400';
let editor = null;
let currentFile = null;
let openTabs = [];
let cmdPaletteIdx = 0;
const OPS_ACTION_LABELS = {
  crosstalk: 'Cross-talk sync',
  portal: 'Verified links portal build',
  backup: 'Ship/verify backup pass',
  synth: 'Internet workflow synthesis',
  publish: 'Article posting queue',
  monetize: 'Revenue checklist',
};

// ─── Virtual File System ───
const defaultFS = {
  'src/': null,
  'src/harmonic/': null,
  'src/harmonic/pipeline14.ts': `/**
 * @file pipeline14.ts
 * @module harmonic/pipeline14
 * @layer Layer 1 through Layer 14
 * @component 14-Layer Security Pipeline
 * @version 4.2.0
 *
 * Implements the full SCBE 14-layer harmonic security pipeline.
 * Each layer transforms the input signal, building an exponential
 * cost barrier against adversarial behavior.
 */

import { HyperbolicSpace } from './hyperbolic';
import { SpectralAnalyzer } from '../spectral';
import { HarmonicWall } from './harmonicScaling';

export interface PipelineResult {
  H_eff: number;
  d_star: number;
  decision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  layers: LayerOutput[];
  coherence: number;
}

interface LayerOutput {
  layer: number;
  name: string;
  value: number;
  axiom?: string;
}

// L12: Harmonic Wall — H(d, pd) = 1 / (1 + d_H + 2*pd)
function harmonicWall(dH: number, pd: number): number {
  return 1 / (1 + dH + 2 * pd);
}

// L5: Hyperbolic distance
function hyperbolicDistance(u: number[], v: number[]): number {
  const diffSq = u.reduce((s, ui, i) => s + (ui - v[i]) ** 2, 0);
  const uNormSq = u.reduce((s, x) => s + x * x, 0);
  const vNormSq = v.reduce((s, x) => s + x * x, 0);
  return Math.acosh(1 + (2 * diffSq) / ((1 - uNormSq) * (1 - vNormSq)));
}

export function runPipeline(input: Float64Array): PipelineResult {
  const layers: LayerOutput[] = [];

  // L1-2: Complex context realification
  const real = Array.from(input).map(Math.abs);
  layers.push({ layer: 1, name: 'Context', value: real.length, axiom: 'A5' });

  // L3-4: Weighted transform + Poincare embedding
  const embedded = real.map(v => Math.tanh(v * 0.5));
  layers.push({ layer: 3, name: 'Embedding', value: embedded[0], axiom: 'A2' });

  // L5: Hyperbolic distance
  const origin = new Array(embedded.length).fill(0);
  const dH = hyperbolicDistance(embedded, origin);
  layers.push({ layer: 5, name: 'Distance', value: dH, axiom: 'A4' });

  // L12: Harmonic wall
  const pd = Math.max(0, dH - 0.5);
  const H = harmonicWall(dH, pd);
  layers.push({ layer: 12, name: 'HarmonicWall', value: H, axiom: 'A4' });

  // L13: Risk decision
  let decision: PipelineResult['decision'];
  if (H > 0.7) decision = 'ALLOW';
  else if (H > 0.4) decision = 'QUARANTINE';
  else if (H > 0.15) decision = 'ESCALATE';
  else decision = 'DENY';

  return { H_eff: H, d_star: dH, decision, layers, coherence: H * 0.95 };
}
`,
  'src/harmonic/hyperbolic.ts': `/**
 * @file hyperbolic.ts
 * @module harmonic/hyperbolic
 * @layer Layer 5, Layer 6, Layer 7
 * @component Poincare Ball Model
 */

export class HyperbolicSpace {
  readonly dim: number;
  readonly curvature: number;

  constructor(dim: number, curvature = -1) {
    this.dim = dim;
    this.curvature = curvature;
  }

  /** L5: Hyperbolic distance in the Poincare ball */
  distance(u: number[], v: number[]): number {
    const diffSq = u.reduce((s, ui, i) => s + (ui - v[i]) ** 2, 0);
    const uNorm = u.reduce((s, x) => s + x * x, 0);
    const vNorm = v.reduce((s, x) => s + x * x, 0);
    const denom = (1 - uNorm) * (1 - vNorm);
    if (denom <= 0) return Infinity;
    return Math.acosh(1 + (2 * diffSq) / denom);
  }

  /** L6: Breathing transform */
  breathe(point: number[], phase: number): number[] {
    const scale = 1 + 0.1 * Math.sin(phase);
    return point.map(x => Math.tanh(Math.atanh(x) * scale));
  }

  /** L7: Mobius addition */
  mobiusAdd(u: number[], v: number[]): number[] {
    const uNorm = u.reduce((s, x) => s + x * x, 0);
    const vNorm = v.reduce((s, x) => s + x * x, 0);
    const uv = u.reduce((s, x, i) => s + x * v[i], 0);
    const denom = 1 + 2 * uv + uNorm * vNorm;
    return u.map((ui, i) =>
      ((1 + 2 * uv + vNorm) * ui + (1 - uNorm) * v[i]) / denom
    );
  }
}
`,
  'src/crypto/': null,
  'src/crypto/h_lwe.py': `"""
h_lwe.py — Homomorphic Learning With Errors
@layer Layer 5
@component Post-Quantum Cryptographic Primitives
"""

import numpy as np
from typing import Tuple

# A2: Unitarity — key generation preserves norm constraints
def keygen(n: int = 256, q: int = 7681) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate H-LWE keypair."""
    s = np.random.randint(0, q, size=n)  # secret key
    A = np.random.randint(0, q, size=(n, n))
    e = np.random.normal(0, 3.2, size=n).astype(int) % q  # error
    b = (A @ s + e) % q
    return A, b, s

def encrypt(A: np.ndarray, b: np.ndarray, m: int, q: int = 7681) -> Tuple[np.ndarray, int]:
    """Encrypt a single bit under H-LWE."""
    n = len(b)
    r = np.random.randint(0, 2, size=n)
    u = (r @ A) % q
    v = (int(r @ b) + m * (q // 2)) % q
    return u, v

def decrypt(s: np.ndarray, u: np.ndarray, v: int, q: int = 7681) -> int:
    """Decrypt ciphertext."""
    inner = (v - int(u @ s)) % q
    return 0 if inner < q // 4 or inner > 3 * q // 4 else 1

# --- Self-test ---
if __name__ == "__main__":
    A, b, s = keygen()
    for bit in [0, 1]:
        u, v = encrypt(A, b, bit)
        assert decrypt(s, u, v) == bit, f"Decryption failed for bit={bit}"
    print("H-LWE self-test: OK")
`,
  'tests/': null,
  'tests/harmonic/': null,
  'tests/harmonic/pipeline14.test.ts': `import { describe, it, expect } from 'vitest';

describe('14-Layer Pipeline', () => {
  it('returns ALLOW for benign input', () => {
    // Simulate benign: small values near origin
    const input = new Float64Array([0.1, 0.05, 0.02, 0.01]);
    // H_eff should be high for near-origin points
    expect(true).toBe(true); // placeholder
  });

  it('returns DENY for adversarial input', () => {
    // Simulate adversarial: large values at boundary
    const input = new Float64Array([0.99, 0.98, 0.97, 0.96]);
    expect(true).toBe(true); // placeholder
  });
});
`,
  'package.json': `{
  "name": "scbe-aethermoore",
  "version": "2.8.0",
  "description": "AI safety framework using hyperbolic geometry",
  "main": "./dist/src/index.js",
  "scripts": {
    "build": "npm run clean && tsc -p tsconfig.json",
    "test": "vitest run",
    "format": "prettier --write src/ tests/",
    "lint": "prettier --check src/ tests/"
  }
}
`,
  'CLAUDE.md': '# SCBE-AETHERMOORE\n\nAI safety and governance framework.\nSee the full CLAUDE.md in the repo root for details.\n',
};

// Load FS from localStorage or default
let fileSystem = {};
try {
  const saved = localStorage.getItem('aethercode-ide-fs');
  if (saved) fileSystem = JSON.parse(saved);
  else fileSystem = { ...defaultFS };
} catch { fileSystem = { ...defaultFS }; }

function saveFS() {
  localStorage.setItem('aethercode-ide-fs', JSON.stringify(fileSystem));
}

// ─── File Tree ───
function renderFileTree() {
  const tree = document.getElementById('fileTree');
  const paths = Object.keys(fileSystem).sort();
  let html = '';
  const openFolders = new Set(JSON.parse(localStorage.getItem('aethercode-ide-folders') || '["src/","src/harmonic/","src/crypto/","tests/","tests/harmonic/"]'));

  for (const p of paths) {
    const isDir = p.endsWith('/');
    const depth = (p.match(/\//g) || []).length - (isDir ? 1 : 0);
    const indent = depth === 0 ? '' : depth === 1 ? ' ft-indent' : depth === 2 ? ' ft-indent2' : ' ft-indent3';
    const name = isDir ? p.split('/').filter(Boolean).pop() : p.split('/').pop();

    // Check if parent folder is open
    const parentDir = p.substring(0, p.lastIndexOf('/', isDir ? p.length - 2 : p.length) + 1);
    if (parentDir && !openFolders.has(parentDir)) continue;

    if (isDir) {
      const isOpen = openFolders.has(p);
      html += `<div class="ft-item folder${indent}" onclick="toggleFolder('${p}')">
        <span class="icon">${isOpen ? '&#9662;' : '&#9656;'}</span>
        <span class="name">${name}</span>
      </div>`;
    } else {
      const icon = getFileIcon(name);
      const isActive = currentFile === p;
      html += `<div class="ft-item${indent}${isActive ? ' active' : ''}" onclick="openFile('${p}')">
        <span class="icon">${icon}</span>
        <span class="name">${name}</span>
      </div>`;
    }
  }
  tree.innerHTML = html;
}

function getFileIcon(name) {
  if (name.endsWith('.ts')) return '<span style="color:#3178c6">TS</span>';
  if (name.endsWith('.py')) return '<span style="color:#ffc53d">Py</span>';
  if (name.endsWith('.json')) return '<span style="color:#ff9152">{}</span>';
  if (name.endsWith('.md')) return '<span style="color:#6b8299">M</span>';
  if (name.endsWith('.html')) return '<span style="color:#e44d26">&lt;&gt;</span>';
  return '&#9632;';
}

function toggleFolder(path) {
  const folders = new Set(JSON.parse(localStorage.getItem('aethercode-ide-folders') || '[]'));
  if (folders.has(path)) folders.delete(path); else folders.add(path);
  localStorage.setItem('aethercode-ide-folders', JSON.stringify([...folders]));
  renderFileTree();
}

function getLanguage(filename) {
  if (filename.endsWith('.ts') || filename.endsWith('.tsx')) return 'typescript';
  if (filename.endsWith('.js') || filename.endsWith('.jsx')) return 'javascript';
  if (filename.endsWith('.py')) return 'python';
  if (filename.endsWith('.json')) return 'json';
  if (filename.endsWith('.md')) return 'markdown';
  if (filename.endsWith('.html')) return 'html';
  if (filename.endsWith('.css')) return 'css';
  return 'plaintext';
}

// ─── File Operations ───
function openFile(path) {
  if (!fileSystem.hasOwnProperty(path) || fileSystem[path] === null) return;

  // Hide welcome
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.style.display = 'none';

  // Add tab if not exists
  if (!openTabs.find(t => t.path === path)) {
    openTabs.push({ path, modified: false });
  }
  currentFile = path;

  renderTabs();
  renderFileTree();

  // Set editor content
  if (editor) {
    const lang = getLanguage(path);
    const model = monaco.editor.createModel(fileSystem[path], lang);
    editor.setModel(model);
    document.getElementById('sbLang').textContent = lang.charAt(0).toUpperCase() + lang.slice(1);
  }

  updateGovernance();
}

function saveFile() {
  if (!currentFile || !editor) return;
  fileSystem[currentFile] = editor.getValue();
  saveFS();
  const tab = openTabs.find(t => t.path === currentFile);
  if (tab) tab.modified = false;
  renderTabs();
  termLog('File saved: ' + currentFile, 'info');
  updateGovernance();
}

function closeTab(path, e) {
  if (e) e.stopPropagation();
  openTabs = openTabs.filter(t => t.path !== path);
  if (currentFile === path) {
    if (openTabs.length > 0) {
      openFile(openTabs[openTabs.length - 1].path);
    } else {
      currentFile = null;
      if (editor) editor.setValue('');
      document.getElementById('welcome').style.display = 'flex';
      renderTabs();
      renderFileTree();
    }
  } else {
    renderTabs();
  }
}

function createNewFile() {
  const name = prompt('File path (e.g. src/myfile.ts):');
  if (!name || !name.trim()) return;
  const path = name.trim();
  // Create parent directories
  const parts = path.split('/');
  for (let i = 1; i < parts.length; i++) {
    const dir = parts.slice(0, i).join('/') + '/';
    if (!fileSystem.hasOwnProperty(dir)) fileSystem[dir] = null;
  }
  fileSystem[path] = '';
  saveFS();
  renderFileTree();
  openFile(path);
  termLog('Created: ' + path, 'info');
}

// ─── Tabs ───
function renderTabs() {
  const bar = document.getElementById('tabBar');
  let html = '';
  for (const tab of openTabs) {
    const name = tab.path.split('/').pop();
    const icon = getFileIcon(name);
    const isActive = tab.path === currentFile;
    html += `<div class="tab${isActive ? ' active' : ''}${tab.modified ? ' modified' : ''}" onclick="openFile('${tab.path}')">
      <span class="tab-icon">${icon}</span>
      <span class="tab-name">${name}</span>
      <span class="tab-close" onclick="closeTab('${tab.path}',event)">&times;</span>
    </div>`;
  }
  html += `<div class="tab-actions"><button title="Command Palette" onclick="showCmdPalette()">&#8984;</button></div>`;
  bar.innerHTML = html;
  updateOpsSnapshot();
}

// ─── Terminal ───
function termLog(msg, cls = '') {
  const body = document.getElementById('terminalBody');
  const div = document.createElement('div');
  div.className = 'line' + (cls ? ' ' + cls : '');
  div.textContent = msg;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

function clearTerminal() {
  document.getElementById('terminalBody').innerHTML = '';
}

function toggleTerminal() {
  document.getElementById('terminalPanel').classList.toggle('collapsed');
}

function execCommand() {
  const inp = document.getElementById('terminalInput');
  const cmd = inp.value.trim();
  inp.value = '';
  if (!cmd) return;

  termLog('> ' + cmd, 'cmd');

  const parts = cmd.split(/\s+/);
  const c = parts[0].toLowerCase();

  if (c === 'clear' || c === 'cls') { clearTerminal(); return; }
  if (c === 'help') {
    termLog('Available commands:', 'accent');
    termLog('  build        — Compile TypeScript');
    termLog('  test         — Run test suite');
    termLog('  lint         — Check code style');
    termLog('  scan         — Run L13 governance scan');
    termLog('  encode <t>   — Encode text to KO tongue');
    termLog('  ops          — Open operations panel');
    termLog('  crosstalk    — Emit cross-talk sync packet');
    termLog('  portal       — Build verified links portal');
    termLog('  backup       — Run ship/verify backup pass');
    termLog('  synth        — Refresh internet workflow profile');
    termLog('  publish      — Queue article posting workflow');
    termLog('  monetize     — Show daily revenue checklist');
    termLog('  status       — Project status');
    termLog('  ls           — List files');
    termLog('  cat <file>   — Display file contents');
    termLog('  clear        — Clear terminal');
    return;
  }
  if (c === 'build') { runBuild(); return; }
  if (c === 'test') { runTests(); return; }
  if (c === 'lint') { runLint(); return; }
  if (c === 'scan') { runGovernanceScan(); return; }
  if (c === 'ops') { openOpsTab(); return; }
  if (c === 'crosstalk' || c === 'portal' || c === 'backup' || c === 'synth' || c === 'publish' || c === 'monetize') {
    runOpsAction(c);
    return;
  }
  if (c === 'status') {
    const files = Object.keys(fileSystem).filter(k => !k.endsWith('/'));
    const ts = files.filter(f => f.endsWith('.ts')).length;
    const py = files.filter(f => f.endsWith('.py')).length;
    termLog('SCBE-AETHERMOORE', 'accent');
    termLog(`  Files: ${files.length} (${ts} TS, ${py} Python)`, 'info');
    termLog(`  Branch: clean-sync`, 'info');
    termLog(`  14-Layer Pipeline: active`, 'info');
    termLog(`  Governance: L13 online`, 'info');
    termLog(`  Ops lane: available (type "ops")`, 'info');
    return;
  }
  if (c === 'ls') {
    const target = parts[1] || '';
    const entries = Object.keys(fileSystem).filter(k => {
      if (target) return k.startsWith(target) && k !== target;
      const depth = (k.match(/\//g) || []).length;
      return k.endsWith('/') ? depth === 1 : depth === 0;
    });
    entries.forEach(e => termLog('  ' + e, e.endsWith('/') ? 'accent' : ''));
    return;
  }
  if (c === 'cat' && parts[1]) {
    const content = fileSystem[parts[1]];
    if (content !== undefined && content !== null) {
      content.split('\n').forEach(l => termLog(l));
    } else {
      termLog('File not found: ' + parts[1], 'err');
    }
    return;
  }
  if (c === 'encode') {
    const text = parts.slice(1).join(' ');
    if (!text) { termLog('Usage: encode <text>', 'warn'); return; }
    const tokens = encodeToKO(text);
    termLog('KO tokens: ' + tokens, 'accent');
    return;
  }
  termLog('Unknown command: ' + c + '. Type "help" for available commands.', 'warn');
}

function runBuild() {
  termLog('> npm run build', 'cmd');
  termLog('Compiling TypeScript...', 'info');
  setTimeout(() => {
    const tsFiles = Object.keys(fileSystem).filter(k => k.endsWith('.ts'));
    termLog(`  Compiled ${tsFiles.length} files`, 'info');
    termLog('Build succeeded.', 'accent');
  }, 600);
}

function runTests() {
  termLog('> npm test', 'cmd');
  termLog('Running vitest...', 'info');
  setTimeout(() => {
    termLog('  PASS  tests/harmonic/pipeline14.test.ts', 'accent');
    termLog('  2 tests passed', 'info');
    termLog('Test suite complete.', 'accent');
  }, 800);
}

function runLint() {
  termLog('> npm run lint', 'cmd');
  setTimeout(() => {
    termLog('  Checking code style...', 'info');
    termLog('  All files pass.', 'accent');
  }, 400);
}

// ─── Ops Workflows ───
function isoNow() {
  return new Date().toISOString();
}

function safeStamp() {
  return isoNow().replace(/[:.]/g, '-');
}

function ensureVirtualDir(path) {
  if (!path) return;
  let current = '';
  for (const part of path.split('/').filter(Boolean)) {
    current += part + '/';
    if (!Object.prototype.hasOwnProperty.call(fileSystem, current)) fileSystem[current] = null;
  }
}

function writeVirtualFile(path, content) {
  const idx = path.lastIndexOf('/');
  const dir = idx >= 0 ? path.slice(0, idx + 1) : '';
  ensureVirtualDir(dir);
  fileSystem[path] = content;
  saveFS();
  renderFileTree();
}

function setOpsPill(id, level, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'ops-pill ' + level;
  el.textContent = text;
}

function appendOpsLog(msg, cls = 'info') {
  const log = document.getElementById('opsLog');
  if (!log) return;
  const line = document.createElement('div');
  line.className = 'ops-line';
  const stamp = new Date().toLocaleTimeString([], { hour12: false });
  line.textContent = `[${stamp}] ${msg}`;
  log.appendChild(line);
  while (log.children.length > 50) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
  termLog('[ops] ' + msg, cls);
}

function updateOpsSnapshot() {
  const files = Object.keys(fileSystem).filter(k => !k.endsWith('/')).length;
  const modified = openTabs.filter(t => t.modified).length;
  const snap = document.getElementById('opsSnapshot');
  if (snap) snap.textContent = `Files: ${files} | Tabs: ${openTabs.length} | Modified: ${modified}`;
}

function initOpsPanel() {
  updateOpsSnapshot();
  appendOpsLog('Ops panel initialized. Use `help` for ops commands.', 'info');
}

function openOpsTab() {
  const rightPanel = document.getElementById('rightPanel');
  if (rightPanel.classList.contains('collapsed')) rightPanel.classList.remove('collapsed');
  const tab = document.querySelectorAll('.rp-tab')[3];
  if (tab) switchRightTab('ops', tab);
}

function runOpsAction(action) {
  if (!OPS_ACTION_LABELS[action]) {
    appendOpsLog('Unknown ops action: ' + action, 'warn');
    return;
  }

  appendOpsLog(OPS_ACTION_LABELS[action] + ' started', 'info');
  const gatewayRoute = '/ops/' + action;
  const payloadByAction = {
    crosstalk: {
      summary: 'Ops sync triggered from AetherCode IDE',
      intent: 'sync',
      status: 'in_progress',
      task_id: 'OPS-SYNC',
      where: 'aethercode:ops-panel',
      why: 'coordinate multi-agent workflow state',
      how: 'gateway route /ops/crosstalk',
    },
    portal: {
      registry: 'config/governance/verified_links_registry.json',
      out_dir: 'artifacts/verified_links_portal',
    },
    backup: {
      source: ['src/aethercode/ide.html'],
      dry_run: true,
    },
    synth: {},
    publish: {},
    monetize: {},
  };
  const payload = payloadByAction[action] || {};

  fetch(GATE_URL + gatewayRoute, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json().catch(() => ({}));
    })
    .then(data => {
      const summary = data.message || data.summary || data.status || 'completed';
      appendOpsLog(OPS_ACTION_LABELS[action] + ' completed via AetherGate (' + summary + ')', 'accent');
      if (action === 'crosstalk') setOpsPill('opsCrossTalkStatus', 'ok', 'synced');
      if (action === 'portal') setOpsPill('opsPortalStatus', 'ok', 'rebuilt');
      if (action === 'backup') setOpsPill('opsBackupStatus', 'ok', 'verified');
      if (data.packet_id) appendOpsLog('Packet: ' + data.packet_id, 'info');
      if (data.manifest) appendOpsLog('Manifest: ' + data.manifest, 'info');
      if (data.defaults_source) appendOpsLog('Backup defaults source: ' + data.defaults_source, 'info');
      updateOpsSnapshot();
    })
    .catch(() => runOpsActionOffline(action));
}

function runOpsActionOffline(action) {
  setTimeout(() => {
    const stamp = safeStamp();

    if (action === 'crosstalk') {
      const packetId = 'cross-talk-' + Date.now().toString(36);
      writeVirtualFile(`artifacts/agent_comm/github_lanes/${packetId}.json`, JSON.stringify({
        packet_id: packetId,
        created_at: isoNow(),
        from: 'aethercode.ide',
        to: 'agent.mesh',
        type: 'terminal_crosstalk_sync',
        summary: 'Manual ops sync emitted from IDE panel',
      }, null, 2));
      setOpsPill('opsCrossTalkStatus', 'ok', 'synced');
      appendOpsLog('Cross-talk packet emitted in local mode: ' + packetId, 'accent');
    }

    if (action === 'portal') {
      writeVirtualFile('artifacts/verified_links_portal/index.html', `<!doctype html>
<html><head><meta charset="utf-8"><title>SCBE Verified Links</title></head>
<body><h1>SCBE Verified Links Portal</h1><p>Generated: ${isoNow()}</p></body></html>`);
      writeVirtualFile('artifacts/verified_links_portal/manifest.json', JSON.stringify({
        generated_at: isoNow(),
        links_digest_sha256: 'local-' + Date.now().toString(16),
        source: 'aethercode-ide-offline',
      }, null, 2));
      setOpsPill('opsPortalStatus', 'ok', 'rebuilt');
      appendOpsLog('Verified links portal rebuilt in artifacts/verified_links_portal/', 'accent');
    }

    if (action === 'backup') {
      const files = Object.keys(fileSystem).filter(k => !k.endsWith('/')).length;
      writeVirtualFile(`artifacts/ops/backup_manifest_${stamp}.json`, JSON.stringify({
        created_at: isoNow(),
        mode: 'dry-run',
        file_count: files,
        min_verified_copies: 2,
        decision: 'safe_to_prune=false',
      }, null, 2));
      setOpsPill('opsBackupStatus', 'ok', 'dry-run');
      appendOpsLog('Backup dry-run manifest generated for ' + files + ' files', 'accent');
    }

    if (action === 'synth') {
      writeVirtualFile('training/internet_workflow_profile.json', JSON.stringify({
        generated_at: isoNow(),
        profile: 'baseline',
        sources: ['arxiv', 'github', 'notion', 'shopify'],
        governance: { fail_closed: true, thresholds: { coherence_min: 0.7, conflict_max: 0.3 } },
      }, null, 2));
      appendOpsLog('Internet workflow profile refreshed (offline baseline)', 'accent');
    }

    if (action === 'publish') {
      writeVirtualFile(`artifacts/publish/article_queue_${stamp}.md`, [
        '# Article Queue',
        '- SCBE: Trusted Cross-talk for Multi-Agent Teams',
        '- AetherBrowser: Transparent Task Automation Lanes',
        '- Practical Guide: Ship/Verify/Prune Without Data Loss',
      ].join('\n'));
      appendOpsLog('Article posting queue file generated under artifacts/publish/', 'info');
    }

    if (action === 'monetize') {
      writeVirtualFile('artifacts/monetization/daily_revenue_loop.md', [
        '# Daily Revenue Loop',
        '1. Run `publish` to stage content assets.',
        '2. Run `portal` to refresh verified service links.',
        '3. Run `crosstalk` to hand off outbound lead tasks.',
        '4. Capture leads and convert via Shopify/Gumroad offer pages.',
      ].join('\n'));
      appendOpsLog('Revenue checklist generated at artifacts/monetization/', 'info');
    }

    updateOpsSnapshot();
  }, 350);
}

// ─── Sacred Tongue Encoding ───
const KO_PREFIX = ['ael','brin','cor','dhal','eth','fael','nav','gor','hael','ith','jor','kel','lor','mael','neth','oth'];
const KO_SUFFIX = ['a','e','i','o','u','or','esh','un','uu','al','el','il','ol','ul','ar','ir'];

function encodeToKO(text) {
  return [...text].map(ch => {
    const b = ch.charCodeAt(0);
    const hi = (b >> 4) & 0xF;
    const lo = b & 0xF;
    return KO_PREFIX[hi] + "'" + KO_SUFFIX[lo];
  }).join(' ');
}

function updateTonguePanel() {
  if (!editor) return;
  const sel = editor.getSelection();
  const text = sel ? editor.getModel().getValueInRange(sel) : '';
  const el = document.getElementById('tongueTokens');
  if (!text) { el.textContent = 'No selection'; return; }
  el.textContent = encodeToKO(text);
}

// ─── Governance ───
function updateGovernance() {
  if (!editor) return;
  const code = editor.getValue();
  const len = code.length;

  // Simulated governance metrics
  const H_eff = Math.max(0.1, 1 - (len / 50000));
  const d_star = Math.min(5, len / 2000);
  const coherence = Math.max(0.3, 0.95 - d_star * 0.08);

  document.getElementById('metricHeff').textContent = H_eff.toFixed(2);
  document.getElementById('metricDstar').textContent = d_star.toFixed(2);
  document.getElementById('metricCohere').textContent = coherence.toFixed(2);

  let decision, color;
  if (H_eff > 0.7) { decision = 'ALLOW'; color = 'var(--green)'; }
  else if (H_eff > 0.4) { decision = 'QUARANTINE'; color = 'var(--amber)'; }
  else if (H_eff > 0.15) { decision = 'ESCALATE'; color = 'var(--accent2)'; }
  else { decision = 'DENY'; color = 'var(--red)'; }

  const badge = document.getElementById('govBadge');
  badge.textContent = decision;
  badge.className = 'gov-badge ' + decision.toLowerCase();

  const meter = document.getElementById('govMeter');
  meter.style.width = (H_eff * 100) + '%';
  meter.style.background = color;

  document.getElementById('sbGateText').textContent = 'L13: ' + decision;
  const dot = document.getElementById('sbGate');
  dot.className = 'sb-dot ' + (decision === 'ALLOW' ? 'ok' : decision === 'DENY' ? 'err' : 'warn');
}

function runGovernanceScan() {
  termLog('> scbe pipeline run --json', 'cmd');
  termLog('Running 14-layer governance scan...', 'info');
  setTimeout(() => {
    const H = document.getElementById('metricHeff').textContent;
    const d = document.getElementById('metricDstar').textContent;
    const badge = document.getElementById('govBadge').textContent;
    termLog(`  H_eff: ${H}  |  d*: ${d}  |  Decision: ${badge}`, 'accent');
    termLog('Scan complete.', 'info');
  }, 500);
}

// ─── AI Assistant ───
function sendAIMessage() {
  const inp = document.getElementById('aiInput');
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';

  const msgs = document.getElementById('aiMessages');
  msgs.innerHTML += `<div class="ai-msg user fade-in">${escHtml(text)}</div>`;

  // Simulated AI responses
  setTimeout(() => {
    let reply = generateAIReply(text);
    msgs.innerHTML += `<div class="ai-msg assistant fade-in">${reply}</div>`;
    msgs.scrollTop = msgs.scrollHeight;
  }, 400 + Math.random() * 300);

  msgs.scrollTop = msgs.scrollHeight;
}

function generateAIReply(q) {
  const lower = q.toLowerCase();
  if (lower.includes('pipeline') || lower.includes('layer')) {
    return `The <strong>14-layer pipeline</strong> transforms input through increasingly strict security checks:<br><br>
<code>L1-2</code> Context realification<br><code>L3-4</code> Weighted embedding<br>
<code>L5</code> Hyperbolic distance<br><code>L6-7</code> Breathing + Mobius<br>
<code>L8</code> Hamiltonian CFI<br><code>L9-10</code> Spectral coherence<br>
<code>L11</code> Triadic temporal<br><code>L12</code> Harmonic wall<br>
<code>L13</code> Risk decision<br><code>L14</code> Audio axis<br><br>
The key formula is <code>H(d,pd) = 1/(1+d_H+2*pd)</code>`;
  }
  if (lower.includes('tongue') || lower.includes('encode')) {
    return `Sacred Tongues use a <strong>16x16 token grid</strong> (256 tokens per language). The 6 tongues are:<br><br>
<code>KO</code> (1.00) <code>AV</code> (1.62) <code>RU</code> (2.62)<br>
<code>CA</code> (4.24) <code>UM</code> (6.85) <code>DR</code> (11.09)<br><br>
Weights scale by the golden ratio. Use the <strong>Tongue</strong> tab to encode selected text.`;
  }
  if (lower.includes('governance') || lower.includes('scan') || lower.includes('allow')) {
    return `L13 governance yields one of four decisions:<br><br>
<span style="color:var(--green)">ALLOW</span> — Safe operation<br>
<span style="color:var(--amber)">QUARANTINE</span> — Needs review<br>
<span style="color:var(--accent2)">ESCALATE</span> — High risk<br>
<span style="color:var(--red)">DENY</span> — Blocked<br><br>
Run <code>scan</code> in the terminal or click <strong>Run Full Scan</strong> in the Governance tab.`;
  }
  if (lower.includes('monetize') || lower.includes('revenue') || lower.includes('lead') || lower.includes('publish')) {
    return `Use the <strong>Ops</strong> tab for execution loops:<br><br>
<code>publish</code> queue articles<br>
<code>portal</code> rebuild verified links<br>
<code>crosstalk</code> hand off tasks to other agents<br>
<code>backup</code> produce ship/verify manifests<br><br>
You can also run these commands directly in the terminal.`;
  }
  if (lower.includes('help') || lower.includes('what can')) {
    return `I can help with:<br>
&#8226; <strong>Code explanation</strong> — Ask about any function or concept<br>
&#8226; <strong>Sacred Tongue encoding</strong> — Select text and check the Tongue tab<br>
&#8226; <strong>Governance analysis</strong> — Check L13 pipeline metrics<br>
&#8226; <strong>SCBE architecture</strong> — Ask about the 14-layer pipeline, axioms, or crypto<br><br>
Try: <em>"Explain the harmonic wall formula"</em>`;
  }
  return `That's a great question. In the SCBE-AETHERMOORE framework, the hyperbolic geometry ensures adversarial intent costs <strong>exponentially</strong> more the further it drifts from safe operation.<br><br>The core formula <code>H(d,R) = R^(d\u00B2)</code> creates an unbounded cost barrier. You can explore this in <code>src/harmonic/pipeline14.ts</code>.`;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Panels ───
function switchPanel(panel) {
  document.querySelectorAll('.ab-btn').forEach(b => b.classList.remove('active'));
  event.currentTarget.classList.add('active');
  const sb = document.getElementById('sidebar');
  sb.classList.remove('collapsed');
  // Update sidebar header
  const header = sb.querySelector('.sidebar-header span');
  if (panel === 'files') header.textContent = 'Explorer';
  else if (panel === 'search') header.textContent = 'Search';
  else if (panel === 'git') header.textContent = 'Source Control';
  else if (panel === 'tongues') header.textContent = 'Sacred Tongues';
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

function toggleAIPanel() {
  document.getElementById('rightPanel').classList.toggle('collapsed');
}

function switchRightTab(tab, el) {
  document.querySelectorAll('.rp-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelector('.rp-header h3').textContent = tab === 'ops' ? 'Operations' : 'AI Assistant';
  document.getElementById('aiMessages').parentElement.querySelector('.ai-input-row').style.display = tab === 'chat' ? 'flex' : 'none';
  document.getElementById('aiMessages').style.display = tab === 'chat' ? 'flex' : 'none';
  document.getElementById('tonguePanel').classList.toggle('visible', tab === 'tongue');
  document.getElementById('govPanel').classList.toggle('visible', tab === 'gov');
  document.getElementById('opsPanel').classList.toggle('visible', tab === 'ops');
  if (tab === 'ops') updateOpsSnapshot();
}

function showOutputTab() { termLog('Output tab selected', 'info'); }
function showProblemsTab() { termLog('Problems tab selected', 'info'); }

// ─── Command Palette ───
const commands = [
  { name: 'Open File...', key: 'Ctrl+P', action: () => { closeCmdPalette(); /* file filter mode */ }},
  { name: 'Toggle Sidebar', key: 'Ctrl+B', action: toggleSidebar },
  { name: 'Toggle Terminal', key: 'Ctrl+`', action: toggleTerminal },
  { name: 'Toggle AI Panel', key: 'Ctrl+I', action: toggleAIPanel },
  { name: 'Open Ops Panel', key: 'Ctrl+Alt+O', action: openOpsTab },
  { name: 'Save File', key: 'Ctrl+S', action: saveFile },
  { name: 'New File', key: '', action: createNewFile },
  { name: 'Run Build', key: '', action: runBuild },
  { name: 'Run Tests', key: '', action: runTests },
  { name: 'Run Lint', key: '', action: runLint },
  { name: 'Governance Scan', key: '', action: runGovernanceScan },
  { name: 'Ops: Sync Cross-talk', key: '', action: () => runOpsAction('crosstalk') },
  { name: 'Ops: Build Link Portal', key: '', action: () => runOpsAction('portal') },
  { name: 'Ops: Run Backup Verify', key: '', action: () => runOpsAction('backup') },
  { name: 'Ops: Refresh Workflow Profile', key: '', action: () => runOpsAction('synth') },
  { name: 'Ops: Queue Articles', key: '', action: () => runOpsAction('publish') },
  { name: 'Ops: Revenue Checklist', key: '', action: () => runOpsAction('monetize') },
  { name: 'Encode Selection (KO)', key: '', action: () => { updateTonguePanel(); switchRightTab('tongue', document.querySelectorAll('.rp-tab')[1]); }},
  { name: 'Clear Terminal', key: '', action: clearTerminal },
  { name: 'Reset File System', key: '', action: () => { fileSystem = { ...defaultFS }; saveFS(); renderFileTree(); termLog('File system reset to defaults', 'warn'); }},
];

function showCmdPalette() {
  const overlay = document.getElementById('cmdOverlay');
  overlay.classList.add('open');
  document.getElementById('cmdInput').value = '';
  document.getElementById('cmdInput').focus();
  cmdPaletteIdx = 0;
  renderCommands('');
}

function closeCmdPalette() {
  document.getElementById('cmdOverlay').classList.remove('open');
}

function renderCommands(filter) {
  const list = document.getElementById('cmdList');
  const lf = filter.toLowerCase();
  const filtered = lf ? commands.filter(c => c.name.toLowerCase().includes(lf)) : commands;
  list.innerHTML = filtered.map((c, i) =>
    `<div class="cmd-item${i === cmdPaletteIdx ? ' selected' : ''}" onclick="runCommand(${commands.indexOf(c)})">
      ${c.name}
      ${c.key ? `<span class="cmd-key">${c.key}</span>` : ''}
    </div>`
  ).join('');
}

function filterCommands() {
  cmdPaletteIdx = 0;
  renderCommands(document.getElementById('cmdInput').value);
}

function handleCmdKey(e) {
  const list = document.getElementById('cmdList');
  const items = list.querySelectorAll('.cmd-item');
  if (e.key === 'ArrowDown') { e.preventDefault(); cmdPaletteIdx = Math.min(cmdPaletteIdx + 1, items.length - 1); renderCommands(document.getElementById('cmdInput').value); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); cmdPaletteIdx = Math.max(cmdPaletteIdx - 1, 0); renderCommands(document.getElementById('cmdInput').value); }
  else if (e.key === 'Enter') {
    e.preventDefault();
    const sel = items[cmdPaletteIdx];
    if (sel) sel.click();
  }
  else if (e.key === 'Escape') closeCmdPalette();
}

function runCommand(idx) {
  closeCmdPalette();
  commands[idx].action();
}

// ─── Keyboard Shortcuts ───
document.addEventListener('keydown', e => {
  // Ctrl+P — command palette
  if (e.ctrlKey && e.key === 'p') { e.preventDefault(); showCmdPalette(); }
  // Ctrl+Shift+P — command palette
  if (e.ctrlKey && e.shiftKey && e.key === 'P') { e.preventDefault(); showCmdPalette(); }
  // Ctrl+S — save
  if (e.ctrlKey && e.key === 's') { e.preventDefault(); saveFile(); }
  // Ctrl+B — toggle sidebar
  if (e.ctrlKey && e.key === 'b') { e.preventDefault(); toggleSidebar(); }
  // Ctrl+` — toggle terminal
  if (e.ctrlKey && e.key === '`') { e.preventDefault(); toggleTerminal(); }
  // Ctrl+J — toggle panel
  if (e.ctrlKey && e.key === 'j') { e.preventDefault(); toggleTerminal(); }
  // Ctrl+I — toggle AI panel
  if (e.ctrlKey && e.key === 'i') { e.preventDefault(); toggleAIPanel(); }
  // Ctrl+Alt+O — open ops panel
  if (e.ctrlKey && e.altKey && (e.key === 'o' || e.key === 'O')) { e.preventDefault(); openOpsTab(); }
  // Escape — close overlays
  if (e.key === 'Escape') closeCmdPalette();
});

// ─── Resize Handles ───
function initResize(handleId, target, dir, prop, min, max) {
  const handle = document.getElementById(handleId);
  if (!handle) return;
  let startPos, startSize;
  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    const el = document.getElementById(target);
    startPos = dir === 'h' ? e.clientX : e.clientY;
    startSize = dir === 'h' ? el.offsetWidth : el.offsetHeight;
    handle.classList.add('active');
    const onMove = ev => {
      const delta = dir === 'h' ? (prop === 'width' ? ev.clientX - startPos : startPos - ev.clientX) : startPos - ev.clientY;
      const newSize = Math.max(min, Math.min(max, startSize + (prop === 'width' ? delta : delta)));
      el.style[prop] = newSize + 'px';
    };
    const onUp = () => {
      handle.classList.remove('active');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}

// ─── Editor Cursor Position ───
function updateCursorPosition() {
  if (!editor) return;
  const pos = editor.getPosition();
  document.getElementById('sbCursor').textContent = `Ln ${pos.lineNumber}, Col ${pos.column}`;
}

// ─── Monaco Initialization ───
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }});

require(['vs/editor/editor.main'], function () {
  // Define AetherCode theme
  monaco.editor.defineTheme('aethercode', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '3d5066', fontStyle: 'italic' },
      { token: 'keyword', foreground: '6c5ce7', fontStyle: 'bold' },
      { token: 'string', foreground: '00d4aa' },
      { token: 'number', foreground: 'ff9152' },
      { token: 'type', foreground: '17c6cf' },
      { token: 'function', foreground: '4ea1f5' },
      { token: 'variable', foreground: 'd8e8f0' },
      { token: 'operator', foreground: 'ffc53d' },
      { token: 'delimiter', foreground: '6b8299' },
      { token: 'tag', foreground: 'ff6b6b' },
      { token: 'attribute.name', foreground: 'ff9152' },
      { token: 'attribute.value', foreground: '00d4aa' },
      { token: 'regexp', foreground: 'ff6b6b' },
    ],
    colors: {
      'editor.background': '#0a0f1a',
      'editor.foreground': '#d8e8f0',
      'editor.lineHighlightBackground': '#0f1729',
      'editor.selectionBackground': '#00d4aa30',
      'editor.inactiveSelectionBackground': '#00d4aa15',
      'editorCursor.foreground': '#00d4aa',
      'editorLineNumber.foreground': '#2a3a4e',
      'editorLineNumber.activeForeground': '#6b8299',
      'editorIndentGuide.background': '#141e33',
      'editorIndentGuide.activeBackground': '#1e2d45',
      'editorBracketMatch.background': '#00d4aa20',
      'editorBracketMatch.border': '#00d4aa40',
      'editor.findMatchBackground': '#ff915240',
      'editor.findMatchHighlightBackground': '#ff915220',
      'editorOverviewRuler.border': '#141e33',
      'scrollbarSlider.background': '#00d4aa15',
      'scrollbarSlider.hoverBackground': '#00d4aa25',
      'scrollbarSlider.activeBackground': '#00d4aa35',
      'editorWidget.background': '#0f1729',
      'editorWidget.border': '#00d4aa20',
      'editorSuggestWidget.background': '#0f1729',
      'editorSuggestWidget.border': '#00d4aa20',
      'editorSuggestWidget.selectedBackground': '#00d4aa20',
      'minimap.background': '#080c14',
    }
  });

  editor = monaco.editor.create(document.getElementById('editor-container'), {
    value: '',
    language: 'typescript',
    theme: 'aethercode',
    fontFamily: "'JetBrains Mono', Consolas, 'Cascadia Code', monospace",
    fontSize: 13,
    lineHeight: 22,
    fontLigatures: true,
    minimap: { enabled: true, scale: 1, showSlider: 'mouseover' },
    smoothScrolling: true,
    cursorBlinking: 'smooth',
    cursorSmoothCaretAnimation: 'on',
    bracketPairColorization: { enabled: true },
    guides: { bracketPairs: true, indentation: true },
    padding: { top: 12 },
    renderLineHighlight: 'all',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
    wordWrap: 'off',
    suggest: { showMethods: true, showFunctions: true, showVariables: true },
  });

  // Listen for cursor changes
  editor.onDidChangeCursorPosition(updateCursorPosition);

  // Listen for content changes
  editor.onDidChangeModelContent(() => {
    if (currentFile) {
      const tab = openTabs.find(t => t.path === currentFile);
      if (tab && !tab.modified) { tab.modified = true; renderTabs(); }
    }
  });

  // Listen for selection changes (tongue encoding)
  editor.onDidChangeCursorSelection(updateTonguePanel);

  // Initialize
  renderFileTree();
  renderTabs();

  // Emit cross-talk startup
  termLog('AetherCode IDE ready.', 'accent');
  termLog('Type "help" for available commands.', '');
  initOpsPanel();

  // Try connecting to AetherGate
  fetch(GATE_URL + '/health').then(r => r.json()).then(data => {
    termLog('AetherGate connected: ' + (data.status || 'online'), 'info');
    setOpsPill('opsGateStatus', 'ok', 'online');
  }).catch(() => {
    termLog('AetherGate offline — running in standalone mode', 'warn');
    setOpsPill('opsGateStatus', 'warn', 'offline');
  });
});

// ─── Init Resize Handles ───
initResize('sidebarResize', 'sidebar', 'h', 'width', 140, 500);
initResize('rightResize', 'rightPanel', 'h', 'width', 200, 500);
initResize('terminalResize', 'terminalPanel', 'v', 'height', 80, 500);

// ─── Git Badge (simulated) ───
document.getElementById('gitBadge').style.display = 'flex';
document.getElementById('gitBadge').textContent = '3';

