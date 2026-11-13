#!/usr/bin/env node
'use strict';

const { execFileSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const SCBE_ROOT = path.resolve(HERE, '..', '..');
const CLAIMS_FILE = path.join(HERE, 'CLAIMS.md');
const RECEIPT_FILE = path.join(HERE, 'RECEIPT.json');

const PKG_DIRS = {
  'scbe-aethermoore': SCBE_ROOT,
  'scbe-aethermoore-cli': path.join(SCBE_ROOT, 'packages', 'cli'),
  'scbe-agent-bus': path.join(SCBE_ROOT, 'packages', 'agent-bus'),
  'scbe-polly-pad-cli': path.join(SCBE_ROOT, 'packages', 'polly-pad-cli'),
  'clay-system': path.join('C:', 'dev', 'loom', 'npm', 'clay-global'),
};

const BIN_SCRIPTS = {
  scbe: ['scbe-aethermoore-cli', 'bin', 'scbe.js'],
  'scbe-task': ['scbe-aethermoore-cli', 'bin', 'scbe-task.js'],
  geoseal: ['scbe-aethermoore-cli', 'bin', 'scbe.js'],
  'scbe-scan': ['scbe-aethermoore', 'bin', 'scbe-scan.cjs'],
  'scbe-agent-bus': ['scbe-agent-bus', 'bin', 'scbe-agent-bus.cjs'],
  polly: ['scbe-polly-pad-cli', 'bin', 'polly.js'],
  clay: ['clay-system', 'bin', 'clay.js'],
};

function parseArgs(argv) {
  let surface = 'local';
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--surface' && argv[i + 1]) {
      surface = String(argv[i + 1]);
      i += 1;
    }
  }
  if (surface !== 'local' && surface !== 'published') {
    throw new Error('--surface must be local or published');
  }
  return { surface };
}

function parseTable(content) {
  const lines = content.split(/\r?\n/).filter((line) => line.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const headers = lines[0]
    .split('|')
    .slice(1, -1)
    .map((cell) => cell.trim());
  return lines
    .slice(2)
    .map((line) => {
      const cells = line
        .split('|')
        .slice(1, -1)
        .map((cell) => cell.trim());
      return headers.reduce((obj, header, i) => {
        obj[header] = cells[i];
        return obj;
      }, {});
    })
    .filter((row) => row.package);
}

function parseClaims(surface) {
  return parseTable(fs.readFileSync(CLAIMS_FILE, 'utf8'))
    .filter((row) => row.surface === surface)
    .map((row) => ({
      package: row.package,
      surface: row.surface,
      command: row.command,
      expected_exit: Number(row.expected_exit),
      expected_stdout_match: row.expected_stdout_match,
    }));
}

function tokenize(command) {
  const tokens = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match;
  while ((match = re.exec(command))) {
    tokens.push(match[1] ?? match[2] ?? match[3]);
  }
  return tokens;
}

function npmCli() {
  return (
    process.env.npm_execpath ||
    path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js')
  );
}

function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, {
    encoding: 'utf8',
    timeout: opts.timeout ?? 300000,
    cwd: opts.cwd,
    env: opts.env || process.env,
    windowsHide: true,
  });
}

function buildLocal(pkgName) {
  const dir = PKG_DIRS[pkgName];
  if (!dir || !fs.existsSync(dir)) {
    throw new Error(`no local dir for ${pkgName}`);
  }
  const result = run(process.execPath, [npmCli(), 'run', 'build', '--if-present'], {
    cwd: dir,
    timeout: 300000,
  });
  if (result.status !== 0) {
    throw new Error(
      `npm build failed for ${pkgName} (${result.status}): ${(
        result.stderr ||
        result.stdout ||
        (result.error && result.error.message) ||
        ''
      ).slice(0, 1200)}`
    );
  }
}

function packLocal(pkgName, destDir) {
  const dir = PKG_DIRS[pkgName];
  if (!dir || !fs.existsSync(dir)) {
    throw new Error(`no local dir for ${pkgName}`);
  }
  fs.mkdirSync(destDir, { recursive: true });
  const out = execFileSync(
    process.execPath,
    [
      npmCli(),
      'pack',
      '--json',
      '--ignore-scripts',
      '--pack-destination',
      destDir,
      '--cache',
      path.join(destDir, '.npm-cache'),
    ],
    {
      cwd: dir,
      encoding: 'utf8',
      timeout: 300000,
      windowsHide: true,
    }
  );
  const parsed = JSON.parse(out);
  const filename = Array.isArray(parsed) ? parsed[0].filename : parsed.filename;
  const tgz = path.join(destDir, filename);
  if (!fs.existsSync(tgz)) {
    throw new Error(`npm pack did not write ${tgz}`);
  }
  return tgz;
}

function fetchPublished(pkgName) {
  const spec = execFileSync(
    process.execPath,
    [npmCli(), 'view', pkgName, 'dist.tarball', '--silent'],
    { encoding: 'utf8', timeout: 60000, windowsHide: true }
  ).trim();
  if (!spec) throw new Error(`no tarball for ${pkgName}`);
  return spec;
}

function installPrefix(tarball, prefix) {
  fs.mkdirSync(prefix, { recursive: true });
  const result = run(
    process.execPath,
    [
      npmCli(),
      'install',
      '--ignore-scripts',
      '--omit=dev',
      '--prefix',
      prefix,
      '--cache',
      path.join(prefix, '.npm-cache'),
      tarball,
    ],
    { timeout: 300000 }
  );
  if (result.status !== 0) {
    throw new Error(
      `npm install failed (${result.status}): ${(result.stderr || result.stdout || (result.error && result.error.message) || '').slice(0, 800)}`
    );
  }
}

function resolveBin(prefix, binName) {
  const rel = BIN_SCRIPTS[binName];
  if (!rel) return null;
  const candidate = path.join(prefix, 'node_modules', ...rel);
  return fs.existsSync(candidate) ? candidate : null;
}

function clip(text, n = 240) {
  return String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, n);
}

function measureTree(root) {
  let bytes = 0;
  let files = 0;
  let directories = 0;
  if (!fs.existsSync(root)) return { root, bytes, files, directories };
  const pending = [root];
  while (pending.length) {
    const current = pending.pop();
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink()) {
      files += 1;
      continue;
    }
    if (stat.isDirectory()) {
      directories += 1;
      for (const name of fs.readdirSync(current)) pending.push(path.join(current, name));
      continue;
    }
    files += 1;
    bytes += stat.size;
  }
  return { root, bytes, files, directories };
}

function installedPackagePath(prefix, pkgName) {
  return path.join(prefix, 'node_modules', ...pkgName.split('/'));
}

function evaluate(claim, prefix, workdir) {
  const tokens = tokenize(claim.command);
  const binName = tokens[0];
  const args = tokens.slice(1);
  const script = resolveBin(prefix, binName);
  if (!script) {
    return {
      ...claim,
      pass: false,
      exit: null,
      stdout_head: '',
      why: `bin not installed: ${binName}`,
    };
  }
  const result = run(process.execPath, [script, ...args], {
    cwd: workdir,
    timeout: 30000,
    env: { ...process.env, FORCE_COLOR: '0' },
  });
  const combined = `${result.stdout || ''}\n${result.stderr || ''}`;
  const exit = result.status === null ? 124 : result.status;
  const exitOk = exit === claim.expected_exit;
  const textOk = combined.toLowerCase().includes(String(claim.expected_stdout_match).toLowerCase());
  const pass = exitOk && textOk;
  let why = 'ok';
  if (!exitOk) why = `exit ${exit} != ${claim.expected_exit}`;
  else if (!textOk) why = `stdout missing ${JSON.stringify(claim.expected_stdout_match)}`;
  if (result.error) why = `${why}; ${result.error.message}`;
  return {
    ...claim,
    pass,
    exit,
    stdout_head: clip(combined),
    why,
  };
}

function main() {
  const { surface } = parseArgs(process.argv);
  const claims = parseClaims(surface);
  if (!claims.length) {
    throw new Error(`no claims for surface=${surface}`);
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-usability-'));
  const retainTemp = process.env.SCBE_KEEP_USABILITY_TEMP === '1';
  try {
    const prefixes = {};
    const tarballs = {};
    const footprints = {};
    const needed = [...new Set(claims.map((row) => row.package))];

    for (const pkgName of needed) {
      const prefix = path.join(tmp, pkgName);
      if (surface === 'local') {
        process.stderr.write(`building ${pkgName} (${surface})\n`);
        buildLocal(pkgName);
      }
      process.stderr.write(`packing ${pkgName} (${surface})\n`);
      const tarball =
        surface === 'local'
          ? packLocal(pkgName, path.join(tmp, 'tarballs'))
          : fetchPublished(pkgName);
      tarballs[pkgName] = tarball;
      process.stderr.write(`installing ${pkgName} from ${tarball}\n`);
      installPrefix(tarball, prefix);
      prefixes[pkgName] = prefix;
      footprints[pkgName] = {
        package: measureTree(installedPackagePath(prefix, pkgName)),
        install_with_dependencies: measureTree(path.join(prefix, 'node_modules')),
      };
    }

    const rows = [];
    for (const claim of claims) {
      const workdir = fs.mkdtempSync(path.join(tmp, 'work-'));
      rows.push(evaluate(claim, prefixes[claim.package], workdir));
    }

    const receipt = {
      schema: 'scbe_usability_receipt_v1',
      measured_at: new Date().toISOString(),
      surface,
      temp_retained: retainTemp,
      temp_path: retainTemp ? tmp : null,
      tarballs,
      footprints,
      passed: rows.filter((row) => row.pass).length,
      failed: rows.filter((row) => !row.pass).length,
      rows,
    };
    fs.writeFileSync(RECEIPT_FILE, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');

    process.stdout.write(
      `usability ${surface}: ${receipt.passed} pass / ${receipt.failed} fail  (${rows.length} claims)\n`
    );
    for (const row of rows) {
      const mark = row.pass ? 'PASS' : 'FAIL';
      process.stdout.write(`  ${mark}  ${row.package}  ${row.command}  ${row.why}\n`);
    }
    for (const [pkgName, footprint] of Object.entries(footprints)) {
      process.stdout.write(
        `  SIZE  ${pkgName}  package=${footprint.package.bytes}B  installed=${footprint.install_with_dependencies.bytes}B\n`
      );
    }
    process.stdout.write(`receipt ${RECEIPT_FILE}\n`);
    process.exitCode = receipt.failed ? 1 : 0;
  } finally {
    if (!retainTemp) fs.rmSync(tmp, { recursive: true, force: true });
  }
}

module.exports = { parseTable, parseClaims, PKG_DIRS };

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
    process.exit(1);
  }
}
