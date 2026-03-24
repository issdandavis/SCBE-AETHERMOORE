import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { Basin, type River } from '../../src/browser/basin.js';

describe('Basin path safety', () => {
  let tempRoot: string;
  let intakePath: string;
  let backupPath: string;
  let archivePath: string;
  let riverRoot: string;
  let basin: Basin;

  beforeEach(() => {
    tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-basin-'));
    intakePath = path.join(tempRoot, 'intake');
    backupPath = path.join(tempRoot, 'backup');
    archivePath = path.join(tempRoot, 'archive');
    riverRoot = path.join(tempRoot, 'river');
    fs.mkdirSync(path.join(riverRoot, 'inbox'), { recursive: true });
    fs.writeFileSync(path.join(riverRoot, 'inbox', 'sample.txt'), 'sample');

    basin = new Basin({ intakePath, backupPath, archivePath });
    const rivers = (basin as unknown as { rivers: Map<string, River> }).rivers;
    const river = rivers.get('local-scbe');
    if (!river) {
      throw new Error('local-scbe river is required for this test');
    }
    river.localPath = riverRoot;
  });

  afterEach(() => {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  });

  it('rejects traversal in categories and filenames during deposit', () => {
    expect(() => basin.deposit('local-scbe', '../reports', 'safe.txt', 'x')).toThrow(/category/i);
    expect(() => basin.deposit('local-scbe', 'reports', '../escape.txt', 'x')).toThrow(/filename/i);
  });

  it('rejects traversal source paths during pull', () => {
    expect(() => basin.pull('local-scbe', '../outside', 'reports')).toThrow(/sourcePath/i);
  });

  it('rejects traversal destination paths during push', () => {
    basin.deposit('local-scbe', 'reports', 'safe.txt', 'payload');
    expect(() => basin.push('local-scbe', 'reports', '../outside')).toThrow(/destPath/i);
  });

  it('allows paths that remain inside configured roots', () => {
    const pulled = basin.pull('local-scbe', 'inbox', 'reports');
    expect(pulled).toHaveLength(1);
    expect(fs.existsSync(path.join(intakePath, 'local-scbe', 'reports', 'sample.txt'))).toBe(true);

    basin.deposit('local-scbe', 'reports', 'safe.txt', 'payload');
    const pushed = basin.push('local-scbe', 'reports', 'exports/2026');
    expect(pushed).toContain(path.join(riverRoot, 'exports', '2026', 'safe.txt'));
  });
});
