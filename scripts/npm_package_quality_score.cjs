#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = process.cwd();
const args = process.argv.slice(2);
const json = args.includes('--json');
const pack = args.includes('--pack');
const packageArgs = args.filter((arg) => !arg.startsWith('--'));
const packageDirs = packageArgs.length ? packageArgs : ['.'];

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function exists(packageDir, relativePath) {
  return fs.existsSync(path.join(packageDir, relativePath));
}

function readTextIfExists(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
}

function run(command, commandArgs, cwd, timeout = 15000, options = {}) {
  return spawnSync(command, commandArgs, {
    cwd,
    encoding: 'utf8',
    shell: Boolean(options.shell),
    timeout,
    env: {
      ...process.env,
      npm_config_audit: 'false',
      npm_config_fund: 'false',
    },
  });
}

function packageManagerCommand() {
  return process.platform === 'win32' ? 'npm.cmd' : 'npm';
}

function resolveBinPath(packageDir, binTarget) {
  const full = path.resolve(packageDir, binTarget);
  return fs.existsSync(full) ? full : null;
}

function runNodeBin(binFile, flags, cwd) {
  return run(process.execPath, [binFile, ...flags], cwd, 10000);
}

function checkBinSurface(packageDir, pkg) {
  const binEntries =
    typeof pkg.bin === 'string'
      ? [[pkg.name, pkg.bin]]
      : Object.entries(pkg.bin || {});

  if (!binEntries.length) {
    return {
      hasBin: true,
      helpOk: true,
      versionOk: true,
      notes: ['no bin surface'],
    };
  }

  const notes = [];
  let hasBin = true;
  let helpOk = true;
  let versionOk = true;

  for (const [binName, binTarget] of binEntries) {
    const binFile = resolveBinPath(packageDir, binTarget);
    if (!binFile) {
      hasBin = false;
      notes.push(`${binName}: missing ${binTarget}`);
      continue;
    }

    const help = runNodeBin(binFile, ['--help'], packageDir);
    const helpText = `${help.stdout || ''}\n${help.stderr || ''}`.toLowerCase();
    if (help.status !== 0 || !helpText.includes('usage')) {
      helpOk = false;
      notes.push(`${binName}: --help failed (${help.status})`);
    }

    const version = runNodeBin(binFile, ['--version'], packageDir);
    const versionText = `${version.stdout || ''}\n${version.stderr || ''}`;
    if (version.status !== 0 || !versionText.includes(String(pkg.version))) {
      versionOk = false;
      notes.push(`${binName}: --version did not report ${pkg.version} (${version.status})`);
    }
  }

  return { hasBin, helpOk, versionOk, notes };
}

function packCheck(packageDir) {
  if (!pack) {
    return { ok: true, skipped: true, notes: ['pack check skipped; pass --pack to run npm pack --dry-run'] };
  }

  const result =
    process.platform === 'win32'
      ? run('npm pack --dry-run --json --ignore-scripts', [], packageDir, 30000, { shell: true })
      : run(packageManagerCommand(), ['pack', '--dry-run', '--json', '--ignore-scripts'], packageDir, 30000);
  if (result.status !== 0) {
    return {
      ok: false,
      skipped: false,
      notes: [
        `npm pack failed (${result.status}${result.signal ? `, ${result.signal}` : ''})`,
        result.error ? String(result.error) : '',
        String(result.stderr || result.stdout || '').trim(),
      ].filter(Boolean),
    };
  }

  try {
    const parsed = JSON.parse(result.stdout);
    const entry = Array.isArray(parsed) ? parsed[0] : parsed;
    const files = Array.isArray(entry?.files) ? entry.files.map((file) => file.path) : [];
    const hasReadme = files.some((file) => /^readme\.md$/i.test(file));
    const hasLicense = files.some((file) => /^license/i.test(file));
    return {
      ok: Boolean(entry?.filename && (entry?.unpackedSize || entry?.packageSize) > 0 && hasReadme && hasLicense),
      skipped: false,
      notes: [`${entry?.filename || 'unknown tarball'}: ${files.length} files, ${entry?.packageSize || 0} bytes`],
    };
  } catch (error) {
    return { ok: false, skipped: false, notes: [`could not parse npm pack JSON: ${error.message}`] };
  }
}

function scorePackage(inputDir) {
  const packageDir = path.resolve(root, inputDir);
  const packageJson = path.join(packageDir, 'package.json');
  if (!fs.existsSync(packageJson)) {
    throw new Error(`missing package.json: ${packageDir}`);
  }

  const pkg = readJson(packageJson);
  const isPrivate = pkg.private === true;
  const readmePath = path.join(packageDir, 'README.md');
  const readme = readTextIfExists(readmePath).toLowerCase();
  const files = Array.isArray(pkg.files) ? pkg.files : [];
  const bin = checkBinSurface(packageDir, pkg);
  const packed = packCheck(packageDir);

  const checks = [
    {
      id: 'identity',
      ok: Boolean(pkg.name && pkg.version),
      note: isPrivate ? 'private package name/version present' : 'publishable name/version present',
    },
    {
      id: 'description',
      ok: typeof pkg.description === 'string' && pkg.description.trim().length >= 40,
      note: isPrivate ? 'description is useful for internal package discovery' : 'description is useful in npm search',
    },
    {
      id: 'license',
      ok: Boolean(pkg.license && !/unlicensed/i.test(pkg.license) && (exists(packageDir, 'LICENSE') || exists(packageDir, 'LICENSE.md'))),
      note: 'license metadata and license file present',
    },
    {
      id: 'repository',
      ok: Boolean(pkg.repository?.url || typeof pkg.repository === 'string'),
      note: 'repository link present',
    },
    {
      id: 'support_links',
      ok: Boolean(pkg.homepage && pkg.bugs?.url),
      note: 'homepage and issue tracker present',
    },
    {
      id: 'keywords',
      ok: Array.isArray(pkg.keywords) && pkg.keywords.length >= 5,
      note: 'at least five npm discovery keywords',
    },
    {
      id: 'readme',
      ok: Boolean(readme.includes('install') && (readme.includes('usage') || readme.includes('quick start')) && readme.includes(pkg.name.toLowerCase())),
      note: 'README covers install and use',
    },
    {
      id: 'files_allowlist',
      ok: files.includes('README.md') && files.some((item) => /^license/i.test(item)) && files.some((item) => ['bin', 'dist', 'lib', 'src'].includes(item.split('/')[0])),
      note: 'package files allowlist includes docs, license, and runtime code',
    },
    {
      id: 'bin_help',
      ok: bin.hasBin && bin.helpOk,
      note: bin.notes.length ? bin.notes.join('; ') : 'all bin --help commands pass',
    },
    {
      id: 'bin_version',
      ok: bin.versionOk,
      note: bin.notes.length ? bin.notes.join('; ') : 'all bin --version commands pass',
    },
    {
      id: 'pack',
      ok: packed.ok,
      note: packed.notes.join('; '),
    },
  ];

  const passed = checks.filter((check) => check.ok).length;
  return {
    packageDir,
    name: pkg.name,
    version: pkg.version,
    score: `${passed}/${checks.length}`,
    passed,
    total: checks.length,
    checks,
  };
}

const results = packageDirs.map(scorePackage);

if (json) {
  process.stdout.write(`${JSON.stringify({ generated_at: new Date().toISOString(), pack, results }, null, 2)}\n`);
} else {
  for (const result of results) {
    console.log(`${result.name}@${result.version} ${result.score}`);
    for (const check of result.checks) {
      console.log(`  ${check.ok ? 'PASS' : 'FAIL'} ${check.id} - ${check.note}`);
    }
  }
}

if (results.some((result) => result.passed !== result.total)) {
  process.exitCode = 1;
}
