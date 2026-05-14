#!/usr/bin/env node

const {
  createAgentWorkspace,
  exportAgentWorkspace,
  postAgentBusEvent,
  runAgentBusTerminalUi,
  startAgentBusServer,
  verifyAgentWorkspaceExport,
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
  scbe-agent-bus serve --port 8787
  scbe-agent-bus ui --base-url http://127.0.0.1:8787
  scbe-agent-bus send --task "review changed files" --task-type review --json
  scbe-agent-bus health --base-url http://127.0.0.1:8787 --json
  scbe-agent-bus workspace new --hint customer-smoke --json
  scbe-agent-bus workspace export --workspace-root .aethermoor-bus/workspaces/<id> --json
  scbe-agent-bus workspace verify --export-path .aethermoor-bus/workspaces/<id>/30_exports/<eid> --json
  scbe-agent-bus upgrade

Commands:
  serve     Start the local HTTP backend.
  ui        Start the terminal frontend.
  send      Send one governed task to the backend.
  health    Check backend health.
  workspace Create a temporary local bus workspace.
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
      const exportPath = String(flags['export-path'] || '').trim();
      if (!exportPath) {
        process.stderr.write(
          'Usage: scbe-agent-bus workspace verify --export-path <path> [--json]\n'
        );
        process.exitCode = 2;
        return;
      }
      const payload = verifyAgentWorkspaceExport({ exportPath });
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
        '  scbe-agent-bus workspace export --workspace-root <path> [--out <name>] [--include 00_inbox,10_work] [--json]\n' +
        '  scbe-agent-bus workspace verify --export-path <path> [--json]\n'
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
    const payload = {
      schema_version: 'scbe-agent-bus-backend-start-v1',
      ok: true,
      url: handle.url,
      routes: ['/health', '/v1/events', '/v1/batch'],
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
    const result = await postAgentBusEvent(
      {
        task,
        taskType: String(flags['task-type'] || 'general'),
        privacy: String(flags.privacy || 'local_only'),
        budgetCents: Number(flags['budget-cents'] || 0),
        dispatchProvider: String(flags['dispatch-provider'] || 'offline'),
        dispatch: flags.dispatch !== 'false',
      },
      { baseUrl }
    );
    process.stdout.write(
      flags.json ? `${JSON.stringify(result, null, 2)}\n` : `${JSON.stringify(result)}\n`
    );
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
