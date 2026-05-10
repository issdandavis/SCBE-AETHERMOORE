#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

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
