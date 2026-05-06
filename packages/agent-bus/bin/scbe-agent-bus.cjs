#!/usr/bin/env node

const { postAgentBusEvent, runAgentBusTerminalUi, startAgentBusServer } = require("../dist/index.js");

function parseArgs(argv) {
  const positionals = [];
  const flags = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      flags[key] = true;
      continue;
    }
    flags[key] = next;
    i += 1;
  }
  return { command: positionals[0] || "help", flags };
}

function printHelp() {
  process.stdout.write(`SCBE Agent Bus

Usage:
  scbe-agent-bus serve --port 8787
  scbe-agent-bus ui --base-url http://127.0.0.1:8787
  scbe-agent-bus send --task "review changed files" --task-type review --json
  scbe-agent-bus health --base-url http://127.0.0.1:8787 --json

Commands:
  serve   Start the local HTTP backend.
  ui      Start the terminal frontend.
  send    Send one governed task to the backend.
  health  Check backend health.
`);
}

async function main() {
  const { command, flags } = parseArgs(process.argv);
  const baseUrl = String(flags["base-url"] || process.env.SCBE_AGENT_BUS_URL || "http://127.0.0.1:8787");
  if (command === "help" || flags.help) {
    printHelp();
    return;
  }
  if (command === "serve") {
    const handle = await startAgentBusServer({
      host: String(flags.host || "127.0.0.1"),
      port: Number(flags.port || 8787),
      repoRoot: flags["repo-root"] ? String(flags["repo-root"]) : undefined,
      python: flags.python ? String(flags.python) : undefined,
      continueOnError: Boolean(flags["continue-on-error"]),
    });
    const payload = {
      schema_version: "scbe-agent-bus-backend-start-v1",
      ok: true,
      url: handle.url,
      routes: ["/health", "/v1/events", "/v1/batch"],
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }
  if (command === "ui") {
    await runAgentBusTerminalUi({ baseUrl });
    return;
  }
  if (command === "send") {
    const task = String(flags.task || "").trim();
    if (!task) throw new Error("send requires --task");
    const result = await postAgentBusEvent(
      {
        task,
        taskType: String(flags["task-type"] || "general"),
        privacy: String(flags.privacy || "local_only"),
        budgetCents: Number(flags["budget-cents"] || 0),
        dispatchProvider: String(flags["dispatch-provider"] || "offline"),
        dispatch: flags.dispatch !== "false",
      },
      { baseUrl }
    );
    process.stdout.write(flags.json ? `${JSON.stringify(result, null, 2)}\n` : `${JSON.stringify(result)}\n`);
    return;
  }
  if (command === "health") {
    const result = await fetch(`${baseUrl.replace(/\/+$/, "")}/health`).then((res) => res.json());
    process.stdout.write(flags.json ? `${JSON.stringify(result, null, 2)}\n` : `${JSON.stringify(result)}\n`);
    return;
  }
  throw new Error(`unknown command: ${command}`);
}

main().catch((err) => {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
});
