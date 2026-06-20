/**
 * @file workspace.test.ts
 * @module agent-bus/workspace
 *
 * Covers: createAgentWorkspace, ingestIntoAgentWorkspace,
 * exportAgentWorkspaceAsync, verifyAgentWorkspaceExportAsync,
 * lineageAgentWorkspace, and Zod schema validation at disk-read boundaries.
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  createAgentWorkspace,
  exportAgentWorkspaceAsync,
  ingestIntoAgentWorkspace,
  lineageAgentWorkspace,
  verifyAgentWorkspaceExportAsync,
  WORKSPACE_FORMATION,
} from '../../packages/agent-bus/src/index.js';

import {
  AgentWorkspaceExportReceiptSchema,
  AgentWorkspaceIngestReceiptSchema,
  AgentWorkspaceReceiptSchema,
  AgentWorkspaceVerifyReceiptSchema,
  WorkspaceExportManifestSchema,
  parseReceipt,
} from '../../packages/agent-bus/src/schemas.js';

// ─── helpers ─────────────────────────────────────────────────────────────────

let tmpBase: string;

function writeTmp(name: string, content: string): string {
  const p = path.join(tmpBase, name);
  fs.writeFileSync(p, content, 'utf8');
  return p;
}

beforeEach(() => {
  tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-test-'));
});

afterEach(() => {
  fs.rmSync(tmpBase, { recursive: true, force: true });
});

// ─── createAgentWorkspace ─────────────────────────────────────────────────────

describe('createAgentWorkspace', () => {
  it('creates all formation folders', () => {
    const receipt = createAgentWorkspace({ root: tmpBase, hint: 'test' });
    expect(receipt.receipt).toBe('SCBE_WORKSPACE_READY=1');
    for (const folder of WORKSPACE_FORMATION.folders) {
      expect(fs.existsSync(path.join(receipt.workspace_root, folder.path))).toBe(true);
    }
  });

  it('writes a Zod-valid workspace.json receipt', () => {
    const receipt = createAgentWorkspace({ root: tmpBase });
    const raw = JSON.parse(fs.readFileSync(receipt.receipt_path, 'utf8'));
    const parsed = parseReceipt(raw, AgentWorkspaceReceiptSchema, 'workspace.json');
    expect(parsed.ok).toBe(true);
    if (parsed.ok) expect(parsed.data.workspace_id).toBe(receipt.workspace_id);
  });

  it('produces unique workspace_id per call', () => {
    const a = createAgentWorkspace({ root: tmpBase, hint: 'a' });
    const b = createAgentWorkspace({ root: tmpBase, hint: 'b' });
    expect(a.workspace_id).not.toBe(b.workspace_id);
  });
});

// ─── ingestIntoAgentWorkspace ─────────────────────────────────────────────────

describe('ingestIntoAgentWorkspace', () => {
  it('copies file into 00_inbox with matching hashes', () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'ingest' });
    const src = writeTmp('payload.txt', 'hello agent bus');
    const receipt = ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    expect(receipt.receipt).toBe('SCBE_WORKSPACE_INGEST=1');
    expect(receipt.source_sha256).toBe(receipt.destination_sha256);
    expect(fs.existsSync(receipt.destination_path)).toBe(true);
  });

  it('persists a Zod-valid ingest receipt under 20_receipts', () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'ingest' });
    const src = writeTmp('data.bin', crypto.randomBytes(128).toString('hex'));
    const receipt = ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const raw = JSON.parse(fs.readFileSync(receipt.receipt_path, 'utf8'));
    const parsed = parseReceipt(raw, AgentWorkspaceIngestReceiptSchema, 'ingest receipt');
    expect(parsed.ok).toBe(true);
  });

  it('rename option changes inbox filename', () => {
    const ws = createAgentWorkspace({ root: tmpBase });
    const src = writeTmp('original.txt', 'content');
    const receipt = ingestIntoAgentWorkspace({
      workspaceRoot: ws.workspace_root,
      sourcePath: src,
      rename: 'aliased.txt',
    });
    expect(receipt.destination_rel).toBe('00_inbox/aliased.txt');
  });
});

// ─── exportAgentWorkspaceAsync + verifyAgentWorkspaceExportAsync ──────────────

describe('exportAgentWorkspaceAsync + verifyAgentWorkspaceExportAsync', () => {
  it('exports a Zod-valid manifest and export receipt', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'export' });
    const src = writeTmp('report.txt', 'governance report');
    ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });

    // Validate the export receipt schema
    const receiptParsed = parseReceipt(exportReceipt, AgentWorkspaceExportReceiptSchema, 'export');
    expect(receiptParsed.ok).toBe(true);

    // Validate the manifest on disk
    const manifestRaw = JSON.parse(fs.readFileSync(exportReceipt.manifest_path, 'utf8'));
    const manifestParsed = parseReceipt(manifestRaw, WorkspaceExportManifestSchema, 'manifest');
    expect(manifestParsed.ok).toBe(true);
  });

  it('clean workspace verifies PASS', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'verify' });
    const src = writeTmp('clean.txt', 'clean content');
    ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });
    const verifyReceipt = await verifyAgentWorkspaceExportAsync({
      exportPath: exportReceipt.export_path,
      persistReceipt: false,
    });

    expect(verifyReceipt.receipt).toBe('SCBE_WORKSPACE_VERIFY_PASS=1');
    expect(verifyReceipt.mismatches).toHaveLength(0);

    // Verify the verify receipt is itself Zod-valid
    const verifyParsed = parseReceipt(
      verifyReceipt,
      AgentWorkspaceVerifyReceiptSchema,
      'verify receipt'
    );
    expect(verifyParsed.ok).toBe(true);
  });

  it('detects tampered file — FAIL with sha256_mismatch', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'tamper' });
    const src = writeTmp('secret.txt', 'original content');
    ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });
    fs.writeFileSync(
      path.join(exportReceipt.export_path, '00_inbox', 'secret.txt'),
      'tampered',
      'utf8'
    );

    const verifyReceipt = await verifyAgentWorkspaceExportAsync({
      exportPath: exportReceipt.export_path,
      persistReceipt: false,
    });
    expect(verifyReceipt.receipt).toBe('SCBE_WORKSPACE_VERIFY_PASS=0');
    const mm = verifyReceipt.mismatches.find((m) => m.path.includes('secret.txt'));
    expect(mm?.reason).toBe('sha256_mismatch');
  });

  it('detects injected extra file — FAIL with extra_file', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'inject' });
    fs.writeFileSync(path.join(ws.workspace_root, '10_work', 'work.txt'), 'work');

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });
    fs.writeFileSync(path.join(exportReceipt.export_path, '10_work', 'injected.txt'), 'evil');

    const verifyReceipt = await verifyAgentWorkspaceExportAsync({
      exportPath: exportReceipt.export_path,
      persistReceipt: false,
    });
    expect(verifyReceipt.receipt).toBe('SCBE_WORKSPACE_VERIFY_PASS=0');
    expect(verifyReceipt.mismatches.some((m) => m.reason === 'extra_file')).toBe(true);
  });

  it('byte counts match between export and verify receipts', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'bytes' });
    const src = writeTmp('large.txt', 'x'.repeat(4096));
    ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });
    const verifyReceipt = await verifyAgentWorkspaceExportAsync({
      exportPath: exportReceipt.export_path,
      persistReceipt: false,
    });
    expect(verifyReceipt.total_bytes_claimed).toBe(verifyReceipt.total_bytes_actual);
  });
});

// ─── Zod schema boundary validation ──────────────────────────────────────────

describe('Zod parseReceipt boundary helper', () => {
  it('returns ok:false with error summary for invalid manifest', () => {
    const bad = { schema_version: 'wrong', files: 'not-an-array' };
    const result = parseReceipt(bad, WorkspaceExportManifestSchema, 'test manifest');
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('test manifest');
    }
  });

  it('catches corrupted sha256 field', () => {
    // Pure schema validation — no real export needed.
    const badEntry = { path: '00_inbox/x.txt', sha256: 'not-a-hex-string', bytes: 5 };
    const result = parseReceipt(
      {
        schema_version: 'aethermoor.bus.workspace_export_manifest.v1',
        export_id: 'x',
        workspace_id: 'ws',
        workspace_root: '/tmp/ws',
        created_at: new Date().toISOString(),
        included_folders: [],
        excluded_folders: [],
        file_count: 1,
        total_bytes: 5,
        files: [badEntry],
      },
      WorkspaceExportManifestSchema,
      'bad manifest'
    );
    expect(result.ok).toBe(false);
  });
});

// ─── lineageAgentWorkspace ────────────────────────────────────────────────────

describe('lineageAgentWorkspace', () => {
  it('reflects the full create→ingest→export→verify cycle', async () => {
    const ws = createAgentWorkspace({ root: tmpBase, hint: 'lineage' });
    const src = writeTmp('artifact.txt', 'lineage content');
    ingestIntoAgentWorkspace({ workspaceRoot: ws.workspace_root, sourcePath: src });

    const exportReceipt = await exportAgentWorkspaceAsync({ workspaceRoot: ws.workspace_root });
    await verifyAgentWorkspaceExportAsync({
      exportPath: exportReceipt.export_path,
      persistReceipt: true,
    });

    const lineage = lineageAgentWorkspace({ workspaceRoot: ws.workspace_root });
    expect(lineage.workspace_id).toBe(ws.workspace_id);
    expect(lineage.export_count).toBeGreaterThanOrEqual(1);
    expect(lineage.verify_count).toBeGreaterThanOrEqual(1);
    const exportEntry = lineage.entries.find(
      (e) => e.kind === 'export' && e.export_id === exportReceipt.export_id
    );
    expect(exportEntry).toBeDefined();
  });
});
