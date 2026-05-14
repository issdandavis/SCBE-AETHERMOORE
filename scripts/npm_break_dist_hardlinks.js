#!/usr/bin/env node
/*
 * npm rejects tarballs containing hard-link entries. Some Windows sync tools
 * can leave build outputs hard-linked to temporary upload files, so normalize
 * dist files after TypeScript builds and before npm packs.
 */

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const distRoot = path.join(root, "dist");

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(full));
    } else if (entry.isFile()) {
      files.push(full);
    }
  }
  return files;
}

function breakHardlink(file) {
  const stat = fs.statSync(file);
  if (stat.nlink <= 1) return false;
  const bytes = fs.readFileSync(file);
  const mode = stat.mode;
  fs.unlinkSync(file);
  fs.writeFileSync(file, bytes, { mode });
  return true;
}

let broken = 0;
for (const file of walk(distRoot)) {
  if (breakHardlink(file)) {
    broken += 1;
  }
}

console.log(`[break-dist-hardlinks] normalized ${broken} hard-linked dist file(s)`);
