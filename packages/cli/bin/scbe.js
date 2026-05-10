#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const SERVICE_CREDITS = {
  schema_version: "scbe_service_credits_v1",
  name: "SCBE Service Credits",
  policy:
    "Free/local/Ollama-first by default; credits only apply to hosted capacity, report delivery, storage, and provider/model usage.",
  fee: "actual provider/model cost + 2-5% SCBE coordination fee",
  hosted_run_intake: "https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html",
  service_credits: "https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html",
  top_up: "https://ko-fi.com/izdandavis",
};

const CLI_HELP = `scbe-aethermoore-cli

Usage:
  scbe <command> [options]

Core commands:
  scbe version
  scbe selftest
  scbe doctor --json
  scbe credits

Hosted run path:
  scbe credits      Print service-credit policy and hosted-run links.

All other commands are forwarded to the GeoSeal shell from scbe-aethermoore.
`;

function resolveGeosealBin() {
  try {
    const entry = require.resolve("scbe-aethermoore");
    return path.resolve(path.dirname(entry), "..", "..", "bin", "geoseal.cjs");
  } catch (_err) {
    const localFallback = path.resolve(__dirname, "..", "..", "..", "bin", "geoseal.cjs");
    try {
      require("node:fs").accessSync(localFallback);
      return localFallback;
    } catch (_fallbackErr) {
      process.stderr.write(
        "scbe-aethermoore-cli could not find scbe-aethermoore. Reinstall with: npm i -g scbe-aethermoore-cli\n",
      );
      process.exit(1);
    }
  }
}

function runSelftest() {
  const target = resolveGeosealBin();
  const checks = [
    ["version"],
    ["doctor", "--json"],
  ];
  const results = checks.map((args) => {
    const child = spawnSync(process.execPath, [target, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    return {
      command: `scbe ${args.join(" ")}`,
      ok: child.status === 0,
      status: child.status,
      stdout_preview: String(child.stdout || "").slice(0, 500),
      stderr_preview: String(child.stderr || "").slice(0, 500),
    };
  });
  const payload = {
    schema_version: "scbe_aethermoore_cli_selftest_v1",
    ok: results.every((row) => row.ok),
    results,
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(payload.ok ? 0 : 1);
}

const argv = process.argv.slice(2);
if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h" || argv[0] === "help") {
  process.stdout.write(CLI_HELP);
  process.exit(0);
}

if (argv[0] === "credits" || argv[0] === "hosted-run") {
  const asJson = argv.includes("--json");
  if (asJson) {
    process.stdout.write(`${JSON.stringify(SERVICE_CREDITS, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        "SCBE Service Credits",
        "",
        SERVICE_CREDITS.policy,
        `Fee: ${SERVICE_CREDITS.fee}`,
        "",
        `Hosted run intake: ${SERVICE_CREDITS.hosted_run_intake}`,
        `Service credits:    ${SERVICE_CREDITS.service_credits}`,
        `Top up:             ${SERVICE_CREDITS.top_up}`,
        "",
      ].join("\n"),
    );
  }
  process.exit(0);
}

if (argv[0] === "selftest") {
  runSelftest();
}

const target = resolveGeosealBin();
const child = spawnSync(process.execPath, [target, ...argv], {
  stdio: "inherit",
});

if (typeof child.status === "number") {
  process.exit(child.status);
}

process.exit(1);
