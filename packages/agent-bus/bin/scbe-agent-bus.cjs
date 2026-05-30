#!/usr/bin/env node

const path = require('node:path');

const {
  createAgentWorkspace,
  exportAgentWorkspace,
  importAgentWorkspace,
  ingestIntoAgentWorkspace,
  lineageAgentWorkspace,
  reportAgentWorkspace,
  verifyAllAgentWorkspaceExports,
  postAgentBusEvent,
  runAgentBusTerminalUi,
  startAgentBusServer,
  verifyAgentWorkspaceExport,
  cleanupWorkspaceTmp,
  listPlugins,
  getQueueStatus,
  drainQueue,
  startQueueWorker,
  listTools,
  autoDiscoverTools,
  auditToolRegistry,
  compilePlan,
  createGovernedPipelineState,
  loadGovernedPipelineState,
  runPipeline,
  saveGovernedPipelineState,
  summarizeGovernedPipelineState,
  hermesModelLanes,
  planHermesRoute,
  buildScbeRollStack,
  scbeCompassModelLanes,
  planScbeCompassRoute,
  scbeCompassCommandTree,
  scbeCompassBoardRules,
  scbeCompassRollCards,
} = require('../dist/index.js');

const HOSTED_INTAKE_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html';
const SERVICE_CREDITS_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html';
const CREDIT_TOPUP_URL = 'https://ko-fi.com/izdandavis';

const LOCAL_PROVIDERS = new Set(['offline', 'local', 'ollama', 'local_only', '']);

function hasHostedCredential() {
  const key = String(process.env.SCBE_API_KEY || '').trim();
  return key.length > 0;
}

function wantsHostedDispatch(flags) {
  const provider = String(flags['dispatch-provider'] || 'offline')
    .trim()
    .toLowerCase();
  return !LOCAL_PROVIDERS.has(provider);
}

function printHostedIntakeNotice(provider) {
  process.stderr.write(
    `\nThis command requested a non-local provider ('${provider}') without an SCBE_API_KEY.\n` +
      `Local routing is free. Hosted runs (provider/model-backed, signed reports, stored history)\n` +
      `go through a scoped intake so cost + scope are agreed before any provider spend happens.\n\n` +
      `  Hosted run intake:  ${HOSTED_INTAKE_URL}\n` +
      `  Service credits:    ${SERVICE_CREDITS_URL}\n` +
      `  Credit top-up:      ${CREDIT_TOPUP_URL}\n\n` +
      `Billable provider/model cost is passed through with a 2-5% SCBE coordination fee.\n` +
      `To run locally instead, omit --dispatch-provider or pass --dispatch-provider offline.\n\n`
  );
}

function printUpgrade() {
  const credentialed = hasHostedCredential();
  process.stdout.write(
    `SCBE Agent Bus — hosted runs\n\n` +
      `Local routing is free. Use 'privacy: \"local_only\"' and Ollama/deterministic harnesses\n` +
      `for sensitive work. No account or key required.\n\n` +
      `Hosted runs (signed reports, provider/model-backed routes, stored history) are billed:\n` +
      `  - Submit a scoped intake:  ${HOSTED_INTAKE_URL}\n` +
      `  - Service credits page:    ${SERVICE_CREDITS_URL}\n` +
      `  - Credit top-up (Ko-fi):   ${CREDIT_TOPUP_URL}\n\n` +
      `Billable provider/model cost is passed through with a 2-5% SCBE coordination fee.\n` +
      `Credits cover hosted capacity, report delivery, storage, and provider/model usage.\n\n` +
      (credentialed
        ? `SCBE_API_KEY is set in your environment. Hosted dispatch is unlocked.\n`
        : `SCBE_API_KEY is not set. Set it (export SCBE_API_KEY=...) after credits are issued.\n`)
  );
}

function parseArgs(argv) {
  const positionals = [];
  const flags = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      positionals.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      flags[key] = true;
      continue;
    }
    flags[key] = next;
    i += 1;
  }
  return { command: positionals[0] || 'help', flags };
}

function printHelp() {
  process.stdout.write(`SCBE Agent Bus

Usage:
  scbe-agent-bus serve --port 8787 [--worker]
  scbe-agent-bus ui --base-url http://127.0.0.1:8787
  scbe-agent-bus send --task "review changed files" --task-type review --json
  scbe-agent-bus send --task "heavy job" --enqueue --json
  scbe-agent-bus send --task "run linter" --tool lint --json
  scbe-agent-bus pipeline run --intent "check security of changed files" [--json]
  scbe-agent-bus pipeline compile --intent "explain routing for task.py" [--json]
  scbe-agent-bus pipeline state --session-id default [--json]
  scbe-agent-bus health --base-url http://127.0.0.1:8787 --json
  scbe-agent-bus queue status --json
  scbe-agent-bus queue drain
  scbe-agent-bus queue worker
  scbe-agent-bus plugins list --json
  scbe-agent-bus tools list --json
  scbe-agent-bus compass plan --task "draft and review a YouTube script" --json
  scbe-agent-bus compass models --json
  scbe-agent-bus compass tree --json
  scbe-agent-bus compass board --task "cross-language compiler" --json
  scbe-agent-bus compass rolls --task "solve maze pathfinding benchmark" --json
  scbe-agent-bus compass stack --task "solve maze pathfinding benchmark" --json
  scbe-agent-bus hermes plan --task "draft and review a YouTube script" --json
  scbe-agent-bus workspace new --hint customer-smoke --json
  scbe-agent-bus workspace ingest --workspace-root <path> --source-path <file> --json
  scbe-agent-bus workspace export --workspace-root <path> --json
  scbe-agent-bus workspace import --export-path <path> --json
  scbe-agent-bus workspace verify --export-path <path> --json
  scbe-agent-bus workspace verify --all --workspace-root <path> --json
  scbe-agent-bus workspace lineage --workspace-root <path> --json
  scbe-agent-bus workspace report --workspace-root <path> --json
  scbe-agent-bus workspace cleanup-tmp --workspace-root <path> [--dry-run] --json
  scbe-agent-bus upgrade

Commands:
  serve     Start the local HTTP backend.
  ui        Start the terminal frontend.
  send      Send one governed task to the backend.
  health    Check backend health.
  queue     Inspect or run the event queue.
  plugins   List registered bus plugins.
  tools     List registered CLI tools (set SCBE_BUS_TOOLS=./tools.json to load).
  compass   SCBE-native agentic CLI front door for formations and adapters.
  hermes    Compatibility alias for compass-style task routing.
  pipeline  Compile and run natural-language intents through GeoSeal governance.
            Use --governed-state to enable the durable trajectory gate.
  workspace Create, export, verify, and clean bus workspaces.
  upgrade   Show how to enable hosted runs (intake, credits, top-up).

Local routing is free. Hosted runs require SCBE_API_KEY (see 'upgrade').
`);
}

async function main() {
  const { command, flags } = parseArgs(process.argv);
  const baseUrl = String(
    flags['base-url'] || process.env.SCBE_AGENT_BUS_URL || 'http://127.0.0.1:8787'
  );
  if (command === 'help' || flags.help) {
    printHelp();
    return;
  }
  if (command === 'upgrade') {
    printUpgrade();
    return;
  }
  if (command === 'workspace') {
    const action = String(flags._action || process.argv[3] || 'help').trim();
    if (action === 'new') {
      const payload = createAgentWorkspace({
        root: flags.root ? String(flags.root) : undefined,
        hint: flags.hint ? String(flags.hint) : undefined,
      });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE workspace receipt: ${payload.receipt}`,
            `Workspace: ${payload.workspace_root}`,
            `Receipt: ${payload.receipt_path}`,
            '',
          ].join('\n')
        );
      }
      return;
    }
    if (action === 'verify') {
      const persistReceipt = !flags['no-persist'];
      if (flags.all) {
        const workspaceRoot = String(flags['workspace-root'] || flags.root || '').trim();
        if (!workspaceRoot) {
          process.stderr.write(
            'Usage: scbe-agent-bus workspace verify --all --workspace-root <path> [--no-persist] [--json]\n'
          );
          process.exitCode = 2;
          return;
        }
        const payload = verifyAllAgentWorkspaceExports({ workspaceRoot, persistReceipt });
        if (flags.json) {
          process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
        } else {
          const lines = [
            `SCBE workspace verify-all receipt: ${payload.receipt}`,
            `Workspace:    ${payload.workspace_root}`,
            `Workspace id: ${payload.workspace_id}`,
            `Verified at:  ${payload.verified_at}`,
            `Exports: ${payload.export_count}    Passed: ${payload.passed_count}    Failed: ${payload.failed_count}`,
            '',
          ];
          if (payload.results.length === 0) {
            lines.push('No exports found under 30_exports/.');
          } else {
            lines.push('Per-export results:');
            for (const r of payload.results) {
              const flag = r.receipt === 'SCBE_WORKSPACE_VERIFY_PASS=1' ? 'PASS' : 'FAIL';
              lines.push(
                `  [${flag}] ${path.basename(r.export_path)}    intact=${r.manifest_intact}    mismatches=${r.mismatches.length}`
              );
            }
          }
          lines.push('');
          process.stdout.write(lines.join('\n'));
        }
        process.exitCode = payload.receipt === 'SCBE_WORKSPACE_VERIFY_ALL_PASS=1' ? 0 : 1;
        return;
      }
      const exportPath = String(flags['export-path'] || '').trim();
      if (!exportPath) {
        process.stderr.write(
          'Usage:\n' +
            '  scbe-agent-bus workspace verify --export-path <path> [--no-persist] [--json]\n' +
            '  scbe-agent-bus workspace verify --all --workspace-root <path> [--no-persist] [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const payload = verifyAgentWorkspaceExport({ exportPath, persistReceipt });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        const lines = [
          `SCBE workspace verify receipt: ${payload.receipt}`,
          `Export:    ${payload.export_path}`,
          `Manifest:  ${payload.manifest_path}`,
          `Manifest sha256 claimed: ${payload.manifest_sha256_claimed || '<no receipt>'}`,
          `Manifest sha256 actual:  ${payload.manifest_sha256_actual}`,
          `Manifest intact: ${payload.manifest_intact}`,
          `Files claimed: ${payload.file_count_claimed}    actual: ${payload.file_count_actual}`,
          `Bytes claimed: ${payload.total_bytes_claimed}    actual: ${payload.total_bytes_actual}`,
          `Receipt:   ${payload.receipt_path || '<not persisted>'}`,
        ];
        if (payload.mismatches.length === 0) {
          lines.push('No mismatches.');
        } else {
          lines.push(`Mismatches (${payload.mismatches.length}):`);
          for (const m of payload.mismatches) {
            lines.push(`  [${m.reason}] ${m.path}`);
            if (m.expected_sha256) {
              lines.push(`      expected sha256: ${m.expected_sha256}`);
            }
            if (m.actual_sha256) {
              lines.push(`      actual sha256:   ${m.actual_sha256}`);
            }
          }
        }
        lines.push('');
        process.stdout.write(lines.join('\n'));
      }
      process.exitCode = payload.receipt === 'SCBE_WORKSPACE_VERIFY_PASS=1' ? 0 : 1;
      return;
    }
    if (action === 'import') {
      const exportPath = String(flags['export-path'] || '').trim();
      if (!exportPath) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace import --export-path <path> [--target-root <dir>] [--hint <name>] [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const targetRoot = flags['target-root'] ? String(flags['target-root']) : undefined;
      const hint = flags.hint ? String(flags.hint) : undefined;
      let payload;
      try {
        payload = importAgentWorkspace({ exportPath, targetRoot, hint });
      } catch (err) {
        process.stderr.write(`scbe-agent-bus workspace import: ${err.message}\n`);
        process.exitCode = 1;
        return;
      }
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE workspace import receipt: ${payload.receipt}`,
            `Source export:   ${payload.source_export_path}`,
            `Source export id: ${payload.source_export_id}`,
            `Source manifest sha256: ${payload.source_manifest_sha256}`,
            `Target workspace: ${payload.target_workspace_root}`,
            `Files imported:  ${payload.imported_files}    bytes: ${payload.imported_bytes}`,
            `Receipt:         ${payload.receipt_path}`,
            '',
          ].join('\n')
        );
      }
      return;
    }
    if (action === 'report') {
      const workspaceRoot = String(flags['workspace-root'] || flags.root || '').trim();
      if (!workspaceRoot) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace report --workspace-root <path> [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const payload = reportAgentWorkspace({ workspaceRoot });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        const ls = payload.lineage_summary;
        const lines = [
          `SCBE workspace report receipt: ${payload.receipt}`,
          `Workspace:    ${payload.workspace_root}`,
          `Workspace id: ${payload.workspace_id}`,
          `Created at:   ${payload.created_at || '<unknown>'}`,
          `Last activity: ${payload.last_activity || '<unknown>'}`,
          `Audit health: ${payload.audit_health.toUpperCase()}`,
          '',
          'Folder stats:',
        ];
        for (const f of payload.folders) {
          lines.push(`  ${f.path.padEnd(14)} ${f.file_count} files    ${f.total_bytes} bytes`);
        }
        lines.push('');
        lines.push('Lineage summary:');
        lines.push(
          `  formation=${ls.formation_count}  ingests=${ls.ingest_count}  exports=${ls.export_count}  verifies=${ls.verify_count}  failed_verifies=${ls.failed_verifies}`
        );
        lines.push(
          `  unverified_exports (${ls.unverified_exports.length}): ${ls.unverified_exports.join(', ') || '<none>'}`
        );
        lines.push('');
        process.stdout.write(lines.join('\n'));
      }
      return;
    }
    if (action === 'cleanup-tmp') {
      const workspaceRoot = String(flags['workspace-root'] || flags.root || '').trim();
      if (!workspaceRoot) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace cleanup-tmp --workspace-root <path> [--dry-run] [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const payload = cleanupWorkspaceTmp({ workspaceRoot, dryRun: flags['dry-run'] === true });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE workspace tmp cleanup: ${payload.receipt}`,
            `Workspace: ${payload.workspace_root}`,
            `Deleted: ${payload.deleted_count} files`,
            `Reclaimed: ${payload.reclaimed_bytes} bytes`,
            payload.dry_run ? '(dry run — no files were deleted)' : '',
            '',
          ].join('\n')
        );
      }
      return;
    }
    if (action === 'ingest') {
      const workspaceRoot = String(flags['workspace-root'] || flags.root || '').trim();
      const sourcePath = String(flags['source-path'] || flags.source || '').trim();
      if (!workspaceRoot || !sourcePath) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace ingest --workspace-root <path> --source-path <file> [--rename <name>] [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const rename = flags.rename ? String(flags.rename) : undefined;
      const payload = ingestIntoAgentWorkspace({ workspaceRoot, sourcePath, rename });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE workspace ingest receipt: ${payload.receipt}`,
            `Workspace: ${payload.workspace_root}`,
            `Source:    ${payload.source_path}`,
            `Dest:      ${payload.destination_path}`,
            `SHA-256:   ${payload.destination_sha256}`,
            `Bytes:     ${payload.bytes}`,
            `Receipt:   ${payload.receipt_path}`,
            '',
          ].join('\n')
        );
      }
      return;
    }
    if (action === 'lineage') {
      const workspaceRoot = String(flags['workspace-root'] || flags.root || '').trim();
      if (!workspaceRoot) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace lineage --workspace-root <path> [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const payload = lineageAgentWorkspace({ workspaceRoot });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        const lines = [
          `SCBE workspace lineage receipt: ${payload.receipt}`,
          `Workspace:        ${payload.workspace_root}`,
          `Workspace id:     ${payload.workspace_id}`,
          `Generated at:     ${payload.generated_at}`,
          `Formation: ${payload.formation_count}    Ingests: ${payload.ingest_count}    Imports: ${payload.import_count}    Exports: ${payload.export_count}    Verifies: ${payload.verify_count}    Failed verifies: ${payload.failed_verifies}`,
          `Unverified exports (${payload.unverified_exports.length}): ${payload.unverified_exports.join(', ') || '<none>'}`,
          '',
          'Chain:',
        ];
        if (payload.entries.length === 0) {
          lines.push('  <empty>');
        } else {
          for (const e of payload.entries) {
            const extra = [];
            if (e.export_id) extra.push(`export=${e.export_id}`);
            if (e.manifest_sha256) extra.push(`manifest=${e.manifest_sha256.slice(0, 12)}…`);
            if (typeof e.manifest_intact === 'boolean') extra.push(`intact=${e.manifest_intact}`);
            if (typeof e.mismatch_count === 'number') extra.push(`mismatches=${e.mismatch_count}`);
            const suffix = extra.length > 0 ? ` (${extra.join(' ')})` : '';
            lines.push(`  [${e.kind}] ${e.timestamp || '?'}  ${e.receipt_name}${suffix}`);
            if (e.parse_error) lines.push(`     parse_error: ${e.parse_error}`);
          }
        }
        lines.push('');
        process.stdout.write(lines.join('\n'));
      }
      return;
    }
    if (action === 'export') {
      const workspaceRoot = String(flags['workspace-root'] || '').trim();
      if (!workspaceRoot) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace export --workspace-root <path> [--out <name>] [--include 00_inbox,10_work] [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const include =
        flags.include && typeof flags.include === 'string'
          ? String(flags.include)
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean)
          : undefined;
      const payload = exportAgentWorkspace({
        workspaceRoot,
        out: flags.out ? String(flags.out) : undefined,
        include,
      });
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE workspace export receipt: ${payload.receipt}`,
            `Workspace: ${payload.workspace_root}`,
            `Export:    ${payload.export_path}`,
            `Manifest:  ${payload.manifest_path}`,
            `Files:     ${payload.file_count} (${payload.total_bytes} bytes)`,
            `Manifest sha256: ${payload.manifest_sha256}`,
            `Receipt:   ${payload.receipt_path}`,
            '',
          ].join('\n')
        );
      }
      return;
    }
    process.stderr.write(
      'Usage:\n' +
        '  scbe-agent-bus workspace new [--root <path>] [--hint <name>] [--json]\n' +
        '  scbe-agent-bus workspace ingest --workspace-root <path> --source-path <file> [--rename <name>] [--json]\n' +
        '  scbe-agent-bus workspace export --workspace-root <path> [--out <name>] [--include 00_inbox,10_work] [--json]\n' +
        '  scbe-agent-bus workspace import --export-path <path> [--target-root <dir>] [--hint <name>] [--json]\n' +
        '  scbe-agent-bus workspace verify --export-path <path> [--no-persist] [--json]\n' +
        '  scbe-agent-bus workspace verify --all --workspace-root <path> [--no-persist] [--json]\n' +
        '  scbe-agent-bus workspace lineage --workspace-root <path> [--json]\n' +
        '  scbe-agent-bus workspace report --workspace-root <path> [--json]\n' +
        '  scbe-agent-bus workspace cleanup-tmp --workspace-root <path> [--dry-run] [--json]\n'
    );
    process.exitCode = action === 'help' ? 0 : 2;
    return;
  }
  if (command === 'serve') {
    const handle = await startAgentBusServer({
      host: String(flags.host || '127.0.0.1'),
      port: Number(flags.port || 8787),
      repoRoot: flags['repo-root'] ? String(flags['repo-root']) : undefined,
      python: flags.python ? String(flags.python) : undefined,
      continueOnError: Boolean(flags['continue-on-error']),
    });
    let workerHandle;
    if (flags.worker) {
      const interval = Number(flags['worker-interval'] || 5000);
      workerHandle = startQueueWorker(interval);
      process.stdout.write(`Queue worker started (interval=${interval}ms).\n`);
    }
    const payload = {
      schema_version: 'scbe-agent-bus-backend-start-v1',
      ok: true,
      url: handle.url,
      routes: ['/health', '/v1/events', '/v1/events/:id/status', '/v1/batch'],
      queue_worker: Boolean(workerHandle),
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }
  if (command === 'ui') {
    await runAgentBusTerminalUi({ baseUrl });
    return;
  }
  if (command === 'send') {
    const task = String(flags.task || '').trim();
    if (!task) throw new Error('send requires --task');
    if (wantsHostedDispatch(flags) && !hasHostedCredential()) {
      const provider = String(flags['dispatch-provider'] || 'offline');
      printHostedIntakeNotice(provider);
      process.exitCode = 2;
      return;
    }
    const event = {
      task,
      taskType: String(flags['task-type'] || 'general'),
      privacy: String(flags.privacy || 'local_only'),
      budgetCents: Number(flags['budget-cents'] || 0),
      dispatchProvider: String(flags['dispatch-provider'] || 'offline'),
      dispatch: flags.dispatch !== 'false',
      enqueue: flags.enqueue === true,
      ...(flags.tool ? { tool: String(flags.tool) } : {}),
    };
    const result = await postAgentBusEvent(event, { baseUrl });
    process.stdout.write(
      flags.json ? `${JSON.stringify(result, null, 2)}\n` : `${JSON.stringify(result)}\n`
    );
    return;
  }
  if (command === 'queue') {
    const action = String(flags._action || process.argv[3] || 'help').trim();
    if (action === 'status') {
      const payload = getQueueStatus();
      process.stdout.write(
        flags.json ? `${JSON.stringify(payload, null, 2)}\n` : `${JSON.stringify(payload)}\n`
      );
      return;
    }
    if (action === 'drain') {
      await drainQueue();
      const payload = getQueueStatus();
      process.stdout.write(
        flags.json
          ? `${JSON.stringify({ drained: true, queue: payload }, null, 2)}\n`
          : 'Queue drained.\n'
      );
      return;
    }
    if (action === 'worker') {
      const interval = Number(flags.interval || 5000);
      const handle = startQueueWorker(interval);
      process.stdout.write(
        `Queue worker started (interval=${interval}ms). Press Ctrl+C to stop.\n`
      );
      process.on('SIGINT', () => {
        handle.stop();
        process.exit(0);
      });
      process.on('SIGTERM', () => {
        handle.stop();
        process.exit(0);
      });
      return;
    }
    process.stderr.write(
      'Usage: scbe-agent-bus queue status | drain | worker [--interval <ms>] [--json]\n'
    );
    process.exitCode = 2;
    return;
  }
  if (command === 'plugins') {
    const action = String(flags._action || process.argv[3] || 'list').trim();
    if (action === 'list') {
      const payload = listPlugins().map((p) => ({
        name: p.name,
        hasBeforeRun: typeof p.beforeRun === 'function',
        hasAfterRun: typeof p.afterRun === 'function',
      }));
      process.stdout.write(
        flags.json
          ? `${JSON.stringify(payload, null, 2)}\n`
          : payload
              .map((p) => `  ${p.name}  beforeRun=${p.hasBeforeRun} afterRun=${p.hasAfterRun}`)
              .join('\n') + '\n'
      );
      return;
    }
    process.stderr.write('Usage: scbe-agent-bus plugins list [--json]\n');
    process.exitCode = 2;
    return;
  }
  if (command === 'tools') {
    autoDiscoverTools();
    const action = String(flags._action || process.argv[3] || 'list').trim();
    if (action === 'list') {
      const payload = listTools().map((t) => ({
        name: t.name,
        command: t.command,
        args: t.args,
        description: t.description || '',
      }));
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else if (payload.length === 0) {
        process.stdout.write(
          'No tools registered. Set SCBE_BUS_TOOLS=./tools.json to load tools.\n'
        );
      } else {
        for (const t of payload) {
          process.stdout.write(
            `  ${t.name}  ${t.command} ${t.args.join(' ')}${t.description ? `  — ${t.description}` : ''}\n`
          );
        }
      }
      return;
    }
    if (action === 'audit') {
      const payload = auditToolRegistry(listTools());
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `SCBE tool registry audit: ${payload.ok ? 'OK' : 'CHECK'}`,
            `Tools: ${payload.tool_count}`,
            'Patent-facing surfaces:',
            ...Object.entries(payload.surface_counts).map(([k, v]) => `  ${k}: ${v}`),
            '',
          ].join('\n')
        );
        const envEntries = Object.entries(payload.missing_required_env);
        if (envEntries.length > 0) {
          process.stdout.write('Missing optional live env vars:\n');
          for (const [tool, envs] of envEntries) {
            process.stdout.write(`  ${tool}: ${envs.join(', ')}\n`);
          }
        }
      }
      process.exitCode = payload.ok ? 0 : 1;
      return;
    }
    process.stderr.write('Usage: scbe-agent-bus tools list|audit [--json]\n');
    process.exitCode = 2;
    return;
  }
  if (command === 'compass' || command === 'hermes') {
    const isHermesAlias = command === 'hermes';
    const action = String(flags._action || process.argv[3] || 'plan').trim();
    if (action === 'models') {
      const payload = {
        schema_version: isHermesAlias
          ? 'scbe.agent_bus.hermes_model_lanes.v1'
          : 'scbe.agent_bus.compass_model_lanes.v1',
        command_surface: isHermesAlias ? 'hermes-alias' : 'scbe-compass',
        generated_at: new Date().toISOString(),
        lanes: isHermesAlias ? hermesModelLanes() : scbeCompassModelLanes(),
        note: 'Local-free means no provider bill after install. Remote free-tier lanes are quota-limited. Paid providers require budget approval.',
      };
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write('Hermes model lanes:\n');
        for (const lane of payload.lanes) {
          process.stdout.write(
            `  ${lane.id}: ${lane.costTier} privacy=${lane.privacy} requires=${lane.requires.join(', ') || 'none'}\n`
          );
        }
        process.stdout.write(`\n${payload.note}\n`);
      }
      return;
    }
    if (action === 'tree') {
      const payload = {
        schema_version: 'scbe.agent_bus.compass_command_tree.v1',
        command_surface: isHermesAlias ? 'hermes-alias' : 'scbe-compass',
        generated_at: new Date().toISOString(),
        source_notes: [
          'notes/sphere-grid/Agentic Sphere Grid.md',
          'notes/round-table/2026-05-01-night-agentic-public-ai-and-runtime-routing.md',
          'notes/theory/ai-mind-map.md',
        ],
        nodes: scbeCompassCommandTree(),
      };
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write('SCBE Compass command tree:\n');
        for (const node of payload.nodes) {
          process.stdout.write(
            `  ${node.path}  domain=${node.domain} tier=T${node.tier} formation=${node.formation}${node.tool ? ` tool=${node.tool}` : ''}\n`
          );
        }
      }
      return;
    }
    if (action === 'board') {
      const task = String(flags.task || flags.intent || '').trim();
      const plan = task ? planScbeCompassRoute(task) : null;
      const mode = plan?.mode || 'general';
      const payload = {
        schema_version: 'scbe.agent_bus.compass_board_rules.v1',
        command_surface: isHermesAlias ? 'hermes-alias' : 'scbe-compass',
        generated_at: new Date().toISOString(),
        task,
        mode,
        command_path: plan?.command_path || 'KO.command',
        source_paths: Array.from(
          new Set(scbeCompassBoardRules(mode).flatMap((rule) => rule.source_paths || []))
        ),
        rules: scbeCompassBoardRules(mode),
      };
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write('SCBE Compass board rules:\n');
        for (const rule of payload.rules) {
          process.stdout.write(`  ${rule.mechanic}: ${rule.purpose}\n`);
          for (const sourcePath of rule.source_paths || []) {
            process.stdout.write(`    source: ${sourcePath}\n`);
          }
        }
      }
      return;
    }
    if (action === 'rolls') {
      const task = String(flags.task || flags.intent || '').trim();
      const plan = task ? planScbeCompassRoute(task) : null;
      const mode = plan?.mode || 'general';
      const payload = {
        schema_version: 'scbe.agent_bus.compass_roll_cards.v1',
        command_surface: isHermesAlias ? 'hermes-alias' : 'scbe-compass',
        generated_at: new Date().toISOString(),
        task,
        mode,
        command_path: plan?.command_path || 'KO.command',
        cards: scbeCompassRollCards(mode),
      };
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write('SCBE Compass roll cards:\n');
        for (const card of payload.cards) {
          process.stdout.write(`  ${card.id}: ${card.title} (${card.kind})\n`);
          process.stdout.write(`    expects: ${card.expected_output.required_fields.join(', ')}\n`);
        }
      }
      return;
    }
    if (action === 'stack') {
      const task = String(flags.task || flags.intent || '').trim();
      if (!task) {
        process.stderr.write(`Usage: scbe-agent-bus ${command} stack --task "..." [--json]\n`);
        process.exitCode = 2;
        return;
      }
      const payload = buildScbeRollStack(task);
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write('SCBE Compass roll stack:\n');
        for (const step of payload.steps) {
          process.stdout.write(
            `  ${step.index}. ${step.roll_id} -> ${step.next_roll || '<done>'}\n`
          );
        }
      }
      return;
    }
    if (action === 'plan') {
      const task = String(flags.task || flags.intent || '').trim();
      if (!task) {
        process.stderr.write(`Usage: scbe-agent-bus ${command} plan --task "..." [--json]\n`);
        process.exitCode = 2;
        return;
      }
      const payload = isHermesAlias ? planHermesRoute(task) : planScbeCompassRoute(task);
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `${isHermesAlias ? 'Hermes alias' : 'SCBE Compass'} route: ${payload.mode}`,
            `Objective: ${payload.objective}`,
            `Command path: ${payload.command_path || '<alias>'}`,
            `Primary tools: ${payload.primary_tools.join(', ')}`,
            `Privacy: ${payload.governance.privacy}  Budget cents: ${payload.governance.budget_cents}`,
            payload.formation ? `Formation: ${payload.formation}` : '',
            '',
            'Next commands:',
            ...payload.cli_examples.map((example) => `  ${example}`),
            '',
          ]
            .filter(Boolean)
            .join('\n')
        );
      }
      return;
    }
    process.stderr.write(
      `Usage: scbe-agent-bus ${command} plan|models|tree|board|rolls|stack [--task "..."] [--json]\n`
    );
    process.exitCode = 2;
    return;
  }
  if (command === 'pipeline') {
    const action = String(process.argv[3] || 'run').trim();
    const intent = String(flags.intent || '').trim();
    const governedStateFlag =
      flags['governed-state'] === true || flags['governed-state'] === 'true';
    const pipelineOpts = {
      repoRoot: flags['repo-root'] ? String(flags['repo-root']) : undefined,
      python: flags.python ? String(flags.python) : undefined,
      governedState: governedStateFlag
        ? {
            enabled: true,
            sessionId: flags['session-id'] ? String(flags['session-id']) : 'default',
            statePath: flags['state-path'] ? String(flags['state-path']) : undefined,
            root: flags['state-root'] ? String(flags['state-root']) : undefined,
          }
        : undefined,
    };

    if (action === 'compile') {
      if (!intent) {
        process.stderr.write('Usage: scbe-agent-bus pipeline compile --intent "..." [--json]\n');
        process.exitCode = 2;
        return;
      }
      const plan = compilePlan(intent, pipelineOpts);
      if (!plan) {
        const err = { ok: false, error: 'geoseal compile failed', intent };
        process.stderr.write(
          flags.json
            ? `${JSON.stringify(err, null, 2)}\n`
            : `geoseal compile failed for intent: "${intent}"\n`
        );
        process.exitCode = 1;
        return;
      }
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `GeoSeal plan (${plan.schema_version})`,
            `Intent:   ${plan.intent.text}`,
            `Tool:     ${plan.tool.class} (${plan.tool.contract.tool})`,
            `Policy:   ${plan.policy.decision} — ${plan.policy.reason}`,
            `Command:  ${plan.command.template}`,
            `Runnable: ${plan.command.runnable}`,
            '',
          ].join('\n')
        );
      }
      process.exitCode = plan.policy.decision === 'ALLOW' ? 0 : 1;
      return;
    }

    if (action === 'run') {
      if (!intent) {
        process.stderr.write('Usage: scbe-agent-bus pipeline run --intent "..." [--json]\n');
        process.exitCode = 2;
        return;
      }
      const result = await runPipeline(intent, pipelineOpts);
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
      } else {
        if (result.blocked) {
          process.stderr.write(`Blocked: ${result.block_reason || 'policy denied'}\n`);
        } else if (result.result) {
          const r = result.result;
          process.stdout.write(
            [
              `Pipeline result: ${r.ok ? 'OK' : 'FAIL'}`,
              `Exit code: ${r.exit_code}`,
              r.stderr_tail ? `Stderr: ${r.stderr_tail.slice(-200)}` : '',
              '',
            ]
              .filter(Boolean)
              .join('\n')
          );
          if (r.result != null) {
            process.stdout.write(`${JSON.stringify(r.result, null, 2)}\n`);
          }
        }
      }
      process.exitCode = result.blocked || (result.result && !result.result.ok) ? 1 : 0;
      return;
    }

    if (action === 'state') {
      const repoRoot = flags['repo-root'] ? String(flags['repo-root']) : process.cwd();
      const sessionId =
        String(flags['session-id'] || 'default')
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9._-]+/g, '-')
          .replace(/^-+|-+$/g, '') || 'default';
      const stateRoot = flags['state-root']
        ? path.resolve(String(flags['state-root']))
        : path.join(repoRoot, '.aethermoor-bus', 'governed-state');
      const statePath = flags['state-path']
        ? path.resolve(String(flags['state-path']))
        : path.join(stateRoot, `${sessionId}.json`);
      let state;
      if (flags.init) {
        state = createGovernedPipelineState(sessionId);
        saveGovernedPipelineState(statePath, state);
      } else {
        state = loadGovernedPipelineState(statePath, sessionId);
      }
      const summary = summarizeGovernedPipelineState(state, statePath);
      if (flags.json) {
        process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
      } else {
        process.stdout.write(
          [
            `Governed pipeline state: ${summary.session_id}`,
            `Path: ${summary.state_path}`,
            `Accepted: ${summary.accepted_count}  Rejected: ${summary.rejected_count}`,
            `Reachable next classes: ${summary.reachable_set.join(', ')}`,
            '',
          ].join('\n')
        );
      }
      return;
    }

    process.stderr.write(
      'Usage:\n' +
        '  scbe-agent-bus pipeline run --intent "..." [--json] [--repo-root <path>] [--python <exe>] [--governed-state] [--session-id <id>]\n' +
        '  scbe-agent-bus pipeline compile --intent "..." [--json] [--repo-root <path>] [--python <exe>]\n' +
        '  scbe-agent-bus pipeline state [--session-id <id>] [--state-root <path>] [--state-path <path>] [--init] [--json]\n'
    );
    process.exitCode = 2;
    return;
  }

  if (command === 'health') {
    const result = await fetch(`${baseUrl.replace(/\/+$/, '')}/health`).then((res) => res.json());
    process.stdout.write(
      flags.json ? `${JSON.stringify(result, null, 2)}\n` : `${JSON.stringify(result)}\n`
    );
    return;
  }
  throw new Error(`unknown command: ${command}`);
}

main().catch((err) => {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
});
