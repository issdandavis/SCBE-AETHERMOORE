/**
 * @file schemas.ts
 * @module agent-bus/schemas
 *
 * Zod v4 schemas for every agent-bus receipt, manifest, and event shape.
 * Use safeParse at disk-read boundaries; parse() when we own the data.
 *
 * parseFromDisk() is the standard boundary helper — returns a typed Result
 * rather than throwing, so callers decide whether to quarantine or propagate.
 */

import { z } from 'zod';

// ─── primitive helpers ────────────────────────────────────────────────────────

const sha256Hex = z.string().regex(/^[0-9a-f]{64}$/, 'expected 64-char lowercase hex sha256');
const isoTs = z.string().min(1, 'expected ISO timestamp string');
const nonNegInt = z.number().int().nonnegative();

// ─── AgentBusEvent ───────────────────────────────────────────────────────────

export const AgentBusEventSchema = z.object({
  task: z.string().min(1),
  taskType: z.string().optional(),
  operationCommand: z.string().optional(),
  seriesId: z.string().optional(),
  privacy: z.string().optional(),
  budgetCents: z.number().nonnegative().optional(),
  dispatch: z.boolean().optional(),
  dispatchProvider: z.string().optional(),
});

export type AgentBusEventParsed = z.infer<typeof AgentBusEventSchema>;

// ─── WorkspaceExportManifest ──────────────────────────────────────────────────

export const WorkspaceExportManifestEntrySchema = z.object({
  path: z.string().min(1),
  sha256: sha256Hex,
  bytes: nonNegInt,
});

export const WorkspaceExportManifestSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_export_manifest.v1'),
  export_id: z.string().min(1),
  workspace_id: z.string().min(1),
  workspace_root: z.string().min(1),
  created_at: isoTs,
  included_folders: z.array(z.string()),
  excluded_folders: z.array(z.string()),
  file_count: nonNegInt,
  total_bytes: nonNegInt,
  files: z.array(WorkspaceExportManifestEntrySchema),
});

export type WorkspaceExportManifestParsed = z.infer<typeof WorkspaceExportManifestSchema>;

// ─── AgentWorkspaceReceipt (formation) ───────────────────────────────────────

export const AgentWorkspaceReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_receipt.v1'),
  receipt: z.literal('SCBE_WORKSPACE_READY=1'),
  workspace_id: z.string().min(1),
  workspace_root: z.string().min(1),
  created_at: isoTs,
  formation: z.object({
    schema_version: z.literal('aethermoor.bus.workspace_formation.v1'),
    default_root: z.string(),
    folders: z.array(z.object({ path: z.string(), purpose: z.string() })),
  }),
  receipt_path: z.string(),
});

export type AgentWorkspaceReceiptParsed = z.infer<typeof AgentWorkspaceReceiptSchema>;

// ─── AgentWorkspaceExportReceipt ─────────────────────────────────────────────

export const AgentWorkspaceExportReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_export.v1'),
  receipt: z.literal('SCBE_WORKSPACE_EXPORT=1'),
  workspace_id: z.string().min(1),
  workspace_root: z.string().min(1),
  export_id: z.string().min(1),
  export_path: z.string().min(1),
  manifest_path: z.string().min(1),
  manifest_sha256: sha256Hex,
  created_at: isoTs,
  file_count: nonNegInt,
  total_bytes: nonNegInt,
  included_folders: z.array(z.string()),
  excluded_folders: z.array(z.string()),
  receipt_path: z.string(),
});

export type AgentWorkspaceExportReceiptParsed = z.infer<typeof AgentWorkspaceExportReceiptSchema>;

// ─── WorkspaceVerifyMismatch ──────────────────────────────────────────────────

export const WorkspaceVerifyMismatchSchema = z.object({
  path: z.string(),
  reason: z.enum(['sha256_mismatch', 'missing_file', 'extra_file', 'bytes_mismatch']),
  expected_sha256: z.string().optional(),
  actual_sha256: z.string().optional(),
  expected_bytes: nonNegInt.optional(),
  actual_bytes: nonNegInt.optional(),
});

export type WorkspaceVerifyMismatchParsed = z.infer<typeof WorkspaceVerifyMismatchSchema>;

// ─── AgentWorkspaceVerifyReceipt ─────────────────────────────────────────────

export const AgentWorkspaceVerifyReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_verify.v1'),
  receipt: z.enum(['SCBE_WORKSPACE_VERIFY_PASS=1', 'SCBE_WORKSPACE_VERIFY_PASS=0']),
  export_path: z.string(),
  manifest_path: z.string(),
  manifest_sha256_claimed: z.string(),
  manifest_sha256_actual: z.string(),
  manifest_intact: z.boolean(),
  file_count_claimed: nonNegInt,
  file_count_actual: nonNegInt,
  total_bytes_claimed: nonNegInt,
  total_bytes_actual: nonNegInt,
  mismatches: z.array(WorkspaceVerifyMismatchSchema),
  verified_at: isoTs,
  receipt_path: z.string(),
});

export type AgentWorkspaceVerifyReceiptParsed = z.infer<typeof AgentWorkspaceVerifyReceiptSchema>;

// ─── AgentWorkspaceIngestReceipt ─────────────────────────────────────────────

export const AgentWorkspaceIngestReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_ingest.v1'),
  receipt: z.literal('SCBE_WORKSPACE_INGEST=1'),
  workspace_id: z.string().min(1),
  workspace_root: z.string().min(1),
  source_path: z.string().min(1),
  destination_path: z.string().min(1),
  destination_rel: z.string().min(1),
  source_sha256: sha256Hex,
  destination_sha256: sha256Hex,
  bytes: nonNegInt,
  ingested_at: isoTs,
  receipt_path: z.string(),
});

export type AgentWorkspaceIngestReceiptParsed = z.infer<typeof AgentWorkspaceIngestReceiptSchema>;

// ─── AgentWorkspaceVerifyAllReceipt ──────────────────────────────────────────

export const AgentWorkspaceVerifyAllReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_verify_all.v1'),
  receipt: z.enum(['SCBE_WORKSPACE_VERIFY_ALL_PASS=1', 'SCBE_WORKSPACE_VERIFY_ALL_PASS=0']),
  workspace_root: z.string(),
  workspace_id: z.string(),
  verified_at: isoTs,
  export_count: nonNegInt,
  passed_count: nonNegInt,
  failed_count: nonNegInt,
  results: z.array(AgentWorkspaceVerifyReceiptSchema),
});

export type AgentWorkspaceVerifyAllReceiptParsed = z.infer<
  typeof AgentWorkspaceVerifyAllReceiptSchema
>;

// ─── AgentWorkspaceImportReceipt ─────────────────────────────────────────────

export const AgentWorkspaceImportReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_import.v1'),
  receipt: z.enum(['SCBE_WORKSPACE_IMPORT=1', 'SCBE_WORKSPACE_IMPORT=0']),
  source_export_path: z.string(),
  source_export_id: z.string(),
  source_manifest_sha256: z.string(),
  source_workspace_id: z.string(),
  target_workspace_id: z.string(),
  target_workspace_root: z.string(),
  imported_files: nonNegInt,
  imported_bytes: nonNegInt,
  imported_at: isoTs,
  verify_pass: z.boolean(),
  verify_mismatches: z.array(WorkspaceVerifyMismatchSchema),
  receipt_path: z.string(),
});

export type AgentWorkspaceImportReceiptParsed = z.infer<typeof AgentWorkspaceImportReceiptSchema>;

// ─── LineageEntry ─────────────────────────────────────────────────────────────

export const LineageEntrySchema = z.object({
  kind: z.enum(['formation', 'ingest', 'export', 'verify', 'import', 'trap_dispatch', 'unknown']),
  receipt_path: z.string(),
  receipt_name: z.string(),
  timestamp: z.string(),
  schema_version: z.string(),
  receipt: z.string(),
  export_id: z.string().optional(),
  manifest_sha256: z.string().optional(),
  manifest_intact: z.boolean().optional(),
  mismatch_count: nonNegInt.optional(),
  gate_decision: z.string().optional(),
  redirect_emitted: z.boolean().optional(),
  parse_error: z.string().optional(),
});

export type LineageEntryParsed = z.infer<typeof LineageEntrySchema>;

// ─── AgentWorkspaceLineageReceipt ────────────────────────────────────────────

export const AgentWorkspaceLineageReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_lineage.v1'),
  receipt: z.literal('SCBE_WORKSPACE_LINEAGE=1'),
  workspace_root: z.string(),
  workspace_id: z.string(),
  generated_at: isoTs,
  entries: z.array(LineageEntrySchema),
  formation_count: nonNegInt,
  ingest_count: nonNegInt,
  export_count: nonNegInt,
  verify_count: nonNegInt,
  import_count: nonNegInt,
  trap_dispatch_count: nonNegInt,
  trap_redirect_count: nonNegInt,
  unverified_exports: z.array(z.string()),
  failed_verifies: nonNegInt,
});

export type AgentWorkspaceLineageReceiptParsed = z.infer<typeof AgentWorkspaceLineageReceiptSchema>;

// ─── AgentWorkspaceReportReceipt ─────────────────────────────────────────────

export const FolderStatSchema = z.object({
  path: z.string(),
  file_count: nonNegInt,
  total_bytes: nonNegInt,
});

export const AgentWorkspaceReportReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.workspace_report.v1'),
  receipt: z.literal('SCBE_WORKSPACE_REPORT=1'),
  workspace_id: z.string(),
  workspace_root: z.string(),
  generated_at: isoTs,
  created_at: z.string(),
  folders: z.array(FolderStatSchema),
  lineage_summary: z.object({
    formation_count: nonNegInt,
    ingest_count: nonNegInt,
    export_count: nonNegInt,
    verify_count: nonNegInt,
    import_count: nonNegInt,
    trap_dispatch_count: nonNegInt,
    trap_redirect_count: nonNegInt,
    failed_verifies: nonNegInt,
    unverified_exports: z.array(z.string()),
  }),
  last_activity: z.string(),
  audit_health: z.enum(['green', 'amber', 'red']),
});

export type AgentWorkspaceReportReceiptParsed = z.infer<typeof AgentWorkspaceReportReceiptSchema>;

// ─── TmpCleanupReceipt ───────────────────────────────────────────────────────

export const TmpCleanupReceiptSchema = z.object({
  schema_version: z.literal('aethermoor.bus.tmp_cleanup.v1'),
  receipt: z.literal('SCBE_WORKSPACE_TMP_CLEANUP=1'),
  workspace_root: z.string(),
  deleted_count: nonNegInt,
  reclaimed_bytes: nonNegInt,
  dry_run: z.boolean(),
  cleaned_at: isoTs,
});

export type TmpCleanupReceiptParsed = z.infer<typeof TmpCleanupReceiptSchema>;

// ─── Boundary helper ─────────────────────────────────────────────────────────

export type ParseResult<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * Parse arbitrary data against a Zod schema and return a typed Result.
 * Never throws. Use at every disk-read boundary before trusting JSON content.
 */
export function parseReceipt<T>(
  raw: unknown,
  schema: z.ZodSchema<T>,
  label = 'receipt'
): ParseResult<T> {
  const result = schema.safeParse(raw);
  if (result.success) return { ok: true, data: result.data };
  const summary = result.error.issues
    .slice(0, 3)
    .map((i) => `${i.path.join('.') || '<root>'}: ${i.message}`)
    .join('; ');
  return { ok: false, error: `${label}: ${summary}` };
}
