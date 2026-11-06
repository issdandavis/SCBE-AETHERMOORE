'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const TEMP_ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-agent-bus-release-'));
const PACK_ROOT = path.join(TEMP_ROOT, 'pack');
const CONSUMER_ROOT = path.join(TEMP_ROOT, 'consumer');
const IS_WINDOWS = process.platform === 'win32';

function formatFailure(label, result) {
  return [
    `${label} failed (status=${result.status}, signal=${result.signal || 'none'})`,
    result.error ? `error: ${result.error.message}` : '',
    result.stdout ? `stdout:\n${result.stdout}` : '',
    result.stderr ? `stderr:\n${result.stderr}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env || process.env,
    encoding: 'utf8',
    timeout: options.timeout || 120_000,
    maxBuffer: 32 * 1024 * 1024,
    shell: options.shell === true,
    windowsHide: true,
  });
  if (result.error || result.status !== 0) {
    throw new Error(formatFailure(options.label || command, result));
  }
  return result;
}

function runNpm(args, options = {}) {
  const npmExecPath = process.env.npm_execpath;
  if (npmExecPath && fs.existsSync(npmExecPath)) {
    return run(process.execPath, [npmExecPath, ...args], { ...options, shell: false });
  }
  return run(IS_WINDOWS ? 'npm.cmd' : 'npm', args, {
    ...options,
    shell: IS_WINDOWS,
  });
}

function verifyTempTarget(target) {
  const resolved = path.resolve(target);
  const tempPrefix = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(tempPrefix), `refusing to remove non-temp path: ${resolved}`);
  assert.match(path.basename(resolved), /^scbe-agent-bus-release-/);
}

async function main() {
  fs.mkdirSync(PACK_ROOT, { recursive: true });
  fs.mkdirSync(CONSUMER_ROOT, { recursive: true });
  fs.writeFileSync(
    path.join(CONSUMER_ROOT, 'package.json'),
    `${JSON.stringify(
      { name: 'scbe-agent-bus-release-consumer', private: true, version: '1.0.0' },
      null,
      2
    )}\n`,
    'utf8'
  );

  const packed = runNpm(
    ['pack', '--json', '--ignore-scripts', '--pack-destination', PACK_ROOT],
    { cwd: PACKAGE_ROOT, timeout: 120_000, label: 'npm pack' }
  );
  let packMetadata;
  try {
    packMetadata = JSON.parse(packed.stdout.trim());
  } catch (error) {
    throw new Error(`npm pack did not return JSON: ${error.message}\n${packed.stdout}`);
  }
  assert.ok(Array.isArray(packMetadata) && packMetadata.length === 1, 'expected one tarball');
  const tarball = path.join(PACK_ROOT, packMetadata[0].filename);
  assert.ok(fs.existsSync(tarball), `tarball was not created: ${tarball}`);

  runNpm(
    ['install', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', tarball],
    { cwd: CONSUMER_ROOT, timeout: 300_000, label: 'clean consumer npm install' }
  );

  const probe = [
    "const assert = require('node:assert/strict');",
    "const { runEvent } = require('scbe-agent-bus');",
    '(async () => {',
    "  const result = await runEvent({ task: 'clean tarball quick start', taskType: 'review', privacy: 'local_only' });",
    '  assert.equal(result.ok, true);',
    "  assert.match(result.receipt_id, /^evt_[a-f0-9]{24}$/);",
    "  assert.equal(result.result.status, 'accepted');",
    '  process.stdout.write(JSON.stringify(result));',
    '})().catch((error) => { console.error(error); process.exit(1); });',
  ].join('\n');
  const quickStart = run(process.execPath, ['-e', probe], {
    cwd: CONSUMER_ROOT,
    timeout: 30_000,
    label: 'installed runEvent quick start',
  });
  const result = JSON.parse(quickStart.stdout);

  process.stdout.write(
    `${JSON.stringify(
      {
        ok: true,
        package: packMetadata[0].name,
        version: packMetadata[0].version,
        packed_files: packMetadata[0].entryCount,
        receipt_id: result.receipt_id,
        checks: ['clean consumer install', 'installed runEvent quick start'],
      },
      null,
      2
    )}\n`
  );
}

main()
  .catch((error) => {
    process.stderr.write(`Agent Bus release gate failed: ${error.stack || error.message}\n`);
    process.exitCode = 1;
  })
  .finally(() => {
    if (process.env.SCBE_KEEP_RELEASE_GATE === '1') {
      process.stderr.write(`Agent Bus release artifacts kept at ${TEMP_ROOT}\n`);
      return;
    }
    verifyTempTarget(TEMP_ROOT);
    fs.rmSync(TEMP_ROOT, { recursive: true, force: true });
  });
