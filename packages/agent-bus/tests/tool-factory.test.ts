import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  listToolSpecsFromFile,
  registerToolSpecInFile,
  unregisterToolSpecInFile,
  validateToolSpec,
} from '../src/index.js';

function tempToolsJson(): { dir: string; file: string } {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-tool-factory-'));
  const file = path.join(dir, 'tools.json');
  fs.writeFileSync(file, '[]\n', 'utf8');
  return { dir, file };
}

describe('tool factory', () => {
  it('validates and atomically registers a node tool spec', () => {
    const { dir, file } = tempToolsJson();
    try {
      const script = path.join(dir, 'echo.cjs');
      fs.writeFileSync(script, 'console.log("ok")\n', 'utf8');
      const relativeScript = path.relative(dir, script).replace(/\\/g, '/');
      const raw = {
        name: 'demo-tool',
        description: 'Demo tool for tests.',
        command: 'node',
        args: [relativeScript, '{task}'],
        patentSurface: 'agent-harness',
      };

      const validated = validateToolSpec(raw);
      expect(validated.ok).toBe(true);
      const result = registerToolSpecInFile(validated.spec!, file, dir);

      expect(result.ok).toBe(true);
      expect(result.action).toBe('registered');
      expect(result.tools_count_after).toBe(1);
      expect(listToolSpecsFromFile(file).tools[0].name).toBe('demo-tool');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('rejects unknown keys and missing task placeholders', () => {
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

  it('unregisters a tool spec from a tools file', () => {
    const { dir, file } = tempToolsJson();
    try {
      const script = path.join(dir, 'echo.cjs');
      fs.writeFileSync(script, 'console.log("ok")\n', 'utf8');
      const validated = validateToolSpec({
        name: 'remove-me',
        description: 'Temporary tool.',
        command: 'node',
        args: ['echo.cjs', '{task}'],
      });
      registerToolSpecInFile(validated.spec!, file, dir);

      const removed = unregisterToolSpecInFile('remove-me', file);

      expect(removed.ok).toBe(true);
      expect(listToolSpecsFromFile(file).tools_count).toBe(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
