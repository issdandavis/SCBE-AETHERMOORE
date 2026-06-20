const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-compare-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  if (options.color) delete env.NO_COLOR;
  return spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 30_000,
    env,
  });
}

test('compare --json emits the structured comparison and exits 0', () => {
  const result = runCli(['compare', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_aethermoore_cli_compare_v1');
  assert.ok(payload.detection.rows.length >= 4);
  assert.ok(payload.governance.rows.length >= 6);
  assert.ok(payload.caveats.length >= 6, 'caveats are first-class, not footnotes');
  assert.ok(payload.provenance.detection_benchmark);
  assert.ok(payload.provenance.action_governance);
});

test('compare --json locks the honest numbers (no overclaim)', () => {
  const payload = JSON.parse(runCli(['compare', '--json']).stdout);
  const byName = (rows, name) => rows.find((r) => r[0] === name);

  const protectai = byName(payload.detection.rows, 'ProtectAI DeBERTa v2');
  assert.equal(protectai[2], '62/91', 'ProtectAI blocked count is the reproduced number');
  assert.equal(protectai[3], '0.319', 'ProtectAI ASR is the reproduced number');

  // Prompt Guard was stubbed in the harness — it must NOT carry a fabricated score.
  const promptGuard = byName(payload.detection.rows, 'Meta Prompt Guard 2 (86M)');
  assert.equal(promptGuard[2], 'not run');

  // The home-field-bias and not-load-bearing-geometry caveats must be present.
  const joined = payload.caveats.join(' ').toLowerCase();
  assert.match(joined, /home-field/);
  assert.match(joined, /not load-bearing/);
  assert.match(joined, /adoption gap/);
});

test('compare (human) renders both axes and the caveats', () => {
  const result = runCli(['compare']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Input prompt-injection detection/);
  assert.match(result.stdout, /Runtime action governance/);
  assert.match(result.stdout, /ProtectAI DeBERTa v2/);
  assert.match(result.stdout, /277,547/);
  assert.match(result.stdout, /not run/);
  assert.match(result.stdout, /Caveats/);
  assert.match(result.stdout, /Provenance/);
});

test('compare honours NO_COLOR (no ANSI escapes in either surface)', () => {
  const human = runCli(['compare']);
  assert.equal(human.status, 0, human.stderr);
  assert.ok(!human.stdout.includes('\x1b'), 'human output has no ANSI under NO_COLOR');

  const json = runCli(['compare', '--json']);
  assert.ok(!json.stdout.includes('\x1b'), '--json output is pure JSON, no ANSI');
});

test('compare is a known command (no typo-suggestion, no NL fallthrough)', () => {
  const result = runCli(['compare']);
  // A near-miss like "comapre" would print a suggestion to stderr and exit 2;
  // the real command must not.
  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stderr, /is not a scbe command/);
});
