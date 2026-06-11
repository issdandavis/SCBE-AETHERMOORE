'use strict';

/**
 * Drift lock for the `scbe tools` manifest.
 *
 * The manifest in lib/tools-manifest.js is the single source of truth for the
 * command surface. This test guarantees it cannot silently fall behind the
 * actual dispatch chain in bin/scbe.js:
 *   1. Every `argv[0] === '<verb>'` dispatched in bin/scbe.js must have a spec.
 *   2. The legacy KNOWN_COMMANDS set must still be fully covered (no regressions
 *      to the typo-suggestion guard / natural-language router).
 *   3. The emitted manifest must be well-formed.
 *
 * Run: node --test packages/cli/tests/tools-manifest.test.cjs
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  manifestCommandNames,
  buildToolsManifest,
  renderToolsHuman,
} = require('../lib/tools-manifest');

const SCBE_JS = path.join(__dirname, '..', 'bin', 'scbe.js');

/** Pull every top-level `argv[0] === '<verb>'` literal out of the dispatch chain. */
function dispatchedVerbs() {
  const src = fs.readFileSync(SCBE_JS, 'utf8');
  const verbs = new Set();
  const re = /argv\[0\]\s*===\s*'([^']+)'/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    const v = m[1];
    if (v.startsWith('-')) continue; // --help / -h / --version style flags, not verbs
    verbs.add(v.toLowerCase());
  }
  return verbs;
}

// The original hand-maintained list, frozen here so removing a verb from the
// spec that the NL router/typo guard relied on fails loudly.
const LEGACY_KNOWN = [
  'help',
  'version',
  'demo',
  'magic',
  'selftest',
  'doctor',
  'platform',
  'tourney',
  'credits',
  'hosted-run',
  'upgrade',
  'do',
  'work',
  'agent',
  'land',
  'shell',
  'advisor',
  'terminal',
  'term',
  'ui',
  'actions',
  'action',
  'desktop',
  'desk',
  'run',
  'exec',
  'x',
  'format',
  'test',
  'fix',
  'prepush',
  'ship',
  'commit',
  'push',
  'alias',
  'aliases',
  'status',
  'liboqs',
  'history',
  'bench',
  'benchmark',
  'bundle',
  'youtube',
  'foundry',
  'flow',
  'workspace',
  'agent-bus',
  'agentbus',
  'abacus',
  'contract',
  'trap-redirect',
  'trap-dispatch',
  'compile-ca',
  'ca-plan',
  'render-op',
  'compile',
  'route',
  'aetherpp',
  'squad',
  'xval',
  'utterances',
  'calc',
  'math',
  'infer',
  'chem',
  'prime',
  'emit',
];

test('every dispatched verb in bin/scbe.js has a manifest spec', () => {
  const known = new Set(manifestCommandNames());
  const missing = [...dispatchedVerbs()].filter((v) => !known.has(v));
  assert.deepEqual(
    missing,
    [],
    `Dispatched verbs missing from lib/tools-manifest.js COMMAND_SPECS: ${missing.join(', ')}`
  );
});

test('legacy KNOWN_COMMANDS are all still covered (no NL-router regression)', () => {
  const known = new Set(manifestCommandNames());
  const missing = LEGACY_KNOWN.filter((v) => !known.has(v));
  assert.deepEqual(missing, [], `Legacy verbs dropped from the spec: ${missing.join(', ')}`);
});

test('manifest is well-formed and honestly typed', () => {
  const m = buildToolsManifest();
  assert.equal(m.schema_version, 'scbe_tools_manifest_v1');
  assert.equal(m.tool, 'scbe');
  assert.ok(Array.isArray(m.commands) && m.commands.length > 0);
  assert.equal(m.command_count, m.commands.length);
  const validStability = new Set(['real', 'partial', 'stub']);
  for (const c of m.commands) {
    assert.ok(c.name, 'command missing name');
    assert.ok(c.summary, `command ${c.name} missing summary`);
    assert.ok(c.usage, `command ${c.name} missing usage`);
    assert.ok(validStability.has(c.stability), `command ${c.name} bad stability: ${c.stability}`);
    assert.equal(typeof c.json, 'boolean');
    assert.ok(m.categories.includes(c.category), `command ${c.name} category not listed`);
  }
  // stability_counts must sum to command_count
  const sum = Object.values(m.stability_counts).reduce((a, b) => a + b, 0);
  assert.equal(sum, m.command_count);
});

test('human render is non-empty and lists categories', () => {
  const text = renderToolsHuman(buildToolsManifest());
  assert.ok(text.includes('CORE'));
  assert.ok(text.includes('scbe tools --json'));
});
