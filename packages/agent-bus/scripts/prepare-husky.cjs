#!/usr/bin/env node
"use strict";

const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageRoot, "..", "..");
const hookDir = path.join("packages", "agent-bus", ".husky");
const binName = process.platform === "win32" ? "husky.cmd" : "husky";
const candidates = [
  path.join(repoRoot, "node_modules", ".bin", binName),
  path.join(packageRoot, "node_modules", ".bin", binName)
];

const huskyBin = candidates.find((candidate) => fs.existsSync(candidate));
if (!huskyBin) {
  console.log("[agent-bus] husky not installed; skipping git hook setup");
  process.exit(0);
}

const result = childProcess.spawnSync(huskyBin, ["install", hookDir], {
  cwd: repoRoot,
  stdio: "inherit",
  shell: false
});

if (result.error) {
  console.warn(`[agent-bus] husky setup skipped: ${result.error.message}`);
  process.exit(0);
}

process.exit(result.status === null ? 0 : result.status);
