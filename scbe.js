#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const scriptPath = path.join(__dirname, "..", "scbe-cli.py");
if (!fs.existsSync(scriptPath)) {
  console.error("scbe-cli.py not found. Ensure the package is intact.");
  process.exit(1);
}

const args = [scriptPath, ...process.argv.slice(2)];
const candidates =
  process.platform === "win32"
    ? [process.env.PYTHON || "python", "py"]
    : [process.env.PYTHON || "python3", "python"];

for (const cmd of candidates) {
  if (!cmd) continue;
  const result = spawnSync(cmd, args, { stdio: "inherit" });
  if (result.error) {
    if (result.error.code === "ENOENT") {
      continue;
    }
    process.exit(result.status ?? 1);
  }
  process.exit(result.status ?? 0);
}

console.error(
  "Python is required to run scbe. Install Python 3.x and retry."
);
process.exit(1);
