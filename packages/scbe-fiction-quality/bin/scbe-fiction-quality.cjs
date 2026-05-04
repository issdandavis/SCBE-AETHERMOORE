#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const PACKAGE_JSON = require(path.join(PACKAGE_ROOT, "package.json"));

function findRepoRoot(startDir) {
  let current = path.resolve(startDir);
  while (true) {
    const scorer = path.join(current, "scripts", "benchmark", "fiction_quality_benchmark.py");
    const blindRound = path.join(current, "scripts", "benchmark", "fiction_quality_blind_round.py");
    if (fs.existsSync(scorer) && fs.existsSync(blindRound)) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

function printHelp() {
  process.stdout.write(`scbe-fiction-quality ${PACKAGE_JSON.version}

Usage:
  scbe-fiction-quality score [args...]
  scbe-fiction-quality blind-round [args...]
  scbe-fiction-quality book-sweep [args...]
  scbe-fiction-quality reference-book [args...]
  scbe-fiction-quality detect [args...]
  scbe-fiction-quality council [args...]
  scbe-fiction-quality version
  scbe-fiction-quality --help

Commands:
  score        Run the deterministic fiction-quality scorer.
  blind-round  Run the anonymous public-domain, AI-control, and own-book comparison round.
  book-sweep   Sample and score the reader-edition manuscript by chapter windows.
  reference-book
               Download and score a public-domain reference book.
  detect       Compare AI-likelihood detector lanes across book/reference sweeps.
  council      Run the multi-lane writing rubric council over quality and detector artifacts.
  version      Print package version.

Examples:
  scbe-fiction-quality score --json
  scbe-fiction-quality blind-round --json
  scbe-fiction-quality book-sweep --json
  scbe-fiction-quality reference-book --json
  scbe-fiction-quality detect --json
  scbe-fiction-quality council --json
  scbe-fiction-quality score --input training-data/evals/fiction_quality_seed.jsonl --json

Environment:
  PYTHON       Python executable to use. Defaults to "python".

This package currently wraps the SCBE-AETHERMOORE Python benchmark scripts so
the scoring logic stays canonical while the npm interface stabilizes.
`);
}

function runPython(scriptRelativePath, args) {
  const repoRoot = findRepoRoot(PACKAGE_ROOT) || findRepoRoot(process.cwd());
  if (!repoRoot) {
    process.stderr.write(
      "Could not find SCBE-AETHERMOORE benchmark scripts. Run this command from a repo checkout or install the full benchmark assets.\n"
    );
    return 2;
  }

  const python = process.env.PYTHON || "python";
  const scriptPath = path.join(repoRoot, scriptRelativePath);
  const result = spawnSync(python, [scriptPath, ...args], {
    cwd: repoRoot,
    stdio: "inherit",
    shell: false,
  });

  if (result.error) {
    process.stderr.write(`${result.error.message}\n`);
    return 1;
  }
  return result.status === null ? 1 : result.status;
}

function main(argv) {
  const [command, ...args] = argv;
  if (!command || command === "--help" || command === "-h" || command === "help") {
    printHelp();
    return 0;
  }
  if (command === "version" || command === "--version" || command === "-v") {
    process.stdout.write(`${PACKAGE_JSON.version}\n`);
    return 0;
  }
  if (command === "score") {
    return runPython(path.join("scripts", "benchmark", "fiction_quality_benchmark.py"), args);
  }
  if (command === "blind-round") {
    return runPython(path.join("scripts", "benchmark", "fiction_quality_blind_round.py"), args);
  }
  if (command === "book-sweep") {
    return runPython(path.join("scripts", "benchmark", "book_quality_sweep.py"), args);
  }
  if (command === "reference-book") {
    return runPython(path.join("scripts", "benchmark", "reference_book_quality_sweep.py"), args);
  }
  if (command === "detect") {
    return runPython(path.join("scripts", "benchmark", "ai_detection_comparison.py"), args);
  }
  if (command === "council") {
    return runPython(path.join("scripts", "benchmark", "writing_rubric_council.py"), args);
  }

  process.stderr.write(`Unknown command: ${command}\n\n`);
  printHelp();
  return 2;
}

process.exitCode = main(process.argv.slice(2));
