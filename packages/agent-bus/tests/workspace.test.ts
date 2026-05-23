/**
 * @file workspace.test.ts
 * @module agent-bus/tests
 * @layer workspace lifecycle (creation, export, verification)
 *
 * Unit tests for agent-bus workspace operations:
 * - Workspace creation with 6-folder formation
 * - File ingest into folders
 * - Export with manifest generation and sha256 anchoring
 * - Verification with tampering detection
 * - Lineage tracking
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {
  createAgentWorkspace,
  exportAgentWorkspace,
  exportAgentWorkspaceAsync,
  verifyAgentWorkspaceExport,
  lineageAgentWorkspace,
} from '../src/index.js';

describe('agent-bus workspace lifecycle', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-test-'));
  });

  afterEach(() => {
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  describe('workspace creation', () => {
    it('should create a workspace with 6 formation folders', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });

      expect(receipt.schema_version).toBe('aethermoor.bus.workspace_receipt.v1');
      expect(receipt.receipt).toBe('SCBE_WORKSPACE_READY=1');
      expect(receipt.workspace_id).toMatch(/^\d{8}T\d{6}Z-test-[a-f0-9]{6}$/);
      expect(receipt.workspace_root).toEqual(expect.stringContaining(receipt.workspace_id));
      expect(receipt.created_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);

      const workspace = receipt.workspace_root;
      expect(fs.existsSync(workspace)).toBe(true);

      const expectedFolders = [
        '00_inbox',
        '10_work',
        '20_receipts',
        '30_exports',
        '40_refs',
        '90_tmp',
      ];
      for (const folder of expectedFolders) {
        expect(fs.existsSync(path.join(workspace, folder))).toBe(true);
      }
    });

    it('should write workspace receipt to 20_receipts/workspace.json', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      expect(fs.existsSync(receipt.receipt_path)).toBe(true);

      const content = JSON.parse(fs.readFileSync(receipt.receipt_path, 'utf8'));
      expect(content.workspace_id).toBe(receipt.workspace_id);
      expect(content.schema_version).toBe('aethermoor.bus.workspace_receipt.v1');
    });

    it('should generate unique workspace IDs on multiple calls', () => {
      const receipt1 = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const receipt2 = createAgentWorkspace({ root: tmpDir, hint: 'test' });

      expect(receipt1.workspace_id).not.toBe(receipt2.workspace_id);
    });

    it('should use custom root directory', () => {
      const customRoot = path.join(tmpDir, 'custom-root');
      const receipt = createAgentWorkspace({ root: customRoot, hint: 'test' });

      expect(receipt.workspace_root).toContain(customRoot);
      expect(fs.existsSync(receipt.workspace_root)).toBe(true);
    });
  });

  describe('file ingestion and folders', () => {
    it('should allow ingesting files into inbox', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const inboxPath = path.join(receipt.workspace_root, '00_inbox');

      const testFile = path.join(inboxPath, 'test.txt');
      fs.writeFileSync(testFile, 'test content', 'utf8');

      expect(fs.existsSync(testFile)).toBe(true);
      expect(fs.readFileSync(testFile, 'utf8')).toBe('test content');
    });

    it('should support moving files between work folders', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const inboxPath = path.join(receipt.workspace_root, '00_inbox');
      const workPath = path.join(receipt.workspace_root, '10_work');

      const inboxFile = path.join(inboxPath, 'document.md');
      fs.writeFileSync(inboxFile, '# Document\nContent here', 'utf8');

      const workFile = path.join(workPath, 'document.md');
      fs.renameSync(inboxFile, workFile);

      expect(fs.existsSync(inboxFile)).toBe(false);
      expect(fs.existsSync(workFile)).toBe(true);
    });

    it('should track multiple files across folders', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'input.json'), '{}');
      fs.writeFileSync(path.join(root, '10_work', 'output.json'), '{}');
      fs.writeFileSync(path.join(root, '40_refs', 'reference.txt'), 'ref');

      expect(fs.readdirSync(path.join(root, '00_inbox')).length).toBeGreaterThanOrEqual(1);
      expect(fs.readdirSync(path.join(root, '10_work')).length).toBeGreaterThanOrEqual(1);
      expect(fs.readdirSync(path.join(root, '40_refs')).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('workspace export', () => {
    it('should export workspace with correct manifest structure', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file1.txt'), 'content1');
      fs.writeFileSync(path.join(root, '10_work', 'file2.txt'), 'content2');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      expect(exportReceipt.schema_version).toBe('aethermoor.bus.workspace_export.v1');
      expect(exportReceipt.receipt).toBe('SCBE_WORKSPACE_EXPORT=1');
      expect(exportReceipt.file_count).toBe(3);
      expect(exportReceipt.total_bytes).toBeGreaterThan(0);

      const manifestPath = exportReceipt.manifest_path;
      expect(fs.existsSync(manifestPath)).toBe(true);

      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      expect(manifest.schema_version).toBe('aethermoor.bus.workspace_export_manifest.v1');
      expect(manifest.files.length).toBe(3);
      const paths = manifest.files.map((f: { path: string }) => f.path);
      expect(paths).toContain('00_inbox/file1.txt');
      expect(paths).toContain('10_work/file2.txt');
      expect(paths).toContain('20_receipts/workspace.json');
    });

    it('should compute correct sha256 for each file in manifest', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      const content1 = 'test file 1';
      const content2 = 'test file 2';
      fs.writeFileSync(path.join(root, '00_inbox', 'file1.txt'), content1);
      fs.writeFileSync(path.join(root, '10_work', 'file2.txt'), content2);

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      const manifest = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));

      const expectedHash1 = crypto.createHash('sha256').update(content1).digest('hex');
      const expectedHash2 = crypto.createHash('sha256').update(content2).digest('hex');

      const hashes = manifest.files.map((f: { path: string; sha256: string }) => f.sha256);
      expect(hashes).toContain(expectedHash1);
      expect(hashes).toContain(expectedHash2);
    });

    it('should exclude 30_exports and 90_tmp from export by default', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'inbox.txt'), 'inbox');
      fs.writeFileSync(path.join(root, '30_exports', 'export.txt'), 'export');
      fs.writeFileSync(path.join(root, '90_tmp', 'tmp.txt'), 'tmp');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      const manifest = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));

      const paths = manifest.files.map((f: { path: string }) => f.path);
      expect(paths.some((p: string) => p.includes('00_inbox'))).toBe(true);
      expect(paths.some((p: string) => p.includes('30_exports'))).toBe(false);
      expect(paths.some((p: string) => p.includes('90_tmp'))).toBe(false);
    });

    it('should support custom include folders', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'inbox.txt'), 'inbox');
      fs.writeFileSync(path.join(root, '10_work', 'work.txt'), 'work');
      fs.writeFileSync(path.join(root, '40_refs', 'ref.txt'), 'ref');

      const exportReceipt = exportAgentWorkspace({
        workspaceRoot: root,
        include: ['00_inbox', '40_refs'],
      });
      const manifest = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));

      const paths = manifest.files.map((f: { path: string }) => f.path);
      expect(paths.some((p: string) => p.includes('00_inbox'))).toBe(true);
      expect(paths.some((p: string) => p.includes('10_work'))).toBe(false);
      expect(paths.some((p: string) => p.includes('40_refs'))).toBe(true);
    });

    it('should write export receipt to 20_receipts', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      expect(fs.existsSync(exportReceipt.receipt_path)).toBe(true);

      const receiptContent = JSON.parse(fs.readFileSync(exportReceipt.receipt_path, 'utf8'));
      expect(receiptContent.export_id).toBe(exportReceipt.export_id);
      expect(receiptContent.manifest_sha256).toBe(exportReceipt.manifest_sha256);
    });
  });

  describe('workspace export async', () => {
    it('should export asynchronously with streaming hashes', async () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file1.txt'), 'content1');
      fs.writeFileSync(path.join(root, '10_work', 'file2.txt'), 'content2');

      const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: root });

      expect(exportReceipt.schema_version).toBe('aethermoor.bus.workspace_export.v1');
      expect(exportReceipt.file_count).toBe(3);
      expect(fs.existsSync(exportReceipt.manifest_path)).toBe(true);
    });

    it('should support custom output directory', async () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;
      const customOut = path.join(tmpDir, 'custom-export');

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');

      const exportReceipt = await exportAgentWorkspaceAsync({
        workspaceRoot: root,
        out: customOut,
      });

      expect(exportReceipt.export_path).toContain(customOut);
      expect(fs.existsSync(exportReceipt.manifest_path)).toBe(true);
    });
  });

  describe('workspace verification', () => {
    it('should verify intact export with no mismatches', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file1.txt'), 'content1');
      fs.writeFileSync(path.join(root, '10_work', 'file2.txt'), 'content2');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: false,
      });

      expect(verifyReceipt.schema_version).toBe('aethermoor.bus.workspace_verify.v1');
      expect(verifyReceipt.manifest_intact).toBe(true);
      expect(verifyReceipt.mismatches.length).toBe(0);
      expect(verifyReceipt.file_count_claimed).toBe(verifyReceipt.file_count_actual);
      expect(verifyReceipt.total_bytes_claimed).toBe(verifyReceipt.total_bytes_actual);
    });

    it('should detect sha256 mismatch on file modification', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'original');
      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      const exportedFile = path.join(exportReceipt.export_path, '00_inbox', 'file.txt');
      fs.writeFileSync(exportedFile, 'modified');

      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: false,
      });

      expect(verifyReceipt.manifest_intact).toBe(true); // manifest itself unchanged
      expect(verifyReceipt.mismatches.length).toBeGreaterThan(0);
      expect(verifyReceipt.mismatches[0].reason).toBe('sha256_mismatch');
    });

    it('should detect missing file', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file1.txt'), 'content1');
      fs.writeFileSync(path.join(root, '00_inbox', 'file2.txt'), 'content2');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      const exportedFile = path.join(exportReceipt.export_path, '00_inbox', 'file1.txt');
      fs.unlinkSync(exportedFile);

      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: false,
      });

      expect(verifyReceipt.mismatches.some((m) => m.reason === 'missing_file')).toBe(true);
    });

    it('should detect extra file', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');
      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      const extraFile = path.join(exportReceipt.export_path, '00_inbox', 'extra.txt');
      fs.writeFileSync(extraFile, 'extra content');

      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: false,
      });

      expect(verifyReceipt.mismatches.some((m) => m.reason === 'extra_file')).toBe(true);
    });

    it('should persist verify receipt to 20_receipts when requested', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');
      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: true,
      });

      expect(verifyReceipt.receipt_path).not.toBe('');
      expect(fs.existsSync(verifyReceipt.receipt_path)).toBe(true);

      const content = JSON.parse(fs.readFileSync(verifyReceipt.receipt_path, 'utf8'));
      expect(content.export_path).toBe(exportReceipt.export_path);
    });
  });

  describe('workspace lineage', () => {
    it('should compute lineage from workspace through export to verify', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');
      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath: exportReceipt.export_path,
        persistReceipt: true,
      });

      const lineage = lineageAgentWorkspace({ workspaceRoot: root });
      const exportEntries = lineage.entries.filter((entry) => entry.kind === 'export');
      const verifyEntries = lineage.entries.filter((entry) => entry.kind === 'verify');

      expect(lineage.workspace_id).toBe(receipt.workspace_id);
      expect(lineage.export_count).toBeGreaterThanOrEqual(1);
      expect(lineage.verify_count).toBeGreaterThanOrEqual(1);
      expect(exportEntries.some((entry) => entry.export_id === exportReceipt.export_id)).toBe(true);
      expect(verifyEntries.some((entry) => entry.export_id === exportReceipt.export_id)).toBe(true);
    });

    it('should track multiple exports in lineage', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');

      const export1 = exportAgentWorkspace({ workspaceRoot: root });
      const export2 = exportAgentWorkspace({ workspaceRoot: root, include: ['00_inbox'] });

      const lineage = lineageAgentWorkspace({ workspaceRoot: root });
      const exportIds = lineage.entries
        .filter((entry) => entry.kind === 'export')
        .map((entry) => entry.export_id);

      expect(lineage.export_count).toBeGreaterThanOrEqual(2);
      expect(exportIds).toContain(export1.export_id);
      expect(exportIds).toContain(export2.export_id);
    });
  });

  describe('edge cases and error handling', () => {
    it('should throw on missing workspace directory', () => {
      const nonExistent = path.join(tmpDir, 'nonexistent');

      expect(() => {
        exportAgentWorkspace({ workspaceRoot: nonExistent });
      }).toThrow(/workspace not found/);
    });

    it('should throw on missing manifest during verification', () => {
      const exportPath = path.join(tmpDir, 'fake-export');
      fs.mkdirSync(exportPath, { recursive: true });

      expect(() => {
        verifyAgentWorkspaceExport({ exportPath, persistReceipt: false });
      }).toThrow(/manifest not found/);
    });

    it('should tolerate corrupt workspace receipt gracefully', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      fs.writeFileSync(path.join(root, '20_receipts', 'workspace.json'), 'invalid json');
      fs.writeFileSync(path.join(root, '00_inbox', 'file.txt'), 'content');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      expect(exportReceipt.workspace_id).toBe(path.basename(root));
    });

    it('should export only the formation receipt for a new workspace', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });

      expect(exportReceipt.file_count).toBe(1);
      expect(exportReceipt.total_bytes).toBeGreaterThan(0);

      const manifest = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));
      expect(manifest.files.map((f: { path: string }) => f.path)).toEqual([
        '20_receipts/workspace.json',
      ]);
    });

    it('should handle deeply nested directory structures', () => {
      const receipt = createAgentWorkspace({ root: tmpDir, hint: 'test' });
      const root = receipt.workspace_root;

      const deepPath = path.join(root, '00_inbox', 'a', 'b', 'c', 'd');
      fs.mkdirSync(deepPath, { recursive: true });
      fs.writeFileSync(path.join(deepPath, 'deep.txt'), 'deep content');

      const exportReceipt = exportAgentWorkspace({ workspaceRoot: root });
      expect(exportReceipt.file_count).toBeGreaterThan(0);

      const manifest = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));
      expect(manifest.files.some((f: { path: string }) => f.path.includes('a/b/c/d'))).toBe(true);
    });
  });
});
