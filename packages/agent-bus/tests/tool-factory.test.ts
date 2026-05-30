/**
 * @file tool-factory.test.ts
 *
 * Failure-path tests are primary — silent corruption of tools.json is the worst
 * outcome. Happy-path is covered, but the rejection gates are the value here.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  listToolSpecsFromFile,
  registerToolSpecInFile,
  unregisterToolSpecInFile,
  validateToolSpec,
  verifyToolSpec,
  type ToolSpec,
} from '../src/index.js';

// ─── Fixture helpers ─────────────────────────────────────────────────────────

const GOOD_NODE_SPEC: ToolSpec = {
  name: 'demo-tool',
  description: 'Demo tool for tests.',
  command: 'node',
  args: ['echo.cjs', '{task}'],
  patentSurface: 'agent-harness',
};

function tempToolsJson(seed: ToolSpec[] = []): { dir: string; file: string } {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-tool-factory-'));
  const file = path.join(dir, 'tools.json');
  fs.writeFileSync(file, JSON.stringify(seed, null, 2) + '\n', 'utf8');
  return { dir, file };
}

function touchScript(dir: string, name: string): string {
  const full = path.join(dir, name);
  fs.writeFileSync(full, '// stub\n', 'utf8');
  return full;
}

// ─── validateToolSpec ─────────────────────────────────────────────────────────

describe('validateToolSpec', () => {
  it('accepts a minimal valid node spec', () => {
    const { dir, file } = tempToolsJson();
    try {
      const script = path.join(dir, 'echo.cjs');
      fs.writeFileSync(script, 'console.log("ok")\n', 'utf8');
      const relativeScript = path.relative(dir, script).replace(/\\/g, '/');
      const result = validateToolSpec({
        name: 'demo-tool',
        description: 'Demo tool for tests.',
        command: 'node',
        args: [relativeScript, '{task}'],
        patentSurface: 'agent-harness',
      });
      expect(result.ok).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.spec?.name).toBe('demo-tool');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('accepts a python spec', () => {
    const result = validateToolSpec({
      name: 'py-tool',
      description: 'Python tool.',
      command: 'python',
      args: ['scripts/run.py', '{task}'],
    });
    expect(result.ok).toBe(true);
  });

  it('rejects non-object input (string, null, array, number)', () => {
    expect(validateToolSpec('string').ok).toBe(false);
    expect(validateToolSpec(null).ok).toBe(false);
    expect(validateToolSpec([]).ok).toBe(false);
    expect(validateToolSpec(42).ok).toBe(false);
  });

  it('rejects unknown keys', () => {
    const result = validateToolSpec({ ...GOOD_NODE_SPEC, extra: 'bad', another: 1 });
    expect(result.ok).toBe(false);
    expect(result.errors.join('\n')).toMatch(/unknown key/);
  });

  it('rejects unknown keys AND missing {task} — accumulates multiple errors', () => {
    const result = validateToolSpec({
      name: 'bad-tool',
      description: 'Bad tool.',
      command: 'node',
      args: ['script.cjs'],
      extra: true,
    });
    expect(result.ok).toBe(false);
    expect(result.errors.join('\n')).toMatch(/unknown key/);
    expect(result.errors.join('\n')).toMatch(/\{task\}/);
  });

  it('rejects PascalCase name', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: 'MyTool' }).ok).toBe(false);
  });

  it('rejects snake_case name', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: 'my_tool' }).ok).toBe(false);
  });

  it('rejects single-char name (min length fails regex)', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: 'a' }).ok).toBe(false);
  });

  it('rejects name starting with digit', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: '1tool' }).ok).toBe(false);
  });

  it('rejects name with spaces', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: 'my tool' }).ok).toBe(false);
  });

  it('accepts multi-segment kebab name', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, name: 'tool-register-v2' }).ok).toBe(true);
  });

  it('rejects empty description', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, description: '' }).ok).toBe(false);
  });

  it('rejects whitespace-only description', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, description: '   ' }).ok).toBe(false);
  });

  it('trims leading/trailing whitespace from description', () => {
    const r = validateToolSpec({ ...GOOD_NODE_SPEC, description: '  padded  ' });
    expect(r.ok).toBe(true);
    expect(r.spec?.description).toBe('padded');
  });

  it('rejects bash command', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, command: 'bash' }).ok).toBe(false);
  });

  it('rejects empty command', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, command: '' }).ok).toBe(false);
  });

  it('rejects ruby command', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, command: 'ruby' }).ok).toBe(false);
  });

  it('rejects empty args array', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, args: [] }).ok).toBe(false);
  });

  it('rejects args without {task} placeholder anywhere', () => {
    const r = validateToolSpec({ ...GOOD_NODE_SPEC, args: ['scripts/foo.cjs', '--flag'] });
    expect(r.ok).toBe(false);
    expect(r.errors.join(' ')).toMatch(/\{task\}/);
  });

  it('accepts {task} in any args position', () => {
    expect(
      validateToolSpec({ ...GOOD_NODE_SPEC, args: ['--prefix', '{task}', '--suffix'] }).ok
    ).toBe(true);
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, args: ['{task}'] }).ok).toBe(true);
  });

  it('rejects non-string patentSurface', () => {
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, patentSurface: 42 }).ok).toBe(false);
    expect(validateToolSpec({ ...GOOD_NODE_SPEC, patentSurface: true }).ok).toBe(false);
  });

  it('accepts absent patentSurface', () => {
    const { patentSurface: _, ...noPat } = GOOD_NODE_SPEC;
    expect(validateToolSpec(noPat).ok).toBe(true);
  });
});

// ─── verifyToolSpec ───────────────────────────────────────────────────────────

describe('verifyToolSpec', () => {
  it('returns ok=false when node script does not exist', () => {
    const spec: ToolSpec = {
      ...GOOD_NODE_SPEC,
      args: ['scripts/nonexistent_file_abc123.cjs', '{task}'],
    };
    const r = verifyToolSpec(spec, process.cwd());
    expect(r.ok).toBe(false);
    expect(r.skipped).toBe(false);
  });

  it('skips verification when no recognisable script path in node args', () => {
    const spec: ToolSpec = { ...GOOD_NODE_SPEC, args: ['{task}'] };
    const r = verifyToolSpec(spec, process.cwd());
    expect(r.skipped).toBe(true);
  });

  it('returns ok=true for an existing node script', () => {
    const repoRoot = path.resolve(__dirname, '..', '..', '..');
    const spec: ToolSpec = {
      ...GOOD_NODE_SPEC,
      args: ['packages/agent-bus/scripts/compass.cjs', '{task}'],
    };
    const r = verifyToolSpec(spec, repoRoot);
    expect(r.ok).toBe(true);
    expect(r.skipped).toBe(false);
  });

  it('returns ok=false for a non-existent python script', () => {
    const spec: ToolSpec = {
      name: 'py-tool',
      description: 'Python tool.',
      command: 'python',
      args: ['scripts/does_not_exist_xyz.py', '{task}'],
    };
    const r = verifyToolSpec(spec, process.cwd());
    expect(r.ok).toBe(false);
    expect(r.skipped).toBe(false);
  });

  it('skips python verification when no script or -m flag is present', () => {
    const spec: ToolSpec = {
      name: 'py-tool',
      description: 'Python tool.',
      command: 'python',
      args: ['{task}'],
    };
    const r = verifyToolSpec(spec, process.cwd());
    expect(r.skipped).toBe(true);
  });
});

// ─── registerToolSpecInFile ───────────────────────────────────────────────────

describe('registerToolSpecInFile', () => {
  it('registers a valid spec and persists it (happy path)', () => {
    const { dir, file } = tempToolsJson();
    try {
      touchScript(dir, 'echo.cjs');
      const raw = { ...GOOD_NODE_SPEC, args: ['echo.cjs', '{task}'] };
      const validated = validateToolSpec(raw);
      expect(validated.ok).toBe(true);
      const result = registerToolSpecInFile(validated.spec!, file, dir);

      expect(result.ok).toBe(true);
      expect(result.action).toBe('registered');
      expect(result.tools_count_after).toBe(1);

      const written = JSON.parse(fs.readFileSync(file, 'utf8')) as ToolSpec[];
      expect(written).toHaveLength(1);
      expect(written[0]!.name).toBe('demo-tool');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('rejects duplicate tool name', () => {
    const { dir, file } = tempToolsJson();
    try {
      touchScript(dir, 'echo.cjs');
      const spec = validateToolSpec({ ...GOOD_NODE_SPEC, args: ['echo.cjs', '{task}'] }).spec!;
      registerToolSpecInFile(spec, file, dir, true);
      const r2 = registerToolSpecInFile(spec, file, dir, true);
      expect(r2.ok).toBe(false);
      expect(r2.errors[0]).toMatch(/already registered/);
      expect(r2.tools_count_after).toBe(1);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('does not mutate registry on rejection', () => {
    const { dir, file } = tempToolsJson();
    try {
      touchScript(dir, 'echo.cjs');
      const spec = validateToolSpec({ ...GOOD_NODE_SPEC, args: ['echo.cjs', '{task}'] }).spec!;
      registerToolSpecInFile(spec, file, dir, true);
      registerToolSpecInFile(spec, file, dir, true); // duplicate
      const written = JSON.parse(fs.readFileSync(file, 'utf8')) as ToolSpec[];
      expect(written).toHaveLength(1);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('leaves no .tmp file after successful write', () => {
    const { dir, file } = tempToolsJson();
    try {
      touchScript(dir, 'echo.cjs');
      const spec = validateToolSpec({ ...GOOD_NODE_SPEC, args: ['echo.cjs', '{task}'] }).spec!;
      registerToolSpecInFile(spec, file, dir, true);
      expect(fs.existsSync(file + '.tmp')).toBe(false);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('rejects when pre-registration node script does not exist', () => {
    const { dir, file } = tempToolsJson();
    try {
      const spec: ToolSpec = {
        name: 'bad-node-tool',
        description: 'Missing script.',
        command: 'node',
        args: ['scripts/nonexistent_xyz789.cjs', '{task}'],
      };
      const r = registerToolSpecInFile(spec, file, dir, false);
      expect(r.ok).toBe(false);
      expect(r.errors[0]).toMatch(/verification failed/);
      const written = JSON.parse(fs.readFileSync(file, 'utf8')) as ToolSpec[];
      expect(written).toHaveLength(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('skipVerify=true bypasses file check and registers anyway', () => {
    const { dir, file } = tempToolsJson();
    try {
      const spec: ToolSpec = {
        name: 'skip-verify-tool',
        description: 'Verify skipped.',
        command: 'node',
        args: ['scripts/ghost_file_abc.cjs', '{task}'],
      };
      const r = registerToolSpecInFile(spec, file, dir, true);
      expect(r.ok).toBe(true);
      expect(r.verification.skipped).toBe(true);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});

// ─── listToolSpecsFromFile ────────────────────────────────────────────────────

describe('listToolSpecsFromFile', () => {
  it('returns empty list from empty registry', () => {
    const { dir, file } = tempToolsJson([]);
    try {
      const r = listToolSpecsFromFile(file);
      expect(r.tools_count).toBe(0);
      expect(r.tools).toHaveLength(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('returns summary entries without exposing full args', () => {
    const { dir, file } = tempToolsJson([GOOD_NODE_SPEC]);
    try {
      const r = listToolSpecsFromFile(file);
      expect(r.tools_count).toBe(1);
      expect(r.tools[0]!.name).toBe('demo-tool');
      // summary entries should not include full args
      expect('args' in r.tools[0]!).toBe(false);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('description_head is the first sentence, capped at 80 chars', () => {
    const spec: ToolSpec = {
      ...GOOD_NODE_SPEC,
      name: 'long-desc-tool',
      description: 'First sentence. This is the rest.',
    };
    const { dir, file } = tempToolsJson([spec]);
    try {
      const r = listToolSpecsFromFile(file);
      expect(r.tools[0]!.description_head).toBe('First sentence');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});

// ─── unregisterToolSpecInFile ─────────────────────────────────────────────────

describe('unregisterToolSpecInFile', () => {
  it('removes an existing tool', () => {
    const { dir, file } = tempToolsJson([GOOD_NODE_SPEC]);
    try {
      const r = unregisterToolSpecInFile('demo-tool', file);
      expect(r.ok).toBe(true);
      expect(r.tools_count_after).toBe(0);
      const written = JSON.parse(fs.readFileSync(file, 'utf8')) as ToolSpec[];
      expect(written).toHaveLength(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('returns ok=false for a name that does not exist', () => {
    const { dir, file } = tempToolsJson([GOOD_NODE_SPEC]);
    try {
      const r = unregisterToolSpecInFile('does-not-exist', file);
      expect(r.ok).toBe(false);
      expect(r.error).toMatch(/not found/);
      // original entry untouched
      const written = JSON.parse(fs.readFileSync(file, 'utf8')) as ToolSpec[];
      expect(written).toHaveLength(1);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('does not write to disk on failed unregister', () => {
    const { dir, file } = tempToolsJson([GOOD_NODE_SPEC]);
    try {
      const mtimeBefore = fs.statSync(file).mtimeMs;
      unregisterToolSpecInFile('phantom-tool', file);
      const mtimeAfter = fs.statSync(file).mtimeMs;
      // mtime should not change — no write occurred
      expect(mtimeAfter).toBe(mtimeBefore);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
