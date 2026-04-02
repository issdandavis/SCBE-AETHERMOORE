#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ALLOWED_FILE_PATHS = new Set([
  "README.md",
  "LICENSE",
  "dist/src/index.js",
  "dist/src/index.d.ts",
]);

const BANNED_PATTERNS = [
  { re: /(^|\/)__pycache__(\/|$)/, reason: "__pycache__ directory" },
  { re: /\.pyc$/i, reason: ".pyc bytecode file" },
  { re: /\.pyo$/i, reason: ".pyo bytecode file" },
  { re: /(^|\/)\.pytest_cache(\/|$)/, reason: ".pytest_cache directory" },
  { re: /(^|\/)\.mypy_cache(\/|$)/, reason: ".mypy_cache directory" },
  { re: /(^|\/)\.ruff_cache(\/|$)/, reason: ".ruff_cache directory" },
  { re: /^docs\//, reason: "docs should not ship in npm tarball" },
  { re: /^notebooks\//, reason: "notebooks should not ship in npm tarball" },
  { re: /^training-data\//, reason: "training data should not ship in npm tarball" },
  { re: /^training\//, reason: "training code should not ship in npm tarball" },
  { re: /^artifacts\//, reason: "artifacts should not ship in npm tarball" },
  { re: /^app\//, reason: "app surfaces should not ship in npm tarball" },
  { re: /^apps\//, reason: "app surfaces should not ship in npm tarball" },
  { re: /^demo\//, reason: "demo surfaces should not ship in npm tarball" },
  { re: /^desktop\//, reason: "desktop surfaces should not ship in npm tarball" },
  { re: /^conference-app\//, reason: "app surfaces should not ship in npm tarball" },
  { re: /^kindle-app\//, reason: "app surfaces should not ship in npm tarball" },
  { re: /^prototype\//, reason: "prototype surfaces should not ship in npm tarball" },
  { re: /^spaces\//, reason: "space surfaces should not ship in npm tarball" },
  { re: /^examples\//, reason: "examples should not ship in npm tarball" },
  { re: /^\.github\//, reason: "GitHub workflows should not ship in npm tarball" },
  { re: /^src\//, reason: "raw source tree should not ship" },
  { re: /^tests\//, reason: "tests should not ship in npm tarball" },
  { re: /^scripts\//, reason: "repo scripts should not ship in npm tarball" },
  { re: /\.py$/i, reason: "python files should not ship in npm tarball" },
  { re: /\.ipynb$/i, reason: "notebooks should not ship in npm tarball" },
  { re: /\.zip$/i, reason: "zip files should not ship in npm tarball" },
];

const REQUIRED_PATHS = [
  "README.md",
  "LICENSE",
  "dist/src/index.js",
  "dist/src/index.d.ts",
];

function readArg(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx < 0 || idx + 1 >= process.argv.length) return null;
  return process.argv[idx + 1];
}

function parsePackJson(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("[");
    const end = trimmed.lastIndexOf("]");
    if (start >= 0 && end > start) {
      return JSON.parse(trimmed.slice(start, end + 1));
    }
    return null;
  }
}

const packJsonFile =
  readArg("--pack-json") ||
  readArg("--from-file") ||
  path.join(process.cwd(), "artifacts", "npm-pack", "pack.json");

let parsed = null;
if (fs.existsSync(packJsonFile)) {
  parsed = parsePackJson(fs.readFileSync(packJsonFile, "utf8"));
} else {
  const localCache = path.join(process.cwd(), ".npm-cache");
  fs.mkdirSync(localCache, { recursive: true });
  try {
    const packOutput = execSync("npm pack --dry-run --json --ignore-scripts", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, npm_config_cache: localCache },
      maxBuffer: 64 * 1024 * 1024,
      windowsHide: true,
    });
    parsed = parsePackJson(packOutput);
  } catch (err) {
    const stderr = err && err.stderr ? String(err.stderr) : "";
    const stdout = err && err.stdout ? String(err.stdout) : "";
    if (stderr) process.stderr.write(stderr);
    if (stdout) process.stderr.write(stdout);
    if (!stderr && !stdout) {
      const msg = err && err.message ? err.message : "npm pack failed";
      process.stderr.write(`[pack-guard] ${msg}\n`);
    }
    process.exit(err && Number.isInteger(err.status) ? err.status : 1);
  }
}

if (!Array.isArray(parsed) || parsed.length === 0 || !Array.isArray(parsed[0].files)) {
  process.stderr.write("[pack-guard] Unable to parse npm pack --dry-run --json output\n");
  process.exit(1);
}

const info = parsed[0];
const filePaths = info.files.map((f) => f.path).filter(Boolean);
const fileSet = new Set(filePaths);

const violations = [];
for (const filePath of filePaths) {
  if (ALLOWED_FILE_PATHS.has(filePath)) continue;
  for (const rule of BANNED_PATTERNS) {
    if (rule.re.test(filePath)) {
      violations.push({ file: filePath, reason: rule.reason });
      break;
    }
  }
}

const missingRequired = REQUIRED_PATHS.filter((p) => !fileSet.has(p));

console.log(`[pack-guard] tarball=${info.filename} entries=${info.entryCount} size=${info.size}`);

if (missingRequired.length > 0) {
  console.error("[pack-guard] Missing required files:");
  for (const file of missingRequired) console.error(` - ${file}`);
}

if (violations.length > 0) {
  console.error("[pack-guard] Disallowed files detected:");
  for (const v of violations) console.error(` - ${v.file} (${v.reason})`);
}

if (missingRequired.length > 0 || violations.length > 0) {
  process.exit(1);
}

console.log("[pack-guard] package contents are clean");
