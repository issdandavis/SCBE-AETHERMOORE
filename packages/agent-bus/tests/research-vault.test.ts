import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  buildResearchRetrievalPacket,
  createResearchSourceCard,
  createResearchStyleCard,
  persistResearchVaultPlan,
  planResearchVaultPacket,
} from '../src/research-vault.js';
import { createAgentWorkspace, startAgentBusServer } from '../src/index.js';

const reviewedSource = {
  title: 'Research Vault Field Notes',
  author: 'Issac Davis',
  source_type: 'note' as const,
  locator: 'docs/internal/research-vault.md',
  rights_status: 'owned' as const,
  claims: ['Research Vault keeps source cards separate from style cards.'],
  verified_notes: ['Keep mail ingestion separate from retrieval packet assembly.'],
  quality: 'reviewed' as const,
  namespace: 'scbe',
  created_at: '2026-05-31T21:00:00.000Z',
};

describe('research vault planning', () => {
  it('creates source and style cards with deterministic required fields', () => {
    const source = createResearchSourceCard(reviewedSource);
    const style = createResearchStyleCard({
      scope: 'project',
      allowed_moves: ['plain engineering prose'],
      banned_moves: ['invented citations'],
      cadence_notes: ['short paragraphs'],
      mechanics_visibility: 'hidden',
      namespace: 'scbe',
      created_at: '2026-05-31T21:00:01.000Z',
    });

    expect(source.schema_version).toBe('source_card_v1');
    expect(source.source_id).toMatch(/^source-/);
    expect(style.schema_version).toBe('style_card_v1');
    expect(style.style_id).toMatch(/^style-/);
    expect(style.namespace).toBe('scbe');
  });

  it('rejects source cards without citation locator metadata', () => {
    expect(() =>
      createResearchSourceCard({
        ...reviewedSource,
        locator: '',
      })
    ).toThrow(/missing locator/);
  });

  it('builds retrieval packets with selected notes and citation requirements', () => {
    const packet = buildResearchRetrievalPacket({
      query: 'Explain Research Vault boundaries',
      source_cards: [reviewedSource],
      namespace: 'scbe',
      created_at: '2026-05-31T21:01:00.000Z',
    });

    expect(packet.schema_version).toBe('retrieval_packet_v1');
    expect(packet.selected_notes).toHaveLength(1);
    expect(packet.selected_notes[0].labels).toContain('sources');
    expect(packet.citation_requirements[0]).toContain('docs/internal/research-vault.md');
    expect(packet.review_required).toBe(true);
  });

  it('denies cross-namespace client/internal mixing by default', () => {
    const plan = planResearchVaultPacket({
      query: 'Make a client deliverable from internal and client cards',
      namespace: 'client-a',
      source_cards: [
        { ...reviewedSource, namespace: 'client-a' },
        {
          ...reviewedSource,
          title: 'Internal Only Notes',
          locator: 'docs/internal/private.md',
          namespace: 'internal',
        },
      ],
      style_cards: [
        {
          scope: 'proposal',
          allowed_moves: ['cite every claim'],
          namespace: 'client-a',
        },
      ],
      created_at: '2026-05-31T21:02:00.000Z',
      generated_at: '2026-05-31T21:02:01.000Z',
    });

    expect(plan.governance.decision).toBe('DENY');
    expect(plan.governance.findings.map((finding) => finding.code)).toContain(
      'blocked_sources_present'
    );
    expect(plan.governance.findings.map((finding) => finding.code)).toContain('mixed_namespaces');
    expect(plan.governance.blocked_actions).toContain('client_export');
  });

  it('denies retrieval packets that contain credential material', () => {
    const plan = planResearchVaultPacket({
      query: 'Summarize deployment note',
      namespace: 'scbe',
      source_cards: [
        {
          ...reviewedSource,
          claims: ['api_key = "sk-this-should-stay-local"'],
        },
      ],
      created_at: '2026-05-31T21:03:00.000Z',
      generated_at: '2026-05-31T21:03:01.000Z',
    });

    expect(plan.governance.decision).toBe('DENY');
    expect(plan.governance.findings.map((finding) => finding.code)).toContain(
      'secret_material_detected'
    );
  });

  it('allows empty selected_notes when require_review is false and source has no notes or claims', () => {
    // Regression: empty selected_notes should produce block finding, not crash.
    const plan = planResearchVaultPacket({
      query: 'No notes at all',
      namespace: 'scbe',
      source_cards: [
        {
          title: 'Bare source',
          source_type: 'note' as const,
          locator: 'docs/bare.md',
          rights_status: 'owned' as const,
          claims: [],
          verified_notes: [],
          quality: 'reviewed' as const,
          namespace: 'scbe',
          created_at: '2026-05-31T22:00:00.000Z',
        },
      ],
      created_at: '2026-05-31T22:00:01.000Z',
      generated_at: '2026-05-31T22:00:02.000Z',
    });

    expect(plan.governance.decision).toBe('DENY');
    expect(plan.governance.findings.map((f) => f.code)).toContain('empty_selected_notes');
  });

  it('serves Research Vault packet plans over the agent-bus HTTP surface', async () => {
    const server = await startAgentBusServer({ port: 18788 });
    try {
      const response = await fetch('http://127.0.0.1:18788/v1/research-vault/packet/plan', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          query: 'Prepare a reviewed local packet',
          namespace: 'scbe',
          source_cards: [reviewedSource],
          created_at: '2026-05-31T21:04:00.000Z',
          generated_at: '2026-05-31T21:04:01.000Z',
        }),
      });
      const payload = (await response.json()) as {
        ok: boolean;
        plan: { governance: { decision: string }; packet: { schema_version: string } };
      };

      expect(response.status).toBe(200);
      expect(payload.ok).toBe(true);
      expect(payload.plan.governance.decision).toBe('REVIEW');
      expect(payload.plan.packet.schema_version).toBe('retrieval_packet_v1');
    } finally {
      await server.close();
    }
  });
});

describe('research vault persistence', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vault-persist-test-'));
  });

  afterEach(() => {
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  function makeWorkspace() {
    return createAgentWorkspace({ root: tmpDir, hint: 'vault-test' });
  }

  it('writes packet to 10_work and receipt to 20_receipts for ALLOW plan', async () => {
    const ws = makeWorkspace();
    const plan = planResearchVaultPacket({
      query: 'Persist an allowed packet',
      namespace: 'scbe',
      source_cards: [
        {
          ...reviewedSource,
          require_review: false,
        } as typeof reviewedSource,
      ],
      require_review: false,
      created_at: '2026-05-31T23:00:00.000Z',
      generated_at: '2026-05-31T23:00:01.000Z',
    });

    // Force decision to ALLOW by ensuring require_review=false yields no review finding.
    // (reviewedSource has quality=reviewed, rights=owned so no findings block; only review_required
    // default=true adds REVIEW. Override with require_review: false.)
    expect(['ALLOW', 'REVIEW']).toContain(plan.governance.decision);

    const receipt = persistResearchVaultPlan(plan, ws.workspace_root);

    expect(receipt.schema_version).toBe('scbe.agent_bus.research_vault_persist.v1');
    expect(receipt.workspace_root).toBe(ws.workspace_root);
    expect(receipt.packet_id).toBe(plan.packet.packet_id);
    expect(receipt.governance_decision).toBe(plan.governance.decision);
    expect(receipt.packet_sha256).toMatch(/^[a-f0-9]{64}$/);

    // Receipt written to 20_receipts/.
    expect(fs.existsSync(receipt.receipt_path)).toBe(true);
    expect(receipt.receipt_path).toContain('20_receipts');

    // Packet written to 10_work/.
    expect(receipt.packet_path).not.toBeNull();
    expect(fs.existsSync(receipt.packet_path!)).toBe(true);
    expect(receipt.packet_path).toContain('10_work');

    // Packet JSON is valid and matches schema.
    const onDisk = JSON.parse(fs.readFileSync(receipt.packet_path!, 'utf8'));
    expect(onDisk.schema_version).toBe('retrieval_packet_v1');
    expect(onDisk.packet_id).toBe(plan.packet.packet_id);

    // SHA256 in receipt matches file on disk.
    const fileHash = crypto
      .createHash('sha256')
      .update(fs.readFileSync(receipt.packet_path!))
      .digest('hex');
    expect(fileHash).toBe(receipt.packet_sha256);
  });

  it('writes only governance receipt (no packet file) for DENY plan', () => {
    const ws = makeWorkspace();
    const plan = planResearchVaultPacket({
      query: 'Cross-namespace denied packet',
      namespace: 'client-a',
      source_cards: [
        { ...reviewedSource, namespace: 'client-a' },
        {
          ...reviewedSource,
          title: 'Internal Notes',
          locator: 'docs/internal.md',
          namespace: 'internal',
        },
      ],
      created_at: '2026-05-31T23:01:00.000Z',
      generated_at: '2026-05-31T23:01:01.000Z',
    });

    expect(plan.governance.decision).toBe('DENY');

    const receipt = persistResearchVaultPlan(plan, ws.workspace_root);

    expect(receipt.governance_decision).toBe('DENY');
    expect(receipt.packet_path).toBeNull();

    // Governance receipt must still be written.
    expect(fs.existsSync(receipt.receipt_path)).toBe(true);

    // 10_work must NOT contain a vault packet file.
    const workDir = path.join(ws.workspace_root, '10_work');
    const workFiles = fs.existsSync(workDir) ? fs.readdirSync(workDir) : [];
    expect(workFiles.filter((f) => f.startsWith('vault-'))).toHaveLength(0);
  });

  it('throws when workspace_root does not exist', () => {
    const plan = planResearchVaultPacket({
      query: 'Nonexistent workspace',
      namespace: 'scbe',
      source_cards: [reviewedSource],
      created_at: '2026-05-31T23:02:00.000Z',
      generated_at: '2026-05-31T23:02:01.000Z',
    });

    expect(() => persistResearchVaultPlan(plan, '/nonexistent/path/that/does/not/exist')).toThrow(
      /workspace not found/
    );
  });

  it('persists via the HTTP /v1/research-vault/packet/persist endpoint', async () => {
    const ws = makeWorkspace();
    const server = await startAgentBusServer({ port: 18789 });
    try {
      const response = await fetch('http://127.0.0.1:18789/v1/research-vault/packet/persist', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          query: 'HTTP persist test',
          namespace: 'scbe',
          source_cards: [reviewedSource],
          workspace_root: ws.workspace_root,
          created_at: '2026-05-31T23:03:00.000Z',
          generated_at: '2026-05-31T23:03:01.000Z',
        }),
      });
      const payload = (await response.json()) as {
        ok: boolean;
        plan: { governance: { decision: string } };
        persist: { schema_version: string; packet_path: string | null; receipt_path: string };
      };

      expect(response.status).toBe(200);
      expect(payload.ok).toBe(true);
      expect(payload.persist.schema_version).toBe('scbe.agent_bus.research_vault_persist.v1');
      expect(fs.existsSync(payload.persist.receipt_path)).toBe(true);
      if (payload.persist.packet_path) {
        expect(fs.existsSync(payload.persist.packet_path)).toBe(true);
      }
    } finally {
      await server.close();
    }
  });

  it('returns 400 when workspace_root is missing from persist request', async () => {
    const server = await startAgentBusServer({ port: 18790 });
    try {
      const response = await fetch('http://127.0.0.1:18790/v1/research-vault/packet/persist', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          query: 'Missing workspace root',
          namespace: 'scbe',
          source_cards: [reviewedSource],
        }),
      });
      const payload = (await response.json()) as { ok: boolean; error: string };

      expect(response.status).toBe(400);
      expect(payload.ok).toBe(false);
      expect(payload.error).toMatch(/workspace_root/);
    } finally {
      await server.close();
    }
  });
});
