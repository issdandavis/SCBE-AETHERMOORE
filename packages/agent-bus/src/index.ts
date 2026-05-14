import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import path from 'node:path';

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
}

export interface RunOptions {
  repoRoot?: string;
  python?: string;
  continueOnError?: boolean;
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
  return String(value || 'workspace')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'workspace';
}

function timestampId(date = new Date()): string {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
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

export function exportAgentWorkspace(
  options: WorkspaceExportOptions
): AgentWorkspaceExportReceipt {
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

  const requestedInclude = (options.include && options.include.length > 0
    ? options.include
    : DEFAULT_EXPORT_INCLUDE
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
    taskType: normalizeTaskType(event.taskType),
    seriesId: String(event.seriesId || `node-event-${index}`).trim(),
    privacy: normalizePrivacy(event.privacy),
    budgetCents: Number(event.budgetCents || 0),
    dispatch: event.dispatch !== false,
    dispatchProvider: String(event.dispatchProvider || 'offline').trim(),
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

export async function runEvent(
  event: AgentBusEvent,
  options: RunOptions = {}
): Promise<AgentBusResult> {
  const normalized = normalizeEvent(event, 1);
  const repoRoot = path.resolve(options.repoRoot || process.cwd());
  const python = options.python || process.env.PYTHON || 'python';
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

  const startedAt = new Date().toISOString();
  const result = spawnSync(python, argv, {
    cwd: repoRoot,
    encoding: 'utf-8',
    maxBuffer: 1024 * 1024 * 8,
  });
  const payload = parseJson(result.stdout || '{}') as Record<string, unknown> | null;
  const taskPayload =
    payload && typeof payload.task === 'object' ? (payload.task as Record<string, unknown>) : null;
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
  };
}

export async function runBatch(
  events: AgentBusEvent[],
  options: RunOptions = {}
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
        sendJson(res, 200, { ok: true, service: 'scbe-agent-bus', version: 1 });
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/events') {
        const body = JSON.parse(await readBody(req)) as AgentBusEvent;
        const row = await runEvent(body, options);
        sendJson(res, row.ok ? 200 : 500, row);
        return;
      }
      if (req.method === 'POST' && req.url === '/v1/batch') {
        const body = JSON.parse(await readBody(req)) as
          | { items?: AgentBusEvent[] }
          | AgentBusEvent[];
        const items = Array.isArray(body) ? body : body.items || [];
        const rows = await runBatch(items, options);
        sendJson(res, rows.every((row) => row.ok) ? 200 : 500, { rows });
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
