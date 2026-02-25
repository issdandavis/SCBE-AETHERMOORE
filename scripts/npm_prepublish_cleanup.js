#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const root = process.cwd();

const PRUNE_DIRS = new Set([
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".nyc_output",
  "coverage",
]);

const SKIP_DIRS = new Set([".git", "node_modules"]);
const ROOT_PRUNE_DIRS = ["artifacts/npm-pack"];
const ROOT_FILE_PATTERNS = [/^scbe-aethermoore-.*\.tgz$/];
const PY_CACHE_FILE = /\.py[co]$/i;

let removedPaths = [];
let skippedPaths = [];

function removePath(targetPath) {
  if (!fs.existsSync(targetPath)) return;
  try {
    fs.rmSync(targetPath, { recursive: true, force: true });
    removedPaths.push(path.relative(root, targetPath) || ".");
  } catch (err) {
    if (err && (err.code === "EPERM" || err.code === "EACCES")) {
      skippedPaths.push(path.relative(root, targetPath) || ".");
      return;
    }
    throw err;
  }
}

function walkDir(dirPath) {
  let entries;
  try {
    entries = fs.readdirSync(dirPath, { withFileTypes: true });
  } catch (err) {
    if (err && (err.code === "EPERM" || err.code === "EACCES")) {
      return;
    }
    throw err;
  }
  for (const entry of entries) {
    const full = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      if (PRUNE_DIRS.has(entry.name)) {
        removePath(full);
        continue;
      }
      if (SKIP_DIRS.has(entry.name)) continue;
      walkDir(full);
      continue;
    }
    if (PY_CACHE_FILE.test(entry.name)) {
      removePath(full);
    }
  }
}

for (const rel of ROOT_PRUNE_DIRS) {
  removePath(path.join(root, rel));
}

for (const name of fs.readdirSync(root)) {
  const filePath = path.join(root, name);
  if (!fs.statSync(filePath).isFile()) continue;
  if (ROOT_FILE_PATTERNS.some((re) => re.test(name))) {
    removePath(filePath);
  }
}

walkDir(root);

if (removedPaths.length === 0) {
  console.log("[prepublish-cleanup] no stale artifacts found");
} else {
  removedPaths = [...new Set(removedPaths)].sort();
  console.log(`[prepublish-cleanup] removed ${removedPaths.length} path(s):`);
  for (const rel of removedPaths) {
    console.log(` - ${rel}`);
  }
}

if (skippedPaths.length > 0) {
  skippedPaths = [...new Set(skippedPaths)].sort();
  console.log(`[prepublish-cleanup] skipped ${skippedPaths.length} protected path(s):`);
  for (const rel of skippedPaths) {
    console.log(` - ${rel}`);
  }
}
