'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const AGENT_BUS_ROOT = path.resolve(PACKAGE_ROOT, '..', 'agent-bus');
const CORE_ROOT = path.resolve(PACKAGE_ROOT, '..', '..');
const TEMP_ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-release-gate-'));
const PACK_ROOT = path.join(TEMP_ROOT, 'pack');
const CONSUMER_ROOT = path.join(TEMP_ROOT, 'consumer');
const IS_WINDOWS = process.platform === 'win32';

function quoteShellArg(value) {
  return '"' + String(value).replace(/"/g, '""') + '"';
}

function resolveWindowsNpmCommand() {
  const found = spawnSync('where.exe', ['npm.cmd'], {
    encoding: 'utf8',
    shell: false,
    windowsHide: true,
  });
  const candidate = String(found.stdout || '')
    .split(/\r?\n/)
    .map((value) => value.trim())
    .find((value) => value && fs.existsSync(value));
  if (!candidate) throw new Error('could not resolve an absolute npm.cmd path');
  return candidate;
}

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
    input: options.input || '',
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

function runShellLine(commandLine, options = {}) {
  const result = spawnSync(commandLine, {
    cwd: options.cwd,
    env: options.env || process.env,
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 120_000,
    maxBuffer: 32 * 1024 * 1024,
    shell: true,
    windowsHide: true,
  });
  if (result.error || result.status !== 0) {
    throw new Error(formatFailure(options.label || commandLine, result));
  }
  return result;
}

function runNpm(args, options = {}) {
  const npmExecPath = process.env.npm_execpath;
  if (npmExecPath && fs.existsSync(npmExecPath)) {
    return run(process.execPath, [npmExecPath, ...args], { ...options, shell: false });
  }
  if (IS_WINDOWS) {
    return runShellLine(
      [resolveWindowsNpmCommand(), ...args].map(quoteShellArg).join(' '),
      options
    );
  }
  return run('npm', args, { ...options, shell: false });
}

function installedBin(name) {
  return path.join(CONSUMER_ROOT, 'node_modules', '.bin', IS_WINDOWS ? `${name}.cmd` : name);
}

function runInstalled(name, args, input) {
  const isolatedHome = path.join(TEMP_ROOT, 'home');
  const env = {
    ...process.env,
    HOME: isolatedHome,
    USERPROFILE: isolatedHome,
    SCBE_HOME: path.join(isolatedHome, '.scbe'),
    SCBE_PROVIDER: 'offline',
    NO_COLOR: '1',
  };
  const shim = installedBin(name);
  const options = {
    cwd: CONSUMER_ROOT,
    env,
    input,
    timeout: 30_000,
    label: `installed ${name} shim ${args.join(' ')}`.trim(),
  };
  if (!IS_WINDOWS) return run(shim, args, options);
  const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;
  return runShellLine([shim, ...args].map(quote).join(' '), options);
}

function runInstalledScbe(args, input) {
  return runInstalled('scbe', args, input);
}

function verifyTempTarget(target) {
  const resolved = path.resolve(target);
  const tempPrefix = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(tempPrefix), `refusing to remove non-temp path: ${resolved}`);
}

async function main() {
  fs.mkdirSync(PACK_ROOT, { recursive: true });
  fs.mkdirSync(CONSUMER_ROOT, { recursive: true });
  fs.writeFileSync(
    path.join(CONSUMER_ROOT, 'package.json'),
    `${JSON.stringify({ name: 'scbe-release-gate-consumer', private: true, version: '1.0.0' }, null, 2)}\n`,
    'utf8'
  );

  const packedCore = runNpm(
    ['pack', '--json', '--ignore-scripts', '--pack-destination', PACK_ROOT],
    { cwd: CORE_ROOT, timeout: 180_000, label: 'npm pack GeoSeal core' }
  );
  let corePackMetadata;
  try {
    corePackMetadata = JSON.parse(packedCore.stdout.trim());
  } catch (error) {
    throw new Error(
      'GeoSeal core npm pack did not return JSON: ' +
        error.message +
        '\n' +
        packedCore.stdout
    );
  }
  assert.ok(
    Array.isArray(corePackMetadata) && corePackMetadata.length === 1,
    'expected exactly one GeoSeal core tarball'
  );
  const coreTarball = path.join(PACK_ROOT, corePackMetadata[0].filename);
  assert.ok(
    fs.existsSync(coreTarball),
    'GeoSeal core tarball was not created: ' + coreTarball
  );

  const packedBus = runNpm(
    ['pack', '--json', '--ignore-scripts', '--pack-destination', PACK_ROOT],
    { cwd: AGENT_BUS_ROOT, timeout: 120_000, label: 'npm pack agent bus' }
  );
  let busPackMetadata;
  try {
    busPackMetadata = JSON.parse(packedBus.stdout.trim());
  } catch (error) {
    throw new Error(`agent-bus npm pack did not return JSON: ${error.message}\n${packedBus.stdout}`);
  }
  assert.ok(
    Array.isArray(busPackMetadata) && busPackMetadata.length === 1,
    'expected exactly one agent-bus tarball'
  );
  const busTarball = path.join(PACK_ROOT, busPackMetadata[0].filename);
  assert.ok(fs.existsSync(busTarball), `agent-bus tarball was not created: ${busTarball}`);

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
  assert.ok(Array.isArray(packMetadata) && packMetadata.length === 1, 'expected exactly one tarball');
  const tarball = path.join(PACK_ROOT, packMetadata[0].filename);
  assert.ok(fs.existsSync(tarball), `tarball was not created: ${tarball}`);

  runNpm(
    [
      'install',
      '--ignore-scripts',
      '--no-audit',
      '--no-fund',
      '--package-lock=false',
      coreTarball,
      busTarball,
      tarball,
    ],
    { cwd: CONSUMER_ROOT, timeout: 300_000, label: 'clean consumer npm install' }
  );

  const installedRoot = path.join(CONSUMER_ROOT, 'node_modules', 'scbe-aethermoore-cli');
  const installedPackage = JSON.parse(
    fs.readFileSync(path.join(installedRoot, 'package.json'), 'utf8')
  );
  const installedCore = JSON.parse(
    fs.readFileSync(
      path.join(CONSUMER_ROOT, 'node_modules', 'scbe-aethermoore', 'package.json'),
      'utf8'
    )
  );
  assert.equal(installedPackage.name, 'scbe-aethermoore-cli');
  assert.equal(installedCore.name, 'scbe-aethermoore');
  assert.equal(
    installedCore.version,
    JSON.parse(fs.readFileSync(path.join(CORE_ROOT, 'package.json'), 'utf8')).version
  );
  assert.equal(installedPackage.bin.scbe, 'bin/scbe.js');
  assert.ok(fs.existsSync(path.join(installedRoot, 'lib', 'agent-runtime.js')));
  assert.ok(fs.existsSync(path.join(installedRoot, 'lib', 'guided-evidence.js')));
  assert.ok(fs.existsSync(path.join(installedRoot, 'lib', 'multi-hash-receipt.js')));
  assert.ok(fs.existsSync(path.join(installedRoot, 'GUIDED_EVIDENCE_BUS.md')));
  assert.ok(fs.existsSync(path.join(installedRoot, 'web', 'index.html')));
  assert.ok(fs.existsSync(installedBin('scbe')));
  assert.ok(fs.existsSync(installedBin('geoseal')));
  assert.ok(
    fs.existsSync(
      path.join(CONSUMER_ROOT, 'node_modules', 'scbe-agent-bus', 'dist', 'command-session.js')
    )
  );

  const bare = runInstalledScbe([], '/exit\n');
  assert.match(bare.stdout, /SCBE agent · offline\/offline · ask · \/help/);
  assert.match(bare.stdout, /you ›/);
  assert.match(bare.stdout, /goodbye\./);

  const prompted = runInstalledScbe(['explain', 'this', 'clean', 'tarball'], '');
  assert.match(prompted.stdout, /you › explain this clean tarball/);
  assert.match(
    prompted.stdout,
    /scbe › \[offline\] I saved your message: explain this clean tarball/
  );

  const evidenceWorkspace = path.join(TEMP_ROOT, 'evidence-workspace');
  const evidenceHome = path.join(TEMP_ROOT, 'evidence-home');
  fs.mkdirSync(evidenceWorkspace, { recursive: true });
  fs.writeFileSync(
    path.join(evidenceWorkspace, 'proof.txt'),
    'A guided evidence packet keeps complete results outside model context.\n',
    'utf8'
  );
  const evidenceProbe = [
    `const { createToolRegistry } = require(${JSON.stringify(path.join(installedRoot, 'lib', 'tool-registry.js'))});`,
    `const workspaceRoot = ${JSON.stringify(evidenceWorkspace)};`,
    `const home = ${JSON.stringify(evidenceHome)};`,
    '(async () => {',
    '  const registry = createToolRegistry({ workspaceRoot, home });',
    "  const required = ['guided_evidence', 'search_evidence', 'verify_evidence', 'verify_receipts'];",
    '  if (!required.every((name) => registry.names().includes(name))) throw new Error("missing evidence tools");',
    '  const packet = await registry.execute("guided_evidence", {',
    '    objective: "guided evidence packet outside model context",',
    '    route: "code",',
    '    limit: 1,',
    '    token_budget: 512,',
    '  });',
    '  const verified = await registry.execute("verify_evidence", { packet_id: packet.packet_id });',
    '  const hashes = packet.receipt && packet.receipt.packet_hashes;',
    '  const hashSetOk = hashes && hashes.sha256 && hashes.sha3_256 && hashes.blake2s_256 && hashes.blake2b_512;',
    '  const referencesOk = packet.evidence.length > 0 && packet.evidence[0].id === "E1";',
    '  if (!packet.ok || !referencesOk || !hashSetOk || packet.retrieval.raw_results_in_prompt !== false || !verified.ok) {',
    '    throw new Error(JSON.stringify({ packet, verified }));',
    '  }',
    '  process.stdout.write(JSON.stringify({ packet_id: packet.packet_id, verified: verified.ok }));',
    '})().catch((error) => { console.error(error); process.exitCode = 1; });',
  ].join('\n');
  const evidence = run(process.execPath, ['-e', evidenceProbe], {
    cwd: CONSUMER_ROOT,
    timeout: 30_000,
    label: 'installed guided evidence code route',
  });
  assert.equal(JSON.parse(evidence.stdout).verified, true);

  const geoInput = [
    { id: 'status', op: 'status' },
    { id: 'geo', op: 'geo', task: 'compile and test the clean package' },
    { id: 'run', op: 'run', command: 'node --version' },
    { id: 'bus', op: 'bus' },
  ]
    .map(JSON.stringify)
    .join('\n');
  const geoseal = runInstalled('geoseal', ['shell', '--agent-json'], geoInput);
  const geoRows = geoseal.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(geoRows.length, 5);
  assert.ok(geoRows.slice(1).every((row) => row.ok));
  assert.match(geoRows[3].result.stdout, /^v\d+/);
  assert.equal(geoRows[3].result.coordination.domain, 'CA');
  assert.equal(geoRows[4].result.result.mode, 'local_receipt');

  process.stdout.write(
    `${JSON.stringify(
      {
        ok: true,
        package: `${installedPackage.name}@${installedPackage.version}`,
        tarball: path.basename(tarball),
        core_tarball: path.basename(coreTarball),
        agent_bus_tarball: path.basename(busTarball),
        packed_files: packMetadata[0].entryCount,
        checks: [
          'clean consumer install',
          'installed scbe shim',
          'bare scbe first prompt',
          'optional prompt offline response',
          'packaged runtime and web assets',
          'packaged guided-evidence code route and four-hash packet verification',
          'matching packed agent bus command-session API',
          'colliding geoseal shim delegates to the installed agent CLI shell',
          'installed geoseal NDJSON status/geo/run/bus session',
        ],
      },
      null,
      2
    )}\n`
  );
}

main()
  .catch((error) => {
    process.stderr.write(`SCBE release gate failed: ${error.stack || error.message}\n`);
    process.exitCode = 1;
  })
  .finally(() => {
    if (process.env.SCBE_KEEP_RELEASE_GATE === '1') {
      process.stderr.write(`SCBE release gate artifacts kept at ${TEMP_ROOT}\n`);
      return;
    }
    verifyTempTarget(TEMP_ROOT);
    fs.rmSync(TEMP_ROOT, { recursive: true, force: true });
  });
