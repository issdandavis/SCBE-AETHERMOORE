import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

function packageOnlyFixture(): string {
  const root = mkdtempSync(join(tmpdir(), 'geoseal-package-only-'));
  mkdirSync(join(root, 'bin'));
  cpSync(resolve('bin/geoseal.cjs'), join(root, 'bin', 'geoseal.cjs'));
  writeFileSync(
    join(root, 'package.json'),
    `${JSON.stringify({ name: 'scbe-aethermoore', version: '0.0.0-test', bin: {} }, null, 2)}\n`,
    'utf8'
  );
  return root;
}

function pathlessEnvironment(): NodeJS.ProcessEnv {
  const env = Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.toLowerCase() !== 'path')
  );
  return {
    ...env,
    PATH: '',
    SCBE_GEOSEAL_AUTODETECT: '0',
    SCBE_GEOSEAL_PYTHON: join(tmpdir(), 'missing-geoseal-python'),
  };
}

describe('GeoSeal package-only capability boundary', () => {
  const fixtures: string[] = [];

  afterEach(() => {
    for (const fixture of fixtures.splice(0)) rmSync(fixture, { recursive: true, force: true });
  });

  it('fails a source-only spine command immediately with structured JSON', () => {
    const root = packageOnlyFixture();
    fixtures.push(root);

    const result = spawnSync(
      process.execPath,
      [join(root, 'bin', 'geoseal.cjs'), 'bits', 'hello', '--json'],
      { cwd: root, encoding: 'utf8', env: pathlessEnvironment(), timeout: 3000 }
    );

    expect(result.error).toBeUndefined();
    expect(result.status).toBe(2);
    expect(result.stderr).toBe('');
    expect(JSON.parse(result.stdout)).toMatchObject({
      schema_version: 'geoseal_command_support_v1',
      ok: false,
      error: 'source_only_command_unavailable',
      command: 'bits',
      support_mode: 'source_only',
      availability: 'not_shipped_in_npm',
      required_file: 'scbe.py',
    });
  });

  it('reports an honest four-mode support matrix from a package-only layout', () => {
    const root = packageOnlyFixture();
    fixtures.push(root);

    const result = spawnSync(
      process.execPath,
      [join(root, 'bin', 'geoseal.cjs'), 'doctor', '--json'],
      {
        cwd: root,
        encoding: 'utf8',
        env: pathlessEnvironment(),
        timeout: 5000,
      }
    );

    expect(result.error).toBeUndefined();
    expect(result.status).toBe(0);
    const payload = JSON.parse(result.stdout);
    expect(payload.capability_matrix.node_native).toMatchObject({
      support: 'available',
      available_now: true,
    });
    expect(payload.capability_matrix.node_native.commands).toContain('doctor');
    expect(payload.capability_matrix.service_backed).toMatchObject({
      support: 'service_required',
      available_now: false,
      configured: false,
    });
    expect(payload.capability_matrix.optional_python_module).toMatchObject({
      support: 'not_installed',
      available_now: false,
    });
    expect(payload.capability_matrix.source_only).toMatchObject({
      support: 'not_shipped_in_npm',
      available_now: false,
      required_file: 'scbe.py',
    });
    expect(payload.capability_matrix.source_only.commands).toContain('bits');
  });
});
