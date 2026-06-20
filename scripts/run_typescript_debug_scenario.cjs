#!/usr/bin/env node
"use strict";

const vm = require("node:vm");

let ts = null;
try {
  ts = require("typescript");
} catch {
  ts = null;
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === "--json") {
      args.json = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function stripTypeScript(source) {
  let code = String(source || "");
  code = code.replace(/```(?:typescript|ts|javascript|js)?\s*([\s\S]*?)```/gi, "$1");
  code = code.replace(/\bexport\s+function\s+evaluate\b/g, "function evaluate");
  code = code.trim();
  if (ts) {
    const transpiled = ts.transpileModule(code, {
      compilerOptions: {
        module: ts.ModuleKind.None,
        target: ts.ScriptTarget.ES2020,
        removeComments: true,
      },
      reportDiagnostics: false,
    });
    return transpiled.outputText.trim();
  }
  return code
    .replace(/\bfunction\s+evaluate\s*\([\s\S]*?\)\s*(?::\s*[^{]+)?\s*\{/m, "function evaluate(input, state) {")
    .trim();
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.json) {
    console.error("Usage: node scripts/run_typescript_debug_scenario.cjs --json <scenario-json>");
    process.exit(2);
  }
  const scenario = JSON.parse(args.json);
  const state = structuredClone(scenario.initialState || {});
  const input = structuredClone(scenario.input || {});
  const timeout = Number(scenario.timeoutMs || 250);
  const source = stripTypeScript(scenario.source || "");
  const context = {
    input,
    state,
    result: undefined,
    console: { log() {} },
  };
  vm.createContext(context);
  try {
    vm.runInContext(`${source}\nresult = evaluate(input, state);`, context, { timeout });
    process.stdout.write(
      JSON.stringify({
        id: scenario.id,
        status: "passed",
        result: context.result,
        finalState: state,
      })
    );
  } catch (error) {
    process.stdout.write(
      JSON.stringify({
        id: scenario.id,
        status: "failed",
        error: `${error.name}: ${error.message}`,
        result: null,
        finalState: state,
      })
    );
  }
}

main();
