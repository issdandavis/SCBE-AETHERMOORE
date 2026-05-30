import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';
import { WorkspaceExportManifestSchema, parseReceipt } from './schemas.js';
import { detectTaskType, decompose, scoreDialogue } from './semantic-bridge.js';
import { autoDiscoverTools, buildToolArgv, getTool } from './tools.js';

// Plugin + queue subsystems
export {
  type BusPlugin,
  type BusPluginContext,
  registerPlugin,
  unregisterPlugin,
  listPlugins,
  clearPlugins,
  autoDiscoverPlugins,
  runBeforeRunPlugins,
  runAfterRunPlugins,
} from './plugins.js';

export {
  type QueuedEvent,
  type QueueStatus,
  enqueueEvent,
  getEventStatus,
  getQueueStatus,
  processOneEvent,
  drainQueue,
  startQueueWorker,
} from './queue.js';

// Semantic atom scanner + dimensional decomposition engine
export {
  // Dimension axis
  type DimVec,
  type DimAxis,
  DIM_AXES,
  // Atom table (10 atoms: 4 domain + 6 discourse)
  type AtomEntry,
  ATOM_TABLE,
  // Core decomposition / recomposition
  type AtomHit,
  type DecompositionResult,
  type RecompositionResult,
  type DimensionalAnalysis,
  type DiscourseProfile,
  type DialogueDimension,
  type DialogueScoreResult,
  decompose,
  recompose,
  analyzeDimensions,
  detectDiscourseProfile,
  // Binary / hex encoding helpers
  combineDims,
  dimsToHex,
  hexToDims,
  dimsToBinary,
  // Legacy thin API (backwards-compat)
  type AtomLedger,
  scanAtoms,
  detectTaskType,
  buildAtomLedger,
  // Spoken longform dialogue bridge
  scoreDialogue,
} from './semantic-bridge.js';

// GeoSeal intent pipeline
export {
  type GeoSealPlan,
  type GeoSealPlanPolicy,
  type GeoSealPlanCommand,
  type PipelineRunResult,
  type GovernedMoveClass,
  type GovernedMoveRecord,
  type GovernedPipelineState,
  type TrajectoryGateResult,
  compilePlan,
  execPlan,
  runPipeline,
  parseShellTemplate,
  resolveRepoRoot,
  createGovernedPipelineState,
  loadGovernedPipelineState,
  saveGovernedPipelineState,
  classifyGovernedMove,
  reachableMoveSet,
  evaluateTrajectoryGate,
} from './pipeline.js';

// Structured output contracts
export {
  type JsonSchema,
  type ValidatedOutput,
  validateOutput,
  SummaryContract,
  CodeReviewContract,
  ResearchContract,
  GovernanceDecisionContract,
} from './contracts.js';

// Resilience (circuit breakers)
export {
  type CircuitState,
  type CircuitBreakerOptions,
  configureCircuitBreaker,
  resetCircuitBreaker,
  getCircuitStates,
  checkCircuit,
  recordSuccess,
  recordFailure,
  withCircuitBreaker,
} from './resilience.js';

export {
  type CliTool,
  registerTool,
  unregisterTool,
  listTools,
  getTool,
  clearTools,
  buildToolArgv,
  autoDiscoverTools,
} from './tools.js';

export {
  type RubixBrowserFace,
  type RubixBrowserBenchmarkCase,
  type RubixBrowserBenchmarkReport,
  type RubixBrowserBenchmarkRow,
  type RubixBrowserMove,
  type RubixBrowserPermission,
  type RubixBrowserPlan,
  RUBIX_BROWSER_BENCHMARK_CASES,
  RUBIX_BROWSER_FACES,
  buildRubixBrowserPlan,
  runRubixBrowserBenchmark,
} from './rubix-browser.js';

export {
  type ResumePacket,
  type ResumePacketOptions,
  type ToolCallRecord,
  type ToolLoopDetection,
  type ToolLoopDetectorOptions,
  createResumePacket,
  createToolLoopDetector,
} from './task-ledger.js';

export type AgentBusPrivacy = 'local_only' | 'remote_allowed' | string;

export interface AgentBusEvent {
  task: string;
  taskType?: string;
  operationCommand?: string;
  seriesId?: string;
  privacy?: AgentBusPrivacy;
  budgetCents?: number;
  dispatch?: boolean;
  dispatchProvider?: string;
  /** Name of a registered CliTool to dispatch to instead of scbe-system-cli.py. */
  tool?: string;
}

export interface RunOptions {
  repoRoot?: string;
  geosealBin?: string;
  python?: string;
  continueOnError?: boolean;
  /**
   * Optional persisted trajectory gate for GeoSeal pipelines.
   * When enabled, the pipeline checks whether the compiled plan is reachable
   * from the session's current governed state before execution.
   */
  governedState?:
    | boolean
    | {
        enabled?: boolean;
        sessionId?: string;
        statePath?: string;
        root?: string;
      };
}

export interface AgentBusResult {
  schema_version: 'scbe-agentbus-node-result-v1';
  event_index: number;
  started_at: string;
  finished_at: string;
  ok: boolean;
  exit_code: number | null;
  stderr_tail: string;
  event: {
    task_sha256: string | null;
    task_chars: number;
    series_id: string;
    operation_command_chars: number;
  };
  result: unknown;
  /** Full dimensional decomposition attached when atoms match the task text. */
  semantic?: import('./semantic-bridge.js').DecompositionResult;
  /** Discourse profile from compound atom patterns (null = none detected). */
  discourse_profile?: import('./semantic-bridge.js').DiscourseProfile;
  /** Spoken longform dialogue score when discourse atoms are detected. */
  dialogue_score?: import('./semantic-bridge.js').DialogueScoreResult;
}

export interface AgentBusServerHandle {
  url: string;
  server: Server;
  close: () => Promise<void>;
}

export interface AgentBusServerOptions extends RunOptions {
  host?: string;
  port?: number;
}

export interface AgentBusClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export interface WorkspaceOptions {
  root?: string;
  hint?: string;
}

export interface AgentWorkspaceReceipt {
  schema_version: 'aethermoor.bus.workspace_receipt.v1';
  receipt: 'SCBE_WORKSPACE_READY=1';
  workspace_id: string;
  workspace_root: string;
  created_at: string;
  formation: {
    schema_version: 'aethermoor.bus.workspace_formation.v1';
    default_root: '.aethermoor-bus/workspaces';
    folders: Array<{ path: string; purpose: string }>;
  };
  receipt_path: string;
}

export const WORKSPACE_FORMATION: AgentWorkspaceReceipt['formation'] = {
  schema_version: 'aethermoor.bus.workspace_formation.v1',
  default_root: '.aethermoor-bus/workspaces',
  folders: [
    { path: '00_inbox', purpose: 'raw drops, uploads, imports, unclassified files' },
    { path: '10_work', purpose: 'active editable working files' },
    { path: '20_receipts', purpose: 'governance verdicts, hashes, signatures, run receipts' },
    { path: '30_exports', purpose: 'customer-ready packets and handoff bundles' },
    { path: '40_refs', purpose: 'non-secret reference files and source notes' },
    { path: '90_tmp', purpose: 'scratch files, deleted after offload verification' },
  ],
};

const TASK_TYPES = new Set(['coding', 'review', 'research', 'governance', 'training', 'general']);

function slugify(value: string): string {
  return (
    String(value || 'workspace')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || 'workspace'
  );
}

function timestampId(date = new Date()): string {
  return date
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d{3}Z$/, 'Z');
}

export function createAgentWorkspace(options: WorkspaceOptions = {}): AgentWorkspaceReceipt {
  const baseRoot = path.resolve(options.root || WORKSPACE_FORMATION.default_root);
  const workspaceId = `${timestampId()}-${slugify(options.hint || 'workspace')}-${crypto
    .randomBytes(3)
    .toString('hex')}`;
  const workspaceRoot = path.join(baseRoot, workspaceId);
  fs.mkdirSync(workspaceRoot, { recursive: true });
  for (const folder of WORKSPACE_FORMATION.folders) {
    fs.mkdirSync(path.join(workspaceRoot, folder.path), { recursive: true });
  }
  const payload: AgentWorkspaceReceipt = {
    schema_version: 'aethermoor.bus.workspace_receipt.v1',
    receipt: 'SCBE_WORKSPACE_READY=1',
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    created_at: new Date().toISOString(),
    formation: WORKSPACE_FORMATION,
    receipt_path: path.join(workspaceRoot, '20_receipts', 'workspace.json'),
  };
  fs.writeFileSync(payload.receipt_path, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  return payload;
}

export interface WorkspaceExportOptions {
  workspaceRoot: string;
  out?: string;
  include?: string[];
}

export interface WorkspaceExportManifestEntry {
  path: string;
  sha256: string;
  bytes: number;
}

export interface WorkspaceExportManifest {
  schema_version: 'aethermoor.bus.workspace_export_manifest.v1';
  export_id: string;
  workspace_id: string;
  workspace_root: string;
  created_at: string;
  included_folders: string[];
  excluded_folders: string[];
  file_count: number;
  total_bytes: number;
  files: WorkspaceExportManifestEntry[];
}

export interface AgentWorkspaceExportReceipt {
  schema_version: 'aethermoor.bus.workspace_export.v1';
  receipt: 'SCBE_WORKSPACE_EXPORT=1';
  workspace_id: string;
  workspace_root: string;
  export_id: string;
  export_path: string;
  manifest_path: string;
  manifest_sha256: string;
  created_at: string;
  file_count: number;
  total_bytes: number;
  included_folders: string[];
  excluded_folders: string[];
  receipt_path: string;
}

const DEFAULT_EXPORT_INCLUDE = ['00_inbox', '10_work', '20_receipts', '40_refs'];
const NEVER_EXPORT = new Set(['30_exports', '90_tmp']);

function sha256OfFile(filePath: string): { hash: string; bytes: number } {
  const hash = crypto.createHash('sha256');
  const data = fs.readFileSync(filePath);
  hash.update(data);
  return { hash: hash.digest('hex'), bytes: data.length };
}

/** Streaming variant — constant memory regardless of file size. */
function sha256OfFileAsync(filePath: string): Promise<{ hash: string; bytes: number }> {
  return new Promise((resolve, reject) => {
    const hasher = crypto.createHash('sha256');
    let bytes = 0;
    const stream = fs.createReadStream(filePath);
    stream.on('data', (chunk: Buffer | string) => {
      const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      bytes += buf.length;
      hasher.update(buf);
    });
    stream.on('end', () => resolve({ hash: hasher.digest('hex'), bytes }));
    stream.on('error', reject);
  });
}

function walkFiles(root: string, relPrefix = ''): string[] {
  const out: string[] = [];
  const stack: Array<{ abs: string; rel: string }> = [{ abs: root, rel: relPrefix }];
  while (stack.length > 0) {
    const next = stack.pop()!;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(next.abs, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const abs = path.join(next.abs, entry.name);
      const rel = next.rel ? `${next.rel}/${entry.name}` : entry.name;
      if (entry.isSymbolicLink()) continue;
      if (entry.isDirectory()) {
        stack.push({ abs, rel });
      } else if (entry.isFile()) {
        out.push(rel);
      }
    }
  }
  out.sort();
  return out;
}

export function exportAgentWorkspace(options: WorkspaceExportOptions): AgentWorkspaceExportReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  // Recover workspace_id from the formation receipt when present; fall back to basename.
  let workspaceId = path.basename(workspaceRoot);
  const formationReceiptPath = path.join(workspaceRoot, '20_receipts', 'workspace.json');
  if (fs.existsSync(formationReceiptPath)) {
    try {
      const raw = fs.readFileSync(formationReceiptPath, 'utf8');
      const parsed = JSON.parse(raw) as { workspace_id?: string };
      if (parsed.workspace_id) workspaceId = parsed.workspace_id;
    } catch {
      // tolerate corrupt receipt — keep basename fallback
    }
  }

  const requestedInclude = (
    options.include && options.include.length > 0 ? options.include : DEFAULT_EXPORT_INCLUDE
  ).filter((folder) => !NEVER_EXPORT.has(folder));
  const includedFolders = requestedInclude.filter((folder) =>
    fs.existsSync(path.join(workspaceRoot, folder))
  );
  const excludedFolders = Array.from(NEVER_EXPORT);

  const exportId = `${timestampId()}-${slugify(options.out || 'export')}-${crypto
    .randomBytes(3)
    .toString('hex')}`;
  const exportPath = path.join(workspaceRoot, '30_exports', exportId);
  fs.mkdirSync(exportPath, { recursive: true });

  const manifestEntries: WorkspaceExportManifestEntry[] = [];
  let totalBytes = 0;
  for (const folder of includedFolders) {
    const folderAbs = path.join(workspaceRoot, folder);
    const relFiles = walkFiles(folderAbs);
    for (const rel of relFiles) {
      const srcAbs = path.join(folderAbs, rel);
      const destRel = `${folder}/${rel}`;
      const destAbs = path.join(exportPath, destRel);
      fs.mkdirSync(path.dirname(destAbs), { recursive: true });
      fs.copyFileSync(srcAbs, destAbs);
      const { hash, bytes } = sha256OfFile(destAbs);
      manifestEntries.push({ path: destRel, sha256: hash, bytes });
      totalBytes += bytes;
    }
  }

  const manifest: WorkspaceExportManifest = {
    schema_version: 'aethermoor.bus.workspace_export_manifest.v1',
    export_id: exportId,
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    created_at: new Date().toISOString(),
    included_folders: includedFolders,
    excluded_folders: excludedFolders,
    file_count: manifestEntries.length,
    total_bytes: totalBytes,
    files: manifestEntries,
  };
  const manifestPath = path.join(exportPath, 'manifest.json');
  const manifestJson = `${JSON.stringify(manifest, null, 2)}\n`;
  fs.writeFileSync(manifestPath, manifestJson, 'utf8');
  const manifestSha256 = crypto.createHash('sha256').update(manifestJson).digest('hex');

  const receiptPath = path.join(workspaceRoot, '20_receipts', `export-${exportId}.json`);
  fs.mkdirSync(path.dirname(receiptPath), { recursive: true });
  const receipt: AgentWorkspaceExportReceipt = {
    schema_version: 'aethermoor.bus.workspace_export.v1',
    receipt: 'SCBE_WORKSPACE_EXPORT=1',
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    export_id: exportId,
    export_path: exportPath,
    manifest_path: manifestPath,
    manifest_sha256: manifestSha256,
    created_at: manifest.created_at,
    file_count: manifest.file_count,
    total_bytes: manifest.total_bytes,
    included_folders: includedFolders,
    excluded_folders: excludedFolders,
    receipt_path: receiptPath,
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}

/**
 * Async (streaming) variant of {@link exportAgentWorkspace}.
 * Hashes each file via createReadStream — safe for large files, no OOM risk.
 */
export async function exportAgentWorkspaceAsync(
  options: WorkspaceExportOptions
): Promise<AgentWorkspaceExportReceipt> {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  let workspaceId = path.basename(workspaceRoot);
  const formationReceiptPath = path.join(workspaceRoot, '20_receipts', 'workspace.json');
  if (fs.existsSync(formationReceiptPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(formationReceiptPath, 'utf8')) as {
        workspace_id?: string;
      };
      if (parsed.workspace_id) workspaceId = parsed.workspace_id;
    } catch {
      /* tolerate */
    }
  }

  const requestedInclude = (
    options.include && options.include.length > 0 ? options.include : DEFAULT_EXPORT_INCLUDE
  ).filter((folder) => !NEVER_EXPORT.has(folder));

  const exportId = `${timestampId()}-${crypto.randomBytes(3).toString('hex')}`;
  const exportBase = options.out
    ? path.resolve(options.out)
    : path.join(workspaceRoot, '30_exports');
  const exportPath = path.join(exportBase, exportId);
  fs.mkdirSync(exportPath, { recursive: true });

  const includedFolders: string[] = [];
  const excludedFolders: string[] = [];
  const manifestEntries: WorkspaceExportManifestEntry[] = [];
  let totalBytes = 0;

  for (const folder of WORKSPACE_FORMATION.folders.map((f) => f.path)) {
    if (NEVER_EXPORT.has(folder)) {
      excludedFolders.push(folder);
      continue;
    }
    if (!requestedInclude.includes(folder)) {
      excludedFolders.push(folder);
      continue;
    }
    includedFolders.push(folder);
    const srcFolder = path.join(workspaceRoot, folder);
    if (!fs.existsSync(srcFolder)) continue;
    for (const rel of walkFiles(srcFolder)) {
      const srcAbs = path.join(srcFolder, rel);
      const destRel = `${folder}/${rel}`;
      const destAbs = path.join(exportPath, destRel);
      fs.mkdirSync(path.dirname(destAbs), { recursive: true });
      fs.copyFileSync(srcAbs, destAbs);
      const { hash, bytes } = await sha256OfFileAsync(destAbs);
      manifestEntries.push({ path: destRel, sha256: hash, bytes });
      totalBytes += bytes;
    }
  }

  const manifest: WorkspaceExportManifest = {
    schema_version: 'aethermoor.bus.workspace_export_manifest.v1',
    export_id: exportId,
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    created_at: new Date().toISOString(),
    included_folders: includedFolders,
    excluded_folders: excludedFolders,
    file_count: manifestEntries.length,
    total_bytes: totalBytes,
    files: manifestEntries,
  };
  const manifestPath = path.join(exportPath, 'manifest.json');
  const manifestJson = `${JSON.stringify(manifest, null, 2)}\n`;
  fs.writeFileSync(manifestPath, manifestJson, 'utf8');
  const manifestSha256 = crypto.createHash('sha256').update(manifestJson).digest('hex');

  const receiptPath = path.join(workspaceRoot, '20_receipts', `export-${exportId}.json`);
  fs.mkdirSync(path.dirname(receiptPath), { recursive: true });
  const receipt: AgentWorkspaceExportReceipt = {
    schema_version: 'aethermoor.bus.workspace_export.v1',
    receipt: 'SCBE_WORKSPACE_EXPORT=1',
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    export_id: exportId,
    export_path: exportPath,
    manifest_path: manifestPath,
    manifest_sha256: manifestSha256,
    created_at: manifest.created_at,
    file_count: manifest.file_count,
    total_bytes: manifest.total_bytes,
    included_folders: includedFolders,
    excluded_folders: excludedFolders,
    receipt_path: receiptPath,
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}

export interface WorkspaceVerifyOptions {
  exportPath: string;
  /**
   * When true (default), write the verify receipt to
   * `<workspaceRoot>/20_receipts/verify-<export-id>-<utc-ts>.json` so that
   * `lineageAgentWorkspace()` can pick it up. Set to false in CI checks that
   * shouldn't mutate the workspace, or for ad-hoc local audits.
   */
  persistReceipt?: boolean;
}

export interface WorkspaceVerifyMismatch {
  path: string;
  reason: 'sha256_mismatch' | 'missing_file' | 'extra_file' | 'bytes_mismatch';
  expected_sha256?: string;
  actual_sha256?: string;
  expected_bytes?: number;
  actual_bytes?: number;
}

export interface AgentWorkspaceVerifyReceipt {
  schema_version: 'aethermoor.bus.workspace_verify.v1';
  receipt: 'SCBE_WORKSPACE_VERIFY_PASS=1' | 'SCBE_WORKSPACE_VERIFY_PASS=0';
  export_path: string;
  manifest_path: string;
  manifest_sha256_claimed: string;
  manifest_sha256_actual: string;
  manifest_intact: boolean;
  file_count_claimed: number;
  file_count_actual: number;
  total_bytes_claimed: number;
  total_bytes_actual: number;
  mismatches: WorkspaceVerifyMismatch[];
  verified_at: string;
  /**
   * Absolute path to the receipt written under `<workspaceRoot>/20_receipts/`
   * when `persistReceipt` was true. Empty string when persistence was skipped
   * or when the workspace root could not be recovered from the manifest.
   */
  receipt_path: string;
}

/**
 * Walk a previously-exported workspace folder and re-verify every sha256
 * against the manifest. Detects four classes of tampering:
 *   - sha256_mismatch: a file's content has been modified
 *   - bytes_mismatch:  byte count differs (subset of sha256_mismatch)
 *   - missing_file:    a manifested file is no longer present
 *   - extra_file:      a file is present that the manifest does not list
 *
 * Also re-hashes manifest.json itself and compares to the export receipt's
 * `manifest_sha256` field (read separately). This is the full chain-of-custody
 * audit — the receipt anchors the manifest sha256, the manifest anchors every
 * file sha256.
 */
export function verifyAgentWorkspaceExport(
  options: WorkspaceVerifyOptions
): AgentWorkspaceVerifyReceipt {
  const exportPath = path.resolve(options.exportPath);
  const manifestPath = path.join(exportPath, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`manifest not found at ${manifestPath}`);
  }
  const manifestBytes = fs.readFileSync(manifestPath);
  const manifestActualSha = crypto.createHash('sha256').update(manifestBytes).digest('hex');
  const manifestParsed = parseReceipt(
    JSON.parse(manifestBytes.toString('utf8')),
    WorkspaceExportManifestSchema,
    manifestPath
  );
  if (!manifestParsed.ok) {
    throw new Error(`manifest schema validation failed: ${manifestParsed.error}`);
  }
  const manifest: WorkspaceExportManifest = manifestParsed.data;

  // The manifest carries the export receipt's record of its own sha256 only
  // indirectly — read the matching export receipt under 20_receipts when
  // available. Falls back to comparing only the per-file hashes.
  let manifestClaimedSha = '';
  // Receipt sits at <workspaceRoot>/20_receipts/export-<export-id>.json.
  // workspaceRoot can be recovered from manifest.workspace_root; fall back to
  // walking up from exportPath.
  try {
    const receiptDir = path.join(manifest.workspace_root, '20_receipts');
    const receiptName = `export-${manifest.export_id}.json`;
    const receiptPath = path.join(receiptDir, receiptName);
    if (fs.existsSync(receiptPath)) {
      const exportReceipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
      if (typeof exportReceipt.manifest_sha256 === 'string') {
        manifestClaimedSha = exportReceipt.manifest_sha256;
      }
    }
  } catch {
    // tolerate: missing receipt just means we can't anchor the manifest hash,
    // but per-file verification still runs below.
  }

  const mismatches: WorkspaceVerifyMismatch[] = [];

  // Build the set of present files (excluding manifest.json itself).
  const presentFiles = walkFiles(exportPath).filter((rel) => rel !== 'manifest.json');
  const manifestPaths = new Set(manifest.files.map((f) => f.path));

  // 1. Verify each manifest entry against actual content.
  let actualBytes = 0;
  for (const entry of manifest.files) {
    const abs = path.join(exportPath, entry.path);
    if (!fs.existsSync(abs)) {
      mismatches.push({
        path: entry.path,
        reason: 'missing_file',
        expected_sha256: entry.sha256,
        expected_bytes: entry.bytes,
      });
      continue;
    }
    const { hash, bytes } = sha256OfFile(abs);
    actualBytes += bytes;
    if (hash !== entry.sha256) {
      mismatches.push({
        path: entry.path,
        reason: 'sha256_mismatch',
        expected_sha256: entry.sha256,
        actual_sha256: hash,
        expected_bytes: entry.bytes,
        actual_bytes: bytes,
      });
    } else if (bytes !== entry.bytes) {
      mismatches.push({
        path: entry.path,
        reason: 'bytes_mismatch',
        expected_bytes: entry.bytes,
        actual_bytes: bytes,
      });
    }
  }

  // 2. Flag extra files (present but not in manifest).
  for (const rel of presentFiles) {
    if (!manifestPaths.has(rel)) {
      mismatches.push({ path: rel, reason: 'extra_file' });
    }
  }

  const manifestIntact =
    manifestClaimedSha === '' ? true : manifestActualSha === manifestClaimedSha;
  const passed = mismatches.length === 0 && manifestIntact;

  const receipt: AgentWorkspaceVerifyReceipt = {
    schema_version: 'aethermoor.bus.workspace_verify.v1',
    receipt: passed ? 'SCBE_WORKSPACE_VERIFY_PASS=1' : 'SCBE_WORKSPACE_VERIFY_PASS=0',
    export_path: exportPath,
    manifest_path: manifestPath,
    manifest_sha256_claimed: manifestClaimedSha,
    manifest_sha256_actual: manifestActualSha,
    manifest_intact: manifestIntact,
    file_count_claimed: manifest.file_count,
    file_count_actual: presentFiles.length,
    total_bytes_claimed: manifest.total_bytes,
    total_bytes_actual: actualBytes,
    mismatches,
    verified_at: new Date().toISOString(),
    receipt_path: '',
  };

  const shouldPersist = options.persistReceipt !== false;
  if (shouldPersist && manifest.workspace_root && manifest.export_id) {
    try {
      const receiptsDir = path.join(manifest.workspace_root, '20_receipts');
      if (fs.existsSync(receiptsDir)) {
        const ts = receipt.verified_at.replace(/[:.]/g, '-');
        const receiptName = `verify-${manifest.export_id}-${ts}.json`;
        const receiptPath = path.join(receiptsDir, receiptName);
        receipt.receipt_path = receiptPath;
        // serialize with receipt_path populated so the on-disk and in-memory
        // representations are identical
        fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
      }
    } catch {
      // persistence is best-effort; never block a verify result on a write
      // failure. receipt_path stays "" if we couldn't write.
      receipt.receipt_path = '';
    }
  }

  return receipt;
}

/**
 * Async (streaming) variant of {@link verifyAgentWorkspaceExport}.
 * Hashes each file via createReadStream — safe for large exports, no OOM risk.
 */
export async function verifyAgentWorkspaceExportAsync(
  options: WorkspaceVerifyOptions
): Promise<AgentWorkspaceVerifyReceipt> {
  const exportPath = path.resolve(options.exportPath);
  const manifestPath = path.join(exportPath, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`manifest not found at ${manifestPath}`);
  }
  const manifestBytes = fs.readFileSync(manifestPath);
  const manifestActualSha = crypto.createHash('sha256').update(manifestBytes).digest('hex');
  const manifestParsed = parseReceipt(
    JSON.parse(manifestBytes.toString('utf8')),
    WorkspaceExportManifestSchema,
    manifestPath
  );
  if (!manifestParsed.ok) {
    throw new Error(`manifest schema validation failed: ${manifestParsed.error}`);
  }
  const manifest: WorkspaceExportManifest = manifestParsed.data;

  let manifestClaimedSha = '';
  try {
    const receiptDir = path.join(manifest.workspace_root, '20_receipts');
    const receiptName = `export-${manifest.export_id}.json`;
    const receiptPath = path.join(receiptDir, receiptName);
    if (fs.existsSync(receiptPath)) {
      const exportReceipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
      if (typeof exportReceipt.manifest_sha256 === 'string') {
        manifestClaimedSha = exportReceipt.manifest_sha256;
      }
    }
  } catch {
    /* tolerate */
  }

  const mismatches: WorkspaceVerifyMismatch[] = [];
  const presentFiles = walkFiles(exportPath).filter((rel) => rel !== 'manifest.json');
  const manifestPaths = new Set(manifest.files.map((f) => f.path));

  let actualBytes = 0;
  for (const entry of manifest.files) {
    const abs = path.join(exportPath, entry.path);
    if (!fs.existsSync(abs)) {
      mismatches.push({
        path: entry.path,
        reason: 'missing_file',
        expected_sha256: entry.sha256,
        expected_bytes: entry.bytes,
      });
      continue;
    }
    const { hash, bytes } = await sha256OfFileAsync(abs);
    actualBytes += bytes;
    if (hash !== entry.sha256) {
      mismatches.push({
        path: entry.path,
        reason: 'sha256_mismatch',
        expected_sha256: entry.sha256,
        actual_sha256: hash,
        expected_bytes: entry.bytes,
        actual_bytes: bytes,
      });
    } else if (bytes !== entry.bytes) {
      mismatches.push({
        path: entry.path,
        reason: 'bytes_mismatch',
        expected_bytes: entry.bytes,
        actual_bytes: bytes,
      });
    }
  }

  for (const rel of presentFiles) {
    if (!manifestPaths.has(rel)) {
      mismatches.push({ path: rel, reason: 'extra_file' });
    }
  }

  const manifestIntact =
    manifestClaimedSha === '' ? true : manifestActualSha === manifestClaimedSha;
  const passed = mismatches.length === 0 && manifestIntact;

  const receipt: AgentWorkspaceVerifyReceipt = {
    schema_version: 'aethermoor.bus.workspace_verify.v1',
    receipt: passed ? 'SCBE_WORKSPACE_VERIFY_PASS=1' : 'SCBE_WORKSPACE_VERIFY_PASS=0',
    export_path: exportPath,
    manifest_path: manifestPath,
    manifest_sha256_claimed: manifestClaimedSha,
    manifest_sha256_actual: manifestActualSha,
    manifest_intact: manifestIntact,
    file_count_claimed: manifest.file_count,
    file_count_actual: presentFiles.length,
    total_bytes_claimed: manifest.total_bytes,
    total_bytes_actual: actualBytes,
    mismatches,
    verified_at: new Date().toISOString(),
    receipt_path: '',
  };

  const shouldPersist = options.persistReceipt !== false;
  if (shouldPersist && manifest.workspace_root && manifest.export_id) {
    try {
      const receiptsDir = path.join(manifest.workspace_root, '20_receipts');
      if (fs.existsSync(receiptsDir)) {
        const ts = receipt.verified_at.replace(/[:.]/g, '-');
        const receiptName = `verify-${manifest.export_id}-${ts}.json`;
        const receiptPath = path.join(receiptsDir, receiptName);
        receipt.receipt_path = receiptPath;
        fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
      }
    } catch {
      receipt.receipt_path = '';
    }
  }

  return receipt;
}

export interface WorkspaceIngestOptions {
  workspaceRoot: string;
  sourcePath: string;
  /** Optional override for the basename used inside 00_inbox/. Defaults to the
   * source file's basename. Useful when ingesting multiple files with
   * conflicting names. */
  rename?: string;
}

export interface AgentWorkspaceIngestReceipt {
  schema_version: 'aethermoor.bus.workspace_ingest.v1';
  receipt: 'SCBE_WORKSPACE_INGEST=1';
  workspace_id: string;
  workspace_root: string;
  source_path: string;
  destination_path: string;
  destination_rel: string;
  source_sha256: string;
  destination_sha256: string;
  bytes: number;
  ingested_at: string;
  receipt_path: string;
}

/**
 * Copy a file from any path into `<workspaceRoot>/00_inbox/` with a sha256
 * receipt persisted under `20_receipts/ingest-<utc-ts>-<basename>.json`. The
 * receipt records both source_sha256 and destination_sha256 (they must match;
 * mismatch indicates filesystem corruption during copy and throws). Closes the
 * audit chain at the entry point — before this, files appeared in 00_inbox/
 * with no provenance.
 */
export function ingestIntoAgentWorkspace(
  options: WorkspaceIngestOptions
): AgentWorkspaceIngestReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  const sourcePath = path.resolve(options.sourcePath);
  if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
    throw new Error(`source file not found at ${sourcePath}`);
  }
  const inboxDir = path.join(workspaceRoot, '00_inbox');
  if (!fs.existsSync(inboxDir)) fs.mkdirSync(inboxDir, { recursive: true });

  const destName = (options.rename ?? path.basename(sourcePath)).trim();
  if (!destName || destName.includes('/') || destName.includes('\\')) {
    throw new Error(`invalid rename target: ${JSON.stringify(destName)}`);
  }
  const destPath = path.join(inboxDir, destName);
  fs.copyFileSync(sourcePath, destPath);
  const sourceHash = sha256OfFile(sourcePath);
  const destHash = sha256OfFile(destPath);
  if (sourceHash.hash !== destHash.hash) {
    throw new Error(
      `sha256 mismatch after copy (source=${sourceHash.hash}, dest=${destHash.hash})`
    );
  }

  let workspaceId = path.basename(workspaceRoot);
  const formationReceiptPath = path.join(workspaceRoot, '20_receipts', 'workspace.json');
  if (fs.existsSync(formationReceiptPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(formationReceiptPath, 'utf8')) as {
        workspace_id?: string;
      };
      if (parsed.workspace_id) workspaceId = parsed.workspace_id;
    } catch {
      // tolerate
    }
  }

  const ingestedAt = new Date().toISOString();
  const tsSafe = ingestedAt.replace(/[:.]/g, '-');
  const receiptName = `ingest-${tsSafe}-${destName}.json`;
  const receiptsDir = path.join(workspaceRoot, '20_receipts');
  if (!fs.existsSync(receiptsDir)) fs.mkdirSync(receiptsDir, { recursive: true });
  const receiptPath = path.join(receiptsDir, receiptName);
  const receipt: AgentWorkspaceIngestReceipt = {
    schema_version: 'aethermoor.bus.workspace_ingest.v1',
    receipt: 'SCBE_WORKSPACE_INGEST=1',
    workspace_id: workspaceId,
    workspace_root: workspaceRoot,
    source_path: sourcePath,
    destination_path: destPath,
    destination_rel: `00_inbox/${destName}`,
    source_sha256: sourceHash.hash,
    destination_sha256: destHash.hash,
    bytes: destHash.bytes,
    ingested_at: ingestedAt,
    receipt_path: receiptPath,
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}

export interface WorkspaceVerifyAllOptions {
  workspaceRoot: string;
  persistReceipt?: boolean;
}

export interface AgentWorkspaceVerifyAllReceipt {
  schema_version: 'aethermoor.bus.workspace_verify_all.v1';
  receipt: 'SCBE_WORKSPACE_VERIFY_ALL_PASS=1' | 'SCBE_WORKSPACE_VERIFY_ALL_PASS=0';
  workspace_root: string;
  workspace_id: string;
  verified_at: string;
  export_count: number;
  passed_count: number;
  failed_count: number;
  results: AgentWorkspaceVerifyReceipt[];
}

/**
 * Verify every export under `<workspaceRoot>/30_exports/`. Runs the same
 * single-export verifier on each, aggregates pass/fail counts, and (by default)
 * persists individual verify receipts so `lineageAgentWorkspace()` updates
 * automatically. Returns SCBE_WORKSPACE_VERIFY_ALL_PASS=1 only when every
 * export passes and no manifest tampering was detected.
 */
export function verifyAllAgentWorkspaceExports(
  options: WorkspaceVerifyAllOptions
): AgentWorkspaceVerifyAllReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  let workspaceId = path.basename(workspaceRoot);
  const formationReceiptPath = path.join(workspaceRoot, '20_receipts', 'workspace.json');
  if (fs.existsSync(formationReceiptPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(formationReceiptPath, 'utf8')) as {
        workspace_id?: string;
      };
      if (parsed.workspace_id) workspaceId = parsed.workspace_id;
    } catch {
      // tolerate
    }
  }
  const exportsDir = path.join(workspaceRoot, '30_exports');
  const results: AgentWorkspaceVerifyReceipt[] = [];
  let passed = 0;
  let failed = 0;
  if (fs.existsSync(exportsDir)) {
    const exportDirs = fs
      .readdirSync(exportsDir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => path.join(exportsDir, d.name))
      .filter((abs) => fs.existsSync(path.join(abs, 'manifest.json')))
      .sort();
    for (const exportPath of exportDirs) {
      const verifyReceipt = verifyAgentWorkspaceExport({
        exportPath,
        persistReceipt: options.persistReceipt !== false,
      });
      results.push(verifyReceipt);
      if (verifyReceipt.receipt === 'SCBE_WORKSPACE_VERIFY_PASS=1') passed += 1;
      else failed += 1;
    }
  }
  return {
    schema_version: 'aethermoor.bus.workspace_verify_all.v1',
    receipt: failed === 0 ? 'SCBE_WORKSPACE_VERIFY_ALL_PASS=1' : 'SCBE_WORKSPACE_VERIFY_ALL_PASS=0',
    workspace_root: workspaceRoot,
    workspace_id: workspaceId,
    verified_at: new Date().toISOString(),
    export_count: results.length,
    passed_count: passed,
    failed_count: failed,
    results,
  };
}

export interface WorkspaceImportOptions {
  exportPath: string;
  /** Parent directory under which the new workspace folder is created.
   * Defaults to `.aethermoor-bus/workspaces`. */
  targetRoot?: string;
  /** Optional hint baked into the new workspace id. Defaults to `import`. */
  hint?: string;
}

export interface AgentWorkspaceImportReceipt {
  schema_version: 'aethermoor.bus.workspace_import.v1';
  receipt: 'SCBE_WORKSPACE_IMPORT=1' | 'SCBE_WORKSPACE_IMPORT=0';
  source_export_path: string;
  source_export_id: string;
  source_manifest_sha256: string;
  source_workspace_id: string;
  target_workspace_id: string;
  target_workspace_root: string;
  imported_files: number;
  imported_bytes: number;
  imported_at: string;
  verify_pass: boolean;
  verify_mismatches: WorkspaceVerifyMismatch[];
  receipt_path: string;
}

/**
 * Cold-restore a workspace from a previously-exported manifest. Always runs
 * the standard verify FIRST and refuses to import any export that fails any
 * tamper class. The new workspace records the source export's manifest sha256
 * as its provenance anchor — `lineageAgentWorkspace` recognizes the resulting
 * import receipt and chains it after formation.
 *
 * The new workspace's own formation receipt is written first (so 20_receipts/
 * is populated for downstream commands), followed by the import receipt.
 */
export function importAgentWorkspace(options: WorkspaceImportOptions): AgentWorkspaceImportReceipt {
  const exportPath = path.resolve(options.exportPath);
  // Verify FIRST. Refuse to import any tampered export.
  const verifyReceipt = verifyAgentWorkspaceExport({ exportPath, persistReceipt: false });
  if (verifyReceipt.receipt !== 'SCBE_WORKSPACE_VERIFY_PASS=1') {
    throw new Error(
      `cannot import ${exportPath}: verify failed with ${verifyReceipt.mismatches.length} ` +
        `mismatch(es) (first reason: ${verifyReceipt.mismatches[0]?.reason ?? 'unknown'})`
    );
  }
  const manifestPath = path.join(exportPath, 'manifest.json');
  const manifest: WorkspaceExportManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  // Form a new workspace under targetRoot.
  const hint = (options.hint || 'import').trim();
  const target = createAgentWorkspace({ root: options.targetRoot, hint });

  // Restore every manifested file into the new workspace at its original
  // relative path (which already includes the leading folder, e.g.
  // `00_inbox/note.txt`). Skip the source's `20_receipts/` — the new
  // workspace has its own audit chain anchored by the import receipt's
  // source_export_id + source_manifest_sha256 fields. Copying the source's
  // workspace.json would overwrite the new workspace's formation receipt
  // and cause lineageAgentWorkspace to report the source's workspace_id.
  let importedBytes = 0;
  let importedFiles = 0;
  for (const entry of manifest.files) {
    if (entry.path.startsWith('20_receipts/')) continue;
    const src = path.join(exportPath, entry.path);
    const dest = path.join(target.workspace_root, entry.path);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    // Re-verify the restored byte count matches the manifest.
    const { bytes } = sha256OfFile(dest);
    importedBytes += bytes;
    importedFiles += 1;
  }

  const importedAt = new Date().toISOString();
  const tsSafe = importedAt.replace(/[:.]/g, '-');
  const receiptName = `import-${manifest.export_id}-${tsSafe}.json`;
  const receiptPath = path.join(target.workspace_root, '20_receipts', receiptName);
  const receipt: AgentWorkspaceImportReceipt = {
    schema_version: 'aethermoor.bus.workspace_import.v1',
    receipt: 'SCBE_WORKSPACE_IMPORT=1',
    source_export_path: exportPath,
    source_export_id: manifest.export_id,
    source_manifest_sha256: verifyReceipt.manifest_sha256_actual,
    source_workspace_id: manifest.workspace_id,
    target_workspace_id: target.workspace_id,
    target_workspace_root: target.workspace_root,
    imported_files: importedFiles,
    imported_bytes: importedBytes,
    imported_at: importedAt,
    verify_pass: true,
    verify_mismatches: [],
    receipt_path: receiptPath,
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}

export interface WorkspaceReportOptions {
  workspaceRoot: string;
}

export interface FolderStat {
  path: string;
  file_count: number;
  total_bytes: number;
}

export interface AgentWorkspaceReportReceipt {
  schema_version: 'aethermoor.bus.workspace_report.v1';
  receipt: 'SCBE_WORKSPACE_REPORT=1';
  workspace_id: string;
  workspace_root: string;
  generated_at: string;
  created_at: string;
  folders: FolderStat[];
  lineage_summary: {
    formation_count: number;
    ingest_count: number;
    export_count: number;
    verify_count: number;
    import_count: number;
    trap_dispatch_count: number;
    trap_redirect_count: number;
    failed_verifies: number;
    unverified_exports: string[];
  };
  last_activity: string;
  audit_health: 'green' | 'amber' | 'red';
}

const REPORT_FOLDERS = ['00_inbox', '10_work', '20_receipts', '30_exports', '40_refs', '90_tmp'];

function folderStat(workspaceRoot: string, folder: string): FolderStat {
  const abs = path.join(workspaceRoot, folder);
  if (!fs.existsSync(abs)) {
    return { path: folder, file_count: 0, total_bytes: 0 };
  }
  let fileCount = 0;
  let totalBytes = 0;
  for (const rel of walkFiles(abs)) {
    try {
      const st = fs.statSync(path.join(abs, rel));
      if (st.isFile()) {
        fileCount += 1;
        totalBytes += st.size;
      }
    } catch {
      // tolerate missing/locked file
    }
  }
  return { path: folder, file_count: fileCount, total_bytes: totalBytes };
}

/**
 * Operator dashboard. Returns folder file/byte counts, lineage summary, and
 * an `audit_health` color: green if every export has a passing verify, amber
 * if there are unverified exports, red if any verify failed. Pure read-only.
 */
export function reportAgentWorkspace(options: WorkspaceReportOptions): AgentWorkspaceReportReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  const lineage = lineageAgentWorkspace({ workspaceRoot });
  let createdAt = '';
  const formation = lineage.entries.find((e) => e.kind === 'formation');
  if (formation) createdAt = formation.timestamp;
  const lastActivity =
    lineage.entries.length > 0 ? lineage.entries[lineage.entries.length - 1].timestamp : createdAt;
  const folders: FolderStat[] = REPORT_FOLDERS.map((f) => folderStat(workspaceRoot, f));
  let auditHealth: 'green' | 'amber' | 'red' = 'green';
  if (lineage.failed_verifies > 0) auditHealth = 'red';
  else if (lineage.unverified_exports.length > 0 && lineage.export_count > 0) auditHealth = 'amber';
  return {
    schema_version: 'aethermoor.bus.workspace_report.v1',
    receipt: 'SCBE_WORKSPACE_REPORT=1',
    workspace_id: lineage.workspace_id,
    workspace_root: workspaceRoot,
    generated_at: new Date().toISOString(),
    created_at: createdAt,
    folders,
    lineage_summary: {
      formation_count: lineage.formation_count,
      ingest_count: lineage.ingest_count,
      export_count: lineage.export_count,
      verify_count: lineage.verify_count,
      import_count: lineage.import_count,
      trap_dispatch_count: lineage.trap_dispatch_count,
      trap_redirect_count: lineage.trap_redirect_count,
      failed_verifies: lineage.failed_verifies,
      unverified_exports: lineage.unverified_exports,
    },
    last_activity: lastActivity,
    audit_health: auditHealth,
  };
}

export interface TmpCleanupOptions {
  workspaceRoot: string;
  /** Delete files older than this many milliseconds. Default: 7 days. */
  maxAgeMs?: number;
  /** If true, only report what would be deleted without removing files. */
  dryRun?: boolean;
}

export interface TmpCleanupReceipt {
  schema_version: 'aethermoor.bus.tmp_cleanup.v1';
  receipt: 'SCBE_WORKSPACE_TMP_CLEANUP=1';
  workspace_root: string;
  deleted_count: number;
  reclaimed_bytes: number;
  dry_run: boolean;
  cleaned_at: string;
}

/**
 * Delete files in 90_tmp/ older than `maxAgeMs`.
 * Default age: 7 days. Set `dryRun: true` to preview without deleting.
 */
export function cleanupWorkspaceTmp(options: TmpCleanupOptions): TmpCleanupReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  const tmpDir = path.join(workspaceRoot, '90_tmp');
  const maxAge = options.maxAgeMs ?? 1000 * 60 * 60 * 24 * 7;
  const now = Date.now();
  let deletedCount = 0;
  let reclaimedBytes = 0;

  if (fs.existsSync(tmpDir)) {
    for (const rel of walkFiles(tmpDir)) {
      const abs = path.join(tmpDir, rel);
      try {
        const st = fs.statSync(abs);
        if (st.isFile() && now - st.mtime.getTime() > maxAge) {
          if (!options.dryRun) {
            fs.unlinkSync(abs);
          }
          deletedCount += 1;
          reclaimedBytes += st.size;
        }
      } catch {
        // tolerate locked/missing file
      }
    }
  }

  return {
    schema_version: 'aethermoor.bus.tmp_cleanup.v1',
    receipt: 'SCBE_WORKSPACE_TMP_CLEANUP=1',
    workspace_root: workspaceRoot,
    deleted_count: deletedCount,
    reclaimed_bytes: reclaimedBytes,
    dry_run: options.dryRun ?? false,
    cleaned_at: new Date().toISOString(),
  };
}

export interface WorkspaceLineageOptions {
  workspaceRoot: string;
}

export interface LineageEntry {
  kind: 'formation' | 'ingest' | 'export' | 'verify' | 'import' | 'trap_dispatch' | 'unknown';
  receipt_path: string;
  receipt_name: string;
  timestamp: string;
  schema_version: string;
  receipt: string;
  export_id?: string;
  manifest_sha256?: string;
  manifest_intact?: boolean;
  mismatch_count?: number;
  // For trap_dispatch entries: gate decision + whether a redirect was emitted.
  // These let lineage consumers spot adversarial inputs without re-reading the
  // underlying envelope (and without exposing the attacker text itself).
  gate_decision?: string;
  redirect_emitted?: boolean;
  parse_error?: string;
}

export interface AgentWorkspaceLineageReceipt {
  schema_version: 'aethermoor.bus.workspace_lineage.v1';
  receipt: 'SCBE_WORKSPACE_LINEAGE=1';
  workspace_root: string;
  workspace_id: string;
  generated_at: string;
  entries: LineageEntry[];
  formation_count: number;
  ingest_count: number;
  export_count: number;
  verify_count: number;
  import_count: number;
  trap_dispatch_count: number;
  trap_redirect_count: number;
  unverified_exports: string[];
  failed_verifies: number;
}

const LINEAGE_KIND_BY_SCHEMA: Record<string, LineageEntry['kind']> = {
  'aethermoor.bus.workspace_receipt.v1': 'formation',
  'aethermoor.bus.workspace_ingest.v1': 'ingest',
  'aethermoor.bus.workspace_export.v1': 'export',
  'aethermoor.bus.workspace_verify.v1': 'verify',
  'aethermoor.bus.workspace_import.v1': 'import',
  'aethermoor.bus.workspace_trap_dispatch.v1': 'trap_dispatch',
};

/**
 * Walk a workspace's 20_receipts/ directory and build a chronological audit
 * chain of formation, export, and verify receipts. Read-only: never writes.
 *
 * Reports the set of exports without a matching verify receipt (unverified) and
 * the count of verify receipts that recorded SCBE_WORKSPACE_VERIFY_PASS=0
 * (failed_verifies). Suitable for compliance reviewers checking that every
 * export has been audited.
 */
export function lineageAgentWorkspace(
  options: WorkspaceLineageOptions
): AgentWorkspaceLineageReceipt {
  const workspaceRoot = path.resolve(options.workspaceRoot);
  if (!fs.existsSync(workspaceRoot) || !fs.statSync(workspaceRoot).isDirectory()) {
    throw new Error(`workspace not found at ${workspaceRoot}`);
  }
  const receiptsDir = path.join(workspaceRoot, '20_receipts');
  let workspaceId = path.basename(workspaceRoot);

  const entries: LineageEntry[] = [];
  if (fs.existsSync(receiptsDir)) {
    const fileNames = fs
      .readdirSync(receiptsDir, { withFileTypes: true })
      .filter((d) => d.isFile() && d.name.endsWith('.json'))
      .map((d) => d.name);
    for (const name of fileNames) {
      const abs = path.join(receiptsDir, name);
      let parsed: Record<string, unknown> | null = null;
      let parseError: string | undefined;
      try {
        parsed = JSON.parse(fs.readFileSync(abs, 'utf8'));
      } catch (err) {
        parseError = err instanceof Error ? err.message : String(err);
      }
      const schemaVersion =
        parsed && typeof parsed.schema_version === 'string' ? parsed.schema_version : '';
      const kind: LineageEntry['kind'] = LINEAGE_KIND_BY_SCHEMA[schemaVersion] ?? 'unknown';
      const receiptFlag = parsed && typeof parsed.receipt === 'string' ? parsed.receipt : '';
      // pick a timestamp field per kind
      let timestamp = '';
      if (parsed) {
        if (typeof parsed.created_at === 'string') timestamp = parsed.created_at;
        else if (typeof parsed.verified_at === 'string') timestamp = parsed.verified_at as string;
      }
      if (!timestamp) {
        try {
          timestamp = fs.statSync(abs).mtime.toISOString();
        } catch {
          timestamp = '';
        }
      }
      const entry: LineageEntry = {
        kind,
        receipt_path: abs,
        receipt_name: name,
        timestamp,
        schema_version: schemaVersion,
        receipt: receiptFlag,
      };
      if (parseError) entry.parse_error = parseError;
      if (kind === 'formation' && parsed && typeof parsed.workspace_id === 'string') {
        workspaceId = parsed.workspace_id;
      }
      if (kind === 'export' && parsed) {
        if (typeof parsed.export_id === 'string') entry.export_id = parsed.export_id;
        if (typeof parsed.manifest_sha256 === 'string')
          entry.manifest_sha256 = parsed.manifest_sha256;
      }
      if (kind === 'verify' && parsed) {
        if (typeof parsed.manifest_intact === 'boolean')
          entry.manifest_intact = parsed.manifest_intact;
        if (Array.isArray(parsed.mismatches)) entry.mismatch_count = parsed.mismatches.length;
        // verify receipts also reference the export they audited via export_path
        if (typeof parsed.export_path === 'string') {
          entry.export_id = path.basename(parsed.export_path as string);
        }
      }
      if (kind === 'trap_dispatch' && parsed) {
        if (typeof parsed.gate_decision === 'string') entry.gate_decision = parsed.gate_decision;
        if (typeof parsed.redirect_emitted === 'boolean')
          entry.redirect_emitted = parsed.redirect_emitted;
      }
      entries.push(entry);
    }
  }
  entries.sort((a, b) => {
    if (a.timestamp && b.timestamp) return a.timestamp.localeCompare(b.timestamp);
    return a.receipt_name.localeCompare(b.receipt_name);
  });

  const exportIds = new Set<string>();
  const verifiedExportIds = new Set<string>();
  let formationCount = 0;
  let ingestCount = 0;
  let exportCount = 0;
  let verifyCount = 0;
  let importCount = 0;
  let trapDispatchCount = 0;
  let trapRedirectCount = 0;
  let failedVerifies = 0;
  for (const e of entries) {
    if (e.kind === 'formation') formationCount += 1;
    if (e.kind === 'ingest') ingestCount += 1;
    if (e.kind === 'import') importCount += 1;
    if (e.kind === 'export') {
      exportCount += 1;
      if (e.export_id) exportIds.add(e.export_id);
    }
    if (e.kind === 'verify') {
      verifyCount += 1;
      if (e.receipt === 'SCBE_WORKSPACE_VERIFY_PASS=0') failedVerifies += 1;
      if (e.export_id) verifiedExportIds.add(e.export_id);
    }
    if (e.kind === 'trap_dispatch') {
      trapDispatchCount += 1;
      if (e.redirect_emitted) trapRedirectCount += 1;
    }
  }
  const unverifiedExports = Array.from(exportIds).filter((id) => !verifiedExportIds.has(id));
  unverifiedExports.sort();

  return {
    schema_version: 'aethermoor.bus.workspace_lineage.v1',
    receipt: 'SCBE_WORKSPACE_LINEAGE=1',
    workspace_root: workspaceRoot,
    workspace_id: workspaceId,
    generated_at: new Date().toISOString(),
    entries,
    formation_count: formationCount,
    ingest_count: ingestCount,
    export_count: exportCount,
    verify_count: verifyCount,
    import_count: importCount,
    trap_dispatch_count: trapDispatchCount,
    trap_redirect_count: trapRedirectCount,
    unverified_exports: unverifiedExports,
    failed_verifies: failedVerifies,
  };
}

function normalizeTaskType(value: unknown): string {
  const taskType = String(value || 'general')
    .trim()
    .toLowerCase();
  return TASK_TYPES.has(taskType) ? taskType : 'general';
}

function normalizePrivacy(value: unknown): string {
  const privacy = String(value || 'local_only')
    .trim()
    .toLowerCase();
  if (privacy === 'remote_allowed') return 'remote_ok';
  if (privacy === 'remote_ok') return 'remote_ok';
  return 'local_only';
}

function normalizeEvent(event: AgentBusEvent, index: number): Required<AgentBusEvent> {
  if (!event || typeof event !== 'object') {
    throw new Error(`event ${index} must be an object`);
  }
  const task = String(event.task || '').trim();
  if (!task) {
    throw new Error(`event ${index} missing task`);
  }
  return {
    task,
    operationCommand: String(event.operationCommand || '').trim(),
    taskType: detectTaskType(task, normalizeTaskType(event.taskType)),
    seriesId: String(event.seriesId || `node-event-${index}`).trim(),
    privacy: normalizePrivacy(event.privacy),
    budgetCents: Number(event.budgetCents || 0),
    dispatch: event.dispatch !== false,
    dispatchProvider: String(event.dispatchProvider || 'offline').trim(),
    tool: event.tool ?? '',
  };
}

function tail(text: string, chars = 1000): string {
  return String(text || '').slice(-chars);
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text || '{}');
  } catch {
    return null;
  }
}

export interface RunEventOptions extends RunOptions {
  /** When true, enqueue the event instead of blocking until completion. */
  enqueue?: boolean;
  /** Fan-out worker count for runFanOut. Default: 4 */
  concurrency?: number;
}

/**
 * Run a single governed event.
 *
 * By default, this blocks until the event completes (backward-compatible).
 * Pass `{ enqueue: true }` to enqueue it for async execution via the
 * filesystem queue. Returns a result envelope in both cases.
 */
export async function runEvent(
  event: AgentBusEvent,
  options: RunEventOptions = {}
): Promise<AgentBusResult & { run_id?: string }> {
  const normalized = normalizeEvent(event, 1);

  if (options.enqueue) {
    const { enqueueEvent } = await import('./queue.js');
    const runId = enqueueEvent(normalized, options);
    return {
      schema_version: 'scbe-agentbus-node-result-v1',
      event_index: 1,
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      ok: true,
      exit_code: 202,
      stderr_tail: '',
      event: {
        task_sha256: null,
        task_chars: normalized.task.length,
        series_id: normalized.seriesId,
        operation_command_chars: normalized.operationCommand.length,
      },
      result: { enqueued: true, run_id: runId },
      run_id: runId,
    };
  }

  const repoRoot = path.resolve(options.repoRoot || process.cwd());
  const python = options.python || process.env.PYTHON || 'python';
  const startedAt = new Date().toISOString();

  if (normalized.tool) {
    autoDiscoverTools();
    const registeredTool = getTool(normalized.tool);
    if (!registeredTool) {
      const d = decompose(normalized.task);
      return {
        schema_version: 'scbe-agentbus-node-result-v1',
        event_index: 1,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        ok: false,
        exit_code: null,
        stderr_tail: `unknown tool: '${normalized.tool}' is not registered`,
        event: {
          task_sha256: null,
          task_chars: normalized.task.length,
          series_id: normalized.seriesId,
          operation_command_chars: normalized.operationCommand.length,
        },
        result: null,
        ...(d.tokenCount > 0 ? { semantic: d } : {}),
        ...(d.discourseProfile ? { discourse_profile: d.discourseProfile } : {}),
        ...(d.discourseProfile ? { dialogue_score: scoreDialogue(normalized.task) } : {}),
      };
    }

    const built = buildToolArgv(registeredTool, normalized, options, normalized.seriesId);
    const result = spawnSync(built.command, built.args, {
      cwd: repoRoot,
      encoding: 'utf-8',
      maxBuffer: 1024 * 1024 * 8,
      env: { ...process.env },
    });
    const stdout = result.stdout || '';
    const payload = parseJson(stdout);
    const d = decompose(normalized.task);
    return {
      schema_version: 'scbe-agentbus-node-result-v1',
      event_index: 1,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      ok: result.status === 0,
      exit_code: result.status,
      stderr_tail: tail(result.stderr || ''),
      event: {
        task_sha256: null,
        task_chars: normalized.task.length,
        series_id: normalized.seriesId,
        operation_command_chars: normalized.operationCommand.length,
      },
      result: {
        tool: normalized.tool,
        command: built.command,
        args: built.args,
        stdout: stdout.slice(-4000),
        parsed: payload,
      },
      ...(d.tokenCount > 0 ? { semantic: d } : {}),
      ...(d.discourseProfile ? { discourse_profile: d.discourseProfile } : {}),
      ...(d.discourseProfile ? { dialogue_score: scoreDialogue(normalized.task) } : {}),
    };
  }

  const cli = path.join(repoRoot, 'scripts', 'scbe-system-cli.py');
  const argv = [
    cli,
    '--repo-root',
    repoRoot,
    'agentbus',
    'run',
    '--task',
    normalized.task,
    '--task-type',
    normalized.taskType,
    '--series-id',
    normalized.seriesId,
    '--privacy',
    normalized.privacy,
    '--budget-cents',
    String(normalized.budgetCents),
    '--dispatch-provider',
    normalized.dispatchProvider,
    '--json',
  ];
  if (normalized.operationCommand) {
    argv.push('--operation-command', normalized.operationCommand);
  }
  if (normalized.dispatch) {
    argv.push('--dispatch');
  }

  const result = spawnSync(python, argv, {
    cwd: repoRoot,
    encoding: 'utf-8',
    maxBuffer: 1024 * 1024 * 8,
  });
  const payload = parseJson(result.stdout || '{}') as Record<string, unknown> | null;
  const taskPayload =
    payload && typeof payload.task === 'object' ? (payload.task as Record<string, unknown>) : null;
  const d = decompose(normalized.task);
  return {
    schema_version: 'scbe-agentbus-node-result-v1',
    event_index: 1,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    ok: result.status === 0 && Boolean(payload),
    exit_code: result.status,
    stderr_tail: tail(result.stderr || ''),
    event: {
      task_sha256: typeof taskPayload?.sha256 === 'string' ? taskPayload.sha256 : null,
      task_chars: normalized.task.length,
      series_id: normalized.seriesId,
      operation_command_chars: normalized.operationCommand.length,
    },
    result: payload,
    ...(d.tokenCount > 0 ? { semantic: d } : {}),
    ...(d.discourseProfile ? { discourse_profile: d.discourseProfile } : {}),
    ...(d.discourseProfile ? { dialogue_score: scoreDialogue(normalized.task) } : {}),
  };
}

export async function runBatch(
  events: AgentBusEvent[],
  options: RunEventOptions = {}
): Promise<AgentBusResult[]> {
  if (!Array.isArray(events) || events.length === 0) {
    throw new Error('events sequence is empty');
  }
  const rows: AgentBusResult[] = [];
  for (const [index, event] of events.entries()) {
    const row = await runEvent(
      { ...event, seriesId: event.seriesId || `node-event-${index + 1}` },
      options
    );
    rows.push({ ...row, event_index: index + 1 });
    if (!row.ok && !options.continueOnError) break;
  }
  return rows;
}

/**
 * Concurrent fan-out execution of events across N workers (round-robin).
 * Unlike runBatch, this does NOT stop on first failure — all events run.
 */
export async function runFanOut(
  events: AgentBusEvent[],
  options: RunEventOptions = {}
): Promise<AgentBusResult[]> {
  if (!Array.isArray(events) || events.length === 0) {
    throw new Error('events sequence is empty');
  }
  const concurrency = Math.max(1, options.concurrency ?? 4);
  const results: AgentBusResult[] = new Array(events.length);

  async function worker(offset: number): Promise<void> {
    for (let i = offset; i < events.length; i += concurrency) {
      const row = await runEvent(
        { ...events[i], seriesId: events[i].seriesId || `node-event-${i + 1}` },
        options
      );
      results[i] = { ...row, event_index: i + 1 };
    }
  }

  await Promise.all(Array.from({ length: concurrency }, (_, w) => worker(w)));
  return results;
}

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
    req.on('error', reject);
  });
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  const body = `${JSON.stringify(payload, null, 2)}\n`;
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
  });
  res.end(body);
}

export async function startAgentBusServer(
  options: AgentBusServerOptions = {}
): Promise<AgentBusServerHandle> {
  const host = options.host || '127.0.0.1';
  const port = Number(options.port || 8787);
  const server = createServer(async (req, res) => {
    try {
      if (req.method === 'GET' && req.url === '/health') {
        const { getQueueStatus } = await import('./queue.js');
        const { getCircuitStates } = await import('./resilience.js');
        sendJson(res, 200, {
          ok: true,
          service: 'scbe-agent-bus',
          version: 1,
          queue: getQueueStatus(),
          circuits: getCircuitStates(),
        });
        return;
      }
      if (req.method === 'GET' && req.url?.startsWith('/v1/events/')) {
        const runId = req.url.split('/').pop();
        const { getEventStatus } = await import('./queue.js');
        const status = runId ? getEventStatus(runId) : null;
        if (status) {
          sendJson(res, 200, status);
        } else {
          sendJson(res, 404, { ok: false, error: 'run_id not found' });
        }
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/events') {
        const body = JSON.parse(await readBody(req)) as AgentBusEvent & { enqueue?: boolean };
        const enqueue = body.enqueue === true;
        const row = await runEvent(body, { ...options, enqueue });
        if (enqueue && row.run_id) {
          sendJson(res, 202, { ok: true, enqueued: true, run_id: row.run_id });
        } else {
          sendJson(res, row.ok ? 200 : 500, row);
        }
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/batch') {
        const body = JSON.parse(await readBody(req)) as
          | { items?: AgentBusEvent[]; enqueue?: boolean }
          | AgentBusEvent[];
        const items = Array.isArray(body) ? body : body.items || [];
        const enqueue = !Array.isArray(body) && body.enqueue === true;
        const rows = await runBatch(items, { ...options, enqueue });
        if (enqueue) {
          sendJson(res, 202, {
            ok: true,
            enqueued: true,
            count: rows.length,
            run_ids: rows.map((r) => (r.result as Record<string, string>)?.run_id).filter(Boolean),
          });
        } else {
          sendJson(res, rows.every((row) => row.ok) ? 200 : 500, { rows });
        }
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/fanout') {
        const body = JSON.parse(await readBody(req)) as
          | { items?: AgentBusEvent[]; enqueue?: boolean; concurrency?: number }
          | AgentBusEvent[];
        const items = Array.isArray(body) ? body : body.items || [];
        const enqueue = !Array.isArray(body) && body.enqueue === true;
        const concurrency = !Array.isArray(body) ? Number(body.concurrency || 4) : 4;
        if (enqueue) {
          const { enqueueEvent } = await import('./queue.js');
          const runIds = items.map((ev, i) => enqueueEvent(normalizeEvent(ev, i), options));
          sendJson(res, 202, { ok: true, enqueued: true, count: runIds.length, run_ids: runIds });
        } else {
          const rows = await runFanOut(items, { ...options, concurrency });
          sendJson(res, rows.every((row) => row.ok) ? 200 : 500, { rows });
        }
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/pipeline') {
        const body = JSON.parse(await readBody(req)) as {
          intent?: string;
          options?: RunOptions;
        };
        const intent = String(body.intent || '').trim();
        if (!intent) {
          sendJson(res, 400, { ok: false, error: 'missing intent' });
          return;
        }
        const { runPipeline } = await import('./pipeline.js');
        const result = await runPipeline(intent, body.options || options);
        sendJson(res, result.blocked ? 403 : 200, result);
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/pipeline/compile') {
        const body = JSON.parse(await readBody(req)) as {
          intent?: string;
          options?: RunOptions;
        };
        const intent = String(body.intent || '').trim();
        if (!intent) {
          sendJson(res, 400, { ok: false, error: 'missing intent' });
          return;
        }
        const { compilePlan } = await import('./pipeline.js');
        const plan = compilePlan(intent, body.options || options);
        if (plan) {
          sendJson(res, 200, { ok: true, plan });
        } else {
          sendJson(res, 500, { ok: false, error: 'compile failed' });
        }
        return;
      }
      sendJson(res, 404, { ok: false, error: 'not_found' });
    } catch (err) {
      sendJson(res, 400, { ok: false, error: err instanceof Error ? err.message : String(err) });
    }
  });
  await new Promise<void>((resolve) => server.listen(port, host, resolve));
  return {
    url: `http://${host}:${port}`,
    server,
    close: () =>
      new Promise((resolve, reject) => server.close((err) => (err ? reject(err) : resolve()))),
  };
}

export async function postAgentBusEvent(
  event: AgentBusEvent,
  options: AgentBusClientOptions = {}
): Promise<unknown> {
  const fetcher = options.fetchImpl || fetch;
  const baseUrl = (options.baseUrl || 'http://127.0.0.1:8787').replace(/\/+$/, '');
  const res = await fetcher(`${baseUrl}/v1/events`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(event),
  });
  const payload = await res.json();
  if (!res.ok) {
    throw new Error(
      `agent-bus request failed: ${res.status} ${JSON.stringify(payload).slice(0, 500)}`
    );
  }
  return payload;
}

export async function runAgentBusTerminalUi(options: AgentBusClientOptions = {}): Promise<void> {
  const rl = createInterface({ input, output });
  try {
    output.write(`SCBE Agent Bus UI (${options.baseUrl || 'http://127.0.0.1:8787'})\n`);
    while (true) {
      const task = (await rl.question('task> ')).trim();
      if (!task || task === 'exit' || task === 'quit') break;
      const result = await postAgentBusEvent(
        { task, taskType: 'general', privacy: 'local_only' },
        options
      );
      output.write(`${JSON.stringify(result, null, 2)}\n`);
    }
  } finally {
    rl.close();
  }
}
