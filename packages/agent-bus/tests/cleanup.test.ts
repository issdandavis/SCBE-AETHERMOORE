import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { cleanupWorkspaceTmp, createAgentWorkspace } from '../src/index.js';

describe('cleanupWorkspaceTmp', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-cleanup-test-'));
  });

  afterEach(() => {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // tolerate
    }
  });

  it('deletes old files in 90_tmp', () => {
    const ws = createAgentWorkspace({ root: tmpDir, hint: 'cleanup-test' });
    const tmpPath = path.join(ws.workspace_root, '90_tmp');

    const oldFile = path.join(tmpPath, 'old.txt');
    fs.writeFileSync(oldFile, 'old content', 'utf8');
    // Backdate mtime by 10 days
    const tenDaysAgo = Date.now() - 1000 * 60 * 60 * 24 * 10;
    fs.utimesSync(oldFile, tenDaysAgo / 1000, tenDaysAgo / 1000);

    const newFile = path.join(tmpPath, 'new.txt');
    fs.writeFileSync(newFile, 'new content', 'utf8');

    const receipt = cleanupWorkspaceTmp({ workspaceRoot: ws.workspace_root });
    expect(receipt.deleted_count).toBe(1);
    expect(receipt.reclaimed_bytes).toBe(Buffer.byteLength('old content', 'utf8'));
    expect(fs.existsSync(oldFile)).toBe(false);
    expect(fs.existsSync(newFile)).toBe(true);
  });

  it('dryRun reports without deleting', () => {
    const ws = createAgentWorkspace({ root: tmpDir, hint: 'cleanup-dry' });
    const tmpPath = path.join(ws.workspace_root, '90_tmp');

    const oldFile = path.join(tmpPath, 'old.txt');
    fs.writeFileSync(oldFile, 'content', 'utf8');
    const tenDaysAgo = Date.now() - 1000 * 60 * 60 * 24 * 10;
    fs.utimesSync(oldFile, tenDaysAgo / 1000, tenDaysAgo / 1000);

    const receipt = cleanupWorkspaceTmp({ workspaceRoot: ws.workspace_root, dryRun: true });
    expect(receipt.dry_run).toBe(true);
    expect(receipt.deleted_count).toBe(1);
    expect(fs.existsSync(oldFile)).toBe(true);
  });
});
